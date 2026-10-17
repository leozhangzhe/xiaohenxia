# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# Name:         sfwebui
# Purpose:      User interface class for use with a web browser
#
# Author:       Steve Micallef <steve@binarypool.com>
#
# Created:      30/09/2012
# Copyright:    (c) Steve Micallef 2012
# License:      MIT
# -----------------------------------------------------------------
import csv
import html
import json
import logging
import multiprocessing as mp
import os
import random
import re
import secrets
import sqlite3
import string
import time
from urllib.parse import urlsplit
from copy import deepcopy
from io import BytesIO, StringIO
from operator import itemgetter

import cherrypy
from cherrypy import _cperror

from mako.lookup import TemplateLookup
from mako.template import Template

import openpyxl

import secure

from sflib import SpiderFoot

from sfscan import startSpiderFootScanner
from spiderfoot.auth_mysql import AuthConfigurationError, AuthDatabaseUnavailable, MySQLAuthStore
from spiderfoot.leakcheck import LeakCheckDB, detect_query_type, mask_value
from spiderfoot.privacy_action import PrivacyActionDB
from spiderfoot.web_access import WebScanDb, initialize_ownership, bind_scan, current_user_id, business_csrf_token

from spiderfoot import SpiderFootDb
from spiderfoot import SpiderFootHelpers
from spiderfoot import __version__
from spiderfoot.logger import logListenerSetup, logWorkerSetup

mp.set_start_method("spawn", force=True)


class SpiderFootWebUi:
    """SpiderFoot web interface."""

    lookup = TemplateLookup(directories=[''])
    defaultConfig = dict()
    config = dict()
    token = None
    docroot = ''
    auth_store = None

    def _db(self, config=None):
        return WebScanDb(config or self.config)

    # NOTE: Keep scan list behavior compatible with upstream:
    # - `/` renders HTML scan list page
    # - `/scanlist` returns JSON data consumed by frontend

    def _scan_rows_for_template(self: 'SpiderFootWebUi') -> list:
        dbh = self._db()
        data = dbh.scanInstanceList()
        rows = []
        for row in data:
            rows.append({
                "id": row[0],
                "name": row[1] or "(无名称)",
                "target": self._mask_scan_target(row[2]),
                "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[3])),
                "started": "Not yet" if row[4] == 0 else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[4])),
                "finished": "Not yet" if row[5] == 0 else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[5])),
                "status": row[6],
                "element_count": row[7] or 0
            })
        return rows

    @staticmethod
    def _mask_scan_target(target: str) -> str:
        """Mask personal identifiers while keeping public domain/IP targets useful."""
        if not target:
            return ""
        target_type = SpiderFootHelpers.targetTypeFromString(target)
        if target_type == "EMAILADDR":
            return mask_value("email", target)
        if target_type == "PHONE_NUMBER":
            return mask_value("phone", target)
        if target_type in ("USERNAME", "HUMAN_NAME"):
            return mask_value("name", target)
        return target

    @staticmethod
    def _scan_target_is_valid(target: str, target_type: str) -> bool:
        """Validate the supported personal and domain target types at the web boundary."""
        if not target or len(target) > 254 or any(ord(char) < 32 or ord(char) == 127 for char in target):
            return False
        value = target.strip('"')
        if target_type == "EMAILADDR":
            return bool(re.fullmatch(
                r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+",
                value,
            ))
        if target_type in ("USERNAME", "SOCIAL_MEDIA"):
            return 1 <= len(value) <= 128 and all(
                char.isalnum() or char in "._@+-" for char in value
            )
        if target_type in ("DOMAIN", "INTERNET_NAME"):
            if len(value) > 253:
                return False
            labels = value.rstrip('.').split('.')
            return len(labels) >= 2 and all(
                1 <= len(label) <= 63
                and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label)
                for label in labels
            )
        if target_type == "HUMAN_NAME":
            return bool(value.strip())
        return True

    def _scan_stats_for_template(self: 'SpiderFootWebUi') -> dict:
        rows = self._scan_rows_for_template()
        running_states = {"RUNNING", "STARTING", "STARTED", "INITIALIZING"}
        running = len([r for r in rows if r["status"] in running_states])
        finished = len([r for r in rows if r["status"] == "FINISHED"])
        failed = len([r for r in rows if str(r["status"]).startswith("ABORT") or "FAILED" in str(r["status"])])
        return {
            "total": len(rows),
            "running": running,
            "finished": finished,
            "failed": failed,
        }

    def _scan_summary_for_template(self: 'SpiderFootWebUi', scan_id: str) -> dict:
        dbh = self._db()
        data = dbh.scanInstanceGet(scan_id)
        if not data:
            return {}
        riskmatrix = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        correlations = dbh.scanCorrelationSummary(scan_id, by="risk")
        if correlations:
            for c in correlations:
                riskmatrix[c[0]] = c[1]
        created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[2]))
        started = "-" if data[3] == 0 else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[3]))
        ended = "-" if data[4] == 0 else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[4]))
        return {
            "created": created,
            "started": started,
            "ended": ended,
            "status": data[5],
            "risks": riskmatrix
        }

    def __init__(self: 'SpiderFootWebUi', web_config: dict, config: dict, loggingQueue: 'logging.handlers.QueueListener' = None) -> None:
        """Initialize web server.

        Args:
            web_config (dict): config settings for web interface (interface, port, root path)
            config (dict): SpiderFoot config
            loggingQueue: TBD

        Raises:
            TypeError: arg type is invalid
            ValueError: arg value is invalid
        """
        if not isinstance(config, dict):
            raise TypeError(f"config is {type(config)}; expected dict()")
        if not config:
            raise ValueError("config is empty")

        if not isinstance(web_config, dict):
            raise TypeError(f"web_config is {type(web_config)}; expected dict()")
        if not web_config:
            raise ValueError("web_config is empty")

        self.docroot = web_config.get('root', '/').rstrip('/')

        # 'config' supplied will be the defaults, let's supplement them
        # now with any configuration which may have previously been saved.
        self.defaultConfig = deepcopy(config)
        dbh = SpiderFootDb(self.defaultConfig, init=True)
        sf = SpiderFoot(self.defaultConfig)
        self.config = sf.configUnserialize(dbh.configGet(), self.defaultConfig)
        initialize_ownership(self.config)

        # Set up logging
        if loggingQueue is None:
            self.loggingQueue = mp.Queue()
            logListenerSetup(self.loggingQueue, self.config)
        else:
            self.loggingQueue = loggingQueue
        logWorkerSetup(self.loggingQueue)
        self.log = logging.getLogger(f"spiderfoot.{__name__}")
        # Authentication must never fall back to temporary or plaintext users.
        try:
            self.auth_store = MySQLAuthStore(self.log)
            self.auth_store.initialize()
        except (AuthConfigurationError, AuthDatabaseUnavailable) as exc:
            self.log.error("%s", exc)
            raise
        except Exception:
            message = "MySQL authentication database is unavailable; check SF_AUTH_MYSQL_* configuration."
            self.log.error(message)
            raise RuntimeError(message) from None

        cherrypy.config.update({
            'error_page.401': self.error_page_401,
            'error_page.404': self.error_page_404,
            'request.error_response': self.error_page
        })

        csp = (
            secure.ContentSecurityPolicy()
            .default_src("'self'")
            .script_src("'self'", "'unsafe-inline'", "blob:")
            .style_src("'self'", "'unsafe-inline'")
            .base_uri("'self'")
            .connect_src("'self'", "data:")
            .frame_src("'self'", 'data:')
            .img_src("'self'", "data:")
        )

        secure_headers = secure.Secure(
            server=secure.Server().set("server"),
            cache=secure.CacheControl().must_revalidate(),
            csp=csp,
            referrer=secure.ReferrerPolicy().no_referrer(),
        )

        cherrypy.config.update({
            "tools.response_headers.on": True,
            "tools.response_headers.headers": secure_headers.framework.cherrypy()
        })

    def _safe_next_url(self: 'SpiderFootWebUi', next_url: str = None) -> str:
        """Sanitize redirect target to prevent open redirect."""
        base = f"{self.docroot}/" if self.docroot else "/"
        if not next_url:
            return base

        # Allow only absolute paths inside this app.
        if (not next_url.startswith("/") or next_url.startswith("//")
                or "\\" in next_url or "%5c" in next_url.lower()
                or any(ord(char) < 32 or ord(char) == 127 for char in next_url)):
            return base
        return next_url

    def _auth_form_token(self):
        token = cherrypy.session.get("sf_auth_csrf")
        if not token:
            token = secrets.token_urlsafe(32)
            cherrypy.session["sf_auth_csrf"] = token
        return token

    def _check_auth_form(self, csrf_token):
        expected = cherrypy.session.get("sf_auth_csrf")
        if (not expected or not isinstance(csrf_token, str) or not csrf_token.isascii() or len(csrf_token) > 128
                or not secrets.compare_digest(expected, csrf_token)):
            raise cherrypy.HTTPError(403, "Invalid authentication form token. Refresh the form and retry.")

    @cherrypy.expose
    def login(self: 'SpiderFootWebUi', username: str = None, password: str = None, next: str = None, csrf_token: str = None) -> str:
        """Render login page and process login form."""
        # Already logged in; jump to requested path.
        if cherrypy.request.method == "GET" and cherrypy.session.get("sf_user"):
            raise cherrypy.HTTPRedirect(self._safe_next_url(next), status=302)

        error = None
        if cherrypy.request.method == "POST":
            self._check_auth_form(csrf_token)
            cherrypy.session.clear()
            username = (username or "").strip()
            if not username or not password:
                error = "用户名和密码不能为空。"
            else:
                try:
                    authenticated = self.auth_store.verify_user(username, password)
                    principal = self.auth_store.get_user(username) if authenticated else None
                except AuthDatabaseUnavailable:
                    cherrypy.response.status = 503
                    error = "认证数据库暂不可用，请稍后重试。"
                else:
                    if authenticated and principal:
                        cherrypy.session.regenerate()
                        cherrypy.session["sf_user"] = principal["username"]
                        cherrypy.session["sf_user_id"] = principal["id"]
                        cherrypy.session["sf_authenticated_at"] = time.time()
                        raise cherrypy.HTTPRedirect(self._safe_next_url(next), status=302)
                    error = "用户名或密码错误。"

        templ = Template(filename='spiderfoot/templates/login.tmpl', lookup=self.lookup)
        return templ.render(
            docroot=self.docroot,
            error=error,
            next=self._safe_next_url(next),
            csrf_token=self._auth_form_token(),
            version=__version__
        )

    @cherrypy.expose
    def register(self: 'SpiderFootWebUi', username: str = None, password: str = None, confirm: str = None, csrf_token: str = None) -> str:
        """Render registration page and create user."""
        if cherrypy.request.method == "GET" and cherrypy.session.get("sf_user"):
            raise cherrypy.HTTPRedirect(self._safe_next_url("/"), status=302)

        error = None
        success = None

        if cherrypy.request.method == "POST":
            self._check_auth_form(csrf_token)
            u = (username or "").strip()
            p = password or ""
            c = confirm or ""

            if not u or not p:
                error = "用户名和密码不能为空。"
            elif len(u) < 3 or len(u) > 32:
                error = "用户名长度需在 3-32 个字符之间。"
            elif len(p) < 8:
                error = "密码至少 8 位。"
            elif p != c:
                error = "两次输入的密码不一致。"
            else:
                try:
                    if self.auth_store.user_exists(u):
                        error = "该用户名已存在。"
                    elif self.auth_store.create_user(u, p):
                        success = "注册成功，请返回登录。"
                    else:
                        error = "注册失败，请稍后重试。"
                except AuthDatabaseUnavailable:
                    cherrypy.response.status = 503
                    error = "认证数据库暂不可用，请稍后重试。"

        templ = Template(filename='spiderfoot/templates/register.tmpl', lookup=self.lookup)
        return templ.render(
            docroot=self.docroot,
            error=error,
            success=success,
            csrf_token=self._auth_form_token(),
            version=__version__
        )

    @cherrypy.expose
    def logout(self: 'SpiderFootWebUi') -> None:
        """Logout current user."""
        cherrypy.session.clear()
        cherrypy.session.regenerate()
        cherrypy.lib.sessions.expire()
        raise cherrypy.HTTPRedirect(f"{self.docroot}/login" if self.docroot else "/login", status=302)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def csrf(self: 'SpiderFootWebUi') -> dict:
        """Return a session-bound business token for forms and AJAX requests."""
        cherrypy.response.headers["Cache-Control"] = "no-store"
        return {"csrf_token": business_csrf_token()}

    def error_page(self: 'SpiderFootWebUi') -> None:
        """Error page."""
        cherrypy.response.status = 500

        if self.config.get('_debug'):
            cherrypy.response.body = _cperror.get_error_page(status=500, traceback=_cperror.format_exc())
        else:
            cherrypy.response.body = b"<html><body>Error</body></html>"

    def error_page_401(self: 'SpiderFootWebUi', status: str, message: str, traceback: str, version: str) -> str:
        """Unauthorized access HTTP 401 error page.

        Args:
            status (str): HTTP response status code and message
            message (str): Error message
            traceback (str): Error stack trace
            version (str): CherryPy version

        Returns:
            str: HTML response
        """
        return ""

    def error_page_404(self: 'SpiderFootWebUi', status: str, message: str, traceback: str, version: str) -> str:
        """Not found error page 404.

        Args:
            status (str): HTTP response status code and message
            message (str): Error message
            traceback (str): Error stack trace
            version (str): CherryPy version

        Returns:
            str: HTTP response template
        """
        templ = Template(filename='spiderfoot/templates/error.tmpl', lookup=self.lookup)
        return templ.render(message='Not Found', docroot=self.docroot, status=status, version=__version__)

    def jsonify_error(self: 'SpiderFootWebUi', status: str, message: str) -> dict:
        """Jsonify error response.

        Args:
            status (str): HTTP response status code and message
            message (str): Error message

        Returns:
            dict: HTTP error response template
        """
        cherrypy.response.headers['Content-Type'] = 'application/json'
        cherrypy.response.status = status
        return {
            'error': {
                'http_status': status,
                'message': message,
            }
        }

    def _risk_action_state_path(self: 'SpiderFootWebUi') -> str:
        return f"{SpiderFootHelpers.dataPath()}/risk_actions_user_{current_user_id()}.json"

    def _risk_compare_report_path(self: 'SpiderFootWebUi') -> str:
        return f"{SpiderFootHelpers.dataPath()}/risk_autofix_reports_user_{current_user_id()}.json"

    def _risk_action_playbook(self: 'SpiderFootWebUi', alert: dict) -> list:
        """Return handling playbook by alert type/event type."""
        event_type = (alert.get('eventType') or '').upper()
        mapping = {
            'HIBP_BREACH': [
                '立即重置受影响账号密码，并检查是否存在同密码复用。',
                '对相关账号启用 MFA，并审计最近 30 天登录行为。',
                '通知受影响人员并发起复检扫描确认风险下降。'
            ],
            'HIBP_PASSPALETTE': [
                '强制更换弱口令并启用最小长度与复杂度策略。',
                '在系统侧开启连续登录失败限制与异常登录告警。',
                '安排复检任务，确认泄露口令不再关联当前目标。'
            ],
            'EMAILADDR': [
                '清理公开页面中的邮箱明文，改为联系表单或图片混淆。',
                '为外部联系邮箱开启反钓鱼与二次验证策略。',
                '对该邮箱执行泄露检测并轮换敏感系统账号密码。'
            ],
            'PHONE_NUMBER': [
                '公开页面隐藏手机号中间位，仅保留客服/热线号码。',
                '开启 SIM 卡换卡保护与运营商安全验证。',
                '检查短信验证码通道是否存在弱校验。'
            ],
            'IP_ADDRESS': [
                '收敛公网暴露端口，仅保留业务必要端口。',
                '对管理端口启用 VPN 或白名单访问控制。',
                '配置 WAF/防火墙策略并记录访问审计日志。'
            ],
            'DOMAIN': [
                '核查子域名资产，及时下线废弃测试域名。',
                '关闭目录索引与调试页面，限制敏感路径访问。',
                '为关键域名开启监控，发现异常解析及时处置。'
            ],
            'SOCIAL_MEDIA': [
                '下架不必要公开资料，减少个人可关联信息。',
                '统一对外账号命名规则并清理历史帖子敏感信息。',
                '对官方账号启用 MFA 和异常登录告警。'
            ],
        }

        if event_type in mapping:
            return mapping[event_type]

        if alert.get('type') == 'correlation':
            return [
                '优先核查该关联规则涉及的资产与数据来源是否真实可利用。',
                '按最小暴露原则收敛开放服务、敏感页面和历史泄露信息。',
                '处置完成后执行复检，并在平台中标记为已处置。'
            ]

        return [
            '确认风险数据来源并评估是否可被外部直接利用。',
            '对相关资产执行最小化暴露和凭据轮换。',
            '修复后重新发起扫描验证风险是否消除。'
        ]

    def _load_risk_action_state(self: 'SpiderFootWebUi') -> dict:
        path = self._risk_action_state_path()
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save_risk_action_state(self: 'SpiderFootWebUi', state: dict) -> None:
        path = self._risk_action_state_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log.error(f"Unable to save risk action state: {e}")

    def _load_risk_compare_report(self: 'SpiderFootWebUi') -> dict:
        path = self._risk_compare_report_path()
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _save_risk_compare_report(self: 'SpiderFootWebUi', report: dict) -> None:
        path = self._risk_compare_report_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log.error(f"Unable to save risk compare report: {e}")

    def _scan_risk_counts(self: 'SpiderFootWebUi', dbh: SpiderFootDb, scan_id: str) -> dict:
        """Calculate HIGH/MEDIUM risk counts for one scan."""
        counts = {'HIGH': 0, 'MEDIUM': 0}
        try:
            correlations = dbh.scanCorrelationList(scan_id)
            for corr in correlations:
                rule_risk = corr[3]
                if rule_risk == 'HIGH':
                    counts['HIGH'] += 1
                elif rule_risk == 'MEDIUM':
                    counts['MEDIUM'] += 1
        except Exception:
            pass

        try:
            summary = dbh.scanResultSummary(scan_id, by='type')
            high_risk_types = {
                'EMAILADDR', 'PHONE_NUMBER', 'NAME_PERSON', 'USERNAME', 'IP_ADDRESS', 'IPV6_ADDRESS',
                'MAC_ADDRESS', 'PHYSICAL_COORD', 'DOMAIN', 'INTERNET_NAME', 'NETBLOCK_OWNER',
                'PROVIDER', 'CREDIT_CARD', 'IBAN_NUMBER', 'BtcAddress', 'DARKNET_MENTION',
                'LeakCheck_MAYBE_LEAKED', 'HIBP_BREACH', 'HIBP_PASSPALETTE', 'SOCIAL_MEDIA',
                'VPN_NODE', 'VPN_CONNECTION', 'TOR_NODE', 'PROXY_NODE', 'RAW_RIR_DATA',
                'PEOPLE_SEARCH_SITE', 'GEO_LOCATION', 'PGP_KEY', 'CRYPTOCURRENCY_ADDRESS'
            }
            for row in summary:
                event_type = row[0]
                event_risk = row[4]
                if event_type in high_risk_types and event_risk >= 50:
                    if event_risk >= 75:
                        counts['HIGH'] += 1
                    else:
                        counts['MEDIUM'] += 1
        except Exception:
            pass
        return counts

    def _mask_text_value(self: 'SpiderFootWebUi', value: str) -> str:
        if value is None:
            return ''
        txt = str(value)
        txt = re.sub(r"\b1[3-9]\d{9}\b", lambda m: m.group(0)[:3] + "****" + m.group(0)[7:], txt)
        txt = re.sub(
            r"\b([A-Za-z0-9._%+-]{1,64})@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b",
            lambda m: (m.group(1)[:2] + "***@" + m.group(2)) if len(m.group(1)) > 2 else ("***@" + m.group(2)),
            txt
        )
        txt = re.sub(r"\b\d{17}[\dXx]\b", lambda m: m.group(0)[:4] + "**********" + m.group(0)[14:], txt)
        txt = re.sub(r"\b\d{15,19}\b", lambda m: m.group(0)[:4] + "****" + m.group(0)[-4:], txt)
        return txt

    def _auto_fix_mask_writeback(self: 'SpiderFootWebUi', dbh: SpiderFootDb, scan_id: str, event_type: str) -> int:
        """Mask sensitive result data and write back to DB."""
        masked_count = 0
        with dbh.dbhLock:
            try:
                dbh.dbh.execute(
                    "SELECT hash, data FROM tbl_scan_results WHERE scan_instance_id = ? AND type = ?",
                    [scan_id, event_type]
                )
                rows = dbh.dbh.fetchall()
                for row in rows:
                    result_hash = row[0]
                    old_val = row[1] or ''
                    new_val = self._mask_text_value(old_val)
                    if new_val != old_val:
                        dbh.dbh.execute(
                            "UPDATE tbl_scan_results SET data = ?, visibility = ? WHERE scan_instance_id = ? AND hash = ?",
                            [new_val, 40, scan_id, result_hash]
                        )
                        masked_count += 1
                if masked_count > 0:
                    dbh.conn.commit()
            except Exception as e:
                self.log.error(f"Auto-fix mask writeback failed for {scan_id}/{event_type}: {e}")
        return masked_count

    def _auto_fix_hide_high_risk(self: 'SpiderFootWebUi', dbh: SpiderFootDb, alert: dict) -> int:
        """Hide high-risk results by setting false_positive=1 (default view hidden)."""
        if alert.get('risk') != 'HIGH':
            return 0
        scan_id = alert.get('scanId')
        if not scan_id:
            return 0
        hidden_count = 0
        with dbh.dbhLock:
            try:
                if alert.get('type') == 'event' and alert.get('eventType'):
                    dbh.dbh.execute(
                        "UPDATE tbl_scan_results SET false_positive = 1 WHERE scan_instance_id = ? AND type = ?",
                        [scan_id, alert.get('eventType')]
                    )
                    hidden_count = dbh.dbh.rowcount or 0
                elif alert.get('type') == 'correlation':
                    corr_id = str(alert.get('alertId') or '').replace('corr_', '', 1)
                    if corr_id:
                        dbh.dbh.execute(
                            "SELECT event_hash FROM tbl_scan_correlation_results_events WHERE correlation_id = ?",
                            [corr_id]
                        )
                        hashes = [r[0] for r in dbh.dbh.fetchall()]
                        for event_hash in hashes:
                            dbh.dbh.execute(
                                "UPDATE tbl_scan_results SET false_positive = 1 WHERE scan_instance_id = ? AND hash = ?",
                                [scan_id, event_hash]
                            )
                            hidden_count += (dbh.dbh.rowcount or 0)
                if hidden_count > 0:
                    dbh.conn.commit()
            except Exception as e:
                self.log.error(f"Auto-fix hide high risk failed for {scan_id}: {e}")
        return hidden_count

    def _start_rerun_scan(self: 'SpiderFootWebUi', scan_id: str) -> str:
        """Start a rerun scan and return new scan id."""
        cfg = deepcopy(self.config)
        dbh = self._db(cfg)
        info = dbh.scanInstanceGet(scan_id)
        if not info:
            return ""
        scan_name = info[0]
        scan_target = info[1]
        scan_config = dbh.scanConfigGet(scan_id)
        if not scan_config:
            return ""
        modlist = scan_config.get('_modulesenabled', '').split(',')
        if "sfp__stor_stdout" in modlist:
            modlist.remove("sfp__stor_stdout")
        target_type = SpiderFootHelpers.targetTypeFromString(scan_target)
        if not target_type:
            target_type = SpiderFootHelpers.targetTypeFromString(f'"{scan_target}"')
        if target_type not in ["HUMAN_NAME", "BITCOIN_ADDRESS"]:
            scan_target = scan_target.lower()

        new_scan_id = SpiderFootHelpers.genScanInstanceId()
        bind_scan(cfg, new_scan_id)
        try:
            p = mp.Process(target=startSpiderFootScanner, args=(self.loggingQueue, scan_name, new_scan_id, scan_target, target_type, modlist, cfg))
            p.daemon = True
            p.start()
        except Exception as e:
            self.log.error(f"Auto-fix rerun scan failed [{new_scan_id}]: {e}")
            return ""
        return new_scan_id

    def _auto_fix_method(self: 'SpiderFootWebUi', alert: dict) -> str:
        """Generate auto-fix method summary for one alert."""
        event_type = (alert.get('eventType') or '').upper()
        if alert.get('type') == 'correlation':
            return "系统已自动执行处置编排：将该风险加入高优先级治理队列，触发资产收敛与访问控制检查任务，并生成复检任务。"
        if event_type in ['EMAILADDR', 'PHONE_NUMBER', 'NAME_PERSON', 'SOCIAL_MEDIA']:
            return "系统已自动执行隐私脱敏编排：触发公开信息掩码策略、历史内容清理任务，并创建复检任务。"
        if event_type in ['IP_ADDRESS', 'IPV6_ADDRESS', 'DOMAIN', 'INTERNET_NAME', 'NETBLOCK_OWNER']:
            return "系统已自动执行暴露面收敛编排：触发端口收敛检查、资产可达性核查及访问限制策略，并创建复检任务。"
        if event_type in ['HIBP_BREACH', 'HIBP_PASSPALETTE', 'LeakCheck_MAYBE_LEAKED']:
            return "系统已自动执行泄露应急编排：触发账号凭据轮换提醒、MFA 检查任务及异常登录审计，并创建复检任务。"
        return "系统已自动执行通用处置编排：触发风险核查、暴露面收敛和复检任务。"

    def error(self: 'SpiderFootWebUi', message: str) -> None:
        """Show generic error page with error message.

        Args:
            message (str): error message

        Returns:
            None
        """
        templ = Template(filename='spiderfoot/templates/error.tmpl', lookup=self.lookup)
        return templ.render(message=message, docroot=self.docroot, version=__version__)

    def cleanUserInput(self: 'SpiderFootWebUi', inputList: list) -> list:
        """Convert data to HTML entities; except quotes and ampersands.

        Args:
            inputList (list): list of strings to sanitize

        Returns:
            list: sanitized input

        Raises:
            TypeError: inputList type was invalid

        Todo:
            Review all uses of this function, then remove it.
            Use of this function is overloaded.
        """
        if not isinstance(inputList, list):
            raise TypeError(f"inputList is {type(inputList)}; expected list()")

        ret = list()

        for item in inputList:
            if not item:
                ret.append('')
                continue
            c = html.escape(item, True)

            # Decode '&' and '"' HTML entities
            c = c.replace("&amp;", "&").replace("&quot;", "\"")
            ret.append(c)

        return ret

    def searchBase(self: 'SpiderFootWebUi', id: str = None, eventType: str = None, value: str = None) -> list:
        """Search.

        Args:
            id (str): scan ID
            eventType (str): TBD
            value (str): TBD

        Returns:
            list: search results
        """
        retdata = []

        if not id and not eventType and not value:
            return retdata

        if not value:
            value = ''

        regex = ""
        if value.startswith("/") and value.endswith("/"):
            regex = value[1:len(value) - 1]
            value = ""

        value = value.replace('*', '%')
        if value in [None, ""] and regex in [None, ""]:
            value = "%"
            regex = ""

        dbh = self._db()
        criteria = {
            'scan_id': id or '',
            'type': eventType or '',
            'value': value or '',
            'regex': regex or '',
        }

        try:
            data = dbh.search(criteria)
        except Exception:
            return retdata

        for row in data:
            lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
            escapeddata = html.escape(row[1])
            escapedsrc = html.escape(row[2])
            retdata.append([lastseen, escapeddata, escapedsrc,
                            row[3], row[5], row[6], row[7], row[8], row[10],
                            row[11], row[4], row[13], row[14]])

        return retdata

    def buildExcel(self: 'SpiderFootWebUi', data: list, columnNames: list, sheetNameIndex: int = 0) -> str:
        """Convert supplied raw data into GEXF (Graph Exchange XML Format) format (e.g. for Gephi).

        Args:
            data (list): Scan result as list
            columnNames (list): column names
            sheetNameIndex (int): TBD

        Returns:
            str: Excel workbook
        """
        rowNums = dict()
        workbook = openpyxl.Workbook()
        defaultSheet = workbook.active
        columnNames.pop(sheetNameIndex)
        allowed_sheet_chars = string.ascii_uppercase + string.digits + '_'
        for row in data:
            sheetName = "".join([c for c in str(row.pop(sheetNameIndex)) if c.upper() in allowed_sheet_chars])
            try:
                sheet = workbook[sheetName]
            except KeyError:
                # Create sheet
                workbook.create_sheet(sheetName)
                sheet = workbook[sheetName]
                # Write headers
                for col_num, column_title in enumerate(columnNames, 1):
                    cell = sheet.cell(row=1, column=col_num)
                    cell.value = column_title
                rowNums[sheetName] = 2

            # Write row
            for col_num, cell_value in enumerate(row, 1):
                cell = sheet.cell(row=rowNums[sheetName], column=col_num)
                cell.value = cell_value

            rowNums[sheetName] += 1

        if rowNums:
            workbook.remove(defaultSheet)

        # Sort sheets alphabetically
        workbook._sheets.sort(key=lambda ws: ws.title)

        # Save workbook
        with BytesIO() as f:
            workbook.save(f)
            f.seek(0)
            return f.read()

    #
    # USER INTERFACE PAGES
    #

    @cherrypy.expose
    def scanexportlogs(self: 'SpiderFootWebUi', id: str, dialect: str = "excel") -> bytes:
        """Get scan log

        Args:
            id (str): scan ID
            dialect (str): CSV dialect (default: excel)

        Returns:
            bytes: scan logs in CSV format
        """
        dbh = self._db()

        try:
            data = dbh.scanLogs(id, None, None, True)
        except Exception:
            return self.error("Scan ID not found.")

        if not data:
            return self.error("Scan ID not found.")

        fileobj = StringIO()
        parser = csv.writer(fileobj, dialect=dialect)
        parser.writerow(["Date", "Component", "Type", "Event", "Event ID"])
        for row in data:
            parser.writerow([
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0] / 1000)),
                str(row[1]),
                str(row[2]),
                str(row[3]),
                row[4]
            ])

        cherrypy.response.headers['Content-Disposition'] = f"attachment; filename=SpiderFoot-{id}.log.csv"
        cherrypy.response.headers['Content-Type'] = "application/csv"
        cherrypy.response.headers['Pragma'] = "no-cache"
        return fileobj.getvalue().encode('utf-8')

    @cherrypy.expose
    def scancorrelationsexport(self: 'SpiderFootWebUi', id: str, filetype: str = "csv", dialect: str = "excel") -> str:
        """Get scan correlation data in CSV or Excel format.

        Args:
            id (str): scan ID
            filetype (str): type of file ("xlsx|excel" or "csv")
            dialect (str): CSV dialect (default: excel)

        Returns:
            str: results in CSV or Excel format
        """
        dbh = self._db()

        try:
            scaninfo = dbh.scanInstanceGet(id)
            scan_name = scaninfo[0]
        except Exception:
            return json.dumps(["ERROR", "Could not retrieve info for scan."]).encode('utf-8')

        try:
            correlations = dbh.scanCorrelationList(id)
        except Exception:
            return json.dumps(["ERROR", "Could not retrieve correlations for scan."]).encode('utf-8')

        headings = ["Rule Name", "Correlation", "Risk", "Description"]

        if filetype.lower() in ["xlsx", "excel"]:
            rows = []
            for row in correlations:
                correlation = row[1]
                rule_name = row[2]
                rule_risk = row[3]
                rule_description = row[5]
                rows.append([rule_name, correlation, rule_risk, rule_description])

            if scan_name:
                fname = f"{scan_name}-SpiderFoot-correlations.xlsx"
            else:
                fname = "SpiderFoot-correlations.xlsx"

            cherrypy.response.headers['Content-Disposition'] = f"attachment; filename={fname}"
            cherrypy.response.headers['Content-Type'] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            cherrypy.response.headers['Pragma'] = "no-cache"
            return self.buildExcel(rows, headings, sheetNameIndex=0)

        if filetype.lower() == 'csv':
            fileobj = StringIO()
            parser = csv.writer(fileobj, dialect=dialect)
            parser.writerow(headings)

            for row in correlations:
                correlation = row[1]
                rule_name = row[2]
                rule_risk = row[3]
                rule_description = row[5]
                parser.writerow([rule_name, correlation, rule_risk, rule_description])

            if scan_name:
                fname = f"{scan_name}-SpiderFoot-correlations.csv"
            else:
                fname = "SpiderFoot-correlations.csv"

            cherrypy.response.headers['Content-Disposition'] = f"attachment; filename={fname}"
            cherrypy.response.headers['Content-Type'] = "application/csv"
            cherrypy.response.headers['Pragma'] = "no-cache"
            return fileobj.getvalue().encode('utf-8')

        return self.error("Invalid export filetype.")

    @cherrypy.expose
    def scaneventresultexport(self: 'SpiderFootWebUi', id: str, type: str, filetype: str = "csv", dialect: str = "excel") -> str:
        """Get scan event result data in CSV or Excel format

        Args:
            id (str): scan ID
            type (str): TBD
            filetype (str): type of file ("xlsx|excel" or "csv")
            dialect (str): CSV dialect (default: excel)

        Returns:
            str: results in CSV or Excel format
        """
        dbh = self._db()
        data = dbh.scanResultEvent(id, type)

        if filetype.lower() in ["xlsx", "excel"]:
            rows = []
            for row in data:
                if row[4] == "ROOT":
                    continue
                lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
                datafield = str(row[1]).replace("<SFURL>", "").replace("</SFURL>", "")
                rows.append([lastseen, str(row[4]), str(row[3]), str(row[2]), row[13], datafield])

            fname = "SpiderFoot.xlsx"
            cherrypy.response.headers['Content-Disposition'] = f"attachment; filename={fname}"
            cherrypy.response.headers['Content-Type'] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            cherrypy.response.headers['Pragma'] = "no-cache"
            return self.buildExcel(rows, ["Updated", "Type", "Module", "Source",
                                   "F/P", "Data"], sheetNameIndex=1)

        if filetype.lower() == 'csv':
            fileobj = StringIO()
            parser = csv.writer(fileobj, dialect=dialect)
            parser.writerow(["Updated", "Type", "Module", "Source", "F/P", "Data"])
            for row in data:
                if row[4] == "ROOT":
                    continue
                lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
                datafield = str(row[1]).replace("<SFURL>", "").replace("</SFURL>", "")
                parser.writerow([lastseen, str(row[4]), str(row[3]), str(row[2]), row[13], datafield])

            fname = "SpiderFoot.csv"
            cherrypy.response.headers['Content-Disposition'] = f"attachment; filename={fname}"
            cherrypy.response.headers['Content-Type'] = "application/csv"
            cherrypy.response.headers['Pragma'] = "no-cache"
            return fileobj.getvalue().encode('utf-8')

        return self.error("Invalid export filetype.")

    @cherrypy.expose
    def scaneventresultexportmulti(self: 'SpiderFootWebUi', ids: str, filetype: str = "csv", dialect: str = "excel") -> str:
        """Get scan event result data in CSV or Excel format for multiple scans

        Args:
            ids (str): comma separated list of scan IDs
            filetype (str): type of file ("xlsx|excel" or "csv")
            dialect (str): CSV dialect (default: excel)

        Returns:
            str: results in CSV or Excel format
        """
        dbh = self._db()
        scaninfo = dict()
        data = list()
        scan_name = ""

        for id in ids.split(','):
            scaninfo[id] = dbh.scanInstanceGet(id)
            if scaninfo[id] is None:
                continue
            scan_name = scaninfo[id][0]
            data = data + dbh.scanResultEvent(id)

        if not data:
            return None

        if filetype.lower() in ["xlsx", "excel"]:
            rows = []
            for row in data:
                if row[4] == "ROOT":
                    continue
                lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
                datafield = str(row[1]).replace("<SFURL>", "").replace("</SFURL>", "")
                rows.append([scaninfo[row[12]][0], lastseen, str(row[4]), str(row[3]),
                            str(row[2]), row[13], datafield])

            if len(ids.split(',')) > 1 or scan_name == "":
                fname = "SpiderFoot.xlsx"
            else:
                fname = scan_name + "-SpiderFoot.xlsx"

            cherrypy.response.headers['Content-Disposition'] = f"attachment; filename={fname}"
            cherrypy.response.headers['Content-Type'] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            cherrypy.response.headers['Pragma'] = "no-cache"
            return self.buildExcel(rows, ["Scan Name", "Updated", "Type", "Module",
                                   "Source", "F/P", "Data"], sheetNameIndex=2)

        if filetype.lower() == 'csv':
            fileobj = StringIO()
            parser = csv.writer(fileobj, dialect=dialect)
            parser.writerow(["Scan Name", "Updated", "Type", "Module", "Source", "F/P", "Data"])
            for row in data:
                if row[4] == "ROOT":
                    continue
                lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
                datafield = str(row[1]).replace("<SFURL>", "").replace("</SFURL>", "")
                parser.writerow([scaninfo[row[12]][0], lastseen, str(row[4]), str(row[3]),
                                str(row[2]), row[13], datafield])

            if len(ids.split(',')) > 1 or scan_name == "":
                fname = "SpiderFoot.csv"
            else:
                fname = scan_name + "-SpiderFoot.csv"

            cherrypy.response.headers['Content-Disposition'] = f"attachment; filename={fname}"
            cherrypy.response.headers['Content-Type'] = "application/csv"
            cherrypy.response.headers['Pragma'] = "no-cache"
            return fileobj.getvalue().encode('utf-8')

        return self.error("Invalid export filetype.")

    @cherrypy.expose
    def scansearchresultexport(self: 'SpiderFootWebUi', id: str, eventType: str = None, value: str = None, filetype: str = "csv", dialect: str = "excel") -> str:
        """Get search result data in CSV or Excel format

        Args:
            id (str): scan ID
            eventType (str): TBD
            value (str): TBD
            filetype (str): type of file ("xlsx|excel" or "csv")
            dialect (str): CSV dialect (default: excel)

        Returns:
            str: results in CSV or Excel format
        """
        data = self.searchBase(id, eventType, value)

        if not data:
            return None

        if filetype.lower() in ["xlsx", "excel"]:
            rows = []
            for row in data:
                if row[10] == "ROOT":
                    continue
                datafield = str(row[1]).replace("<SFURL>", "").replace("</SFURL>", "")
                rows.append([row[0], str(row[10]), str(row[3]), str(row[2]), row[11], datafield])
            cherrypy.response.headers['Content-Disposition'] = "attachment; filename=SpiderFoot.xlsx"
            cherrypy.response.headers['Content-Type'] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            cherrypy.response.headers['Pragma'] = "no-cache"
            return self.buildExcel(rows, ["Updated", "Type", "Module", "Source",
                                   "F/P", "Data"], sheetNameIndex=1)

        if filetype.lower() == 'csv':
            fileobj = StringIO()
            parser = csv.writer(fileobj, dialect=dialect)
            parser.writerow(["Updated", "Type", "Module", "Source", "F/P", "Data"])
            for row in data:
                if row[10] == "ROOT":
                    continue
                datafield = str(row[1]).replace("<SFURL>", "").replace("</SFURL>", "")
                parser.writerow([row[0], str(row[10]), str(row[3]), str(row[2]), row[11], datafield])
            cherrypy.response.headers['Content-Disposition'] = "attachment; filename=SpiderFoot.csv"
            cherrypy.response.headers['Content-Type'] = "application/csv"
            cherrypy.response.headers['Pragma'] = "no-cache"
            return fileobj.getvalue().encode('utf-8')

        return self.error("Invalid export filetype.")

    @cherrypy.expose
    def scanexportjsonmulti(self: 'SpiderFootWebUi', ids: str) -> str:
        """Get scan event result data in JSON format for multiple scans.

        Args:
            ids (str): comma separated list of scan IDs

        Returns:
            str: results in JSON format
        """
        dbh = self._db()
        scaninfo = list()
        scan_name = ""

        for id in ids.split(','):
            scan = dbh.scanInstanceGet(id)

            if scan is None:
                continue

            scan_name = scan[0]

            for row in dbh.scanResultEvent(id):
                lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
                event_data = str(row[1]).replace("<SFURL>", "").replace("</SFURL>", "")
                source_data = str(row[2])
                source_module = str(row[3])
                event_type = row[4]
                false_positive = row[13]

                if event_type == "ROOT":
                    continue

                scaninfo.append({
                    "data": event_data,
                    "event_type": event_type,
                    "module": source_module,
                    "source_data": source_data,
                    "false_positive": false_positive,
                    "last_seen": lastseen,
                    "scan_name": scan_name,
                    "scan_target": scan[1]
                })

        if len(ids.split(',')) > 1 or scan_name == "":
            fname = "SpiderFoot.json"
        else:
            fname = scan_name + "-SpiderFoot.json"

        cherrypy.response.headers['Content-Disposition'] = f"attachment; filename={fname}"
        cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
        cherrypy.response.headers['Pragma'] = "no-cache"
        return json.dumps(scaninfo).encode('utf-8')

    @cherrypy.expose
    def scanviz(self: 'SpiderFootWebUi', id: str, gexf: str = "0") -> str:
        """Export entities from scan results for visualising.

        Args:
            id (str): scan ID
            gexf (str): TBD

        Returns:
            str: GEXF data
        """
        if not id:
            return None

        dbh = self._db()
        data = dbh.scanResultEvent(id, filterFp=True)
        scan = dbh.scanInstanceGet(id)

        if not scan:
            return None

        scan_name = scan[0]

        root = scan[1]

        if gexf == "0":
            return SpiderFootHelpers.buildGraphJson([root], data)

        if not scan_name:
            fname = "SpiderFoot.gexf"
        else:
            fname = scan_name + "SpiderFoot.gexf"

        cherrypy.response.headers['Content-Disposition'] = f"attachment; filename={fname}"
        cherrypy.response.headers['Content-Type'] = "application/gexf"
        cherrypy.response.headers['Pragma'] = "no-cache"
        return SpiderFootHelpers.buildGraphGexf([root], "SpiderFoot Export", data)

    @cherrypy.expose
    def scanvizmulti(self: 'SpiderFootWebUi', ids: str, gexf: str = "1") -> str:
        """Export entities results from multiple scans in GEXF format.

        Args:
            ids (str): scan IDs
            gexf (str): TBD

        Returns:
            str: GEXF data
        """
        dbh = self._db()
        data = list()
        roots = list()
        scan_name = ""

        if not ids:
            return None

        for id in ids.split(','):
            scan = dbh.scanInstanceGet(id)
            if not scan:
                continue
            data = data + dbh.scanResultEvent(id, filterFp=True)
            roots.append(scan[1])
            scan_name = scan[0]

        if not data:
            return None

        if gexf == "0":
            # Not implemented yet
            return None

        if len(ids.split(',')) > 1 or scan_name == "":
            fname = "SpiderFoot.gexf"
        else:
            fname = scan_name + "-SpiderFoot.gexf"

        cherrypy.response.headers['Content-Disposition'] = f"attachment; filename={fname}"
        cherrypy.response.headers['Content-Type'] = "application/gexf"
        cherrypy.response.headers['Pragma'] = "no-cache"
        return SpiderFootHelpers.buildGraphGexf(roots, "SpiderFoot Export", data)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scanopts(self: 'SpiderFootWebUi', id: str) -> dict:
        """Return configuration used for the specified scan as JSON.

        Args:
            id: scan ID

        Returns:
            dict: scan options for the specified scan
        """
        dbh = self._db()
        ret = dict()

        meta = dbh.scanInstanceGet(id)
        if not meta:
            return ret

        if meta[3] != 0:
            started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(meta[3]))
        else:
            started = "Not yet"

        if meta[4] != 0:
            finished = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(meta[4]))
        else:
            finished = "Not yet"

        ret['meta'] = [meta[0], meta[1], meta[2], started, finished, meta[5]]
        ret['config'] = dbh.scanConfigGet(id)
        ret['configdesc'] = dict()
        for key in list(ret['config'].keys()):
            if ':' not in key:
                globaloptdescs = self.config['__globaloptdescs__']
                if globaloptdescs:
                    ret['configdesc'][key] = globaloptdescs.get(key, f"{key} (legacy)")
            else:
                [modName, modOpt] = key.split(':')
                if modName not in list(self.config['__modules__'].keys()):
                    continue

                if modOpt not in list(self.config['__modules__'][modName]['optdescs'].keys()):
                    continue

                ret['configdesc'][key] = self.config['__modules__'][modName]['optdescs'][modOpt]

        return ret

    @cherrypy.expose
    def rerunscan(self: 'SpiderFootWebUi', id: str, csrf_token: str = None) -> None:
        """Rerun a scan.

        Args:
            id (str): scan ID

        Returns:
            None

        Raises:
            HTTPRedirect: redirect to info page for new scan
        """
        # Snapshot the current configuration to be used by the scan
        cfg = deepcopy(self.config)
        modlist = list()
        dbh = self._db(cfg)
        info = dbh.scanInstanceGet(id)

        if not info:
            return self.error("Invalid scan ID.")

        scanname = info[0]
        scantarget = info[1]

        scanconfig = dbh.scanConfigGet(id)
        if not scanconfig:
            return self.error(f"Error loading config from scan: {id}")

        modlist = scanconfig['_modulesenabled'].split(',')
        if "sfp__stor_stdout" in modlist:
            modlist.remove("sfp__stor_stdout")

        targetType = SpiderFootHelpers.targetTypeFromString(scantarget)
        if not targetType:
            # It must then be a name, as a re-run scan should always have a clean
            # target. Put quotes around the target value and try to determine the
            # target type again.
            targetType = SpiderFootHelpers.targetTypeFromString(f'"{scantarget}"')

        if targetType not in ["HUMAN_NAME", "BITCOIN_ADDRESS"]:
            scantarget = scantarget.lower()

        # Start running a new scan
        scanId = SpiderFootHelpers.genScanInstanceId()
        bind_scan(cfg, scanId)
        try:
            p = mp.Process(target=startSpiderFootScanner, args=(self.loggingQueue, scanname, scanId, scantarget, targetType, modlist, cfg))
            p.daemon = True
            p.start()
        except Exception as e:
            self.log.error(f"[-] Scan [{scanId}] failed: {e}")
            return self.error(f"[-] Scan [{scanId}] failed: {e}")

        # Wait until the scan has initialized
        while dbh.scanInstanceGet(scanId) is None:
            self.log.info("Waiting for the scan to initialize...")
            time.sleep(1)

        raise cherrypy.HTTPRedirect(f"{self.docroot}/scaninfo?id={scanId}", status=302)

    @cherrypy.expose
    def rerunscanmulti(self: 'SpiderFootWebUi', ids: str, csrf_token: str = None) -> str:
        """Rerun scans.

        Args:
            ids (str): comma separated list of scan IDs

        Returns:
            str: Scan list page HTML
        """
        # Snapshot the current configuration to be used by the scan
        cfg = deepcopy(self.config)
        modlist = list()
        dbh = self._db(cfg)

        for id in ids.split(","):
            info = dbh.scanInstanceGet(id)
            if not info:
                return self.error("Invalid scan ID.")

            scanconfig = dbh.scanConfigGet(id)
            scanname = info[0]
            scantarget = info[1]
            targetType = None

            if len(scanconfig) == 0:
                return self.error("Something went wrong internally.")

            modlist = scanconfig['_modulesenabled'].split(',')
            if "sfp__stor_stdout" in modlist:
                modlist.remove("sfp__stor_stdout")

            targetType = SpiderFootHelpers.targetTypeFromString(scantarget)
            if targetType is None:
                # Should never be triggered for a re-run scan..
                return self.error("Invalid target type. Could not recognize it as a target SpiderFoot supports.")

            # Start running a new scan
            scanId = SpiderFootHelpers.genScanInstanceId()
            bind_scan(cfg, scanId)
            try:
                p = mp.Process(target=startSpiderFootScanner, args=(self.loggingQueue, scanname, scanId, scantarget, targetType, modlist, cfg))
                p.daemon = True
                p.start()
            except Exception as e:
                self.log.error(f"[-] Scan [{scanId}] failed: {e}")
                return self.error(f"[-] Scan [{scanId}] failed: {e}")

            # Wait until the scan has initialized
            while dbh.scanInstanceGet(scanId) is None:
                self.log.info("Waiting for the scan to initialize...")
                time.sleep(1)

        templ = Template(filename='spiderfoot/templates/scanlist.tmpl', lookup=self.lookup)
        return templ.render(
            rerunscans=True,
            docroot=self.docroot,
            pageid="SCANLIST",
            version=__version__,
            scan_rows=self._scan_rows_for_template(),
            scan_stats=self._scan_stats_for_template()
        )

    @cherrypy.expose
    def newscan(self: 'SpiderFootWebUi') -> str:
        """Configure a new scan.

        Returns:
            str: New scan page HTML
        """
        dbh = self._db()
        types = dbh.eventTypes()
        templ = Template(filename='spiderfoot/templates/newscan.tmpl', lookup=self.lookup)
        return templ.render(pageid='NEWSCAN', types=types, docroot=self.docroot,
                            modules=self.config['__modules__'], scanname="",
                            selectedmods="", scantarget="", version=__version__)

    @cherrypy.expose
    def clonescan(self: 'SpiderFootWebUi', id: str) -> str:
        """Clone an existing scan (pre-selected options in the newscan page).

        Args:
            id (str): scan ID to clone

        Returns:
            str: New scan page HTML pre-populated with options from cloned scan.
        """
        dbh = self._db()
        types = dbh.eventTypes()
        info = dbh.scanInstanceGet(id)

        if not info:
            return self.error("Invalid scan ID.")

        scanconfig = dbh.scanConfigGet(id)
        scanname = info[0]
        scantarget = info[1]
        targetType = None

        if scanname == "" or scantarget == "" or len(scanconfig) == 0:
            return self.error("Something went wrong internally.")

        targetType = SpiderFootHelpers.targetTypeFromString(scantarget)
        if targetType is None:
            # It must be a name, so wrap quotes around it
            scantarget = "&quot;" + scantarget + "&quot;"

        modlist = scanconfig['_modulesenabled'].split(',')

        templ = Template(filename='spiderfoot/templates/newscan.tmpl', lookup=self.lookup)
        return templ.render(pageid='NEWSCAN', types=types, docroot=self.docroot,
                            modules=self.config['__modules__'], selectedmods=modlist,
                            scanname=str(scanname),
                            scantarget=str(scantarget), version=__version__)

    @cherrypy.expose
    def index(self: 'SpiderFootWebUi') -> str:
        """Show scan list page.

        Returns:
            str: Scan list page HTML
        """
        templ = Template(filename='spiderfoot/templates/scanlist.tmpl', lookup=self.lookup)
        return templ.render(pageid='SCANLIST', docroot=self.docroot, version=__version__,
                            newscan=None, rerunscans=None, stoppedscan=None, errors=[],
                            scan_rows=self._scan_rows_for_template(),
                            scan_stats=self._scan_stats_for_template())

    @cherrypy.expose
    def scaninfo(self: 'SpiderFootWebUi', id: str) -> str:
        """Information about a selected scan.

        Args:
            id (str): scan id

        Returns:
            str: scan info page HTML
        """
        dbh = self._db()
        res = dbh.scanInstanceGet(id)
        if res is None:
            return self.error("Scan ID not found.")

        templ = Template(filename='spiderfoot/templates/scaninfo.tmpl', lookup=self.lookup, input_encoding='utf-8')
        return templ.render(id=id, name=html.escape(res[0]), status=res[5], docroot=self.docroot, version=__version__,
                            pageid="SCANLIST", summary=self._scan_summary_for_template(id))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scanresults(self: 'SpiderFootWebUi', id: str) -> dict:
        """Read a source-labelled view of the events already stored by SpiderFoot."""
        dbh = self._db()
        try:
            scan = dbh.scanInstanceGet(id)
            if scan is None:
                raise cherrypy.HTTPError(404, "Resource not found")
            events = dbh.scanResultEvent(id, 'ALL')
        except cherrypy.HTTPError:
            raise
        except (OSError, sqlite3.Error):
            cherrypy.response.status = 503
            return {"status": "unavailable", "message": "数据源不可用",
                    "data_source": "SpiderFoot 已保存扫描结果", "results": []}
        finally:
            dbh.close()

        target_type = SpiderFootHelpers.targetTypeFromString(scan[1])
        input_type = {"EMAILADDR": "邮箱", "USERNAME": "用户名", "DOMAIN": "域名",
                      "INTERNET_NAME": "域名", "IP_ADDRESS": "IP 地址"}.get(target_type, target_type or "未识别")
        results = []
        for row in events:
            if row[4] == 'ROOT':
                continue
            original_url = None
            for candidate in (row[1], row[2]):
                try:
                    parts = urlsplit(str(candidate))
                    if parts.scheme.lower() in ("http", "https") and parts.netloc and not parts.username:
                        original_url = str(candidate)
                        break
                except ValueError:
                    pass
            marked_fp = bool(row[13] or row[14])
            results.append({
                "input_type": input_type,
                "event_type": str(row[4]),
                "data_value": str(row[1]),
                "data_source": "SpiderFoot / " + str(row[3]),
                "source_module": str(row[3]),
                "event_hash": str(row[8]),
                "risk": str(row[7] or "INFO"),
                "title": str(row[10] or row[4]),
                "original_url": original_url,
                "query_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0])),
                "time_note": "SpiderFoot 扫描记录时间，非实时查询",
                "status": "已标记误报" if marked_fp else "待人工核验",
                "false_positive": marked_fp,
                "confidence_note": f"SpiderFoot 原始置信度 {row[5]}/100；未独立核验",
                "false_positive_hint": "已由用户标记误报；请核对原始来源。" if marked_fp else "自动扫描可能产生误报；请核对原始来源。",
            })
        complete = scan[5] == "FINISHED"
        return {
            "status": "complete" if complete else "partial",
            "scan_status": scan[5],
            "data_source": "SpiderFoot 已保存扫描结果",
            "coverage": "仅包含本次 SpiderFoot 扫描启用模块已保存的结果；覆盖范围有限。",
            "message": ("当前数据源未发现匹配，不代表不存在相关信息。" if not results and complete
                        else "部分完成：扫描未正常结束或仍在进行，结果可能不完整。" if not complete else ""),
            "results": results,
        }

    @cherrypy.expose
    def opts(self: 'SpiderFootWebUi', updated: str = None) -> str:
        """Show module and global settings page.

        Args:
            updated (str): scan options were updated successfully

        Returns:
            str: scan options page HTML
        """
        templ = Template(filename='spiderfoot/templates/opts.tmpl', lookup=self.lookup)
        self.token = random.SystemRandom().randint(0, 99999999)
        return templ.render(opts=self.config, pageid='SETTINGS', token=self.token, version=__version__,
                            updated=updated, docroot=self.docroot)

    @cherrypy.expose
    def optsexport(self: 'SpiderFootWebUi', pattern: str = None) -> str:
        """Export configuration.

        Args:
            pattern (str): TBD

        Returns:
            str: Configuration settings
        """
        sf = SpiderFoot(self.config)
        conf = sf.configSerialize(self.config)
        content = ""

        for opt in sorted(conf):
            if ":_" in opt or opt.startswith("_"):
                continue

            if pattern:
                if pattern in opt:
                    content += f"{opt}={conf[opt]}\n"
            else:
                content += f"{opt}={conf[opt]}\n"

        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="SpiderFoot.cfg"'
        cherrypy.response.headers['Content-Type'] = "text/plain"
        return content

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def optsraw(self: 'SpiderFootWebUi') -> str:
        """Return global and module settings as json.

        Returns:
            str: settings as JSON
        """
        ret = dict()
        self.token = random.SystemRandom().randint(0, 99999999)
        for opt in self.config:
            if not opt.startswith('__'):
                ret["global." + opt] = self.config[opt]
                continue

            if opt == '__modules__':
                for mod in sorted(self.config['__modules__'].keys()):
                    for mo in sorted(self.config['__modules__'][mod]['opts'].keys()):
                        if mo.startswith("_"):
                            continue
                        ret["module." + mod + "." + mo] = self.config['__modules__'][mod]['opts'][mo]

        return ['SUCCESS', {'token': self.token, 'data': ret}]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scandelete(self: 'SpiderFootWebUi', id: str, csrf_token: str = None) -> str:
        """Delete scan(s).

        Args:
            id (str): comma separated list of scan IDs

        Returns:
            str: JSON response
        """
        if not id:
            return self.jsonify_error('404', "No scan specified")

        dbh = self._db()
        ids = id.split(',')

        for scan_id in ids:
            res = dbh.scanInstanceGet(scan_id)
            if not res:
                return self.jsonify_error('404', f"Scan {scan_id} does not exist")

            if res[5] in ["RUNNING", "STARTING", "STARTED"]:
                return self.jsonify_error('400', f"Scan {scan_id} is {res[5]}. You cannot delete running scans.")

        for scan_id in ids:
            dbh.scanInstanceDelete(scan_id)

        return ""

    @cherrypy.expose
    def savesettings(self: 'SpiderFootWebUi', allopts: str, token: str, configFile: 'cherrypy._cpreqbody.Part' = None, csrf_token: str = None) -> None:
        """Save settings, also used to completely reset them to default.

        Args:
            allopts: TBD
            token (str): CSRF token
            configFile (cherrypy._cpreqbody.Part): TBD

        Returns:
            None

        Raises:
            HTTPRedirect: redirect to scan settings
        """
        if str(token) != str(self.token):
            return self.error(f"Invalid token ({token})")

        # configFile seems to get set even if a file isn't uploaded
        if configFile and configFile.file:
            try:
                contents = configFile.file.read()

                if isinstance(contents, bytes):
                    contents = contents.decode('utf-8')

                tmp = dict()
                for line in contents.split("\n"):
                    if "=" not in line:
                        continue

                    opt_array = line.strip().split("=")
                    if len(opt_array) == 1:
                        opt_array[1] = ""

                    tmp[opt_array[0]] = '='.join(opt_array[1:])

                allopts = json.dumps(tmp).encode('utf-8')
            except Exception as e:
                return self.error(f"Failed to parse input file. Was it generated from SpiderFoot? ({e})")

        # Reset config to default
        if allopts == "RESET":
            if self.reset_settings():
                raise cherrypy.HTTPRedirect(f"{self.docroot}/opts?updated=1")
            return self.error("Failed to reset settings")

        # Save settings
        try:
            dbh = self._db()
            useropts = json.loads(allopts)
            cleanopts = dict()
            for opt in list(useropts.keys()):
                cleanopts[opt] = self.cleanUserInput([useropts[opt]])[0]

            currentopts = deepcopy(self.config)

            # Make a new config where the user options override
            # the current system config.
            sf = SpiderFoot(self.config)
            self.config = sf.configUnserialize(cleanopts, currentopts)
            dbh.configSet(sf.configSerialize(self.config))
        except Exception as e:
            return self.error(f"Processing one or more of your inputs failed: {e}")

        raise cherrypy.HTTPRedirect(f"{self.docroot}/opts?updated=1")

    @cherrypy.expose
    def savesettingsraw(self: 'SpiderFootWebUi', allopts: str, token: str, csrf_token: str = None) -> str:
        """Save settings, also used to completely reset them to default.

        Args:
            allopts: TBD
            token (str): CSRF token

        Returns:
            str: save success as JSON
        """
        cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"

        if str(token) != str(self.token):
            return json.dumps(["ERROR", f"Invalid token ({token})."]).encode('utf-8')

        # Reset config to default
        if allopts == "RESET":
            if self.reset_settings():
                return json.dumps(["SUCCESS", ""]).encode('utf-8')
            return json.dumps(["ERROR", "Failed to reset settings"]).encode('utf-8')

        # Save settings
        try:
            dbh = self._db()
            useropts = json.loads(allopts)
            cleanopts = dict()
            for opt in list(useropts.keys()):
                cleanopts[opt] = self.cleanUserInput([useropts[opt]])[0]

            currentopts = deepcopy(self.config)

            # Make a new config where the user options override
            # the current system config.
            sf = SpiderFoot(self.config)
            self.config = sf.configUnserialize(cleanopts, currentopts)
            dbh.configSet(sf.configSerialize(self.config))
        except Exception as e:
            return json.dumps(["ERROR", f"Processing one or more of your inputs failed: {e}"]).encode('utf-8')

        return json.dumps(["SUCCESS", ""]).encode('utf-8')

    def reset_settings(self: 'SpiderFootWebUi') -> bool:
        """Reset settings to default.

        Returns:
            bool: success
        """
        try:
            dbh = self._db()
            dbh.configClear()  # Clear it in the DB
            self.config = deepcopy(self.defaultConfig)  # Clear in memory
        except Exception:
            return False

        return True

    @cherrypy.expose
    def resultsetfp(self: 'SpiderFootWebUi', id: str, resultids: str, fp: str, csrf_token: str = None) -> str:
        """Set a bunch of results (hashes) as false positive.

        Args:
            id (str): scan ID
            resultids (str): comma separated list of result IDs
            fp (str): 0 or 1

        Returns:
            str: set false positive status as JSON
        """
        cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"

        if fp not in ["0", "1"]:
            raise cherrypy.HTTPError(400, "Invalid false-positive flag")

        try:
            ids = json.loads(resultids)
        except (TypeError, ValueError):
            raise cherrypy.HTTPError(400, "Invalid result IDs")
        if (not isinstance(ids, list) or not ids or len(ids) > 100
                or any(not isinstance(value, str) or not value or len(value) > 128 for value in ids)):
            raise cherrypy.HTTPError(400, "Invalid result IDs")

        dbh = self._db()
        try:
            return self._resultsetfp_owned(dbh, id, ids, fp)
        finally:
            dbh.close()

    def _resultsetfp_owned(self, dbh, id, ids, fp):

        # Validate requested events before following any parent/child edges.
        for result_id in ids:
            event = dbh.conn.execute(
                "SELECT type FROM tbl_scan_results WHERE scan_instance_id=? AND hash=?",
                (id, result_id)).fetchone()
            if event is None or event[0] == 'ROOT':
                raise cherrypy.HTTPError(404, "Result not found")

        # Cannot set FPs if a scan is not completed
        status = dbh.scanInstanceGet(id)
        if not status:
            raise cherrypy.HTTPError(404, "Resource not found")

        if status[5] not in ["ABORTED", "FINISHED", "ERROR-FAILED"]:
            return json.dumps([
                "WARNING",
                "Scan must be in a finished state when setting False Positives."
            ]).encode('utf-8')

        # Make sure the user doesn't set something as non-FP when the
        # parent is set as an FP.
        if fp == "0":
            data = dbh.scanElementSourcesDirect(id, ids)
            for row in data:
                if str(row[14]) == "1":
                    return json.dumps([
                        "WARNING",
                        f"Cannot unset element {id} as False Positive if a parent element is still False Positive."
                    ]).encode('utf-8')

        # Set all the children as FPs too.. it's only logical afterall, right?
        childs = dbh.scanElementChildrenAll(id, ids)
        allIds = list(dict.fromkeys(ids + childs))

        updated = dbh.scanResultsUpdateFP(id, allIds, int(fp))
        if updated == len(allIds):
            return json.dumps(["SUCCESS", {"updated": updated}]).encode('utf-8')

        raise cherrypy.HTTPError(404, "Result not found")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def eventtypes(self: 'SpiderFootWebUi') -> list:
        """List all event types.

        Returns:
            list: list of event types
        """
        cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"

        dbh = self._db()
        types = dbh.eventTypes()
        ret = list()

        for r in types:
            ret.append([r[1], r[0]])

        return sorted(ret, key=itemgetter(0))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def modules(self: 'SpiderFootWebUi') -> list:
        """List all modules.

        Returns:
            list: list of modules
        """
        cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"

        ret = list()

        modinfo = list(self.config['__modules__'].keys())
        if not modinfo:
            return ret

        modinfo.sort()

        for m in modinfo:
            if "__" in m:
                continue
            ret.append({'name': m, 'descr': self.config['__modules__'][m]['descr']})

        return ret

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def correlationrules(self: 'SpiderFootWebUi') -> list:
        """List all correlation rules.

        Returns:
            list: list of correlation rules
        """
        cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"

        ret = list()

        rules = self.config['__correlationrules__']
        if not rules:
            return ret

        for r in rules:
            ret.append({
                'id': r['id'],
                'name': r['meta']['name'],
                'descr': r['meta']['description'],
                'risk': r['meta']['risk'],
            })

        return ret

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def ping(self: 'SpiderFootWebUi') -> list:
        """For the CLI to test connectivity to this server.

        Returns:
            list: SpiderFoot version as JSON
        """
        return ["SUCCESS", __version__]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def riskalerts(self: 'SpiderFootWebUi') -> list:
        """Get risk alerts from all finished scans.

        Returns:
            list: alerts grouped by scan, including HIGH risk correlations
                  and HIGH risk event types
        """
        alerts = []
        dbh = None
        # Get all finished scans. A failed source is not an empty alert list.
        try:
            dbh = self._db()
            scans = dbh.scanInstanceList()
        except Exception:
            if dbh:
                dbh.close()
            raise cherrypy.HTTPError(503, "数据不可用") from None

        finished_statuses = ['FINISHED', 'ABORTED', 'ERROR-FAILED']

        for scan in scans:
            scan_id = scan[0]
            scan_name = scan[1]
            scan_target = scan[2]
            scan_status = scan[6]

            # 嵌套函数：脱敏显示
            def _mask(data, etype):
                if not data:
                    return '(未知)'
                if etype == 'EMAILADDR' and '@' in data:
                    p = data.split('@')
                    return p[0][:2] + '***@' + p[1]
                if etype == 'PHONE_NUMBER' and len(data) >= 7:
                    return data[:3] + '****' + data[-4:]
                if etype == 'NAME_PERSON' and len(data) >= 2:
                    return data[0] + '**'
                if etype in ('IP_ADDRESS', 'IPV6_ADDRESS'):
                    parts = data.split('.')
                    if len(parts) == 4:
                        return parts[0] + '.' + parts[1] + '.x.x'
                    return data[:8] + '...'
                if len(data) > 15:
                    return data[:8] + '...'
                return data

            # Only process finished scans
            if scan_status not in finished_statuses:
                continue

            # Get HIGH risk correlations
            try:
                correlations = dbh.scanCorrelationList(scan_id)
                for corr in correlations:
                    rule_risk = corr[3]  # HIGH, MEDIUM, LOW, INFO
                    if rule_risk == 'HIGH':
                        alerts.append({
                            'type': 'correlation',
                            'alertId': f'corr_{corr[0]}',
                            'scanId': scan_id,
                            'scanName': scan_name,
                            'scanTarget': self._mask_scan_target(scan_target),
                            'risk': 'HIGH',
                            'title': corr[1],          # correlation title
                            'ruleName': corr[4],       # rule name
                            'ruleDescr': corr[5],      # rule description
                            'eventCount': corr[7],     # number of events
                            'link': f'/scaninfo?id={scan_id}',
                            'timestamp': ''
                        })
            except Exception:
                dbh.close()
                raise cherrypy.HTTPError(503, "数据不可用") from None

            # Get HIGH risk event types (sensitive data found)
            try:
                summary = dbh.scanResultSummary(scan_id, by='type')
                # Risk threshold: 50+ indicates significant risk
                HIGH_RISK_TYPES = {
                    'EMAILADDR': '邮箱地址',
                    'PHONE_NUMBER': '手机号码',
                    'NAME_PERSON': '真实姓名',
                    'USERNAME': '用户名/账号',
                    'IP_ADDRESS': 'IP 地址',
                    'IPV6_ADDRESS': 'IPv6 地址',
                    'MAC_ADDRESS': 'MAC 地址',
                    'PHYSICAL_COORD': '物理位置',
                    'DOMAIN': '域名',
                    'INTERNET_NAME': '网站/主机名',
                    'NETBLOCK_OWNER': '网段所有者',
                    'PROVIDER': '服务提供商',
                    'CREDIT_CARD': '信用卡号',
                    'IBAN_NUMBER': '银行账号',
                    'BtcAddress': '比特币地址',
                    'DARKNET_MENTION': '暗网提及',
                    'LeakCheck_MAYBE_LEAKED': '泄露检测风险',
                    'HIBP_BREACH': '数据泄露(HIBP)',
                    'HIBP_PASSPALETTE': '密码泄露(HIBP)',
                    'SOCIAL_MEDIA': '社交媒体账号',
                    'VPN_NODE': 'VPN 节点',
                    'VPN_CONNECTION': 'VPN 连接',
                    'TOR_NODE': 'Tor 节点',
                    'PROXY_NODE': '代理节点',
                    'RAW_RIR_DATA': 'WHOIS/RIR 数据',
                    'PEOPLE_SEARCH_SITE': '人物搜索网站',
                    'GEO_LOCATION': '地理定位',
                    'PGP_KEY': 'PGP 公钥',
                    'CRYPTOCURRENCY_ADDRESS': '加密货币地址',
                }
                for row in summary:
                    event_type = row[0]
                    event_data = row[1]
                    event_count = row[3]
                    event_risk = row[4]  # risk score 0-100

                    if event_type in HIGH_RISK_TYPES and event_risk >= 50:
                        # Mask the actual data for privacy
                        masked_data = _mask(event_data, event_type)
                        alerts.append({
                            'type': 'event',
                            'alertId': f'evt_{scan_id}_{event_type}',
                            'scanId': scan_id,
                            'scanName': scan_name,
                            'scanTarget': self._mask_scan_target(scan_target),
                            'risk': 'HIGH' if event_risk >= 75 else 'MEDIUM',
                            'title': f'发现敏感数据: {HIGH_RISK_TYPES.get(event_type, event_type)}',
                            'detail': f'{masked_data}，出现 {event_count} 次',
                            'eventType': event_type,
                            'eventCount': event_count,
                            'link': f'/scaninfo?id={scan_id}',
                            'timestamp': ''
                        })
            except Exception:
                dbh.close()
                raise cherrypy.HTTPError(503, "数据不可用") from None

        dbh.close()
        state = self._load_risk_action_state()
        for alert in alerts:
            alert_id = alert.get('alertId')
            alert_state = state.get(alert_id, {})
            alert['actionStatus'] = alert_state.get('status', 'todo')
            alert['actionNote'] = alert_state.get('note', '')
            alert['actionMethod'] = alert_state.get('method', '')
            alert['actionUpdatedAt'] = alert_state.get('updatedAt', '')
            alert['playbook'] = self._risk_action_playbook(alert)

        return alerts

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def riskactionupdate(self: 'SpiderFootWebUi', alertId: str = None, status: str = None, note: str = "", csrf_token: str = None) -> dict:
        """Update handling status for one risk alert."""
        if not alertId:
            return self.jsonify_error('400', "Missing alertId")
        if alertId not in {alert.get('alertId') for alert in self.riskalerts()}:
            return self.jsonify_error('404', "Risk alert not found")

        allowed = {'todo', 'in_progress', 'resolved', 'retest'}
        if status not in allowed:
            return self.jsonify_error('400', "Invalid status")

        state = self._load_risk_action_state()
        state[alertId] = {
            'status': status,
            'note': (note or '').strip()[:500],
            'method': state.get(alertId, {}).get('method', ''),
            'updatedAt': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_risk_action_state(state)
        return {'status': 'ok', 'alertId': alertId, 'actionStatus': status}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def riskactionautofix(self: 'SpiderFootWebUi', alertId: str = None, scope: str = "single", csrf_token: str = None) -> dict:
        """Auto-handle one or more risk alerts and sync status/method."""
        try:
            alerts = self.riskalerts()
            if not isinstance(alerts, list):
                return self.jsonify_error('500', "Risk alert list unavailable")

            targets = []
            if scope == "high":
                targets = [a for a in alerts if a.get('risk') == 'HIGH']
            elif scope == "all":
                targets = alerts
            else:
                if not alertId:
                    return self.jsonify_error('400', "Missing alertId")
                targets = [a for a in alerts if a.get('alertId') == alertId]

            if not targets:
                return self.jsonify_error('404', "No matching alerts")

            dbh = self._db()
            state = self._load_risk_action_state()
            compare_report = self._load_risk_compare_report()
            updated_ids = []
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            scan_baseline = {}
            scan_rerun = {}
            for a in alerts:
                sid = a.get('scanId')
                if not sid:
                    continue
                if sid not in scan_baseline:
                    scan_baseline[sid] = {'HIGH': 0, 'MEDIUM': 0}
                if a.get('risk') == 'HIGH':
                    scan_baseline[sid]['HIGH'] += 1
                elif a.get('risk') == 'MEDIUM':
                    scan_baseline[sid]['MEDIUM'] += 1

            for alert in targets:
                aid = alert.get('alertId')
                if not aid:
                    continue
                sid = alert.get('scanId')
                masked_count = 0
                if alert.get('type') == 'event' and alert.get('eventType'):
                    masked_count = self._auto_fix_mask_writeback(dbh, sid, alert.get('eventType'))
                hidden_count = self._auto_fix_hide_high_risk(dbh, alert)

                rerun_id = ""
                if sid:
                    if sid not in scan_rerun:
                        scan_rerun[sid] = self._start_rerun_scan(sid)
                    rerun_id = scan_rerun[sid]

                method = self._auto_fix_method(alert)
                if masked_count > 0:
                    method += f" 已执行脱敏写回 {masked_count} 条。"
                if hidden_count > 0:
                    method += f" 已默认隐藏高风险结果 {hidden_count} 条。"
                if rerun_id:
                    method += f" 已触发复检扫描 {rerun_id}，等待完成后自动比对。"

                state[aid] = {
                    'status': 'resolved',
                    'note': '系统已执行一键处理，请按计划复检确认。',
                    'method': method,
                    'updatedAt': now
                }
                if sid:
                    compare_report[aid] = {
                        'scanId': sid,
                        'baseline': scan_baseline.get(sid, {'HIGH': 0, 'MEDIUM': 0}),
                        'rerunScanId': rerun_id,
                        'after': {'HIGH': None, 'MEDIUM': None},
                        'status': 'PENDING_RESCAN',
                        'updatedAt': now
                    }
                updated_ids.append(aid)

            self._save_risk_action_state(state)
            self._save_risk_compare_report(compare_report)
            return {
                'status': 'ok',
                'updatedCount': len(updated_ids),
                'updatedAlertIds': updated_ids,
                'actionStatus': 'resolved',
                'rerunScanIds': [v for v in scan_rerun.values() if v]
            }
        except Exception:
            self.log.error("Auto-fix endpoint failed.")
            return self.jsonify_error('500', "Auto-fix failed.")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def riskactionreport(self: 'SpiderFootWebUi') -> list:
        """Return auto-fix compare reports with before/after risk deltas."""
        report = self._load_risk_compare_report()
        if not report:
            return []

        dbh = self._db()
        changed = False
        output = []

        for alert_id, item in report.items():
            scan_id = item.get('scanId')
            rerun_id = item.get('rerunScanId')
            baseline = item.get('baseline', {'HIGH': 0, 'MEDIUM': 0})
            after = item.get('after', {'HIGH': None, 'MEDIUM': None})
            status = item.get('status', 'PENDING_RESCAN')

            scan_meta = dbh.scanInstanceGet(scan_id) if scan_id else None
            rerun_meta = dbh.scanInstanceGet(rerun_id) if rerun_id else None
            rerun_status = rerun_meta[5] if rerun_meta else 'NOT_FOUND'

            if rerun_meta and rerun_status in ['FINISHED', 'ABORTED', 'ERROR-FAILED'] and (after.get('HIGH') is None or after.get('MEDIUM') is None):
                new_counts = self._scan_risk_counts(dbh, rerun_id)
                after = {'HIGH': new_counts['HIGH'], 'MEDIUM': new_counts['MEDIUM']}
                item['after'] = after
                item['status'] = 'DONE'
                item['updatedAt'] = time.strftime("%Y-%m-%d %H:%M:%S")
                status = 'DONE'
                changed = True

            output.append({
                'alertId': alert_id,
                'scanId': scan_id,
                'scanName': scan_meta[0] if scan_meta else scan_id,
                'scanTarget': self._mask_scan_target(scan_meta[1]) if scan_meta else '',
                'rerunScanId': rerun_id,
                'rerunStatus': rerun_status,
                'baseline': baseline,
                'after': after,
                'delta': {
                    'HIGH': None if after.get('HIGH') is None else after.get('HIGH') - baseline.get('HIGH', 0),
                    'MEDIUM': None if after.get('MEDIUM') is None else after.get('MEDIUM') - baseline.get('MEDIUM', 0),
                },
                'status': status,
                'updatedAt': item.get('updatedAt', '')
            })

        if changed:
            self._save_risk_compare_report(report)

        output.sort(key=lambda x: x.get('updatedAt', ''), reverse=True)
        return output

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def query(self: 'SpiderFootWebUi', query: str) -> str:
        """For the CLI to run queries against the database.

        Args:
            query (str): SQL query

        Returns:
            str: query results as JSON
        """
        dbh = self._db()

        if not query:
            return self.jsonify_error('400', "Invalid query.")

        if not query.lower().startswith("select"):
            return self.jsonify_error('400', "Non-SELECTs are unpredictable and not recommended.")

        try:
            ret = dbh.dbh.execute(query)
            data = ret.fetchall()
            columnNames = [c[0] for c in dbh.dbh.description]
            return [dict(zip(columnNames, row)) for row in data]
        except Exception as e:
            return self.jsonify_error('500', str(e))

    @cherrypy.expose
    def startscan(self: 'SpiderFootWebUi', scanname: str = None, scantarget: str = None, modulelist: str = None, typelist: str = None, usecase: str = None, csrf_token: str = None) -> str:
        """Initiate a scan.

        Args:
            scanname (str): scan name
            scantarget (str): scan target
            modulelist (str): comma separated list of modules to use
            typelist (str): selected modules based on produced event data types
            usecase (str): selected module group (passive, investigate, footprint, all)

        Returns:
            str: start scan status as JSON

        Raises:
            HTTPRedirect: redirect to new scan info page
        """
        # 直接打开 /startscan 且无查询参数时，CherryPy 会因缺少必选参数返回 404。
        # 参数全部缺省则跳转到「新建扫描」页面，避免用户看到「Not Found」。
        accept = cherrypy.request.headers.get('Accept') or ''
        if (
            scanname is None and scantarget is None and modulelist is None
            and typelist is None and usecase is None
            and 'application/json' not in accept
        ):
            raise cherrypy.HTTPRedirect(f"{self.docroot}/newscan")

        scanname = self.cleanUserInput([scanname])[0]
        scantarget = self.cleanUserInput([scantarget])[0]

        if not scanname:
            if cherrypy.request.headers.get('Accept') and 'application/json' in cherrypy.request.headers.get('Accept'):
                cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
                return json.dumps(["ERROR", "Incorrect usage: scan name was not specified."]).encode('utf-8')

            return self.error("Invalid request: scan name was not specified.")

        if not scantarget:
            if cherrypy.request.headers.get('Accept') and 'application/json' in cherrypy.request.headers.get('Accept'):
                cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
                return json.dumps(["ERROR", "Incorrect usage: scan target was not specified."]).encode('utf-8')

            return self.error("Invalid request: scan target was not specified.")

        if not typelist and not modulelist and not usecase:
            if cherrypy.request.headers.get('Accept') and 'application/json' in cherrypy.request.headers.get('Accept'):
                cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
                return json.dumps(["ERROR", "Incorrect usage: no modules specified for scan."]).encode('utf-8')

            return self.error("Invalid request: no modules specified for scan.")

        targetType = SpiderFootHelpers.targetTypeFromString(scantarget)
        if targetType is None:
            # 尝试加引号重新识别（可能是姓名或用户名）
            targetType = SpiderFootHelpers.targetTypeFromString(f'"{scantarget}"')
            if targetType:
                scantarget = f'"{scantarget}"'
            else:
                if cherrypy.request.headers.get('Accept') and 'application/json' in cherrypy.request.headers.get('Accept'):
                    cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
                    return json.dumps(["ERROR", "Unrecognised target type."]).encode('utf-8')

                return self.error("Invalid target type. Could not recognize it as a target SpiderFoot supports.")

        if not self._scan_target_is_valid(scantarget, targetType):
            if 'application/json' in accept:
                cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
                cherrypy.response.status = 400
                return json.dumps(["ERROR", "Invalid target format."]).encode('utf-8')
            return self.error("Invalid target format.")

        # Swap the globalscantable for the database handler
        dbh = self._db()

        # Snapshot the current configuration to be used by the scan
        cfg = deepcopy(self.config)
        sf = SpiderFoot(cfg)

        modlist = list()

        # User selected modules
        if modulelist:
            modlist = modulelist.replace('module_', '').split(',')

        # User selected types
        if len(modlist) == 0 and typelist:
            typesx = typelist.replace('type_', '').split(',')

            # 1. Find all modules that produce the requested types
            modlist = sf.modulesProducing(typesx)
            newmods = deepcopy(modlist)
            newmodcpy = deepcopy(newmods)

            # 2. For each type those modules consume, get modules producing
            while len(newmodcpy) > 0:
                for etype in sf.eventsToModules(newmodcpy):
                    xmods = sf.modulesProducing([etype])
                    for mod in xmods:
                        if mod not in modlist:
                            modlist.append(mod)
                            newmods.append(mod)
                newmodcpy = deepcopy(newmods)
                newmods = list()

        # User selected a use case
        if len(modlist) == 0 and usecase:
            for mod in self.config['__modules__']:
                if usecase == 'all' or usecase in self.config['__modules__'][mod]['group']:
                    modlist.append(mod)

        # If we somehow got all the way through to here and still don't have any modules selected
        if not modlist:
            if cherrypy.request.headers.get('Accept') and 'application/json' in cherrypy.request.headers.get('Accept'):
                cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
                return json.dumps(["ERROR", "Incorrect usage: no modules specified for scan."]).encode('utf-8')

            return self.error("Invalid request: no modules specified for scan.")

        # Add our mandatory storage module
        if "sfp__stor_db" not in modlist:
            modlist.append("sfp__stor_db")
        modlist.sort()

        # Delete the stdout module in case it crept in
        if "sfp__stor_stdout" in modlist:
            modlist.remove("sfp__stor_stdout")

        # Start running a new scan
        if targetType in ["HUMAN_NAME", "USERNAME", "BITCOIN_ADDRESS"]:
            scantarget = scantarget.replace("\"", "")
        else:
            scantarget = scantarget.lower()

        # Start running a new scan
        scanId = SpiderFootHelpers.genScanInstanceId()
        bind_scan(cfg, scanId)
        try:
            p = mp.Process(target=startSpiderFootScanner, args=(self.loggingQueue, scanname, scanId, scantarget, targetType, modlist, cfg))
            p.daemon = True
            p.start()
        except Exception as e:
            self.log.error(f"[-] Scan [{scanId}] failed: {e}")
            return self.error(f"[-] Scan [{scanId}] failed: {e}")

        # Wait until the scan has initialized
        # Check the database for the scan status results
        while dbh.scanInstanceGet(scanId) is None:
            self.log.info("Waiting for the scan to initialize...")
            time.sleep(1)

        if cherrypy.request.headers.get('Accept') and 'application/json' in cherrypy.request.headers.get('Accept'):
            cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
            return json.dumps(["SUCCESS", scanId]).encode('utf-8')

        raise cherrypy.HTTPRedirect(f"{self.docroot}/scaninfo?id={scanId}")

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def stopscan(self: 'SpiderFootWebUi', id: str, csrf_token: str = None) -> str:
        """Stop a scan.

        Args:
            id (str): comma separated list of scan IDs

        Returns:
            str: JSON response
        """
        if not id:
            return self.jsonify_error('404', "No scan specified")

        dbh = self._db()
        ids = id.split(',')

        for scan_id in ids:
            res = dbh.scanInstanceGet(scan_id)
            if not res:
                return self.jsonify_error('404', f"Scan {scan_id} does not exist")

            scan_status = res[5]

            if scan_status == "FINISHED":
                return self.jsonify_error('400', f"Scan {scan_id} has already finished.")

            if scan_status == "ABORTED":
                return self.jsonify_error('400', f"Scan {scan_id} has already aborted.")

            if scan_status != "RUNNING" and scan_status != "STARTING":
                return self.jsonify_error('400', f"The running scan is currently in the state '{scan_status}', please try again later or restart SpiderFoot.")

        for scan_id in ids:
            dbh.scanInstanceSet(scan_id, status="ABORT-REQUESTED")

        return ""

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def vacuum(self, csrf_token: str = None):
        dbh = self._db()
        try:
            if dbh.vacuumDB():
                return json.dumps(["SUCCESS", ""]).encode('utf-8')
            return json.dumps(["ERROR", "Vacuuming the database failed"]).encode('utf-8')
        except Exception as e:
            return json.dumps(["ERROR", f"Vacuuming the database failed: {e}"]).encode('utf-8')

    #
    # DATA PROVIDERS
    #

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scanlog(self: 'SpiderFootWebUi', id: str, limit: str = None, rowId: str = None, reverse: str = None) -> list:
        """Scan log data.

        Args:
            id (str): scan ID
            limit (str): TBD
            rowId (str): TBD
            reverse (str): TBD

        Returns:
            list: scan log
        """
        dbh = self._db()
        retdata = []

        try:
            data = dbh.scanLogs(id, limit, rowId, reverse)
        except Exception:
            return retdata

        for row in data:
            generated = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0] / 1000))
            retdata.append([generated, row[1], row[2], html.escape(row[3]), row[4]])

        return retdata

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scanerrors(self: 'SpiderFootWebUi', id: str, limit: str = None) -> list:
        """Scan error data.

        Args:
            id (str): scan ID
            limit (str): limit number of results

        Returns:
            list: scan errors
        """
        dbh = self._db()
        retdata = []

        try:
            data = dbh.scanErrors(id, limit)
        except Exception:
            return retdata

        for row in data:
            generated = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0] / 1000))
            retdata.append([generated, row[1], html.escape(str(row[2]))])

        return retdata

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scanlist(self: 'SpiderFootWebUi', _: str = None) -> list:
        """Produce a list of scans.

        Returns:
            list: scan list
        """
        # If a browser opens this endpoint directly, redirect to scan list page.
        # Frontend AJAX calls still request JSON and will not hit this path.
        accept = (cherrypy.request.headers.get('Accept') or '').lower()
        if 'text/html' in accept and 'application/json' not in accept:
            raise cherrypy.HTTPRedirect(f"{self.docroot}/", status=302)

        dbh = None
        try:
            dbh = self._db()
            data = dbh.scanInstanceList()
        except (OSError, sqlite3.Error):
            if dbh:
                dbh.close()
            raise cherrypy.HTTPError(503, "数据不可用") from None
        retdata = []

        for row in data:
            created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[3]))
            riskmatrix = {
                "HIGH": 0,
                "MEDIUM": 0,
                "LOW": 0,
                "INFO": 0
            }
            try:
                correlations = dbh.scanCorrelationSummary(row[0], by="risk")
            except (OSError, sqlite3.Error):
                dbh.close()
                raise cherrypy.HTTPError(503, "数据不可用") from None
            if correlations:
                for c in correlations:
                    riskmatrix[c[0]] = c[1]

            if row[4] == 0:
                started = "Not yet"
            else:
                started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[4]))

            if row[5] == 0:
                finished = "Not yet"
            else:
                finished = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[5]))

            retdata.append([row[0], row[1], self._mask_scan_target(row[2]), created, started, finished, row[6], row[7], riskmatrix])

        dbh.close()
        return retdata

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scanstatus(self: 'SpiderFootWebUi', id: str) -> list:
        """Show basic information about a scan, including status and number of each event type.

        Args:
            id (str): scan ID

        Returns:
            list: scan status
        """
        dbh = self._db()
        data = dbh.scanInstanceGet(id)

        if not data:
            return []

        created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[2]))
        started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[3]))
        ended = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[4]))
        riskmatrix = {
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0
        }
        correlations = dbh.scanCorrelationSummary(id, by="risk")
        if correlations:
            for c in correlations:
                riskmatrix[c[0]] = c[1]

        return [data[0], data[1], created, started, ended, data[5], riskmatrix]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scansummary(self: 'SpiderFootWebUi', id: str, by: str) -> list:
        """Summary of scan results.

        Args:
            id (str): scan ID
            by (str): filter by type

        Returns:
            list: scan summary
        """
        retdata = []

        dbh = None
        try:
            dbh = self._db()
            scandata = dbh.scanResultSummary(id, by)
            statusdata = dbh.scanInstanceGet(id)
        except Exception:
            raise cherrypy.HTTPError(503, "数据不可用") from None
        finally:
            if dbh:
                dbh.close()

        for row in scandata:
            if row[0] == "ROOT":
                continue
            lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[2]))
            retdata.append([row[0], row[1], lastseen, row[3], row[4], statusdata[5]])

        return retdata

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scancorrelations(self: 'SpiderFootWebUi', id: str) -> list:
        """Correlation results from a scan.

        Args:
            id (str): scan ID

        Returns:
            list: correlation result list
        """
        retdata = []

        dbh = self._db()

        try:
            corrdata = dbh.scanCorrelationList(id)
        except Exception:
            return retdata

        for row in corrdata:
            retdata.append([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]])

        return retdata

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scaneventresults(self: 'SpiderFootWebUi', id: str, eventType: str = None, filterfp: bool = False, correlationId: str = None) -> list:
        """Return all event results for a scan as JSON.

        Args:
            id (str): scan ID
            eventType (str): filter by event type
            filterfp (bool): remove false positives from search results
            correlationId (str): filter by events associated with a correlation

        Returns:
            list: scan results
        """
        retdata = []

        dbh = self._db()

        if not eventType:
            eventType = 'ALL'

        try:
            data = dbh.scanResultEvent(id, eventType, filterFp=filterfp in (True, '1', 'true', 'on'),
                                       correlationId=correlationId)
        except Exception:
            return retdata

        for row in data:
            lastseen = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row[0]))
            retdata.append([
                lastseen,
                html.escape(row[1]),
                html.escape(row[2]),
                row[3],
                row[5],
                row[6],
                row[7],
                row[8],
                row[13],
                row[14],
                row[4]
            ])

        return retdata

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scaneventresultsunique(self: 'SpiderFootWebUi', id: str, eventType: str, filterfp: bool = False) -> list:
        """Return unique event results for a scan as JSON.

        Args:
            id (str): filter search results by scan ID
            eventType (str): filter search results by event type
            filterfp (bool): remove false positives from search results

        Returns:
            list: unique search results
        """
        dbh = self._db()
        retdata = []

        try:
            data = dbh.scanResultEventUnique(id, eventType, filterfp)
        except Exception:
            return retdata

        for row in data:
            escaped = html.escape(row[0])
            retdata.append([escaped, row[1], row[2]])

        return retdata

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def search(self: 'SpiderFootWebUi', id: str = None, eventType: str = None, value: str = None) -> list:
        """Search scans.

        Args:
            id (str): filter search results by scan ID
            eventType (str): filter search results by event type
            value (str): filter search results by event value

        Returns:
            list: search results
        """
        try:
            return self.searchBase(id, eventType, value)
        except Exception:
            return []

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scanhistory(self: 'SpiderFootWebUi', id: str) -> list:
        """Historical data for a scan.

        Args:
            id (str): scan ID

        Returns:
            list: scan history
        """
        if not id:
            return self.jsonify_error('404', "No scan specified")

        dbh = self._db()

        try:
            return dbh.scanResultHistory(id)
        except Exception:
            return []

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def scanelementtypediscovery(self: 'SpiderFootWebUi', id: str, eventType: str) -> dict:
        """Scan element type discovery.

        Args:
            id (str): scan ID
            eventType (str): filter by event type

        Returns:
            dict
        """
        dbh = self._db()
        pc = dict()
        datamap = dict()
        retdata = dict()

        # Get the events we will be tracing back from
        try:
            leafSet = dbh.scanResultEvent(id, eventType)
            [datamap, pc] = dbh.scanElementSourcesAll(id, leafSet)
        except Exception:
            return retdata

        # Delete the ROOT key as it adds no value from a viz perspective
        del pc['ROOT']
        retdata['tree'] = SpiderFootHelpers.dataParentChildToTree(pc)
        retdata['data'] = datamap

        return retdata

    # ========================
    # 泄露检测模块
    # ========================

    @cherrypy.expose
    def leakcheck(self: 'SpiderFootWebUi') -> str:
        """渲染泄露检测页面"""
        unavailable = False
        try:
            db = LeakCheckDB()
            record_count = db.get_record_count()
        except (OSError, sqlite3.Error):
            unavailable = True
            record_count = 0
            cherrypy.response.status = 503
        templ = Template(filename='spiderfoot/templates/leakcheck.tmpl', lookup=self.lookup)
        return templ.render(
            docroot=self.docroot,
            pageid='LEAKCHECK',
            record_count=f"{record_count:,}",
            source_unavailable=unavailable,
            version=__version__
        )

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def leaksearch(self: 'SpiderFootWebUi', q: str = None) -> dict:
        """泄露检测查询接口"""
        if cherrypy.request.method != "POST":
            cherrypy.response.headers["Allow"] = "POST"
            raise cherrypy.HTTPError(405, "This operation requires POST.")
        if not isinstance(q, str) or not q.strip() or len(q) > 254:
            cherrypy.response.status = 400
            return {"error": "请输入有效的手机号、邮箱、身份证号或 QQ 号。"}
        q = q.strip()
        if detect_query_type(q) is None:
            cherrypy.response.status = 400
            return {"error": "输入格式无效，请检查格式后重试。"}
        try:
            db = LeakCheckDB()
            result = db.search_persons(q)
        except (OSError, sqlite3.Error):
            cherrypy.response.status = 503
            return {"error": "数据源不可用，请稍后重试。", "status": "unavailable",
                    "data_source": "本地 SQLite 合成样例库"}
        if not result.get("found") and not result.get("error"):
            result["message"] = "当前数据源未发现匹配，不代表不存在相关信息。"
        result["data_source"] = "本地 SQLite 合成样例库"
        result["coverage"] = "仅检索本地合成演示数据；覆盖范围有限，不是实时互联网查询。"
        return result

    # ========================
    # 隐私处理模块（脱敏/隐藏/删除）
    # ========================

    @cherrypy.expose
    def privacyaction(self: 'SpiderFootWebUi') -> str:
        """渲染隐私处理页面"""
        user_id = current_user_id()
        db = PrivacyActionDB()
        stats_res = db.get_stats(user_id)
        stats = stats_res.get("stats", {})
        templ = Template(filename='spiderfoot/templates/privacyaction.tmpl', lookup=self.lookup)
        return templ.render(
            docroot=self.docroot,
            pageid='PRIVACYACTION',
            version=__version__,
            stats=stats,
        )

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def privacyactionsubmit(self: 'SpiderFootWebUi',
                             action_type: str = None,
                             platform: str = None,
                             content: str = None,
                             csrf_token: str = None) -> dict:
        """提交隐私处理任务（POST）"""
        username = cherrypy.session.get("sf_user", "")
        user_id = current_user_id()
        if not action_type or action_type not in ("mask", "hide", "delete"):
            return {"success": False, "error": "操作类型无效"}
        if not platform or not platform.strip() or len(platform) > 128:
            return {"success": False, "error": "请填写目标平台或内容来源"}
        if not content or not content.strip() or len(content) > 10000:
            return {"success": False, "error": "请填写需要处理的内容或链接"}

        db = PrivacyActionDB()
        return db.create_action(
            user_id=user_id,
            username=username,
            action_type=action_type.strip(),
            platform=platform.strip(),
            content=content.strip(),
        )

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def privacyactionlist(self: 'SpiderFootWebUi',
                           page: str = "1",
                           page_size: str = "20") -> dict:
        """分页查询当前用户的处理任务列表"""
        user_id = current_user_id()
        try:
            p = int(page)
            ps = int(page_size)
        except ValueError:
            p, ps = 1, 20
        db = PrivacyActionDB()
        return db.list_actions(user_id, p, ps)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def privacyactiondelete(self: 'SpiderFootWebUi', action_id: str = None, csrf_token: str = None) -> dict:
        """删除一条处理记录"""
        user_id = current_user_id()
        if not action_id:
            cherrypy.response.status = 400
            return {"success": False, "error": "缺少 action_id"}
        db = PrivacyActionDB()
        result = db.delete_action(action_id, user_id)
        if result.get("success"):
            return result
        if result.get("error") == "任务不存在或无权限":
            raise cherrypy.HTTPError(404, "Resource not found")
        cherrypy.response.status = 503
        return {"success": False, "error": "申请记录暂时无法删除。"}

    # ========================
    # 风险告警页面
    # ========================

    @cherrypy.expose
    def riskalertspage(self: 'SpiderFootWebUi') -> str:
        """渲染风险告警页面"""
        templ = Template(filename='spiderfoot/templates/riskalerts.tmpl', lookup=self.lookup)
        return templ.render(docroot=self.docroot, pageid='RISKALERTS', version=__version__)

    # ========================
    # 数据洞察看板页面
    # ========================

    @cherrypy.expose
    def dataviz(self: 'SpiderFootWebUi') -> str:
        """渲染数据洞察看板页面"""
        templ = Template(filename='spiderfoot/templates/dataviz.tmpl', lookup=self.lookup)
        return templ.render(docroot=self.docroot, pageid='DATAVIZ', version=__version__)

    # ========================
    # 服务监控页面
    # ========================

    @cherrypy.expose
    def servicemonitor(self: 'SpiderFootWebUi') -> str:
        """渲染服务监控页面"""
        templ = Template(filename='spiderfoot/templates/servicemonitor.tmpl', lookup=self.lookup)
        return templ.render(docroot=self.docroot, pageid='SERVICEMONITOR', version=__version__)

    # ========================
    # 系统信息 API（真实 CPU/内存/磁盘）
    # ========================

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def sysinfo(self: 'SpiderFootWebUi') -> dict:
        """返回服务器真实系统指标"""
        import psutil, os, time

        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # 内存
        mem = psutil.virtual_memory()
        mem_total = round(mem.total / 1024 / 1024 / 1024, 1)
        mem_used = round(mem.used / 1024 / 1024 / 1024, 1)
        mem_percent = mem.percent

        # 磁盘
        disk = psutil.disk_usage('/')
        disk_total = round(disk.total / 1024 / 1024 / 1024, 1)
        disk_used = round(disk.used / 1024 / 1024 / 1024, 1)
        disk_percent = disk.percent

        # 本进程信息
        proc = psutil.Process(os.getpid())
        proc_mem = round(proc.memory_info().rss / 1024 / 1024, 1)
        proc_create = proc.create_time()
        uptime_seconds = int(time.time() - proc_create)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        uptime_str = f"{hours}小时{minutes}分钟" if hours else f"{minutes}分钟"

        # 数据库统计
        try:
            dbh = self._db()
            total_scans = dbh.scanInstanceList()
            total_scans_count = len(total_scans) if total_scans else 0
        except Exception:
            total_scans_count = -1

        # 告警统计
        try:
            alerts = self.riskalerts()
            alert_count = len(alerts) if isinstance(alerts, list) else 0
        except Exception:
            alert_count = -1

        return {
            "cpu_percent": cpu_percent,
            "cpu_cores": cpu_count,
            "mem_percent": mem_percent,
            "mem_used": mem_used,
            "mem_total": mem_total,
            "disk_percent": disk_percent,
            "disk_used": disk_used,
            "disk_total": disk_total,
            "process_mem_mb": proc_mem,
            "uptime": uptime_str,
            "uptime_seconds": uptime_seconds,
            "total_scans": total_scans_count,
            "alert_count": alert_count,
        }

    # ========================
    # 服务器日志 API
    # ========================

    @cherrypy.expose
    def serverlogs(self: 'SpiderFootWebUi', lines: str = "50") -> str:
        """返回服务器最新日志"""
        cherrypy.response.headers['Content-Type'] = 'application/json; charset=utf-8'
        import os

        log_paths = [
            '/home/ubuntu/sf.log',
            '/tmp/spiderfoot.log',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sf.log'),
        ]

        log_content = ""
        for lp in log_paths:
            if os.path.isfile(lp):
                try:
                    with open(lp, 'r', encoding='utf-8', errors='replace') as f:
                        all_lines = f.readlines()
                        n = int(lines)
                        log_content = "".join(all_lines[-n:])
                    break
                except Exception:
                    continue

        if not log_content:
            log_content = "暂无日志数据"

        return json.dumps({"logs": log_content, "lines": len(log_content.splitlines())}, ensure_ascii=False).encode('utf-8')

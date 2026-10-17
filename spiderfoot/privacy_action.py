# -*- coding: utf-8 -*-
"""
本地脱敏，以及隐藏/删除申请记录与人工跟进。
申请记录本身不会联系第三方平台或改变外部内容。
"""

import os
import re
import time
import uuid
import logging

import pymysql

from spiderfoot.auth_mysql import AuthConfigurationError, AuthDatabaseUnavailable

log = logging.getLogger("spiderfoot.privacy_action")


# ================================================================
# 脱敏工具函数（优先本地正则，NLP 降级）
# ================================================================

_PHONE_RE  = re.compile(r'1[3-9]\d{9}')
_EMAIL_RE  = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
_ID_RE     = re.compile(r'\d{17}[\dXx]')
_NAME_RE   = re.compile(r'[\u4e00-\u9fa5]{2,4}')   # 中文姓名（2-4 汉字）
_ADDR_RE   = re.compile(
    r'[\u4e00-\u9fa5]{2,}(?:省|市|区|县|镇|乡|街道|路|大道|号|弄|室|楼)[^\s，。；,;]{1,30}'
)


def _mask_phone(m: re.Match) -> str:
    v = m.group()
    return v[:3] + '****' + v[-4:]


def _mask_email(m: re.Match) -> str:
    v = m.group()
    name, domain = v.split('@', 1)
    masked = name[:2] + '***' if len(name) > 2 else name[0] + '***'
    return masked + '@' + domain


def _mask_id(m: re.Match) -> str:
    v = m.group()
    return v[:4] + '**********' + v[-2:]


def _mask_addr(m: re.Match) -> str:
    v = m.group()
    return v[:2] + '****'


def mask_text_local(text: str) -> str:
    """本地正则脱敏：手机 > 邮箱 > 身份证 > 地址"""
    text = _PHONE_RE.sub(_mask_phone, text)
    text = _EMAIL_RE.sub(_mask_email, text)
    text = _ID_RE.sub(_mask_id, text)
    text = _ADDR_RE.sub(_mask_addr, text)
    return text


def mask_text(text: str) -> str:
    """
    优先本地正则脱敏；若文本超过 200 字且本地未命中任何敏感词，
    则尝试调用 NLP 接口（此处为占位逻辑，可接入 HanLP 等）。
    """
    result = mask_text_local(text)
    # NLP 兜底：仅当本地完全没有命中且文本较长时触发
    # 实际部署时可在此调用第三方 NLP 服务
    if result == text and len(text) > 200:
        try:
            result = _mask_text_nlp(text)
        except Exception as e:
            log.warning("NLP 脱敏失败，降级使用原文: %s", e)
    return result


def _mask_text_nlp(text: str) -> str:
    """
    NLP 命名实体识别脱敏（占位实现）。
    实际可接入 HanLP / jieba + 自定义规则 / 腾讯 NLP API。
    当前版本：简单匹配中文 2-4 汉字序列（人名特征）进行额外脱敏。
    """
    # 简易占位：对疑似人名（2-4 汉字）打码
    def _name_repl(m: re.Match) -> str:
        v = m.group()
        return v[0] + '*' * (len(v) - 1)

    return _NAME_RE.sub(_name_repl, text)


# ================================================================
# MySQL 数据库操作
# ================================================================

class PrivacyActionDB:
    """隐私处理记录的 MySQL 存储层。"""

    LEGACY_CLAIM_PREFIX = re.compile(
        r"(?:系统|申请)?已提交给平台|已向(?:对应)?平台提交(?:删除)?(?:申请|请求)?"
        r"|预计\s*1\s*[-–—~～]\s*3\s*天(?:内)?(?:处理)?(?:完成)?"
    )
    LEGACY_NOTE = "历史模拟记录，平台提交情况未经核实，需人工跟进。"

    FOLLOWUP_STATUSES = (
        "draft", "recorded", "awaiting_manual", "platform_contacted",
        "platform_processing", "completed", "unable",
    )

    TABLE_DDL = """
    CREATE TABLE IF NOT EXISTS privacy_actions (
        id          VARCHAR(64)  NOT NULL PRIMARY KEY,
        username    VARCHAR(64)  NOT NULL,
        user_id     BIGINT       NULL,
        action_type VARCHAR(16)  NOT NULL COMMENT 'mask|hide|delete',
        platform    VARCHAR(128) NOT NULL COMMENT '目标平台/内容描述',
        content     TEXT         NOT NULL COMMENT '原始内容或 URL',
        masked_content TEXT      COMMENT '脱敏后内容（仅 mask 操作有值）',
        status      VARCHAR(32)  NOT NULL DEFAULT 'pending'
                    COMMENT 'pending|processing|done|failed',
        note        VARCHAR(512) DEFAULT '' COMMENT '备注/进度说明',
        user_confirmed TINYINT NOT NULL DEFAULT 0 COMMENT '用户确认记录申请',
        manual_note VARCHAR(1024) NOT NULL DEFAULT '' COMMENT '人工跟进备注',
        created_at  BIGINT       NOT NULL,
        updated_at  BIGINT       NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """

    def __init__(self):
        self.host     = os.getenv("SF_AUTH_MYSQL_HOST", "127.0.0.1")
        try:
            self.port = int(os.getenv("SF_AUTH_MYSQL_PORT", "3306"))
        except ValueError:
            raise AuthConfigurationError("SF_AUTH_MYSQL_PORT must be an integer.") from None
        self.user     = os.getenv("SF_AUTH_MYSQL_USER", "").strip()
        self.password = os.getenv("SF_AUTH_MYSQL_PASSWORD")
        self.database = os.getenv("SF_AUTH_MYSQL_DATABASE", "spiderfoot_auth")
        if not self.user or not self.password:
            raise AuthConfigurationError("Configure SF_AUTH_MYSQL_USER and SF_AUTH_MYSQL_PASSWORD.")
        self._ensure_table()

    def _connect(self):
        return pymysql.connect(
            host=self.host, port=self.port,
            user=self.user, password=self.password,
            database=self.database,
            charset="utf8mb4", autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def _ensure_table(self):
        conn = None
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(self.TABLE_DDL)
                # Existing records keep their username for display, while all access
                # control is migrated to the stable authentication user ID.
                cur.execute(
                    "SELECT COUNT(*) AS column_count FROM information_schema.columns "
                    "WHERE table_schema=DATABASE() AND table_name=%s AND column_name=%s",
                    ("privacy_actions", "user_id"),
                )
                column_row = cur.fetchone()
                column_count = next(iter(column_row.values())) if isinstance(column_row, dict) else column_row[0]
                if not column_count:
                    cur.execute("ALTER TABLE privacy_actions ADD COLUMN user_id BIGINT NULL AFTER username")
                for column, definition in (
                    ("user_confirmed", "TINYINT NOT NULL DEFAULT 0"),
                    ("manual_note", "VARCHAR(1024) NOT NULL DEFAULT ''"),
                ):
                    cur.execute(
                        "SELECT COUNT(*) AS column_count FROM information_schema.columns "
                        "WHERE table_schema=DATABASE() AND table_name=%s AND column_name=%s",
                        ("privacy_actions", column),
                    )
                    row = cur.fetchone()
                    count = next(iter(row.values())) if isinstance(row, dict) else row[0]
                    if not count:
                        cur.execute(f"ALTER TABLE privacy_actions ADD COLUMN {column} {definition}")
                cur.execute(
                    "UPDATE privacy_actions SET user_id=(SELECT id FROM users WHERE users.username=privacy_actions.username) "
                    "WHERE user_id IS NULL AND EXISTS (SELECT 1 FROM users WHERE users.username=privacy_actions.username)"
                )
                # Previous versions also converted old statuses to 'recorded'
                # without cleaning their simulated notes. Unconfirmed records
                # cover that migration without touching new confirmed requests.
                cur.execute(
                    "SELECT id, note FROM privacy_actions WHERE action_type IN ('hide','delete') "
                    "AND (status IN ('processing','pending','done','failed') "
                    "OR (status='recorded' AND user_confirmed=0))"
                )
                for row in cur.fetchall():
                    cleaned = self._sanitize_legacy_note(row["note"])
                    if cleaned != row["note"]:
                        cur.execute("UPDATE privacy_actions SET note=%s WHERE id=%s",
                                    (cleaned, row["id"]))
                # Old processing/pending values never proved a platform request.
                cur.execute(
                    "UPDATE privacy_actions SET status='recorded' "
                    "WHERE action_type IN ('hide','delete') "
                    "AND status IN ('processing','pending','done','failed')"
                )
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.statistics "
                    "WHERE table_schema=DATABASE() AND table_name='privacy_actions' "
                    "AND index_name='idx_privacy_actions_owner'"
                )
                index_row = cur.fetchone()
                index_count = next(iter(index_row.values())) if isinstance(index_row, dict) else index_row[0]
                if not index_count:
                    cur.execute("CREATE INDEX idx_privacy_actions_owner ON privacy_actions(user_id)")
        except Exception:
            log.error("隐私申请数据库初始化失败。")
            raise AuthDatabaseUnavailable("隐私申请数据库暂不可用。") from None
        finally:
            if conn:
                conn.close()

    @classmethod
    def _sanitize_legacy_note(cls, note):
        """Remove only recognized leading simulation claims; retain human text."""
        if not isinstance(note, str):
            return note
        remaining = note.lstrip()
        found = False
        while match := cls.LEGACY_CLAIM_PREFIX.match(remaining):
            found = True
            remaining = remaining[match.end():].lstrip(" \t\r\n，,；;。")
        if not found:
            return note
        replacement = cls.LEGACY_NOTE + ("；" + remaining if remaining else "")
        # Existing note columns are VARCHAR(512). Preserve all human text if
        # adding the explanation would exceed the old column's capacity.
        return replacement if len(replacement) <= 512 else remaining

    # ---- CRUD ----

    def create_action(self, user_id: int, username: str, action_type: str,
                      platform: str, content: str, user_confirmed: bool = False) -> dict:
        """
        本地脱敏立即完成；隐藏/删除只生成待跟进记录。
        """
        action_id = str(uuid.uuid4())
        now = int(time.time())
        masked_content = None
        status = "recorded"
        note = ""

        if action_type == "mask":
            masked_content = mask_text(content)
            status = "done"
            note = "脱敏处理完成，敏感信息已打码"
        elif action_type == "hide":
            note = "申请记录已保存，等待人工跟进；尚未向平台提交"
        elif action_type == "delete":
            note = "申请记录已保存，等待人工跟进；尚未向平台提交"
        else:
            return {"success": False, "error": "未知操作类型"}

        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO privacy_actions
                       (id, username, user_id, action_type, platform, content,
                        masked_content, status, note, user_confirmed, manual_note,
                        created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (action_id, username, user_id, action_type, platform, content,
                     masked_content, status, note, int(bool(user_confirmed)), "", now, now)
                )
        except Exception:
            log.error("创建隐私申请记录失败。")
            return {"success": False, "error": "申请记录暂时无法保存，请稍后重试。"}
        finally:
            if 'conn' in locals():
                conn.close()

        return {
            "success": True,
            "id": action_id,
            "action_type": action_type,
            "status": status,
            "note": note,
            "masked_content": masked_content,
        }

    def list_actions(self, user_id: int, page: int = 1,
                     page_size: int = 20, *, admin: bool = False) -> dict:
        """分页查询本人记录；管理员入口显式指定 admin。"""
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        offset = (page - 1) * page_size
        conn = None
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                scope = "action_type IN ('hide','delete')" if admin else "user_id=%s"
                cur.execute("SELECT COUNT(*) AS cnt FROM privacy_actions WHERE " + scope,
                            () if admin else (user_id,))
                total = cur.fetchone()["cnt"]
                preview = "content" if admin else "SUBSTRING(content, 1, 80)"
                cur.execute(
                    """SELECT id, username, action_type, platform, status, note,
                              user_confirmed, manual_note, created_at, updated_at,
                              """ + preview + """ AS content_preview,
                              masked_content
                       FROM privacy_actions
                       WHERE """ + scope + """
                       ORDER BY created_at DESC
                       LIMIT %s OFFSET %s""",
                    (page_size, offset) if admin else (user_id, page_size, offset)
                )
                rows = cur.fetchall()
            for row in rows:
                row["content_preview"] = mask_text(row.get("content_preview") or "")
                row["platform"] = mask_text(row.get("platform") or "")
                row["manual_note"] = mask_text(row.get("manual_note") or "")
            return {"success": True, "total": total, "items": rows}
        except Exception:
            log.error("读取隐私申请记录失败。")
            return {"success": False, "error": "申请记录暂时无法读取。", "total": 0, "items": []}
        finally:
            if conn:
                conn.close()

    def get_action(self, action_id: str, user_id: int) -> dict:
        """查询单条任务详情"""
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM privacy_actions WHERE id=%s AND user_id=%s",
                    (action_id, user_id)
                )
                row = cur.fetchone()
            conn.close()
            if not row:
                return {"success": False, "error": "任务不存在"}
            return {"success": True, "item": row}
        except Exception:
            log.error("读取隐私申请详情失败。")
            return {"success": False, "error": "申请记录暂时无法读取。"}

    def update_status(self, action_id: str, user_id: int,
                      status: str, note: str = "") -> dict:
        """更新任务状态（内部使用）"""
        now = int(time.time())
        if status not in self.FOLLOWUP_STATUSES:
            return {"success": False, "error": "处理状态无效"}
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE privacy_actions
                       SET status=%s, note=%s, updated_at=%s
                       WHERE id=%s AND user_id=%s""",
                    (status, note, now, action_id, user_id)
                )
                affected = cur.rowcount
            conn.close()
            if affected == 0:
                return {"success": False, "error": "任务不存在或无权限"}
            return {"success": True}
        except Exception:
            log.error("更新隐私申请状态失败。")
            return {"success": False, "error": "申请记录暂时无法更新。"}

    def update_followup(self, action_id: str, status: str, manual_note: str) -> dict:
        """仅供管理员 HTTP 入口调用；外部处理状态需留下人工依据。"""
        if not isinstance(manual_note, str):
            return {"success": False, "error": "人工备注格式无效"}
        if status not in self.FOLLOWUP_STATUSES:
            return {"success": False, "error": "处理状态无效"}
        manual_note = (manual_note or "").strip()
        if len(manual_note) > 1024 or (status in (
                "platform_contacted", "platform_processing", "completed", "unable")
                and not manual_note):
            return {"success": False, "error": "请填写人工跟进依据（最多 1024 字）"}
        conn = None
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE privacy_actions SET status=%s, manual_note=%s, note='', "
                    "updated_at=CASE WHEN updated_at >= %s THEN updated_at+1 ELSE %s END "
                    "WHERE id=%s AND action_type IN ('hide','delete')",
                    (status, manual_note, int(time.time()), int(time.time()), action_id),
                )
                if cur.rowcount == 0:
                    return {"success": False, "error": "申请记录不存在"}
            return {"success": True, "status": status}
        except Exception:
            log.error("更新人工跟进状态失败。")
            return {"success": False, "error": "人工跟进状态暂时无法更新。"}
        finally:
            if conn:
                conn.close()

    def delete_action(self, action_id: str, user_id: int) -> dict:
        """删除一条处理记录"""
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM privacy_actions WHERE id=%s AND user_id=%s",
                    (action_id, user_id)
                )
                affected = cur.rowcount
            conn.close()
            if affected == 0:
                return {"success": False, "error": "任务不存在或无权限"}
            return {"success": True}
        except Exception:
            log.error("删除隐私申请记录失败。")
            return {"success": False, "error": "申请记录暂时无法删除。"}

    def get_stats(self, user_id: int) -> dict:
        """统计当前用户各状态任务数量"""
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT action_type, status, COUNT(*) AS cnt
                       FROM privacy_actions
                       WHERE user_id=%s
                       GROUP BY action_type, status""",
                    (user_id,)
                )
                rows = cur.fetchall()
            conn.close()
            stats = {kind: {status: 0 for status in (*self.FOLLOWUP_STATUSES, "done")}
                     for kind in ("mask", "hide", "delete")}
            stats["total"] = 0
            for r in rows:
                at = r["action_type"]
                st = r["status"]
                if at in stats and st in stats[at]:
                    stats[at][st] = r["cnt"]
                stats["total"] += r["cnt"]
            return {"success": True, "stats": stats}
        except Exception:
            log.error("统计隐私申请记录失败。")
            return {"success": False, "error": "申请统计暂时无法读取。"}

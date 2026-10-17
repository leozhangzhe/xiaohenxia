# -*- coding: utf-8 -*-
"""
隐私处理模块 - 消痕侠核心功能
支持三种数字痕迹处理方式：
  1. 脱敏处理 (mask)   — 对内容中的姓名/电话/地址/邮箱自动打码
  2. 隐藏处理 (hide)   — 一键发起隐藏申请，内容不再对外公开
  3. 删除申请 (delete) — 自动向平台提交删除请求，全程跟踪进度
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
    """隐私处理任务的 MySQL 存储层"""

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
                cur.execute(
                    "UPDATE privacy_actions SET user_id=(SELECT id FROM users WHERE users.username=privacy_actions.username) "
                    "WHERE user_id IS NULL AND EXISTS (SELECT 1 FROM users WHERE users.username=privacy_actions.username)"
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

    # ---- CRUD ----

    def create_action(self, user_id: int, username: str, action_type: str,
                      platform: str, content: str) -> dict:
        """
        创建一条处理任务：
          - mask   → 立即执行本地脱敏，状态直接置 done
          - hide   → 状态置 processing，模拟异步发起申请
          - delete → 状态置 processing，模拟异步提交删除请求
        """
        action_id = str(uuid.uuid4())
        now = int(time.time())
        masked_content = None
        status = "processing"
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
                        masked_content, status, note, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (action_id, username, user_id, action_type, platform, content,
                     masked_content, status, note, now, now)
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
                     page_size: int = 20) -> dict:
        """分页查询当前用户的处理任务列表"""
        offset = (page - 1) * page_size
        try:
            conn = self._connect()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM privacy_actions WHERE user_id=%s",
                    (user_id,)
                )
                total = cur.fetchone()["cnt"]
                cur.execute(
                    """SELECT id, action_type, platform, status, note,
                              created_at, updated_at,
                              SUBSTRING(content, 1, 80) AS content_preview,
                              masked_content
                       FROM privacy_actions
                       WHERE user_id=%s
                       ORDER BY created_at DESC
                       LIMIT %s OFFSET %s""",
                    (user_id, page_size, offset)
                )
                rows = cur.fetchall()
            for row in rows:
                row["content_preview"] = mask_text(row.get("content_preview") or "")
                row["platform"] = mask_text(row.get("platform") or "")
            conn.close()
            return {"success": True, "total": total, "items": rows}
        except Exception:
            log.error("读取隐私申请记录失败。")
            return {"success": False, "error": "申请记录暂时无法读取。", "total": 0, "items": []}

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
            stats = {
                "mask":   {"done": 0, "processing": 0, "pending": 0, "failed": 0},
                "hide":   {"done": 0, "processing": 0, "pending": 0, "failed": 0},
                "delete": {"done": 0, "processing": 0, "pending": 0, "failed": 0},
                "total":  0,
            }
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

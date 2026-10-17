"""Owned, persistent live-search jobs and independent source adapters."""
import os
import time
import ipaddress
import json
import re
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path
from urllib.parse import urlsplit


SOURCES = {
    "spiderfoot": "SpiderFoot DNS 模块实时检索；仅限本次启用模块，不代表互联网全部信息。",
    "sherlock": "Sherlock 最多 10 个常见站点响应规则匹配；同名不证明身份归属，可能误报。",
    "maigret": "Maigret 前 25 个站点检索，关闭递归与身份推断；可能误报或漏报。",
    "whatsmyname": "WhatsMyName 最多 10 个常见站点，经 sfp_accounts 检查；规则会失效，需人工核验。",
    "holehe": "邮箱可能注册过相关网站；仅 GitHub / Gravatar 注册信号，不是泄露记录，限流或规则失效会影响结果。",
    "hibp": "HIBP 已收录事件中的邮箱匹配；覆盖有限，无匹配不代表不存在相关信息。",
}
TERMINAL = {"completed", "partial", "failed", "not_configured", "timeout", "cancelled"}
INPUT_SOURCES = {"username": ("sherlock", "maigret", "whatsmyname"), "email": ("holehe", "hibp"),
                 "domain": ("spiderfoot",), "website": ("spiderfoot",), "ip": ("spiderfoot",)}


def validate_input(kind, query):
    if not isinstance(query, str) or not query.strip() or len(query) > 254 or any(ord(c) < 32 or ord(c) == 127 for c in query):
        raise ValueError("输入格式无效")
    query = query.strip()
    if kind == "username":
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", query):
            raise ValueError("用户名仅支持 1–64 位字母、数字、点、横线和下划线")
    elif kind == "email":
        if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+", query):
            raise ValueError("邮箱格式无效")
    elif kind in ("domain", "website", "ip"):
        host = query
        if "://" in query:
            parsed = urlsplit(query)
            if not safe_url(query) or parsed.query or parsed.fragment or parsed.port not in (None, 80, 443):
                raise ValueError("仅支持不带密码、查询参数的 HTTP/HTTPS 网站")
            host, kind = parsed.hostname, "website"
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                raise ValueError("仅支持公开 IP")
            kind = "ip"
        except ValueError as exc:
            if re.fullmatch(r"[0-9.]+", host or "") or ":" in (host or ""):
                raise ValueError("IP 格式无效或不是公开地址") from exc
            try:
                domain = host.encode("idna").decode("ascii")
            except (UnicodeError, AttributeError):
                raise ValueError("域名格式无效") from None
            if not re.fullmatch(r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", domain):
                raise ValueError("域名格式无效") from None
            if kind != "website":
                query = domain.lower()
    else:
        raise ValueError("不支持该输入类型；支持公开域名/网站/IP、用户名和邮箱")
    return kind, query


def display_query(kind, value):
    if kind == "email":
        name, domain = value.split("@", 1)
        return name[:2] + "***@" + domain
    if kind == "username":
        return value[:2] + "***"
    return value


def safe_url(value):
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme in ("https", "http") and parsed.hostname and not parsed.username and not parsed.password:
            return value
    except ValueError:
        pass
    return None


class SourceAdapter:
    def __init__(self, source, runner):
        self.source = source
        self.runner = runner

    def search(self, input_type, query, cancel, timeout=90):
        now = int(time.time())
        def outcome(status, message, results=None):
            return {"status": status, "results": results or [], "queried_at": now,
                    "message": message, "limitations": SOURCES[self.source]}
        if self.source == "hibp" and not os.environ.get("SF_HIBP_API_KEY", "").strip():
            return outcome("not_configured", "HIBP API Key 未配置；未发送请求。")
        if cancel.is_set():
            return outcome("cancelled", "已取消")
        if not self.runner.available(self.source):
            return outcome("not_configured", "工具未安装；请运行 scripts/install-live-sources.ps1 重建依赖。")
        try:
            raw = self.runner.run(self.source, {"input_type": input_type, "query": query}, cancel, timeout)
            status = raw.get("status")
            if status not in TERMINAL:
                raise ValueError("invalid source output")
            rows = []
            for item in raw.get("items", [])[:1000]:
                if not isinstance(item, dict):
                    raise ValueError("invalid source item")
                rows.append({
                    "source": self.source, "input_type": input_type, "query": query,
                    "result_type": "email_registration_signal" if self.source == "holehe" else str(item.get("type", "public_signal"))[:80],
                    "title": str(item.get("title", "检索线索"))[:500],
                    "value": str(item.get("value", ""))[:4000],
                    "original_url": safe_url(item.get("url")),
                    "confidence": "工具规则匹配，未经身份归属验证；请人工核验。",
                    "status": "待人工核验", "queried_at": now,
                    "limitations": SOURCES[self.source],
                    "raw_summary": str(item.get("summary", "仅保存必要来源摘要，不含响应正文。"))[:1000],
                })
            messages = {"completed": "检索完成" if rows else "当前数据源未发现匹配，不代表不存在相关信息。",
                        "partial": "部分完成；部分站点不可用或受限。", "failed": "数据源不可用。",
                        "timeout": "数据源超时。", "cancelled": "已取消", "not_configured": "数据源未配置或未安装。"}
            return outcome(status, messages[status], rows)
        except TimeoutError:
            return outcome("timeout", "数据源超时，已关闭检索进程。")
        except Exception:
            return outcome("cancelled" if cancel.is_set() else "failed", "已取消" if cancel.is_set() else "数据源不可用，请检查安装或网络。")


class LiveSearchService:
    def __init__(self, path, runner, max_workers=2, timeout=90):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.runner, self.timeout = runner, timeout
        self.executor = ThreadPoolExecutor(max_workers=max(1, min(4, max_workers)), thread_name_prefix="live-source")
        self.lock = threading.RLock()
        self.jobs = {}
        self.closed = False
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS live_tasks (
                    id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, input_type TEXT NOT NULL,
                    query TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS live_task_owner ON live_tasks(user_id);
                CREATE TABLE IF NOT EXISTS live_sources (
                    task_id TEXT NOT NULL REFERENCES live_tasks(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL,
                    message TEXT NOT NULL, limitations TEXT NOT NULL, queried_at INTEGER NOT NULL,
                    results TEXT NOT NULL DEFAULT '[]', PRIMARY KEY(task_id, source));
                CREATE INDEX IF NOT EXISTS live_source_owner ON live_sources(user_id, task_id);
                UPDATE live_sources SET status='cancelled', message='服务已重启，未完成来源已取消。'
                    WHERE status IN ('waiting','running');
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def create(self, owner, kind, query, sources=None):
        kind, query = validate_input(kind, query)
        selected = list(INPUT_SOURCES[kind]) if sources is None else sources
        if (not isinstance(selected, list) or not selected or len(selected) > 3
                or any(not isinstance(s, str) or s not in INPUT_SOURCES[kind] for s in selected)
                or len(set(selected)) != len(selected)):
            raise ValueError("数据源与输入类型不匹配")
        with self.lock:
            if self.closed:
                raise RuntimeError("检索服务已停止")
            with self.connect() as db:
                pending = db.execute("SELECT COUNT(DISTINCT task_id) FROM live_sources WHERE status IN ('waiting','running')").fetchone()[0]
                own = db.execute("SELECT COUNT(DISTINCT task_id) FROM live_sources WHERE user_id=? AND status IN ('waiting','running')", (owner,)).fetchone()[0]
                if pending >= 16 or own >= 3:
                    raise ValueError("检索队列已满，请等待当前任务完成")
                task_id, now = uuid.uuid4().hex, int(time.time())
                db.execute("INSERT INTO live_tasks VALUES (?,?,?,?,?,?)", (task_id, owner, kind, query, now, now))
                db.executemany("INSERT INTO live_sources(task_id,user_id,source,status,message,limitations,queried_at) VALUES (?,?,?,'waiting','等待执行',?,?)",
                               [(task_id, owner, source, SOURCES[source], now) for source in selected])
            event = threading.Event()
            futures = [self.executor.submit(self._run, owner, task_id, source, kind, query, event) for source in selected]
            self.jobs[task_id] = (event, futures)
        return self.get(owner, task_id)

    def _run(self, owner, task_id, source, kind, query, event):
        with self.connect() as db:
            updated = db.execute("UPDATE live_sources SET status='running', message='检索中' WHERE task_id=? AND user_id=? AND source=? AND status='waiting'", (task_id, owner, source)).rowcount
        if not updated:
            return
        result = SourceAdapter(source, self.runner).search(kind, query, event, self.timeout)
        with self.connect() as db:
            db.execute("UPDATE live_sources SET status=?, message=?, queried_at=?, results=? WHERE task_id=? AND user_id=? AND source=? AND status='running'",
                       (result["status"], result["message"], result["queried_at"], json.dumps(result["results"], ensure_ascii=False), task_id, owner, source))
            db.execute("UPDATE live_tasks SET updated_at=? WHERE id=? AND user_id=?", (int(time.time()), task_id, owner))

    def get(self, owner, task_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM live_tasks WHERE id=? AND user_id=?", (task_id, owner)).fetchone()
            if not row:
                raise KeyError("Resource not found")
            task = dict(row)
            sources = [dict(s) for s in db.execute("SELECT source,status,message,limitations,queried_at,results FROM live_sources WHERE task_id=? AND user_id=? ORDER BY source", (task_id, owner))]
        results = []
        for source in sources:
            results.extend(json.loads(source.pop("results")))
        statuses = [s["status"] for s in sources]
        task["status"] = ("running" if "running" in statuses else "waiting" if "waiting" in statuses
            else "completed" if all(s == "completed" for s in statuses)
            else "cancelled" if all(s == "cancelled" for s in statuses)
            else "not_configured" if all(s == "not_configured" for s in statuses)
            else "partial" if any(s in ("completed", "partial") for s in statuses) else "failed")
        task["query"] = display_query(task["input_type"], task["query"])
        for result in results:
            result["query"] = task["query"]
        task["sources"], task["results"] = sources, results
        return task

    def list(self, owner):
        with self.connect() as db:
            ids = [r[0] for r in db.execute("SELECT id FROM live_tasks WHERE user_id=? ORDER BY created_at DESC LIMIT 100", (owner,))]
        return [self.get(owner, task_id) for task_id in ids]

    def cancel(self, owner, task_id):
        self.get(owner, task_id)
        with self.lock:
            job = self.jobs.get(task_id)
            if job:
                job[0].set()
                for future in job[1]:
                    future.cancel()
                running = [future for future in job[1] if not future.cancelled()]
                if running and wait(running, timeout=5).not_done:
                    raise RuntimeError("来源进程正在关闭，请稍后重试")
            with self.connect() as db:
                db.execute("UPDATE live_sources SET status='cancelled', message='已取消' WHERE task_id=? AND user_id=? AND status IN ('waiting','running')", (task_id, owner))
        return self.get(owner, task_id)

    def delete(self, owner, task_id):
        self.cancel(owner, task_id)
        with self.connect() as db:
            db.execute("DELETE FROM live_tasks WHERE id=? AND user_id=?", (task_id, owner))
        with self.lock:
            self.jobs.pop(task_id, None)

    def close(self):
        with self.lock:
            self.closed = True
            for event, _ in self.jobs.values():
                event.set()
        self.executor.shutdown(wait=True)

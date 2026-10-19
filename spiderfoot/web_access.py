"""Account ownership at the web boundary; scanner storage stays compatible."""
import re
import secrets
from urllib.parse import parse_qs

import cherrypy

from spiderfoot import SpiderFootDb


def current_user_id():
    value = cherrypy.session.get("sf_user_id")
    if type(value) is not int or value <= 0:
        raise cherrypy.HTTPError(401, "Authentication required")
    return value


class WebScanDb(SpiderFootDb):
    def scanInstanceList(self):
        owner = current_user_id()
        owned = {row[0] for row in self.conn.execute(
            "SELECT scan_id FROM web_scan_owners WHERE user_id=?", (owner,))}
        counts = dict(self.conn.execute(
            "SELECT scan_instance_id,COUNT(*) FROM tbl_scan_results WHERE user_id=? "
            "AND type <> 'ROOT' AND COALESCE(module,'') <> 'SpiderFoot UI' GROUP BY scan_instance_id", (owner,)))
        return [(*row[:7], counts.get(row[0], 0)) for row in super().scanInstanceList() if row[0] in owned]

    def scanResultEvent(self, *args, **kwargs):
        return [row for row in super().scanResultEvent(*args, **kwargs) if row[3] != 'SpiderFoot UI']

    def scanResultSummary(self, instanceId, by="type"):
        return super().scanResultSummary(instanceId, by, excludeInputSeeds=True)

    def search(self, criteria, filterFp=False):
        if criteria.get("scan_id"):
            require_scan(self, criteria["scan_id"])
            return super().search(criteria, filterFp)
        results = []
        for scan in self.scanInstanceList():
            results.extend(super().search(dict(criteria, scan_id=scan[0]), filterFp))
        return results

    def scanInstanceDelete(self, instanceId):
        require_scan(self, instanceId)
        deleted = super().scanInstanceDelete(instanceId)
        self.conn.execute("DELETE FROM web_monitor_tasks WHERE scan_id=? AND user_id=?", (instanceId, current_user_id()))
        self.conn.execute("DELETE FROM web_scan_owners WHERE scan_id=? AND user_id=?", (instanceId, current_user_id()))
        self.conn.commit()
        return deleted


SCAN_ROUTES = set("scanexportlogs scancorrelationsexport scaneventresultexport scansearchresultexport scanviz scanopts rerunscan clonescan scaninfo scanresults scandelete resultsetfp stopscan scanlog scanerrors scanstatus scansummary scancorrelations scaneventresults scaneventresultsunique scanhistory scanelementtypediscovery search".split())
BATCH_ROUTES = set("scaneventresultexportmulti scanexportjsonmulti scanvizmulti rerunscanmulti".split())
ADMIN_ROUTES = set("opts optsexport optsraw savesettings savesettingsraw vacuum serverlogs privacyactionadminlist privacyactionstatus".split())
GENERAL_ROUTES = set("index newscan eventtypes modules correlationrules ping riskalerts riskactionupdate riskactionautofix riskactionreport startscan scanlist leakcheck leaksearch privacyaction privacyactionsubmit privacyactionlist privacyactiondelete riskalertspage dataviz servicemonitor sysinfo serverlogs csrf".split())
# Every route below changes persistent data or scanner state. Keep methods and
# CSRF validation in this shared request boundary rather than individual views.
BUSINESS_WRITE_ROUTES = set("startscan stopscan scandelete rerunscan rerunscanmulti resultsetfp savesettings savesettingsraw vacuum riskactionupdate riskactionautofix privacyactionsubmit privacyactiondelete privacyactionstatus".split())
POST_ONLY_ROUTES = BUSINESS_WRITE_ROUTES | {"leaksearch", "search", "scansearchresultexport"}
GENERAL_ROUTES.update({"livesearch", "liveavailability", "livecreate", "liveget", "livelist", "livecancel", "livedelete"})
BUSINESS_WRITE_ROUTES.update({"livecreate", "livecancel", "livedelete"})
POST_ONLY_ROUTES.update({"livecreate", "livecancel", "livedelete"})
CSRF_SESSION_KEY = "sf_business_csrf"


def business_csrf_token():
    token = cherrypy.session.get(CSRF_SESSION_KEY)
    if not isinstance(token, str) or len(token) < 40:
        token = secrets.token_urlsafe(32)
        cherrypy.session[CSRF_SESSION_KEY] = token
    return token


def validate_business_csrf():
    expected = cherrypy.session.get(CSRF_SESSION_KEY)
    if "csrf_token" in parse_qs(cherrypy.request.query_string, keep_blank_values=True):
        cherrypy.response.headers["X-CSRF-Error"] = "1"
        raise cherrypy.HTTPError(403, "安全令牌无效或已过期，请刷新页面后重试。")
    supplied = cherrypy.request.headers.get("X-CSRF-Token")
    if supplied is None:
        supplied = cherrypy.request.params.get("csrf_token")
    if (not isinstance(expected, str) or not isinstance(supplied, str)
            or not expected.isascii() or not supplied.isascii()
            or len(supplied) > 256 or not secrets.compare_digest(expected, supplied)):
        cherrypy.response.headers["X-CSRF-Error"] = "1"
        raise cherrypy.HTTPError(403, "安全令牌无效或已过期，请刷新页面后重试。")


def require_scan(db, scan_id):
    if (not isinstance(scan_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", scan_id)
            or not db.conn.execute("SELECT 1 FROM web_scan_owners WHERE scan_id=? AND user_id=?", (scan_id, current_user_id())).fetchone()):
        raise cherrypy.HTTPError(404, "Resource not found")


def authorize_request(ui):
    path = cherrypy.request.path_info or "/"
    if ui.docroot and path.startswith(ui.docroot + "/"):
        path = path[len(ui.docroot):]
    if path.startswith("/static/") or path in ("/login", "/register", "/logout", "/favicon.ico", "/csrf"):
        return
    current_user_id()
    cherrypy.request.is_admin = cherrypy.session.get("sf_user") == ui.auth_store.admin_user
    route = path.strip("/") or "index"
    if route in POST_ONLY_ROUTES and cherrypy.request.method != "POST":
        cherrypy.response.headers["Allow"] = "POST"
        raise cherrypy.HTTPError(405, "This operation requires POST.")
    if route in BUSINESS_WRITE_ROUTES:
        validate_business_csrf()
    params = cherrypy.request.params
    if route == "query":
        # Arbitrary SQL cannot enforce account ownership. Keep CLI scanning intact.
        raise cherrypy.HTTPError(403, "Raw SQL is unavailable in the multi-user web interface")
    if route in ADMIN_ROUTES:
        if not cherrypy.request.is_admin:
            raise cherrypy.HTTPError(403, "Administrator required")
    elif route not in SCAN_ROUTES | BATCH_ROUTES | GENERAL_ROUTES:
        raise cherrypy.HTTPError(404, "Resource not found")
    if any(key in params for key in ("user_id", "username", "owner", "sf_user_id")):
        raise cherrypy.HTTPError(400, "Identity must come from the authenticated session")
    if route in SCAN_ROUTES | BATCH_ROUTES:
        raw_ids = params.get("ids" if route in BATCH_ROUTES else "id")
        if raw_ids or route != "search":
            if not isinstance(raw_ids, str) or len(raw_ids) > 13000:
                raise cherrypy.HTTPError(404, "Resource not found")
            ids = raw_ids.split(",")
            if len(ids) > 100:
                raise cherrypy.HTTPError(400, "Too many resources")
            if len(ids) != 1 and route not in BATCH_ROUTES | {"scandelete"}:
                raise cherrypy.HTTPError(404, "Resource not found")
            db = ui._db()
            try:
                for sid in ids:
                    require_scan(db, sid)
                if params.get("correlationId") and not db.conn.execute(
                    "SELECT 1 FROM tbl_scan_correlation_results WHERE id=? AND scan_instance_id=?", (params["correlationId"], ids[0])).fetchone():
                    raise cherrypy.HTTPError(404, "Resource not found")
            finally:
                db.close()


def bind_scan(config, scan_id):
    """Reserve ownership before the scanner process can write any results."""
    db = SpiderFootDb(config)
    try:
        db.conn.execute("INSERT INTO web_scan_owners(scan_id,user_id) VALUES (?,?)", (scan_id, current_user_id()))
        db.conn.commit()
    finally:
        db.close()


def initialize_ownership(config):
    db = SpiderFootDb(config)
    try:
        db.conn.execute("CREATE TABLE IF NOT EXISTS web_scan_owners (scan_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL)")
        db.conn.execute("CREATE INDEX IF NOT EXISTS idx_web_scan_owner ON web_scan_owners(user_id)")
        db.conn.execute("CREATE TABLE IF NOT EXISTS web_monitor_tasks (scan_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL)")
        db.conn.execute("CREATE INDEX IF NOT EXISTS idx_web_monitor_owner ON web_monitor_tasks(user_id)")
        db.conn.execute("INSERT OR IGNORE INTO web_monitor_tasks SELECT scan_id,user_id FROM web_scan_owners")
        db.conn.execute("CREATE TRIGGER IF NOT EXISTS web_monitor_owner_insert AFTER INSERT ON web_scan_owners BEGIN INSERT INTO web_monitor_tasks VALUES (NEW.scan_id,NEW.user_id); END")
        db.conn.execute("CREATE TRIGGER IF NOT EXISTS web_owner_immutable BEFORE UPDATE ON web_scan_owners BEGIN SELECT RAISE(ABORT,'Resource ownership is immutable'); END")
        for table, key in (("tbl_scan_instance", "guid"), ("tbl_scan_results", "scan_instance_id"), ("tbl_scan_log", "scan_instance_id"), ("tbl_scan_config", "scan_instance_id"), ("tbl_scan_correlation_results", "scan_instance_id")):
            if "user_id" not in {row[1] for row in db.conn.execute(f"PRAGMA table_info({table})")}:
                db.conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")
            db.conn.execute(f"CREATE INDEX IF NOT EXISTS idx_web_owner_{table} ON {table}(user_id)")
            db.conn.execute(f"UPDATE {table} SET user_id=(SELECT user_id FROM web_scan_owners WHERE scan_id={table}.{key}) WHERE user_id IS NULL AND {key} IN (SELECT scan_id FROM web_scan_owners)")
            db.conn.execute(f"CREATE TRIGGER IF NOT EXISTS web_owner_{table}_insert AFTER INSERT ON {table} BEGIN UPDATE {table} SET user_id=(SELECT user_id FROM web_scan_owners WHERE scan_id=NEW.{key}) WHERE rowid=NEW.rowid; END")
        db.conn.commit()
    finally:
        db.close()

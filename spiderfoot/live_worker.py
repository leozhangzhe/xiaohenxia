"""Disposable vendor-library workers. Queries arrive on stdin, never argv."""
import asyncio
from collections import Counter
from contextlib import redirect_stdout, redirect_stderr, contextmanager
from copy import deepcopy
import importlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import socket
import threading
import uuid
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def outcome(items, checked, errors, reasons=None, unit="site"):
    return {"status": "failed" if not checked or errors >= checked else "partial" if errors else "completed", "items": items,
            "diagnostics": {"checked": checked, "unresolved": min(checked, errors), "unit": unit,
                            "reasons": dict(reasons or ({"unknown": errors} if errors else {}))}}


def failure_reason(value):
    """Classify in-process errors; never return their text, URL, query or headers."""
    text = str(value).lower()
    for needles, code in ((('429', 'rate limit', 'ratelimit'), 'rate_limit'),
                          (('403', '451', 'waf', 'captcha', 'cloudflare'), 'blocked'),
                          (('timeout', 'timed out'), 'timeout'),
                          (('ssl', 'certificate', 'tls'), 'tls'),
                          (('connect', 'resolve', 'dns', 'proxy'), 'connection')):
        if any(needle in text for needle in needles):
            return code
    return 'unknown'


@contextmanager
def dns_failure_monitor():
    """Observe transient resolver faults inside this disposable process only."""
    errors = []
    originals = {name:getattr(socket,name) for name in ('gethostbyname_ex','gethostbyaddr','getaddrinfo')}
    def wrap(original):
        def call(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except OSError as exc:
                # Negative DNS answers are legitimate nonmatches; transient
                # resolver/network failures are unavailable data, never safety.
                if isinstance(exc, TimeoutError) or exc.errno not in (1,4,-2,-5,11001,11004):
                    errors.append(True)
                raise
        return call
    try:
        for name, original in originals.items():
            setattr(socket, name, wrap(original))
        yield errors
    finally:
        for name, original in originals.items():
            setattr(socket, name, original)


def sherlock(query, payload):
    import sherlock_project
    from sherlock_project.sherlock import sherlock as search
    from sherlock_project.notify import QueryNotify
    from sherlock_project.result import QueryStatus
    path = Path(sherlock_project.__file__).parent / "resources/data.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    names = ("GitHub", "GitLab", "Reddit", "Steam", "YouTube", "Vimeo", "Pinterest", "SoundCloud", "Twitch", "Wikipedia")
    sites = {name: data[name] for name in names if name in data and not data[name].get("isNSFW")}
    results = search(query, sites, QueryNotify(), timeout=8)
    items, errors, reasons = [], 0, Counter()
    for name, row in results.items():
        state = row["status"].status
        if state == QueryStatus.CLAIMED:
            items.append({"title": name, "type": "username_profile", "value": row.get("url_user", ""), "url": row.get("url_user")})
        elif state != QueryStatus.AVAILABLE:
            errors += 1
            reasons['unsupported_input' if state == QueryStatus.ILLEGAL else 'blocked' if state == QueryStatus.WAF
                    else failure_reason(getattr(row['status'], 'context', None))] += 1
    return outcome(items, len(results), errors, reasons)


def maigret(query, payload):
    import maigret as package
    from maigret.checking import maigret as search
    from maigret.sites import MaigretDatabase
    from maigret.result import MaigretCheckStatus
    database = MaigretDatabase().load_from_file(str(Path(package.__file__).parent / "resources/data.json"))
    sites = dict(list(database.ranked_sites_dict(top=25, disabled=False).items())[:25])
    results = asyncio.run(search(query, sites, logging.getLogger("live.maigret"), timeout=8,
        max_connections=4, no_progressbar=True, is_parsing_enabled=False, is_enrich_enabled=False, retries=0, dns_resolver="threaded"))
    items, errors, reasons = [], 0, Counter()
    for name, row in results.items():
        state = row.get("status")
        if state and state.status == MaigretCheckStatus.CLAIMED:
            items.append({"title": name, "type": "username_profile", "value": row.get("url_user", ""), "url": row.get("url_user")})
        elif not state or state.status != MaigretCheckStatus.AVAILABLE:
            errors += 1
            reasons['unsupported_input' if state and state.status == MaigretCheckStatus.ILLEGAL
                    else failure_reason(getattr(state, 'error', None) or getattr(state, 'context', None))] += 1
    return outcome(items, len(results), errors, reasons)


def holehe(query, payload):
    import trio
    import httpx
    modules = ("programing.github", "cms.gravatar")
    results, failures = [], []
    class CheckedClient(httpx.AsyncClient):
        async def request(self, *args, **kwargs):
            response = await super().request(*args, **kwargs)
            if response.status_code >= 400 and response.status_code not in (404, 422):
                raise RuntimeError("http_" + str(response.status_code))
            return response
    async def run():
        async with CheckedClient(timeout=8, follow_redirects=True, trust_env=False) as client:
            async def check(name):
                try:
                    module = importlib.import_module("holehe.modules." + name)
                    output = []
                    await getattr(module, name.split(".")[-1])(query, client, output)
                    if not output or output[0].get("rateLimit"):
                        failures.append('rate_limit' if output and output[0].get('rateLimit') else 'unknown')
                    else:
                        results.extend(output)
                except Exception as exc:
                    failures.append(failure_reason(exc))
            async with trio.open_nursery() as nursery:
                for name in modules:
                    nursery.start_soon(check, name)
    trio.run(run)
    items = [{"title": r["name"], "type": "email_registration_signal", "value": "邮箱可能注册过相关网站",
              "url": "https://" + r["domain"], "summary": "Holehe 站点响应信号；未保存找回邮箱或手机号。"}
             for r in results if r.get("exists") is True]
    return outcome(items, len(modules), len(failures), Counter(failures))


class ModuleTransport:
    """Small HTTP/cache bridge, preserving vendor modules without their debug logs."""
    def __init__(self, cache=None):
        import requests
        self.session = requests.Session()
        self.session.trust_env = False
        self.cache, self.codes = cache, []
        self.errors = 0
        self.reasons = Counter()
        self.lock = threading.Lock()

    def cacheGet(self, *args):
        return self.cache

    def cachePut(self, *args):
        pass

    def fetchUrl(self, url, **options):
        try:
            headers = options.get("headers", {})
            response = self.session.request("POST" if options.get("postData") else "GET", url,
                data=options.get("postData"), headers=dict(headers, **{"User-Agent": "XiaoHenXia-LiveSearch/1.0"}), timeout=8)
            code = response.status_code
            with self.lock:
                self.codes.append(code)
                if code in (403, 429) or code >= 500:
                    self.errors += 1
                    self.reasons['blocked' if code == 403 else 'rate_limit' if code == 429 else 'http_error'] += 1
            return {"code":str(code), "content":response.text if code not in (403,429) and code < 500 else None}
        except Exception as exc:
            with self.lock:
                self.codes.append(0)
                self.errors += 1
                self.reasons[failure_reason(exc)] += 1
            return {"code":"0", "content":None}


def whatsmyname(query, payload):
    from modules.sfp_accounts import sfp_accounts
    rules = ROOT / ".tools/live/whatsmyname/wmn-data.json"
    if not rules.is_file():
        return {"status":"not_configured", "items":[]}
    transport = ModuleTransport(rules.read_text(encoding="utf-8"))
    class CheckedAccounts(sfp_accounts):
        def checkSite(self, *args, **kwargs):
            try:
                return super().checkSite(*args, **kwargs)
            except Exception:
                with transport.lock:
                    transport.errors += 1
                    transport.reasons['invalid_response'] += 1
                raise
    module = CheckedAccounts()
    module.opts = deepcopy(module.opts)
    module.setup(transport, {"_fetchtimeout":8, "_useragent":"XiaoHenXia", "_maxthreads":4})
    if module.errorState:
        return {"status":"failed", "items":[]}
    preferred = {"github", "gitlab", "reddit", "steam", "youtube", "vimeo", "pinterest", "soundcloud", "twitch", "wikipedia"}
    sites = [s for s in module.sites if s["name"].lower() in preferred][:10]
    if not sites:
        return {"status":"failed", "items":[]}
    found = module.checkSites(query, sites)
    items = []
    for item in found:
        match = re.search(r"<SFURL>(.*?)</SFURL>", item)
        items.append({"title":item.split(" (Category:")[0], "type":"username_profile",
                      "value":match.group(1) if match else "规则匹配", "url":match.group(1) if match else None})
    return outcome(items, len(transport.codes), transport.errors, transport.reasons, unit='request')


def hibp(query, payload):
    key = os.environ.get("SF_HIBP_API_KEY", "").strip()
    if not key:
        return {"status":"not_configured", "items":[]}
    from modules.sfp_haveibeenpwned import sfp_haveibeenpwned
    transport = ModuleTransport()
    module = sfp_haveibeenpwned()
    module.opts = deepcopy(module.opts)
    module.setup(transport, {"api_key":key, "_fetchtimeout":8})
    data = module.query(quote(query, safe=""))
    if transport.codes and transport.codes[-1] == 404:
        return {"status":"completed", "items":[]}
    if not isinstance(data, list) or module.errorState:
        code = transport.codes[-1] if transport.codes else None
        reasons = dict(transport.reasons)
        if code in (401, 402):
            reasons['api_auth'] = 1
        return {"status":"failed", "items":[], "diagnostics":{"reasons":reasons or {'invalid_response':1}}}
    return {"status":"completed", "items":[{"title":str(row.get("Name", "HIBP 事件")),
        "type":"breach_record", "value":str(row.get("Name", "")),
        "url":"https://haveibeenpwned.com/breach/" + quote(str(row.get("Name", "")), safe=""),
        "summary":"HIBP 事件名称匹配；非密码或泄露正文。"} for row in data]}


def spiderfoot(query, payload):
    from spiderfoot import SpiderFootDb
    from sfscan import SpiderFootScanner
    from modules.sfp_dnsresolve import sfp_dnsresolve
    from modules.sfp__stor_db import sfp__stor_db
    host = urlsplit(query).hostname if "://" in query else query
    import ipaddress
    try:
        addr = ipaddress.ip_address(host)
        target_type = "IPV6_ADDRESS" if addr.version == 6 else "IP_ADDRESS"
    except ValueError:
        target_type = "INTERNET_NAME"
    cfg = {"_debug":False, "__logging":False, "__logstdout":False, "__outputfilter":None,
        "_useragent":"XiaoHenXia-LiveSearch/1.0", "_dnsserver":"", "_fetchtimeout":8,
        "_internettlds":"com\norg\nnet\ncn\nio\n" + host.split(".")[-1], "_internettlds_cache":72,
        "_genericusers":"", "_socks1type":"", "_socks2addr":"", "_socks3port":"",
        "_socks4user":"", "_socks5pwd":"", "_maxthreads":2, "__globaloptdescs__":{},
        "__correlationrules__":[], "__database":str(Path(payload["work_dir"]) / "spiderfoot.sqlite"),
        "__modules__":{"sfp_dnsresolve":{"opts":dict(sfp_dnsresolve.opts, netblocklookup=False)},
                       "sfp__stor_db":{"opts":deepcopy(sfp__stor_db.opts)}}}
    db = SpiderFootDb(cfg, init=True)
    db.close()
    scan_id = uuid.uuid4().hex
    with dns_failure_monitor() as dns_errors:
        scanner = SpiderFootScanner("统一实时检索", scan_id, host, target_type, ["sfp_dnsresolve", "sfp__stor_db"], cfg)
    db = SpiderFootDb(cfg)
    try:
        rows = db.scanResultEvent(scan_id, filterFp=True)
        items = [{"title":row[4], "type":row[4], "value":row[1],
                  "url":row[1] if str(row[1]).startswith(("https://", "http://")) else None,
                  "summary":"SpiderFoot / " + str(row[3]) + "；DNS 事件通常没有网页原始链接。"}
                 for row in rows if row[4] != "ROOT" and row[3] != "SpiderFoot UI"]
        errors = db.scanErrors(scan_id, limit=100)
        state = ("partial" if items else "failed") if errors or dns_errors or scanner.status != "FINISHED" else "completed"
        reasons = {}
        if dns_errors: reasons['dns_failure'] = len(dns_errors)
        if errors: reasons['scan_error'] = len(errors)
        if scanner.status != 'FINISHED': reasons['scan_incomplete'] = 1
        return {"status":state, "items":items, "diagnostics":{"reasons":reasons}}
    finally:
        db.close()


def main():
    payload = json.loads(sys.stdin.readline())
    logging.disable(logging.CRITICAL)
    source = sys.argv[1]
    with open(os.devnull, "w", encoding="utf-8") as sink:
        with redirect_stdout(sink), redirect_stderr(sink):
            try:
                reply = {"sherlock":sherlock, "maigret":maigret, "holehe":holehe,
                         "whatsmyname":whatsmyname, "hibp":hibp, "spiderfoot":spiderfoot}[source](payload["query"], payload)
            except (Exception, SystemExit):
                reply = {"status":"failed", "items":[], "diagnostics":{"reasons":{"tool_error":1}}}
    print(json.dumps(reply, ensure_ascii=False))


if __name__ == "__main__":
    main()

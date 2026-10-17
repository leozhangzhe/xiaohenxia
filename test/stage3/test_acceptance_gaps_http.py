"""Focused HTTP regressions for the final stage-three acceptance gaps."""
import json
import sqlite3
import time
from uuid import uuid4

import pytest

from test.stage2.test_isolation_http import ALICE, alice, business_token, http_server


def test_scan_list_ignores_jquery_cache_parameter(alice):
    client, url = alice
    response = client.get(url + "/scanlist", params={"_": "1792200000000"},
                          headers={"Accept": "application/json"}, timeout=3)
    assert response.status_code == 200
    assert [row[0] for row in response.json()] == [ALICE]


@pytest.mark.parametrize("route,table,params", [
    ("scansummary", "tbl_event_types", {"id": ALICE, "by": "type"}),
    ("riskalerts", "tbl_event_types", {}),
    ("scanlist", "tbl_scan_results", {}),
])
def test_summary_and_dashboard_database_faults_are_unavailable(alice, http_server, route, table, params):
    client, url = alice
    database = http_server[3]
    with sqlite3.connect(database) as db:
        db.execute(f"ALTER TABLE {table} RENAME TO acceptance_gap_unavailable")
    try:
        response = client.get(url + "/" + route, params=params,
                              headers={"Accept": "application/json"}, timeout=3)
        assert response.status_code == 503
        assert response.content != b"[]"
    finally:
        with sqlite3.connect(database) as db:
            db.execute(f"ALTER TABLE acceptance_gap_unavailable RENAME TO {table}")


@pytest.mark.parametrize("root_request", [False, True], ids=["cyclic-descendants", "self-referencing-root"])
def test_false_positive_traversal_terminates_and_rejects_root(alice, http_server, root_request):
    client, url = alice
    database = http_server[3]
    root, first, second, branch = [uuid4().hex for _ in range(4)]
    with sqlite3.connect(database) as db:
        db.executemany("INSERT OR REPLACE INTO tbl_event_types(event,event_descr,event_raw,event_type) VALUES (?,?,?,?)",
                       [("ROOT", "扫描目标", 0, "ENTITY"), ("STAGE3_CYCLE", "测试发现", 0, "ENTITY")])
        for event, event_type, source in [(root, "ROOT", root), (first, "STAGE3_CYCLE", second),
                                           (second, "STAGE3_CYCLE", first), (branch, "STAGE3_CYCLE", root)]:
            db.execute("INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash) VALUES (?,?,?,?,?,?,?)",
                       (ALICE, event, event_type, 1760000000, "sfp_test", "synthetic", source))
    started = time.monotonic()
    response = client.post(url + "/resultsetfp", data={
        "id": ALICE, "resultids": json.dumps([root if root_request else first]), "fp": "1"
    }, headers={"X-CSRF-Token": business_token(client, url)}, timeout=2)
    assert time.monotonic() - started < 2
    assert response.status_code in (400, 404) if root_request else response.status_code == 200
    with sqlite3.connect(database) as db:
        flags = dict(db.execute("SELECT hash,false_positive FROM tbl_scan_results WHERE hash IN (?,?,?,?)",
                                (root, first, second, branch)))
    assert flags[root] == 0
    assert [flags[first], flags[second], flags[branch]] == ([0, 0, 0] if root_request else [1, 1, 0])


@pytest.mark.parametrize("external_match", [False, True], ids=["input-only", "external-same-value"])
def test_ui_input_seed_is_not_an_external_discovery(alice, http_server, external_match):
    client, url = alice
    database = http_server[3]
    baseline = int(client.get(url + "/scanlist").json()[0][7])
    root, seed, external = [uuid4().hex for _ in range(3)]
    with sqlite3.connect(database) as db:
        db.executemany("INSERT OR REPLACE INTO tbl_event_types(event,event_descr,event_raw,event_type) VALUES (?,?,?,?)",
                       [("ROOT", "扫描目标", 0, "ENTITY"), ("EMAILADDR", "邮箱地址", 0, "ENTITY")])
        rows = [(root, "ROOT", "", root), (seed, "EMAILADDR", "SpiderFoot UI", root)]
        if external_match:
            rows.append((external, "EMAILADDR", "sfp_example", seed))
        for event, kind, module, source in rows:
            db.execute("INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash) VALUES (?,?,?,?,?,?,?)",
                       (ALICE, event, kind, 1760000000, module, "seed@example.invalid", source))
    try:
        results = client.get(url + "/scanresults", params={"id": ALICE}).json()["results"]
        assert seed not in {item["event_hash"] for item in results}
        assert (external in {item["event_hash"] for item in results}) is external_match
        summary = client.get(url + "/scansummary", params={"id": ALICE, "by": "type"}).json()
        email_rows = [row for row in summary if row[0] == "EMAILADDR"]
        assert [row[3] for row in email_rows] == ([1] if external_match else [])
        assert client.get(url + "/scanlist").json()[0][7] == baseline + int(external_match)
    finally:
        with sqlite3.connect(database) as db:
            db.execute("DELETE FROM tbl_scan_results WHERE hash IN (?,?,?)", (root, seed, external))


def test_non_ascii_csrf_is_forbidden_without_database_side_effects(alice, http_server):
    client, url = alice
    business_token(client, url)
    assert client.get(url + "/privacyactionlist").status_code == 200
    with sqlite3.connect(http_server[2]) as db:
        before = db.execute("SELECT COUNT(*) FROM privacy_actions").fetchone()[0]
    response = client.post(url + "/privacyactionsubmit", data={
        "action_type": "delete", "platform": "example.invalid", "content": "csrf-test@example.invalid",
        "csrf_token": "中文错误令牌",
    }, timeout=3)
    assert response.status_code == 403
    with sqlite3.connect(http_server[2]) as db:
        assert db.execute("SELECT COUNT(*) FROM privacy_actions").fetchone()[0] == before

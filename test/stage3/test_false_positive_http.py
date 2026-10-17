"""False-positive actions must persist only for owned, existing scan events."""
import json
import sqlite3
from uuid import uuid4

import pytest

from test.stage2.test_isolation_http import ALICE, BOB, alice, bob, business_token, http_server


@pytest.fixture
def event_row(http_server):
    scan_db = http_server[3]
    suffix = uuid4().hex
    parent = "stage3-root-" + suffix
    event = "stage3-event-" + suffix
    with sqlite3.connect(scan_db) as db:
        db.execute("INSERT OR REPLACE INTO tbl_event_types(event,event_descr,event_raw,event_type) VALUES (?,?,?,?)",
                   ("ROOT", "扫描目标", 0, "ENTITY"))
        db.execute("INSERT OR REPLACE INTO tbl_event_types(event,event_descr,event_raw,event_type) VALUES (?,?,?,?)",
                   ("STAGE3_FP_LINK", "公开页面链接", 0, "ENTITY"))
        db.execute("INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash) VALUES (?,?,?,?,?,?,?)",
                   (ALICE, parent, "ROOT", 1760000000, "SpiderFoot", "alice@example.invalid", parent))
        db.execute("INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash) VALUES (?,?,?,?,?,?,?)",
                   (ALICE, event, "STAGE3_FP_LINK", 1760000001, "sfp_example",
                    "https://example.org/" + suffix, parent))
    return scan_db, event


def fp_value(scan_db, event):
    with sqlite3.connect(scan_db) as db:
        return db.execute("SELECT false_positive FROM tbl_scan_results WHERE hash=?", (event,)).fetchone()[0]


def mark(client, url, event, *, scan_id=ALICE, token=None, method="POST"):
    payload = {"id": scan_id, "resultids": json.dumps([event]), "fp": "1"}
    headers = {"X-CSRF-Token": token} if token is not None else {}
    return client.request(method, url + "/resultsetfp", data=payload if method == "POST" else None,
                          params=payload if method == "GET" else None, headers=headers)


def test_mark_false_positive_changes_database_and_survives_fresh_result_read(alice, event_row):
    client, url = alice
    scan_db, event = event_row
    assert fp_value(scan_db, event) == 0

    response = mark(client, url, event, token=business_token(client, url))

    assert response.status_code == 200
    assert response.json()[0] == "SUCCESS"
    assert fp_value(scan_db, event) == 1
    reread = client.get(url + "/scanresults", params={"id": ALICE})
    assert reread.status_code == 200
    item = next(item for item in reread.json()["results"] if item["event_hash"] == event)
    assert item["status"] == "已标记误报"
    assert item["false_positive"] is True
    assert all(item["event_type"] != "ROOT" for item in reread.json()["results"])


def test_unknown_event_and_empty_batch_are_not_success(alice, event_row):
    client, url = alice
    scan_db, event = event_row
    token = business_token(client, url)
    unknown = mark(client, url, "missing-event-" + uuid4().hex, token=token)
    empty = client.post(url + "/resultsetfp", data={"id": ALICE, "resultids": "[]", "fp": "1"},
                        headers={"X-CSRF-Token": token})
    assert unknown.status_code in (400, 404)
    assert empty.status_code == 400
    assert fp_value(scan_db, event) == 0


def test_mixed_valid_and_unknown_batch_is_atomic(alice, event_row):
    client, url = alice
    scan_db, event = event_row
    response = client.post(url + "/resultsetfp", data={
        "id": ALICE, "resultids": json.dumps([event, "missing-event-" + uuid4().hex]), "fp": "1"
    }, headers={"X-CSRF-Token": business_token(client, url)})
    assert response.status_code == 404
    assert fp_value(scan_db, event) == 0


def test_root_event_cannot_be_marked_as_discovery(alice, event_row):
    client, url = alice
    scan_db, event = event_row
    with sqlite3.connect(scan_db) as db:
        root = db.execute("SELECT source_event_hash FROM tbl_scan_results WHERE hash=?", (event,)).fetchone()[0]
    response = mark(client, url, root, token=business_token(client, url))
    assert response.status_code == 404
    assert fp_value(scan_db, event) == 0


def test_valid_token_cannot_mark_another_users_scan(bob, event_row):
    client, url = bob
    scan_db, event = event_row
    response = mark(client, url, event, token=business_token(client, url))
    assert response.status_code == 404
    assert fp_value(scan_db, event) == 0


@pytest.mark.parametrize("token_kind", ["missing", "wrong", "other_session"])
def test_invalid_csrf_cannot_change_event(alice, bob, event_row, token_kind):
    client, url = alice
    other_client, _ = bob
    scan_db, event = event_row
    token = {"missing": None, "wrong": "invalid-stage3-token",
             "other_session": business_token(other_client, url)}[token_kind]
    response = mark(client, url, event, token=token)
    assert response.status_code == 403
    assert fp_value(scan_db, event) == 0


def test_get_request_cannot_mark_event(alice, event_row):
    client, url = alice
    scan_db, event = event_row
    response = mark(client, url, event, token=business_token(client, url), method="GET")
    assert response.status_code == 405
    assert fp_value(scan_db, event) == 0

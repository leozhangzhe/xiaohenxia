"""Phase 3 public HTTP contract for truthful, source-limited results."""
import sqlite3
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

from test.stage2.test_isolation_http import ALICE, BOB, alice, bob, http_server
from test.stage1.test_auth_http import form_token


def test_leak_page_and_empty_response_name_the_local_source_and_limit(alice, http_server):
    client, url = alice
    page = client.get(url + "/leakcheck")
    assert page.status_code == 200
    page.encoding = "utf-8"
    assert "本地 SQLite 合成样例库" in page.text
    assert "覆盖范围有限" in page.text
    assert "不是实时互联网查询" in page.text
    assert "当前数据源未发现匹配，不代表不存在相关信息。" in page.text
    assert "<h3" in page.text
    assert ">安全</h3>" not in page.text
    assert "background: rgba(34,197,94,0.1)" not in page.text

    response = client.post(url + "/leaksearch", data={"q": "no-match-stage3@example.invalid"})
    assert response.status_code == 200
    assert response.json()["found"] is False
    assert response.json()["message"] == "当前数据源未发现匹配，不代表不存在相关信息。"
    assert response.json()["data_source"] == "本地 SQLite 合成样例库"
    assert "覆盖范围有限" in response.json()["coverage"]
    assert "不是实时互联网查询" in response.json()["coverage"]


@pytest.fixture(scope="module")
def scan_evidence(http_server):
    scan_db = http_server[3]
    with sqlite3.connect(scan_db) as db:
        db.execute("INSERT OR REPLACE INTO tbl_event_types(event,event_descr,event_raw,event_type) VALUES (?,?,?,?)",
                   ("STAGE3_LINK", "公开页面链接", 0, "ENTITY"))
        db.execute("INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash) VALUES (?,?,?,?,?,?,?)",
                   (ALICE, "stage3-root", "ROOT", 1760000000, "SpiderFoot", "alice.private@example.org", "ROOT"))
        db.execute("INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash,confidence) VALUES (?,?,?,?,?,?,?,?)",
                   (ALICE, "stage3-link", "STAGE3_LINK", 1760000001, "sfp_example",
                    "https://example.org/profile/alice", "stage3-root", 75))
    return scan_db


def test_scan_results_show_existing_event_provenance_and_page_link(alice, scan_evidence):
    client, url = alice
    response = client.get(url + "/scanresults", params={"id": ALICE})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert body["data_source"] == "SpiderFoot 已保存扫描结果"
    assert "启用模块" in body["coverage"]
    item = next(item for item in body["results"] if item["original_url"] == "https://example.org/profile/alice")
    assert item["input_type"] == "邮箱"
    assert item["data_source"] == "SpiderFoot / sfp_example"
    assert item["title"] == "公开页面链接"
    assert item["data_value"] == "https://example.org/profile/alice"
    assert item["event_type"] == "STAGE3_LINK"
    assert item["event_hash"] == "stage3-link"
    assert item["source_module"] == "sfp_example"
    assert item["query_time"]
    assert item["time_note"] == "SpiderFoot 扫描记录时间，非实时查询"
    assert item["status"] == "待人工核验"
    assert "75" in item["confidence_note"]
    assert "误报" in item["false_positive_hint"]
    page = client.get(url + "/scaninfo", params={"id": ALICE})
    page.encoding = "utf-8"
    assert page.status_code == 200
    assert "统一结果" in page.text
    assert "spiderfoot.resultview.js" in page.text
    script = client.get(url + "/static/js/spiderfoot.resultview.js")
    assert script.status_code == 200
    assert "/scanresults?id=" in script.text


def test_real_scan_page_loads_jquery_before_initializing_results(alice):
    client, url = alice
    page = client.get(url + "/scaninfo", params={"id": ALICE})
    assert page.status_code == 200
    html = page.text
    jquery = html.index("/static/node_modules/jquery/dist/jquery.min.js")
    initializer = html.index("loadNormalizedScanResults(\"" + ALICE + "\")")
    assert jquery < initializer


def test_finished_scan_without_events_reports_no_match_not_safety(bob):
    client, url = bob
    response = client.get(url + "/scanresults", params={"id": BOB})
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert response.json()["message"] == "当前数据源未发现匹配，不代表不存在相关信息。"


def test_scan_seed_event_alone_is_not_reported_as_a_discovery(bob, scan_evidence):
    client, url = bob
    with sqlite3.connect(scan_evidence) as db:
        db.execute("INSERT OR REPLACE INTO tbl_event_types(event,event_descr,event_raw,event_type) VALUES (?,?,?,?)",
                   ("ROOT", "扫描目标", 0, "ENTITY"))
        db.execute("INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash) VALUES (?,?,?,?,?,?,?)",
                   (BOB, "stage3-bob-root", "ROOT", 1760000000, "SpiderFoot", "bob.private@example.org", "stage3-bob-root"))
    response = client.get(url + "/scanresults", params={"id": BOB})
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert response.json()["message"] == "当前数据源未发现匹配，不代表不存在相关信息。"


def test_aborted_scan_reports_partial_results(alice, scan_evidence):
    client, url = alice
    with sqlite3.connect(scan_evidence) as db:
        db.execute("UPDATE tbl_scan_instance SET status='ABORTED' WHERE guid=?", (ALICE,))
    try:
        response = client.get(url + "/scanresults", params={"id": ALICE})
        assert response.status_code == 200
        assert response.json()["status"] == "partial"
        assert response.json()["message"].startswith("部分完成")
        assert response.json()["results"]
    finally:
        with sqlite3.connect(scan_evidence) as db:
            db.execute("UPDATE tbl_scan_instance SET status='FINISHED' WHERE guid=?", (ALICE,))


def test_scan_storage_error_is_unavailable_not_empty(alice, scan_evidence):
    client, url = alice
    with sqlite3.connect(scan_evidence) as db:
        db.execute("ALTER TABLE tbl_event_types RENAME TO stage3_unavailable_event_types")
    try:
        response = client.get(url + "/scanresults", params={"id": ALICE})
        assert response.status_code == 503
        assert response.json()["status"] == "unavailable"
        assert response.json()["message"] == "数据源不可用"
    finally:
        with sqlite3.connect(scan_evidence) as db:
            db.execute("ALTER TABLE stage3_unavailable_event_types RENAME TO tbl_event_types")


def test_existing_local_leak_record_is_labelled_without_claiming_live_search(alice, http_server):
    client, url = alice
    leak_db = http_server[2].parent / "leak-check.sqlite"
    # The no-match request above initializes this isolated test database.
    client.get(url + "/leakcheck")
    with sqlite3.connect(leak_db) as db:
        db.execute("INSERT INTO source(id,source) VALUES (?,?)", (31, "test-import"))
        db.execute("INSERT INTO person(email,source_id) VALUES (?,?)",
                   ("stage3-found@example.invalid", 31))
    response = client.post(url + "/leaksearch", data={"q": "stage3-found@example.invalid"})
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["sources"] == ["test-import"]
    assert body["data_source"] == "本地 SQLite 合成样例库"
    assert "覆盖范围有限" in body["coverage"]
    assert "stage3-found@example.invalid" not in response.text


@pytest.fixture(params=["directory", "corrupt"])
def unavailable_leak_server(tmp_path, request):
    root = Path(__file__).resolve().parents[2]
    blocked_path = tmp_path / "leak-check.sqlite"
    if request.param == "directory":
        blocked_path.mkdir()
    else:
        blocked_path.write_bytes(b"not a SQLite database")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = os.environ.copy()
    env.update({
        "SF_AUTH_MYSQL_HOST": "127.0.0.1", "SF_AUTH_MYSQL_PORT": "3306",
        "SF_AUTH_MYSQL_USER": "stage3_boundary", "SF_AUTH_MYSQL_PASSWORD": "Boundary-Only-4387",
        "SF_AUTH_MYSQL_DATABASE": "stage3_auth_boundary", "SF_AUTH_ADMIN_USER": "admin",
        "SF_AUTH_ADMIN_PASS": "StageThree-Admin-4387", "SF_AUTH_ADMIN_RESET": "0",
        "SF_AUTH_COOKIE_SECURE": "0", "STAGE2_AUTH_DB": str(tmp_path / "auth.sqlite"),
        "STAGE2_SCAN_DB": str(tmp_path / "scans.sqlite"), "SF_LEAKCHECK_DB": str(blocked_path),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
    })
    for name in ("SPIDERFOOT_DATA", "SPIDERFOOT_CACHE", "SPIDERFOOT_LOGS"):
        directory = tmp_path / name.lower()
        directory.mkdir(exist_ok=True)
        env[name] = str(directory)
    log = tmp_path / "server.log"
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen([sys.executable, "-B", "-m", "test.stage2.http_runner", str(port)],
                                   cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT)
        url = f"http://127.0.0.1:{port}"
        try:
            with requests.Session() as client:
                client.trust_env = False
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        pytest.fail(log.read_text(encoding="utf-8"))
                    try:
                        if client.get(url + "/login", timeout=1).status_code == 200:
                            break
                    except requests.RequestException:
                        pass
                    time.sleep(0.1)
                else:
                    pytest.fail("Server not ready: " + log.read_text(encoding="utf-8"))
                token = form_token(client.get(url + "/login"))
                result = client.post(url + "/login", data={"username": "alice",
                    "password": "StageTwo-HTTP-Password-4387", **token}, allow_redirects=False)
                assert result.status_code == 302
                yield client, url
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


def test_unavailable_local_source_returns_explicit_status_on_page_and_api(unavailable_leak_server):
    client, url = unavailable_leak_server
    page = client.get(url + "/leakcheck")
    page.encoding = "utf-8"
    assert page.status_code == 503
    assert "数据源不可用" in page.text
    response = client.post(url + "/leaksearch", data={"q": "example@example.invalid"})
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert "数据源不可用" in response.json()["error"]


def test_existing_event_api_filters_marked_false_positives(alice, scan_evidence):
    client, url = alice
    with sqlite3.connect(scan_evidence) as db:
        db.execute("INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash,false_positive) VALUES (?,?,?,?,?,?,?,?)",
                   (ALICE, "stage3-false-positive", "STAGE3_LINK", 1760000002, "sfp_example",
                    "https://example.org/false-positive", "stage3-root", 1))
    response = client.get(url + "/scaneventresults", params={"id": ALICE, "filterfp": "1"})
    assert response.status_code == 200
    assert any("https://example.org/profile/alice" in str(row) for row in response.json())
    assert not any("https://example.org/false-positive" in str(row) for row in response.json())
    normalized = client.get(url + "/scanresults", params={"id": ALICE}).json()
    assert any(item["status"] == "已标记误报" for item in normalized["results"])


def test_scan_summary_does_not_claim_safety_from_zero_risks(bob):
    client, url = bob
    page = client.get(url + "/scaninfo", params={"id": BOB})
    page.encoding = "utf-8"
    assert page.status_code == 200
    assert "分数越高越安全" not in page.text
    script = client.get(url + "/static/js/spiderfoot.scaninfo.js")
    script.encoding = "utf-8"
    assert "分数越高越安全" not in script.text


def test_new_scan_results_route_keeps_existing_owner_boundary(alice):
    client, url = alice
    assert client.get(url + "/scanresults", params={"id": BOB}).status_code == 404


def test_scan_list_calls_have_no_extra_argument(alice):
    client, url = alice
    assert client.get(url + "/").status_code == 200
    assert client.get(url + "/scanlist").status_code == 200
    assert client.get(url + "/sysinfo").status_code == 200

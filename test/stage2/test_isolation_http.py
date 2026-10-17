"""Public HTTP behavior: every account sees only its own resources."""
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time

import pytest
import requests

from test.stage1.test_auth_http import form_token
from sfwebui import SpiderFootWebUi
import sfscan

ROOT = Path(__file__).resolve().parents[2]
ALICE = "a" * 32
BOB = "b" * 32
LEGACY = "c" * 32


@pytest.fixture(scope="module")
def http_server(tmp_path_factory):
    folder = tmp_path_factory.mktemp("stage2-http")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = os.environ.copy()
    env.update({
        "SF_AUTH_MYSQL_HOST": "127.0.0.1", "SF_AUTH_MYSQL_PORT": "3306",
        "SF_AUTH_MYSQL_USER": "stage2_boundary", "SF_AUTH_MYSQL_PASSWORD": "Boundary-Only-4387",
        "SF_AUTH_MYSQL_DATABASE": "stage2_auth_boundary",
        "SF_AUTH_ADMIN_USER": "admin", "SF_AUTH_ADMIN_PASS": "StageTwo-Admin-4387",
        "SF_AUTH_ADMIN_RESET": "0", "SF_AUTH_COOKIE_SECURE": "0",
        "STAGE2_AUTH_DB": str(folder / "auth.sqlite"), "STAGE2_SCAN_DB": str(folder / "scans.sqlite"),
        "SF_LEAKCHECK_DB": str(folder / "leak-check.sqlite"),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
    })
    for name in ("SPIDERFOOT_DATA", "SPIDERFOOT_CACHE", "SPIDERFOOT_LOGS"):
        directory = folder / name.lower()
        directory.mkdir()
        env[name] = str(directory)
    log = folder / "server.log"
    with log.open("w", encoding="utf-8") as output:
        process = subprocess.Popen([sys.executable, "-B", "-m", "test.stage2.http_runner", str(port)], cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
        url = f"http://127.0.0.1:{port}"
        try:
            deadline = time.monotonic() + 20
            with requests.Session() as probe:
                probe.trust_env = False
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        pytest.fail(log.read_text(encoding="utf-8"))
                    try:
                        if probe.get(url + "/login", timeout=1).status_code == 200:
                            break
                    except requests.RequestException:
                        pass
                    time.sleep(0.1)
                else:
                    pytest.fail("Server not ready: " + log.read_text(encoding="utf-8"))
            yield url, log, Path(env["STAGE2_AUTH_DB"]), Path(env["STAGE2_SCAN_DB"])
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


@pytest.fixture
def alice(http_server):
    url, _, _, _ = http_server
    with requests.Session() as client:
        client.trust_env = False
        token = form_token(client.get(url + "/login"))
        result = client.post(url + "/login", data={"username": "alice", "password": "StageTwo-HTTP-Password-4387", **token}, allow_redirects=False)
        assert result.status_code == 302
        yield client, url


@pytest.fixture
def bob(http_server):
    url, _, _, _ = http_server
    with requests.Session() as client:
        client.trust_env = False
        token = form_token(client.get(url + "/login"))
        result = client.post(url + "/login", data={"username": "bob", "password": "StageTwo-HTTP-Password-4387", **token}, allow_redirects=False)
        assert result.status_code == 302
        yield client, url


def business_token(client, url):
    response = client.get(url + "/csrf")
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_scan_list_contains_only_current_users_scans(alice):
    client, url = alice
    response = client.get(url + "/scanlist")
    assert response.status_code == 200
    assert [row[0] for row in response.json()] == [ALICE]
    assert response.json()[0][2] == "al***@example.org"


@pytest.mark.parametrize("route,params", [
    ("scaninfo", {}), ("scanstatus", {}), ("scanopts", {}),
    ("scanlog", {}), ("scanerrors", {}), ("scanhistory", {}),
    ("scansummary", {"by": "type"}), ("scancorrelations", {}),
    ("scaneventresults", {"eventType": "ALL"}),
    ("scaneventresultsunique", {"eventType": "ALL"}),
    ("scanelementtypediscovery", {"eventType": "ALL"}),
    ("scanexportlogs", {}), ("scancorrelationsexport", {}),
    ("scaneventresultexport", {"type": "ALL"}), ("scanviz", {}),
    ("clonescan", {}), ("rerunscan", {}), ("stopscan", {}),
    ("scandelete", {}), ("resultsetfp", {"resultids": "[]", "fp": "1"}),
    ("search", {"value": "private"}), ("scansearchresultexport", {"value": "private"}),
])
@pytest.mark.parametrize("sid", [BOB, LEGACY, "d" * 32])
def test_foreign_unknown_and_legacy_scan_ids_are_indistinguishable(alice, route, params, sid):
    client, url = alice
    response = client.post(url + "/" + route, data={"id": sid, **params},
                           headers={"X-CSRF-Token": business_token(client, url)}, allow_redirects=False)
    assert response.status_code == 404
    assert "bob.private" not in response.text


@pytest.mark.parametrize("route", ["scanexportjsonmulti", "scanvizmulti", "scaneventresultexportmulti", "rerunscanmulti"])
def test_batch_cannot_mix_own_and_foreign_scans(alice, route):
    client, url = alice
    response = client.post(url + "/" + route, data={"ids": ALICE + "," + BOB},
                           headers={"X-CSRF-Token": business_token(client, url)}, allow_redirects=False)
    assert response.status_code == 404


def test_sql_query_cannot_bypass_resource_ownership(alice):
    client, url = alice
    response = client.post(url + "/query", data={"query": "SELECT seed_target FROM tbl_scan_instance"})
    assert response.status_code == 403


def test_monitor_scan_count_is_scoped_to_current_user(alice):
    client, url = alice
    response = client.get(url + "/sysinfo")
    assert response.status_code == 200
    assert response.json()["total_scans"] == 1


def test_privacy_actions_are_persisted_with_immutable_user_id(alice, http_server):
    client, url = alice
    secret = "stage2-private-unique@example.invalid"
    response = client.post(url + "/privacyactionsubmit", data={
        "action_type": "delete", "platform": "example.invalid", "content": secret,
        "csrf_token": business_token(client, url),
    })
    assert response.status_code == 200
    action = response.json()
    assert action["success"]
    _, _, auth_db, scan_db = http_server
    with sqlite3.connect(auth_db) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(privacy_actions)")}
        assert "user_id" in columns
        row = db.execute("SELECT user_id, content FROM privacy_actions WHERE id=?", (action["id"],)).fetchone()
        legacy_owner = db.execute("SELECT user_id FROM privacy_actions WHERE id='legacy-action-id'").fetchone()[0]
    assert row == (2, secret)
    assert legacy_owner == 2
    assert secret not in str(client.get(url + "/privacyactionlist").json())
    with sqlite3.connect(scan_db) as db:
        scan_owner = db.execute("SELECT user_id FROM tbl_scan_instance WHERE guid=?", (ALICE,)).fetchone()[0]
        monitor_owner = db.execute("SELECT user_id FROM web_monitor_tasks WHERE scan_id=?", (ALICE,)).fetchone()[0]
        db.execute(
            "INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash) "
            "VALUES(?,?,?,?,?,?,?)",
            (ALICE, "stage2-event-hash", "ROOT", 1, "test", secret, "ROOT"),
        )
        db.execute(
            "INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash) "
            "VALUES(?,?,?,?,?,?,?)",
            (BOB, "stage2-bob-event-hash", "ROOT", 1, "test", "bob.private@example.org", "ROOT"),
        )
        result_owner = db.execute("SELECT user_id FROM tbl_scan_results WHERE hash=?", ("stage2-event-hash",)).fetchone()[0]
        bob_result_owner = db.execute("SELECT user_id FROM tbl_scan_results WHERE hash=?", ("stage2-bob-event-hash",)).fetchone()[0]
    assert (scan_owner, monitor_owner, result_owner, bob_result_owner) == (2, 2, 2, 3)


def test_privacy_list_and_delete_are_scoped_to_user_id(alice, bob):
    alice_client, url = alice
    bob_client, _ = bob
    created = alice_client.post(url + "/privacyactionsubmit", data={
        "action_type": "hide", "platform": "example.invalid", "content": "alice-only-private@example.invalid",
        "csrf_token": business_token(alice_client, url),
    }).json()
    assert created["success"]
    assert "尚未向平台提交" in created["note"]
    assert bob_client.get(url + "/privacyactionlist").json()["total"] == 0
    attempt = bob_client.post(url + "/privacyactiondelete", data={
        "action_id": created["id"], "csrf_token": business_token(bob_client, url),
    })
    assert attempt.status_code == 404
    own_list = alice_client.get(url + "/privacyactionlist").json()
    assert own_list["total"] == 3
    assert "alice-only-private@example.invalid" not in str(own_list)


def test_privacy_delete_rejects_get_requests(alice):
    client, url = alice
    response = client.get(url + "/privacyactiondelete?action_id=" + "a" * 36)
    assert response.status_code == 405


def test_sensitive_leak_search_is_post_only_and_not_echoed(alice, http_server):
    client, url = alice
    secret = "stage2-private-query-unique@example.invalid"
    response = client.get(url + "/leaksearch?q=" + secret)
    assert response.status_code in (405, 404)
    response = client.post(url + "/leaksearch", data={"q": secret})
    assert response.status_code == 200
    assert secret not in response.text
    _, log, _, _ = http_server
    assert secret not in log.read_text(encoding="utf-8")
    assert client.get(url + "/search?id=" + "a" * 32 + "&value=" + secret).status_code in (404, 405)


def test_leak_search_page_uses_post_without_sensitive_query_in_url(alice):
    client, url = alice
    response = client.get(url + "/leakcheck")
    assert response.status_code == 200
    assert "fetch(docroot + '/leaksearch', {" in response.text
    assert "method: 'POST'" in response.text
    assert "/leaksearch?q=" not in response.text


def test_login_redirect_does_not_copy_sensitive_get_query(http_server):
    url, _, _, _ = http_server
    with requests.Session() as observer:
        observer.trust_env = False
        secret = "stage2-redirect-private@example.invalid"
        for path in (
            "/leaksearch?q=", "/startscan?scantarget=", "/privacyactionsubmit?content=",
            "/riskactionupdate?note=", "/search?value=", "/scansearchresultexport?value=",
        ):
            response = observer.get(url + path + secret, allow_redirects=False)
            assert response.status_code == 302
            assert secret not in response.headers.get("Location", "")


def test_invalid_sensitive_query_returns_generic_error(alice, http_server):
    client, url = alice
    secret = "stage2-invalid-private@example.invalid<script>"
    response = client.post(url + "/leaksearch", data={"q": secret})
    assert response.status_code == 400
    assert secret not in response.text
    assert secret not in http_server[1].read_text(encoding="utf-8")


def test_foreign_risk_action_and_shared_server_logs_are_blocked(alice):
    client, url = alice
    response = client.post(url + "/riskactionupdate", data={"alertId": "foreign-alert", "status": "resolved"},
                           headers={"X-CSRF-Token": business_token(client, url)})
    assert response.status_code == 404
    assert client.get(url + "/serverlogs").status_code == 403


def test_scan_target_email_format_is_validated_without_echo(alice):
    client, url = alice
    secret = "invalid-address-private@"
    response = client.post(url + "/startscan", data={
        "scanname": "format check", "scantarget": secret,
        "modulelist": "sfp__stor_db",
        "csrf_token": business_token(client, url),
    }, headers={"Accept": "application/json"})
    assert response.status_code == 400
    assert secret not in response.text
    assert "Invalid target format" in response.text


@pytest.mark.parametrize("target,target_type,valid", [
    ("person@example.org", "EMAILADDR", True),
    ("invalid-address@", "EMAILADDR", False),
    ("example.org", "INTERNET_NAME", True),
    ("bad-.example", "INTERNET_NAME", False),
    ("alice_2026", "USERNAME", True),
    ("bad name", "USERNAME", False),
    ("<script>", "USERNAME", False),
])
def test_scan_target_validation_for_email_username_and_domain(target, target_type, valid):
    assert SpiderFootWebUi._scan_target_is_valid(target, target_type) is valid


def test_scanner_target_errors_do_not_log_or_echo_sensitive_value(monkeypatch):
    secret = "private-target@example.invalid"
    messages = []

    class FakeDb:
        def scanInstanceCreate(self, *_args):
            pass

        def scanInstanceSet(self, *_args, **_kwargs):
            pass

    class FakeSpiderFoot:
        def __init__(self, _config):
            self.dbh = None

        def status(self, message):
            messages.append(message)

    monkeypatch.setattr(sfscan, "SpiderFootDb", lambda _config: FakeDb())
    monkeypatch.setattr(sfscan, "SpiderFoot", FakeSpiderFoot)

    def invalid_target(value, _target_type):
        raise ValueError(f"invalid target {value}")

    monkeypatch.setattr(sfscan, "SpiderFootTarget", invalid_target)
    with pytest.raises(ValueError) as error:
        sfscan.SpiderFootScanner(
            "safe name", "scan-id", secret, "EMAILADDR", ["sfp__stor_db"], {"test": True}, start=False
        )
    assert str(error.value) == "Invalid target."
    assert all(secret not in message for message in messages)


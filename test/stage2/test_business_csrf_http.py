"""Real HTTP regression coverage for session-bound business CSRF controls."""
import sqlite3
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import secrets

import pytest
import requests

from test.stage1.test_auth_http import form_token
from test.stage2.test_isolation_http import ALICE, BOB, alice, bob, http_server
from test.stage1.live_mysql import LiveMySQL

ROOT = Path(__file__).resolve().parents[2]


PASSWORD = "StageTwo-HTTP-Password-4387"


def csrf_token(client, url):
    response = client.get(url + "/csrf")
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def privacy_count(database):
    with sqlite3.connect(database) as conn:
        return conn.execute("SELECT count(*) FROM privacy_actions").fetchone()[0]


def scan_task_snapshot(database):
    with sqlite3.connect(database) as conn:
        scans = conn.execute("SELECT guid,status FROM tbl_scan_instance ORDER BY guid").fetchall()
        monitors = conn.execute("SELECT scan_id,user_id FROM web_monitor_tasks ORDER BY scan_id").fetchall()
    return scans, monitors


@pytest.fixture
def admin(http_server):
    url, _, _, _ = http_server
    with requests.Session() as client:
        client.trust_env = False
        form = form_token(client.get(url + "/login"))
        response = client.post(url + "/login", data={
            "username": "admin", "password": "StageTwo-Admin-4387", **form,
        }, allow_redirects=False)
        assert response.status_code == 302
        yield client, url


def privacy_payload():
    return {"action_type": "hide", "platform": "example.invalid", "content": "csrf-probe@example.invalid"}


def test_missing_privacy_csrf_is_rejected_without_database_write(alice, http_server):
    client, url = alice
    before = privacy_count(http_server[2])
    response = client.post(url + "/privacyactionsubmit", data=privacy_payload())
    assert response.status_code in (400, 403)
    assert privacy_count(http_server[2]) == before


def test_wrong_privacy_csrf_is_rejected_without_database_write(alice, http_server):
    client, url = alice
    before = privacy_count(http_server[2])
    response = client.post(url + "/privacyactionsubmit", data={
        **privacy_payload(), "csrf_token": "wrong-session-token",
    })
    assert response.status_code in (400, 403)
    assert response.headers.get("X-CSRF-Error") == "1"
    assert privacy_count(http_server[2]) == before


def test_other_session_privacy_csrf_is_rejected_without_database_write(alice, bob, http_server):
    alice_client, url = alice
    bob_client, _ = bob
    token = csrf_token(bob_client, url)
    before = privacy_count(http_server[2])
    response = alice_client.post(url + "/privacyactionsubmit", data={
        **privacy_payload(), "csrf_token": token,
    })
    assert response.status_code in (400, 403)
    assert privacy_count(http_server[2]) == before


def test_privacy_csrf_in_url_is_rejected_without_database_write(alice, http_server):
    client, url = alice
    token = csrf_token(client, url)
    before = privacy_count(http_server[2])
    response = client.post(url + "/privacyactionsubmit?csrf_token=" + token, data=privacy_payload())
    assert response.status_code in (400, 403)
    assert response.headers.get("X-CSRF-Error") == "1"
    assert privacy_count(http_server[2]) == before


def test_valid_privacy_csrf_creates_exactly_one_user_owned_record(alice, http_server):
    client, url = alice
    token = csrf_token(client, url)
    before = privacy_count(http_server[2])
    response = client.post(url + "/privacyactionsubmit", data={
        **privacy_payload(), "csrf_token": token,
    })
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    assert privacy_count(http_server[2]) == before + 1


@pytest.mark.parametrize("route,params", [
    ("startscan", {"scanname": "x", "scantarget": "example.org", "modulelist": "sfp__stor_db"}),
    ("stopscan", {"id": ALICE}), ("scandelete", {"id": ALICE}),
    ("rerunscan", {"id": ALICE}), ("rerunscanmulti", {"ids": ALICE}),
    ("resultsetfp", {"id": ALICE, "resultids": "[]", "fp": "1"}),
    ("riskactionupdate", {"alertId": "known-risk", "status": "resolved"}),
    ("riskactionautofix", {"alertId": "known-risk"}),
    ("privacyactionsubmit", privacy_payload()),
    ("privacyactiondelete", {"action_id": "legacy-action-id"}),
    ("savesettings", {"allopts": "{}", "token": "0"}),
    ("savesettingsraw", {"allopts": "{}", "token": "0"}),
    ("vacuum", {}),
])
def test_business_write_route_inventory_is_post_only_and_csrf_protected(admin, http_server, route, params):
    client, url = admin
    before_scans, before_privacy = scan_task_snapshot(http_server[3]), privacy_count(http_server[2])
    get_response = client.get(url + "/" + route, params=params, allow_redirects=False)
    assert get_response.status_code == 405
    post_response = client.post(url + "/" + route, data=params, allow_redirects=False)
    assert post_response.status_code in (400, 403)
    assert scan_task_snapshot(http_server[3]) == before_scans
    assert privacy_count(http_server[2]) == before_privacy


def test_privacy_delete_foreign_owner_returns_not_found_and_does_not_delete(alice, bob, http_server):
    alice_client, url = alice
    bob_client, _ = bob
    created = alice_client.post(url + "/privacyactionsubmit", data={
        **privacy_payload(), "csrf_token": csrf_token(alice_client, url),
    }).json()
    before = privacy_count(http_server[2])
    attempt = bob_client.post(url + "/privacyactiondelete", data={
        "action_id": created["id"], "csrf_token": csrf_token(bob_client, url),
    })
    assert attempt.status_code in (403, 404), attempt.text
    assert privacy_count(http_server[2]) == before


def test_valid_csrf_cannot_delete_another_users_scan(alice, http_server):
    client, url = alice
    before = scan_task_snapshot(http_server[3])
    response = client.post(url + "/scandelete", data={
        "id": BOB, "csrf_token": csrf_token(client, url),
    }, allow_redirects=False)
    assert response.status_code == 404
    assert scan_task_snapshot(http_server[3]) == before


def test_write_pages_and_browser_transport_load_csrf_support(admin, alice):
    admin_client, url = admin
    user_client, _ = alice
    new_scan = user_client.get(url + "/newscan")
    settings = admin_client.get(url + "/opts")
    privacy = user_client.get(url + "/privacyaction")
    assert new_scan.status_code == settings.status_code == privacy.status_code == 200, settings.text[settings.text.find("<pre"):settings.text.find("</pre>") + 6]
    assert 'name="csrf_token"' in new_scan.text
    assert 'name="csrf_token"' in settings.text
    assert "csrf.js" in new_scan.text and "csrf.js" in settings.text
    csrf_script = user_client.get(url + "/static/js/csrf.js").content.decode("utf-8")
    assert "X-CSRF-Token" in csrf_script
    assert "安全令牌无效或已过期" in csrf_script


def test_anonymous_csrf_token_is_rotated_after_login(http_server):
    url, _, _, _ = http_server
    with requests.Session() as client:
        client.trust_env = False
        bootstrap = client.get(url + "/csrf")
        before = bootstrap.json()["csrf_token"]
        assert before not in bootstrap.url
        assert bootstrap.headers.get("Cache-Control") == "no-store"
        login_form = form_token(client.get(url + "/login"))
        response = client.post(url + "/login", data={
            "username": "alice", "password": PASSWORD, **login_form,
        }, allow_redirects=False)
        assert response.status_code == 302
        after = csrf_token(client, url)
        assert after != before
        rejected = client.post(url + "/privacyactionsubmit", data={
            **privacy_payload(), "csrf_token": before,
        })
        assert rejected.status_code in (400, 403)


def test_logout_invalidates_business_csrf_token(http_server):
    url, _, database, _ = http_server
    with requests.Session() as client:
        client.trust_env = False
        login_form = form_token(client.get(url + "/login"))
        logged_in = client.post(url + "/login", data={
            "username": "alice", "password": PASSWORD, **login_form,
        }, allow_redirects=False)
        assert logged_in.status_code == 302
        old_token = csrf_token(client, url)
        client.get(url + "/logout", allow_redirects=False)
        before = privacy_count(database)
        attempt = client.post(url + "/privacyactionsubmit", data={
            **privacy_payload(), "csrf_token": old_token,
        }, allow_redirects=False)
        assert attempt.status_code in (302, 400, 401, 403)
        assert privacy_count(database) == before


@pytest.fixture
def real_mysql_http_server(tmp_path):
    """Run the HTTP application against an isolated instance of real MySQL."""
    folder = tmp_path / ("csrf-real-mysql-" + secrets.token_hex(5))
    folder.mkdir(parents=True)
    mysql_folder = folder / "mysql"
    mysql_folder.mkdir()
    mysql = LiveMySQL(mysql_folder)
    try:
        mysql.initialize()
    except Exception:
        mysql.close()
        raise
    database = "csrf_" + secrets.token_hex(6)
    env = os.environ.copy()
    env.update({
        "STAGE2_REAL_MYSQL": "1",
        "SF_AUTH_MYSQL_HOST": "127.0.0.1", "SF_AUTH_MYSQL_PORT": str(mysql.port),
        "SF_AUTH_MYSQL_USER": "root", "SF_AUTH_MYSQL_PASSWORD": mysql.password,
        "SF_AUTH_MYSQL_DATABASE": database,
        "SF_AUTH_ADMIN_USER": "admin", "SF_AUTH_ADMIN_PASS": "Real-MySQL-CSRF-Admin-4387!",
        "SF_AUTH_ADMIN_RESET": "0", "SF_AUTH_COOKIE_SECURE": "0",
        "STAGE2_AUTH_DB": str(folder / "unused-auth.sqlite"),
        "STAGE2_SCAN_DB": str(folder / "scans.sqlite"),
        "SF_LEAKCHECK_DB": str(folder / "leak-check.sqlite"),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
    })
    for name in ("SPIDERFOOT_DATA", "SPIDERFOOT_CACHE", "SPIDERFOOT_LOGS"):
        directory = folder / name.lower()
        directory.mkdir()
        env[name] = str(directory)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    log = folder / "http-server.log"
    process = None
    try:
        with log.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(
                [sys.executable, "-B", "-m", "test.stage2.http_runner", str(port)],
                cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT,
            )
            url = "http://127.0.0.1:" + str(port)
            deadline = time.monotonic() + 25
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
                    pytest.fail("Real MySQL HTTP server did not start: " + log.read_text(encoding="utf-8"))
            yield url, mysql, database, log
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        mysql.close()


def test_csrf_privacy_submission_over_http_uses_real_mysql(real_mysql_http_server):
    url, mysql, database, _ = real_mysql_http_server
    with requests.Session() as client:
        client.trust_env = False
        auth = form_token(client.get(url + "/login"))
        login = client.post(url + "/login", data={
            "username": "alice", "password": PASSWORD, **auth,
        }, allow_redirects=False)
        assert login.status_code == 302

        def count_records():
            with mysql.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("USE `" + database + "`")
                    cursor.execute("SHOW TABLES LIKE 'privacy_actions'")
                    if not cursor.fetchone():
                        return 0
                    cursor.execute("SELECT COUNT(*) FROM privacy_actions")
                    return cursor.fetchone()[0]

        before = count_records()
        rejected = client.post(url + "/privacyactionsubmit", data=privacy_payload())
        assert rejected.status_code in (400, 403)
        assert count_records() == before

        token = csrf_token(client, url)
        accepted = client.post(url + "/privacyactionsubmit", data={
            **privacy_payload(), "csrf_token": token,
        })
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["success"] is True
        assert count_records() == before + 1


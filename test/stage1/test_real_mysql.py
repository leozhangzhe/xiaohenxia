"""Real MySQL cold restart and complete application startup checks."""
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import secrets

import pytest
import requests

from spiderfoot.auth_mysql import MySQLAuthStore
from test.stage1.live_mysql import LiveMySQL, ROOT
from test.stage1.test_auth_http import form_token


@pytest.fixture
def live_mysql(tmp_path, monkeypatch):
    folder = tmp_path / "real-mysql"
    folder.mkdir()
    server = LiveMySQL(folder)
    try:
        server.initialize()
        for name, value in {
            "SF_AUTH_MYSQL_HOST": "127.0.0.1", "SF_AUTH_MYSQL_PORT": str(server.port),
            "SF_AUTH_MYSQL_USER": "root", "SF_AUTH_MYSQL_PASSWORD": server.password,
            "SF_AUTH_MYSQL_DATABASE": "stage1_auth_test",
        }.items():
            monkeypatch.setenv(name, value)
        yield server
    finally:
        server.close()


def test_real_mysql_accounts_survive_database_and_application_restart(live_mysql, monkeypatch, tmp_path):
    password = "StageOne-Real-MySQL-4387"
    monkeypatch.setenv("SF_AUTH_ADMIN_PASS", password)
    auth = MySQLAuthStore(logging.getLogger("stage1.mysql"))
    auth.initialize()
    assert auth.create_user("  participant  ", password)
    assert auth.verify_user("participant", password)
    with live_mysql.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT password_hash FROM stage1_auth_test.users WHERE username=%s", ("participant",))
            encoded = cursor.fetchone()[0]
            assert encoded.startswith("pbkdf2_sha256$600000$") and password not in encoded
    live_mysql.stop()
    live_mysql.start()
    monkeypatch.delenv("SF_AUTH_ADMIN_PASS")
    restored = MySQLAuthStore(logging.getLogger("stage1.mysql"))
    restored.initialize()
    assert restored.verify_user("  participant  ", password)
    assert not restored.verify_user("admin", "admin123")

    check = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/auth_admin.py"), "--check"],
                           cwd=tmp_path, capture_output=True, timeout=15)
    assert check.returncode == 0, check.stderr.decode("utf-8", errors="replace")
    launcher_env = os.environ.copy()
    launcher_data = ROOT / ".stage2" / ("stage1-launcher-" + secrets.token_hex(5))
    launcher_env["SPIDERFOOT_DATA"] = str(launcher_data)
    launcher_env["SPIDERFOOT_LOGS"] = str(launcher_data / "logs")
    launcher_env["SPIDERFOOT_CACHE"] = str(launcher_data / "cache")
    for path in (launcher_data, launcher_data / "logs", launcher_data / "cache"):
        path.mkdir(parents=True)
    launcher = subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "scripts/start-local.ps1"), "-CheckOnly",
    ], cwd=ROOT, env=launcher_env, capture_output=True, timeout=20)
    assert launcher.returncode == 0, launcher.stderr.decode("utf-8", errors="replace")

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    logfile = tmp_path / "application.log"
    with logfile.open("w", encoding="utf-8") as output:
        process = subprocess.Popen([sys.executable, "-B", "sf.py", "-l", f"127.0.0.1:{port}"],
                                   cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
        client = requests.Session()
        client.trust_env = False
        url = f"http://127.0.0.1:{port}"
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail("Application startup failed; see " + str(logfile))
                try:
                    if client.get(url + "/login", timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(0.2)
            else:
                pytest.fail("Application startup timed out; see " + str(logfile))
            response = client.post(url + "/login", data={
                "username": "  participant  ", "password": password, "next": "/ping",
                **form_token(client.get(url + "/login")),
            }, allow_redirects=False)
            assert response.status_code == 302
            assert client.get(url + "/ping").status_code == 200
        finally:
            client.close()
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


def test_complete_application_refuses_to_start_when_mysql_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("SF_AUTH_MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("SF_AUTH_MYSQL_PORT", "1")
    monkeypatch.setenv("SF_AUTH_MYSQL_PASSWORD", "NeverPrint-Application-Test-Secret")
    result = subprocess.run([sys.executable, "-B", "sf.py", "-l", "127.0.0.1:59999"],
                            cwd=ROOT, capture_output=True, timeout=20)
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    (tmp_path / "unavailable-startup.log").write_text(output, encoding="utf-8")
    assert result.returncode != 0
    assert "authentication database" in output
    assert "NeverPrint-Application-Test-Secret" not in output

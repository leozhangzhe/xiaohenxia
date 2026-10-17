"""Black-box HTTP regression tests through sf.start_web_server."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

import pytest
import requests


ROOT = Path(__file__).resolve().parents[2]
ADMIN_PASSWORD = "StageOne-HTTP-Password-4387"


def form_token(response):
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    return {"csrf_token": match.group(1)} if match else {}


@pytest.fixture
def server_factory(tmp_path):
    counter = 0

    @contextmanager
    def run(extra_env=None):
        nonlocal counter
        counter += 1
        folder = tmp_path / f"http-{counter}"
        folder.mkdir()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        env = os.environ.copy()
        env.update({
            "SF_AUTH_ADMIN_USER": "admin", "SF_AUTH_ADMIN_PASS": ADMIN_PASSWORD,
            "SF_AUTH_ADMIN_RESET": "0", "PYTHONDONTWRITEBYTECODE": "1",
            "SF_AUTH_COOKIE_SECURE": "0",
            "STAGE1_BOUNDARY_DB": str(folder / "auth.sqlite"),
            "STAGE1_SCAN_DB": str(folder / "scans.sqlite"),
            "STAGE1_OUTAGE_MARKER": str(folder / "outage"),
        })
        env.update(extra_env or {})
        logfile = folder / "server.log"
        with logfile.open("w", encoding="utf-8") as output:
            process = subprocess.Popen(
                [sys.executable, "-B", "-m", "test.stage1.http_runner", str(port)],
                cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT,
            )
            client = requests.Session()
            client.trust_env = False
            url = f"http://127.0.0.1:{port}"
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        pytest.fail("HTTP server exited:\n" + logfile.read_text(encoding="utf-8"))
                    try:
                        if client.get(url + "/login", timeout=1).status_code == 200:
                            break
                    except requests.RequestException:
                        pass
                    time.sleep(0.1)
                else:
                    pytest.fail("HTTP startup timed out:\n" + logfile.read_text(encoding="utf-8"))
                yield client, url, Path(env["STAGE1_OUTAGE_MARKER"])
            finally:
                client.close()
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)

    return run


@pytest.mark.parametrize("route", ["login", "register"])
def test_auth_database_outage_returns_503_without_fake_success(server_factory, route):
    with server_factory() as (client, url, outage):
        token = form_token(client.get(url + "/" + route))
        outage.touch()
        data = {
            "username": "participant", "password": "Participant-HTTP-4387",
            **token,
        }
        if route == "register":
            data["confirm"] = data["password"]
        response = client.post(url + "/" + route, data=data, allow_redirects=False)
        assert response.status_code == 503
        assert "认证数据库暂不可用" in response.text
        assert client.get(url + "/ping", allow_redirects=False).status_code == 302


def login(client, url, username="admin", password=ADMIN_PASSWORD, next_url="/ping"):
    token = form_token(client.get(url + "/login"))
    return client.post(url + "/login", data={
        "username": username, "password": password, "next": next_url, **token,
    }, allow_redirects=False)


def test_successful_login_rotates_session_and_logout_revokes_it(server_factory):
    with server_factory() as (client, url, outage):
        client.get(url + "/login")
        anonymous = client.cookies.get("session_id")
        response = login(client, url, "  admin  ")
        assert response.status_code == 302
        authenticated = client.cookies.get("session_id")
        assert authenticated != anonymous
        assert client.get(url + "/ping").status_code == 200
        with requests.Session() as observer:
            observer.trust_env = False
            stale = observer.get(url + "/ping", headers={"Cookie": f"session_id={anonymous}"}, allow_redirects=False)
            assert stale.status_code == 302
        client.get(url + "/logout", allow_redirects=False)
        replay = client.get(url + "/ping", headers={"Cookie": f"session_id={authenticated}"}, allow_redirects=False)
        assert replay.status_code == 302


def test_session_cookie_and_auth_pages_have_security_attributes(server_factory):
    with server_factory() as (client, url, outage):
        response = client.get(url + "/login")
        cookie = response.headers["Set-Cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=Lax" in cookie
        assert "Max-Age" not in cookie
        assert response.headers["Cache-Control"] == "no-store"


def test_secure_cookie_can_be_enabled_for_https_deployments(server_factory):
    with server_factory({"SF_AUTH_COOKIE_SECURE": "1"}) as (client, url, outage):
        assert "Secure" in client.get(url + "/login").headers["Set-Cookie"]


def test_failed_login_remains_unauthenticated_after_logout(server_factory):
    with server_factory() as (client, url, outage):
        assert login(client, url).status_code == 302
        client.get(url + "/logout", allow_redirects=False)
        response = login(client, url, password="wrong-password")
        assert response.status_code == 200
        assert client.get(url + "/ping", allow_redirects=False).status_code == 302


def test_authenticated_session_has_an_absolute_expiry(server_factory):
    with server_factory({"SF_AUTH_SESSION_MAX_AGE_SECONDS": "1"}) as (client, url, outage):
        assert login(client, url).status_code == 302
        time.sleep(1.1)
        assert client.get(url + "/ping", allow_redirects=False).status_code == 302


def test_login_cannot_redirect_to_a_backslash_external_url(server_factory):
    with server_factory() as (client, url, outage):
        response = login(client, url, next_url="/\\example.invalid/path")
        assert response.status_code == 302
        assert response.headers["Location"] == url + "/"


def test_registration_and_login_agree_about_username_whitespace(server_factory):
    with server_factory() as (client, url, outage):
        token = form_token(client.get(url + "/register"))
        response = client.post(url + "/register", data={
            "username": "  participant  ", "password": "Participant-HTTP-4387",
            "confirm": "Participant-HTTP-4387", **token,
        })
        assert response.status_code == 200 and "注册成功" in response.text
        assert login(client, url, " participant ", "Participant-HTTP-4387").status_code == 302
        assert client.get(url + "/ping").status_code == 200


def test_redirect_parameter_cannot_inject_html_into_the_login_form(server_factory):
    with server_factory() as (client, url, outage):
        response = client.get(url + "/login", params={"next": '/"><img src=x onerror=alert(1)>'})
        assert '<img src=x onerror=alert(1)>' not in response.text


@pytest.mark.parametrize("route", ["login", "register"])
@pytest.mark.parametrize("token", [None, "invalid-test-token", pytest.param("非法令牌", id="non-ascii")])
def test_auth_forms_reject_missing_or_wrong_csrf_tokens(server_factory, route, token):
    with server_factory() as (client, url, outage):
        data = {"username": "admin", "password": ADMIN_PASSWORD}
        if route == "register":
            data.update(username="participant", confirm=ADMIN_PASSWORD)
        if token is not None:
            data["csrf_token"] = token
        response = client.post(url + "/" + route, data=data, allow_redirects=False)
        assert response.status_code == 403
        assert client.get(url + "/ping", allow_redirects=False).status_code == 302

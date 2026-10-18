from html.parser import HTMLParser
from pathlib import Path

import pytest
import requests

from test.stage1.test_auth_http import form_token
from test.stage2.test_isolation_http import alice


class AuthPage(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.bootstrap = {}
        self.assets = []
        self.forms = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if data.get("id") == "auth-root":
            self.bootstrap = data
        if tag == "script" and data.get("src"):
            self.assets.append(data["src"])
        if tag == "link" and data.get("rel") == "stylesheet":
            self.assets.append(data["href"])
        if tag == "form":
            self.forms.append(data)


@pytest.mark.parametrize("mode", ["login", "register"])
def test_react_bootstrap_has_session_form_token_and_all_local_built_assets(http_server, mode):
    url = http_server[0]
    client = requests.Session()
    client.trust_env = False
    page = client.get(url + "/" + mode)
    assert page.status_code == 200
    parsed = AuthPage(page.text)
    assert parsed.bootstrap["data-mode"] == mode
    assert parsed.bootstrap["data-csrf-token"] == form_token(page)["csrf_token"]
    assert parsed.forms[0]["method"] == "post"
    assert parsed.forms[0]["action"] == "/" + mode
    assert parsed.assets and all(p.startswith("/static/") for p in parsed.assets)
    for asset in parsed.assets:
        response = client.get(url + asset)
        assert response.status_code == 200
        assert len(response.content) > 100
    assert page.headers["Cache-Control"] == "no-store"


def test_real_registration_response_and_session_rotation_feed_react_bootstrap(http_server):
    url = http_server[0]
    client = requests.Session()
    client.trust_env = False
    page = client.get(url + "/register")
    before = client.cookies.get("session_id")
    payload = {"username":"synthetic_stage6", "password":"Synthetic-Stage6!2026", "confirm":"Synthetic-Stage6!2026", **form_token(page)}
    invalid = client.post(url + "/register", data={**payload, "csrf_token":"中文错误令牌"})
    assert invalid.status_code == 403
    registered = client.post(url + "/register", data=payload)
    assert registered.status_code == 200
    assert AuthPage(registered.text).bootstrap["data-success"] == "注册成功，请返回登录。"
    assert client.get(url + "/livelist", allow_redirects=False).status_code == 302
    page = client.get(url + "/login")
    failed = client.post(url + "/login", data={"username":payload["username"], "password":"wrong", **form_token(page)})
    assert AuthPage(failed.text).bootstrap["data-error"] == "用户名或密码错误。"
    assert not AuthPage(failed.text).bootstrap["data-success"]
    login = client.post(url + "/login", data={"username":" synthetic_stage6 ", "password":payload["password"], **form_token(failed)}, allow_redirects=False)
    assert login.status_code == 302
    assert client.cookies.get("session_id") != before
    assert client.get(url + "/livelist").status_code == 200
    assert client.get(url + "/livelist").status_code == 200  # refresh retains server session
    client.get(url + "/logout", allow_redirects=False)
    assert client.get(url + "/livelist", allow_redirects=False).status_code == 302


@pytest.mark.parametrize("route", ["/", "/livesearch", "/privacyaction", "/newscan", "/leakcheck", "/riskalertspage", "/dataviz", "/servicemonitor", "/opts"])
def test_business_pages_share_tokens_and_keep_original_routes(alice, route):
    client, url = alice
    response = client.get(url + route)
    if route == "/opts":
        assert response.status_code == 403  # same administrator-only boundary
        return
    assert response.status_code == 200
    assets = AuthPage(response.text).assets
    assert any("css/theme.css" in p for p in assets)
    assert any("css/workspace.css" in p for p in assets)


def test_auth_build_has_no_remote_runtime_assets_and_does_not_bundle_old_demo():
    root = Path(__file__).resolve().parents[2]
    code = (root / "spiderfoot/static/react-auth/auth.js").read_text(encoding="utf-8")
    assert "cdn.21st.dev" not in code
    assert "Demo complete. No account was created." not in code
    assert "Signing you up..." not in code
    assert "http://127.0.0.1:5001/login" in code  # developer-only entry hint, never a fetch
    css = (root / "spiderfoot/static/react-auth/auth.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css
    assert "--background:#121212" in css.replace(" ", "")

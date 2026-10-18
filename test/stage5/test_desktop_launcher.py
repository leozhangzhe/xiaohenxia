"""Local launcher's safety/persistence contract; no existing MySQL instance is touched."""
import importlib.util
import json
import os
from pathlib import Path
import re
import uuid

import pytest
import requests

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("desktop_launcher", ROOT / "scripts/start-desktop.py")
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


def test_desktop_refuses_data_outside_local_profile():
    with pytest.raises(desktop.LaunchError, match="runtime-profile"):
        desktop.DesktopServer(ROOT / "not-a-runtime-profile")


def test_missing_configuration_never_reinitializes_existing_database():
    profile = ROOT / ".runtime-profile" / ("launcher-preserve-" + uuid.uuid4().hex)
    data = profile / "mysql/data"
    data.mkdir(parents=True)
    marker = data / "original-marker"
    marker.write_text("preserve", encoding="utf-8")
    server = desktop.DesktopServer(profile)
    with pytest.raises(desktop.LaunchError, match="缺少加密"):
        server.start(lambda: pytest.fail("must reject before prompting or initializing"))
    assert marker.read_text(encoding="utf-8") == "preserve"
    assert not (profile / "connection.dpapi").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI")
def test_desktop_configuration_is_encrypted_and_corruption_fails_closed():
    profile = ROOT / ".runtime-profile" / ("launcher-crypto-" + uuid.uuid4().hex)
    profile.mkdir(parents=True)
    config = {"version": 1, "port": 54321, "password": "Synthetic-Config-Only!"}
    raw = desktop.crypt(json.dumps(config).encode())
    assert config["password"].encode() not in raw
    path = profile / "connection.dpapi"
    path.write_bytes(raw)
    assert desktop.load_config(profile) == config
    path.write_bytes(b"corrupt")
    with pytest.raises(desktop.LaunchError):
        desktop.load_config(profile)


@pytest.mark.skipif(os.name != "nt", reason="Bundled Windows MySQL")
def test_real_desktop_cold_restart_keeps_accounts_and_uses_same_database():
    profile = ROOT / ".runtime-profile" / ("launcher-restart-" + uuid.uuid4().hex)
    port = desktop.free_port()
    saved = None
    for iteration in range(2):
        server = desktop.DesktopServer(profile, port)
        try:
            def password_provider():
                assert iteration == 0, "restart must not prompt for or reset the administrator"
                return "Synthetic-Admin-Launcher!2026"
            server.start(password_provider)
            server.start_web()
            config = (profile / "connection.dpapi").read_bytes()
            if saved is not None:
                assert config == saved
            saved = config
            client = requests.Session()
            client.trust_env = False
            base = "http://127.0.0.1:" + str(port)
            if iteration == 0:
                page = client.get(base + "/register")
                token = re.search(r'name="csrf_token" value="([^"]+)"', page.text)[1]
                response = client.post(base + "/register", data={"csrf_token": token, "username": "synthetic_persistent", "password": "Synthetic-User-Only!2026", "confirm": "Synthetic-User-Only!2026"})
                assert response.status_code == 200
                assert "注册成功" in response.text
            page = client.get(base + "/login")
            token = re.search(r'name="csrf_token" value="([^"]+)"', page.text)[1]
            response = client.post(base + "/login", data={"csrf_token": token, "username": "synthetic_persistent", "password": "Synthetic-User-Only!2026"}, allow_redirects=False)
            assert response.status_code in (302, 303)
            assert client.get(base + "/").status_code == 200
        finally:
            server.close()
        assert server.web is None or server.web.poll() is not None
        assert server.mysql is None or server.mysql.poll() is not None
    logs = (profile / "web.log").read_text(encoding="utf-8")
    assert "Synthetic-Admin-Launcher!2026" not in logs
    assert "Synthetic-User-Only!2026" not in logs

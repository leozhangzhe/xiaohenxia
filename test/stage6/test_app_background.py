"""Controlled GPU/DOM lifecycle tests and real authenticated HTTP asset checks."""
from pathlib import Path
import subprocess

import pytest
import requests

from test.stage2.test_isolation_http import alice

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("case", ["lifecycle", "reduced", "fallback", "pause", "singleton", "mobile", "pixels", "adaptive", "pagehide", "nonblocking"])
def test_background_lifecycle(case):
    result = subprocess.run(["node", str(Path(__file__).with_name("background_runner.cjs")), case],
                            cwd=ROOT, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("route", ["/login", "/register", "/", "/livesearch", "/privacyaction", "/newscan"])
def test_shared_local_background_assets_and_no_duplicate_template_host(alice, route):
    client, base = alice
    if route in ["/login", "/register"]:
        # An authenticated session redirects these pages to the workspace. Inspect
        # the actual public auth page, not that redirect's unrelated HTML.
        with requests.Session() as anonymous:
            anonymous.trust_env = False
            page = anonymous.get(base + route)
        assert 'id="auth-root"' in page.text
    else:
        page = client.get(base + route)
    assert page.status_code == 200
    if route in ["/login", "/register"]:
        assert "/static/js/app-background.js" not in page.text
        assert "/static/vendor/liquid-metal/" not in page.text
        assert "/static/css/app-background.css" not in page.text
        assert "/static/react-auth/auth.js" in page.text
        return
    for asset in ["/static/vendor/liquid-metal/liquid-metal.js", "/static/js/app-background.js", "/static/css/app-background.css"]:
        assert page.text.count(asset) == 1
        response = client.get(base + asset)
        assert response.status_code == 200
        assert len(response.content) > 100
    assert page.text.count('data-app-background="workspace"') == 1


def test_shader_identity_license_and_no_remote_dependencies():
    vendor = ROOT / "spiderfoot/static/vendor/liquid-metal"
    import hashlib
    import json
    provenance = json.loads((vendor / "source-identity.json").read_text(encoding="utf-8"))
    # Preserved raw GLSL agrees with the supplied archive's identity; no textures/CDN.
    for suffix, key in [("vert", "vertexShaderSha256"), ("frag", "fragmentShaderSha256")]:
        source = (vendor / ("liquid-metal." + suffix)).read_text(encoding="utf-8")
        assert hashlib.sha256(source.encode()).hexdigest() == provenance[key]
    assert "MIT License" in (vendor / "LICENSE").read_text()
    engine = (ROOT / "spiderfoot/static/js/app-background.js").read_text(encoding="utf-8")
    assert "fetch(" not in engine and "https://" not in engine
    assert "preventDefault" not in engine.split("'pointermove'")[1].split("this.listen(win.document")[0]

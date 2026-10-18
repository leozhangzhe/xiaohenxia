"""Motion public boundaries: lifecycle, actual API state, form and local assets."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest
from test.stage2.test_isolation_http import alice
from test.stage5.test_fluent_interface import Assets


@pytest.mark.parametrize("case", ["lifecycle", "adaptive", "refreshCap", "offscreen", "realStates", "reduced", "form"])
def test_motion_runtime_boundaries(case):
    run = subprocess.run(
        [shutil.which("node"), str(Path(__file__).with_name("vault_motion_runner.js")), case],
        capture_output=True, text=True, encoding="utf-8", timeout=15,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["case"] == case


def test_motion_enhancement_uses_local_assets_and_preserves_real_forms(alice):
    client, url = alice
    import requests
    public = requests.Session()
    public.trust_env = False
    for session, route in [(public,"/login"),(public,"/register"),(client,"/"),(client,"/livesearch"),(client,"/privacyaction")]:
        response = session.get(url + route)
        assert response.status_code == 200
        page = response.content.decode("utf-8")
        assets = Assets()
        assets.feed(page)
        assert all(p.startswith("/") and not p.startswith("//") for p in assets.paths)
        if route not in ("/login", "/register"):
            assert any("vault-motion.js" in p for p in assets.paths)
        for asset in assets.paths:
            assert session.get(url + asset).status_code == 200
        if route in ("/login", "/register"):
            assert 'method="post"' in page and 'name="csrf_token"' in page
            # Stage 6 deliberately replaces the decorative auth Canvas with React.
            # Preserve this test's local-assets, real-form and no-JS usability boundary.
            assert any("react-auth/auth.js" in p for p in assets.paths)
            assert 'class="auth-fallback"' in page and '<label for="password">' in page
    assert public.post(url + "/register", data={"username":"synthetic_motion"}).status_code == 403


def test_motion_layer_cannot_fetch_or_inject_html():
    root = Path(__file__).resolve().parents[2]
    for filename in ("vault-scene.js", "vault-motion.js"):
        code = (root / "spiderfoot/static/js" / filename).read_text(encoding="utf-8")
        # Supplemental architectural guard; runtime cases above validate behavior.
        assert "fetch(" not in code and "XMLHttpRequest" not in code
        assert ".innerHTML" not in code
        assert "setTimeout(" not in code and "setInterval(" not in code

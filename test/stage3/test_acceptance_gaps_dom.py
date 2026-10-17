"""Behavior tests for scan-list and dashboard failure handling."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from test.stage2.test_isolation_http import alice, http_server


def run_dom(**scenario):
    node = shutil.which("node")
    assert node, "Node.js is required for browser-facing regression tests"
    runner = Path(__file__).with_name("acceptance_gaps_dom_runner.js")
    result = subprocess.run([node, str(runner)], input=json.dumps(scenario), text=True,
                            encoding="utf-8", capture_output=True, check=True, timeout=10)
    return json.loads(result.stdout)


@pytest.mark.parametrize("kind", ["scanlist", "scaninfo"])
def test_scan_list_html_404_is_an_error_not_a_login_redirect(kind):
    shown = run_dom(kind=kind, status=404)
    assert shown["href"] == "unchanged"
    if kind == "scanlist":
        assert shown["errors"]


@pytest.mark.parametrize("failed,failure", [
    ("/scanlist", "http"), ("/riskalerts", "http"),
    ("/riskalerts", "json"), ("/scanlist", "network"),
    ("/riskalerts", "shape"),
])
def test_dashboard_upstream_fault_is_unavailable_not_zero(alice, failed, failure):
    client, url = alice
    page = client.get(url + "/dataviz")
    assert page.status_code == 200
    page.encoding = "utf-8"
    shown = run_dom(kind="dashboard", html=page.text, failed=failed, failure=failure)
    for element in ("dv-total-scans", "dv-total-events", "dv-high-risk", "dv-privacy-score",
                    "dv-scan-chart", "dv-donut-area", "dv-risk-bars", "dv-alert-chart"):
        assert "数据不可用" in shown[element]

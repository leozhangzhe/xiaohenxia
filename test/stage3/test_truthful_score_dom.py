"""The dashboard must not infer comprehensive safety from alert counts."""
import json
import shutil
import subprocess
from pathlib import Path

from test.stage2.test_isolation_http import alice, http_server


RUNNER = Path(__file__).with_name("score_dom_runner.js")


def test_dashboard_avoids_unsupported_perfect_score_for_no_or_low_alerts(alice):
    client, url = alice
    page = client.get(url + "/dataviz")
    assert page.status_code == 200
    page.encoding = "utf-8"
    node = shutil.which("node")
    assert node, "Node.js is required for browser-facing DOM regression tests"
    process = subprocess.run([node, str(RUNNER)], input=page.text, text=True,
                             encoding="utf-8", capture_output=True, check=True, timeout=10)
    shown = json.loads(process.stdout)
    assert shown["empty"] == "暂无足够数据"
    assert shown["lowOnly"] == "暂无足够数据"
    assert "覆盖范围有限" in page.text
    assert "不提供综合安全评分" in page.text
    assert "当前告警数" in page.text

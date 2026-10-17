"""The default scan summary subview must stop loading when its API fails."""
import json
import shutil
import subprocess
from pathlib import Path


def test_summary_api_failure_replaces_spinner_with_error():
    node = shutil.which("node")
    assert node, "Node.js is required for browser-facing DOM regression tests"
    runner = Path(__file__).with_name("summary_failure_dom_runner.js")
    result = subprocess.run([node, str(runner)], text=True, encoding="utf-8",
                            capture_output=True, check=True, timeout=10)
    shown = json.loads(result.stdout)
    assert shown["section"] == "btn-status"
    assert shown["statusLoaded"] is True
    assert "数据源不可用" in shown["summaryText"]

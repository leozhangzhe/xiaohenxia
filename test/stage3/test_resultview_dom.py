"""Rendered DOM behavior backed by real HTTP result payloads."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from test.stage2.test_isolation_http import ALICE, BOB, alice, bob, http_server
from test.stage3.test_truthful_results_http import scan_evidence


RUNNER = Path(__file__).with_name("resultview_dom_runner.js")


def render(body, status=200, **options):
    node = shutil.which("node")
    assert node, "Node.js is required for browser-facing DOM regression tests"
    process = subprocess.run([node, str(RUNNER)], input=json.dumps({
        "body": body, "httpStatus": status, **options
    }), text=True, encoding="utf-8", capture_output=True, check=True, timeout=10)
    return json.loads(process.stdout)


def test_normal_result_ends_loading_and_maps_each_named_field(alice, scan_evidence):
    client, url = alice
    response = client.get(url + "/scanresults", params={"id": ALICE})
    assert response.status_code == 200
    shown = render(response.json(), response.status_code)

    assert shown["loaderGone"] is True
    assert shown["requested"] == ["/scanresults?id=" + ALICE]
    assert len(shown["rows"]) == 1
    cells = dict(zip(shown["headers"], shown["rows"][0]))
    assert cells["输入类型"] == "邮箱"
    assert cells["数据类型"] == "STAGE3_LINK"
    assert cells["数据值"] == "https://example.org/profile/alice"
    assert cells["数据源"] == "SpiderFoot / sfp_example"
    assert cells["扫描记录时间"] == "2025-10-09 16:53:21"
    assert cells["结果状态"] == "待人工核验"
    assert "75/100" in cells["可信程度说明"]
    assert shown["links"] == [{"href": "https://example.org/profile/alice", "text": "查看原始链接"}]


def test_selectable_browse_rows_use_event_hash_and_exclude_root(alice, scan_evidence):
    client, url = alice
    response = client.get(url + "/scanresults", params={"id": ALICE})
    assert response.status_code == 200
    shown = render(response.json(), response.status_code, selectable=True)
    assert shown["checkboxIds"] == ["checkall", "cb_stage3-link"]
    assert len(shown["rows"]) == 1
    cells = dict(zip(shown["headers"][1:], shown["rows"][0][1:]))
    assert cells["数据类型"] == "STAGE3_LINK"
    assert cells["数据值"] == "https://example.org/profile/alice"
    assert cells["数据源"] == "SpiderFoot / sfp_example"


def test_no_results_ends_loading_with_coverage_warning(bob):
    client, url = bob
    response = client.get(url + "/scanresults", params={"id": BOB})
    shown = render(response.json(), response.status_code)
    assert shown["loaderGone"] is True
    assert shown["rows"] == []
    assert "当前数据源未发现匹配，不代表不存在相关信息。" in shown["text"]


@pytest.mark.parametrize("scenario", [
    {"httpStatus": 503, "body": {"status": "unavailable", "results": []}},
    {"httpStatus": 500, "body": {"status": "complete", "results": [{"data_value": "wrong"}]}},
    {"httpStatus": 200, "body": {}, "badJson": True},
    {"httpStatus": 200, "body": {}, "reject": True},
])
def test_failed_request_ends_loading_with_error(scenario):
    shown = render(scenario["body"], scenario["httpStatus"],
                   badJson=scenario.get("badJson", False), reject=scenario.get("reject", False))
    assert shown["loaderGone"] is True
    assert "数据源不可用" in shown["text"]
    assert shown["rows"] == []


def test_partial_result_ends_loading_and_explains_incompleteness():
    shown = render({"status": "partial", "message": "部分完成：扫描未正常结束。", "results": []})
    assert shown["loaderGone"] is True
    assert "部分完成" in shown["text"]


def test_result_fields_are_text_not_executable_html():
    item = {"input_type": "邮箱", "event_type": "STAGE3_LINK", "data_value": "<img src=x onerror=alert(1)>",
            "data_source": "<script>unsafe</script>", "source_module": "test", "title": "<b>unsafe</b>",
            "original_url": "javascript:alert(1)", "query_time": "2025-10-09 16:53:21",
            "status": "待人工核验", "confidence_note": "未独立核验", "false_positive_hint": "需人工核验"}
    shown = render({"status": "complete", "results": [item]})
    assert shown["loaderGone"] is True
    assert shown["htmlWrites"] == 0
    assert shown["links"] == []
    assert "<img src=x onerror=alert(1)>" in shown["text"]

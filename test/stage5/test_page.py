import json
from pathlib import Path
import shutil
import subprocess
import pytest


def render(task, **filters):
    result=subprocess.run([shutil.which("node"),str(Path(__file__).with_name("live_dom_runner.js"))],
        input=json.dumps({"task":task,**filters}),text=True,encoding="utf-8",capture_output=True,check=True,timeout=10)
    return json.loads(result.stdout)


def test_untrusted_evidence_is_text_and_filters_keep_field_mappings():
    rows=[{"source":"holehe","input_type":"email","result_type":"email_registration_signal",
           "title":"<img onerror=alert(1)>","value":"邮箱可能注册过相关网站", "original_url":"javascript:alert(1)",
           "queried_at":1700000000,"confidence":"规则信号", "limitations":"不是泄露记录", "status":"待人工核验", "raw_summary":"<script>bad</script>"},
          {"source":"sherlock","result_type":"username_profile","title":"Other site","value":"Evidence","original_url":"https://example.org/profile"}]
    task={"status":"partial","sources":[{"source":"maigret","status":"failed"}],"results":rows}
    shown=render(task)
    assert shown["htmlWrites"]==0 and shown["cards"]==2
    assert shown["links"]==["https://example.org/profile"]
    assert "<img onerror=alert(1)>" in shown["text"]
    assert "邮箱可能注册过相关网站" in shown["text"]
    filtered=render(task,source="holehe",type="email_registration_signal")
    assert filtered["cards"]==1 and "Other site" not in filtered["text"]
    assert "结果类型：email_registration_signal" in filtered["text"]


@pytest.mark.parametrize("status,text",[("completed","当前数据源未发现匹配"),("failed","数据源不可用"),
    ("not_configured","数据源不可用"),("timeout","数据源不可用"),("running","正在检索"),("cancelled","已取消")])
def test_no_result_is_distinct_from_failed_or_unconfigured_source(status,text):
    shown=render({"status":status,"sources":[{"status":status}],"results":[]})
    assert text in shown["text"]


def test_finished_task_updates_list_status_and_stops_claiming_it_is_running():
    result=subprocess.run([shutil.which("node"),str(Path(__file__).with_name("controller_dom_runner.js"))],
        text=True,encoding="utf-8",capture_output=True,check=True,timeout=10)
    shown=json.loads(result.stdout)
    assert "已结束" in shown["message"]
    assert "完成" in shown["tasks"] and "运行" not in shown["tasks"]

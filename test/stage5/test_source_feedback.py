"""Execution feedback must remain useful even when there are no findings."""
import threading
import time
import json
import os
import subprocess
from pathlib import Path

import pytest

from spiderfoot.live_search import LiveSearchService, SourceAdapter
from spiderfoot import live_worker
from test.stage5.test_adapters import ControlledRunner
from test.stage5.test_page import render


@pytest.mark.parametrize('status,verdict,next_step', [
    ('completed', '查询完成，未发现匹配', '其他来源'),
    ('partial', '部分查询未能完成', '重试'),
    ('failed', '查询失败', '重试'),
    ('timeout', '查询超时', '重试'),
    ('not_configured', '未配置或未安装', '配置'),
    ('cancelled', '查询已取消', '重新'),
    ('running', '正在查询', '等待'),
])
def test_zero_findings_have_source_verdict_reason_time_and_recovery(status, verdict, next_step):
    shown = render({'status': status, 'sources': [
        {'source': 'sherlock', 'status': status, 'message': '受控来源说明', 'queried_at': 1700000000}], 'results': []})
    assert '检索执行报告' in shown['text']
    assert 'Sherlock' in shown['text'] and verdict in shown['text']
    assert '受控来源说明' in shown['text'] and '查询时间' in shown['text']
    assert next_step in shown['text']
    assert shown['cards'] == 0  # Reports are not fabricated findings.


def test_mixed_sources_keep_success_and_failure_visible_even_with_findings():
    shown = render({'status': 'partial', 'sources': [
        {'source': 'sherlock', 'status': 'completed', 'message': '检查完成'},
        {'source': 'maigret', 'status': 'timeout', 'message': '受控超时'}],
        'results': [{'source': 'sherlock', 'title': 'Saved evidence', 'result_type': 'profile'}]})
    assert shown['cards'] == 1 and 'Saved evidence' in shown['text']
    assert 'Maigret' in shown['text'] and '受控超时' in shown['text']
    assert '1 条已保存线索' in shown['text']


def test_filtered_empty_does_not_claim_source_returned_no_matches():
    shown = render({'status': 'completed', 'sources': [{'source': 'sherlock', 'status': 'completed'}],
                    'results': [{'source': 'sherlock', 'title': 'Saved', 'result_type': 'profile'}]}, type='different')
    assert '当前筛选条件下没有结果' in shown['text']
    assert '此任务共保存 1 条线索' in shown['text']
    assert '当前数据源未发现匹配' not in shown['text']


def test_legacy_partial_records_admit_missing_diagnostics_without_inventing_causes():
    shown = render({'status': 'partial', 'sources': [{'source': 'maigret', 'status': 'partial',
                    'message': '部分完成；部分站点不可用或受限。'}], 'results': []})
    assert '历史记录未保存具体失败站点或错误类型' in shown['text']
    assert '连接失败 10' not in shown['text']


def test_source_report_escapes_untrusted_text_and_does_not_create_links():
    shown = render({'status': 'failed', 'sources': [{'source': 'sherlock', 'status': 'failed',
                    'message': '<img src=x onerror=alert(1)>', 'limitations': '<script>bad</script>'}], 'results': []})
    assert '<img src=x onerror=alert(1)>' in shown['text']
    assert shown['htmlWrites'] == 0 and shown['links'] == []


def test_adapter_persists_only_allowlisted_diagnostic_counts_and_reasons():
    runner = ControlledRunner({'status': 'partial', 'items': [], 'diagnostics': {
        'checked': 10, 'unresolved': 8, 'unit': 'site',
        'reasons': {'timeout': 5, 'connection': 2, 'unsupported_input': 1,
                    'alice@example.invalid token=secret-placeholder': 99},
        'raw_error': 'alice@example.invalid token=secret-placeholder'}})
    reply = SourceAdapter('sherlock', runner).search('username', 'synthetic_demo', threading.Event())
    assert '检查数量：10 个站点' in reply['message']
    assert '可判定：2' in reply['message'] and '无法判定：8' in reply['message']
    assert '请求超时：5' in reply['message'] and '连接失败：2' in reply['message']
    assert '站点不支持此用户名格式：1' in reply['message']
    assert 'alice@' not in reply['message'] and 'secret-placeholder' not in reply['message']


def test_worker_outcome_keeps_real_counts_and_no_match_distinct_from_failure():
    reply = live_worker.outcome([], 10, 8, reasons={'timeout': 8})
    assert reply['status'] == 'partial'
    assert reply['diagnostics']['checked'] == 10 and reply['diagnostics']['unresolved'] == 8
    assert live_worker.outcome([], 10, 0)['status'] == 'completed'
    assert live_worker.outcome([], 10, 10)['status'] == 'failed'


def test_installed_sherlock_glue_classifies_controlled_failures_without_network():
    root = Path(__file__).resolve().parents[2]
    python = root / '.tools/live/sherlock/Scripts/python.exe'
    assert python.is_file(), 'Rebuild the isolated Sherlock environment for this test'
    code = '''
import json
import importlib.util
from types import SimpleNamespace as N
from unittest.mock import patch
from sherlock_project.result import QueryStatus as S
spec = importlib.util.spec_from_file_location('worker', 'spiderfoot/live_worker.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)
rows = {'A':{'status':N(status=S.AVAILABLE)}, 'B':{'status':N(status=S.AVAILABLE)},
        'C':{'status':N(status=S.UNKNOWN,context='Timeout alice@example.invalid token=placeholder')},
        'D':{'status':N(status=S.ILLEGAL)}}
with patch('sherlock_project.sherlock.sherlock',return_value=rows):
    print(json.dumps(worker.sherlock('synthetic_demo',{})))
'''
    result = subprocess.run([str(python), '-B', '-c', code], cwd=root, text=True,
                            encoding='utf-8', capture_output=True, check=True, timeout=15,
                            env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    report = json.loads(result.stdout)
    assert report['status'] == 'partial' and report['items'] == []
    assert report['diagnostics'] == {'checked': 4, 'unresolved': 2, 'unit': 'site',
                                     'reasons': {'timeout': 1, 'unsupported_input': 1}}
    assert 'alice@' not in result.stdout and 'token=' not in result.stdout


def test_execution_feedback_survives_reopen_and_remains_owner_scoped(tmp_path):
    runner = ControlledRunner({'status': 'partial', 'items': [], 'diagnostics': {
        'checked': 3, 'unresolved': 2, 'unit': 'site', 'reasons': {'blocked': 2}}})
    path = tmp_path / 'feedback.sqlite'
    service = LiveSearchService(path, runner)
    try:
        task = service.create(10, 'username', 'synthetic_demo', ['sherlock'])
        for _ in range(100):
            result = service.get(10, task['id'])
            if result['status'] not in ('waiting', 'running'):
                break
            time.sleep(.01)
        assert '访问被拒绝：2' in result['sources'][0]['message']
    finally:
        service.close()
    reopened = LiveSearchService(path, runner)
    try:
        assert reopened.get(10, task['id'])['sources'][0]['message'] == result['sources'][0]['message']
        with pytest.raises(KeyError):
            reopened.get(11, task['id'])
    finally:
        reopened.close()

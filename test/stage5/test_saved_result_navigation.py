import json
from pathlib import Path
import shutil
import subprocess

import pytest


def navigate(**scenario):
    completed = subprocess.run(
        [shutil.which('node'), str(Path(__file__).with_name('navigation_dom_runner.js'))],
        input=json.dumps(scenario), text=True, encoding='utf-8', capture_output=True,
        check=True, timeout=10,
    )
    return json.loads(completed.stdout)


def test_generic_results_entry_opens_latest_saved_task_and_can_reopen():
    shown = navigate(reenter=True)
    for page in (shown['before'], shown['after']):
        assert page['hash'] == '#results/' + 'a' * 32
        assert 'Saved A' in page['text']
    assert all('query=' not in url for url in shown['requests'])


def test_task_switch_stays_in_results_and_resets_previous_tasks_filters():
    shown = navigate(hash='#results/' + 'a' * 32, click=1)
    assert 'Saved A' in shown['before']['text']
    assert shown['after']['hash'] == '#results/' + 'b' * 32
    assert 'Saved B' in shown['after']['text']
    assert shown['after']['source'] == shown['after']['type'] == ''


def test_explicit_saved_task_survives_full_page_reentry():
    for _ in range(2):
        shown = navigate(hash='#results/' + 'b' * 32)
        assert 'Saved B' in shown['after']['text']
        assert '/liveget?id=' + 'a' * 32 not in shown['requests']


@pytest.mark.parametrize('status', [403, 404])
def test_invalid_or_foreign_task_never_falls_back_to_another_task(status):
    shown = navigate(hash='#results/' + 'c' * 32, deniedStatus=status)
    assert '数据不可用' in shown['after']['text']
    assert all(not url.startswith('/liveget?id=a') for url in shown['requests'])


def test_empty_results_center_explains_no_tasks_instead_of_no_matches():
    shown = navigate(empty=True)
    assert '暂无检索任务' in shown['after']['text']
    assert '新建检索' in shown['after']['text']
    assert not any(url.startswith('/liveget') for url in shown['requests'])


def test_list_failure_is_unavailable_not_an_empty_result():
    shown = navigate(listFailure=True)
    assert '数据不可用' in shown['after']['text']
    assert '未发现匹配' not in shown['after']['text']


def test_progress_task_switch_still_opens_progress():
    shown = navigate(hash='#progress/' + 'a' * 32, click=1)
    assert shown['after']['hash'] == '#progress/' + 'b' * 32

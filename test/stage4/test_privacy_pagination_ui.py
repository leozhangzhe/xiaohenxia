import json
from pathlib import Path
import shutil
import subprocess


def page(**scenario):
    process = subprocess.run([shutil.which('node'), str(Path(__file__).with_name('privacy_pagination_dom.cjs'))],
                             input=json.dumps(scenario), capture_output=True, text=True, encoding='utf-8',
                             timeout=10, check=True)
    return json.loads(process.stdout)


def test_both_lists_are_bounded_and_admin_editors_start_collapsed():
    shown = page()
    assert shown['before']['adminRows'] == 5
    assert shown['before']['ownRows'] == 5
    assert shown['before']['adminEditors'] == 0
    assert '200' in shown['before']['pager']


def test_admin_next_page_fetches_different_records_without_writes():
    shown = page(next=True)
    assert shown['after']['adminRows'] == 5
    assert shown['before']['adminText'] != shown['after']['adminText']
    assert any('page=2&' in r['url'] for r in shown['requests'])
    assert shown['writes'] == []


def test_expanding_one_record_builds_only_one_editor_and_saves_that_id():
    shown = page(edit=True)
    assert len(shown['writes']) == 1
    assert shown['writes'][0]['action_id'] == 'request-0'
    assert shown['writes'][0]['manual_note'] == 'synthetic note'
    assert shown['after']['adminEditors'] == 2
    assert shown['after']['htmlElements'] == 0


def test_failed_and_empty_lists_finish_loading_with_clear_state():
    failed = page(failure=True)
    assert '暂时无法读取' in failed['after']['adminText']
    assert failed['after']['adminEditors'] == 0
    empty = page(empty=True)
    assert '暂无' in empty['after']['adminText']
    assert '共 0 条' in empty['after']['pager']

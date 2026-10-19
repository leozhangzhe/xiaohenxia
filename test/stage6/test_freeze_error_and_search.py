"""Actual error-rendering and first-connection SQLite regressions found by the full run."""
from queue import Queue
import secrets

import pytest

from sfwebui import SpiderFootWebUi
from spiderfoot import SpiderFootDb
from test.stage1.conftest import mysql_boundary  # noqa: F401
from test.stage2.test_isolation_http import alice, business_token  # noqa: F401


def test_error_helper_renders_and_escapes_untrusted_text(mysql_boundary, tmp_path, monkeypatch):
    monkeypatch.setenv('SF_AUTH_ADMIN_PASS', secrets.token_urlsafe(24) + 'a7!')
    ui = SpiderFootWebUi({'root':'/'}, {'__database':str(tmp_path/'error.db'),
        '__modules__':{}, '__logging':False, '_debug':False}, Queue())
    page = ui.error('<img src=x onerror=alert(1)>')
    assert 'data-page="ERROR"' in page
    assert '&lt;img' in page and '<img src=x' not in page


def test_actual_http_unknown_page_remains_404(alice):
    client, url = alice
    response = client.get(url + '/synthetic-missing-page', timeout=5)
    assert response.status_code == 404
    assert '发生了一个错误' in response.content.decode('utf-8')
    assert 'Traceback' not in response.text and 'Undefined' not in response.text


def test_actual_http_invalid_scan_shows_error_without_private_input(alice, http_server):
    client, url = alice
    private_input = 'freeze-private@example.invalid'
    response = client.post(url + '/startscan', data={'scanname':'', 'scantarget':private_input,
        'modulelist':'sfp__stor_db', 'csrf_token':business_token(client,url)}, timeout=5)
    assert response.status_code == 200
    assert '发生了一个错误' in response.content.decode('utf-8')
    assert 'scan name was not specified' in response.text
    assert private_input not in response.text and private_input not in response.url
    assert private_input not in http_server[1].read_text(encoding='utf-8')


@pytest.mark.parametrize('reopen', [False, True])
def test_regex_search_works_on_first_connection_and_after_reopen(tmp_path, reopen):
    opts = {'__database':str(tmp_path/'regex.db')}
    db = SpiderFootDb(opts, False)
    try:
        db.conn.execute("INSERT INTO tbl_scan_instance(guid,name,seed_target,status) VALUES (?,?,?,?)",
                        ('synthetic-scan','合成扫描','example.invalid','FINISHED'))
        db.conn.executemany("INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,module,data,source_event_hash) VALUES (?,?,?,?,?,?,?)", [
            ('synthetic-scan','ROOT','ROOT',1700000000,'SpiderFoot','example.invalid','ROOT'),
            ('synthetic-scan','synthetic-child','INTERNET_NAME',1700000001,'sfp_test','synthetic-evidence','ROOT')])
        db.conn.commit()
        if reopen:
            db.close()
            db = SpiderFootDb(opts, False)
        rows = db.search({'scan_id':'synthetic-scan','regex':'^synthetic-evidence$'})
        assert len(rows) == 1 and rows[0][1] == 'synthetic-evidence'
        assert db.search({'scan_id':'synthetic-scan','regex':'^no-match$'}) == []
    finally:
        db.close()

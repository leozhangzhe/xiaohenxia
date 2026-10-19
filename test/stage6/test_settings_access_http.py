"""Settings navigation and real HTTP denial must preserve admin protection."""
import sqlite3

from bs4 import BeautifulSoup
import pytest

from test.stage2.test_isolation_http import alice, http_server, business_token  # noqa: F401
from test.stage2.test_business_csrf_http import admin  # noqa: F401


def test_regular_user_settings_denial_has_safe_workspace_page(alice):
    client, url = alice
    response = client.get(url + '/opts')
    assert response.status_code == 403
    page = BeautifulSoup(response.content, 'html.parser')
    assert page.select_one('body[data-page="ERROR"]') is not None
    assert '管理员' in page.get_text() and '回到首页' in page.get_text()
    assert page.select_one('form[action$="/savesettings"]') is None
    for forbidden in ('Traceback', 'web_access.py', 'sfwebui.py', 'site-packages', 'Administrator required'):
        assert forbidden not in response.text


@pytest.mark.parametrize('principal,expected', [('alice', False), ('admin', True)])
def test_settings_navigation_matches_actual_session_role(request, principal, expected):
    client, url = request.getfixturevalue(principal)
    response = client.get(url + '/newscan')
    assert response.status_code == 200
    page = BeautifulSoup(response.content, 'html.parser')
    assert bool(page.select('nav a[href$="/opts"]')) is expected


def test_admin_can_open_real_settings_form(admin):
    client, url = admin
    response = client.get(url + '/opts')
    assert response.status_code == 200
    page = BeautifulSoup(response.content, 'html.parser')
    form = page.select_one('form[action$="/savesettings"]')
    assert form is not None and form.get('method').upper() == 'POST'
    assert form.select_one('input[name="csrf_token"]') is not None


def test_regular_user_valid_csrf_cannot_change_settings(alice, http_server):
    client, url = alice
    def snapshot():
        with sqlite3.connect(http_server[3]) as db:
            return db.execute('SELECT * FROM tbl_config ORDER BY opt').fetchall()
    before = snapshot()
    response = client.post(url + '/savesettings', data={
        'csrf_token': business_token(client, url), 'allopts': '{}',
    })
    assert response.status_code == 403
    assert snapshot() == before
    assert 'Traceback' not in response.text


@pytest.mark.parametrize('token', [None, 'wrong-token', '中文错误令牌'])
def test_admin_settings_csrf_denial_still_403_without_traceback(admin, token):
    client, url = admin
    data = {'allopts': '{}'}
    if token is not None:
        data['csrf_token'] = token
    response = client.post(url + '/savesettings', data=data)
    assert response.status_code == 403
    assert response.headers.get('X-CSRF-Error') == '1'
    assert 'Traceback' not in response.text

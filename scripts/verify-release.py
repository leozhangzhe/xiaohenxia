"""Cold-start acceptance in an extracted package using its real launcher, MySQL and HTTP.

Creates synthetic users only in a NEW local profile. No mocks or developer database.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sys
import time

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if not (ROOT / 'RELEASE.json').is_file() or (ROOT / '.git').exists():
        raise SystemExit('Run only in a freshly extracted competition ZIP, not the development repository.')
    profile = ROOT / '.runtime-profile/release-verification'
    if profile.exists():
        raise SystemExit('Verification profile already exists; preserve it and extract into another NEW directory.')
    for line in (ROOT / 'MANIFEST.sha256').read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, 'Package manifest mismatch'
    spec = importlib.util.spec_from_file_location('release_desktop', ROOT / 'scripts/start-desktop.py')
    desktop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(desktop)
    port = desktop.free_port()
    url = 'http://127.0.0.1:' + str(port)
    password = secrets.token_urlsafe(28) + 'a7!'
    users = ('synthetic_release_a', 'synthetic_release_b')
    results = []
    os.environ.pop('SF_HIBP_API_KEY', None)
    action_id = scan_id = task_id = None

    def check(name, condition, detail=''):
        results.append({'check': name, 'passed': bool(condition), 'detail': detail})
        if not condition:
            raise AssertionError(name)

    def client():
        session = requests.Session()
        session.trust_env = False
        return session

    def token(session, route='login'):
        page = session.get(url + '/' + route, timeout=15)
        check(route + ' page', page.status_code == 200)
        return re.search(r'name="csrf_token" value="([^"]+)"', page.text)[1]

    def login(name):
        session = client()
        response = session.post(url + '/login', data={'username': name, 'password': password,
                                'csrf_token': token(session)}, allow_redirects=False, timeout=20)
        check('real login', response.status_code in (302, 303))
        return session

    def csrf(session):
        response = session.get(url + '/csrf', timeout=15)
        check('session CSRF', response.status_code == 200)
        return response.json()['csrf_token']

    def post(session, route, values, extra=None):
        return session.post(url + '/' + route, data=dict(values, csrf_token=csrf(session)),
                            timeout=125, allow_redirects=False, **(extra or {}))

    try:
        for iteration in (0, 1):
            server = desktop.DesktopServer(profile, port)
            try:
                server.start(lambda: password if iteration == 0 else (_ for _ in ()).throw(AssertionError('Restart prompted for password')))
                server.start_web()
                check('cold start' if iteration == 0 else 'restart', True)
                if iteration == 0:
                    check('fresh MySQL connection protected by DPAPI', (profile / 'connection.dpapi').is_file())
                    for name in users:
                        with client() as session:
                            response = session.post(url + '/register', data={'username': name, 'password': password,
                                'confirm': password, 'csrf_token': token(session, 'register')}, timeout=25)
                            check('real registration', response.status_code == 200 and '注册成功' in response.content.decode('utf-8'))
                    with client() as session:
                        response = session.post(url + '/login', data={'username': users[0], 'password': 'wrong-synthetic-password',
                            'csrf_token': token(session)}, timeout=15)
                        check('incorrect password rejected', response.status_code == 200 and 'data-error=""' not in response.text)
                a, b = login(users[0]), login(users[1])
                try:
                    check('refresh retains session', a.get(url + '/', timeout=20).status_code == 200)
                    for route in ('newscan', 'livesearch', 'privacyaction', 'leakcheck'):
                        check('page ' + route, a.get(url + '/' + route, timeout=20).status_code == 200)
                    # Verify every actual stylesheet/script referenced by a business page is present.
                    html = a.get(url + '/', timeout=20).text + a.get(url + '/login', timeout=20).text
                    assets = set(re.findall(r'(?:src|href)=["\'](/static/[^"\']+)', html))
                    for path in assets:
                        check('asset ' + path.split('?')[0], a.get(url + path, timeout=15).status_code == 200)
                    if iteration == 0:
                        availability = a.get(url + '/liveavailability', timeout=15).json()
                        check('all source tools rebuilt', all(item['installed'] for item in availability if item['source'] != 'hibp'))
                        check('HIBP unconfigured', not next(item for item in availability if item['source'] == 'hibp')['configured'])
                        before = a.get(url + '/privacyactionlist', timeout=15).json()['total']
                        values = {'action_type':'hide', 'platform':'example.invalid', 'content':'https://example.invalid/synthetic-release', 'user_confirmed':'1'}
                        for bad in (None, '中文错误', csrf(b)):
                            payload = dict(values)
                            if bad is not None:
                                payload['csrf_token'] = bad
                            response = a.post(url + '/privacyactionsubmit', data=payload, timeout=20)
                            check('CSRF rejection with no side effect', response.status_code == 403 and
                                a.get(url + '/privacyactionlist', timeout=15).json()['total'] == before)
                        response = post(a, 'privacyactionsubmit', values)
                        check('request recorded', response.status_code == 200 and response.json().get('status') == 'recorded')
                        action_id = response.json()['id']
                        response = post(b, 'privacyactiondelete', {'action_id':action_id})
                        check('cross-user request deletion rejected', response.status_code == 404)
                        response = post(a, 'privacyactionstatus', {'action_id':action_id, 'status':'completed', 'manual_note':'synthetic'})
                        check('ordinary user cannot process requests', response.status_code == 403)
                        check('write methods enforced', a.get(url + '/privacyactionsubmit', timeout=15).status_code == 405)
                        response = post(a, 'livecreate', {'input_type':'email', 'query':'alice@example.invalid', 'sources':'["hibp"]'})
                        check('unified task created', response.status_code == 200 and bool(response.json().get('id')))
                        task_id = response.json()['id']
                        deadline = time.monotonic() + 15
                        while time.monotonic() < deadline:
                            task = a.get(url + '/liveget', params={'id':task_id}, timeout=15).json()
                            if task['status'] not in ('waiting','running'):
                                break
                            time.sleep(.2)
                        check('HIBP missing Key does not fake results', task['sources'][0]['status'] == 'not_configured' and not task['results'])
                        response = post(a, 'startscan', {'scanname':'Synthetic release DNS verification', 'scantarget':'example.com',
                            'modulelist':'sfp_dnsresolve'}, {'headers':{'Accept':'application/json'}})
                        check('real SpiderFoot scan created', response.status_code == 200 and response.json()[0] == 'SUCCESS')
                        scan_id = response.json()[1]
                        deadline = time.monotonic() + 100
                        while time.monotonic() < deadline:
                            scan = a.get(url + '/scanstatus', params={'id':scan_id}, timeout=15).json()
                            if scan and scan[5] in ('FINISHED','ERROR-FAILED','ABORTED'):
                                break
                            time.sleep(1)
                        check('real SpiderFoot scan finished', bool(scan) and scan[5] == 'FINISHED')
                        response = a.get(url + '/scanresults', params={'id':scan_id}, timeout=15)
                        check('unified scan result response', response.status_code == 200 and 'results' in response.json())
                        check('synthetic sample hit', a.post(url + '/leaksearch', data={'q':'alice@example.invalid'}, timeout=15).json()['found'])
                        miss = a.post(url + '/leaksearch', data={'q':'no-match@example.invalid'}, timeout=15).json()
                        check('no match is not safety', not miss['found'] and miss['message'] == '当前数据源未发现匹配，不代表不存在相关信息。')
                    check('other user cannot read scan', b.get(url + '/scanresults', params={'id':scan_id}, timeout=15).status_code == 404)
                    check('other user cannot read unified task', b.get(url + '/liveget', params={'id':task_id}, timeout=15).status_code == 404)
                    check('requests isolated', action_id not in str(b.get(url + '/privacyactionlist', timeout=15).json()))
                    check('request survives restart', action_id in str(a.get(url + '/privacyactionlist', timeout=15).json()))
                    check('scan survives restart', a.get(url + '/scanresults', params={'id':scan_id}, timeout=15).status_code == 200)
                    check('unified task survives restart', a.get(url + '/liveget', params={'id':task_id}, timeout=15).status_code == 200)
                    old = csrf(a)
                    response = post(a, 'logout', {})
                    check('logout', response.status_code in (200,302,303))
                    check('logout invalidates access', a.get(url + '/privacyactionlist', allow_redirects=False, timeout=15).status_code in (302,303,401))
                    check('old session token unusable', a.post(url + '/privacyactionsubmit', data={'csrf_token':old}, allow_redirects=False, timeout=15).status_code in (302,303,401,403))
                finally:
                    a.close()
                    b.close()
            finally:
                server.close()
            check('owned Web and MySQL stopped', (server.web is None or server.web.poll() is not None) and
                (server.mysql is None or server.mysql.poll() is not None))
            with socket.socket() as probe:
                check('Web port released', probe.connect_ex(('127.0.0.1', port)) != 0)
        logs = (profile / 'web.log').read_text(encoding='utf-8', errors='replace')
        check('logs do not expose password or synthetic email input', password not in logs and 'alice@example.invalid' not in logs)
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({'commit':json.loads((ROOT/'RELEASE.json').read_text())['commit'],
            'checks':results,'passed':sum(r['passed'] for r in results), 'failed':sum(not r['passed'] for r in results),
            'method':'real Windows DPAPI + new MySQL + real CherryPy HTTP; no mocks; real source availability; one DNS scan',
            'browser':'HTTP acceptance only; no new visual-browser acceptance claimed'}, ensure_ascii=False, indent=2),encoding='utf-8')
    print('Cold-start checks passed:', len(results), '; report:', args.report)


if __name__ == '__main__':
    main()

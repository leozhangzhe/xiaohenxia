"""Class setup for the legacy CherryPy harness needs credentials before per-test fixtures.

Use a NEW real MySQL instance. Do not disable authentication to fit old assertions.
"""
import os
import secrets

import pytest

from test.stage1.live_mysql import LiveMySQL


@pytest.fixture(scope='module', autouse=True)
def legacy_route_authentication(request, tmp_path_factory):
    if request.module.__name__ != 'test.integration.test_sfwebui':
        yield
        return
    folder = tmp_path_factory.mktemp('legacy-routes-real-mysql')
    database = LiveMySQL(folder)
    saved = {}
    values = {
        'SF_AUTH_MYSQL_HOST': '127.0.0.1', 'SF_AUTH_MYSQL_PORT': str(database.port),
        'SF_AUTH_MYSQL_USER': 'root', 'SF_AUTH_MYSQL_PASSWORD': database.password,
        'SF_AUTH_MYSQL_DATABASE': 'freeze_legacy_routes', 'SF_AUTH_ADMIN_USER': 'admin',
        'SF_AUTH_ADMIN_PASS': secrets.token_urlsafe(30) + 'a7!', 'SF_AUTH_ADMIN_RESET': '0',
    }
    for name in ('SPIDERFOOT_DATA', 'SPIDERFOOT_CACHE', 'SPIDERFOOT_LOGS'):
        target = folder / name
        target.mkdir()
        values[name] = str(target)
    try:
        database.initialize()
        for name, value in values.items():
            saved[name] = os.environ.get(name)
            os.environ[name] = value
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        database.close()

"""Authentication startup must fail closed at the public Web UI boundary."""
import pymysql
import pytest

from sfwebui import SpiderFootWebUi


def test_database_failure_prevents_web_ui_startup(monkeypatch, web_config, logging_queue):
    def unavailable(**kwargs):
        raise pymysql.OperationalError(2003, "test database is unavailable")

    monkeypatch.setattr(pymysql, "connect", unavailable)
    with pytest.raises(RuntimeError, match="authentication database"):
        SpiderFootWebUi({"root": "/"}, web_config, logging_queue)

"""The checked-in LeakCheckDB sample contains only unmistakable synthetic data."""
import sqlite3
from pathlib import Path

import pytest

import spiderfoot.leakcheck as leakcheck
from spiderfoot.leakcheck import LeakCheckDB


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "leak-check.db"
EXPECTED_EMAILS = {"alice@example.invalid", "bob@example.invalid"}


def test_bundled_database_opens_and_contains_only_synthetic_records():
    db = LeakCheckDB(db_path=str(DB_PATH))
    assert db.get_record_count() == 2

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT p.name, p.email, p.id, p.phone, p.qq, p.receiver,
                   p.nickname, p.address, p.car, p.weibo, p.contact, p.company,
                   s.source
            FROM person AS p JOIN source AS s ON s.id = p.source_id
        """).fetchall()
        source_count = conn.execute("SELECT COUNT(*) FROM source").fetchone()[0]

    assert len(rows) == 2
    assert source_count == 1
    assert {row[1] for row in rows} == EXPECTED_EMAILS
    assert {row[0] for row in rows} == {"测试用户一", "测试用户二"}
    for row in rows:
        assert all(value is None for value in row[2:12])
        assert "本地合成演示数据" in row[12]
        assert "非真实泄露事件" in row[12]


def test_bundled_database_synthetic_email_match_and_no_match():
    db = LeakCheckDB(db_path=str(DB_PATH))
    assert db.search_persons("alice@example.invalid")["found"] is True
    assert db.search_persons("not-in-sample@example.invalid")["found"] is False


def test_missing_bundled_database_is_unavailable_not_an_empty_match(monkeypatch, tmp_path):
    fake_package = tmp_path / "spiderfoot"
    fake_package.mkdir()
    monkeypatch.setattr(leakcheck, "__file__", str(fake_package / "leakcheck.py"))
    monkeypatch.delenv("SF_LEAKCHECK_DB", raising=False)

    with pytest.raises(FileNotFoundError, match="数据源不可用"):
        LeakCheckDB()

    assert not (tmp_path / "data" / "leak-check.db").exists()

"""Isolated boundaries for stage-one authentication tests."""
import logging
import sqlite3
from queue import Queue

import pytest
import pymysql


@pytest.fixture(autouse=True)
def default_options(monkeypatch, tmp_path):
    # Override the legacy class-only fixture. Never use an existing runtime DB.
    for name in ("SPIDERFOOT_DATA", "SPIDERFOOT_CACHE", "SPIDERFOOT_LOGS"):
        directory = tmp_path / name.lower()
        directory.mkdir()
        monkeypatch.setenv(name, str(directory))
    for name in ("SF_AUTH_ADMIN_USER", "SF_AUTH_ADMIN_PASS", "SF_AUTH_ADMIN_RESET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SF_AUTH_MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("SF_AUTH_MYSQL_PORT", "3306")
    monkeypatch.setenv("SF_AUTH_MYSQL_USER", "stage1_boundary_user")
    monkeypatch.setenv("SF_AUTH_MYSQL_PASSWORD", "StageOne-Boundary-Only-4387")
    monkeypatch.setenv("SF_AUTH_MYSQL_DATABASE", "stage1_auth_boundary")


@pytest.fixture
def web_config(tmp_path):
    return {
        "__database": str(tmp_path / "scan-test.db"),
        "__modules__": {},
        "__logging": False,
        "_debug": False,
    }


@pytest.fixture
def logging_queue():
    queue = Queue()
    yield queue
    logging.getLogger("spiderfoot").handlers.clear()


class MySQLBoundary:
    """A test database adapter at the third-party connector boundary.

    MySQL DDL is translated only for fast behavioral tests. Real MySQL smoke
    checks are separate; this adapter does not claim MySQL compatibility.
    """

    def __init__(self, path):
        self.path = path
        self.available = True

    def connect(self, **kwargs):
        if not self.available:
            raise pymysql.OperationalError(2003, "test database unavailable")
        return BoundaryConnection(self, kwargs)

    def stored_hash(self, username):
        with sqlite3.connect(self.path) as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE username=?", (username,)).fetchone()
            return row[0] if row else None

    def replace_stored_hash(self, username, value):
        with sqlite3.connect(self.path) as conn:
            conn.execute("UPDATE users SET password_hash=? WHERE username=?", (value, username))


class BoundaryConnection:
    def __init__(self, boundary, kwargs):
        self.boundary = boundary
        self.conn = sqlite3.connect(boundary.path, isolation_level=None)
        self.dict_cursor = kwargs.get("cursorclass") is pymysql.cursors.DictCursor

    def cursor(self):
        return BoundaryCursor(self, self.dict_cursor)

    def close(self):
        self.conn.close()


class BoundaryCursor:
    def __init__(self, connection, dict_cursor):
        self.connection = connection
        self.cursor = connection.conn.cursor()
        self.dict_cursor = dict_cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cursor.close()

    def execute(self, sql, params=()):
        if not self.connection.boundary.available:
            raise pymysql.OperationalError(2013, "test connection lost")
        if sql.strip().upper().startswith("CREATE DATABASE"):
            return 0
        if sql.strip().upper().startswith("CREATE TABLE") and "users" in sql:
            sql = """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
        elif sql.strip().upper().startswith("CREATE TABLE") and "privacy_actions" in sql:
            sql = """CREATE TABLE IF NOT EXISTS privacy_actions (
                id TEXT PRIMARY KEY, username TEXT NOT NULL, user_id INTEGER NULL,
                action_type TEXT NOT NULL, platform TEXT NOT NULL, content TEXT NOT NULL,
                masked_content TEXT, status TEXT NOT NULL, note TEXT DEFAULT '',
                user_confirmed INTEGER NOT NULL DEFAULT 0, manual_note TEXT NOT NULL DEFAULT '',
                created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL)"""
        if "FROM information_schema.columns" in sql:
            columns = {row[1] for row in self.cursor.execute("PRAGMA table_info(privacy_actions)")}
            self.cursor.execute("SELECT ? AS column_count", (1 if params[1] in columns else 0,))
            return 0
        if sql.strip().upper().startswith("ALTER TABLE PRIVACY_ACTIONS ADD COLUMN USER_ID"):
            columns = {row[1] for row in self.cursor.execute("PRAGMA table_info(privacy_actions)")}
            if "user_id" not in columns:
                self.cursor.execute("ALTER TABLE privacy_actions ADD COLUMN user_id BIGINT NULL")
            return 0
        if "FROM information_schema.statistics" in sql:
            exists = self.cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?",
                ("idx_privacy_actions_owner",),
            ).fetchone()
            self.cursor.execute("SELECT ?", (1 if exists else 0,))
            return 0
        try:
            self.cursor.execute(sql.replace("%s", "?"), params)
        except sqlite3.IntegrityError as exc:
            raise pymysql.IntegrityError(1062, "duplicate user") from exc
        except sqlite3.Error as exc:
            raise pymysql.OperationalError(1146, "test table unavailable") from exc
        return self.cursor.rowcount

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None or not self.dict_cursor:
            return row
        return dict(zip((item[0] for item in self.cursor.description), row))

    def fetchall(self):
        rows = self.cursor.fetchall()
        if not self.dict_cursor:
            return rows
        columns = [item[0] for item in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]


@pytest.fixture
def mysql_boundary(monkeypatch, tmp_path):
    boundary = MySQLBoundary(tmp_path / "auth-boundary.sqlite")
    monkeypatch.setattr(pymysql, "connect", boundary.connect)
    return boundary

"""Exercise the privacy ownership migration against the bundled real MySQL server."""
import logging

import pytest

from spiderfoot.auth_mysql import MySQLAuthStore
from spiderfoot.privacy_action import PrivacyActionDB
from test.stage1.live_mysql import LiveMySQL


@pytest.fixture
def privacy_mysql(tmp_path, monkeypatch):
    folder = tmp_path / "privacy-mysql"
    folder.mkdir()
    server = LiveMySQL(folder)
    try:
        server.initialize()
        for name, value in {
            "SF_AUTH_MYSQL_HOST": "127.0.0.1",
            "SF_AUTH_MYSQL_PORT": str(server.port),
            "SF_AUTH_MYSQL_USER": "root",
            "SF_AUTH_MYSQL_PASSWORD": server.password,
            "SF_AUTH_MYSQL_DATABASE": "stage2_privacy_test",
            "SF_AUTH_ADMIN_USER": "admin",
            "SF_AUTH_ADMIN_PASS": "StageTwo-Real-MySQL-4387",
            "SF_AUTH_ADMIN_RESET": "0",
        }.items():
            monkeypatch.setenv(name, value)
        auth = MySQLAuthStore(logging.getLogger("stage2.mysql"))
        auth.initialize()
        assert auth.create_user("alice", "StageTwo-Real-MySQL-4387")
        assert auth.create_user("bob", "StageTwo-Real-MySQL-4387")
        with server.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("USE stage2_privacy_test")
                cursor.execute("""CREATE TABLE privacy_actions (
                    id VARCHAR(64) NOT NULL PRIMARY KEY,
                    username VARCHAR(64) NOT NULL,
                    action_type VARCHAR(16) NOT NULL,
                    platform VARCHAR(128) NOT NULL,
                    content TEXT NOT NULL,
                    masked_content TEXT,
                    status VARCHAR(32) NOT NULL,
                    note VARCHAR(512) DEFAULT '',
                    created_at BIGINT NOT NULL,
                    updated_at BIGINT NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
                cursor.execute(
                    "INSERT INTO privacy_actions VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    ("legacy-action", "alice", "hide", "example.invalid", "legacy@example.invalid",
                     None, "processing", "legacy", 1, 1),
                )
        yield server, auth
    finally:
        server.close()


def test_privacy_ownership_migration_and_crud_use_real_mysql(privacy_mysql):
    server, auth = privacy_mysql
    alice = auth.get_user("alice")
    bob = auth.get_user("bob")
    privacy = PrivacyActionDB()
    created = privacy.create_action(alice["id"], alice["username"], "delete", "example.invalid", "private@example.invalid")
    assert created["success"]
    assert privacy.list_actions(alice["id"])["total"] == 2
    assert privacy.list_actions(bob["id"])["total"] == 0
    assert not privacy.delete_action(created["id"], bob["id"])["success"]
    assert not privacy.update_status(created["id"], bob["id"], "done")["success"]
    with server.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("USE stage2_privacy_test")
            cursor.execute("SELECT user_id FROM privacy_actions WHERE id=%s", ("legacy-action",))
            assert cursor.fetchone()[0] == alice["id"]
            cursor.execute("SELECT user_id FROM privacy_actions WHERE id=%s", (created["id"],))
            assert cursor.fetchone()[0] == alice["id"]

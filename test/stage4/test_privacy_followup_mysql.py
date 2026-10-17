"""The recorded application survives a real isolated MySQL restart."""
from spiderfoot.privacy_action import PrivacyActionDB
from test.stage2.test_privacy_real_mysql import privacy_mysql


def test_request_persists_through_mysql_restart(privacy_mysql):
    server, auth = privacy_mysql
    alice = auth.get_user("alice")
    action = PrivacyActionDB().create_action(
        alice["id"], "alice", "hide", "example.invalid",
        "https://example.invalid/persistent", user_confirmed=True,
    )
    assert action["success"] and action["status"] == "recorded"
    server.stop()
    server.start()
    with server.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("USE stage2_privacy_test")
            cursor.execute("UPDATE privacy_actions SET status='done' WHERE id='legacy-action'")
    fresh_store = PrivacyActionDB()
    item = fresh_store.get_action(action["id"], alice["id"])
    assert item["success"]
    assert item["item"]["status"] == "recorded"
    assert item["item"]["user_confirmed"] == 1
    legacy = fresh_store.get_action("legacy-action", alice["id"])
    assert legacy["item"]["status"] == "recorded"
    assert legacy["item"]["user_confirmed"] == 0

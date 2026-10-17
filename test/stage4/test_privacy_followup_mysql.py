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


def test_legacy_claims_are_sanitized_without_erasing_human_notes(privacy_mysql):
    server, auth = privacy_mysql
    alice_id = auth.get_user("alice")["id"]
    cases = [("old-" + status, status, "已提交给平台，预计1–3天完成")
             for status in ("pending", "processing", "done", "failed")]
    cases.extend([
        ("manual-only", "processing", "人工备注：已核对申请目标"),
        ("mixed-note", "pending", "已提交给平台；预计1–3天完成；人工备注：已核对申请目标"),
        ("previously-migrated", "recorded", "已提交给平台，预计1–3天完成"),
        ("human-quotation", "recorded", "人工备注：用户声称已提交给平台，需核实"),
    ])
    with server.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("USE stage2_privacy_test")
            cursor.executemany(
                "INSERT INTO privacy_actions "
                "(id, username, action_type, platform, content, status, note, created_at, updated_at) "
                "VALUES (%s, 'alice', 'hide', 'example.invalid', 'https://example.invalid/demo', %s, %s, 1, 1)",
                cases,
            )

    store = PrivacyActionDB()
    expected = "历史模拟记录，平台提交情况未经核实，需人工跟进。"
    for action_id, _, _ in cases[:4]:
        item = store.get_action(action_id, alice_id)["item"]
        assert item["status"] == "recorded"
        assert item["note"] == expected
        assert item["user_confirmed"] == 0
    manual = store.get_action("manual-only", alice_id)["item"]
    assert manual["status"] == "recorded"
    assert manual["note"] == "人工备注：已核对申请目标"
    assert manual["user_confirmed"] == 0
    mixed = store.get_action("mixed-note", alice_id)["item"]
    assert mixed["status"] == "recorded"
    assert mixed["note"].startswith(expected)
    assert "人工备注：已核对申请目标" in mixed["note"]
    assert "已提交给平台" not in mixed["note"]
    assert "预计1–3天完成" not in mixed["note"]
    assert mixed["user_confirmed"] == 0
    previous = store.get_action("previously-migrated", alice_id)["item"]
    assert previous["status"] == "recorded"
    assert previous["note"] == expected
    assert previous["user_confirmed"] == 0
    quotation = store.get_action("human-quotation", alice_id)["item"]
    assert quotation["note"] == "人工备注：用户声称已提交给平台，需核实"

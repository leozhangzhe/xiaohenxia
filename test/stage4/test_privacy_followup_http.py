"""Real HTTP boundaries for privacy request records and human follow-up."""
import sqlite3

from test.stage2.test_isolation_http import alice, bob, http_server, business_token
from test.stage2.test_business_csrf_http import admin


def submit(client, url, action_type="hide", confirmed="1"):
    return client.post(url + "/privacyactionsubmit", data={
        "action_type": action_type, "platform": "example.invalid",
        "content": "https://example.invalid/request", "user_confirmed": confirmed,
        "csrf_token": business_token(client, url),
    })


def test_request_requires_confirmation_and_records_truthful_state(alice, http_server):
    client, url = alice
    auth_db = http_server[2]
    with sqlite3.connect(auth_db) as db:
        before = db.execute("SELECT COUNT(*) FROM privacy_actions").fetchone()[0]
    rejected = submit(client, url, confirmed="")
    assert rejected.status_code == 400
    with sqlite3.connect(auth_db) as db:
        assert db.execute("SELECT COUNT(*) FROM privacy_actions").fetchone()[0] == before

    response = submit(client, url)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] and data["status"] == "recorded"
    with sqlite3.connect(auth_db) as db:
        row = db.execute(
            "SELECT user_id, action_type, platform, content, user_confirmed, status, "
            "manual_note, created_at, updated_at FROM privacy_actions WHERE id=?", (data["id"],)
        ).fetchone()
    assert row[:7] == (2, "hide", "example.invalid", "https://example.invalid/request", 1,
                       "recorded", "")
    assert row[7] > 0 and row[8] >= row[7]


def test_other_user_cannot_read_or_change_request(alice, bob, http_server):
    alice_client, url = alice
    bob_client, _ = bob
    action_id = submit(alice_client, url).json()["id"]
    assert action_id not in str(bob_client.get(url + "/privacyactionlist").json())
    assert bob_client.get(url + "/privacyactionadminlist").status_code == 403
    attempt = bob_client.post(url + "/privacyactionstatus", data={
        "action_id": action_id, "status": "platform_contacted", "manual_note": "test note",
        "csrf_token": business_token(bob_client, url),
    })
    assert attempt.status_code == 403
    owner_attempt = alice_client.post(url + "/privacyactionstatus", data={
        "action_id": action_id, "status": "platform_contacted", "manual_note": "test note",
        "csrf_token": business_token(alice_client, url),
    })
    assert owner_attempt.status_code == 403
    with sqlite3.connect(http_server[2]) as db:
        assert db.execute("SELECT status, manual_note FROM privacy_actions WHERE id=?",
                          (action_id,)).fetchone() == ("recorded", "")


def test_admin_followup_requires_role_csrf_and_real_record(alice, admin, http_server):
    alice_client, url = alice
    admin_client, _ = admin
    action_id = submit(alice_client, url, "delete").json()["id"]
    assert admin_client.get(url + "/privacyactionadminlist").status_code == 200
    admin_items = admin_client.get(url + "/privacyactionadminlist").json()["items"]
    assert any(item["id"] == action_id and item["user_confirmed"] == 1 for item in admin_items)
    payload = {"action_id": action_id, "status": "platform_contacted", "manual_note": "已人工核对联系记录"}
    assert admin_client.get(url + "/privacyactionstatus", params=payload).status_code == 405
    assert admin_client.post(url + "/privacyactionstatus", data=payload).status_code == 403
    assert admin_client.post(url + "/privacyactionstatus", data={
        **payload, "csrf_token": "wrong-token",
    }).status_code == 403
    assert admin_client.post(url + "/privacyactionstatus", data={
        **payload, "csrf_token": business_token(alice_client, url),
    }).status_code == 403
    with sqlite3.connect(http_server[2]) as db:
        assert db.execute("SELECT status FROM privacy_actions WHERE id=?",
                          (action_id,)).fetchone()[0] == "recorded"
    response = admin_client.post(url + "/privacyactionstatus", data={
        **payload, "csrf_token": business_token(admin_client, url),
    })
    assert response.status_code == 200 and response.json()["success"]
    with sqlite3.connect(http_server[2]) as db:
        assert db.execute("SELECT status, manual_note FROM privacy_actions WHERE id=?",
                          (action_id,)).fetchone() == ("platform_contacted", "已人工核对联系记录")
    own = alice_client.get(url + "/privacyactionlist").json()["items"]
    assert any(row["id"] == action_id and row["status"] == "platform_contacted" for row in own)
    missing = admin_client.post(url + "/privacyactionstatus", data={
        **payload, "action_id": "missing-request", "csrf_token": business_token(admin_client, url),
    })
    assert missing.status_code == 404


def test_all_followup_states_and_repeat_save_are_persisted(alice, admin, http_server):
    alice_client, url = alice
    admin_client, _ = admin
    action_id = submit(alice_client, url).json()["id"]
    token = business_token(admin_client, url)
    for state in ("draft", "recorded", "awaiting_manual", "platform_contacted",
                  "platform_processing", "completed", "unable"):
        payload = {"action_id": action_id, "status": state,
                   "manual_note": "人工核对演示记录", "csrf_token": token}
        assert admin_client.post(url + "/privacyactionstatus", data=payload).status_code == 200
        with sqlite3.connect(http_server[2]) as db:
            assert db.execute("SELECT status FROM privacy_actions WHERE id=?",
                              (action_id,)).fetchone()[0] == state
    with sqlite3.connect(http_server[2]) as db:
        before = db.execute("SELECT updated_at FROM privacy_actions WHERE id=?", (action_id,)).fetchone()[0]
    same = admin_client.post(url + "/privacyactionstatus", data=payload)
    assert same.status_code == 200
    with sqlite3.connect(http_server[2]) as db:
        after = db.execute("SELECT updated_at FROM privacy_actions WHERE id=?", (action_id,)).fetchone()[0]
    assert after > before
    invalid = admin_client.post(url + "/privacyactionstatus", data={
        **payload, "status": "success_without_evidence",
    })
    assert invalid.status_code == 400
    malformed = admin_client.post(url + "/privacyactionstatus", data=[
        ("action_id", action_id), ("status", "recorded"),
        ("manual_note", "first"), ("manual_note", "second"), ("csrf_token", token),
    ])
    assert malformed.status_code == 400
    with sqlite3.connect(http_server[2]) as db:
        assert db.execute("SELECT status FROM privacy_actions WHERE id=?",
                          (action_id,)).fetchone()[0] == "unable"


def test_page_describes_manual_record_without_unsupported_claims(alice, admin):
    client, url = alice
    html = client.get(url + "/privacyaction").content.decode("utf-8")
    assert "申请记录与人工跟进" in html
    assert "这不是自动删除" in html
    assert "不保证第三方平台执行" in html
    assert "需要人工跟进或用户自行联系平台" in html
    for unsupported in ("已提交给平台", "1–3 天", "1-3 天", "自动向对应平台提交", "全自动处理"):
        assert unsupported not in html
    assert "管理员人工跟进" not in html
    admin_client, _ = admin
    admin_html = admin_client.get(url + "/privacyaction").content.decode("utf-8")
    assert "管理员人工跟进" in admin_html

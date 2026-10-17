import json
import time
import pytest
from test.stage2.test_isolation_http import alice, bob, business_token


def create(client, url, **override):
    data = {"input_type":"username", "query":"stage5_sensitive_demo", "csrf_token":business_token(client,url)}
    data.update(override)
    return client.post(url+"/livecreate",data=data,allow_redirects=False)


def test_real_http_ownership_post_methods_and_private_input(alice,bob,http_server):
    client,url = alice
    other,_ = bob
    response = create(client,url)
    assert response.status_code == 200
    task_id = response.json()["id"]
    assert "stage5_sensitive_demo" not in response.url
    for route in ("liveget","livecancel","livedelete"):
        request = other.get if route=="liveget" else other.post
        result = request(url+"/"+route, **({"params":{"id":task_id}} if route=="liveget" else
                        {"data":{"id":task_id,"csrf_token":business_token(other,url)}}))
        assert result.status_code == 404
    assert other.get(url+"/livelist").json() == []
    task = client.get(url+"/liveget",params={"id":task_id})
    assert task.status_code==200 and task.json()["query"]=="st***"
    assert "stage5_sensitive_demo" not in http_server[1].read_text(encoding="utf-8")
    for route in ("livecreate","livecancel","livedelete"):
        assert client.get(url+"/"+route).status_code==405


@pytest.mark.parametrize("bad_token",["missing","wrong","cross_session"])
def test_csrf_failure_has_no_task_side_effect(alice,bob,bad_token):
    client,url = alice
    other,_ = bob
    before=client.get(url+"/livelist").json()
    data={"input_type":"email","query":"alice@example.invalid"}
    if bad_token!="missing":
        data["csrf_token"]=business_token(other,url) if bad_token=="cross_session" else "wrong"
    assert client.post(url+"/livecreate",data=data).status_code==403
    assert client.get(url+"/livelist").json()==before


def test_invalid_query_never_echoed_in_errors_and_page_is_truthful(alice,http_server):
    client,url=alice
    secret="invalid-secret-email-value"
    result=create(client,url,input_type="email",query=secret)
    assert result.status_code==400 and secret not in result.text
    page=client.get(url+"/livesearch")
    assert page.status_code==200
    html=page.content.decode("utf-8")
    assert "邮箱可能注册过相关网站" in html
    assert "手机号、身份证、QQ" in html
    assert "确认属于本人" not in html
    assert secret not in http_server[1].read_text(encoding="utf-8")


def test_cancel_delete_and_hibp_missing_key_remain_functional(alice):
    client,url=alice
    created=create(client,url,input_type="email",query="alice@example.invalid").json()
    task_id=created["id"]
    for _ in range(50):
        task=client.get(url+"/liveget",params={"id":task_id}).json()
        if task["status"] not in ("waiting","running"):
            break
        time.sleep(.02)
    assert next(s for s in task["sources"] if s["source"]=="hibp")["status"]=="not_configured"
    assert client.post(url+"/livecancel",data={"id":task_id,"csrf_token":business_token(client,url)}).status_code==200
    assert client.post(url+"/livedelete",data={"id":task_id,"csrf_token":business_token(client,url)}).status_code==200
    assert client.get(url+"/liveget",params={"id":task_id}).status_code==404


@pytest.mark.parametrize("route",["livecancel","livedelete"])
def test_cancel_and_delete_require_current_session_csrf_without_side_effect(alice,bob,route):
    client,url=alice
    other,_=bob
    task=create(client,url,input_type="email",query="alice@example.invalid",sources='["hibp"]').json()
    task_id=task["id"]
    for token in (None,"wrong",business_token(other,url)):
        data={"id":task_id}
        if token is not None:data["csrf_token"]=token
        assert client.post(url+"/"+route,data=data).status_code==403
        assert client.get(url+"/liveget",params={"id":task_id}).status_code==200

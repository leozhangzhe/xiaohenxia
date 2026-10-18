"""Real HTTP/assets and evidence-state regressions for the selected C interface."""
from html.parser import HTMLParser
import pytest
from test.stage2.test_isolation_http import alice
from test.stage5.test_page import render


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []
        self.actions = []
    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "script" and data.get("src"):
            self.paths.append(data["src"])
        if tag == "link" and data.get("rel") == "stylesheet":
            self.paths.append(data["href"])
        if tag == "button" and "data-action" in data:
            self.actions.append(data)


def test_six_interface_views_retain_real_local_assets_and_http_boundaries(alice):
    client, url = alice
    for route in ("/", "/livesearch", "/privacyaction"):
        response = client.get(url + route)
        assert response.status_code == 200
        parser = Assets()
        parser.feed(response.content.decode("utf-8"))
        assert parser.paths and all(p.startswith("/") for p in parser.paths)
        for path in parser.paths:
            assert client.get(url + path).status_code == 200
    page = client.get(url + "/livesearch").content.decode("utf-8")
    assert 'id="live-new-view"' in page and 'id="live-task-view"' in page
    assert 'id="live-result-panel"' in page
    # The JS-free fallback never sends private input via GET.
    assert '<form id="live-form" method="post"' in page
    assert client.get(url + "/livecreate").status_code == 405
    assert client.post(url + "/livecreate", data={"input_type":"email", "query":"alice@example.invalid"}).status_code == 403


def test_all_three_real_request_actions_survive_bootstrap_visibility_rules(alice):
    client, url = alice
    parser = Assets()
    parser.feed(client.get(url + "/privacyaction").content.decode("utf-8"))
    assert {a["data-action"] for a in parser.actions} == {"mask", "hide", "delete"}
    # Bootstrap's .hide forces display:none!important even on an otherwise valid button.
    assert all("hide" not in a.get("class", "").split() for a in parser.actions)


@pytest.mark.parametrize("source,unavailable", [("sherlock",False),("maigret",True),("hibp",True),("",True)])
def test_filtered_empty_results_only_use_relevant_source_status(source, unavailable):
    shown = render({"status":"partial", "results":[], "sources":[
        {"source":"sherlock", "status":"completed"},
        {"source":"maigret", "status":"failed"},
        {"source":"hibp", "status":"not_configured"},
    ]}, source=source)
    if unavailable:
        assert "数据源不可用" in shown["text"]
    else:
        assert "当前数据源未发现匹配" in shown["text"]
        assert "数据源不可用" not in shown["text"]
    assert shown["htmlWrites"] == 0

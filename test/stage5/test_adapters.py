"""Adapters are tested through their public input/output and runner boundary."""
import threading
import pytest

from spiderfoot.live_search import SourceAdapter


class ControlledRunner:
    def __init__(self, reply=None, installed=True, error=None):
        self.reply = reply or {"status": "completed", "items": []}
        self.installed = installed
        self.error = error
        self.calls = []

    def available(self, source):
        return self.installed

    def run(self, source, payload, cancel, timeout):
        self.calls.append((source, payload))
        if self.error:
            raise self.error
        return self.reply


def test_hibp_without_key_does_not_start_worker_or_request(monkeypatch):
    monkeypatch.delenv("SF_HIBP_API_KEY", raising=False)
    runner = ControlledRunner()
    reply = SourceAdapter("hibp", runner).search("email", "alice@example.invalid", threading.Event())
    assert reply["status"] == "not_configured"
    assert reply["results"] == []
    assert runner.calls == []


SOURCES = [("spiderfoot", "domain", "example.org"), ("sherlock", "username", "synthetic_demo"),
           ("maigret", "username", "synthetic_demo"), ("whatsmyname", "username", "synthetic_demo"),
           ("holehe", "email", "alice@example.invalid"), ("hibp", "email", "alice@example.invalid")]


@pytest.mark.parametrize("source,kind,query", SOURCES)
@pytest.mark.parametrize("scenario", ["normal", "empty", "failed", "timeout", "missing"])
def test_each_adapter_reports_independent_outcome_and_uniform_results(source, kind, query, scenario, monkeypatch):
    monkeypatch.setenv("SF_HIBP_API_KEY", "placeholder-not-a-real-key")
    runner = ControlledRunner(
        {"status": "completed", "items": [{"title": "Example", "value": "public evidence",
          "url": "https://example.org/profile", "type": "profile"}]} if scenario == "normal" else None,
        installed=scenario != "missing",
        error=TimeoutError() if scenario == "timeout" else RuntimeError(query) if scenario == "failed" else None,
    )
    result = SourceAdapter(source, runner).search(kind, query, threading.Event())
    assert result["status"] == {"normal":"completed", "empty":"completed", "failed":"failed",
                                "timeout":"timeout", "missing":"not_configured"}[scenario]
    if scenario == "normal":
        item = result["results"][0]
        assert set(item) == {"source", "input_type", "query", "result_type", "title", "value",
                             "original_url", "confidence", "status", "queried_at", "limitations", "raw_summary"}
        assert item["source"] == source and item["query"] == query and item["input_type"] == kind
        assert item["original_url"] == "https://example.org/profile"
        assert item["queried_at"] > 0 and item["limitations"] and item["confidence"]
        if source == "holehe":
            assert item["result_type"] == "email_registration_signal"
            assert "邮箱可能注册过相关网站" in item["limitations"]
    else:
        assert result["results"] == []
        assert query not in result["message"]


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,hi", "file:///C:/secret", "https://u:p@example.org", "//example.org"])
def test_adapter_rejects_unsafe_original_link_protocols(url):
    runner = ControlledRunner({"status": "partial", "items": [{"title": "<img onerror=x>", "url": url}]})
    reply = SourceAdapter("sherlock", runner).search("username", "demo", threading.Event())
    assert reply["status"] == "partial"
    assert reply["results"][0]["original_url"] is None

import threading
import time

import pytest

from spiderfoot.live_search import LiveSearchService


class JobRunner:
    def __init__(self):
        self.running = self.peak = 0
        self.lock = threading.Lock()

    def available(self, source):
        return True

    def run(self, source, payload, cancel, timeout):
        with self.lock:
            self.running += 1
            self.peak = max(self.peak, self.running)
        try:
            cancel.wait(0.15)
            if cancel.is_set():
                return {"status":"cancelled", "items":[]}
            if source == "maigret":
                raise RuntimeError(payload["query"])
            return {"status":"completed", "items":[{"title":"Example", "value":"public signal", "url":"https://example.org"}]}
        finally:
            with self.lock:
                self.running -= 1


def finished(service, owner, task_id):
    end = time.monotonic() + 5
    while time.monotonic() < end:
        task = service.get(owner, task_id)
        if task["status"] not in ("waiting", "running"):
            return task
        time.sleep(.02)
    raise AssertionError("task never completed")


def test_independent_sources_ownership_limits_and_persistence(tmp_path):
    runner = JobRunner()
    path = tmp_path / "jobs.sqlite"
    service = LiveSearchService(path, runner, max_workers=2)
    try:
        task = service.create(2, "username", "synthetic_demo")
        assert service.list(3) == []
        with pytest.raises(KeyError):
            service.get(3, task["id"])
        with pytest.raises(KeyError):
            service.cancel(3, task["id"])
        with pytest.raises(KeyError):
            service.delete(3, task["id"])
        result = finished(service, 2, task["id"])
        assert result["status"] == "partial"
        assert {s["source"]:s["status"] for s in result["sources"]} == {
            "sherlock":"completed", "maigret":"failed", "whatsmyname":"completed"}
        assert len(result["results"]) == 2 and runner.peak <= 2
    finally:
        service.close()
    reopened = LiveSearchService(path, runner)
    try:
        assert len(reopened.get(2, task["id"])["results"]) == 2
        reopened.delete(2, task["id"])
        assert reopened.list(2) == []
    finally:
        reopened.close()


@pytest.mark.parametrize("kind,query", [("email","bad"), ("email","a@example.invalid\nsecret"),
    ("username","--help"), ("username","a/b"), ("phone","13800000000"),
    ("domain","http://user:secret@example.org"), ("domain","https://example.org/?secret=x"),
    ("domain","localhost"), ("domain","127.0.0.1")])
def test_invalid_input_is_rejected_before_any_source(tmp_path, kind, query):
    service = LiveSearchService(tmp_path / "jobs.sqlite", JobRunner())
    try:
        with pytest.raises(ValueError):
            service.create(2, kind, query)
        assert service.list(2) == []
    finally:
        service.close()


def test_cancelled_job_cannot_be_overwritten_by_worker_completion(tmp_path):
    service = LiveSearchService(tmp_path / "jobs.sqlite", JobRunner(), max_workers=1)
    try:
        task = service.create(2, "username", "synthetic_demo")
        service.cancel(2, task["id"])
        state = service.get(2, task["id"])
        assert state["status"] == "cancelled"
        assert all(s["status"] == "cancelled" for s in state["sources"])
        assert state["results"] == []
    finally:
        service.close()


def test_queued_job_cancels_without_waiting_for_another_users_worker(tmp_path):
    entered=threading.Event()
    class BlockingRunner(JobRunner):
        def run(self,source,payload,cancel,timeout):
            entered.set()
            cancel.wait(10)
            return {"status":"cancelled","items":[]}
    service=LiveSearchService(tmp_path/"jobs.sqlite",BlockingRunner(),max_workers=1)
    try:
        service.create(2,"username","synthetic_demo",["sherlock"])
        assert entered.wait(2)
        queued=service.create(3,"email","bob@example.invalid",["holehe"])
        started=time.monotonic()
        result=service.cancel(3,queued["id"])
        assert time.monotonic()-started<1
        assert result["status"]=="cancelled"
    finally:
        service.close()

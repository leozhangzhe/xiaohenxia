"""Actual process trees are terminated on timeout and cancellation."""
import json
from pathlib import Path
import sys
import threading
import time

import psutil
import pytest

from spiderfoot.live_process import ProcessRunner


@pytest.mark.parametrize("mode", ["timeout", "cancel"])
def test_timeout_and_cancel_close_worker_and_its_child(tmp_path, mode):
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import sys,json,subprocess,time,os\n"
        "p=json.loads(sys.stdin.readline())\n"
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\n"
        "open(p['pid_file'],'w').write(json.dumps([os.getpid(),child.pid]))\n"
        "time.sleep(60)\n", encoding="utf-8")
    pids = tmp_path / "pids.json"
    runner = ProcessRunner(tmp_path, worker=worker, interpreters={"sherlock": Path(sys.executable)})
    cancel = threading.Event()
    timer = threading.Timer(1.5, cancel.set) if mode == "cancel" else None
    if timer:
        timer.start()
    started = time.monotonic()
    try:
        if mode == "timeout":
            with pytest.raises(TimeoutError):
                runner.run("sherlock", {"query": "synthetic_demo", "pid_file": str(pids)}, cancel, 1.5)
        else:
            assert runner.run("sherlock", {"query": "synthetic_demo", "pid_file": str(pids)}, cancel, 10)["status"] == "cancelled"
    finally:
        if timer:
            timer.cancel()
    assert time.monotonic() - started < 6
    assert pids.exists(), "the real worker and child must have started"
    for pid in json.loads(pids.read_text()):
        assert not psutil.pid_exists(pid), "source child process was left running"


def test_worker_receives_sensitive_query_only_through_stdin(tmp_path):
    worker = tmp_path / "worker.py"
    worker.write_text("import sys,json\np=json.loads(sys.stdin.readline())\n"
                      "assert p['query'] not in ' '.join(sys.argv)\n"
                      "print(json.dumps({'status':'completed','items':[]}))\n", encoding="utf-8")
    runner = ProcessRunner(tmp_path, worker=worker, interpreters={"holehe": Path(sys.executable)})
    assert runner.run("holehe", {"query": "alice@example.invalid"}, threading.Event(), 5)["status"] == "completed"

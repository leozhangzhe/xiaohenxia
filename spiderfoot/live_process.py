"""Bounded, stdin-only source workers with owned process-tree cleanup."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


class WindowsJob:
    def __init__(self, process):
        class Basic(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
                        ("flags", wintypes.DWORD), ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t),
                        ("active", wintypes.DWORD), ("affinity", ctypes.c_size_t),
                        ("priority", wintypes.DWORD), ("scheduling", wintypes.DWORD)]
        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", ctypes.c_ulonglong * 6),
                        ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                        ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        api.CreateJobObjectW.restype = wintypes.HANDLE
        api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api = api
        self.handle = api.CreateJobObjectW(None, None)
        info = Extended()
        info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not api.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise OSError("Cannot create source process job")
        # Workers wait on stdin before importing tools/spawning descendants.
        if not api.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle))):
            self.close()
            raise OSError("Cannot contain source process")

    def close(self):
        if getattr(self, "handle", None):
            self.api.CloseHandle(self.handle)
            self.handle = None


class ProcessRunner:
    def __init__(self, root, config=None, worker=None, interpreters=None):
        self.root = Path(root).resolve()
        self.config = config or {}
        self.worker = Path(worker) if worker else self.root / "spiderfoot/live_worker.py"
        self.interpreters = interpreters

    def python(self, source):
        if self.interpreters is not None:
            return self.interpreters.get(source, Path("missing-python"))
        if source in ("sherlock", "maigret", "holehe"):
            return self.root / ".tools/live" / source / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        return Path(sys.executable)

    def available(self, source):
        if source == "whatsmyname":
            return (self.root / ".tools/live/whatsmyname/wmn-data.json").is_file()
        python = self.python(source)
        if not python.is_file():
            return False
        if self.interpreters is not None or source not in ("sherlock", "maigret", "holehe"):
            return True
        package = "sherlock_project" if source == "sherlock" else source
        base = python.parent.parent
        return (base / "Lib/site-packages" / package).is_dir() if os.name == "nt" else bool(list(base.glob("lib/python*/site-packages/" + package)))

    def run(self, source, payload, cancel, timeout):
        runtime = self.root / ".runtime-profile/live-work"
        runtime.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix=source + "-", dir=runtime))
        env = {key: value for key, value in os.environ.items() if key.upper() in (
            "PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC", "PATHEXT",
            "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE")}
        env.update({"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1",
                    "SPIDERFOOT_DATA": str(work), "SPIDERFOOT_CACHE": str(work / "cache"),
                    "SPIDERFOOT_LOGS": str(work / "logs")})
        if source == "hibp":
            env["SF_HIBP_API_KEY"] = os.environ.get("SF_HIBP_API_KEY", "")
        payload = dict(payload, work_dir=str(work))
        process = subprocess.Popen([str(self.python(source)), "-B", str(self.worker), source],
            cwd=self.root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            creationflags=(subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0,
            start_new_session=os.name != "nt")
        job = None
        try:
            if os.name == "nt":
                job = WindowsJob(process)
            started = time.monotonic()
            data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
            while True:
                if cancel.is_set():
                    return {"status": "cancelled", "items": []}
                if time.monotonic() - started > timeout:
                    raise TimeoutError("Source deadline exceeded")
                try:
                    output, _ = process.communicate(input=data, timeout=0.1)
                    if process.returncode or len(output) > 2_000_000:
                        raise RuntimeError("Source worker failed")
                    return json.loads(output.decode("utf-8"))
                except subprocess.TimeoutExpired:
                    data = None
        finally:
            if job:
                job.close()
            elif os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3)

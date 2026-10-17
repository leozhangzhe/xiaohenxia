"""Isolate stage-five filesystem and authentication from local user data."""
from test.stage1.conftest import default_options  # noqa: F401
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import pytest
import requests


@pytest.fixture(scope="module")
def http_server(tmp_path_factory):
    folder = tmp_path_factory.mktemp("stage5-http")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1",0))
        port = listener.getsockname()[1]
    env = os.environ.copy()
    env.update({"SF_AUTH_MYSQL_USER":"boundary", "SF_AUTH_MYSQL_PASSWORD":"Boundary-Only-4387",
                "SF_AUTH_MYSQL_DATABASE":"stage5_boundary", "SF_AUTH_ADMIN_USER":"admin",
                "SF_AUTH_ADMIN_PASS":"StageTwo-Admin-4387", "SF_AUTH_ADMIN_RESET":"0", "SF_AUTH_COOKIE_SECURE":"0",
                "STAGE2_AUTH_DB":str(folder / "auth.sqlite"), "STAGE2_SCAN_DB":str(folder / "scans.sqlite"),
                "PYTHONIOENCODING":"utf-8", "PYTHONDONTWRITEBYTECODE":"1", "SF_HIBP_API_KEY":""})
    env.pop("STAGE5_REAL_SOURCES", None)
    env.pop("STAGE5_REAL_MYSQL", None)
    for key in ("SPIDERFOOT_DATA","SPIDERFOOT_CACHE","SPIDERFOOT_LOGS"):
        (folder / key).mkdir()
        env[key] = str(folder / key)
    url = f"http://127.0.0.1:{port}"
    log = folder / "server.log"
    with log.open("w",encoding="utf-8") as output:
        process = subprocess.Popen([sys.executable,"-B","-m","test.stage5.http_runner",str(port)],
            cwd=Path(__file__).resolve().parents[2],env=env,stdout=output,stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic()+20
            client = requests.Session()
            client.trust_env = False
            while time.monotonic()<deadline:
                try:
                    if client.get(url+"/login",timeout=1).status_code==200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(.1)
            else:
                pytest.fail("Stage5 HTTP fixture did not start")
            yield url,log,Path(env["STAGE2_AUTH_DB"]),Path(env["STAGE2_SCAN_DB"])
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)

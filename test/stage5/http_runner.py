"""A real Web server; controlled outputs replace only the external process boundary."""
import logging
import os
from pathlib import Path
from queue import Queue
import sys

import pymysql
from test.stage1.conftest import MySQLBoundary
from test.stage5.test_jobs import JobRunner


if __name__ == "__main__":
    if os.environ.get("STAGE5_REAL_MYSQL") != "1":
        pymysql.connect = MySQLBoundary(Path(os.environ["STAGE2_AUTH_DB"])).connect
    if os.environ.get("STAGE5_REAL_SOURCES") != "1":
        import spiderfoot.live_process
        spiderfoot.live_process.ProcessRunner = lambda *a, **kw: JobRunner()
    from spiderfoot.auth_mysql import MySQLAuthStore
    store = MySQLAuthStore(logging.getLogger("stage5.fixture"))
    store.initialize()
    for username in ("alice", "bob"):
        store.create_user(username, "StageTwo-HTTP-Password-4387")
    from sf import start_web_server
    config = {"__database":os.environ["STAGE2_SCAN_DB"], "__modules__":{},
              "__globaloptdescs__":{}, "__logging":False, "_debug":False}
    start_web_server({"host":"127.0.0.1", "port":int(sys.argv[1]), "root":"/"}, config, Queue())

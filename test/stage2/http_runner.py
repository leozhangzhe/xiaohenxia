"""Seed test resources at the storage boundary, then run the real server."""
import os
import logging
from pathlib import Path
from queue import Queue
import sqlite3
import sys

import pymysql

from test.stage1.conftest import MySQLBoundary


if __name__ == "__main__":
    real_mysql = os.environ.get("STAGE2_REAL_MYSQL") == "1"
    if not real_mysql:
        pymysql.connect = MySQLBoundary(Path(os.environ["STAGE2_AUTH_DB"])).connect
    from spiderfoot.auth_mysql import MySQLAuthStore
    from spiderfoot import SpiderFootDb
    store = MySQLAuthStore(logging.getLogger("stage2-fixture"))
    store.initialize()
    for username in ("alice", "bob"):
        store.create_user(username, "StageTwo-HTTP-Password-4387")
    config = {
        "__database": os.environ["STAGE2_SCAN_DB"], "__modules__": {},
        "__globaloptdescs__": {}, "__logging": False, "_debug": True,
    }
    db = SpiderFootDb(config, init=True)
    db.scanInstanceCreate("a" * 32, "Alice scan", "alice.private@example.org")
    db.scanInstanceCreate("b" * 32, "Bob scan", "bob.private@example.org")
    db.scanInstanceCreate("c" * 32, "Legacy scan", "legacy@example.org")
    for sid in ("a" * 32, "b" * 32, "c" * 32):
        db.scanInstanceSet(sid, status="FINISHED")
    db.close()
    # Resource fixtures with known principal IDs: admin=1, alice=2, bob=3.
    with sqlite3.connect(config["__database"]) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS web_scan_owners (scan_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL)")
        connection.executemany("INSERT INTO web_scan_owners VALUES (?,?)", [("a" * 32, 2), ("b" * 32, 3)])
    # Exercise the non-destructive migration from the pre-user_id privacy schema.
    with sqlite3.connect(os.environ["STAGE2_AUTH_DB"]) as connection:
        connection.execute("""CREATE TABLE privacy_actions (
            id TEXT PRIMARY KEY, username TEXT NOT NULL, action_type TEXT NOT NULL,
            platform TEXT NOT NULL, content TEXT NOT NULL, masked_content TEXT,
            status TEXT NOT NULL, note TEXT DEFAULT '', created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL)""")
        connection.execute(
            "INSERT INTO privacy_actions VALUES (?,?,?,?,?,?,?,?,?,?)",
            ("legacy-action-id", "alice", "hide", "example.invalid", "legacy-private@example.invalid",
             None, "processing", "legacy record", 1, 1),
        )
    from sf import start_web_server
    start_web_server({"host": "127.0.0.1", "port": int(sys.argv[1]), "root": "/"}, config, Queue())


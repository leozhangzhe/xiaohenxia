"""Run the real HTTP entry point with only the external DB replaced."""
import os
from pathlib import Path
from queue import Queue
import sys

import pymysql

from test.stage1.conftest import MySQLBoundary


class OutageBoundary(MySQLBoundary):
    def connect(self, **kwargs):
        self.available = not Path(os.environ["STAGE1_OUTAGE_MARKER"]).exists()
        return super().connect(**kwargs)


if __name__ == "__main__":
    boundary = OutageBoundary(Path(os.environ["STAGE1_BOUNDARY_DB"]))
    pymysql.connect = boundary.connect
    from sf import start_web_server
    config = {
        "__database": os.environ["STAGE1_SCAN_DB"],
        "__modules__": {}, "__logging": False, "_debug": False,
    }
    start_web_server({"host": "127.0.0.1", "port": int(sys.argv[1]), "root": "/"}, config, Queue())

"""A disposable MySQL instance: new data only, preserved after the test."""
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time

import pymysql


ROOT = Path(__file__).resolve().parents[2]


class LiveMySQL:
    def __init__(self, folder):
        self.folder = folder
        self.password = secrets.token_urlsafe(32)
        self.process = None
        self.output = None
        self.letter = next((c for c in "ZYXWVUTSRQ" if not Path(c + ":/").exists()), None)
        if not self.letter:
            raise RuntimeError("No free temporary drive letter for the MySQL test")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]
        self.binary = f"{self.letter}:/.mysql/mysql-8.0.46-winx64/bin/mysqld.exe"
        # MySQL accepts an absolute Windows datadir. Tests commonly use pytest's
        # temp path on a different volume, so requiring it to be below ROOT
        # turned a fixture configuration detail into an unrelated test failure.
        data_dir = folder.resolve().as_posix()
        self.common = [
            "--no-defaults", f"--basedir={self.letter}:/.mysql/mysql-8.0.46-winx64",
            f"--datadir={data_dir}/data", "--innodb-undo-log-truncate=OFF",
        ]

    def initialize(self):
        if os.name != "nt" or not (ROOT / ".mysql/mysql-8.0.46-winx64/bin/mysqld.exe").is_file():
            raise RuntimeError("The real MySQL test requires the existing Windows MySQL 8.0.46 binary")
        subprocess.run(["subst.exe", self.letter + ":", str(ROOT)], check=True, capture_output=True)
        result = subprocess.run(
            [self.binary, *self.common, "--initialize-insecure", "--console"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45,
        )
        (self.folder / "initialize.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError("Isolated MySQL initialization failed; see its initialize.log")
        self.start()
        with self.connect(password="") as conn:
            with conn.cursor() as cursor:
                cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (self.password,))

    def start(self):
        self.output = (self.folder / "server.log").open("a", encoding="utf-8")
        self.process = subprocess.Popen([
            self.binary, *self.common, "--console", f"--port={self.port}",
            "--bind-address=127.0.0.1", "--mysqlx=0", "--skip-log-bin",
        ], cwd=f"{self.letter}:/", stdout=self.output, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("Isolated MySQL startup failed; see its server.log")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.2)
        raise RuntimeError("Isolated MySQL startup timed out")

    def connect(self, password=None):
        return pymysql.connect(
            host="127.0.0.1", port=self.port, user="root",
            password=self.password if password is None else password,
            autocommit=True, connect_timeout=5,
        )

    def stop(self):
        if self.process and self.process.poll() is None:
            with self.connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHUTDOWN")
            self.process.wait(timeout=15)
        if self.output:
            self.output.close()
            self.output = None

    def close(self):
        try:
            self.stop()
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=10)
            if self.output:
                self.output.close()
            subprocess.run(["subst.exe", self.letter + ":", "/d"], check=True, capture_output=True)

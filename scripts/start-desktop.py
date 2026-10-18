"""Persistent Windows desktop launcher. Own processes/data only; no default passwords."""
import argparse
import ctypes
from ctypes import wintypes
import getpass
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import webbrowser

import pymysql
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PROFILE = ROOT / ".runtime-profile" / "desktop"


class LaunchError(Exception):
    pass


def crypt(data, decrypt=False):
    """DPAPI current-user protection; ciphertext cannot be used by another Windows user."""
    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buf = ctypes.create_string_buffer(data)
    incoming = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = Blob()
    library = ctypes.WinDLL("crypt32", use_last_error=True)
    free = ctypes.WinDLL("kernel32", use_last_error=True).LocalFree
    free.argtypes = [ctypes.c_void_p]
    if decrypt:
        ok = library.CryptUnprotectData(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing))
    else:
        ok = library.CryptProtectData(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing))
    if not ok:
        raise LaunchError("无法读取 Windows 加密配置。请用首次配置时的 Windows 用户运行；原数据库已保留。")
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        free(ctypes.cast(outgoing.data, ctypes.c_void_p))


def load_config(profile):
    try:
        config = json.loads(crypt((profile / "connection.dpapi").read_bytes(), decrypt=True))
        if config.get("version") != 1 or not config.get("password") or not 1 <= int(config["port"]) <= 65535:
            raise ValueError()
        return config
    except LaunchError:
        raise
    except (OSError, ValueError, KeyError, TypeError):
        raise LaunchError("本地配置缺失或损坏；不会重建或清空已有数据库。") from None


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def admin_password():
    from spiderfoot.auth_mysql import MySQLAuthStore, AuthConfigurationError
    while True:
        password = getpass.getpass("首次配置：设置管理员 admin 密码（至少12位，含字母及数字或符号）：")
        try:
            MySQLAuthStore._validate_admin_password(password)
        except AuthConfigurationError:
            print("密码需为12–1024位，包含字母以及数字或非空白符号。")
            continue
        if password == getpass.getpass("再次输入管理员密码："):
            return password
        print("两次输入不一致，请重新设置。")


class DesktopServer:
    def __init__(self, profile=PROFILE, port=5001):
        self.profile = Path(profile).resolve()
        if not self.profile.is_relative_to(ROOT / ".runtime-profile"):
            raise LaunchError("本地工作区必须位于项目 .runtime-profile 目录内。")
        self.port = port
        self.mysql = self.web = self.output = None
        self.drive = None
        self.config = None
        self.env = None

    def start(self, password_provider=admin_password):
        binary = ROOT / ".mysql/mysql-8.0.46-winx64/bin/mysqld.exe"
        if not binary.is_file():
            raise LaunchError("缺少项目内 MySQL 8.0.46。请恢复官方 MySQL 压缩包至 .mysql；不会自动下载或使用其他数据库。")
        self.profile.mkdir(parents=True, exist_ok=True)
        config_file = self.profile / "connection.dpapi"
        data = self.profile / "mysql" / "data"
        first = not config_file.exists()
        if first and data.exists():
            raise LaunchError("发现已有 MySQL 数据，但缺少加密连接配置。已停止，原文件全部保留，请恢复 connection.dpapi。")
        admin = password_provider() if first else None
        self.config = {"version": 1, "port": free_port(), "password": secrets.token_urlsafe(32)} if first else load_config(self.profile)
        if first:
            # Save before initialization: interrupted initialization never triggers an automatic reset.
            config_file.write_bytes(crypt(json.dumps(self.config).encode("utf-8")))
        elif not (data / "mysql").is_dir():
            raise LaunchError("数据库目录缺失或初始化不完整；已停止，不会重建。请保留文件并检查 mysql/server.log。")
        self.drive = next((c for c in "ZYXWVUTSRQ" if not Path(c + ":/").exists()), None)
        if not self.drive:
            raise LaunchError("没有可用的临时盘符。请释放 Q–Z 中一个未使用盘符后重试。")
        subprocess.run(["subst.exe", self.drive + ":", str(ROOT)], capture_output=True, check=True)
        base = self.drive + ":/.mysql/mysql-8.0.46-winx64"
        mapped = self.drive + ":/" + data.relative_to(ROOT).as_posix()
        common = ["--no-defaults", "--basedir=" + base, "--datadir=" + mapped, "--innodb-undo-log-truncate=OFF"]
        mysql_dir = data.parent
        mysql_dir.mkdir(exist_ok=True)
        self.output = (mysql_dir / "server.log").open("a", encoding="utf-8")
        if first:
            print("正在初始化独立本地数据库（仅首次，约20秒）……", flush=True)
            result = subprocess.run([base + "/bin/mysqld.exe", *common, "--initialize-insecure", "--console"], stdout=self.output, stderr=subprocess.STDOUT, timeout=90)
            if result.returncode:
                raise LaunchError("MySQL 初始化失败。原文件已保留，详见 .runtime-profile/desktop/mysql/server.log。")
        self.mysql = subprocess.Popen([base + "/bin/mysqld.exe", *common, "--console", "--port=" + str(self.config["port"]), "--bind-address=127.0.0.1", "--mysqlx=0", "--skip-log-bin"], cwd=self.drive + ":/", stdout=self.output, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 30
        while True:
            if self.mysql.poll() is not None:
                raise LaunchError("本地 MySQL 未能启动，请查看 mysql/server.log；不会切换到内存账号库。")
            try:
                conn = pymysql.connect(host="127.0.0.1", port=self.config["port"], user="root", password="" if first else self.config["password"], connect_timeout=2, autocommit=True)
                break
            except pymysql.MySQLError:
                if time.monotonic() > deadline:
                    raise LaunchError("本地 MySQL 连接失败，请检查 mysql/server.log。") from None
                time.sleep(.25)
        with conn:
            if first:
                with conn.cursor() as cursor:
                    cursor.execute("ALTER USER 'root'@'localhost' IDENTIFIED BY %s", (self.config["password"],))
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("SF_AUTH_", "STAGE1_", "STAGE2_", "STAGE5_"))}
        self.env.update(SF_AUTH_MYSQL_HOST="127.0.0.1", SF_AUTH_MYSQL_PORT=str(self.config["port"]), SF_AUTH_MYSQL_USER="root", SF_AUTH_MYSQL_PASSWORD=self.config["password"], SF_AUTH_MYSQL_DATABASE="xiaohenxia_desktop", SF_AUTH_ADMIN_USER="admin", SF_AUTH_COOKIE_SECURE="0", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        for key, name in [("SPIDERFOOT_DATA", "data"), ("SPIDERFOOT_LOGS", "logs"), ("SPIDERFOOT_CACHE", "cache")]:
            folder = self.profile / name
            folder.mkdir(exist_ok=True)
            self.env[key] = str(folder)
        if first:
            self.env["SF_AUTH_ADMIN_PASS"] = admin
        with (self.profile / "web.log").open("a", encoding="utf-8") as output:
            checked = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/auth_admin.py"), "--initialize" if first else "--check"], env=self.env, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
        self.env.pop("SF_AUTH_ADMIN_PASS", None)
        admin = None
        if checked.returncode:
            raise LaunchError("账号数据库检查失败，详见 .runtime-profile/desktop/web.log；不会重置账号。")

    def start_web(self):
        self.web_log = (self.profile / "web.log").open("a", encoding="utf-8")
        self.web = subprocess.Popen([sys.executable, "-B", str(ROOT / "sf.py"), "-l", "127.0.0.1:" + str(self.port)], env=self.env, cwd=ROOT, stdout=self.web_log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        client = requests.Session()
        client.trust_env = False
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if self.web.poll() is not None:
                break
            try:
                if client.get(self.url, timeout=2).status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(.3)
        raise LaunchError("Web 未能启动，请查看 .runtime-profile/desktop/web.log。")

    @property
    def url(self):
        return "http://127.0.0.1:" + str(self.port) + "/login"

    def close(self):
        # Stop only subprocesses created and retained by this launcher.
        if self.web and self.web.poll() is None:
            import signal
            try:
                self.web.send_signal(signal.CTRL_BREAK_EVENT)
                self.web.wait(timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                self.web.terminate()
                self.web.wait(timeout=10)
        if getattr(self, "web_log", None):
            self.web_log.close()
        if self.mysql and self.mysql.poll() is None:
            try:
                with pymysql.connect(host="127.0.0.1", port=self.config["port"], user="root", password=self.config["password"], connect_timeout=3) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SHUTDOWN")
                self.mysql.wait(timeout=25)
            except (pymysql.MySQLError, OSError, subprocess.TimeoutExpired):
                self.mysql.terminate()
                self.mysql.wait(timeout=10)
        if self.output:
            self.output.close()
        if self.drive:
            subprocess.run(["subst.exe", self.drive + ":", "/d"], capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="消痕侠本地持久工作区：首次设置管理员，以后直接启动。")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        print("此双击启动器仅用于 Windows；其他平台请使用现有环境变量启动方式。")
        return 1
    import msvcrt
    PROFILE.mkdir(parents=True, exist_ok=True)
    guard = (PROFILE / "launch.lock").open("a+b")
    if guard.tell() == 0:
        guard.write(b"0")
        guard.flush()
    guard.seek(0)
    try:
        msvcrt.locking(guard.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        guard.close()
        print("持久工作区已在其他启动窗口运行，请使用原窗口。")
        return 1
    server = DesktopServer()
    # Check before prompting or touching data. Do not mistake a different service for our app.
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", server.port))
        except OSError:
            print("5001 端口已被占用。若项目正在运行，请直接访问 " + server.url)
            print("如需启动持久工作区，请先在原启动窗口按 Ctrl+C；不会关闭其他进程。")
            guard.close()
            return 1
    try:
        server.start()
        server.start_web()
        print("\n消痕侠已启动：" + server.url, flush=True)
        print("管理员：admin；密码为首次设置的密码。普通用户也可在页面注册。")
        print("账号和记录保存在 .runtime-profile/desktop，重启会保留。")
        print("请保留此窗口。退出时按 Ctrl+C，等待“已安全停止”后再关闭。", flush=True)
        if not args.no_browser:
            webbrowser.open(server.url)
        while server.web.poll() is None:
            time.sleep(.5)
        raise LaunchError("Web 已退出，请查看 .runtime-profile/desktop/web.log。")
    except KeyboardInterrupt:
        print("\n正在停止本次启动的 Web 和 MySQL，请稍候……", flush=True)
        return 0
    except LaunchError as exc:
        print("启动失败：" + str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("启动失败：请检查本地依赖和 .runtime-profile/desktop 日志；已有数据均保留。", file=sys.stderr)
        return 1
    finally:
        server.close()
        guard.close()
        print("已安全停止。")


if __name__ == "__main__":
    raise SystemExit(main())

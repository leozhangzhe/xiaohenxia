"""Operator-facing configuration and startup process contracts."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]


def isolated_env(tmp_path):
    env = os.environ.copy()
    for name in list(env):
        if name.startswith("SF_AUTH_"):
            env.pop(name)
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "SPIDERFOOT_DATA": str(tmp_path / "data"),
        "SPIDERFOOT_LOGS": str(tmp_path / "logs"),
        "SPIDERFOOT_CACHE": str(tmp_path / "cache"),
    })
    return env


def test_startup_requires_operator_database_credentials(tmp_path):
    result = subprocess.run([
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "scripts/start-local.ps1"), "-CheckOnly",
    ], cwd=tmp_path, env=isolated_env(tmp_path), capture_output=True, timeout=20)
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    assert result.returncode != 0
    assert "SF_AUTH_MYSQL_USER" in output


def test_configuration_check_fails_without_exposing_a_database_password(tmp_path):
    env = isolated_env(tmp_path)
    env.update({
        "SF_AUTH_MYSQL_HOST": "127.0.0.1", "SF_AUTH_MYSQL_PORT": "1",
        "SF_AUTH_MYSQL_USER": "test_missing_user", "SF_AUTH_MYSQL_PASSWORD": "NeverPrint-This-Test-Secret",
    })
    result = subprocess.run([
        sys.executable, "-B", str(ROOT / "scripts/auth_admin.py"), "--check",
    ], cwd=tmp_path, env=env, capture_output=True, timeout=15)
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    assert result.returncode != 0
    assert "authentication database" in output
    assert env["SF_AUTH_MYSQL_PASSWORD"] not in output
    assert "Traceback" not in output


def test_legacy_plaintext_password_authentication_cannot_be_enabled(tmp_path):
    env = isolated_env(tmp_path)
    env.update({"SF_LEGACY_PASSWD_AUTH": "1", "SF_AUTH_MYSQL_PORT": "1"})
    result = subprocess.run([sys.executable, "-B", "sf.py", "-l", "127.0.0.1:59999"],
                            cwd=ROOT, env=env, capture_output=True, timeout=20)
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    assert result.returncode != 0
    assert "plaintext password authentication is disabled" in output


@pytest.mark.parametrize("entry", ["启动平台.bat", "启动本地版.bat", "启动本地版.ps1"])
def test_existing_launchers_preserve_failure_exit_codes_from_another_directory(tmp_path, entry):
    if entry.endswith(".ps1"):
        command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / entry), "-CheckOnly"]
    else:
        command = ["cmd.exe", "/d", "/c", str(ROOT / entry), "-CheckOnly"]
    result = subprocess.run(command, cwd=tmp_path, env=isolated_env(tmp_path), capture_output=True, timeout=20)
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    assert result.returncode != 0
    assert "SF_AUTH_MYSQL_USER" in output

"""Regression for the Python 3.12 CLI collection/startup blocker."""
from pathlib import Path
import subprocess
import sys


def test_cli_import_and_readline_public_api_work_in_a_fresh_process():
    root = Path(__file__).resolve().parents[2]
    probe = subprocess.run(
        [sys.executable, '-B', '-c',
         'import sfcli, readline; '
         'assert callable(readline.add_history); '
         'assert callable(readline.get_current_history_length); '
         'assert sfcli.SpiderFootCli().complete_start(None,None,None,None) == []; '
         'print("CLI_STARTUP_OK")'],
        cwd=root, capture_output=True, text=True, timeout=20,
    )
    assert probe.returncode == 0, probe.stderr
    assert 'CLI_STARTUP_OK' in probe.stdout

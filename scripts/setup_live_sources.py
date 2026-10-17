"""Rebuild project-local source environments from pinned package versions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import venv

ROOT = Path(__file__).resolve().parents[1]
WMN_URL = 'https://raw.githubusercontent.com/WebBreacher/WhatsMyName/ec273f81aa1b8728a932589dcba71c6894001acc/wmn-data.json'
WMN_SHA256 = '8893631e8bf0cab4dc846c6fbfb4010c83187384b438b0c99091329e2ce07afa'


def python_at(folder):
    return folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--include-app', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    env = dict(os.environ, PIP_CACHE_DIR=str(ROOT / '.cache/live-pip'), PYTHONNOUSERSITE='1')
    if args.check:
        for source in ('sherlock', 'maigret', 'holehe'):
            python = python_at(ROOT / '.tools/live' / source)
            if not python.is_file():
                raise SystemExit(source + ': not installed; rerun without --check')
            subprocess.run([str(python), '-m', 'pip', 'check'], check=True, env=env)
            print(source + ': installed')
        rules = ROOT / '.tools/live/whatsmyname/wmn-data.json'
        if not rules.is_file() or hashlib.sha256(rules.read_bytes()).hexdigest() != WMN_SHA256:
            raise SystemExit('WhatsMyName rules missing or checksum mismatch')
        print('WhatsMyName: pinned rules verified; HIBP uses application environment variable SF_HIBP_API_KEY.')
        return
    if args.include_app:
        app = ROOT / '.venv'
        if not python_at(app).is_file():
            venv.EnvBuilder(with_pip=True).create(app)
        subprocess.run([str(python_at(app)), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')], check=True, env=env)
        frontend = ROOT / 'spiderfoot/static'
        npm = 'npm.cmd' if os.name == 'nt' else 'npm'
        if (frontend / 'node_modules').exists():
            # npm ci removes an existing node_modules tree. Preserve local
            # files instead and report incomplete existing installations.
            subprocess.run([npm, 'ls', '--depth=0'], cwd=frontend, check=True, env=env)
        else:
            subprocess.run([npm, 'ci', '--ignore-scripts', '--no-audit', '--no-fund',
                            '--cache', str(ROOT / '.cache/live-npm')], cwd=frontend, check=True, env=env)
    for source in ('sherlock', 'maigret', 'holehe'):
        folder = ROOT / '.tools/live' / source
        if not python_at(folder).is_file():
            venv.EnvBuilder(with_pip=True).create(folder)
        subprocess.run([str(python_at(folder)), '-m', 'pip', 'install', '--disable-pip-version-check',
                        '-r', str(ROOT / 'scripts/live-source-locks' / (source + '.txt'))], check=True, env=env)
    # Official data only, pinned to a commit with an independent checksum.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(WMN_URL, timeout=30) as response:
        data = response.read(2_000_000)
    if hashlib.sha256(data).hexdigest() != WMN_SHA256:
        raise SystemExit('Official WhatsMyName rules checksum mismatch; existing rules preserved.')
    parsed = json.loads(data)
    if not isinstance(parsed.get('sites'), list):
        raise SystemExit('Invalid WhatsMyName rules; existing rules preserved.')
    rules = ROOT / '.tools/live/whatsmyname/wmn-data.json'
    rules.parent.mkdir(parents=True, exist_ok=True)
    rules.write_bytes(data)
    print('Isolated live-source dependencies rebuilt. No searches were run.')


if __name__ == '__main__':
    main()

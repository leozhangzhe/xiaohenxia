"""Competition package bootstrap: local environments, prebuilt assets, verified MySQL ZIP.

No Node.js, existing databases, global installs or automatic binary downloads.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mysql-archive', type=Path, help='Official mysql-8.0.46-winx64.zip, explicitly downloaded by operator')
    parser.add_argument('--skip-live-sources', action='store_true', help='Only install main app; missing tools remain visibly uninstalled')
    parser.add_argument('--wheelhouse', type=Path, help='Optional operator-prepared offline Python wheel directory')
    args = parser.parse_args()
    if os.name != 'nt' or sys.version_info[:2] != (3, 12):
        raise SystemExit('Validated release requires Windows x64 and Python 3.12 (tested 3.12.10).')
    manifest = json.loads((ROOT / 'third_party/runtime-assets/manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        source = ROOT / 'third_party/runtime-assets/files' / entry['path']
        if hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
            raise SystemExit('Runtime asset checksum mismatch: ' + entry['path'])
        target = ROOT / 'spiderfoot/static/node_modules' / entry['path']
        if target.exists() and target.read_bytes() != source.read_bytes():
            raise SystemExit('Existing asset differs; preserved: ' + entry['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
    mysql = ROOT / '.mysql/mysql-8.0.46-winx64'
    if not (mysql / 'bin/mysqld.exe').is_file():
        if not args.mysql_archive:
            raise SystemExit('MySQL missing. Read README: download official ZIP, then pass --mysql-archive <path>. No binary is downloaded automatically.')
        expected = json.loads((ROOT / 'third_party/mysql-artifact.json').read_text(encoding='utf-8'))
        digest = hashlib.file_digest(args.mysql_archive.open('rb'), 'sha256').hexdigest()
        if digest != expected['sha256']:
            raise SystemExit('MySQL archive SHA-256 mismatch; no files extracted.')
        with zipfile.ZipFile(args.mysql_archive) as archive:
            for item in archive.infolist():
                destination = (ROOT / '.mysql' / item.filename).resolve()
                if not destination.is_relative_to(mysql) or destination.exists():
                    raise SystemExit('Unsafe archive path or existing partial installation; preserved, inspect manually.')
            archive.extractall(ROOT / '.mysql')
    python = ROOT / '.venv/Scripts/python.exe'
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(ROOT / '.venv')
    env = dict(os.environ, PIP_CACHE_DIR=str(ROOT / '.cache/release-pip'), PYTHONNOUSERSITE='1')
    options = ['--no-index', '--find-links', str(args.wheelhouse.resolve())] if args.wheelhouse else []
    subprocess.run([str(python), '-m', 'pip', 'install', *options, '-r', str(ROOT / 'requirements-release-win-py312.lock.txt')], env=env, check=True)
    subprocess.run([str(python), '-m', 'pip', 'check'], env=env, check=True)
    if not args.skip_live_sources:
        # Existing source bootstrap installs only isolated Python tools and official pinned rules.
        # --include-app is intentionally NOT passed, so npm is never invoked.
        if args.wheelhouse:
            env.update(PIP_NO_INDEX='1', PIP_FIND_LINKS=str(args.wheelhouse.resolve()))
        subprocess.run([str(python), '-B', str(ROOT / 'scripts/setup_live_sources.py')], env=env, check=True)
    print('Installation complete. Run 双击启动.bat; set your own admin password on first launch.')


if __name__ == '__main__':
    main()

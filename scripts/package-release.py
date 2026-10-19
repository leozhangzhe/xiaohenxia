"""Build an allowlisted, audited source ZIP from immutable Git blobs, never a directory dump."""
import argparse
import datetime
import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', '.cache',
                  '.tools', '.runtime-profile', '.stage1', '.stage2', '.stage3', '.stage4', '.stage5', '.stage6',
                  '.github', '.impeccable', 'tmp', 'temp', 'logs', 'results'}
EXCLUDED_SUFFIXES = {'.zip', '.7z', '.gz', '.exe', '.dll', '.pyc', '.log', '.tmp', '.temp', '.pid',
                     '.dpapi', '.sqlite', '.sqlite3', '.db', '.wal', '.shm', '.docx', '.pem', '.key', '.session', '.cookie'}
SECRET_RULES = {
    'private-key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'aws-access-key': rb'\bAKIA[0-9A-Z]{16}\b',
    'github-token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b',
    'openai-token': rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b',
    'literal-api-secret': rb'''(?i)(?:api[_-]?key|api[_-]?secret|access[_-]?token)["']?\s*[:=]\s*["']([A-Za-z0-9_/-]{24,})["']''',
}


def allowed(name):
    parts = PurePosixPath(name).parts
    if name == 'data/leak-check.db' or name == '.env.example':
        return True
    return not (any(p in EXCLUDED_PARTS or p.startswith(('.mysql', '.runtime', '.stage')) for p in parts)
                or any(p.startswith('.env') for p in parts)
                or PurePosixPath(name).suffix.lower() in EXCLUDED_SUFFIXES
                or any(fnmatch.fnmatch(parts[-1].lower(), pattern) for pattern in
                       ('*credentials*', '*secrets.json', '*.db-wal', '*.db-shm', '*.sqlite-wal', '*.sqlite-shm', '*acceptance*.log')))


def audit(files):
    findings = []
    for name, data in files.items():
        if not allowed(name):
            findings.append({'file': name, 'line': 0, 'type': 'excluded-runtime-file'})
            continue
        for kind, pattern in SECRET_RULES.items():
            for match in re.finditer(pattern, data):
                # Source fixtures are explicitly synthetic, never deployed credentials.
                literal = match.group(1).lower() if match.lastindex else b''
                if literal and any(mark in literal for mark in (b'test', b'placeholder', b'synthetic', b'example', b'your_', b'configured-')):
                    continue
                findings.append({'file': name, 'line': data[:match.start()].count(b'\n') + 1, 'type': kind})
    sample = ROOT / 'data/leak-check.db'
    with sqlite3.connect('file:' + sample.as_posix() + '?mode=ro', uri=True) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert db.execute('SELECT COUNT(*) FROM person').fetchone()[0] == 2
        for column in ('phone', 'id', 'qq'):
            assert db.execute('SELECT COUNT(*) FROM person WHERE "' + column + '" IS NOT NULL').fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM person WHERE email NOT LIKE '%@example.invalid'").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM person WHERE name NOT IN ('测试用户一','测试用户二')").fetchone()[0] == 0
        assert db.execute('PRAGMA freelist_count').fetchone()[0] == 0
    return findings


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--audit-working', action='store_true')
    args = parser.parse_args()
    if args.audit_working:
        names = git('ls-files', '--cached', '--others', '--exclude-standard', '-z').decode('utf-8').split('\0')
        files = {n: (ROOT / n).read_bytes() for n in names if n and allowed(n) and (ROOT / n).is_file()}
    else:
        if git('status', '--porcelain').strip():
            raise SystemExit('Tracked/untracked working changes remain. Commit and inspect before packaging.')
        names = git('ls-tree', '-r', '--name-only', '-z', 'HEAD').decode('utf-8').split('\0')
        files = {n: git('show', 'HEAD:' + n) for n in names if n and allowed(n)}
        if files['data/leak-check.db'] != (ROOT / 'data/leak-check.db').read_bytes():
            raise SystemExit('Working sample differs from committed sample; inspect before packaging.')
    findings = audit(files)
    report = {'files': len(files), 'uncompressed_bytes': sum(map(len, files.values())),
              'findings': findings, 'synthetic_sample': '2 rows, example.invalid only; phone/id/QQ NULL; no free pages',
              'largest20': [{'file': n, 'bytes': len(d)} for n, d in sorted(files.items(), key=lambda i: len(i[1]), reverse=True)[:20]]}
    if findings or args.audit_working:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    if findings:
        raise SystemExit('Suspicious secrets found; packaging stopped. Values intentionally omitted.')
    if args.audit_working:
        return
    if not args.output:
        raise SystemExit('--output <new ZIP path> required')
    if args.output.exists():
        raise SystemExit('Output already exists; will not overwrite an earlier package.')
    commit = git('rev-parse', 'HEAD').decode().strip()
    files['RELEASE.json'] = (json.dumps({'commit': commit, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                      'runtime_data': False, 'node_required': False, 'source': 'Git committed blobs'}, indent=2) + '\n').encode()
    files['MANIFEST.sha256'] = ''.join(hashlib.sha256(d).hexdigest() + '  ' + n + '\n' for n, d in sorted(files.items())).encode('utf-8')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            assert allowed(name), name
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix('.zip.sha256').write_text(digest + '  ' + args.output.name + '\n', encoding='utf-8')
    report.update(commit=commit, zip=str(args.output.resolve()), zip_bytes=args.output.stat().st_size, sha256=digest,
                  packaged_files=len(files), excluded_names=[n for n in names if n and not allowed(n)])
    args.output.with_suffix('.audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('largest20','excluded_names')},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

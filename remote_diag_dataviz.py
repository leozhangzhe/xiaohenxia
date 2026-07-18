import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

cmd = r"""python3 - <<'PY'
import requests
from pathlib import Path

base = 'http://127.0.0.1:5001'
s = requests.Session()
s.get(base + '/login', timeout=10)
s.post(base + '/login', data={'username': 'admin', 'password': '<ADMIN_PASSWORD>', 'next': '/'}, allow_redirects=False, timeout=10)

for p in ['/dataviz', '/scanlist', '/riskalerts']:
    r = s.get(base + p, timeout=10)
    print(p, r.status_code, r.headers.get('content-type'))
    print((r.text or '')[:120].replace('\n', ' '))

tpl = Path('/home/ubuntu/apps/spiderfoot/spiderfoot/templates/dataviz.tmpl')
print('dataviz_exists', tpl.exists())
if tpl.exists():
    text = tpl.read_text(encoding='utf-8', errors='ignore')
    for key in ["scanlist", "riskalerts", "apiJson(", "loadDashboard("]:
        idx = text.find(key)
        print(key, "idx", idx)
    for line in text.splitlines():
        if "scanlist" in line or "riskalerts" in line:
            print("LINE:", line.strip())
PY"""

stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
code = stdout.channel.recv_exit_status()
print(f"exit={code}")
print(out)
print(err)
ssh.close()


import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

cmd = r"""python3 - <<'PY'
import requests
s = requests.Session()
base = 'http://127.0.0.1:5001'
r = s.get(base + '/login', timeout=10)
print('login_get', r.status_code, r.headers.get('content-type'))
r = s.post(base + '/login', data={'username':'admin','password':'<ADMIN_PASSWORD>','next':'/'}, allow_redirects=False, timeout=10)
print('login_post', r.status_code, r.headers.get('location'))
r = s.get(base + '/scanlistjson', timeout=10)
print('scanlistjson', r.status_code, r.headers.get('content-type'))
print('body_prefix', r.text[:80].replace('\n',' '))
try:
    data = r.json()
    print('scan_count', len(data))
    if data:
        print('first_scan', data[0][:8])
except Exception as e:
    print('json_err', e)
PY"""

stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
code = stdout.channel.recv_exit_status()
print(f"exit={code}")
print(out)
print(err)
ssh.close()

import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

cmd = """python3 - <<'PY'
import requests
s=requests.Session()
base='http://127.0.0.1:5001'
s.get(base+'/login',timeout=10)
s.post(base+'/login',data={'username':'admin','password':'<ADMIN_PASSWORD>','next':'/'},allow_redirects=False,timeout=10)
r=s.get(base+'/',timeout=10)
print('status', r.status_code)
print('ct', r.headers.get('content-type'))
print((r.text or '')[:800])
PY"""

stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
code = stdout.channel.recv_exit_status()
print(out)
print(err)
ssh.close()

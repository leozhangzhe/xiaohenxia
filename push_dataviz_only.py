import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

LOCAL = r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\dataviz.tmpl"
REMOTE = "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/dataviz.tmpl"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

sftp = ssh.open_sftp()
sftp.put(LOCAL, REMOTE)
sftp.close()

sudo = f"echo '{PASSWORD}' | sudo -S -p '' "
ssh.exec_command(sudo + "systemctl restart spiderfoot", get_pty=True)[1].read()

check_cmd = """python3 - <<'PY'
import requests
s = requests.Session()
base = 'http://127.0.0.1:5001'
s.get(base + '/login', timeout=10)
s.post(base + '/login', data={'username':'admin','password':'<ADMIN_PASSWORD>','next':'/'}, allow_redirects=False, timeout=10)
r = s.get(base + '/dataviz', timeout=10)
print('dataviz', r.status_code, r.headers.get('content-type'), len(r.text))
print('contains_apiJson', 'apiJson(' in r.text)
PY"""
stdin, stdout, stderr = ssh.exec_command(check_cmd, get_pty=True)
print(stdout.read().decode("utf-8", errors="replace"))
print(stderr.read().decode("utf-8", errors="replace"))
ssh.close()


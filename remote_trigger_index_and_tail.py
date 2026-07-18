import paramiko

HOST="<SERVER_HOST>"
USER="ubuntu"
PASSWORD="<SERVER_PASSWORD>"

ssh=paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

cmd_req = """python3 - <<'PY'
import requests
s=requests.Session()
base='http://127.0.0.1:5001'
s.get(base+'/login',timeout=10)
s.post(base+'/login',data={'username':'admin','password':'<ADMIN_PASSWORD>','next':'/'},allow_redirects=False,timeout=10)
r=s.get(base+'/',timeout=10)
print('index_status', r.status_code)
PY"""
ssh.exec_command(cmd_req, get_pty=True)[1].read()

cmd_tail = "tail -n 120 /home/ubuntu/.spiderfoot/logs/spiderfoot.error.log"
stdin, stdout, stderr = ssh.exec_command(cmd_tail, get_pty=True)
print(stdout.read().decode("utf-8", errors="replace"))
print(stderr.read().decode("utf-8", errors="replace"))
ssh.close()

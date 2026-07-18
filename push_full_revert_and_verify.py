import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

FILES = [
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\sfwebui.py", "/home/ubuntu/apps/spiderfoot/sfwebui.py"),
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\scanlist.tmpl", "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/scanlist.tmpl"),
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\static\js\spiderfoot.scanlist.js", "/home/ubuntu/apps/spiderfoot/spiderfoot/static/js/spiderfoot.scanlist.js"),
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\static\js\privacyguard.js", "/home/ubuntu/apps/spiderfoot/spiderfoot/static/js/privacyguard.js"),
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\HEADER.tmpl", "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/HEADER.tmpl"),
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\dataviz.tmpl", "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/dataviz.tmpl"),
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\servicemonitor.tmpl", "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/servicemonitor.tmpl"),
]


def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(f"\n$ {cmd}\n[exit={code}]")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())
    return code, out, err


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
sftp = ssh.open_sftp()
for local, remote in FILES:
    sftp.put(local, remote)
    print("uploaded", remote)
sftp.close()

sudo = f"echo '{PASSWORD}' | sudo -S -p '' "
run(ssh, sudo + "systemctl restart spiderfoot")

# Verify key endpoints: scanlist page, scanlist API, scaninfo HTML and scanstatus JSON.
cmd = """python3 - <<'PY'
import time,requests,re
s=requests.Session()
base='http://127.0.0.1:5001'
for _ in range(20):
  try:
    if requests.get(base+'/login',timeout=3).status_code==200: break
  except Exception: time.sleep(1)
s.get(base+'/login',timeout=10)
s.post(base+'/login',data={'username':'admin','password':'<ADMIN_PASSWORD>','next':'/'},allow_redirects=False,timeout=10)
r_api=s.get(base+'/scanlist',timeout=10)
print('scanlist_api', r_api.status_code, r_api.headers.get('content-type'), 'count', len(r_api.json()))
first = r_api.json()[0][0] if r_api.json() else None
r_page=s.get(base+'/',timeout=10)
print('index_page', r_page.status_code, r_page.headers.get('content-type'), 'has_table', ('scanlist-tbody' in r_page.text))
if first:
  r_info=s.get(base+'/scaninfo?id='+first,timeout=10)
  print('scaninfo_page', r_info.status_code, 'len', len(r_info.text))
  r_status=s.get(base+'/scanstatus?id='+first,timeout=10)
  print('scanstatus_api', r_status.status_code, r_status.headers.get('content-type'), 'len', len(r_status.json()) if r_status.headers.get('content-type','').startswith('application/json') else 'na')
PY"""
run(ssh, cmd)

ssh.close()

import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

FILES = [
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\sfwebui.py", "/home/ubuntu/apps/spiderfoot/sfwebui.py"),
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
    return code


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
run(ssh, "python3 - <<'PY'\nimport time,requests\nfor _ in range(12):\n  try:\n    r=requests.get('http://127.0.0.1:5001/login',timeout=3)\n    if r.status_code==200:\n      break\n  except Exception:\n    time.sleep(1)\nr1=requests.get('http://127.0.0.1:5001/scanlist',timeout=10)\nprint('normal', r1.status_code, r1.headers.get('content-type'))\nr2=requests.get('http://127.0.0.1:5001/scanlist?format=json',timeout=10)\nprint('json', r2.status_code, r2.headers.get('content-type'), 'count', len(r2.json()))\nPY")
ssh.close()

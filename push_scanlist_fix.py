import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

FILES = [
    (
        r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\scanlist.tmpl",
        "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/scanlist.tmpl",
    ),
    (
        r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\static\js\spiderfoot.scanlist.js",
        "/home/ubuntu/apps/spiderfoot/spiderfoot/static/js/spiderfoot.scanlist.js",
    ),
    (
        r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\static\js\privacyguard.scanlist.js",
        "/home/ubuntu/apps/spiderfoot/spiderfoot/static/js/privacyguard.scanlist.js",
    ),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
sftp = ssh.open_sftp()
for local, remote in FILES:
    sftp.put(local, remote)
    print("uploaded", remote)
sftp.close()

sudo = f"echo '{PASSWORD}' | sudo -S -p '' "
for cmd in [
    sudo + "systemctl restart spiderfoot",
    sudo + "systemctl is-active spiderfoot",
    "python3 - <<'PY'\nimport requests\ns=requests.Session()\nbase='http://127.0.0.1:5001'\ns.get(base+'/login',timeout=10)\ns.post(base+'/login',data={'username':'admin','password':'<ADMIN_PASSWORD>','next':'/'},allow_redirects=False,timeout=10)\nr=s.get(base+'/scanlist',timeout=10)\nprint('scanlist_status',r.status_code)\nprint('scan_count', len(r.json()))\nPY",
]:
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(f"\n$ {cmd}\n[exit={code}]")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())

ssh.close()

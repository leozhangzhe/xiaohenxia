import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

LOCAL = r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\sfwebui.py"
REMOTE = "/home/ubuntu/apps/spiderfoot/sfwebui.py"


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


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
sftp = ssh.open_sftp()
sftp.put(LOCAL, REMOTE)
sftp.close()

sudo = f"echo '{PASSWORD}' | sudo -S -p '' "
run(ssh, sudo + "systemctl restart spiderfoot")
run(ssh, "curl -I --max-time 8 http://127.0.0.1:5001/scanlist")
run(ssh, "python3 - <<'PY'\nimport requests\nr=requests.get('http://127.0.0.1:5001/scanlist',headers={'X-Requested-With':'XMLHttpRequest'},timeout=10)\nprint(r.status_code, r.headers.get('content-type'))\nprint((r.text or '')[:60])\nPY")
ssh.close()

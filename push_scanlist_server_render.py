import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

FILES = [
    (
        r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\sfwebui.py",
        "/home/ubuntu/apps/spiderfoot/sfwebui.py",
    ),
    (
        r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\scanlist.tmpl",
        "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/scanlist.tmpl",
    ),
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
run(ssh, sudo + "systemctl is-active spiderfoot")
run(ssh, "curl -s --max-time 8 http://127.0.0.1:5001/ | head -c 300")
run(ssh, "curl -s --max-time 8 http://127.0.0.1:5001/ | grep -n 'scanlist-tbody' | head -n 2")

ssh.close()

import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

for cmd in [
    "pwd",
    "ls -la /home/ubuntu/apps",
    "ls -la /home/ubuntu/apps/spiderfoot | head -n 40",
    "ls -la /home/ubuntu/apps/spiderfoot/.venv/bin/python",
    "ps -ef | grep sf.py | grep -v grep || true",
]:
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(f"\n$ {cmd}\n[exit={code}]")
    print(out)
    if err.strip():
        print(err)

ssh.close()

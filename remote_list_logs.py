import paramiko

HOST="<SERVER_HOST>"
USER="ubuntu"
PASSWORD="<SERVER_PASSWORD>"

ssh=paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

cmds=[
    "ls -la /home/ubuntu/.spiderfoot/logs | tail -n 30 || true",
    "ls -la /home/ubuntu/.spiderfoot/logs/*.log 2>/dev/null | tail -n 20 || true",
    "for f in /home/ubuntu/.spiderfoot/logs/*.log; do echo '---' $f; tail -n 200 $f; done 2>/dev/null || true",
]
for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(f"\n$ {cmd}\n{out}")
    if err.strip():
        print(err)
ssh.close()

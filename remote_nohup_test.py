import time
import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

commands = [
    "which nohup || true",
    "rm -f /home/ubuntu/spiderfoot.log",
    "nohup sh -c 'echo hello; sleep 1; echo done' > /home/ubuntu/spiderfoot.log 2>&1 &",
]
for cmd in commands:
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(f"\n$ {cmd}\n[exit={code}]")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())

time.sleep(2)
stdin, stdout, stderr = ssh.exec_command("ls -la /home/ubuntu/spiderfoot.log; cat /home/ubuntu/spiderfoot.log", get_pty=True)
print(stdout.read().decode("utf-8", errors="replace"))
print(stderr.read().decode("utf-8", errors="replace"))
ssh.close()

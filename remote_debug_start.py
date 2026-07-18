import time
import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"


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

run(ssh, "cd /home/ubuntu/apps/spiderfoot && .venv/bin/python --version")
run(ssh, "cd /home/ubuntu/apps/spiderfoot && ls -la sf.py sfwebui.py")
run(
    ssh,
    "cd /home/ubuntu/apps/spiderfoot && nohup sh -c 'echo hello-log; sleep 1; echo done-log' > /home/ubuntu/spiderfoot.log 2>&1 & echo launched",
)
time.sleep(2)
run(ssh, "cat /home/ubuntu/spiderfoot.log || true")
run(ssh, "cd /home/ubuntu/apps/spiderfoot && .venv/bin/python sf.py -l 0.0.0.0:5001 > /home/ubuntu/spiderfoot.log 2>&1 & echo started")
time.sleep(3)
run(ssh, "cat /home/ubuntu/spiderfoot.log || true")
run(ssh, "ps -ef | grep sf.py | grep -v grep || true")
run(ssh, "ss -lntp | grep 5001 || true")

ssh.close()

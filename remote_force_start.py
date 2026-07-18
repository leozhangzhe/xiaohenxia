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

run(ssh, "pkill -f 'sf.py -l 0.0.0.0:5001' || true")
run(
    ssh,
    "cd /home/ubuntu/apps/spiderfoot && setsid .venv/bin/python sf.py -l 0.0.0.0:5001 >/home/ubuntu/spiderfoot.log 2>&1 < /dev/null & echo started",
)
time.sleep(5)
run(ssh, "ps -ef | grep 'sf.py -l 0.0.0.0:5001' | grep -v grep || true")
run(ssh, "tail -n 80 /home/ubuntu/spiderfoot.log || true")
run(ssh, "curl -I --max-time 8 http://127.0.0.1:5001/login || true")

ssh.close()

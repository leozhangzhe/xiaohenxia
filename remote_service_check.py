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


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
time.sleep(6)

run(ssh, "echo '<SERVER_PASSWORD>' | sudo -S -p '' systemctl is-active spiderfoot")
run(ssh, "echo '<SERVER_PASSWORD>' | sudo -S -p '' systemctl --no-pager --full status spiderfoot | head -n 60")
run(ssh, "echo '<SERVER_PASSWORD>' | sudo -S -p '' journalctl -u spiderfoot -n 80 --no-pager")
run(ssh, "curl -I --max-time 8 http://127.0.0.1:5001/login")
run(ssh, "ss -lntp | grep 5001")

ssh.close()

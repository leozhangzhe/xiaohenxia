import time

import paramiko


HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"
REMOTE_BASE = "/home/ubuntu/apps/spiderfoot"


def run(ssh: paramiko.SSHClient, cmd: str, check: bool = True):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(f"\n$ {cmd}\n[exit={code}]", flush=True)
    if out.strip():
        print(out.strip(), flush=True)
    if err.strip():
        print(err.strip(), flush=True)
    if check and code != 0:
        raise RuntimeError(f"command failed: {cmd}")


def main():
    sudo = f"echo '{PASSWORD}' | sudo -S -p '' "
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

    run(ssh, "while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do echo 'waiting apt lock'; sleep 3; done", check=False)
    run(
        ssh,
        sudo + "apt-get install -y python3 python3-pip python3-venv build-essential libffi-dev libssl-dev libxml2-dev libxslt1-dev",
    )
    run(ssh, f"cd {REMOTE_BASE} && python3 -m venv .venv")
    run(ssh, f"cd {REMOTE_BASE} && .venv/bin/pip install --upgrade pip setuptools wheel")
    run(ssh, f"cd {REMOTE_BASE} && .venv/bin/pip install -r requirements.txt")
    run(ssh, "pkill -f 'sf.py -l 0.0.0.0:5001' || true", check=False)
    run(ssh, f"cd {REMOTE_BASE} && nohup .venv/bin/python sf.py -l 0.0.0.0:5001 > /home/ubuntu/spiderfoot.log 2>&1 &")
    time.sleep(3)
    run(ssh, "ss -lntp | grep 5001")
    run(ssh, sudo + "ufw allow 5001/tcp || true", check=False)
    run(ssh, "curl -I --max-time 8 http://127.0.0.1:5001/login")

    print("DEPLOY_OK http://<SERVER_HOST>:5001/login", flush=True)
    ssh.close()


if __name__ == "__main__":
    main()

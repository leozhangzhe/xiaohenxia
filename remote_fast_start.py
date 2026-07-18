import time
import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"
BASE = "/home/ubuntu/apps/spiderfoot"


def run(ssh, cmd, check=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(f"\n$ {cmd}\n[exit={code}]")
    if out.strip():
        print(out.strip().encode("gbk", errors="ignore").decode("gbk", errors="ignore"))
    if err.strip():
        print(err.strip().encode("gbk", errors="ignore").decode("gbk", errors="ignore"))
    if check and code != 0:
        raise RuntimeError(cmd)


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

    run(ssh, f"cd {BASE} && python3 -m venv .venv")
    run(ssh, f"cd {BASE} && .venv/bin/pip install --upgrade pip setuptools wheel")
    run(ssh, f"cd {BASE} && .venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
    run(ssh, "pkill -f 'sf.py -l 0.0.0.0:5001' || true", check=False)
    run(ssh, f"cd {BASE} && nohup .venv/bin/python sf.py -l 0.0.0.0:5001 > /home/ubuntu/spiderfoot.log 2>&1 &")
    time.sleep(4)
    run(ssh, "curl -I --max-time 8 http://127.0.0.1:5001/login")
    run(ssh, "ss -lntp | grep 5001")
    print("READY http://<SERVER_HOST>:5001/login")
    ssh.close()


if __name__ == "__main__":
    main()

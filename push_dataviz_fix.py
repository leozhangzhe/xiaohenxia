import paramiko


HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"
LOCAL_FILE = r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\dataviz.tmpl"
REMOTE_FILE = "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/dataviz.tmpl"


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


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

    sftp = ssh.open_sftp()
    sftp.put(LOCAL_FILE, REMOTE_FILE)
    sftp.close()

    run(ssh, "pkill -f 'sf.py -l 0.0.0.0:5001' || true")
    run(
        ssh,
        "cd /home/ubuntu/apps/spiderfoot && nohup .venv/bin/python sf.py -l 0.0.0.0:5001 > /home/ubuntu/spiderfoot.log 2>&1 &",
    )
    run(ssh, "sleep 2; curl -I --max-time 8 http://127.0.0.1:5001/dataviz")
    run(ssh, "curl -I --max-time 8 http://127.0.0.1:5001/login")
    print("PUSH_OK")
    ssh.close()


if __name__ == "__main__":
    main()

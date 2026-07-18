import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

SERVICE_CONTENT = """[Unit]
Description=SpiderFoot Web UI
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/apps/spiderfoot
ExecStart=/home/ubuntu/apps/spiderfoot/.venv/bin/python sf.py -l 0.0.0.0:5001
Restart=always
RestartSec=3
Environment=SF_AUTH_ADMIN_USER=admin
Environment=SF_AUTH_ADMIN_PASS=<ADMIN_PASSWORD>

[Install]
WantedBy=multi-user.target
"""


def run(ssh, cmd, check=True):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(f"\n$ {cmd}\n[exit={code}]")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())
    if check and code != 0:
        raise RuntimeError(cmd)


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
sftp = ssh.open_sftp()
tmp_service = "/home/ubuntu/spiderfoot.service"
with sftp.file(tmp_service, "w") as f:
    f.write(SERVICE_CONTENT)
sftp.close()

sudo = f"echo '{PASSWORD}' | sudo -S -p '' "
run(ssh, sudo + f"mv {tmp_service} /etc/systemd/system/spiderfoot.service")
run(ssh, sudo + "systemctl daemon-reload")
run(ssh, sudo + "systemctl enable spiderfoot")
run(ssh, sudo + "systemctl restart spiderfoot")
run(ssh, sudo + "systemctl --no-pager --full status spiderfoot | head -n 40", check=False)
run(ssh, "curl -I --max-time 8 http://127.0.0.1:5001/login")
run(ssh, "ss -lntp | grep 5001")
print("DEPLOY_OK http://<SERVER_HOST>:5001/login")
ssh.close()

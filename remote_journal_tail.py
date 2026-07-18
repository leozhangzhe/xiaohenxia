import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

cmd = "echo '<SERVER_PASSWORD>' | sudo -S -p '' journalctl -u spiderfoot -n 160 --no-pager"
stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
print(out)
print(err)
ssh.close()

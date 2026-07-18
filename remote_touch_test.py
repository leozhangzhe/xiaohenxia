import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
for cmd in [
    "id",
    "pwd",
    "touch /home/ubuntu/spiderfoot.log",
    "ls -la /home/ubuntu/spiderfoot.log",
    "echo testline > /home/ubuntu/spiderfoot.log",
    "cat /home/ubuntu/spiderfoot.log",
]:
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(f"\n$ {cmd}\n[exit={code}]")
    print(out)
    if err.strip():
        print(err)
ssh.close()

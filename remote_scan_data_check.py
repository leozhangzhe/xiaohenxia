import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

commands = [
    "echo '<SERVER_PASSWORD>' | sudo -S -p '' systemctl is-active spiderfoot",
    "ls -la /home/ubuntu/.spiderfoot || true",
    "ls -la /home/ubuntu/apps/spiderfoot/data || true",
    "ls -la /home/ubuntu/spiderfoot-master/data || true",
    "python3 - <<'PY'\nimport os\nroot='/home/ubuntu'\ncount=0\nfor base, dirs, files in os.walk(root):\n    rel=base[len(root):].count('/')\n    if rel>4:\n        dirs[:] = []\n        continue\n    for f in files:\n        if f.endswith('.db') or f=='spiderfoot.db':\n            print(os.path.join(base,f))\n            count += 1\n            if count >= 40:\n                raise SystemExit\nPY",
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

ssh.close()

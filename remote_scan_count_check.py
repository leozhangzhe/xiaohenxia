import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

cmd = (
    "python3 - <<'PY'\n"
    "import sqlite3\n"
    "db='/home/ubuntu/.spiderfoot/spiderfoot.db'\n"
    "conn=sqlite3.connect(db)\n"
    "cur=conn.cursor()\n"
    "tables=['tbl_scan_instance','tbl_scan_results','tbl_scan_config']\n"
    "for t in tables:\n"
    "  try:\n"
    "    cur.execute(f'SELECT COUNT(1) FROM {t}')\n"
    "    print(t, cur.fetchone()[0])\n"
    "  except Exception as e:\n"
    "    print(t, 'ERR', e)\n"
    "cur.execute('SELECT guid,name,target,status FROM tbl_scan_instance ORDER BY created DESC LIMIT 10')\n"
    "for r in cur.fetchall():\n"
    "  print('scan', r)\n"
    "conn.close()\n"
    "PY"
)

stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
code = stdout.channel.recv_exit_status()
print(f"exit={code}")
print(out)
print(err)
ssh.close()

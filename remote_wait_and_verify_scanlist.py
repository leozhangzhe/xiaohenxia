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

for _ in range(12):
    code = run(ssh, "curl -I --max-time 3 http://127.0.0.1:5001/login >/dev/null 2>&1; echo $?")
    if code == 0:
        break
    time.sleep(2)

run(ssh, "python3 - <<'PY'\nimport requests\nbase='http://127.0.0.1:5001/scanlist'\nr1=requests.get(base,timeout=10)\nprint('normal', r1.status_code, r1.headers.get('content-type'))\nprint((r1.text or '')[:80].replace('\\n',' '))\nr2=requests.get(base,headers={'X-Requested-With':'XMLHttpRequest'},timeout=10)\nprint('xhr', r2.status_code, r2.headers.get('content-type'))\nprint((r2.text or '')[:80].replace('\\n',' '))\nPY")
ssh.close()

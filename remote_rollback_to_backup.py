import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

DEPLOY = "/home/ubuntu/apps/spiderfoot"
BACKUP = "/home/ubuntu/spiderfoot-master.bak.20260428"

# Files that were touched during “数据洞察看板/扫描列表”改动链路
ROLLBACK_PATHS = [
    "sfwebui.py",
    "sf.py",
    "spiderfoot/templates/HEADER.tmpl",
    "spiderfoot/templates/scanlist.tmpl",
    "spiderfoot/templates/servicemonitor.tmpl",
    "spiderfoot/templates/dataviz.tmpl",
    "spiderfoot/static/js/privacyguard.js",
    "spiderfoot/static/js/spiderfoot.scanlist.js",
    "spiderfoot/static/js/spiderfoot.scaninfo.js",
]


def run(ssh: paramiko.SSHClient, cmd: str):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    print(f"\n$ {cmd}\n[exit={code}]")
    if out.strip():
        print(out.strip())
    if err.strip():
        print(err.strip())
    if code != 0:
        raise RuntimeError(cmd)


def main() -> None:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)

    run(ssh, f"test -d {BACKUP} && echo backup_ok")
    run(ssh, f"test -d {DEPLOY} && echo deploy_ok")

    # Copy back files from backup
    for rel in ROLLBACK_PATHS:
        src = f"{BACKUP}/{rel}"
        dst = f"{DEPLOY}/{rel}"
        # Ensure destination directory exists
        dst_dir = "/".join(dst.split("/")[:-1])
        run(ssh, f"mkdir -p {dst_dir}")
        # Some files may not exist in older backup versions; skip safely.
        run(ssh, f"if test -f {src}; then cp -f {src} {dst} && echo rolled:{rel}; else echo skip_missing:{rel}; fi")

    # Restart service
    sudo = f"echo '{PASSWORD}' | sudo -S -p '' "
    run(ssh, sudo + "systemctl restart spiderfoot")
    run(ssh, sudo + "systemctl is-active spiderfoot")

    # Verify: index HTML + scanlist JSON + scaninfo HTML
    verify = r"""python3 - <<'PY'
import time,requests
s=requests.Session()
base='http://127.0.0.1:5001'
for _ in range(25):
  try:
    if requests.get(base+'/login',timeout=3).status_code==200:
      break
  except Exception:
    time.sleep(1)
s.get(base+'/login',timeout=10)
s.post(base+'/login',data={'username':'admin','password':'<ADMIN_PASSWORD>','next':'/'},allow_redirects=False,timeout=10)
r_api=s.get(base+'/scanlist',timeout=10)
print('scanlist_api', r_api.status_code, r_api.headers.get('content-type'))
data=r_api.json()
print('scan_count', len(data))
first=data[0][0] if data else None
r_idx=s.get(base+'/',timeout=10)
print('index', r_idx.status_code, r_idx.headers.get('content-type'), 'len', len(r_idx.text))
if first:
  r_info=s.get(base+'/scaninfo?id='+first,timeout=10)
  print('scaninfo', r_info.status_code, 'len', len(r_info.text))
PY"""
    run(ssh, verify)

    ssh.close()
    print("\nROLLBACK_DONE")


if __name__ == "__main__":
    main()


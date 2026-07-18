import paramiko

HOST="<SERVER_HOST>"
USER="ubuntu"
PASSWORD="<SERVER_PASSWORD>"

FILES = [
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\static\js\spiderfoot.scanlist.js",
     "/home/ubuntu/apps/spiderfoot/spiderfoot/static/js/spiderfoot.scanlist.js"),
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\static\js\spiderfoot.scaninfo.js",
     "/home/ubuntu/apps/spiderfoot/spiderfoot/static/js/spiderfoot.scaninfo.js"),
]

ssh=paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
sftp=ssh.open_sftp()
for local, remote in FILES:
    sftp.put(local, remote)
    print("uploaded", remote)
sftp.close()

sudo=f"echo '{PASSWORD}' | sudo -S -p '' "
ssh.exec_command(sudo+"systemctl restart spiderfoot", get_pty=True)[1].read()
print("RESTARTED")
ssh.close()


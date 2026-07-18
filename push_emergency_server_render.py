import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

FILES = [
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\sfwebui.py", "/home/ubuntu/apps/spiderfoot/sfwebui.py"),
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\scanlist.tmpl", "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/scanlist.tmpl"),
    (r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\scaninfo.tmpl", "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/scaninfo.tmpl"),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
sftp = ssh.open_sftp()
for local, remote in FILES:
    sftp.put(local, remote)
    print("uploaded", remote)
sftp.close()

sudo = f"echo '{PASSWORD}' | sudo -S -p '' "
ssh.exec_command(sudo + "systemctl restart spiderfoot", get_pty=True)[1].read()
print("RESTARTED")
ssh.close()

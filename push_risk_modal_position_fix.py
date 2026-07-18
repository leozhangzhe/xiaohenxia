import paramiko

HOST = "<SERVER_HOST>"
USER = "ubuntu"
PASSWORD = "<SERVER_PASSWORD>"

LOCAL = r"C:\Users\张哲\Desktop\spiderfoot比赛项目\spiderfoot-master\spiderfoot\templates\riskalerts.tmpl"
REMOTE = "/home/ubuntu/apps/spiderfoot/spiderfoot/templates/riskalerts.tmpl"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=20)
sftp = ssh.open_sftp()
sftp.put(LOCAL, REMOTE)
sftp.close()

sudo = f"echo '{PASSWORD}' | sudo -S -p '' "
ssh.exec_command(sudo + "systemctl restart spiderfoot", get_pty=True)[1].read()
print("DEPLOYED riskalerts.tmpl and restarted service")
ssh.close()

#!/bin/bash
# ============================================================
#  消痕侠 - 一键部署脚本 (Ubuntu 22.04)
# ============================================================

set -e

echo ""
echo "============================================"
echo "  消痕侠 - 服务器一键部署"
echo "============================================"
echo ""

# ---------- 1. 更新系统 & 安装基础工具 ----------
echo "[1/7] 更新系统包..."
sudo apt-get update -y
sudo apt-get upgrade -y

echo "[2/7] 安装基础工具..."
sudo apt-get install -y python3-pip python3-venv nodejs npm mysql-server curl unzip git

# ---------- 2. 安装 pip 依赖 ----------
echo "[3/7] 安装 Python 依赖..."
cd /opt/spiderfoot
sudo pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt

# ---------- 3. 安装前端依赖 ----------
echo "[4/7] 安装前端依赖..."
cd /opt/spiderfoot/spiderfoot/static
npm install --legacy-peer-deps

# ---------- 4. 配置 MySQL ----------
echo "[5/7] 配置 MySQL..."
sudo systemctl start mysql
sudo systemctl enable mysql

# 创建数据库和用户
sudo mysql -e "
CREATE DATABASE IF NOT EXISTS spiderfoot_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'root'@'localhost' IDENTIFIED BY '<MYSQL_PASSWORD>';
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '<MYSQL_PASSWORD>';
GRANT ALL PRIVILEGES ON spiderfoot_auth.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
" 2>/dev/null || sudo mysql -e "
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '<MYSQL_PASSWORD>';
FLUSH PRIVILEGES;
"

# ---------- 5. 创建 systemd 服务 ----------
echo "[6/7] 创建系统服务..."
sudo tee /etc/systemd/system/xiaohenxia.service > /dev/null <<'EOF'
[Unit]
Description=Xiaohenxia (SpiderFoot) Platform
After=network.target mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/spiderfoot
Environment=SF_AUTH_MYSQL_HOST=127.0.0.1
Environment=SF_AUTH_MYSQL_PORT=3306
Environment=SF_AUTH_MYSQL_USER=root
Environment=SF_AUTH_MYSQL_PASSWORD=<MYSQL_PASSWORD>
Environment=SF_AUTH_MYSQL_DATABASE=spiderfoot_auth
ExecStart=/usr/bin/python3 /opt/spiderfoot/sf.py -l 0.0.0.0:5001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable xiaohenxia
sudo systemctl start xiaohenxia

# ---------- 6. 开放防火墙 ----------
echo "[7/7] 配置防火墙..."
sudo ufw allow 22/tcp 2>/dev/null || true
sudo ufw allow 5001/tcp 2>/dev/null || true
sudo ufw --force enable 2>/dev/null || true

# ---------- 完成 ----------
echo ""
echo "============================================"
echo "  部署完成!"
echo "============================================"
echo ""
echo "  访问地址: http://<SERVER_HOST>:5001"
echo "  登录账号: admin / <ADMIN_PASSWORD>"
echo ""
echo "  注意: 请确保腾讯云控制台防火墙已放行 5001 端口"
echo ""
echo "  管理命令:"
echo "    启动: sudo systemctl start xiaohenxia"
echo "    停止: sudo systemctl stop xiaohenxia"
echo "    重启: sudo systemctl restart xiaohenxia"
echo "    状态: sudo systemctl status xiaohenxia"
echo ""

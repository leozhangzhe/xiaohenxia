@echo off
chcp 65001 > nul
echo.
echo ============================================
echo   消痕侠 - 数字痕迹管理平台
echo   一键启动脚本
echo ============================================
echo.

:: 检查 Python
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.7+
    pause
    exit /b 1
)

:: 检查 Node.js
node --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 未找到 Node.js，正在尝试从官网下载安装...
    echo 请手动安装 Node.js: https://nodejs.org/
    echo 安装后重新运行此脚本
    pause
    exit /b 1
)

:: 安装前端依赖（仅首次需要）
if not exist "spiderfoot\static\node_modules" (
    echo [步骤 1/3] 安装前端依赖...
    cd spiderfoot\static
    npm install --legacy-peer-deps
    cd ..\..
    echo [完成] 前端依赖安装成功
) else (
    echo [跳过] 前端依赖已存在
)

:: 安装 Python 依赖
echo [步骤 2/3] 检查 Python 依赖...
pip install -r requirements.txt --quiet
echo [完成] Python 依赖已就绪

:: 设置 MySQL 连接环境变量
set SF_AUTH_MYSQL_HOST=127.0.0.1
set SF_AUTH_MYSQL_PORT=3306
set SF_AUTH_MYSQL_USER=root
set SF_AUTH_MYSQL_PASSWORD=<MYSQL_PASSWORD>
set SF_AUTH_MYSQL_DATABASE=spiderfoot_auth

:: 启动服务
echo.
echo [步骤 3/3] 启动消痕侠平台...
echo.
echo   访问地址: http://localhost:5001
echo   登录账号: admin / <ADMIN_PASSWORD>
echo   按 Ctrl+C 停止服务
echo.
python sf.py -l 127.0.0.1:5001

pause

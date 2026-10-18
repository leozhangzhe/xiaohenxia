@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title 消痕侠 - 本地工作区
if not exist ".venv\Scripts\python.exe" (
  echo 找不到项目虚拟环境 .venv，请先完成环境安装。
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -B "scripts\start-desktop.py" %*
set "app_exit=%errorlevel%"
if not "%app_exit%"=="0" pause
exit /b %app_exit%

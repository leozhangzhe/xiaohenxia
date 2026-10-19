@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
py -3.12 scripts\install-release.py %*
set "install_exit=%errorlevel%"
if not "%install_exit%"=="0" pause
exit /b %install_exit%

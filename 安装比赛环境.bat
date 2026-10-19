@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
where py.exe >nul 2>nul
if %errorlevel% equ 0 (
  py -3.12 scripts\install-release.py %*
) else (
  python scripts\install-release.py %*
)
set "install_exit=%errorlevel%"
if not "%install_exit%"=="0" pause
exit /b %install_exit%

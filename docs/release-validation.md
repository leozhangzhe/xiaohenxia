# 比赛包冷启动验收

交付准备中。本文件最终将记录从 Git 导出 ZIP、全新目录安装、真实 MySQL/CherryPy HTTP 流程及重启验证的实际结果。只有完成执行后才声明通过。

复现命令（请在全新解压包中运行）：

```powershell
py -3.12 scripts/install-release.py --mysql-archive '<官方MySQL ZIP路径>'
.\.venv\Scripts\python.exe -B scripts/verify-release.py --report '..\cold-start-results.json'
```

verify-release 使用与双击启动相同的 DesktopServer 初始化、数据库和 Web 生命周期；为避免影响用户正在运行的 5001 实例，自动选择空闲 Web 端口，随机生成合成验收密码，只在新的 .runtime-profile/release-verification 建立合成账号。不会复制开发虚拟环境或连接原数据库。它是可重复的真实 HTTP 验证，不声称重新完成视觉浏览器验收。

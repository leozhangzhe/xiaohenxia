# 最终启动说明

## 当前电脑

项目：`D:\消痕侠\消痕侠程序`。当前已打开的 `http://127.0.0.1:5001/` 是既有运行实例，不会为了测试停止它或合并其账号。新启动器的 `.runtime-profile/desktop` 是另一独立工作区。

日常双击 **双击启动.bat**，或：

```powershell
Set-Location 'D:\消痕侠\消痕侠程序'
.\.venv\Scripts\python.exe -B scripts/start-desktop.py
```

5001 已占用时会停止并提示，不会结束别人的 Python/MySQL。若使用现有实例，沿用其窗口及已配置账号；若切换桌面工作区，先在该实例自己的启动窗口正常停止，不能按进程名称批量结束。

首次桌面启动设置管理员 admin 的密码：至少12位，含字母及数字或符号，隐藏输入，没有默认密码。完成初始化后打开登录页。保持窗口打开；退出按 Ctrl+C，等待“已安全停止”，再用相同入口启动。账号及记录持久化，会话需重新登录。

## 全新电脑

Windows x64、Python 3.12（本机3.12.10）、MySQL官方8.0.46 x64 ZIP，必要时微软VC++ x64运行库。Node不参与运行；正式React资源及后台发布资源已保存。

在干净源码解压目录执行：

```powershell
python --version
python scripts/install-release.py --mysql-archive 'D:\Downloads\mysql-8.0.46-winx64.zip'
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -B scripts/setup_live_sources.py --check
.\双击启动.bat
```

路径按实际替换。安装批处理支持有py启动器时 `py -3.12`、没有时 `python`。根README记录MySQL官方地址和SHA-256。只在项目中建立环境，不全局pip安装、不自动下载未知EXE。最新Windows依赖是pyreadline3==3.5.6；不要拿旧pyreadline2.1替代。

若已经具备环境，不重复安装。没有外网时可用提前准备的发行包缓存：安装器增加 `--wheelhouse '<缓存目录>'`。WhatsMyName规则首次下载仍需网络；应赛前准备并校验。仅安装主程序可加 `--skip-live-sources`，但缺工具必须显示未安装，不能声称来源正常。

## 数据与密码

桌面工作区 `.runtime-profile/desktop/` 保存独立MySQL、扫描/任务数据、日志和缓存。随机数据库密码以Windows当前用户DPAPI加密保存；不使用写死root密码。不要只复制凭据到另一台机器，不删除/重建已有数据库。备份需停服后完整保存工作区。

`.env.example` 仅说明变量，应用不自动读取.env。外部MySQL的手动初始化见根README和docs/auth-stage1.md；只在当前进程通过隐藏输入提供密码。HIBP Key可选，无Key就是未配置。

## 排障

| 现象 | 操作 |
| --- | --- |
| 端口占用 | 确认是否已有项目窗口；使用已有实例或在其窗口Ctrl+C，不批量杀进程 |
| 账号不对 | 核实是否切到了独立工作区；不要套用admin123，不自动重置账号 |
| 数据库/认证503 | 检查启动窗口、工作区web.log和mysql/server.log；保留数据，不回退内存账号 |
| MySQL缺文件/版本错 | 使用校验通过的8.0.46 ZIP；不覆盖部分安装或猜测数据目录 |
| 静态资源404 | 用安装脚本恢复第三方发布资源；保留react-auth/auth.js和auth.css，无需npm |
| 外部来源失败 | 查看每个来源状态，按备用方案演示，不把失败解释为无痕 |
| 字体/背景慢 | 使用减少动态效果或静态降级，保持业务可用 |

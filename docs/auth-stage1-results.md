# 第一阶段验收记录（2026-10-17）

状态：实现和本阶段验证完成，等待用户验收；未进入下一阶段。

## 1. 文件范围

已修改的原有文件共 9 个：

1. `D:\消痕侠\消痕侠程序\spiderfoot\auth_mysql.py`
2. `D:\消痕侠\消痕侠程序\sfwebui.py`
3. `D:\消痕侠\消痕侠程序\sf.py`
4. `D:\消痕侠\消痕侠程序\启动平台.bat`
5. `D:\消痕侠\消痕侠程序\启动本地版.bat`
6. `D:\消痕侠\消痕侠程序\启动本地版.ps1`
7. `D:\消痕侠\消痕侠程序\spiderfoot\templates\login.tmpl`
8. `D:\消痕侠\消痕侠程序\spiderfoot\templates\register.tmpl`
9. `D:\消痕侠\消痕侠程序\.gitignore`

新增文件：

- `D:\消痕侠\消痕侠程序\scripts\auth_admin.py`
- `D:\消痕侠\消痕侠程序\scripts\start-local.ps1`
- `D:\消痕侠\消痕侠程序\docs\auth-stage1.md`
- 本验收记录。
- `D:\消痕侠\消痕侠程序\test\stage1\conftest.py`
- `D:\消痕侠\消痕侠程序\test\stage1\http_runner.py`
- `D:\消痕侠\消痕侠程序\test\stage1\live_mysql.py`
- `D:\消痕侠\消痕侠程序\test\stage1\test_auth_startup.py`
- `D:\消痕侠\消痕侠程序\test\stage1\test_auth_store.py`
- `D:\消痕侠\消痕侠程序\test\stage1\test_auth_http.py`
- `D:\消痕侠\消痕侠程序\test\stage1\test_auth_commands.py`
- `D:\消痕侠\消痕侠程序\test\stage1\test_real_mysql.py`

登录、注册模板只增加隐藏 CSRF 字段及跳转参数转义，没有改变布局。扫描器、扫描模块、规则、SQLite 扫描存储、外部数据源、泄露检测和隐私申请源码均未改动。

## 2. 新增测试及 TDD 记录

本阶段先确认了三项测试边界：认证存储公开接口、真实 HTTP 行为、启动配置行为。按小步失败测试 → 实现 → 通过测试执行。

| 测试文件 | 最终用例数 | 主要行为 |
|---|---:|---|
| `test_auth_startup.py` | 1 | 数据库故障必须阻止 UI 初始化 |
| `test_auth_store.py` | 23 | 首次密码必填、弱密码拒绝、默认密码显式重置、数据库错误、哈希和盐、账号持久、空格规范化、配置校验、只读检查、明文哈希拒绝、旧哈希兼容和禁止意外改密 |
| `test_auth_http.py` | 16 | 运行时 503、真实注册登录、Session 轮换和撤销、Cookie 属性、会话过期、跳转安全、HTML 转义及认证表单 CSRF |
| `test_auth_commands.py` | 6 | 缺失配置退出、密码不出现在错误中、禁用旧明文认证、三个启动入口在其他目录执行时保留失败码 |
| `test_real_mysql.py` | 2 | 真实 MySQL 冷重启、持久账号、哈希落库、部署检查、完整应用启动和数据库不可用时拒绝启动 |

失败测试日志保存在 `.stage1` 下，以 `red-` 开头；最终代码测试没有失败项。早期非 ASCII CSRF 筛选命令曾选中 0 项，随后改用明确的参数 ID 运行，确认 500 的失败后修复为 403，最终包含在完整测试中。

快速数据库测试替换第三方连接边界，不代替真实 MySQL 验证；HTTP 测试使用真实 CherryPy、真实认证存储及真实启动入口。真实 MySQL 使用新建目录、随机端口和运行时随机密码，未访问原业务数据库。

## 3. 命令与完整结果

工作目录：`D:\消痕侠\消痕侠程序`；测试命令使用项目 `.venv`。设置 `PYTHONDONTWRITEBYTECODE=1`，避免修改原有源码字节码。

最终认证测试实际命令：

```text
.venv\Scripts\python.exe -B -m pytest test\stage1 --confcutdir=test\stage1 --basetemp .stage1\acceptance-328c1a96e1e24e31a80f40747b62a0ad -v --tb=short -p no:cacheprovider -W ignore::DeprecationWarning
```

结果：**48 passed in 67.36s (0:01:07)，退出码 0**。

[48 项测试的完整输出](/D:/消痕侠/消痕侠程序/.stage1/stage1-tests-full.txt)

以上 basetemp 是此次留存的测试证据目录。**重新执行时必须换一个新的 GUID 目录**，防止 pytest 对已有 basetemp 执行清理。可复用的安全命令在配置说明中。

扫描存储回归命令：

```text
.venv\Scripts\python.exe -B -m pytest test\unit\spiderfoot\test_spiderfootdb.py --basetemp <本次新建项目内目录> -q --tb=short -p no:cacheprovider -W ignore::DeprecationWarning
```

运行前将 `SPIDERFOOT_DATA`、`SPIDERFOOT_LOGS`、`SPIDERFOOT_CACHE` 设置到本次新建 `.stage1\scan-db-<GUID>` 子目录。

结果：**82 passed, 4 skipped, 82 warnings in 0.28s，退出码 0**。4 项为原有 `todo` 跳过；82 条为旧测试框架在 Python 3.12 下产生的 `TestResult has no addDuration method` 兼容性警告。

[扫描存储回归完整输出](/D:/消痕侠/消痕侠程序/.stage1/scan-db-tests-full.txt)

其他检查：

```text
.venv\Scripts\python.exe -B -m flake8 spiderfoot\auth_mysql.py sf.py sfwebui.py scripts test\stage1 --select E9,F63,F7,F82 --show-source --statistics
.venv\Scripts\python.exe -B -m pip check
```

- 定向语法及未定义名称检查：退出码 0，无输出；这不是全项目风格检查。
- pip check：`No broken requirements found.`
- PowerShell Parser：`scripts\start-local.ps1`、`启动本地版.ps1` 均为 0 个解析错误。
- 完整 `sf.py` 启动及三个启动包装入口的成功／失败行为已经包含在上述测试中。
- 没有执行全量联网模块集成测试，没有触发真实外部数据检索。

## 4. 数据库配置与首次管理员

[配置、初始化、显式改密及启动说明](/D:/消痕侠/消痕侠程序/docs/auth-stage1.md)

数据库凭据由 `SF_AUTH_MYSQL_HOST/PORT/USER/PASSWORD/DATABASE` 进程环境变量传入，其中 USER/PASSWORD 必填。首次管理员由 `SF_AUTH_ADMIN_USER/PASS` 配置，不存在默认管理员密码。初始化后移除 ADMIN_PASS；现有账号改密只在停服后显式设置 ADMIN_RESET=1 执行，结束后移除该标记。

`auth_admin.py --initialize` 只初始化应用认证结构，不重建 MySQL 数据目录；`--check` 只读检查。数据库密码不写入启动脚本、不回显、不作为命令行参数。

新哈希为 PBKDF2-HMAC-SHA256、随机盐、600000 次迭代；现有合法 200000 次哈希继续可用。没有新增明文密码存储。

## 5. 启动方式

先启动并配置好已有 MySQL 服务，在当前 PowerShell 会话提供数据库环境变量并完成一次认证初始化，然后执行：

```powershell
Set-Location 'D:\消痕侠\消痕侠程序'
& '.\.venv\Scripts\python.exe' -B '.\scripts\auth_admin.py' --check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\scripts\start-local.ps1' -CheckOnly
& '.\启动平台.bat'
```

本机访问 `http://127.0.0.1:5001/login`。现有三个启动入口转到同一实现；默认扫描数据目录保持 `.runtime-profile\.spiderfoot`，不会换到一个空的业务目录。启动器不会自动操作现存 MySQL 实例。

## 6. 保留内容、回滚与未解决问题

- 修改前原文件及校验值保存到 `.stage1\baseline-20261017-002157`；对照差异保存为 `.stage1\stage1-code.diff`。
- 原 `.mysql*`、`.venv`、数据库、实验文件、部署文件均保留。测试自建的 MySQL 及 Web 进程已经退出，临时盘符已撤销。
- 当前目录仍没有 Git 仓库，没有执行 Git 重置、覆盖检出或提交。
- 正式管理员密码和正式数据库凭据需要操作者按说明提供；本轮没有替用户选定或保存正式密码。
- 原有 `.mysql-data*` 目录的冷启动问题未修复。通过测试的是新建隔离实例，不能据此将原实验数据库标为可部署。
- 用户数据授权隔离、其他业务接口 CSRF、退出入口 POST 化、登录限流、多设备会话撤销及生产 TLS 配置未完成。
- 其他审计问题仍留待后续阶段；本阶段版本仅建议在本机使用，不能视为公网发布验收通过。
- 如需回滚，应停止服务、核对用户是否有后续修改，再按差异撤销本阶段代码。不得用破坏性 Git 操作或删除运行目录回滚；密码显式重置若已由操作者执行，不应通过恢复旧弱密码来回滚。

## 7. 下一阶段建议

建议验收本阶段后进入授权和用户隔离阶段。进入前应确认使用哪个现存 MySQL 实例，并由操作者完成正式管理员密码配置。本任务等待用户验收，不自动进入下一阶段。

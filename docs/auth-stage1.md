# 第一阶段：认证、数据库行为与基础会话安全

本阶段仅改造认证及启动边界。扫描引擎、模块、外部数据源、泄露样例库和隐私申请功能未改造。

## 行为

- MySQL 认证不可用时，Web 服务初始化失败并以非零状态退出，不创建内存账号库。
- 服务运行后，登录或注册遇到认证数据库故障，返回 HTTP 503 和“认证数据库暂不可用，请稍后重试。”，不报告注册成功或密码错误。
- 操作者必须提供 MySQL 用户名和非空数据库密码；脚本不写入、猜测或回显密码。
- 管理员用户名默认为 `admin`，密码没有默认值。首次初始化必须显式提供管理员密码。
- 管理员密码为 12–1024 字符，包含字母以及数字或非空白符号。现有 `admin123` 密码或非法管理员哈希会阻止启动，必须显式重置。
- 环境变量中的新密码不会自动覆盖已有账号；只有显式设置 `SF_AUTH_ADMIN_RESET=1` 才会更新指定管理员。
- 注册、登录及认证存储统一去掉用户名首尾空格，密码本身不做 trim。
- 新密码使用 PBKDF2-HMAC-SHA256、随机 16 字节盐、默认 600000 次迭代和恒定时间比较；原有合法 200000 次迭代哈希仍可验证。明文哈希字段不会被当作合法密码接受。
- 旧 `passwd` 文件保留但不读取。`SF_LEGACY_PASSWD_AUTH=1` 明确报错，禁止启用明文密码认证。
- 登录成功更换 Session ID；退出清空会话、撤销旧 ID 并使 Cookie 过期。会话闲置 30 分钟或达到绝对有效期后需要重新登录。
- Cookie 使用 HttpOnly、SameSite=Lax、浏览器会话有效期；HTTPS 可使用 Secure。认证页面及非静态响应使用 `Cache-Control: no-store`。
- 登录、注册 POST 必须携带同一浏览器会话表单中的 CSRF token。登录跳转参数进行路径检查及 HTML 转义。

## MySQL 前提

需要已经启动并能连接的 MySQL。下述“初始化”只创建缺少的应用数据库、`users` 表和管理员，**不初始化或重建 MySQL 数据目录**。

现有 `.mysql*`、数据库、虚拟环境、部署文件均保留。启动器不自动启动、关闭、修复或重建任何现存 MySQL 实例。

建议使用本机 MySQL 的专用应用账号。当前初始化和 Web 启动仍执行幂等的 `CREATE DATABASE IF NOT EXISTS` / `CREATE TABLE IF NOT EXISTS`，因此该账号需要相应建库/建表权限，以及读取、插入、更新用户记录的权限。部署账号与日常账号的权限拆分尚未完成。不要把生产管理员凭据放入源码或批处理文件。

## 配置变量

| 变量 | 说明 |
|---|---|
| `SF_AUTH_MYSQL_HOST` | 默认 `127.0.0.1` |
| `SF_AUTH_MYSQL_PORT` | 默认 `3306`，与实际服务端口一致 |
| `SF_AUTH_MYSQL_USER` | 必填，MySQL 用户名 |
| `SF_AUTH_MYSQL_PASSWORD` | 必填，非空 MySQL 密码，只从进程环境读取 |
| `SF_AUTH_MYSQL_DATABASE` | 默认 `spiderfoot_auth`；仅字母、数字和下划线，1–64 字符 |
| `SF_AUTH_ADMIN_USER` | 默认 `admin`，去空格后为 3–32 字符 |
| `SF_AUTH_ADMIN_PASS` | 首次初始化或显式重置时必填，之后应从环境中移除 |
| `SF_AUTH_ADMIN_RESET` | 仅在停服后的一次显式改密操作设置为 `1`，完成后移除 |
| `SF_AUTH_PBKDF2_ITERATIONS` | 默认 `600000`，范围 `200000`–`2000000` |
| `SF_AUTH_COOKIE_SECURE` | 默认 `0`；HTTPS 反向代理部署设为 `1`；应用自身 HTTPS 自动开启 Secure |
| `SF_AUTH_SESSION_MAX_AGE_SECONDS` | 绝对会话有效期，默认 `28800`（8 小时），范围 1–86400 秒 |

不自动读取 `.env` 文件。密码不要写入命令行参数、版本库或日志。环境变量仅在当前进程及其子进程有效；不要用 `setx` 持久保存密码。

## 首次初始化

在 PowerShell 中执行；用户名和端口应替换为已有 MySQL 实例的配置，密码通过隐藏输入读取：

```powershell
Set-Location 'D:\消痕侠\消痕侠程序'
$env:SF_AUTH_MYSQL_HOST = '127.0.0.1'
$env:SF_AUTH_MYSQL_PORT = '3306'
$env:SF_AUTH_MYSQL_DATABASE = 'spiderfoot_auth'
$env:SF_AUTH_MYSQL_USER = Read-Host 'MySQL user'
$env:SF_AUTH_MYSQL_PASSWORD = [Net.NetworkCredential]::new('', (Read-Host 'MySQL password' -AsSecureString)).Password
$env:SF_AUTH_ADMIN_USER = 'admin'
$env:SF_AUTH_ADMIN_PASS = [Net.NetworkCredential]::new('', (Read-Host 'First administrator password' -AsSecureString)).Password
& '.\.venv\Scripts\python.exe' -B '.\scripts\auth_admin.py' --initialize
if ($LASTEXITCODE -ne 0) { throw 'Authentication initialization failed; read the message above.' }
$env:SF_AUTH_ADMIN_PASS = $null
```

重复运行初始化不会删除表或已有账号，也不会在未开启显式重置时覆盖已有密码。缺失管理员、重复初始化中的错误或权限不足会明确报错。

## 已有弱口令或非法管理员哈希

先停止 Web 服务，设置正确的数据库环境变量，然后执行：

```powershell
$env:SF_AUTH_ADMIN_USER = 'admin'
$env:SF_AUTH_ADMIN_PASS = [Net.NetworkCredential]::new('', (Read-Host 'New administrator password' -AsSecureString)).Password
$env:SF_AUTH_ADMIN_RESET = '1'
& '.\.venv\Scripts\python.exe' -B '.\scripts\auth_admin.py' --initialize
if ($LASTEXITCODE -ne 0) { throw 'Administrator reset failed; read the message above.' }
$env:SF_AUTH_ADMIN_PASS = $null
$env:SF_AUTH_ADMIN_RESET = $null
```

这会更新指定账号的密码哈希，不删除账号或业务数据。若自定义了管理员用户名，但旧 `admin` 仍使用已知默认密码，必须先对旧 `admin` 执行上述显式改密。改密后重新启动 Web 服务，清除原进程中的所有登录会话。

## 启动与检查

保持数据库连接环境变量可用，先检查再启动：

```powershell
& '.\.venv\Scripts\python.exe' -B '.\scripts\auth_admin.py' --check
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\scripts\start-local.ps1' -CheckOnly
if ($LASTEXITCODE -ne 0) { throw 'Authentication preflight failed.' }
& '.\启动平台.bat'
```

访问 `http://127.0.0.1:5001/login`，使用首次配置的账号密码。`启动本地版.bat` 和 `启动本地版.ps1` 转发到相同启动入口，失败时保留非零退出码。启动时不运行全局 pip/npm 安装。

启动器使用项目 `.venv`，默认保留原本地启动器的数据位置 `.runtime-profile\.spiderfoot`，日志和缓存也放在其下。可通过 `SPIDERFOOT_DATA`、`SPIDERFOOT_LOGS`、`SPIDERFOOT_CACHE` 指定其他项目内路径。测试均使用 `.stage1` 下的新建目录，不使用该现存业务路径。

会话只保存在进程内，重启后需重新登录；用户账号及密码哈希保存在 MySQL，不会因 Web 进程重启消失。直接运行 `sf.py -l ...` 同样必须提供认证环境变量；如需限制其扫描数据写入项目，应同时配置 `SPIDERFOOT_*` 路径。

## 测试

从项目目录运行，使用新的 basetemp，避免 pytest 清理任何已有目录：

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$run = Join-Path '.stage1' ('tests-' + [guid]::NewGuid().ToString('N'))
& '.\.venv\Scripts\python.exe' -B -m pytest test\stage1 --confcutdir=test\stage1 --basetemp $run -v --tb=short -p no:cacheprovider -W ignore::DeprecationWarning
```

快速行为测试只替换第三方 MySQL 连接边界；HTTP 测试启动真实 CherryPy 和真实认证类。真实数据库测试另启项目现有 MySQL 8.0.46 二进制，使用新建数据目录、随机本机端口和内存随机密码，验证数据库冷重启、应用启动及持久化。它仅在本地 Windows 环境执行，不访问现有数据库。测试保留自身数据和日志，正常关闭自建进程并撤销自身临时盘符。

真实测试实例使用 `--innodb-undo-log-truncate=OFF`，该选项仅用于新建的测试实例，没有修改原有 MySQL 配置或数据。它通过冷启动验证不能证明原 `.mysql-data*` 目录的问题已修复。

## 尚未纳入本阶段

扫描和申请的用户授权隔离、其他业务写接口的 CSRF、登录限流、多设备在线撤销、生产 HTTPS/MySQL TLS 配置及外部数据源改造未完成。退出仍保留现有 GET 入口以兼容导航，注销请求的 POST 化留待后续请求保护阶段。当前不建议将该阶段版本直接公开到公网。

# 消痕侠 — 数字痕迹管理平台

比赛提交源码，2026-10-19。本包是已完成本地验收的功能与界面，不含开发工作区、现存账号、真实查询记录或凭据。上游说明保留在 [docs/upstream-spiderfoot-README.md](docs/upstream-spiderfoot-README.md)。

## 功能与真实边界

| 入口 | 真实能力 | 限制 |
| --- | --- | --- |
| 域名 / 网站 / IP | SpiderFoot 原生扫描；统一入口 DNS 检索 | 只覆盖启用模块，统一入口不是全模块扫描 |
| 用户名 | Sherlock、Maigret、WhatsMyName | 分别最多 10 / 25 / 10 个站点；同名不证明属于本人 |
| 邮箱 | Holehe 注册信号、HIBP 已收录事件 | Holehe 只调用 GitHub / Gravatar；注册信号不是泄露；HIBP 需要 Key |
| 本地样例检测 | SQLite 合成演示数据 | 两条合成记录，非真实泄露事件，不是实时互联网查询 |
| 申请记录与人工跟进 | 用户确认、持久记录、管理员备注和处理状态 | 不是自动删除，不保证平台执行，没有自动提交渠道 |
| 多用户 | MySQL 密码哈希、Session、CSRF、资源隔离 | 本机参赛版本，不是生产集群 |

**当前数据源未发现匹配，不代表不存在相关信息。** 失败、超时、未安装、未配置与无匹配分别展示。不支持手机号、身份证、QQ 的“全网查全”。

## 验证过的环境

- Windows x64，CPython **3.12.10**（安装器要求 Python 3.12）。
- MySQL Community Server **8.0.46 Windows x64 ZIP**；启动器创建本机独立实例，监听随机 loopback 端口。
- Edge / Chrome 等现代浏览器。WebGL、移动端和减少动态效果会降级，不影响业务。
- 默认地址 `http://127.0.0.1:5001/login`，端口占用会明确停止，不关闭其他程序。
- **运行无需 Node.js / npm**。正式 React 构建、后台 JS/CSS/字体和许可证已包含。仅前端开发重建时需要 Node。
- 首次安装依赖及实时检索需要网络；源码 ZIP 不是离线免安装 EXE。

## 全新电脑首次安装

1. 安装 Python 3.12 x64（包含 Python Launcher）。新开 PowerShell：`py -3.12 --version`。
2. MySQL 如提示缺少运行库，从微软官方安装 Visual C++ 2015–2022 x64 Redistributable。
3. 从 [MySQL 官方页面](https://dev.mysql.com/downloads/mysql/8.0.html) 下载 **mysql-8.0.46-winx64.zip**，不要选 debug/test。官方直链：<https://dev.mysql.com/get/Downloads/MySQL-8.0/mysql-8.0.46-winx64.zip>。安装脚本不自动下载二进制，也不安装系统服务。
4. 解压本源码到新的、有写权限的目录，如 `D:\Contest\xiaohenxia`。中文路径支持。不要复制旧 `.venv`、`.runtime-profile` 或数据库。
5. 在解压目录打开 PowerShell（下载路径按实际替换）：

```powershell
py -3.12 scripts/install-release.py --mysql-archive 'D:\Downloads\mysql-8.0.46-winx64.zip'
```

也可执行 `安装比赛环境.bat --mysql-archive "D:\Downloads\mysql-8.0.46-winx64.zip"`。

安装器校验 MySQL SHA-256，在项目内创建 `.venv`、`.mysql` 和 `.tools/live`，按锁文件安装 Python 依赖，将 21 个发布资源恢复至旧模板兼容路径。不运行 npm，不全局安装，不读取开发数据库。

MySQL SHA-256：`28e9eda019d88eff4478d811ea2110b83f02a3966be157fe91cc55def3ab0d4d`。
与官方页面核对的 MD5：`003f527d5df61b663ff191038cd676bd`。下载信息见 third_party/mysql-artifact.json。

安装外部工具的网络暂不可用时，可加 `--skip-live-sources` 先启动主程序；此时相应来源显示“未安装”，不能宣称检索完成。网络恢复后：

```powershell
.\.venv\Scripts\python.exe -B scripts/setup_live_sources.py
.\.venv\Scripts\python.exe -B scripts/setup_live_sources.py --check
```

不要使用历史开发选项 `--include-app`，它会调用 npm。可选 `--wheelhouse <目录>` 使用自行准备的 Python 离线包；WhatsMyName 规则首次下载仍需网络。完整离线介质不随源码包提供。

## 启动、停止、再次启动

双击 **双击启动.bat**。首次在控制台设置管理员 `admin` 强密码（至少12位，包含字母及数字或符号；输入不回显）。没有预设密码，也没有 admin123。

首次初始化需要等待，完成后自动打开浏览器。保持窗口打开；退出时在启动窗口按 **Ctrl+C**，等待“已安全停止”。以后双击同一个文件，账号、扫描、检索任务和申请记录保留；会话重启后需重新登录。

命令行等价：

```powershell
.\.venv\Scripts\python.exe -B scripts/start-desktop.py
```

运行数据统一保存在 `.runtime-profile/desktop/`：独立 MySQL、扫描 SQLite、统一检索 SQLite、缓存、日志及 Windows DPAPI 加密配置。数据库密码随机生成；DPAPI 绑定本机 Windows 用户，不能直接跨电脑使用。数据库故障明确停止，不回退内存账号库。

## 账号与配置

本包**没有现成账号或通用演示密码**。

- 管理员首次启动由演示者设置，只有管理员能修改人工跟进状态。
- 在真实注册页注册 `demo_user_a` / `demo_user_b`，密码自行设置，不写入代码、截图或说明。
- `.env.example` 只有变量和安全示例，**应用不会自动读取 .env**。推荐桌面启动无需手填数据库配置。
- HIBP Key 仅从启动进程的 `SF_HIBP_API_KEY` 读取；未配置时不发请求，页面显示“未配置”。不要写入 Git/ZIP。
- 外部 MySQL 首次初始化、幂等迁移和显式改密见 [docs/auth-stage1.md](docs/auth-stage1.md)。历史“尚未纳入本阶段”段落只是阶段一记录，当前行为以本 README 和 competition-guide 为准。

## 演示、源码与许可

- [演示流程、合成数据、初始化和已知限制](docs/competition-guide.md)
- [第三方许可证清单](THIRD_PARTY_LICENSES.md)
- [本次冷启动验证](docs/release-validation.md)

主要目录：`sf.py/sfwebui.py/sfscan.py` 为入口/路由/引擎；`spiderfoot/` 为认证、权限、存储、任务、模板和静态资源；`modules/`、`correlations/` 保留 SpiderFoot；`frontend/` 保存 React 源码；`spiderfoot/static/react-auth/` 为正式构建；`third_party/runtime-assets/` 保存必需浏览器发布文件及许可；`scripts/` 为安装启动打包；`data/leak-check.db` 仅合成样例；`test/stage1` 至 `stage6` 保留回归。

精确 Python 版本见 requirements-release-win-py312.lock.txt（包含回归工具），外部工具见 scripts/live-source-locks。根 LICENSE 保留上游许可；第三方完整许可随源码归档，不要删除。

## 包完整性

RELEASE.json 记录对应 Git SHA；MANIFEST.sha256 校验包内除自身外每个文件。包外同名 `.sha256` 校验整个 ZIP：

```powershell
Get-FileHash '.\消痕侠-比赛源码-<提交短哈希>.zip' -Algorithm SHA256
```

不要直接压缩运行后的目录。使用 scripts/package-release.py 从提交树生成干净包；不带 .git、虚拟环境、node_modules、密钥和运行数据。

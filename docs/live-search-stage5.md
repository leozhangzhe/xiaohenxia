# 第五阶段：统一实时检索

## 官方来源与许可证（2026-10-18 核对）

| 来源 | 官方仓库 / 文档 | 安装 | 许可证 / 使用边界 |
| --- | --- | --- | --- |
| SpiderFoot | https://github.com/smicallef/spiderfoot | 沿用项目 requirements.txt | MIT；原引擎保留 |
| Sherlock | https://github.com/sherlock-project/sherlock | sherlock-project==0.16.2 | MIT |
| Maigret | https://github.com/soxoj/maigret | maigret==0.6.6 | MIT |
| WhatsMyName | https://github.com/WebBreacher/WhatsMyName | 固定提交 JSON 规则，经 sfp_accounts 使用 | CC BY-SA 4.0；保留规则原始作者与许可信息 |
| Holehe | https://github.com/megadose/holehe | holehe==1.61 | GPLv3；独立环境调用，不修改上游源码；若再分发工具须遵守其源码和许可要求 |
| HIBP | https://haveibeenpwned.com/API/v3 | 复用 sfp_haveibeenpwned.query | API 服务条款与归属说明；需要有效订阅 Key |

直接依赖及当前解析出的间接依赖固定在 scripts/live-source-locks/*.txt。
WhatsMyName 规则固定提交 ec273f81aa1b8728a932589dcba71c6894001acc，SHA256 为
8893631e8bf0cab4dc846c6fbfb4010c83187384b438b0c99091329e2ce07afa。
源码中不包含下载后的第三方环境或检索数据。规则许可信息保留在下载的原始 JSON 中。

## 安装与启动

前提：Windows、Python 3.12、Node.js 18 或更高版本及 npm、已配置的 MySQL。安装脚本只在本项目内建虚拟环境，
既有 .venv、.mysql* 和数据文件都保留。源码 ZIP 解压后运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install-live-sources.ps1 -IncludeApp
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install-live-sources.ps1 -CheckOnly
```

仅重建检索源环境时省略 -IncludeApp。安装脚本创建 .tools/live/{sherlock,maigret,holehe}，
下载官方固定版本规则到 .tools/live/whatsmyname。不会下载独立 EXE 或其他未知二进制。
主应用前端通过 package-lock.json 与 npm ci 重建。网络不可用或校验不符时安装明确失败，保留现有规则。

按 docs/auth-stage1.md 配置 SF_AUTH_MYSQL_* 与首次管理员环境变量后：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

登录后打开 /livesearch。HIBP Key 可选：只在当前服务进程环境设置 SF_HIBP_API_KEY；不写进源码、
测试、数据库或示例文件。未配置时不启动 HIBP worker、不发请求。Key 变更后重启服务。

## 覆盖范围和任务语义

- 域名 / 网站 / 公开 IP：沿用原 SpiderFootScanner，引擎运行 DNS Resolver 与 Storage 模块；网站只查询主机名。
  原扫描页面和其他 SpiderFoot 模块继续保留。统一入口不启用全模块扫描、端口探测或网页爬取。
- 用户名：Sherlock 固定最多 10 个常见站点；Maigret 当前安装库排名前 25 个站点，关闭递归、信息抽取和代理绕过；
  WhatsMyName 规则中最多 10 个常见站点，复用 sfp_accounts.checkSites。规则匹配不证明身份归属。
- 邮箱：Holehe 仅调用 GitHub 与 Gravatar 两个模块，不调用账户创建或发送找回邮件的模块，不保存恢复电话和邮箱。
  注册信号不是泄露记录；上游规则过时或封禁会显示部分完成 / 失败。
- HIBP 只查官方已收录的 breach 名称，不保存泄露正文，不查询 paste、电话或身份证。
- 同时最多 2 个来源 worker；每个用户最多 3 个未完成任务，整个服务最多 16 个未完成任务；
  单来源 90 秒截止。每个来源独立状态，个别失败不丢弃其他来源结果。
- Windows Job Object 约束整个进程树，POSIX 使用独立进程组；标准输入在进程约束建立后才发送。
  超时、取消、正常结束及服务正常关闭都会关闭归属进程树；服务重启将中断来源标为已取消。
- 任务与来源结果存储在主扫描数据库路径旁的 .live.sqlite，包含 user_id；仅本人可读、取消或删除。
  原始查询值只用于 worker 和受用户隔离的存储；页面任务摘要与 query 字段对用户名、邮箱脱敏。
  创建/取消/删除使用 POST + 当前 Session CSRF，浏览器地址仅含随机任务 ID。
- 外部检索本身需要向对应平台发送输入；外部服务的协议可能使用 GET 路径/URL。
  本应用不把敏感查询值放入浏览器检索 URL、普通日志或错误信息。源 worker 的第三方调试输出被抑制。
- HTTP/HTTPS 原始链接保留；拒绝 javascript/data/file、相对链接与含凭据链接。DNS 记录没有网页链接时明确显示未提供。
- 检索无结果不表示安全；未安装、未配置、失败、超时与无匹配分别展示。

## 打包与验证

源码包使用 git archive 生成，保证仅包含已提交源码、依赖锁文件和重建脚本；不要把 .tools、.venv、
.runtime-profile、.cache、运行数据库和运行日志打进 ZIP；保留明确合成样例 data/leak-check.db。
MySQL 由使用者明确安装和配置。

```powershell
.\.venv\Scripts\python.exe -m pip install -r test/requirements.txt
.\.venv\Scripts\python.exe -m pytest test/stage5 -ra
.\.venv\Scripts\python.exe -m pytest test/stage1 test/stage2 test/stage3 test/stage4 test/stage5 -ra
```

测试仅使用合成数据与受控输出。真实网络冒烟每个已配置工具只运行一次；HIBP 无 Key 只检查未配置，
不会发送匿名或伪造密钥的查询。真实网络失败按实际状态报告，不重复请求来追求命中。

# 比赛源码交付验证

## 已执行的业务回归

2026-10-19，在原项目中对已验收界面和业务执行：

```powershell
.\.venv\Scripts\python.exe -B -m pytest test/stage1 test/stage2 test/stage3 test/stage4 test/stage5 test/stage6 --basetemp '.runtime-profile/release-regression-<新随机目录>' -ra --tb=short
```

结果：**351 通过，0 失败，0 错误，0 跳过，971 个警告，272.22 秒，退出码 0**。警告主要来自 pytest 7 与 Python 3.12 的旧 AST API；没有放宽认证或权限。本次未运行依赖外网的完整历史测试集。

## 全新目录验收方式

先从最终 Git 提交生成 ZIP，再解压到新的独立目录，按 README 安装。不会复制原 .venv、数据库、账号、配置或查询记录。首次在线安装验证与可选 wheelhouse 安装方式均由 README 描述，Node 不参与运行或安装。

```powershell
python scripts/install-release.py --mysql-archive '<官方MySQL ZIP路径>'
# 可选：在上述命令加 --wheelhouse '<已下载Python发行包目录>'
.\.venv\Scripts\python.exe -B scripts/verify-release.py --report '..\cold-start-results.json'
```

verify-release 使用双击启动器的同一个 DesktopServer，实现相同数据库初始化、账号检查、Web 启动和停服。为保留用户正在运行的 5001 服务，验收选择随机空闲 Web 端口。使用新的 .runtime-profile/release-verification 和随机合成密码，创建 A/B 两个合成用户，不触及开发工作区。

检查：包内每文件 SHA-256；真实 MySQL/DPAPI；注册/错误密码/登录/刷新/退出；认证和后台资源 HTTP 200；来源安装状态和 HIBP 无 Key；真实原生 DNS 扫描；统一检索创建、取消、删除、状态与来源；扫描/任务/申请隔离；合法申请持久化、普通用户无处理权限；缺失/中文错误/跨会话 CSRF 无副作用；写接口 GET 405；正常关闭及端口释放；再次启动后持久数据可读；密码和合成邮箱不进入日志。

首次候选检查在退出步骤因验收脚本给无参数的退出接口发送 POST + CSRF 参数而失败。现按现有导航真实 GET /logout 调用，保留退出、旧会话/旧 token 失效断言；没有修改业务路由或放宽安全断言。失败候选报告和原始日志保留在包外验收目录。

**最终 ZIP 对应的逐项执行结果、Git SHA 和通过数保存在包外同名冷启动验收 JSON 中**，交付时与 ZIP、SHA-256 校验文件一起提供。失败会抛异常且报告记录失败项，不会把异常隐藏为成功。这里保留可复现方法，避免把包生成后的运行数据再次塞入源码。

本轮冷启动是实际 HTTP 和数据库验收，不声称另做了视觉浏览器验收；界面沿用用户已通过的本地最终验收。外网检索状态取实际响应，无伪造命中。依赖安装日志与运行日志仅保存在验收目录，不进入 ZIP。

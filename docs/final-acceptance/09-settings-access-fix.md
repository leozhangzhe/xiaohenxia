# 系统设置入口与403页面修复

2026-10-19，针对用户截图的冻结期阻塞修复，不扩展功能。

## 根因与行为

系统设置本来只允许管理员使用；共享侧栏却无条件展示入口。普通用户点击后，权限边界正确拒绝，但没有自定义403处理，CherryPy默认页暴露内部路径和堆栈。

- 服务端按当前Session计算管理员标志，共享导航仅向管理员显示系统设置。
- 新增安全的403页面，复用现有工作区和返回入口；管理员权限不足、CSRF失效、其他拒绝分别使用固定中文提示，不展示内部异常、用户输入或堆栈。
- 仍返回403；没有改成成功、放开设置权限或绕过CSRF。
- 通用错误标题与说明允许服务端提供，并继续HTML转义。

修改：sfwebui.py、spiderfoot/web_access.py、spiderfoot/templates/HEADER.tmpl、spiderfoot/templates/error.tmpl、新增test/stage6/test_settings_access_http.py及本文档/索引。

## 测试

先运行新增真实HTTP用例，6失败、2通过、233警告、退出码1，复现导航泄露和默认堆栈；再实现修复。

```powershell
.\.venv\Scripts\python.exe -B -m pytest test/stage6/test_settings_access_http.py test/stage6/test_freeze_error_and_search.py test/stage2/test_business_csrf_http.py test/stage2/test_isolation_http.py --basetemp .runtime-profile/settings-access-20261019/green --junitxml .runtime-profile/settings-access-20261019/green.xml -ra --tb=short
```

结果：**127通过，0失败，0错误，0跳过，426警告，55.42秒，退出码0**。包含管理员真实设置表单、普通用户403/隐藏入口、有效CSRF仍不能越权写配置、缺失/错误/中文CSRF拒绝、原用户隔离及业务CSRF回归。配置更新拒绝前后数据库快照一致。没有运行第二次完整旧测试集，08-tests.md的历史失败仍保留，不宣称整个项目全绿。

## 当前运行实例

确认原项目进程树后，通过原监督进程停止协议重启，仅使用原manual-ui-5567338工作区和MySQL端口54519，保留所有账号和数据库。停止请求移为带日期的完成记录，没有删除。

首次就绪轮询将venv启动器PID当作监督进程PID而超时；随后只读核实实际监督子进程的父PID正是该启动器，state为ready，登录HTTP200。这是本次运行控制轮询误报，不是服务启动失败；没有据此重复重启。原始证据在忽略目录.runtime-profile/settings-access-20261019中。

重启后需要重新登录。管理员可使用系统设置；普通账号继续使用自己的检索和申请，不授予管理员权限。本轮以真实HTTP/DOM与数据库验证，没有新增浏览器截图验收。

# 最终测试结果与验收矩阵

日期：2026-10-19。**开发自测未达到完整回归全绿，不能据此宣布最终验收通过。** 未删测试、未放宽权限、未将外网故障解释为无结果。以下计数不得相加冒充互不重复的总通过数。

## 环境与证据

Windows x64、项目Python 3.12.10、真实隔离MySQL 8.0.46。真实MySQL/DPAPI测试以当前Windows用户运行；普通单元测试使用受控边界，分别说明。账号与查询均为合成数据；没有清空现有用户库。测试没有结束用户5001实例。

原始证据保留于项目内 `.runtime-profile/final-acceptance-20261019-143250/`，不纳入Git/交付包。原始失败日志可能包含测试会话/HTML，勿公开。可公开的计数及失败用例名见本目录 `test-results.json`、`failure-inventory.md`；不复制响应正文、密码或token。

提交前只读源码审计：扫描允许交付的1123个文件（17,288,846字节），现有规则未发现秘密；SQLite完整性及合成约束检查通过：2条合成记录，邮箱仅example.invalid，phone/id/qq均NULL，无空闲页。扫描规则不能证明绝无未知秘密。没有生成新版ZIP、提交日志或运行数据库。

## 运行清单

| 运行 | 通过 | 失败 | 错误 | 跳过 | 未选中 | 警告 | 耗时 | 退出码 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 初次收集（readline不兼容） | — | — | 1收集错误 | — | — | — | — | 2 |
| CLI启动新增红测 | 0 | 1 | 0 | 0 | 0 | 27 | 0.38秒 | 1 |
| 首次CLI组诊断 | 39 | 7 | 0 | 2 | 0 | 72 | 1.14秒 | 1 |
| 夹具修复定向组 | 48 | 0 | 0 | 2原有TODO | 0 | 78 | 14.96秒 | 0 |
| 独立外网pytest组 | 3 | 3 | 0 | 0 | 2178 | 1004 | 6.88秒 | 1 |
| **唯一完整项目回归** | **1916** | **48** | **0** | **214原有** | **6** | **2610** | **349.39秒** | **15，汇总后定点停止** |
| 错误页/首次REGEXP新增红测 | 1 | 4 | 0 | 0 | 0 | 198 | 4.19秒 | 1 |
| 修复后首次57项组（新增夹具缺管理员配置） | 56 | 1 | 0 | 0 | 0 | 203 | 66.68秒 | 1 |
| 修正显式管理员夹具的单测 | 1 | 0 | 0 | 0 | 0 | 198 | 0.94秒 | 0 |
| **最终定向认证/CSRF/误报/错误页/查询组** | **57** | **0** | **0** | **0** | **0** | **203** | **68.79秒** | **0** |
| **最终真实MySQL/桌面冷重启组** | **3** | **0** | **0** | **0** | **0** | **197** | **28.71秒** | **0** |

依赖修复后收集2184项；完整运行在新增5项错误页/SQL红测之前。完整回归写完JUnit和汇总后未退出，确认对应pytest PID 71628且无子进程，才停止该叶进程；退出码15不是自然通过。旧UI单元测试没有日志消费者，后续以公开loggingQueue注入普通队列隔离，57项定向组正常退出。未再次运行完整回归，不能把代表性定向结果改写为新的完整通过数。

警告主要来自旧依赖/弃用API及unittest运行器，未通过过滤警告制造零警告。所有跳过为原有标记；新增的external标记已在外网组实际执行。

## 执行命令

在项目根目录，用 `.venv\Scripts\python.exe -B -m pytest`；本轮工作目录变量 `$evidence` 指向上述忽略的验收目录。各次使用不同basetemp，保留证据，不清理用户文件。

```powershell
# 仅一次完整运行
.\.venv\Scripts\python.exe -B -m pytest test -m 'not external' --basetemp "$evidence/full-local-once" --junitxml "$evidence/full-local-once.xml" -ra --tb=short

# 外网单独运行一次
.\.venv\Scripts\python.exe -B -m pytest test -m external --basetemp "$evidence/external-pytest" --junitxml "$evidence/external-pytest.xml" -ra --tb=short

# 最终定向57项
.\.venv\Scripts\python.exe -B -m pytest test/stage6/test_freeze_error_and_search.py test/unit/test_spiderfootwebui.py::TestSpiderFootWebUi::test_error test/unit/test_spiderfootwebui.py::TestSpiderFootWebUi::test_error_page_404 test/unit/spiderfoot/test_spiderfootdb.py::TestSpiderFootDb::test_search_should_return_a_list test/stage1/test_auth_http.py test/stage2/test_business_csrf_http.py test/stage3/test_false_positive_http.py --basetemp "$evidence/blockers-final-directed" --junitxml "$evidence/blockers-final-directed.xml" -ra --tb=short

# 最终真实MySQL与桌面重启3项
.\.venv\Scripts\python.exe -B -m pytest test/stage1/test_real_mysql.py test/stage5/test_desktop_launcher.py::test_real_desktop_cold_restart_keeps_accounts_and_uses_same_database --basetemp "$evidence/final-real-startup" --junitxml "$evidence/final-real-startup.xml" -ra --tb=short
```

运行时设置 `WEBTEST_INTERACTIVE=false`、`PYTHONDONTWRITEBYTECODE=1`。没有放宽生产认证或向用户运行实例注入测试数据。

## 完整失败分类（48项，保留原结果）

| 分类 | 数量 | 结论 |
| --- | ---: | --- |
| Windows CLI负数退出码预期 | 5 | 旧测试期待Unix 255，Windows为4294967295；均为失败退出，断言未篡改，兼容问题仍保留 |
| 旧CPWebCase路由测试 | 15 | 旧夹具未建立现行Session/资源中间件，含GET写操作/旧200/英文断言；存在上下文500，不能统一声称无害或通过 |
| 未标记external的旧外网模块 | 11 | 广告列表、DNS过滤/黑名单等依赖外网；按外部依赖失败单列，不冒充本地确定性失败或无结果 |
| 旧WebUI单元测试 | 16 | 11项关联真实Mako缺pageid问题（已修复并定向验证代表项）；3项缺Session上下文，1项旧英文设置标题，1项期待空数组而当前故障返回503。未经修复后整组重跑，不能宣称16项全部解决 |
| 新SQLite首连接REGEXP | 1 | 真实程序缺陷，已修复，首次连接及重开查询新增用例和原查询用例通过 |

同一完整JUnit的分拆：阶段1–6 **352通过**；旧本地/core **1541通过、37失败、35跳过**；未标记外网模块目录 **23通过、11失败、179跳过**。这不是三次独立运行。由于发现旧模块漏标，`not external`并未完全排除网络；本轮不改跳过标记追求全绿。

## 外网结果（每来源一次，不重复查询）

现有适配器合成输入冒烟，结果写入 `live-sources.json`；汇总退出码1，表示并非所有来源完整完成。

| 来源 | 实际状态 | 条数 | 解释 |
| --- | --- | ---: | --- |
| SpiderFoot | 完成 | 2 | DNS模块返回，合成保留域名的响应仍须核验，不能据此认定公网身份 |
| Sherlock | 部分完成 | 1 | 部分站点受限，同名不证明本人 |
| Maigret | 失败 | 0 | 数据源不可用，不是成功无匹配 |
| WhatsMyName | 部分完成 | 0 | 部分站点不可用或规则受限 |
| Holehe | 部分完成 | 0 | 邮箱注册信号，不是泄露记录 |
| HIBP | 未配置 | 0 | 本次显式不使用Key，没有发送请求 |

独立pytest外网组3失败：IPv6解析无预期结果、主机解析地址与预期不同、IP验证不符。观察到198.18网段响应，疑似环境DNS改写；没有核实系统配置，不确定根因，也未擅自改变网络。所有来源输出结构和链接协议检查通过，不代表外网查询内容真实准确。

## 验收要求与证据边界

| 范围 | 本轮证据 | 结论/限制 |
| --- | --- | --- |
| 数据库失败不回退内存；默认弱密码；哈希；空格一致；持久化 | stage1认证/真实MySQL，最终57+3定向组 | 通过对应测试；真实冷重启账号保留，未公布密码 |
| A/B扫描、结果、申请隔离；管理员权限 | 同一次完整运行stage2、stage4、stage5；最终业务CSRF/误报定向 | 对应阶段用例通过；不能替代仍失败的旧路由测试 |
| POST、CSRF、跨Session、拒绝无数据库副作用 | 最终test_business_csrf_http、test_false_positive_http | 定向通过，未绕过保护 |
| URL/日志脱敏、HTML/链接安全、第三方授权边界 | 阶段2/3/5/6回归；新增真实非法输入HTTP测试 | 测试合成值不出现在URL/响应/日志；不承诺覆盖所有历史第三方日志 |
| 来源/时间/链接；无结果≠安全；本地样例真实性；失败/部分完成 | 阶段3/5页面和DOM/HTTP测试；本次真实来源报告 | 对应测试通过，外网不全可用；无Key未请求 |
| 申请真实状态、备注、用户确认、迁移、隔离及持久化 | stage4真实MySQL及HTTP（同一次完整运行） | 对应阶段通过，无自动平台提交承诺 |
| 当前电脑启动、依赖、重启 | 当前5001登录HTTP200、最终3项真实启动、pip check | 当前实例未改；新机冷启动未在本轮重新完整执行，上一提交包验收仅历史证据 |
| 新真实浏览器可视验收 | 本轮未执行新的截图/完整人工浏览器验收 | 不将DOM/HTTP测试冒充浏览器人工验收；先前用户视觉验收仅历史记录 |

## 仍待处理/确认

完整项目回归全绿条件尚未满足：旧路由/Session夹具、跨平台退出码断言及外网可达性仍有失败。阻塞修复后没有第二次完整回归，因此最终门禁仍待后续明确安排；本轮停止新增功能，等待用户最终验收，不创建通过标签、不推送、不覆盖旧提交包。

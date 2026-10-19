# 修改文件与回滚说明

## 本轮范围

未改认证、Session、CSRF、资源归属、数据库迁移、接口、扫描引擎或人工申请流程。生产代码仅修复错误页渲染/转义，以及新SQLite连接的REGEXP注册时机。没有新数据源或视觉重做。

| 文件 | 原因 |
| --- | --- |
| requirements.txt | Windows旧pyreadline2.1无法在Python3.12导入，改用pyreadline3==3.5.6 |
| requirements-release-win-py312.lock.txt | 同步可重建依赖版本 |
| third_party/python/inventory.json、licenses/pyreadline3/licenses/LICENSE.md | 新依赖BSD许可证归档，旧许可文件保留 |
| test/stage6/test_freeze_startup.py | 新进程真实导入CLI/readline的回归，先失败再修复 |
| test/conftest.py | 为隔离CLI子进程准备合成TLD缓存，不依赖在线publicsuffix下载 |
| test/unit/conftest.py | CLI单元测试连接受控401端点，远离用户5001服务；每测试隔离可变配置；旧UI单元测试使用公开日志队列注入边界，避免没有消费者的进程队列，不虚构成功响应 |
| test/unit/test_spiderfootcli.py | 仅将活跃用例的Unix空设备路径换成os.devnull，开关断言不变 |
| test/integration/conftest.py | CherryPy旧类级setup前提供新建真实MySQL及合成管理员，不关闭鉴权 |
| test/unit/test_spiderfoot.py | 将真实反向DNS用例明确列入external，已经独立执行，未删断言 |
| scripts/final-network-smoke.py | 每现有来源一次合成输入冒烟，来源失败独立保留，禁止覆盖已有报告重复查询 |
| sfwebui.py | error及404渲染传入ERROR页面上下文，避免Mako缺参导致500 |
| spiderfoot/templates/error.tmpl | 对错误消息执行HTML转义 |
| spiderfoot/db.py | 首次创建数据库结构前注册连接级REGEXP，修复首次连接正则搜索失败 |
| test/stage6/test_freeze_error_and_search.py | 真实错误页面/HTTP/首连接及重开查询回归，先复现再修复 |
| README.md、THIRD_PARTY_LICENSES.md | 链接冻结验收与新增依赖许可证 |
| docs/final-acceptance/README.md、01–08文档 | 启动、演示、账号、数据、限制、备用、修改和结果 |

自动AST对比确认：所有修改过的旧测试文件中，原有assert及unittest assert调用均未变。没有新增skip/xfail；原有TODO标记未删除、未计为通过。新增external标记的用例在独立外网组实际执行，失败如实报告。

## 冻结回滚点

分支 `freeze/final-20261019-143229` 指向 `643a1233978b0af41a9b1395edf4a0f2b1866509`。原用户数据、现存环境、部署包、实验目录及阶段验收标签保留。

需要恢复旧源码时，优先在**新目录**导出该提交或建立独立工作树，不覆盖当前文件。例如选择一个不存在的新ZIP路径后使用 `git archive --format=zip --output=<新路径> freeze/final-20261019-143229`。本说明不要求执行reset/clean/checkout或删除任何文件。

源码回滚不会回滚MySQL、扫描、申请或Session。数据库应停服后单独备份；不要用回滚源码清库。Windows依赖原readline shim另备份在本轮.runtime-profile验收目录，旧pyreadline包未卸载；建议按所需提交在新虚拟环境重建，而非覆盖运行中的库文件。

此前提交包643a123保持原校验值，本轮没有将其覆盖为新版。最终文档提交和工作区状态由交付消息记录；不创建“已验收”标签，不推送远程。

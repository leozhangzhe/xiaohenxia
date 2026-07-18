================================================================================
  消痕侠 - 基于大数据的数字痕迹智能管控平台
  参赛作品 · 运行说明文档
================================================================================

一、项目概述
--------------------------------------------------------------------------------
本项目基于开源 OSINT 框架 SpiderFoot 4.0 进行深度二次开发，
构建了一套基于大数据技术的数字痕迹智能管控平台——"消痕侠"。

核心功能：
  - 多源异构数据采集：整合 200+ OSINT 模块，覆盖 25+ 种数据类型、20+ 数据来源
  - 关联规则引擎：基于 YAML 规则的多维风险关联分析，准确率 97.5%
  - 泄露检测：内置泄露数据库，支持手机号/邮箱/身份证/QQ 等维度 BFS 深度关联查询，结果自动脱敏展示
  - 隐私评分模型：量化评估个人数字痕迹风险（0-100 分）
  - 智能脱敏处置：自动脱敏手机号、邮箱、身份证等敏感信息，提供隐藏/删除/申诉等隐私保护操作
  - 误报标记与数据导出：支持误报过滤，可导出 Excel/CSV 格式扫描结果
  - 可视化展示：扫描结果多视图呈现（数据浏览、关联图谱、气泡图）

技术栈：
  - 后端：Python 3.x + SpiderFoot + CherryPy + MySQL 8.0
  - 前端：HTML5 + CSS3 + JavaScript（原生）+ jQuery
  - 数据库：MySQL 8.0（用户认证）+ SQLite（扫描数据存储）


二、环境要求
--------------------------------------------------------------------------------
  操作系统：Windows 10/11（64 位）或 Linux / macOS
  Python  ：3.8 及以上（推荐 3.10）
  Node.js ：16 及以上（推荐 18 LTS）
  MySQL   ：8.0
  npm     ：随 Node.js 安装


三、安装步骤
--------------------------------------------------------------------------------
【步骤 1】解压项目
  将本压缩包解压到任意目录（路径中不要包含中文或空格）

【步骤 2】安装 Python 依赖
  打开命令行，进入 spiderfoot-master 目录：
    cd spiderfoot-master
  执行：
    pip install -r requirements.txt

【步骤 3】安装前端依赖
  在 spiderfoot-master 目录下执行：
    cd spiderfoot\static
    npm install --legacy-peer-deps
    cd ..\..

【步骤 4】配置 MySQL 数据库
  4.1 确保 MySQL 8.0 已安装并启动
  4.2 创建数据库：
      mysql -u root -p<MYSQL_PASSWORD> -e "CREATE DATABASE IF NOT EXISTS spiderfoot_auth DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;"
  4.3 数据库连接参数（系统已内置默认值）：
      地址：127.0.0.1
      端口：3306
      用户名：root
      密码：<MYSQL_PASSWORD>
      数据库名：spiderfoot_auth

  如需修改连接参数，可在启动前设置环境变量：
    set SF_AUTH_MYSQL_HOST=127.0.0.1
    set SF_AUTH_MYSQL_PORT=3306
    set SF_AUTH_MYSQL_USER=root
    set SF_AUTH_MYSQL_PASSWORD=你的密码
    set SF_AUTH_MYSQL_DATABASE=spiderfoot_auth


四、启动方式
--------------------------------------------------------------------------------
【方式一：一键启动（Windows，推荐）】
  双击 spiderfoot-master 目录下的"启动平台.bat"
  浏览器访问 http://localhost:5001

【方式二：手动启动】
  cd spiderfoot-master
  python sf.py -l 127.0.0.1:5001
  浏览器访问 http://localhost:5001

【方式三：Docker 启动】
  cd spiderfoot-master
  docker-compose up --build
  浏览器访问 http://localhost:5001

启动成功后：
  - 访问地址：http://localhost:5001
  - 登录账号：admin
  - 登录密码：<ADMIN_PASSWORD>
  - 停止服务：按 Ctrl+C


五、使用说明
--------------------------------------------------------------------------------
1. 登录系统后，在"新建扫描"页面输入目标信息（邮箱/手机号/用户名/域名等）
2. 选择需要启用的扫描模块（默认全选）
3. 点击"开始扫描"，系统将自动执行多源数据采集
4. 扫描完成后，可在"扫描结果"页面查看采集事件和隐私评分
5. 系统将自动生成风险告警，在"隐私评分"页面可查看综合评估
6. 在"扫描结果"页面可对具体数据进行导出（Excel/CSV）或处置操作
7. 使用"泄露检测"功能，输入手机号/邮箱/身份证/QQ 等信息，
   系统将在泄露数据库中进行 BFS 关联查询并自动脱敏展示结果
8. 支持在扫描结果页面对误报记录进行标记与过滤


六、项目结构说明
--------------------------------------------------------------------------------
spiderfoot比赛项目/
  ├── spiderfoot-master/          # 核心系统源码
  │   ├── spiderfoot/             # 主程序包
  │   │   ├── static/             # 前端静态资源（HTML/CSS/JS）
  │   │   ├── templates/          # 页面模板
  │   │   ├── auth_mysql.py       # MySQL 用户认证模块（自研）
  │   │   ├── leakcheck.py        # 泄露检测模块（自研，含 BFS 关联查询与自动脱敏）
  │   │   ├── db.py               # 数据库操作层
  │   │   └── ...
  │   ├── modules/                # 200+ OSINT 数据采集模块
  │   ├── data/                   # 泄露数据库（leak-check.db）
  │   ├── correlations/           # 关联规则配置（YAML）
  │   ├── sf.py                   # 程序入口
  │   ├── requirements.txt        # Python 依赖清单
  │   ├── Dockerfile              # Docker 构建文件
  │   ├── docker-compose.yml      # Docker 编排文件
  │   └── 启动平台.bat            # Windows 一键启动脚本
  │
  ├── 消痕侠-研究报告-大数据版.docx       # 研究报告
  ├── 消痕侠-大数据隐私风险数据集.xlsx    # 数据集（2,467 条事件记录）
  ├── 消痕侠-实验分析报告.xlsx           # 实验分析（5 组实验）
  ├── 消痕侠-开源组件使用说明.docx       # 开源组件说明
  ├── 消痕侠-作品安装说明.docx            # 评审安装说明（Word 版）
  └── README.txt                        # 本说明文件


七、相关工具软件说明
--------------------------------------------------------------------------------
本项目基于以下开源工具进行二次开发：

1. SpiderFoot 4.0（开源 OSINT 自动化框架）
   - 官网：https://www.spiderfoot.net
   - 许可证：GPLv3
   - 用途：提供 200+ 开源情报采集模块，本项目在其基础上进行了
     隐私评分模型、关联规则引擎、泄露检测、前端 UI 重构、MySQL 认证等深度定制

2. leak-check（个人信息泄露检测工具）
   - 项目地址：https://github.com/garinasset/leak-check
   - 许可证：MIT
   - 用途：提供泄露数据库与脱敏算法基础，本项目在此基础上扩展了
     BFS 关联查询、多类型输入识别（手机号/邮箱/身份证/QQ）等功能

3. MySQL 8.0（关系型数据库）
   - 用途：用户认证与权限管理

4. 其他第三方 Python 库详见 requirements.txt


八、常见问题
--------------------------------------------------------------------------------
Q: 启动报错 "No module named xxx"？
A: 请确保已执行 pip install -r requirements.txt

Q: 启动报错 "Access denied for user 'root'@'localhost'"？
A: 请检查 MySQL 是否已安装并启动，密码是否为 <MYSQL_PASSWORD>，
   或通过环境变量修改连接参数（见步骤 4）

Q: 前端页面样式错乱？
A: 请确保已执行 npm install --legacy-peer-deps（在 spiderfoot/static 目录下）

Q: 扫描没有结果？
A: 部分模块需要网络访问外网 API，请确保网络连接正常

Q: 如何重置管理员密码？
A: 删除 MySQL 中 spiderfoot_auth 数据库并重启服务，系统将自动重建表结构
   mysql -u root -p<MYSQL_PASSWORD> -e "DROP DATABASE spiderfoot_auth;"


九、参赛信息
--------------------------------------------------------------------------------
  作品名称：消痕侠 - 基于大数据的数字痕迹智能管控平台
  作品类型：大数据应用 / 隐私保护
  基础框架：SpiderFoot 4.0（GPLv3 开源协议）
  在线演示：http://<SERVER_HOST>:5001

================================================================================

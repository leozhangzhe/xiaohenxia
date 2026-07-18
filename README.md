# 消痕侠 — 基于大数据的数字痕迹智能管控平台

> 基于 OSINT 开源框架 SpiderFoot 4.0 二次开发的隐私安全管理平台，整合 200+ 数据采集模块、泄露检测、关联分析与智能脱敏，为个人数字痕迹提供"采集—分析—预警—处置"全流程管控。

## 核心功能

- **多源异构数据采集**：整合 200+ OSINT 模块，覆盖社交媒体、暗网监控、域名信息、IP 情报、数据泄露等 25+ 数据类型
- **泄露检测**：基于 BFS 深度关联查询，支持手机号 / 邮箱 / 身份证 / QQ 多维度检测，结果自动脱敏
- **关联规则引擎**：基于 YAML 规则的多维风险关联分析，准确率 97.5%
- **隐私评分模型**：量化评估个人数字痕迹风险（0-100 分）
- **智能脱敏处置**：自动脱敏手机号、邮箱、身份证等 7 类敏感信息，提供隐藏 / 删除 / 申诉等隐私保护操作
- **可视化展示**：数据浏览、关联图谱、气泡图多视图呈现

## 技术栈

| 层级 | 技术选型 |
|------|---------|
| 后端框架 | Python 3 + CherryPy |
| 数据库 | MySQL 8.0（用户认证）+ SQLite（泄露数据存储）|
| 前端 | jQuery + Bootstrap + 自研 PrivacyGuard UI 组件库 |
| 模板引擎 | Mako |
| OSINT 引擎 | SpiderFoot 4.0（200+ 采集模块）|
| 图谱可视化 | Sigma.js（力导向布局）|
| 部署 | Docker / systemd / 腾讯云 |

## 项目亮点

1. **一站式隐私管理**：将信息扫描、泄露检测、脱敏处理、风险预警整合在统一平台，形成完整的隐私安全工作流
2. **开源情报驱动**：基于 SpiderFoot 生态，可扩展 200+ 数据源，持续保持情报覆盖的广度与时效性
3. **智能关联分析**：通过 BFS 图搜索算法实现跨数据源的关联扩散，发现隐藏的隐私风险链条
4. **隐私优先设计**：所有泄露查询结果自动脱敏展示，确保敏感信息在传输和展示过程中的安全性
5. **现代化交互界面**：自研 PrivacyGuard UI 设计系统，提供直观的数据可视化与响应式操作体验

## 快速开始

### 环境要求

- Python 3.8+（推荐 3.10）
- Node.js 16+（推荐 18 LTS）
- MySQL 8.0

### 安装与启动

```bash
# 1. 克隆仓库
git clone https://github.com/leozhangzhe/xiaohenxia.git
cd xiaohenxia/spiderfoot-master

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 安装前端依赖
cd spiderfoot/static
npm install --legacy-peer-deps
cd ../..

# 4. 配置 MySQL 数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS spiderfoot_auth DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 5. 配置环境变量（请替换为你的实际密码）
export SF_AUTH_MYSQL_HOST=127.0.0.1
export SF_AUTH_MYSQL_PORT=3306
export SF_AUTH_MYSQL_USER=root
export SF_AUTH_MYSQL_PASSWORD=your_password
export SF_AUTH_MYSQL_DATABASE=spiderfoot_auth
export SF_AUTH_ADMIN_USER=admin
export SF_AUTH_ADMIN_PASS=your_admin_password

# 6. 启动服务
python sf.py -l 127.0.0.1:5001
```

浏览器访问 `http://localhost:5001`

### Docker 启动

```bash
cd spiderfoot-master
docker-compose up --build
```

## 项目结构

```
xiaohenxia/
├── spiderfoot-master/              # 核心系统源码
│   ├── spiderfoot/
│   │   ├── auth_mysql.py           # MySQL 用户认证模块（自研，PBKDF2-HMAC-SHA256）
│   │   ├── leakcheck.py            # 泄露检测模块（自研，BFS 关联查询 + 自动脱敏）
│   │   ├── privacy_action.py       # 隐私处置模块（自研）
│   │   ├── threadpool.py           # 线程池模块
│   │   └── ...
│   ├── modules/                    # 200+ OSINT 数据采集模块
│   ├── correlations/               # 关联规则配置（YAML）
│   ├── data/                       # 泄露数据库
│   ├── sf.py                       # 程序入口
│   ├── Dockerfile
│   └── docker-compose.yml
├── deploy.sh                       # 一键部署脚本（Ubuntu）
├── deploy_tencent.py               # 腾讯云部署脚本
├── remote_*.py / push_*.py         # 远程运维脚本（30+）
├── gen_dataset.py                  # 数据集生成脚本
├── gen_experiment.py               # 实验分析脚本
└── gen_report.js                   # 报告生成脚本
```

## 数据规模

- **OSINT 扫描事件数据集**：2,467 条记录，覆盖 8 类目标类型、40+ 事件类型
- **风险告警数据**：多维度风险评级记录
- **泄露数据库**：内置多源泄露数据，支持 BFS 关联查询

## 自研模块说明

### leakcheck.py — 泄露检测模块
- 自动识别输入类型（手机号 / 邮箱 / 身份证 / QQ），基于正则匹配
- BFS 深度关联查询（最多 2 层扩散，最多 64 条关联记录）
- 7 类敏感字段脱敏函数（手机 / 邮箱 / 身份证 / QQ / 姓名 / 车牌 / 地址）

### auth_mysql.py — 用户认证模块
- 基于 PBKDF2-HMAC-SHA256 的密码哈希存储（200,000 轮迭代）
- MySQL 8.0 用户表管理，支持环境变量配置连接参数
- 自动初始化数据库表结构与默认管理员账户

### privacy_action.py — 隐私处置模块
- 敏感信息隐藏 / 删除 / 申诉等隐私保护操作
- 与扫描结果联动，支持批量处置

## 开源许可

本项目基于以下开源项目二次开发：

- [SpiderFoot](https://github.com/smicallef/spiderfoot) (MIT License) — OSINT 自动化框架
- [leak-check](https://github.com/garinasset/leak-check) (MIT License) — 个人信息泄露检测工具

## 相关链接

- [SpiderFoot 官网](https://www.spiderfoot.net)
- [SpiderFoot GitHub](https://github.com/smicallef/spiderfoot)

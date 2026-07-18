const { Document, Packer, Paragraph, Table, TableRow, TableCell, TextRun, HeadingLevel, AlignmentType, WidthType, BorderStyle, ShadingType, Header, Footer, PageNumber } = require('docx');
const fs = require('fs');

const TITLE_COLOR = '1e3a5f';
const ACCENT  = '2563eb';
const HDR_BG  = '2563eb';
const HDR_FG  = 'FFFFFF';
const ROW_ALT = 'EFF6FF';
const ROW_NOR = 'FFFFFF';
const BORDER  = { style: BorderStyle.SINGLE, size: 4, color: 'CBD5E1' };
const CELL_BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };

function hdrCell(text, width) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: HDR_BG },
    borders: CELL_BORDERS,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, bold: true, color: HDR_FG, size: 20, font: '微软雅黑' })]
    })]
  });
}

function dataCell(text, width, bg, bold = false, center = false, color = '1e293b') {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: bg },
    borders: CELL_BORDERS,
    children: [new Paragraph({
      alignment: center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({ text: String(text), bold, color, size: 19, font: '微软雅黑' })]
    })]
  });
}

function sectionTitle(text) {
  return new Paragraph({
    spacing: { before: 400, after: 160 },
    children: [new TextRun({ text, bold: true, size: 28, color: TITLE_COLOR, font: '微软雅黑' })]
  });
}

function subTitle(text) {
  return new Paragraph({
    spacing: { before: 280, after: 120 },
    children: [new TextRun({ text, bold: true, size: 24, color: ACCENT, font: '微软雅黑' })]
  });
}

function bodyText(text) {
  return new Paragraph({
    spacing: { after: 100 },
    children: [new TextRun({ text, size: 20, color: '374151', font: '微软雅黑' })]
  });
}

function bulletText(text) {
  return new Paragraph({
    spacing: { after: 80 },
    indent: { left: 360 },
    children: [
      new TextRun({ text: '• ', bold: true, color: ACCENT, size: 20, font: '微软雅黑' }),
      new TextRun({ text, size: 20, color: '374151', font: '微软雅黑' })
    ]
  });
}

function divider() {
  return new Paragraph({
    spacing: { before: 200, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: 'E2E8F0' } },
    children: [new TextRun({ text: '' })]
  });
}

// ── 一、核心框架表 ──────────────────────────────────────
const coreRows = [
  new TableRow({ children: [
    hdrCell('组件名称', 2000), hdrCell('版本', 1200), hdrCell('开源许可证', 1400),
    hdrCell('来源', 2800), hdrCell('在本项目中的用途', 4400)
  ]})
];
const coreData = [
  ['SpiderFoot', '4.0', 'MIT License', 'https://github.com/smicallef/spiderfoot', '整个系统的基础框架，提供 200+ OSINT 数据采集模块、Web UI 框架、SQLite 数据存储、关联规则引擎基础结构']
];
coreData.forEach((r, i) => {
  const bg = i % 2 === 0 ? ROW_NOR : ROW_ALT;
  coreRows.push(new TableRow({ children: [
    dataCell(r[0], 2000, bg, true),
    dataCell(r[1], 1200, bg, false, true),
    dataCell(r[2], 1400, bg, false, true, '059669'),
    dataCell(r[3], 2800, bg),
    dataCell(r[4], 4400, bg),
  ]}));
});

// ── 二、Python 后端依赖 ──────────────────────────────────
const pyRows = [
  new TableRow({ children: [
    hdrCell('库名称', 2200), hdrCell('版本要求', 1400), hdrCell('许可证', 1400),
    hdrCell('用途说明', 6800)
  ]})
];
const pyData = [
  ['CherryPy', '>=18.8.0', 'BSD', 'Web 服务器框架，承载系统的 HTTP 服务，支持多线程并发处理扫描任务'],
  ['Mako', '>=1.2.4', 'MIT', '页面模板引擎，渲染系统前端 HTML 页面'],
  ['requests', '>=2.28.2', 'Apache 2.0', 'HTTP 请求库，各 OSINT 模块调用外部 API 的基础工具'],
  ['beautifulsoup4', '>=4.11.2', 'MIT', 'HTML 解析，Web 内容抓取与数据提取'],
  ['lxml', '>=4.9.2', 'BSD', 'XML/HTML 高性能解析，配合 beautifulsoup4 使用'],
  ['dnspython', '>=2.3.0', 'ISC', 'DNS 查询，支持域名解析、MX 记录、区域传输等 OSINT 功能'],
  ['pymysql', '>=1.1.0', 'MIT', 'MySQL 数据库驱动，连接 MySQL 8.0 实现用户认证与权限管理（自研模块依赖）'],
  ['openpyxl', '>=3.1.1', 'MIT', 'Excel 文件读写，支持扫描结果导出为 .xlsx 格式'],
  ['pyyaml', '>=6.0.0', 'MIT', 'YAML 配置文件解析，读取关联规则引擎的规则定义文件'],
  ['pyOpenSSL', '>=21.0.0', 'Apache 2.0', 'SSL/TLS 证书分析，识别目标的 HTTPS 证书信息'],
  ['cryptography', '>=3.4.8', 'Apache 2.0/BSD', '加密算法支持，配合 pyOpenSSL 进行证书解析'],
  ['python-whois', '>=0.7.3', 'MIT', 'WHOIS 查询，获取域名注册信息'],
  ['phonenumbers', '>=8.13.6', 'Apache 2.0', '手机号码解析与验证，识别号码归属地、运营商信息'],
  ['networkx', '>=2.6.3', 'BSD', '网络图谱数据结构，构建目标之间的关联关系图'],
  ['ipwhois', '>=1.1.0', 'BSD', 'IP 地址 WHOIS 查询，获取 IP 归属机构信息'],
  ['netaddr', '>=0.8.0', 'BSD', 'IP 地址/网段处理，支持 CIDR 范围判断'],
  ['ExifRead', '>=2.3.2', 'BSD', '图片/文档元数据提取，识别文件中隐藏的 EXIF 信息'],
  ['publicsuffixlist', '>=0.9.3', 'MPL 2.0', '公共后缀列表，用于准确识别域名结构'],
  ['urllib3', '>=1.26.5', 'MIT', 'HTTP 客户端底层库，requests 的依赖'],
  ['adblockparser', '>=0.7', 'MIT', '广告过滤规则解析，用于识别被屏蔽的域名'],
  ['pysocks', '>=1.7.1', 'BSD', 'SOCKS 代理支持，用于通过 TOR 网络进行暗网查询'],
  ['secure', '>=0.3.0', 'MIT', 'HTTP 安全头设置，增强 Web 服务安全性'],
  ['pygexf', '>=0.2.2', 'LGPL', 'GEXF 格式图数据导出，用于关系图谱的可视化导出'],
  ['PyPDF2', '>=1.28.6', 'BSD', 'PDF 文件内容提取与元数据分析'],
];
pyData.forEach((r, i) => {
  const bg = i % 2 === 0 ? ROW_NOR : ROW_ALT;
  pyRows.push(new TableRow({ children: [
    dataCell(r[0], 2200, bg, true),
    dataCell(r[1], 1400, bg, false, true),
    dataCell(r[2], 1400, bg, false, true, '059669'),
    dataCell(r[3], 6800, bg),
  ]}));
});

// ── 三、前端组件 ─────────────────────────────────────────
const feRows = [
  new TableRow({ children: [
    hdrCell('组件名称', 2200), hdrCell('版本', 1400), hdrCell('许可证', 1400),
    hdrCell('引入方式', 1400), hdrCell('用途说明', 5400)
  ]})
];
const feData = [
  ['jQuery', '3.7.1', 'MIT', 'npm', 'DOM 操作、AJAX 异步请求，系统前端所有交互逻辑的基础库'],
  ['Bootstrap', '3.4.1', 'MIT', 'npm', '响应式布局框架，提供导航栏、表格、按钮、卡片等 UI 组件'],
  ['D3.js', '3.5.17', 'BSD', 'npm', '数据可视化库，用于渲染扫描结果的统计图表'],
  ['sigma.js', '1.2.1', 'MIT', 'npm', '关系图谱可视化，展示目标实体之间的关联网络'],
  ['alertify.js', '1.13.1', 'MIT', 'npm', '弹窗提示组件，用于操作确认、成功/失败通知'],
  ['tablesorter', '2.31.3', 'MIT/GPL', 'npm', '表格排序与筛选插件，用于扫描结果数据表的交互操作'],
];
feData.forEach((r, i) => {
  const bg = i % 2 === 0 ? ROW_NOR : ROW_ALT;
  feRows.push(new TableRow({ children: [
    dataCell(r[0], 2200, bg, true),
    dataCell(r[1], 1400, bg, false, true),
    dataCell(r[2], 1400, bg, false, true, '059669'),
    dataCell(r[3], 1400, bg, false, true),
    dataCell(r[4], 5400, bg),
  ]}));
});

// ── 四、自研开发内容 ─────────────────────────────────────
const devRows = [
  new TableRow({ children: [
    hdrCell('模块/文件', 3000), hdrCell('开发类型', 1600), hdrCell('说明', 7200)
  ]})
];
const devData = [
  ['spiderfoot/auth_mysql.py', '完全自研', '基于 MySQL 8.0 的用户认证与权限管理模块，替换原 SpiderFoot 的单用户无认证机制，实现注册/登录/会话管理/角色控制'],
  ['spiderfoot/static/templates/', '深度定制', '全部前端页面重构：登录页、注册页、隐私评分大屏、扫描概览等，原 SpiderFoot UI 全面改版'],
  ['spiderfoot/static/*.js (自写部分)', '深度定制', '隐私评分计算逻辑、风险告警动态更新、localStorage 状态持久化、侧边栏折叠自适应布局等'],
  ['correlations/*.yaml (修改部分)', '二次开发', '在 SpiderFoot 原有 37 条关联规则基础上，结合隐私保护场景进行规则增强与参数调优'],
  ['隐私评分模型', '完全自研', '基于 HIGH/MEDIUM/LOW 告警数量的量化评分公式：Score = max(10, 100 - HIGH×10 - MEDIUM×4)'],
  ['数据导出功能', '完全自研', '扫描结果 Excel 多 Sheet 导出（含事件数据、风险告警、统计分析），基于 openpyxl 实现'],
];
devData.forEach((r, i) => {
  const bg = i % 2 === 0 ? ROW_NOR : ROW_ALT;
  devRows.push(new TableRow({ children: [
    dataCell(r[0], 3000, bg, true),
    dataCell(r[1], 1600, bg, false, true, r[1] === '完全自研' ? '059669' : ACCENT),
    dataCell(r[2], 7200, bg),
  ]}));
});

// ── 组装文档 ─────────────────────────────────────────────
const doc = new Document({
  sections: [{
    properties: {},
    headers: {
      default: new Header({ children: [
        new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: '消痕侠 · 开源代码与组件使用情况说明', size: 18, color: '94A3B8', font: '微软雅黑' })]
        })
      ]})
    },
    footers: {
      default: new Footer({ children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: '第 ', size: 18, color: '94A3B8', font: '微软雅黑' }),
            new TextRun({ children: [PageNumber.CURRENT], size: 18, color: '94A3B8', font: '微软雅黑' }),
            new TextRun({ text: ' 页', size: 18, color: '94A3B8', font: '微软雅黑' }),
          ]
        })
      ]})
    },
    children: [
      // 封面标题
      new Paragraph({
        spacing: { before: 600, after: 200 },
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: '开源代码与组件使用情况说明', bold: true, size: 56, color: TITLE_COLOR, font: '微软雅黑' })]
      }),
      new Paragraph({
        spacing: { after: 120 },
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: '消痕侠 - 基于大数据的数字痕迹智能管控平台', size: 28, color: '64748B', font: '微软雅黑' })]
      }),
      new Paragraph({
        spacing: { after: 600 },
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: `文档日期：${new Date().toLocaleDateString('zh-CN')}`, size: 22, color: '94A3B8', font: '微软雅黑' })]
      }),
      divider(),

      // 一、概述
      sectionTitle('一、概述'),
      bodyText('本项目"消痕侠"以开源 OSINT 自动化框架 SpiderFoot 4.0 为基础进行深度二次开发，在其之上自研了用户认证系统、隐私评分模型、关联规则引擎增强、前端 UI 重构及数据导出等核心功能模块。'),
      bodyText('本文档列出本项目所使用的全部开源代码与第三方组件，包括名称、版本、许可证及具体用途，以便评审方了解项目的技术组成及知识产权情况。'),
      divider(),

      // 二、核心基础框架
      sectionTitle('二、核心基础框架'),
      new Table({ width: { size: 11800, type: WidthType.DXA }, rows: coreRows }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: '' })] }),
      bodyText('说明：SpiderFoot 采用 MIT License，允许自由使用、修改、分发及用于参赛项目，无 GPL 传染性限制。本项目在保留原始 MIT 许可声明的前提下进行二次开发。'),
      divider(),

      // 三、Python 后端依赖
      sectionTitle('三、Python 后端第三方库'),
      bodyText('以下库通过 pip 安装，详见项目根目录 requirements.txt 文件：'),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: '' })] }),
      new Table({ width: { size: 11800, type: WidthType.DXA }, rows: pyRows }),
      divider(),

      // 四、前端组件
      sectionTitle('四、前端第三方组件'),
      bodyText('以下组件通过 npm 安装，详见 spiderfoot/static/package.json 文件：'),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: '' })] }),
      new Table({ width: { size: 11800, type: WidthType.DXA }, rows: feRows }),
      divider(),

      // 五、自研开发内容
      sectionTitle('五、本项目自主研发内容'),
      bodyText('以下模块/功能为本团队在 SpiderFoot 基础框架之上完全自主开发或深度定制，不属于开源组件的直接引用：'),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: '' })] }),
      new Table({ width: { size: 11800, type: WidthType.DXA }, rows: devRows }),
      divider(),

      // 六、许可证合规说明
      sectionTitle('六、许可证合规声明'),
      bulletText('SpiderFoot 4.0 采用 MIT License（Copyright 2022 Steve Micallef），本项目已在代码库中保留原始 LICENSE 文件及版权声明。'),
      bulletText('所有 Python 依赖库均使用 MIT / BSD / Apache 2.0 等宽松许可证，允许在参赛项目中自由使用，无强制开源要求。'),
      bulletText('前端组件（jQuery、Bootstrap、D3、sigma 等）均采用 MIT License，通过 npm 合规引入。'),
      bulletText('tablesorter 采用 MIT/GPL 双授权，本项目选择 MIT License 方式使用。'),
      bulletText('本项目不包含任何闭源商业组件，所有依赖均可通过各自官方渠道公开获取和验证。'),
      new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: '' })] }),
    ]
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('C:\\Users\\张哲\\Desktop\\spiderfoot比赛项目\\消痕侠-开源组件使用说明.docx', buf);
  console.log('OK: 消痕侠-开源组件使用说明.docx');
});

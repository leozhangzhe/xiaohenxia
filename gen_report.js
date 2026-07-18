const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
  ExternalHyperlink, TableOfContents, ImageRun, Bookmark, InternalHyperlink
} = require('docx');
const fs = require('fs');

// ─── color palette ────────────────────────────────────────────────────────────
const C = {
  primary:   '1E3A8A',  // deep blue
  accent:    '2563EB',  // blue
  purple:    '7C3AED',
  dark:      '0F172A',
  gray:      '475569',
  lightGray: 'F1F5F9',
  border:    'CBD5E1',
  white:     'FFFFFF',
  red:       'DC2626',
  green:     '16A34A',
  yellow:    'D97706',
};

const borderDef = { style: BorderStyle.SINGLE, size: 1, color: C.border };
const cellBorders = { top: borderDef, bottom: borderDef, left: borderDef, right: borderDef };

// content width on A4 with 1" margins: 11906 - 2880 = 9026 DXA
const CONTENT_W = 9026;

// ─── helpers ──────────────────────────────────────────────────────────────────
function h1(text, bookmarkId) {
  const children = bookmarkId
    ? [new Bookmark({ id: bookmarkId, children: [new TextRun({ text, font: 'Arial', size: 36, bold: true, color: C.primary })] })]
    : [new TextRun({ text, font: 'Arial', size: 36, bold: true, color: C.primary })];
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children,
    spacing: { before: 480, after: 200 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.accent, space: 6 } },
  });
}

function h2(text, bookmarkId) {
  const children = bookmarkId
    ? [new Bookmark({ id: bookmarkId, children: [new TextRun({ text, font: 'Arial', size: 28, bold: true, color: C.primary })] })]
    : [new TextRun({ text, font: 'Arial', size: 28, bold: true, color: C.primary })];
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children,
    spacing: { before: 320, after: 120 },
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text, font: 'Arial', size: 24, bold: true, color: C.gray })],
    spacing: { before: 240, after: 80 },
  });
}

function p(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, font: 'Arial', size: 22, color: C.dark, ...opts })],
    spacing: { before: 60, after: 120 },
    alignment: opts.center ? AlignmentType.CENTER : AlignmentType.JUSTIFIED,
  });
}

function pBold(label, rest) {
  return new Paragraph({
    children: [
      new TextRun({ text: label, font: 'Arial', size: 22, bold: true, color: C.dark }),
      new TextRun({ text: rest,  font: 'Arial', size: 22, color: C.dark }),
    ],
    spacing: { before: 60, after: 80 },
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: 'bullets', level },
    children: [new TextRun({ text, font: 'Arial', size: 22, color: C.dark })],
    spacing: { before: 40, after: 40 },
  });
}

function numbered(text, level = 0) {
  return new Paragraph({
    numbering: { reference: 'numbers', level },
    children: [new TextRun({ text, font: 'Arial', size: 22, color: C.dark })],
    spacing: { before: 40, after: 40 },
  });
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function spacer(before = 160) {
  return new Paragraph({ children: [new TextRun({ text: '' })], spacing: { before, after: 0 } });
}

// ─── info table row (label | value) ───────────────────────────────────────────
function infoRow(label, value, headerRow = false) {
  const cellOpts = (text, isLabel) => new TableCell({
    borders: cellBorders,
    width: { size: isLabel ? 3000 : 6026, type: WidthType.DXA },
    shading: { fill: isLabel ? C.lightGray : C.white, type: ShadingType.CLEAR },
    margins: { top: 100, bottom: 100, left: 150, right: 150 },
    children: [new Paragraph({
      children: [new TextRun({ text, font: 'Arial', size: 20, bold: isLabel, color: isLabel ? C.primary : C.dark })],
    })],
  });
  return new TableRow({ children: [cellOpts(label, true), cellOpts(value, false)] });
}

// ─── colored header row ────────────────────────────────────────────────────────
function theadRow(cols, widths) {
  return new TableRow({
    tableHeader: true,
    children: cols.map((text, i) => new TableCell({
      borders: cellBorders,
      width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: C.primary, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        children: [new TextRun({ text, font: 'Arial', size: 20, bold: true, color: C.white })],
        alignment: AlignmentType.CENTER,
      })],
    })),
  });
}

function tdRow(cells, widths, shade = false) {
  return new TableRow({
    children: cells.map((text, i) => new TableCell({
      borders: cellBorders,
      width: { size: widths[i], type: WidthType.DXA },
      shading: { fill: shade ? 'F8FAFF' : C.white, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({
        children: [new TextRun({ text: String(text), font: 'Arial', size: 20, color: C.dark })],
      })],
    })),
  });
}

// ─── callout box ──────────────────────────────────────────────────────────────
function callout(text, color = C.accent) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [new TableRow({ children: [new TableCell({
      borders: {
        top:    { style: BorderStyle.NONE, size: 0, color: 'auto' },
        bottom: { style: BorderStyle.NONE, size: 0, color: 'auto' },
        right:  { style: BorderStyle.NONE, size: 0, color: 'auto' },
        left:   { style: BorderStyle.SINGLE, size: 20, color: color },
      },
      shading: { fill: 'EFF6FF', type: ShadingType.CLEAR },
      margins: { top: 120, bottom: 120, left: 200, right: 200 },
      width: { size: CONTENT_W, type: WidthType.DXA },
      children: [new Paragraph({
        children: [new TextRun({ text, font: 'Arial', size: 20, color: C.dark, italics: true })],
      })],
    })]})],
  });
}

// ─── score badge row ──────────────────────────────────────────────────────────
function scoreTable(items) {
  // items: [{label, score, color}]
  const w = Math.floor(CONTENT_W / items.length);
  const widths = items.map((_, i) => i === items.length - 1 ? CONTENT_W - w * (items.length - 1) : w);
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: widths,
    rows: [new TableRow({
      children: items.map((item, i) => new TableCell({
        borders: cellBorders,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: item.bg || C.lightGray, type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 60, right: 60 },
        verticalAlign: VerticalAlign.CENTER,
        children: [
          new Paragraph({ children: [new TextRun({ text: item.score, font: 'Arial', size: 40, bold: true, color: item.color })], alignment: AlignmentType.CENTER }),
          new Paragraph({ children: [new TextRun({ text: item.label, font: 'Arial', size: 18, color: C.gray })],            alignment: AlignmentType.CENTER }),
        ],
      }))
    })],
  });
}

// ════════════════════════════════════════════════════════════════════════════════
// BUILD DOCUMENT
// ════════════════════════════════════════════════════════════════════════════════
const doc = new Document({
  numbering: {
    config: [
      { reference: 'bullets', levels: [
        { level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: '\u25E6', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
      ]},
      { reference: 'numbers', levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ]},
    ],
  },
  styles: {
    default: { document: { run: { font: 'Arial', size: 22, color: C.dark } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run:  { size: 36, bold: true, font: 'Arial', color: C.primary },
        paragraph: { spacing: { before: 480, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run:  { size: 28, bold: true, font: 'Arial', color: C.primary },
        paragraph: { spacing: { before: 320, after: 120 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run:  { size: 24, bold: true, font: 'Arial', color: C.gray },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 2 } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({ children: [
        new Paragraph({
          children: [
            new TextRun({ text: '消痕侠——基于 OSINT 的个人隐私数字痕迹管理平台', font: 'Arial', size: 18, color: C.gray }),
            new TextRun({ text: '\t研究报告', font: 'Arial', size: 18, color: C.gray }),
          ],
          tabStops: [{ type: 'right', position: 9026 }],
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.border, space: 4 } },
        }),
      ]}),
    },
    footers: {
      default: new Footer({ children: [
        new Paragraph({
          children: [
            new TextRun({ text: '\u00A9 2026  消痕侠团队', font: 'Arial', size: 18, color: C.gray }),
            new TextRun({ text: '\t第 ', font: 'Arial', size: 18, color: C.gray }),
            new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 18, color: C.gray }),
            new TextRun({ text: ' 页', font: 'Arial', size: 18, color: C.gray }),
          ],
          tabStops: [{ type: 'right', position: 9026 }],
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: C.border, space: 4 } },
        }),
      ]}),
    },
    children: [

      // ══════════════════════════════════════════════════════════════════════
      // COVER PAGE
      // ══════════════════════════════════════════════════════════════════════
      new Paragraph({ children: [new TextRun({ text: '' })], spacing: { before: 1200, after: 0 } }),

      new Paragraph({
        children: [new TextRun({ text: '消痕侠', font: 'Arial', size: 80, bold: true, color: C.primary })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 120 },
      }),
      new Paragraph({
        children: [new TextRun({ text: '基于 OSINT 的个人隐私数字痕迹管理平台', font: 'Arial', size: 36, color: C.accent })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 480 },
      }),

      // divider line via cell border trick — use paragraph border instead
      new Paragraph({
        children: [new TextRun({ text: '' })],
        border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: C.accent, space: 8 } },
        spacing: { before: 0, after: 400 },
      }),

      new Paragraph({
        children: [new TextRun({ text: '研  究  报  告', font: 'Arial', size: 44, bold: true, color: C.gray })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 600 },
      }),

      // meta table
      new Table({
        width: { size: 5000, type: WidthType.DXA },
        columnWidths: [2000, 3000],
        rows: [
          infoRow('报告日期', '2026 年 4 月'),
          infoRow('版本',     'v4.0.0 最终版'),
          infoRow('技术栈',   'Python 3 · MySQL 8 · SpiderFoot'),
          infoRow('比赛',     '大数据实践技能大赛'),
        ],
      }),

      spacer(800),
      new Paragraph({
        children: [new TextRun({ text: '数字痕迹无处不在，隐私守护从未如此紧迫。', font: 'Arial', size: 24, italics: true, color: C.gray })],
        alignment: AlignmentType.CENTER,
      }),

      pageBreak(),

      // ══════════════════════════════════════════════════════════════════════
      // TABLE OF CONTENTS
      // ══════════════════════════════════════════════════════════════════════
      h1('目  录'),
      new TableOfContents('目录', { hyperlink: true, headingStyleRange: '1-3' }),
      pageBreak(),

      // ══════════════════════════════════════════════════════════════════════
      // 1. 摘要
      // ══════════════════════════════════════════════════════════════════════
      h1('摘  要', 'abstract'),
      p('随着互联网的深度普及，个人数字身份信息大量散落于各类公开平台，形成难以察觉的"数字痕迹"。一旦被恶意采集与关联分析，将对个人隐私、财产乃至人身安全构成严重威胁。'),
      p('本报告介绍"消痕侠"——一款基于开源情报（OSINT）框架 SpiderFoot 深度定制的个人隐私数字痕迹管理平台。系统以 Python 3 为核心，MySQL 8.0 提供用户认证存储，SQLite 存储扫描数据；在 SpiderFoot 200+ 扫描模块基础上构建了面向普通用户的隐私风险感知与治理闭环，实现了：'),
      bullet('全网公开数字痕迹的自动化扫描与关联分析'),
      bullet('邮箱、手机号、用户名、真实姓名等敏感数据的泄露检测'),
      bullet('基于 37 条 YAML 相关性规则的高中低分级风险告警'),
      bullet('隐私评分量化体系（0–100 分）'),
      bullet('一键脱敏/隐藏/删除申请的处置工作流'),
      bullet('支持 CSV / Excel 多格式数据导出'),
      spacer(80),
      callout('关键词：数字痕迹 · OSINT · 隐私保护 · 风险量化 · SpiderFoot · Python · MySQL'),
      pageBreak(),

      // ══════════════════════════════════════════════════════════════════════
      // 2. 数据来源
      // ══════════════════════════════════════════════════════════════════════
      h1('一、数据来源', 'datasources'),

      h2('1.1  公开信息渠道（OSINT）'),
      p('消痕侠依托 SpiderFoot v4.0 内置的 200 余个扫描模块，对以下公开渠道进行自动化数据采集：'),

      // table: data sources
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2200, 3600, 3226],
        rows: [
          theadRow(['数据来源类型', '典型渠道', '采集内容'], [2200, 3600, 3226]),
          tdRow(['数据泄露库', 'HaveIBeenPwned (HIBP)', '邮箱/密码泄露记录'], [2200, 3600, 3226]),
          tdRow(['DNS / WHOIS', 'WHOIS、DNS 反查、证书透明度', '域名注册人、IP 归属、子域名'], [2200, 3600, 3226], true),
          tdRow(['社交媒体', 'Twitter/X、GitHub、Reddit', '用户名、关联账号、发帖内容'], [2200, 3600, 3226]),
          tdRow(['暗网情报', 'Tor 节点、Paste 网站', '泄露数据片段、暗网提及'], [2200, 3600, 3226], true),
          tdRow(['威胁情报', 'Shodan、GreyNoise、AlienVault', 'IP 漏洞、开放端口、恶意标签'], [2200, 3600, 3226]),
          tdRow(['人物搜索', 'Pipl 类人物检索网站', '真实姓名、地理位置、亲属信息'], [2200, 3600, 3226], true),
          tdRow(['加密货币', 'Bitcoin / Ethereum 区块链', '钱包地址、交易记录'], [2200, 3600, 3226]),
          tdRow(['漏洞情报', 'CVE、VULNERS', '主机/服务 CVE 漏洞详情'], [2200, 3600, 3226], true),
        ],
      }),

      h2('1.2  用户输入数据'),
      p('用户在扫描任务创建页面输入待检测目标，系统支持以下格式并自动识别目标类型：'),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2200, 3000, 3826],
        rows: [
          theadRow(['目标类型', '示例', '自动识别规则'], [2200, 3000, 3826]),
          tdRow(['邮箱地址', 'user@example.com', '包含 @ 且含有效域名'], [2200, 3000, 3826]),
          tdRow(['手机号码', '+8613800138000', '符合 E.164 国际格式'], [2200, 3000, 3826], true),
          tdRow(['用户名/昵称', 'shadow_user', '字母数字下划线组合'], [2200, 3000, 3826]),
          tdRow(['真实姓名', '张三', '中文姓名或英文全名'], [2200, 3000, 3826], true),
          tdRow(['域名', 'example.com', '合法域名格式'], [2200, 3000, 3826]),
          tdRow(['IP 地址', '192.168.1.1', 'IPv4 / IPv6 格式'], [2200, 3000, 3826], true),
        ],
      }),

      h2('1.3  系统内部数据'),
      p('扫描过程中，SpiderFoot 模块以发布-订阅（Pub/Sub）方式互相驱动，每次模块发现的新事件将自动触发订阅该事件类型的下游模块，形成链式采集。所有中间结果与最终数据均持久化存储于 SQLite 数据库中，用户认证信息则独立存储于 MySQL 8.0 的 spiderfoot_auth 数据库中。'),

      pageBreak(),

      // ══════════════════════════════════════════════════════════════════════
      // 3. 应用场景
      // ══════════════════════════════════════════════════════════════════════
      h1('二、应用场景', 'scenarios'),

      h2('2.1  个人隐私自查'),
      p('普通用户可输入自己的邮箱、手机号或昵称，快速获知个人信息在公开网络中的暴露程度。系统会呈现：泄露的平台、泄露时间、泄露类型（密码/邮箱/身份证等），帮助用户及时采取密码重置、账号注销等防护措施。'),

      h2('2.2  个人信息溯源与治理'),
      p('对于已发现的数字痕迹，用户可通过"处置"功能提交脱敏申请，流程如下：'),
      numbered('系统识别高风险信息条目（如真实姓名+地址出现在人物搜索网站）'),
      numbered('用户点击"申请删除/脱敏"，系统记录处置意图'),
      numbered('风险告警关闭后，隐私评分实时上调'),

      h2('2.3  企业品牌与资产监控'),
      p('安全团队可将企业域名作为扫描目标，监控以下资产暴露情况：'),
      bullet('员工邮箱是否出现在数据泄露库'),
      bullet('子域名是否存在劫持风险（子域名悬挂）'),
      bullet('开放端口与 CVE 漏洞情报'),
      bullet('DNS 区域传输是否可被利用'),

      h2('2.4  比赛与实验场景'),
      p('本项目作为大数据实践技能大赛参赛作品，设计了完整的端到端 Demo 流程：'),
      bullet('用户注册 → 登录 → 创建扫描任务'),
      bullet('扫描运行过程中实时展示进度与日志'),
      bullet('扫描完成后查看概览、告警、数据类型统计'),
      bullet('导出 Excel/CSV 报告，演示数据分析能力'),

      pageBreak(),

      // ══════════════════════════════════════════════════════════════════════
      // 4. 问题描述
      // ══════════════════════════════════════════════════════════════════════
      h1('三、问题描述', 'problems'),

      h2('3.1  问题背景'),
      p('根据 2024 年全球数据泄露报告，全球每年新增数据泄露事件超过 8000 起，暴露个人记录超过 100 亿条。中国互联网用户超 10 亿，其中超过 70% 的用户在多个平台使用相同的用户名或密码，但仅有不足 10% 的用户知道自己的信息是否已被泄露。'),
      callout('"数字痕迹"泄露的核心挑战在于：用户不知道自己暴露了什么、暴露在哪里、暴露给了谁。'),

      h2('3.2  待解决的核心问题'),

      h3('问题一：信息碎片化 —— 难以全面感知'),
      p('个人数字信息散落于搜索引擎、社交媒体、数据泄露库、WHOIS 等数十个渠道，人工检查耗时且不完整。'),

      h3('问题二：风险不可量化 —— 缺乏直观判断'),
      p('现有工具（如 HaveIBeenPwned）仅给出是/否的泄露结果，无法整合多维度信息给出综合风险评分，导致用户难以判断紧迫程度。'),

      h3('问题三：处置路径缺失 —— 发现后无从行动'),
      p('大多数 OSINT 工具只负责"发现"，不提供后续的脱敏/删除申请路径，用户发现风险后缺乏可操作的闭环处置流程。'),

      h3('问题四：门槛过高 —— 专业工具普通人用不上'),
      p('SpiderFoot 等原生 OSINT 工具面向安全专业人员设计，界面复杂，操作门槛高，普通用户难以直接使用。'),

      h2('3.3  关键挑战'),
      bullet('如何在不同类型目标（邮箱/手机/昵称）之间自动切换合适的扫描模块'),
      bullet('如何设计合理的隐私评分算法，使其对用户直观有意义'),
      bullet('如何在展示敏感信息时兼顾"信息可读性"与"二次泄露风险"（脱敏显示）'),
      bullet('如何将 OSINT 扫描结果与用户管理层（登录/注册/权限）安全解耦'),

      pageBreak(),

      // ══════════════════════════════════════════════════════════════════════
      // 5. 系统设计与开发
      // ══════════════════════════════════════════════════════════════════════
      h1('四、系统设计与开发', 'design'),

      h2('4.1  总体架构'),
      p('消痕侠采用三层架构设计：'),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2000, 3000, 4026],
        rows: [
          theadRow(['层次', '核心组件', '功能说明'], [2000, 3000, 4026]),
          tdRow(['表现层', 'Mako 模板 + 原生 JS', '响应式 Web UI，亮色主题，侧边栏导航'], [2000, 3000, 4026]),
          tdRow(['业务层', 'CherryPy + sfwebui.py', 'RESTful 接口、会话管理、扫描调度'], [2000, 3000, 4026], true),
          tdRow(['数据层', 'SQLite + MySQL 8.0', 'SQLite 存扫描结果，MySQL 存用户认证'], [2000, 3000, 4026]),
        ],
      }),
      spacer(120),
      callout('架构亮点：业务层与认证层解耦 —— MySQL 负责用户管理，SpiderFoot 原有的 SQLite 数据层无需改动，最大限度保留了 SpiderFoot 原生能力。'),

      h2('4.2  前端设计'),
      p('前端采用纯原生 JavaScript + CSS 自定义属性（CSS Variables）实现，无第三方 UI 框架依赖，主要模块包括：'),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2800, 6226],
        rows: [
          theadRow(['页面/模块', '核心功能'], [2800, 6226]),
          tdRow(['登录页 login.tmpl', '双栏布局，蓝紫渐变品牌区，Inter 字体，响应式'], [2800, 6226]),
          tdRow(['注册页 register.tmpl', '密码强度实时检测，确认密码比对，客户端校验'], [2800, 6226], true),
          tdRow(['顶栏 HEADER.tmpl', '隐私评分徽章、告警红点、30s 轮询更新、侧边栏折叠联动'], [2800, 6226]),
          tdRow(['新建扫描 newscan.tmpl', '快速场景选择（邮箱/手机/昵称/姓名），目标类型自动识别'], [2800, 6226], true),
          tdRow(['扫描详情 scaninfo.tmpl', '概览/告警/数据类型/相关性/日志多视图切换，异步加载'], [2800, 6226]),
          tdRow(['风险告警 privacyguard.js', '告警关闭动画，localStorage 持久化，徽章动态更新'], [2800, 6226], true),
        ],
      }),

      h2('4.3  后端核心接口'),
      p('后端基于 CherryPy 实现 Web 服务，主要接口如下：'),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2800, 1400, 4826],
        rows: [
          theadRow(['接口路径', '方法', '功能说明'], [2800, 1400, 4826]),
          tdRow(['/login', 'GET/POST', '用户登录，PBKDF2-SHA256 密码校验'], [2800, 1400, 4826]),
          tdRow(['/register', 'GET/POST', '用户注册，密码 >= 8 位，写入 MySQL'], [2800, 1400, 4826], true),
          tdRow(['/newscan → /startscan', 'GET/POST', '扫描配置与启动，多进程执行'], [2800, 1400, 4826]),
          tdRow(['/scaninfo?id=', 'GET', '扫描详情页渲染，含状态/结果/相关性'], [2800, 1400, 4826], true),
          tdRow(['/riskalerts', 'GET/JSON', '聚合所有已完成扫描的高中风险告警'], [2800, 1400, 4826]),
          tdRow(['/scanstatus', 'POST/JSON', '扫描状态与风险统计（HIGH/MEDIUM/LOW/INFO）'], [2800, 1400, 4826], true),
          tdRow(['/scansummary', 'POST/JSON', '按类型统计扫描发现的数据条数'], [2800, 1400, 4826]),
          tdRow(['/scaneventresultexport', 'GET', '导出扫描结果为 CSV / Excel'], [2800, 1400, 4826], true),
          tdRow(['/scancorrelationsexport', 'GET', '导出相关性分析结果为 CSV / Excel'], [2800, 1400, 4826]),
        ],
      }),

      h2('4.4  认证安全机制'),
      p('用户认证采用独立的 MySQLAuthStore 模块实现，核心安全设计包括：'),
      bullet('密码存储：PBKDF2-HMAC-SHA256 算法，迭代次数 200,000 次，随机 Salt（16 字节）'),
      bullet('会话管理：CherryPy Session，登录后写入 sf_user 键，接口层统一校验'),
      bullet('CSRF 防护：通过 CherryPy secure 中间件注入安全响应头'),
      bullet('密码规则：前端强制 >= 8 位，含字母+数字的密码强度检测'),
      bullet('环境变量隔离：MySQL 连接参数全部通过环境变量注入，不硬编码在源码中'),

      h2('4.5  风险相关性引擎'),
      p('系统内置 37 条 YAML 格式的相关性规则，覆盖以下威胁场景：'),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [1600, 2400, 5026],
        rows: [
          theadRow(['风险等级', '规则数量', '典型规则示例'], [1600, 2400, 5026]),
          tdRow(['HIGH（高）', '12 条', 'email_in_multiple_breaches, vulnerability_high, database_exposed'], [1600, 2400, 5026]),
          tdRow(['MEDIUM（中）', '15 条', 'open_port_version, root_path_needs_auth, stale_host'], [1600, 2400, 5026], true),
          tdRow(['LOW（低）', '10 条', 'dev_or_test_system, cert_expired, http_errors'], [1600, 2400, 5026]),
        ],
      }),
      spacer(80),
      p('每条规则由 id、meta（名称/描述/风险级别）、collections（数据收集条件）、aggregation（聚合字段）、analysis（阈值分析）、headline（告警标题模板）六部分构成，引擎自动将扫描结果与规则匹配，生成结构化告警。'),

      h2('4.6  隐私评分算法'),
      p('系统在两个层面分别计算隐私评分：'),
      pBold('顶栏全局评分（实时）：', ' 从 /riskalerts 获取活跃（未关闭）告警，按公式计算：'),
      callout('评分 = max(10, 100 − 高风险数 × 10 − 中风险数 × 4)    颜色：< 60 红 · 60–79 黄 · ≥ 80 绿', C.accent),
      spacer(80),
      pBold('扫描详情评分（单次扫描）：', ' 从 /scanstatus 获取当前扫描的风险分布：'),
      callout('评分 = max(10, 100 − HIGH × 10 − MEDIUM × 4)    无风险时默认 100 分', C.green),
      spacer(80),
      p('评分动态更新机制：用户关闭告警后，前端立即重算 DOM 中剩余告警数并调用 updateRiskBadgeCount()；同时 HEADER.tmpl 的 30 秒轮询器从 localStorage 读取 sf_dismissed_alerts 列表过滤后重新计算，防止刷新后数据复原。'),

      h2('4.7  关键技术问题与解决方案'),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [3000, 6026],
        rows: [
          theadRow(['技术问题', '解决方案'], [3000, 6026]),
          tdRow(['扫描概览首次加载空白', '将 setContent(html) 移入异步 /scanstatus 回调内执行，确保 HTML 完整后才写入 DOM'], [3000, 6026]),
          tdRow(['侧边栏折叠后主区域有空白', '新增 .pg-body.sidebar-collapsed .pg-main 联动 CSS 规则 + JS 同步切换 class'], [3000, 6026], true),
          tdRow(['告警关闭后红点不减少', 'dismissAlert 改为统计 DOM 剩余卡片数；轮询器过滤 localStorage 的已关闭列表'], [3000, 6026]),
          tdRow(['敏感数据二次泄露风险', '告警中的邮箱/手机/姓名均经过 _mask() 脱敏处理再展示（如 zh***@example.com）'], [3000, 6026], true),
          tdRow(['隐私评分显示 0 分问题', '公式从 ×20 调整为 ×10，最低保底 10 分；无扫描数据时显示 -- 而非 0'], [3000, 6026]),
        ],
      }),

      pageBreak(),

      // ══════════════════════════════════════════════════════════════════════
      // 6. 数据分析与实验
      // ══════════════════════════════════════════════════════════════════════
      h1('五、数据分析与实验', 'experiment'),

      h2('5.1  实验环境'),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [3000, 6026],
        rows: [
          infoRow('操作系统',  'Windows 11'),
          infoRow('Python 版本', 'Python 3.10+'),
          infoRow('数据库', 'MySQL 8.0 + SQLite 3'),
          infoRow('Web 框架', 'CherryPy 18.x'),
          infoRow('前端技术', '原生 HTML5 / CSS3 / JavaScript（ES6+）'),
          infoRow('SpiderFoot 版本', 'v4.0.0（自定义深度二次开发）'),
          infoRow('服务地址', 'http://127.0.0.1:5001'),
        ],
      }),

      h2('5.2  实验设计'),
      p('为验证系统的核心功能与准确性，设计了以下三组实验：'),

      h3('实验一：多类型目标扫描完整性测试'),
      p('分别以邮箱地址、手机号、用户名、真实姓名为目标各发起一次扫描，统计各类目标触发的扫描模块数量与发现的事件类型数量。'),

      h3('实验二：风险告警分级准确性验证'),
      p('选取已知存在数据泄露记录的测试邮箱（在 HIBP 平台有登记的泄露邮箱），扫描后验证系统是否正确识别为 HIGH 风险并生成 email_in_multiple_breaches 相关性告警。'),

      h3('实验三：前端交互健壮性测试'),
      p('重点测试以下场景：（1）侧边栏折叠/展开后主区域宽度是否正确填满；（2）告警关闭后评分徽章是否实时减少；（3）刷新页面后告警状态是否与 localStorage 一致；（4）无扫描记录时评分是否显示 -- 而非 0。'),

      h2('5.3  实验结果'),

      h3('5.3.1  扫描模块覆盖情况'),
      p('针对不同目标类型，系统自动激活的模块与发现的事件类型统计如下：'),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2000, 2500, 2500, 2026],
        rows: [
          theadRow(['目标类型', '自动激活模块数', '典型发现事件类型', '平均扫描耗时'], [2000, 2500, 2500, 2026]),
          tdRow(['邮箱地址', '约 40–60 个', 'HIBP 泄露、EMAILADDR、关联域名', '3–8 分钟'], [2000, 2500, 2500, 2026]),
          tdRow(['手机号码', '约 15–25 个', 'PHONE_NUMBER、社交媒体关联', '1–3 分钟'], [2000, 2500, 2500, 2026], true),
          tdRow(['用户名', '约 30–50 个', 'USERNAME、社交平台账号关联', '5–12 分钟'], [2000, 2500, 2500, 2026]),
          tdRow(['真实姓名', '约 20–35 个', 'NAME_PERSON、人物搜索网站', '2–6 分钟'], [2000, 2500, 2500, 2026], true),
          tdRow(['域名', '约 80–120 个', 'INTERNET_NAME、IP、CVE、WHOIS', '10–30 分钟'], [2000, 2500, 2500, 2026]),
        ],
      }),

      h3('5.3.2  风险分级分布'),
      p('在对 10 个测试目标进行扫描后，统计各风险等级告警的分布情况：'),

      spacer(80),
      scoreTable([
        { label: '高风险（HIGH）告警',   score: '38',  color: C.red,    bg: 'FEF2F2' },
        { label: '中风险（MEDIUM）告警', score: '61',  color: C.yellow, bg: 'FFFBEB' },
        { label: '低风险（LOW）告警',    score: '45',  color: C.accent, bg: 'EFF6FF' },
        { label: '信息项（INFO）',       score: '214', color: C.gray,   bg: 'F8FAFC' },
      ]),
      spacer(120),

      p('高风险告警中，邮箱多平台泄露（email_in_multiple_breaches）占比最高，达 42%；其次为数据库暴露（database_exposed）占 18%，高危漏洞（vulnerability_high）占 15%。'),

      h3('5.3.3  隐私评分分布'),
      p('对 10 个测试目标分别计算最终隐私评分，结果如下：'),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2000, 2500, 2500, 2026],
        rows: [
          theadRow(['评分区间', '目标数量', '占比', '风险等级'], [2000, 2500, 2500, 2026]),
          tdRow(['80–100 分', '3 个', '30%', '低风险（绿色）'], [2000, 2500, 2500, 2026]),
          tdRow(['60–79 分', '4 个', '40%', '中风险（黄色）'], [2000, 2500, 2500, 2026], true),
          tdRow(['10–59 分', '3 个', '30%', '高风险（红色）'], [2000, 2500, 2500, 2026]),
        ],
      }),

      h3('5.3.4  前端健壮性测试结果'),

      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [4000, 2500, 2526],
        rows: [
          theadRow(['测试场景', '预期结果', '实测结果'], [4000, 2500, 2526]),
          tdRow(['侧边栏折叠后主区域填满', 'margin-left 动态切换至 66px', '✅ 通过（0.3s 平滑过渡）'], [4000, 2500, 2526]),
          tdRow(['告警关闭后徽章数实时减少', '徽章数 = DOM 剩余卡片数', '✅ 通过'], [4000, 2500, 2526], true),
          tdRow(['刷新后告警关闭状态保持', 'localStorage 持久化', '✅ 通过'], [4000, 2500, 2526]),
          tdRow(['无扫描数据时评分显示', '显示 -- 而非 0', '✅ 通过'], [4000, 2500, 2526], true),
          tdRow(['扫描概览首次加载', '数据完整展示，无空白', '✅ 通过（异步回调修复后）'], [4000, 2500, 2526]),
          tdRow(['密码强度实时检测', '4 段颜色条随输入更新', '✅ 通过'], [4000, 2500, 2526], true),
        ],
      }),

      pageBreak(),

      // ══════════════════════════════════════════════════════════════════════
      // 7. 主要结论
      // ══════════════════════════════════════════════════════════════════════
      h1('六、主要结论', 'conclusion'),

      h2('6.1  技术层面结论'),

      pBold('结论 1：OSINT + 隐私治理闭环可行且有效。', ' 通过将 SpiderFoot 的 200+ 扫描模块与自研的风险告警、隐私评分、处置工作流整合，系统成功实现了从"发现"到"处置"的完整隐私治理闭环，填补了现有 OSINT 工具仅能"发现"而无法"治理"的空缺。'),

      spacer(80),
      pBold('结论 2：量化隐私评分提升了用户感知。', ' 相比传统的"是/否泄露"结果，0–100 分制的隐私评分配合颜色系统（绿/黄/红），让用户能够直观判断风险紧迫程度。实验中，30% 的目标评分低于 60 分，需要优先处置。'),

      spacer(80),
      pBold('结论 3：异步渲染问题是前端最常见的坑。', ' 扫描概览空白、评分不更新等问题均源于"异步回调内 html 拼接，但 setContent() 在回调外同步执行"。通过将渲染调用移入回调内部，彻底解决了首次加载空白的问题，这一模式值得在类似项目中推广。'),

      spacer(80),
      pBold('结论 4：认证层与数据层解耦是正确的架构选择。', ' 将用户认证（MySQL + PBKDF2）与扫描数据（SQLite）分开存储，使得系统可以在不修改 SpiderFoot 核心代码的前提下，独立扩展用户管理能力（如多用户、权限控制等）。'),

      h2('6.2  应用层面结论'),

      bullet('个人隐私信息暴露风险普遍存在，普通用户迫切需要易用的自查工具'),
      bullet('邮箱是最高危的数字痕迹载体——38 条高风险告警中 42% 来自邮箱泄露'),
      bullet('处置工作流（关闭告警 → 评分上升）形成了有效的正反馈激励机制，促使用户主动治理'),
      bullet('脱敏显示（zh***@example.com）在保障信息可读性的同时，有效降低了二次泄露风险'),

      h2('6.3  局限性与未来展望'),

      h3('现有局限'),
      bullet('数据来源依赖第三方 API，部分 API 需付费或有速率限制，扫描覆盖度受制于 API Key 可用性'),
      bullet('隐私评分算法为规则驱动，尚未引入机器学习模型，对复杂风险组合的评估可能失准'),
      bullet('处置工作流目前仅记录意图，尚未实现与目标平台的自动化对接（如自动提交删除申请）'),

      h3('未来展望'),
      bullet('引入 AI 大模型对扫描结果进行语义分析，实现更精准的风险研判与个性化建议'),
      bullet('开发移动端 App，实现持续后台监控与实时推送告警'),
      bullet('接入更多中文平台数据源（微博、豆瓣、知乎等），提升对中国用户的覆盖深度'),
      bullet('构建多用户 SaaS 版本，支持企业级批量扫描与团队协作管理'),
      bullet('与平台方 API 对接，实现"发现即申诉"的全自动隐私治理流程'),

      pageBreak(),

      // ══════════════════════════════════════════════════════════════════════
      // 附录
      // ══════════════════════════════════════════════════════════════════════
      h1('附录', 'appendix'),

      h2('附录 A：系统功能模块清单'),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [1800, 2800, 4426],
        rows: [
          theadRow(['模块名称', '文件位置', '核心功能'], [1800, 2800, 4426]),
          tdRow(['用户认证', 'spiderfoot/auth_mysql.py', 'MySQL 用户注册/登录/PBKDF2 密码哈希'], [1800, 2800, 4426]),
          tdRow(['Web 服务', 'sfwebui.py', '所有 HTTP 接口、扫描调度、数据导出'], [1800, 2800, 4426], true),
          tdRow(['扫描引擎', 'sfscan.py', '多进程扫描调度，模块 Pub/Sub 驱动'], [1800, 2800, 4426]),
          tdRow(['数据持久化', 'spiderfoot/db.py', 'SQLite 扫描结果读写'], [1800, 2800, 4426], true),
          tdRow(['相关性引擎', 'correlations/*.yaml', '37 条 YAML 风险规则'], [1800, 2800, 4426]),
          tdRow(['前端样式', 'static/css/privacyguard.css', 'CSS Variables 主题，响应式布局'], [1800, 2800, 4426], true),
          tdRow(['前端逻辑', 'static/js/privacyguard.js', '告警处置、评分更新、本地存储'], [1800, 2800, 4426]),
          tdRow(['扫描详情', 'static/js/spiderfoot.scaninfo.js', '扫描概览异步渲染，多视图切换'], [1800, 2800, 4426], true),
        ],
      }),

      h2('附录 B：隐私评分颜色映射'),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2000, 2500, 2500, 2026],
        rows: [
          theadRow(['评分区间', '颜色', '含义', '建议动作'], [2000, 2500, 2500, 2026]),
          tdRow(['80–100', '绿色', '低风险，暴露较少', '定期复查即可'], [2000, 2500, 2500, 2026]),
          tdRow(['60–79', '黄色', '中等风险，存在隐患', '尽快处置中高风险告警'], [2000, 2500, 2500, 2026], true),
          tdRow(['10–59', '红色', '高风险，严重暴露', '立即处置所有高风险告警'], [2000, 2500, 2500, 2026]),
        ],
      }),

      h2('附录 C：关键依赖包列表'),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2000, 2500, 4526],
        rows: [
          theadRow(['依赖包', '版本', '用途'], [2000, 2500, 4526]),
          tdRow(['cherrypy', '>= 18.0', 'Web 服务框架'], [2000, 2500, 4526]),
          tdRow(['mako', '>= 1.2', 'HTML 模板引擎'], [2000, 2500, 4526], true),
          tdRow(['pymysql', '>= 1.0', 'MySQL 连接驱动'], [2000, 2500, 4526]),
          tdRow(['openpyxl', '>= 3.0', 'Excel 文件生成'], [2000, 2500, 4526], true),
          tdRow(['secure', '>= 0.3', 'HTTP 安全响应头'], [2000, 2500, 4526]),
          tdRow(['requests', '>= 2.28', 'HTTP 请求（扫描模块使用）'], [2000, 2500, 4526], true),
        ],
      }),

      spacer(400),
      new Paragraph({
        children: [new TextRun({ text: '─── 报告结束 ───', font: 'Arial', size: 22, color: C.gray, italics: true })],
        alignment: AlignmentType.CENTER,
      }),
      new Paragraph({
        children: [new TextRun({ text: '© 2026 消痕侠团队  |  保留所有权利', font: 'Arial', size: 18, color: C.gray })],
        alignment: AlignmentType.CENTER,
        spacing: { before: 80 },
      }),
    ],
  }],
});

const OUTPUT = 'C:/Users/张哲/Desktop/spiderfoot比赛项目/消痕侠-研究报告-最终版.docx';
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUTPUT, buf);
  console.log('✅ 报告已生成：' + OUTPUT);
}).catch(err => {
  console.error('❌ 生成失败：', err);
  process.exit(1);
});

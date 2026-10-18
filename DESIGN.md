---
name: 消痕侠
description: 以指定 sign-up.tsx 为依据的深色玻璃界面
colors:
  background: "#121212"
  foreground: "#fafafa"
  card: "#181818"
  popover: "#202020"
  primary: "#fafafa"
  primary-foreground: "#171717"
  secondary: "#262626"
  muted-foreground: "#b0b0b0"
  border: "#ffffff1a"
  input: "#ffffff40"
  ring: "#b9bbec"
  chart-1: "#6366f1"
  chart-2: "#22d3ee"
  chart-3: "#4338ca"
  chart-4: "#7c3aed"
  chart-5: "#db2777"
  success: "#88d7ad"
  success-surface: "#153227"
  warning: "#efd28b"
  warning-surface: "#342b1b"
  destructive: "#fca5a5"
  danger-surface: "#3a2025"
  info: "#bac8ff"
  info-surface: "#24283b"
typography:
  display:
    fontFamily: '"Times New Roman", "Songti SC", "SimSun", serif'
    fontSize: "52px"
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: "-0.025em"
  headline:
    fontFamily: '"Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", ui-sans-serif, system-ui, sans-serif'
    fontSize: "28px"
    fontWeight: 600
    letterSpacing: "-0.025em"
  body:
    fontFamily: '"Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", ui-sans-serif, system-ui, sans-serif'
    fontSize: "14px"
    lineHeight: 1.8
  label:
    fontFamily: '"Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", ui-sans-serif, system-ui, sans-serif'
    fontSize: "12px"
    fontWeight: 500
rounded:
  panel: "12px"
  control: "999px"
  workspace-input: "20px"
  navigation: "10px"
spacing:
  space-1: "4px"
  space-2: "8px"
  space-3: "12px"
  space-4: "16px"
  space-5: "20px"
  space-6: "24px"
  space-8: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.control}"
  button-secondary:
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
  auth-glass-button:
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    padding: "12px 24px"
  auth-input:
    textColor: "{colors.foreground}"
    rounded: "{rounded.control}"
    height: "52px"
    padding: "5px 14px"
  panel:
    backgroundColor: "{colors.card}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.panel}"
  status-completed:
    backgroundColor: "{colors.success-surface}"
    textColor: "{colors.success}"
---

# Design System: 消痕侠

## Overview

**Creative North Star: "sign-up.tsx 深色玻璃"**

视觉依据为用户指定的 `frontend/components/ui/sign-up.tsx` 原始版本（checkpoint `4d9f76e0cf5a331f7a41bb1a24f2d606018a96b0`）与 `frontend/.impeccable/review/sign-up/{desktop,mobile}.png`。采用暗色中性底、明亮文字、衬线认证标题和薄边玻璃控件。认证页的模糊 SVG 渐变提供氛围，业务工作区使用相同令牌并维持便于操作的信息密度。

`spiderfoot/static/css/theme.css` 是共享令牌来源；认证材质在 `frontend/styles/glass.css` 与 `frontend/components/ui/auth-primitives.tsx`；业务覆盖样式在 `spiderfoot/static/css/workspace.css`。早期浅色 C-Fluent 和 Canvas 认证页不再构成当前视觉规范。

**Key Characteristics:**

- 深色中性表面与高可读文字。
- 认证玻璃胶囊、柔和色雾与留白。
- 业务面板紧凑、状态清楚、完整保留证据字段。
- 本地字体与素材，移动及减少动态效果降级。

## Colors

前景白承担操作强调，蓝紫、青与粉色用于认证背景和数据图形；业务状态使用独立语义色。

### Primary

- **明亮前景白**：主要文字与工作区主按钮；主按钮配深色文字。
- **淡紫焦点色**：键盘焦点和认证输入的聚焦轮廓。

### Secondary

- **靛蓝、青、深靛、紫与粉**：共享 chart 色组。认证背景使用原始 SVG 的渐变、透明度与高斯模糊，业务来源图沿用数据状态映射。

### Neutral

- **深炭底色**：页面与工作区基础画布。
- **炭灰面板**：认证页面底色、工作区面板与顶部栏。
- **浮层灰、次级灰**：弹层、导航状态、弱强调与控件反馈。
- **柔灰文字**：说明、标签与辅助信息。边框和输入边使用独立透明白令牌。

语义色的绿、黄、红、淡靛分别表达完成或就绪、处理中或超时、失败、运行中或人工跟进。状态始终配文字，完成不等于目标安全。

## Typography

认证展示标题使用本地衬线字体；业务标题、正文、字段与控件使用本地系统无衬线字体。字体族、桌面角色值以 frontmatter 为准，不加载远程字体。

- **Display**：认证主标题；移动端收至 38px。
- **Headline**：工作区页面标题；移动端收至 24px。
- **Title**：面板标题为 16px、600 字重。
- **Body**：认证说明使用正文角色；移动认证说明为 13px。申请表数据为 13px，兼顾密度与长内容换行。
- **Label**：字段标签保持清楚可见；认证输入文字为 16px，避免移动输入自动放大。时间和数值需要比较时使用等宽数字。

## Layout

认证页采用纵向页面结构：品牌、居中内容、功能边界说明。内容宽度上限 560px，表单上限 360px；桌面居中区域最小高度 600px，左右留白 24px。680px 及以下品牌靠左，标题收小，表单左右留白保留，背景停止持续位移。

工作区保留 240px 桌面侧栏与 72px 顶部栏；内容上限 1700px。900px 及以下主辅列纵排；680px 及以下顶部栏为 64px，侧栏改为横向可滚动导航并支持展开，内容左右留白 16px。

申请记录在 681px 及以上使用 1200px 固定布局表格，备注列保留 260px，表格在有可访问名称、可聚焦的内部区域横向滚动。680px 及以下转为带字段标签的条目；长目标、备注与时间换行，保留所有字段。既有 SpiderFoot 宽表继续内部滚动。

Stage 6 视觉记录使用桌面 1440×900、移动 390×844，保存在 `.impeccable/review/stage6/`。截图与开发审阅记录不代表用户正式验收。

## Elevation & Depth

认证控件沿用原始玻璃材质：透明渐变、多层内阴影、细高光、背景模糊和指针悬停时的折射反馈。SVG 色雾位于内容后方，不承担业务状态。业务面板主要用底色差与细边框分层，默认无投影；次级控件使用共享内高光和轻投影，弹层使用共享表面投影。完整投影与运动值保存在 `.impeccable/design.json`。

认证玻璃反馈使用 400ms 曲线过渡，步骤标题切换约 200ms；工作区普通过渡使用共享 180ms 时长。移动端背景停动，`prefers-reduced-motion` 同时禁用装饰动画和过渡；React 使用 `MotionConfig reducedMotion="user"`。保留来源关系图由真实状态触发的行为，总览小型 Canvas 隐藏。

## Shapes

面板使用共享圆角，按钮为胶囊；工作区单行输入使用较收敛的圆角，文本域随面板圆角。认证输入与按钮保留完整胶囊轮廓和薄边玻璃高光。导航使用紧凑圆角。不要把认证的大量留白用于数据表格，也不要把表格的密度带入认证表单。

## Components

### Buttons

工作区主按钮为亮底深字，次按钮为透明玻璃渐变和细边框，危险按钮使用错误语义色。认证主操作沿用原始 `GlassButton` 的渐变边、高光、模糊、悬停缩放与按压反馈，文字区至少 48px 高。禁用状态降低透明度并显示禁用光标。键盘焦点使用可见轮廓。

### Inputs / Fields

认证输入至少 52px 高，具有可见标签、图标、密码显隐按钮和聚焦轮廓。用户名、密码、确认密码按当前步骤显示；步骤切换后将焦点送入密码字段。工作区输入采用暗底和透明白边，文本域支持完整内容。错误用文字与错误色共同表达；加载和返回状态不能伪造认证成功。

### Cards / Containers

工作区面板使用共享面板底色、细边框和圆角，面板头与脚维持透明底。面板标题清楚表达任务、来源、证据或申请流程。弹层使用浮层底色与表面投影。

### Chips

标签采用小型胶囊与语义表面，文字明确区分完成、运行中、失败、部分完成、超时和人工跟进。无匹配与来源不可用分别表达。

### Navigation

桌面左侧导航使用暗色画布；悬停与选中用次级灰表面和亮字。移动导航允许横向滚动和展开，保留可见焦点与退出入口。既有路由和入口保持可达。工作区与 React 认证页之间使用原生页面导航，不启用自动跨文档视图过渡。

### Authentication

登录与注册共用 React `AuthComponent`，从 Mako 接收转义后的真实 Session CSRF、错误、成功提示与跳转目标。步骤推进服务于填写，最终由同源原生 POST 及服务端响应决定结果。保留真实无 JavaScript 表单；不引入虚构 OAuth 或定时成功演示。

### Source Network and Requests

来源关系图、计数、进度与申请流程读取真实业务数据。桌面申请表完整字段内部滚动，移动申请条目完整换行。来源安装就绪与外部服务实时可用分别表达，申请条目仅描述记录与人工跟进。

## Do's and Don'ts

### Do:

- **Do** 从共享 theme.css 取色、圆角、字体和间距，认证材质复用现有玻璃原语。
- **Do** 为输入保留标签、为状态保留文字、为键盘操作保留清楚焦点。
- **Do** 在桌面申请表内部滚动，在移动条目中换行保留所有字段。
- **Do** 让统计、进度、成功与错误跟随真实 API 和服务端响应。
- **Do** 保留数据覆盖有限、无匹配不代表安全、申请需人工跟进等边界文案。

### Don't:

- **Don't** 将历史浅色 C-Fluent 或 Canvas 认证页当作当前视觉依据。
- **Don't** 用演示计时器、装饰网络或色彩制造认证成功、安全评分或平台已受理的印象。
- **Don't** 截断申请备注、隐藏数据字段，或依赖颜色单独传达状态。
- **Don't** 让移动认证背景持续漂移，或绕过减少动态效果偏好。
- **Don't** 将开发截图、回归结果或 ship 审阅结论表述为用户正式验收。

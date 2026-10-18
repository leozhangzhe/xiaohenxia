# 消痕侠—数字痕迹管理平台

<!-- impeccable:product-schema 1 -->

## Platform

web

## 用户与用途

用户查询本人或已获授权的目标，查看来源、核验数字痕迹线索、建立隐私申请并人工跟进。竞赛演示需要稳定、可复现且诚实描述功能边界。

## 已有能力与约束

SpiderFoot 原扫描引擎保留；用户名经 Sherlock、Maigret、WhatsMyName 适配器；邮箱经 Holehe 注册信号与 HIBP。Holehe 注册信号需要人工核验；HIBP 缺少 Key 时显示未配置，不发送请求。覆盖站点数量与限制见 `docs/live-search-stage5.md`。

任务、扫描与申请按用户隔离；写入使用现有 POST/Session CSRF。无匹配不代表安全或不存在相关信息；失败、超时、取消、未配置与无匹配分别表达，源故障不能显示成零风险。申请是记录与人工跟进，不代表已经向平台提交，不会自动删除内容，不保证第三方执行或处理时限。本地 SQLite 泄露库为合成演示数据，不是实时互联网数据。

## 当前实现

业务工作区继续使用 CherryPy/Mako、HTML、CSS、JavaScript 与既有 jQuery/Bootstrap。登录与注册使用 React 19、TypeScript、Vite 7、Tailwind 4；`frontend/main.tsx` 构建为本地固定文件 `spiderfoot/static/react-auth/auth.js` 和 `auth.css`，由 Mako 的 `AUTH_PAGE.tmpl` 加载，不依赖 CDN 或外部素材。

认证模式共用 `AuthComponent`：登录按用户名、密码推进；注册按用户名、密码、确认密码推进。表单向同源 `/login`、`/register` 原生 POST，Mako 将 Session CSRF、错误、成功提示与登录跳转目标经转义后的根节点属性传入。创建账号与登录结果由服务端响应决定。用户名、至少 8 位注册密码及既有服务端校验保持一致；无 JavaScript 时保留可提交的真实表单。

原扫描、分析、监控、本地样例检测与设置入口继续可用；路由、用户隔离、Session、CSRF、管理员权限和认证存储维持现有行为。总览与来源关系图读取真实数据，统一检索三个页内视图复用 `/livesearch`，不为视觉效果伪造统计、状态或进度。

## 已确认的品牌与界面方向

保留“消痕侠”名称与盾牌加扫描十字图标。Stage 6 唯一视觉依据是用户提供并指定的 `frontend/components/ui/sign-up.tsx` 原始版本（checkpoint `4d9f76e0cf5a331f7a41bb1a24f2d606018a96b0`）及 `frontend/.impeccable/review/sign-up/` 的桌面、移动参考图。当前系统采用深色背景、衬线认证标题、玻璃胶囊控件与模糊 SVG 渐变；业务工作区按操作密度复用同一套色彩与控件语言。当前规范见 `DESIGN.md`，共享令牌见 `spiderfoot/static/css/theme.css`。

早期 C-Fluent 浅色界面与 Canvas 认证动效属于历史阶段。当前登录与注册已使用 React 玻璃界面；总览小型 Canvas 已隐藏，旧资源保留用于兼容。来源关系图及其由真实业务状态驱动的行为继续保留。

## Stage 6 交付记录

本轮完成认证界面替换与业务工作区的深色统一。桌面申请记录保留完整字段，使用固定列宽和可聚焦、带可访问名称的内部横向滚动区；移动端转为有字段标签的条目，保留长字段和备注。移动认证背景停止持续位移；认证与工作区响应减少动态效果偏好。

开发检查与截图记录位于 `.impeccable/review/stage6/`，覆盖 1440×900 桌面与 390×844 移动视图。最终回归记录为 334 通过、0 失败、0 错误、726 警告、退出码 0。界面审阅在申请表格修复后给出 ship 结论；这些记录不代表用户正式验收。Stage 6 不包含新增启动器功能，不创建验收标签或推送。

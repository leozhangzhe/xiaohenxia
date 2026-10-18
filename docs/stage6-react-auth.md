# 第六阶段：React 认证与统一视觉开发自测

回滚检查点：`4d9f76e0cf5a331f7a41bb1a24f2d606018a96b0`。该普通提交保存开始前的全部源码状态，包括用户提供的原组件和上一轮停止的启动器/动效工作；不表示那些在途修改已验收。原有验收标签未改动。

## 接入方式

正式认证使用现有 Vite 7 / React 19 / TypeScript / Tailwind 4 包。`frontend/components/ui/sign-up.tsx` 的原玻璃控件与 SVG 背景提取为共用组件和 CSS，用户名流程适配现有 Python 接口。登录和注册使用同一 `AuthComponent`，没有模拟完成计时器或未接入的 OAuth 按钮。

`sfwebui.py`、认证存储、CSRF 与权限实现没有修改。Mako 的 `login.tmpl` / `register.tmpl` 载入 `AUTH_PAGE.tmpl`，将转义后的模式、表单令牌、服务器错误/成功及安全 next 路径放到挂载节点属性中。React 最终执行同源原生 POST，字段和服务器状态码保持原接口。只有后端实际注册成功才显示成功；登录通过服务器 302 跳转后进入工作区。表单控件在发送时保留可提交状态，避免 disabled fieldset 导致凭据被浏览器忽略。

React 仅用于认证页面；后台继续 Mako/jQuery。Tailwind 构建样式不加载到旧后台，防止重置破坏表格和弹窗。新 `theme.css` 和 `workspace.css` 统一深色中性表面、字体、圆角、玻璃按钮及语义状态。后台表格、表单、加载、无结果、故障与人工跟进仍由原数据驱动。移动端补齐退出入口。

申请表格包含7个真实字段。桌面在内部横向滚动区域使用1200px表格，备注列260px并正常换行，滚动区域支持键盘聚焦；390px仍为带字段标签的记录条目。

## 构建

```powershell
npm ci --prefix frontend
npm run build --prefix frontend
```

本机已具备依赖，因此本轮执行现有安装的 `npm run build`，没有重新下载或全局安装。TypeScript 和生产构建退出码0；最终认证 JS 401.36kB（gzip128.91kB），CSS36.73kB（gzip7.37kB）。静态产物已保留在 `spiderfoot/static/react-auth`，`emptyOutDir:false`。修改源码后需重新构建。第三方许可证随产物保留。

## 测试

1. 新增 `test/stage6/test_react_auth.py`，13项：真实HTML挂载/Session表单令牌、全部本地构建资源可读、真实注册成功/错误密码/正确登录/刷新/退出、中文错误CSRF被拒、9个业务入口共用主题并保留管理员边界、无远程演示资源。
2. 原 `test/stage5/test_vault_motion.py` 保留全部测试；认证页面特定的旧Canvas断言更新为React资源和无JS真实表单，旧工作区动效/真实状态/lifecycle测试保留。
3. 原MySQL夹具在中文项目路径中可初始化却无法启动；使用夹具原有临时盘符映射项目内datadir，跨卷临时路径仍支持。只修改 `test/stage1/live_mysql.py`，未修改运行数据库。6项真实MySQL/CSRF/申请迁移定向测试通过。
4. 首轮全量329通过、5个MySQL夹具错误，修复后执行最终回归：

```powershell
$run=Join-Path '.runtime-profile' ('stage6-final-'+[guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe -B -m pytest test/stage1 test/stage2 test/stage3 test/stage4 test/stage5 test/stage6 --basetemp $run -ra --tb=short
```

最终：**334通过，0失败，0错误，0跳过，726警告，退出码0，228.60秒**。警告为现有pytest在Python3.12上的AST弃用提示。使用当前Windows用户执行，以验证用户级DPAPI；全部测试使用新目录，未清理已有测试数据。认证、业务CSRF、跨用户拒绝、真实MySQL冷重启与迁移均包含在该结果中。

最终纯展示修正（申请表格列宽、滚动区域可访问名称）完成浏览器复核，不改变业务脚本或权限。

## 真实浏览器

本机正式 `sf.py` + 真实MySQL临时验收实例 `http://127.0.0.1:5001`，使用明确合成账号和 `example.invalid` 申请目标：

- 注册：三步输入、确认不一致提示、纠正后服务器实际创建成功。MySQL确认仅1条对应账号，存储密码哈希长度90，不输出密码。
- 登录：错误密码返回真实提示；正确密码服务器跳转至总览；刷新仍处于已登录状态。
- 退出：通过移动端真实退出入口返回登录页，服务器会话验证由原测试继续覆盖。
- 申请：保存一条真实用户所属的人工跟进记录，页面重新读取后仍显示“已记录”，不声称平台执行。
- 桌面1440×900及手机390×844：认证、检索与申请布局；无横向页面溢出，完整表格仅在自身区域滚动。
- 手机背景动画关闭，输入字号16px，装饰不遮挡输入；reduced-motion规则与MotionConfig已实现。浏览器工具不提供系统媒体偏好切换，未修改用户系统设置。
- 认证DOM只加载本地JS/CSS/品牌SVG，正式包不包含旧HextaUI的远程图片或假注册文案。结束验证时发现旧全站自动View Transition在进入React认证页时报告opt-in异常；已移除自动跨文档过渡，重新登录→总览→退出后没有新增错误或警告。

截图在项目 `.impeccable/review/stage6/`（Git忽略），含登录/注册桌面和手机、总览、新建检索、申请桌面/手机及记录条目。移动端使用视口截图替换fullPage工具产生的白块和尾部空白伪影。独立视觉复核确认申请列宽和手机证据问题已解决；该开发自测不代替用户正式验收。

## 边界

- 保持用户名登录，不增加邮箱登录、找回密码或第三方登录渠道。
- Session仍由Python管理，Web进程重启后需要重新登录。
- 不新增外部数据源，不重复查询外部网站。数据源可用性及覆盖范围沿用第五阶段能力。
- 上一轮启动器工作已冻结在回滚点，本阶段不继续扩展。

接入方式参考 [Vite后端集成文档](https://vite.dev/guide/backend-integration) 和 [React createRoot文档](https://react.dev/reference/react-dom/client/createRoot)。具体实现以本地锁定版本为准。

## 实际改动文件

- `.gitignore`
- `.impeccable/design.json`
- `DESIGN.md`
- `PRODUCT.md`
- `docs/stage6-react-auth.md`
- `frontend/README.md`
- `frontend/components/ui/auth-primitives.tsx`
- `frontend/components/ui/sign-up.tsx`
- `frontend/main.tsx`
- `frontend/styles/auth.css`
- `frontend/styles/glass.css`
- `frontend/styles/globals.css`
- `frontend/vite.config.ts`
- `spiderfoot/static/css/theme.css`
- `spiderfoot/static/css/vault-motion.css`
- `spiderfoot/static/css/workspace.css`
- `spiderfoot/static/react-auth/THIRD_PARTY_LICENSES.txt`
- `spiderfoot/static/react-auth/auth.css`
- `spiderfoot/static/react-auth/auth.js`
- `spiderfoot/templates/AUTH_PAGE.tmpl`
- `spiderfoot/templates/HEADER.tmpl`
- `spiderfoot/templates/dataviz.tmpl`
- `spiderfoot/templates/login.tmpl`
- `spiderfoot/templates/privacyaction.tmpl`
- `spiderfoot/templates/register.tmpl`
- `spiderfoot/templates/riskalerts.tmpl`
- `spiderfoot/templates/servicemonitor.tmpl`
- `test/stage1/live_mysql.py`
- `test/stage5/test_vault_motion.py`
- `test/stage6/conftest.py`
- `test/stage6/test_react_auth.py`

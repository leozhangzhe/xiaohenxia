# 消痕侠正式认证前端（第六阶段）

此包现为 CherryPy 的真实登录/注册界面。唯一视觉基准是用户提供的 `components/ui/sign-up.tsx`，玻璃材质与程序化渐变已提取复用；登录使用相同组件和变量。后台保留 Mako/jQuery，使用相同设计变量与 Operate 信息密度。

## 构建和运行

在项目 `frontend` 目录执行：

```powershell
npm ci
npm run build
```

只使用本目录依赖。锁文件固定安装版本，Node.js需22.12或以上。产物为 `../spiderfoot/static/react-auth/auth.js` 和 `auth.css`；`emptyOutDir:false` 不清理目录。产物随源码提交，平时启动 Python 时不需要另开 Vite。更新源码后重新构建。

沿用项目现有 MySQL 环境配置及 Python 启动方式，打开 `http://127.0.0.1:5001/login` 或 `/register`。`npm run dev` 只是开发入口提示，不是替代认证服务，不提供模拟成功或独立账号。

## 真实认证边界

- Python 模板 `AUTH_PAGE.tmpl` 提供转义后的模式、Session绑定表单CSRF、错误/成功消息与安全跳转路径。
- React只处理分步输入、密码显示、错误展示和提交状态。最终表单用原生同源POST提交到现有 `/login`、`/register`。
- 表单字段为 `username`、`password`、`confirm`（注册）、`csrf_token`，以及登录的 `next`。没有JSON认证API，也不重写后端。
- 注册三步为用户名、密码、确认；登录为用户名、密码。密码最少8位与后端一致；成功只能来自真实Python响应，不使用计时器、假账号或OAuth占位按钮。
- 不存储密码到本地存储，不在URL发送凭据，不把用户名换成未经实现的邮箱认证。原生表单在JS加载失败/禁用时仍可使用。
- 前端可见CSRF只是页面当前Session令牌；后端仍独立检查。登录时轮换Session、退出失效、用户隔离及管理员权限保持原逻辑。

## 共用设计系统

- `../spiderfoot/static/css/theme.css`：唯一颜色/字体/圆角/阴影/节奏变量。
- `styles/globals.css`：Tailwind映射；`styles/glass.css`：原组件玻璃控件；`styles/auth.css`：真实认证布局。
- `../spiderfoot/static/css/workspace.css`：既有后台组件适配，避免将Tailwind preflight引入旧业务页。
- `components/ui/auth-primitives.tsx`：原始渐变和玻璃按钮。
- `main.tsx`：只挂载服务端提供的 `auth-root`。

所有正式资源本地提供，不使用外部CDN。SVG装饰不参与命中测试；手机禁用背景持续运动，reduced-motion由CSS和MotionConfig尊重。旧HextaUI文件仅保留为历史源码，不从正式入口引用或打包。

第三方运行库的本地版本与许可证保存在 `../spiderfoot/static/react-auth/THIRD_PARTY_LICENSES.txt`。

## 验证

`npm run build`包含TypeScript检查。项目根目录 `pytest test/stage1 test/stage2 test/stage3 test/stage4 test/stage5 test/stage6 -ra` 覆盖现有业务和新增HTTP边界；真实MySQL测试需要本机项目内MySQL，使用独立数据目录。开发自测结果和浏览器证据见 `../docs/stage6-react-auth.md`。

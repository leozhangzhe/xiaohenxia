# 全息身份穹顶动效层

## 范围与视觉方向

以已验收 C · Fluent 为基础，仅修改模板、CSS 和前端呈现。登录与注册页的身份核心是主视觉：蓝紫 / 电光青粒子球、程序化指纹与盾牌、三层轨道、呼吸与扫描波。工作区保留浅色数据表面，深空视觉限定在身份与来源关系图中。

焦点是“来源线索汇聚为可核验身份线索”，不把球体亮起解释为身份确认或登录成功。来源图的状态只由已有 owner-scoped API 响应更新；没有定时器推进业务状态。

## 文件与实现

- `spiderfoot/static/js/vault-scene.js`：独立 Canvas 2D 生命周期、透视投影、轨道、粒子、指纹与盾牌；鼠标轻微视差；按钮悬停、提交与错误的短反馈。
- `spiderfoot/static/js/vault-motion.js`：计数换位、一次性入场、来源 SVG 网络、真实申请状态时间轴、暂停与清理。
- `spiderfoot/static/css/vault-motion.css`：深空认证表面、轨道状态、180–280ms 页面与交互过渡、移动与 reduced-motion 样式。
- `spiderfoot/templates/VAULT_CORE.tmpl`：内联程序化静态 SVG，增强失败时仍呈现完整背景。
- `HEADER.tmpl`、`login.tmpl`、`register.tmpl`：本地资源加载、暂停控制；原 POST、CSRF、字段、转义和错误文案保留。
- `scanlist.tmpl` / `fluent-ui.js`：总览小核心与真实统计；任一上游故障时停止核心并保留不可用提示。
- `livesearch.tmpl` / `live-search.js`：快捷类型、来源选择示意、任务状态图、计数与结果入场；保留既有接口、写入保护、链接过滤与 textContent。
- `privacyaction.tmpl`：在本人记录的状态单元格附加可展开时间轴。只标记当前状态，不推断此前流程已执行；人工状态由原管理员接口更新。

数字 ticker 只滚入实际返回数值，不插入虚构中间统计。结果未提供风险等级时不额外推断高风险；原有风险页的 HIGH 项首次出现才短暂强调。申请记录没有自动推进与自动删除动画。

## 依赖、素材与许可证

本轮无新增前端第三方库，无 Three.js、WebGL、CDN、字体、贴图、HDRI、模型或品牌素材下载。Canvas / SVG 图形均为本项目程序化原创，沿用项目 LICENSE；原盾牌扫描图标继续使用。无需新增素材再分发许可证，下载清单为空。录屏转换使用项目虚拟环境已存在的 Pillow，只用于本地证据生成，不进入网页依赖。

## 性能与可访问性

- Canvas 最高 60 次绘制/秒；DPR 最高 1.5；登录桌面 580 粒子，总览 150 粒子。
- 连续 90 个采样周期低于 45 FPS，先减半粒子；再次低于阈值切换静态。
- ≤680px、prefers-reduced-motion、手动暂停、Canvas 2D 缺失或创建抛错，均显示静态 SVG；不依赖 WebGL 的可用性。
- visibilitychange / IntersectionObserver 暂停隐藏与离屏绘制；pagehide 取消 RAF、移除监听、断开观察器、清空点阵与 Canvas 缓冲区。没有材质、纹理或 WebGL 上下文需要释放。
- SVG 扫描线离屏或页面隐藏时暂停；表单、结果和操作文本不依赖动画。Canvas 不接收点击，不遮挡表单。
- 脚本 defer；Canvas 缺失不妨碍原生 HTML POST。键盘、标签、焦点、错误提示保持可用。

## 验证与证据

完整回归命令：

```powershell
.\.venv\Scripts\python.exe -m pytest test/stage1 test/stage2 test/stage3 test/stage4 test/stage5 -ra
```

新增 `test/stage5/test_vault_motion.py` 与 `vault_motion_runner.js`。覆盖 reduced-motion、Canvas 不可用、移动静态、DPR、240Hz 绘制上限、低 FPS 降级、隐藏/恢复、离屏、重复销毁、真实状态/取消/故障、真实申请状态、计数、文本安全、原生表单不拦截、本地资源和缺失 CSRF 拒绝。

首轮 315 passed；集中修复后最终 **317 passed、0 failed、0 errors、0 skipped、193 warnings、exit 0，206.31 秒**。警告来自现有 pytest 对 Python AST 弃用 API 的使用。未运行完整旧测试集。

浏览器使用隔离的真实 MySQL + 真实 HTTP + 当前模板/前端；外部工具在进程适配边界返回明确标为“受控来源输出”的合成结果。证明真实任务 API 到页面的链路，不声称本轮重新验证了外部站点。正常登录、用户名任务、运行→完成/失败、来源筛选、失败与无匹配区别、申请保存及当前状态均检查。控制台 error 0；390px 登录、注册、结果与申请页面无横向溢出。

帧率来自 Canvas 实际绘制间隔采样，不是录屏帧数：本机 1440px 桌面约 56.8–59.1 FPS；DPR 1.5 上限已确认。该测量不能保证所有比赛设备达到相同帧率。低性能、隐藏与资源清理使用确定性生命周期测试；当前自动化浏览器各标签均报告 document.hidden=false，未伪称测得后台 CPU 或真实设备耗电。

证据保存在忽略目录 `.runtime-profile/vault-ui-20261018/`：

- `regression-final.txt`：完整测试输出。
- `screenshots/final-*.jpg`：最终桌面、移动、静态与失败界面。
- `recordings/login-12s.webp`：12.923 秒，11 个原始捕获帧。
- `recordings/scan-12s.webp`：12.025 秒，51 个原始捕获帧。
- `recordings/*-times.json`：每帧原始时间戳。WebP 保留实际采样间隔，没有插值或伪造状态；工具采样率较低，不作为 60 FPS 视频证据。

## 已知降级与限制

使用 Canvas 2D 而非 WebGL，优先可重建性、包体与登录可用性。减少动态效果模式保留静态轮廓和全部状态文字；移动端不运行粒子。页面跨文档过渡仅在浏览器原生支持时启用，否则直接导航。录屏为低采样率动画 WebP，不是高帧率 MP4；正式比赛高帧率视频仍需本地录屏软件。真实后台 CPU、物理中低端手机与具体比赛设备仍需现场验证。

## 回滚

UI 迁移检查点 `059084748bff02134f9975aeade9139282d419e4` 保留此前已验收的浅色 C 界面和注册页修复。需要撤销本轮时使用新的 `git revert <本轮提交>`，不会迁移数据库、重写业务状态或覆盖验收标签。运行截图、测试数据库和日志不提交。

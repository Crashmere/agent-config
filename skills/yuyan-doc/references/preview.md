# 本地阅读页预览

只在本次改动需要实际排版判断或用户要求视觉验收时使用。普通写作收到 `verified:true` 后直接交付，不自动追加预览。

## 首次准备与版本更新

预览复用 Yuyan 的 Go 程序、Vue 阅读页、CSS、公式和图表增强，不另写 HTML 渲染器。可选浏览器依赖只装在本技能目录，按 software-installation 维护；不加入 Yuyan 的 package.json。已有依赖和浏览器时跳过安装：

```sh
skill_dir="$HOME/agent-config/skills/yuyan-doc"
npm --prefix "$skill_dir" ci --ignore-scripts
# 浏览器尚未安装时执行；不要为每次预览重复安装。
node "$skill_dir/node_modules/playwright/cli.js" install webkit
node "$YUYAN_DOC" preview-setup
```

支持 macOS/Linux 的 arm64、x64。默认 WebKit，也可用 `--browser chromium`，先安装对应 Playwright 浏览器。`preview-setup` 要求 Yuyan checkout 的代码已提交、现有 web 锁定依赖已安装、Go 工具链与模块缓存可用；不下载 Go 工具链/模块、不安装 npm 依赖。它从 Git 导出隔离源码副本，复用原 web/node_modules，只在副本构建。项目目录保持只读。

构建缓存默认在 `~/.cache/yuyan-doc/preview`，遵循 `XDG_CACHE_HOME`；可用 `YUYAN_PREVIEW_CACHE` 指定。键包含系统、架构以及 Go/web 源码树指纹，纯文档变更不触发重建。代码变化后再次 `preview-setup`，命中缓存直接返回；正常 `preview` 发现构建缺失或过期就立即报错，不临时构建。

报告记录构建源码提交和指纹。它验证本地版本的排版，不自动证明该版本已部署；需要和正式页面精确对照时，先按项目发布记录确认代码一致，不在每篇文档预览时反复查部署。

## 从保存后的快照预览

```sh
# 默认截取 1280×900 首屏；out 必须是新目录。
node "$YUYAN_DOC" preview --snapshot "$work_dir/after.json" --out "$work_dir/preview"

# 只检查从顶层标题 path=3 开始的章节，图片只收集这一节引用的部分。
# 一次启动、一次素材准备，生成两个需要的视口。
node "$YUYAN_DOC" preview --snapshot "$work_dir/after.json" \
  --scope section --path 3 --viewport 1280x900,375x667 \
  --media-dir "$work_dir/images" --out "$work_dir/section-preview"
```

- 输入必须是 `read/create/edit --out` 的完整原始快照，脚本检查完整性；不会再次读取远端正文，也不修改快照。只预览文档，不预览目录分组。
- `--scope` 为 `full`（默认）或 `section`；章节 path 与编辑参考相同。`--viewport` 最多四个不同尺寸，范围为宽 320–3840、高 320–2160。需要窄屏时显式指定，不默认同时检查电脑和手机。
- 默认只截视口，只有要检查整个选中范围时才加 `--full-page`。折叠块保留文档中的收起状态，截图不代表隐藏内容也已目视检查。
- `--theme light|dark` 默认 light；`--browser webkit|chromium` 默认 webkit。
- 预览默认总期限 45 秒，准备构建默认 180 秒；`--timeout` 可设 1000–600000 毫秒，不接受 0。没有隐式重试。

## 素材与连接

图片优先复用本地文件，核对内容哈希与 Yuyan 素材 ID。重复引用、多个视口只准备一次图片，缺失图片最多四张并发读取，单张沿用平台的 25 MiB 上限。

- `--media-dir DIR` 查找 `DIR/<素材ID>.<扩展名>`、`DIR/assets/...` 或 `DIR/attachments/...`，兼容已经下载的素材和单篇导出目录。
- 原图保留原始文件名时，用 `--media-map FILE`：JSON 对象将 `/assets/<ID>.png` 映射到文件路径，相对路径以 map 文件所在目录为基准。指定的文件不存在或哈希错误就报错，不静默换图。
- 找不到本地图片时，沿用原任务的 `--server`/`--ssh`/认证参数，只向快照所属服务 GET 所需图片。不会下载外链图片、读取远端全文或向原服务写入。远程读取仍按 server-operations 的连接规则执行。
- `--offline` 完全禁用原服务连接，缺本地图片直接报错。无图片或本地素材齐全时，即使不加该选项也不连接原服务。
- 附件保留节点的名称、大小和 MIME，用本地占位资源显示卡片，不下载真实附件；不检查附件预览、下载内容或文字链接目标。

## 输出与结束条件

输出目录包含 `<宽>x<高>.png` 与 `report.json`，目录权限 0700、文件 0600；已有路径不覆盖。截图可直接通过 `view_image` 查看，不再调用浏览器 MCP 截图。成功、失败、超时或 Ctrl+C 都关闭浏览器、临时服务和隧道，并删除临时数据库及素材；输出截图和报告保留供检查。强制 SIGKILL 或主机断电无法执行清理。

报告包含源文档 revision、构建来源、素材来源计数、截图范围、图片尺寸、加载/渲染错误与警告。浏览器只允许访问临时实例的 GET/HEAD，不访问生产、外部地址或其他本机服务。公式和 Mermaid 渲染完成、字体与图片就绪后才截图。

- `rendered:true` 表示已产生所选视口截图；`checksPassed:true` 表示未检测到加载或渲染错误，**不等于排版已经目视验收**。查看与本次修改相关的截图后结束。
- 图片失败、公式/图表错误、异常网络请求或页面错误会产生非零退出码；错误回执中的 `preview` 指向已有报告和截图，不应重新写入文档。
- 页面横向溢出和浏览器的 ResizeObserver 循环通知作为警告记录，不隐瞒，也不自动认定排版失败；结合截图判断是否影响本次目标。
- 依赖缺失、构建过期或预览失败时遵循 editing 的停止规则。可选检查不要现场安装环境或扩展为整站排障；用户要求的验收、已发现的缺陷未解决时必须如实报告。

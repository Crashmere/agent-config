# 共性问题与全局方案

这里存放可能影响多个应用的问题及统一处理方案：主机与网络、共享 Nginx、共享的发布/备份模式、运行时依赖等。在任一项目遇到这类问题时，把方案写在这里并覆盖全部受影响应用；项目 docs 只保留本项目参数和指向本文的链接，不各自复制一份流程。只属于单个应用的问题留在该项目 docs。

每条写清现象与判断条件、适用应用、处理步骤、清理与验收，以及尚未实施的改进。方案被替代时直接改写本条，历史由 Git 保存。

## 门户 API 列表与服务不一致

适用于各服务的 `docs/API.md` 和 `deploy/portal.json.apis`。门户回执成功只证明声明已加载；共享校验器检查格式、归属与资源边界，不会对照业务路由验证接口是否真实存在或完整。文档把多个接口写在同一单元格、只提取第一张表，或把同一路径的 action 当成独立接口，都会留下错误或遗漏，即使文件已成功同步。

以当前服务的路由注册及处理函数为准核对方法、内部路径、参数位置、返回值和鉴权说明。遍历全部路由文件，也检查循环注册的接口；媒体的 main/thumb 等受限变体分别列出。项目接口表每行只写一个方法与路径，路径字段不包含查询串、顿号、第二个方法或 body action；参数与动作写入说明。门户声明与接口表逐项比较，补齐遗漏并移除不存在或重复的条目，不直接从叙述文本按空格截取路径。

修正来源文件后运行共享 `validate-portal.py`，并另外对照实现检查条目集合与语义；格式校验不能替代后者。只改说明时，先确认相关路由代码与线上版本一致，再按 [门户发布协议](portal.md#共用校验和发布协议) 运行 `make portal`，文档使用 `sync-docs.sh <项目名>` 同步。核对门户实际加载哈希与文档来源，不为文档修正重启业务服务，也不通过生产写请求验证列表。

当前没有自动比较各业务路由与声明内容的发布门禁；修改接口的 agent 仍需完成上述核对。遇到尚未发布的功能，应随对应程序版本发布声明，不能提前把源码中的新接口描述成线上已可用。

## 统一认证误拦大请求

现象：业务请求返回 500，Nginx error.log 同时出现 `client intended to send too large body`、`subrequest: "/_portal_device_check"` 和 `auth request unexpected status: 413`，应用 journal 没有对应请求。2026-10-01 在 RecipeBox 上传约 4.4 MiB 照片时确认，并在隔离 Nginx 复现：1 MiB 通过，多 1 字节即失败。

原因：业务 location 的 `client_max_body_size` 不会传给认证子请求的 location；`/_portal_device_check` 原来继承 Nginx 默认 1 MiB。即使配置了 `proxy_pass_request_body off` 和清空 `Content-Length`，Nginx 仍会在进入代理阶段前依据原请求长度检查这个上限。认证子请求的 413 不是 auth_request 接受的认证结果，最终对客户端表现为 500。

| 应用 | 原有入口和程序上限 | 影响 |
| --- | --- | --- |
| RecipeBox、FabricWorld | Nginx 26 MiB，单张图片 25 MiB | 超过 1 MiB 的正常图片可能被误拦 |
| Yuyan | Nginx 26 MiB，单张图片 25 MiB，JSON 16 MiB | 大图片与大文档保存均可能被误拦 |
| Ledger | Nginx 与 JSON 均为 2 MiB | 1–2 MiB 的请求无法到达业务校验 |
| FeeTable | Nginx 2 MiB，JSON 64 KiB | 正常业务输入不受影响；同样继承共享认证 |
| ServerPortal | Nginx 与 JSON 均为 1 MiB，自行认证 | 不经过该子请求，不受此问题影响 |

修正只放在共享 `assets/nginx-portal-auth.conf` 的 `location = /_portal_device_check` 内：设置 `client_max_body_size 0;`，保留 `internal`、`proxy_pass_request_body off`、空 `Content-Length` 和 Cookie 校验。业务 location 与后端继续执行各自大小上限；不能在整个 http/server 层取消限制，也不能通过豁免业务 API 认证来绕开故障。

应用前使用全部现有 location、独立回环 Nginx 和合成认证/业务上游，验证各站正常与大请求、无凭据/伪造凭据、超过业务入口上限、认证故障、Cookie 续期，以及外部不能直接访问认证内部路径。确认业务上游收到的字节数与哈希一致，认证上游不收到请求体；隔离检查无需写入真实业务。按授权表安装到 `/etc/nginx/snippets/portal-auth.conf`，保留旧配置，`nginx -t` 成功后平滑 reload；失败恢复旧配置。随后核对六站健康、公开图标 GET/HEAD、未授权页面跳转及 API 拒绝。源码、服务器运行配置和 `/opt/server-context` 副本须一致，部署状态以 [current-state](current-state.md#门户与统一认证) 为准。

## 统一认证的 Cookie 续期

五个业务应用通过 Nginx auth_request 检查设备；子请求中的 Set-Cookie 不会自动成为业务响应头。共享 assets/nginx-portal-auth.conf 使用 auth_request_set 取得该头，再由 add_header Set-Cookie ... always 转发，门户自身直接续期。匿名、伪造、过期和撤销凭据不得收到续期 Cookie；不降低 Secure/HttpOnly/SameSite=Strict/Path=/ 属性。

应用 location 新增自己的 add_header 会覆盖上层整组 add_header 继承，可能使持续使用该应用也无法续期。变更时在该层显式保留共享续期头，并核对其他共享响应头。运行 scripts/test-cookie-renewal.py --locations /etc/nginx/app-locations --auth <待部署的共享认证文件>，在独立回环 Nginx 与合成上游验证有效请求恰好续期一次、无效请求不续期；脚本当前覆盖五个业务应用，新增应用时同步扩充案例。不要为此临时放宽生产认证或向测试日志输出真实设备凭据。

## 统一认证后 iPhone 桌面图标缺失

诊断：HTTPS 资源地址和已有 PNG 本身正常，五个业务应用的图标原来也继承了设备认证。访问日志可见 iPhone 的 Ledger 页面图标/manifest 返回 200，独立的 icon-192.png 请求返回 401。不能假定系统添加桌面时会携带当前浏览器的 Cookie。

| 应用 | 图标配置 |
| --- | --- |
| Ledger | 180 px touch icon、192/512 px manifest 图标及公开 manifest，精确 GET/HEAD 例外 |
| FeeTable | 180 px touch icon，Vite 哈希路径按三个品牌图标名称匹配 |
| FabricWorld | 180 px touch icon、favicon.ico 与项目 SVG，精确 GET/HEAD 例外 |
| RecipeBox | 180 px touch icon、favicon.ico 与项目 SVG，精确 GET/HEAD 例外 |
| Yuyan | static/favicon.svg 与补充的 static/apple-touch-icon.png，精确 GET/HEAD 例外 |
| ServerPortal | 公共 static/favicon.svg 与补充的 static/apple-touch-icon.png，由 Web 层提供 |

处理：各业务项目自己的 nginx-location.conf 只对指定品牌图标（Ledger 还包括公开 manifest）关闭 auth_request，限制为 GET/HEAD；FeeTable 只匹配三个图标名称及其构建哈希。不得开放整个 assets/static、用户上传媒体或 API。Yuyan 与门户从已有 SVG 生成不透明的 180×180 PNG，并在所有页面 head 中声明 apple-touch-icon；不改变它们的登录、Cookie 或业务数据行为。

新增/修改图标时核对 HTML 的真实 href、构建后路径、PNG 尺寸、Content-Type、匿名请求和查询版本参数；部署前运行 scripts/test-public-icons.py（参数见 --help），在独立回环 Nginx 和合成上游验证规则。此脚本的五个服务图标案例需随图标路由更新；门户静态文件由 Web 自身提供，还要检查 /portal/api/overview 未登录仍返回 401。真实 iPhone 添加桌面的最终效果仍需用户确认，不能从服务器检查推断。

六站的图标与 HTML head 已随当前程序上线，匿名图标规则由各项目的 location 维护；修改规则后先通过 nginx -t 再 reload。当前部署状态见 current-state，后续项目默认按 conventions 配齐图标。

后续新网站必须从首次交付配齐上述配置，完整规范见 [网站图标约定](conventions.md#网站图标与手机桌面入口)。通用 `scripts/check-site-icons.py` 从真实 HTML 自动发现图标和 manifest，核对匿名 GET/HEAD、类型、文件签名与 PNG 尺寸；构建哈希变化无需更新中央列表。

手机验收应先在浏览器完成认证并回到对应应用页面，再添加到桌面；不要在统一登录页创建应用快捷方式。已有快捷方式可能保留旧图标，需要重新添加。桌面应用如果再次要求设备授权，按正常流程登录，不降低 Cookie 安全属性。Apple 的 PNG/页面图标规则见 [Configuring Web Applications](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html)。

## root 采集进程无法切换应用用户

ServerPortal 的 root 采集器使用非 root 主组 serverportal，以便 Unix socket 仅向 Web 用户开放。当前主机上，此组合叠加 NoNewPrivileges 与 RestrictAddressFamilies/LockPersonality 时，进程 CapEff/CapPrm 缺少 CAP_SETUID；runuser 报 cannot set user id: Operation not permitted，原生备份无法开始。直接以 root 在终端运行成功不能证明 unit 内可用。

在采集器 unit 明确配置 AmbientCapabilities=CAP_SETUID，保留其他沙箱项；源码在 ServerPortal deploy/serverportal-agent.service。现场已对照验证主组、seccomp 属性和 capabilities，并通过同等沙箱执行原生快照。固定应用用户运行的现有五个备份 unit 无需改动。后续验证必须从正式采集器发起备份，不只检查 id/true。

## HTTPS 页面能打开但保存返回 403

适用 Ledger、FeeTable、FabricWorld、RecipeBox：TLS 在共享 Nginx 终止，Go 看到本机 HTTP；原来只检查 r.TLS，会把浏览器的 HTTPS Origin 判成跨站。四个项目已统一修复，详见 [共享 HTTPS 的代理信任边界与验收](https.md)。只修改 Nginx 证书不足以完成迁移，也不能通过删除 Origin 校验或放开 CORS 解决。应用只监听回环，Nginx 覆盖 X-Forwarded-Proto，应用仅接受回环对端的单个合法值；回归覆盖 IPv4/IPv6、直接 TLS、跨站与伪造头。

## iPhone 主屏幕页面顶部发虚

用户反馈：通过 iPhone Chrome 添加到主屏幕后，Ledger、FeeTable、FabricWorld、RecipeBox 靠近时间、电量的顶部区域发虚，Yuyan 正常。代码上的关键差别是定位方式：Yuyan 使用 `position: sticky; top: 0`；三个旧服务原为普通流页头；Ledger 虽然位于内部正文滚动区之外、肉眼看起来常驻，原 CSS 仍是 `position: relative`，并不等同于 WebKit 识别的 fixed/sticky 元素。

[WebKit 工程师对顶部颜色延伸的说明](https://bugs.webkit.org/show_bug.cgi?id=301756#c2)指出，浏览器会针对视口边缘的 fixed/sticky 元素延伸实色背景，避免其上方在滚动时出现缺口；iPhone 浏览器 UI 下方本身有较柔和的模糊效果。这是对上述代码差异的机制依据，不能仅凭桌面浏览器验证就断言某台 iPhone 的主屏幕效果已修复。

处理：四个服务均使用 `sticky; top: 0` 的实色页头；Ledger 保留内部正文滚动和顶栏尺寸，另外三个保留文档滚动、路由恢复与弹窗滚动锁。新增吸顶的应用为控件/锚点定位预留顶部空间；FabricWorld 桌面照片栏的吸顶位置也移到导航下方。四个服务的视口同时对齐 Yuyan，采用默认安全区布局。用户已真机确认：仅取消 Ledger 的 `viewport-fit=cover` 仍然发虚，FeeTable 改为 sticky 后顶部正常，Ledger 随后仅把 relative 改成 `sticky; top: 0` 后也恢复正常。这验证了显式吸顶在本次问题中的作用，不能把安全区设置单独当作根因或解法。FabricWorld、RecipeBox 的同类修改已发布并通过浏览器回归，但未分别收到真机反馈。无需修改 Nginx、PWA 身份、数据库或系统状态栏设置。

验证分两层：电脑 Chromium/WebKit 只检查 320/375px 和桌面的页头位置、滚动、导航、表单及弹窗，不把它当作 iPhone 原生模糊层的复现或消除证明；最终效果需在真实 iPhone 从主屏幕重新打开、上下滚动后确认。优先完全关闭该主屏幕窗口后重开以加载新 HTML/CSS，不先清除站点数据。页面和 Ledger 的 manifest 使用 no-cache，未注册 Service Worker。仅凭代码差异不能确定具体 iOS 版本的原生渲染原因，也不应添加所谓通用“关闭系统模糊”的 CSS。

安全区行为参考 [WebKit 官方说明](https://webkit.org/blog/7929/designing-websites-for-iphone-x/)：`viewport-fit=cover` 会让页面延伸到屏幕边缘，需要开发者自行用安全区 inset 避让；这些应用目前采用默认布局。

## 官方 snap 下载过慢

服务器到 Snap Store 的单连接可能仅有几十 KB/s。2026-09-27 安装 Certbot 时，core24/snapd 已完成，但 75 MB 的 Certbot 包下载仍缓慢；问题在下载链路，并非安装后启动失败。

可在受信终端从 Snap Store 的同一下载 URL 预取准确架构与 revision 的包（必要时分段），按 Store 元数据的 SHA3-384 核对完整文件，再传到服务器独立暂存目录，命名为 certbot_<revision>.snap。在该目录执行 snap download certbot --revision=<revision> --target-directory=<目录>，它会核验并复用已有完整文件，同时下载官方 assertion 链。确认生成 .assert 后，取消本次尚未完成的重复下载并等其结束，然后 snap ack <文件.assert>、snap install <文件.snap> --classic；绝不能使用 --dangerous 跳过签名。检查版本、发行者、stable 跟踪与续期 timer 后清理这些明确的安装暂存文件，保留回退配置。

此方法只替换文件传输，仍由官方签名和 snap 管理安装、更新。不要删除或改写 snapd 内部缓存、partial 文件或状态数据库；如服务真正 failed，先按日志排障。

## systemd 沙箱下照片硬链接备份失败

适用 FabricWorld、RecipeBox，以及今后任何“在备份目录里硬链接数据文件”的应用；Ledger、FeeTable 只备份 SQLite，不受影响。FabricWorld、RecipeBox 已于 2026-09-24 按下述方法修复并验证；Yuyan 于 2026-09-26 安装时即按此配置，并通过 unit 验证。

现象：`<app>-backup.service` 每次 failed，journal 为 `hard-link media backup: link ... invalid cross-device link`。安装时用 `runuser` 手动做的首份备份不经过 unit 沙箱，不会暴露这个问题；两应用因此从第一次定时运行起连续失败了 5 天才被发现。

原因：unit 使用 `ProtectSystem=strict` 和 `ReadWritePaths=/opt/<app>/data /opt/<app>/backups`，systemd 把两个目录各自绑定挂载成独立挂载点。Linux 不允许跨挂载点建硬链接（即使底层是同一文件系统），返回 EXDEV。

修复：备份 unit 使用 `ReadWritePaths=/opt/<app>`，让 data 与 backups 处于同一个可写挂载点。`/opt/<app>` 下其余内容由 root 所有，应用用户按文件权限本来就不能写，实际写入范围不变。改项目仓库 `deploy/<app>-backup.service` 并推送，安装到 `/opt/<app>/config/` 后 `systemctl daemon-reload`；常驻服务 unit 不需要改。失败的运行不会留下不完整的备份目录，无需清理。

验证：`systemctl start <app>-backup.service` 后 `systemctl show <app>-backup.service -p Result` 为 success；新的 `daily-*` 目录含 `manifest.json`，其中照片的硬链接数（`stat -c %h`）大于 1。新增应用启用备份 timer 后，也要像这样通过 unit 实际运行一次，不能只用 `runuser` 手动备份代替。

## Go 程序返回的 JavaScript 没有被 Nginx 压缩

适用在应用 location 中用 `gzip_types` 开启压缩的应用，目前只有 Yuyan；Ledger、FeeTable、FabricWorld、RecipeBox 没有设置 `gzip_types`，沿用 nginx.conf 默认只压缩 HTML，不受影响。以后任何 Go 应用开启 `gzip_types` 时都要按此配置。

现象：CSS、JSON 响应带 `Content-Encoding: gzip`，`.js` 没有。Yuyan 从安装起就是这样，2026-09-26 发布单页应用后才发现：应用脚本原样传输 297 KB（压缩后约 100 KB），编辑器分块约 930 KB（压缩后约 290 KB），按服务器约 0.5 MB/s 的下行速度多等 1 秒以上。

原因：Go 的 `http.FileServer` 按扩展名把 `.js` 返回为 `text/javascript; charset=utf-8`，而 `gzip_types` 只写了 `application/javascript`。

处理：在应用自己的 location 中让 `gzip_types` 同时包含 `text/javascript` 与 `application/javascript`。改项目仓库的 `deploy/nginx-location.conf` 并推送，安装到 `/opt/<app>/config/nginx-location.conf` 后 `nginx -t`，再 `systemctl reload nginx`；不需要改共享 server。

验收：`curl -sI -H 'Accept-Encoding: gzip'` 请求应用的一个 `.js` 资源，返回 `Content-Encoding: gzip`；reload 后逐个核对五个应用的直连、代理健康检查与深链接。Yuyan 已于 2026-09-26 按此修复并验证。

## 发布后旧标签页的动态模块加载失败

带内容哈希的前端分块随 Go 程序一起替换后，已打开的标签页仍可能请求上一版的懒加载文件。2026-09-28 在 Yuyan 确认：Nginx 日志里的 Mermaid 核心、依赖分块和代码阅读模块均返回 404，而当前 manifest 指向的新文件存在；这是版本引用失效，不能当成图表语法错误。

排查时先从浏览器或访问日志取得准确文件名，核对当前构建清单与回环响应；404 表示文件不存在，401 或登录页应查统一认证，连接错误应查网络。不要凭动态 import 的错误文字判断 Mermaid 语法，也不要为恢复脚本加载放开静态目录鉴权。

页面外壳必须重验证，哈希资源可长期缓存。单纯清空 JavaScript 的加载 Promise 无法清除浏览器记录的失败模块；应提供明确的整页刷新入口。编辑表单先等待上传和保存完成，保存期间的新输入也必须计入；失败或冲突时保留页面和草稿，不能直接刷新。监听分块加载失败时保留原 Promise 的拒绝，避免调用者误以为模块已成功加载；不能仅在路由层处理，图表和语言模块还有嵌套 import。

当前范围核对：Yuyan 采用全局提示和保存后刷新，浏览器用真实 404 覆盖核心与嵌套分块；Ledger 的路由懒加载已有错误组件和“重新加载页面”入口；FeeTable、FabricWorld、RecipeBox 的当前应用源码未使用动态 import；ServerPortal 使用内嵌静态脚本，没有同类懒加载链。此次不改变各应用的发布脚本、资源目录或共享 Nginx。以后引入懒加载时同时验证旧标签页、加载失败及未保存输入的恢复行为。

## 新应用首次文档同步找不到目录

`sync-docs.sh` 对新应用应直接创建 `/opt/<app>/docs`。旧实现先执行 `find` 扫描 AppleDouble 文件，目标目录尚不存在时返回非零，因 `pipefail` 在安装文件前中断；服务本身和已完成目标不受影响。

共享脚本现在只对已存在目录进行预扫描，首次同步由后续 `install -D` 创建目标目录；`--check` 也允许新目标不存在并报告 BEHIND。既有目录的读取错误继续报错，不用 `|| true` 隐藏故障。2026-10-07 在 AICalendar 的真实首次文档同步中验证，已有项目使用同一流程。修复后只重试未完成目标，无需重新发布程序。

## 本机发布失败

当前发布入口、身份、产物复用和回退统一见 [本机发布](release.md)。上传失败先检查本机 SSH、网络和发布日志，校验通过之前服务继续运行；不要为网络失败反复停服。声明失败使用 make portal 单独修复。

如果日志已显示 `Deployed`，之后才在公网 HTTPS 检查中超时，程序可能已经发布成功。先核对 `current-commit`、unit/回环健康与本机 `last-deployment.json` 的 `program`，再单独重试未授权 API 的只读检查，预期 401；成功后补记本地发布回执，不重新部署程序。2026-09-30 门户发布已按此处理。

维护电脑新建 SSH 连接偶发超时时，先用短 `ConnectTimeout` 做只读连通检查；文档同步可临时使用 OpenSSH ControlMaster 复用已建立的连接，仍使用原 SSH 别名、身份和主机指纹校验，结束后关闭临时连接。连接超时本身不足以判断应用或服务器故障，不因此重启服务或更改鉴权。

## 备份与发布历史持续占用磁盘

适用全部已登记应用；2026-10-01 核对了运行版本对应代码、现场发布脚本、目录、timer 和最近任务结果。当前保留机制如下，不能把 daily 的 14 份限制推广到整个 backups 目录。

| 数据 | 当前机制与增长条件 |
| --- | --- |
| 业务应用 `daily-*` | 新备份成功后仅保留最新 14 份完整 daily；份数受控，单份大小仍随数据库和素材增长 |
| 全部应用 `before-deploy-*`、`releases/` | 每日 05:00 按 [发布保留策略](retention.md) 留 5 份完整备份、3 次成功发布并保护当前版本和对应备份；忙碌跳过 |
| manual、迁移/恢复前快照、`/opt/backup-exports` | 无自动轮换，生成后一直保留；不按名称推断可以删除 |
| ServerPortal `exports/` | 手动生成完整包或旧增量链；无自动过期清理，旧增量依赖父链 |
| FabricWorld、RecipeBox 数据内清理 | daily 先删除超过 30 天的回收站与已移除媒体、超过 24 小时的未绑定/孤立上传和 upload 暂存，再清理超过 7 天的普通幂等结果；FabricWorld 的 Ledger 来源记录长期保留。存活业务记录的修改历史无独立轮换 |
| Yuyan 数据内历史和素材 | 历史保留 30 天，每天北京时间 03:00 清理、不保底保留，停机后启动补跑；当前与回收站正文独立保留，回收站需手动清空。图片/附件最后引用消失后连续一小时才回收，每分钟扫描；历史过期后重新开始宽限期，重新引用/上传重置计时。已有备份按自身策略保留；备份与回收通过目录锁协调，详见 Yuyan OPERATIONS |
| Ledger、FeeTable 删除 | Ledger 软删除记录长期保留；FeeTable 直接删除记录。SQLite 删除释放的页可复用，不保证文件立刻变小，不自动对正式库做 VACUUM |
| 系统日志和临时目录 | Nginx daily/14 份并压缩，rsyslog weekly/4 份；journald 按默认空间上限轮换；tmpfiles 默认 /tmp 10 天、/var/tmp 30 天并有系统排除项。它们不清理 /opt 应用历史 |

门户仅为业务应用已登记的 backups/releases 提供手动候选、预览和确认；保护当前运行版本、最近两项及未完成/未知格式，执行时再次核对发布锁和备份服务。它不是自动调度，也不覆盖门户自身发布历史、导出包及 root 维护暂存目录。三个媒体应用的每日轮换不会回收异常中断留下的无 manifest 目录；正常失败会由应用尽力清理，残留需要先核对是否仍被使用。

排查时先查 `df -h /`、各应用 backup service 的 Result/最近执行时间和 `systemctl list-timers --all`，再统计各目录实际磁盘块与文件数。FabricWorld、RecipeBox、Yuyan 的媒体与备份用硬链接共享 inode：多个独立 du 结果相加会重复计数，一次跨目录 du 又会把共享块归到先访问的目录。评估可回收空间时以正式 data 为先去重，再算备份额外占用；删除某一链接不代表其全部逻辑大小会释放，历史备份也可能继续保留已从正式数据移除的照片。

2026-10-01 用户已授权实施 [发布材料自动保留](retention.md)；手工里程碑、门户导出完整链和业务历史仍须单独安排。自动任务只处理有可信来源的已完成批次，检查其 journal 中的保护/跳过原因，不把保留数量大于 3/5 直接视为轮换失效。主机另有 [30 天云备份](current-state.md#云备份)，其过期规则不会清理源目录，原生一致性备份仍需保留。

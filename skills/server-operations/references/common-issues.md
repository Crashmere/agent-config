# 共性问题与全局方案

这里存放可能影响多个应用的问题及统一处理方案：主机与网络、共享 Nginx、共享的发布/备份模式、运行时依赖等。在任一项目遇到这类问题时，把方案写在这里并覆盖全部受影响应用；项目 docs 只保留本项目参数和指向本文的链接，不各自复制一份流程。只属于单个应用的问题留在该项目 docs。

每条写清现象与判断条件、适用应用、处理步骤、清理与验收，以及尚未实施的改进。方案被替代时直接改写本条，历史由 Git 保存。

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

新增/修改图标时核对 HTML 的真实 href、构建后路径、PNG 尺寸、Content-Type、匿名请求和查询版本参数；部署前运行 scripts/test-public-icons.py（参数见 --help），在独立回环 Nginx 和合成上游验证规则。此脚本的五个服务图标案例需随图标路由更新；门户静态文件由 Web 自身提供，还要检查 /portal/api/overview 未登录仍返回 401。本次隔离检查共 132 项通过，临时进程与目录已清理；Yuyan 构建、make test 与门户 Web race 测试通过。真实 iPhone 添加桌面的最终效果仍需用户确认，不能从服务器检查推断。

2026-09-28 用户已确认六站上线及后续项目默认配置。Yuyan、门户通过 CI 发布包含 PNG 和 head 的程序；其余四个业务程序无需重发，只安装各项目的 location 配置并在 nginx -t 通过后 reload。当前部署状态见 current-state，验证结果见 ServerPortal docs/VERIFICATION.md。

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

## GitHub runner 版本固定

GitHub 的 `ubuntu-latest` 从 2026-10-19 起迁移到 Ubuntu 26，会同时改变五个应用 CI 中的系统包、编译环境和 Playwright 依赖安装。2026-09-26 起五个应用的检查与发布作业都固定为 `runs-on: ubuntu-24.04`，每个仓库各推送一次并完成发布和健康检查。

升级时统一处理：在一个应用的分支上改为新版本（如 `ubuntu-26.04`），确认检查、端到端测试（Yuyan 的 `playwright install --with-deps`）和构建产物在服务器上正常运行后，再逐个修改其余应用；不要改回 `ubuntu-latest`。GitHub 宣布 24.04 退役前完成。

## GitHub 上传过慢时的备用发布

五个应用都由 GitHub 托管 runner 构建，再经受限 SSH 身份把程序通过 stdin 交给 root 管理的 `/opt/<app>/bin/deploy-release.sh`。Ledger、FeeTable、FabricWorld、RecipeBox 的脚本只等待 90 秒上传（`timeout 90 head -c ...`）；Yuyan 从安装起就上传 gzip 压缩后的程序，并等待 600 秒。runner 位于境外 Azure，到服务器的跨境线路可能突然变慢。2026-09-24 实测：同一 17.7 MB 程序此前 CI 上传约 8–10 秒，当天三次只有约 30–60 KB/s；同时服务器负载、网卡、防火墙正常，境内上传 3.5 秒完成，GitHub 状态页无故障。原因在跨境线路，不是应用或服务器配置。

遇到上传超时不反复重跑发布作业，直接由管理员从受信终端把同一提交的 CI 产物交给同一个发布脚本。锁、哈希校验、停服备份、候选检查/迁移、原子替换、健康检查和失败回退都与 CI 发布相同。

### 判断条件

以下全部成立才使用；哈希不符、候选 check/migrate 失败、健康检查失败或回退信息等其他错误先排查原因，不用本方案绕过。

- 发布作业的 SSH 步骤以 exit code 124 结束，耗时约 90–100 秒（Yuyan 的上传时限为 600 秒）。
- 该应用最新发布目录 `result` 为 failed 且没有 `metadata`：脚本在上传阶段中止，从未停服，也没有 before-deploy 备份。
- `current-commit` 仍是旧提交，服务 active、健康检查正常。
- 待发布提交仍是 main 最新提交，且对应的测试/构建作业成功。若其后只有带 `[skip ci]` 的纯文档提交，先 fetch 并逐文件确认差异仅在未参与构建的文档中，代码、依赖、资源、嵌入文件、构建和发布配置均相同，才可补发原提交的同次 CI 产物；运行版本仍记录真实产物的原源码提交，文档副本同步最新文档提交。任一构建输入有变化就不能用此例外。

### 各应用参数

| 应用 | 产物来源 | artifact / 文件 | 验收路径 |
| --- | --- | --- | --- |
| Ledger | 失败的 `CI and deploy` run 本身 | `ledger-linux` / `ledger-linux-amd64` | `/ledger/healthz`、`/ledger/search` |
| FeeTable | 失败的 `CI and deploy` run 本身 | `feetable-linux` / `feetable-linux-amd64` | `/feetable/healthz`、`/feetable/tables/1` |
| FabricWorld | 失败的 `CI and deploy` run 本身 | `fabricworld-linux` / `fabricworld-linux-amd64` | `/fabricworld/healthz`、`/fabricworld/new` |
| RecipeBox | 失败的 `CI and deploy` run 本身 | `recipebox-linux` / `recipebox-linux-amd64` | `/recipebox/healthz`、`/recipebox/new` |
| Yuyan | 失败的 `CI and deploy` run 本身 | `yuyan-linux` / `yuyan-linux-amd64` | `/yuyan/healthz`、`/yuyan/search` |

Yuyan 的发布脚本读取 gzip 流：第 3 步改为 `gzip -9 -c "$tmp/yuyan-linux-amd64" | ssh ali '/opt/yuyan/bin/deploy-release.sh <commit> <sha256>'`，SHA-256 仍为未压缩程序的值。

下列命令中 `<app>` 为小写应用名，`<commit>` 为完整 40 位提交号；不要上传本地构建的程序。

### 步骤

1. 核对现场，并从受限入口的 sudo 日志取出失败发布传入的 SHA-256（第二个参数）：

   ```sh
   ssh ali 'cat /opt/<app>/current-commit; systemctl is-active <app>
     d=$(ls -1t /opt/<app>/releases | head -1); echo "$d"; cat "/opt/<app>/releases/$d/result"; ls "/opt/<app>/releases/$d"
     journalctl --since today --no-pager | grep "deploy-release.sh <commit>" | tail -1'
   ```

2. 下载产物到新的临时目录并核对。本地 SHA-256 必须等于 sudo 日志中的值；五个应用的发布作业都直接使用同一次检查构建的 artifact。服务器上已安装的脚本须与该项目仓库 `deploy/deploy-release.sh` 哈希相同。

   ```sh
   tmp=$(mktemp -d)
   gh run download <run-id> -R Crashmere/<Repo> -n <artifact> -D "$tmp"
   shasum -a 256 "$tmp/<file>" /path/to/<Repo>/deploy/deploy-release.sh
   ssh ali 'sha256sum /opt/<app>/bin/deploy-release.sh'
   ```

3. 以管理员身份发布。成功时脚本输出 `Deployed <commit>`；刚启动时可能出现一次本机端口连接失败，是等待健康前的探测。

   ```sh
   ssh ali '/opt/<app>/bin/deploy-release.sh <commit> <sha256>' < "$tmp/<file>"
   ```

4. 只读验收：`current-commit` 为新提交，服务 active，直连 `/healthz` 与上表验收路径正常，按改动核对页面或 API，不写测试数据。
5. 清理：逐个确认本次超时留下的发布目录 `result` 为 failed 且没有 `metadata` 后，按完整目录名删除；删除本地 `$tmp`。保留成功的发布目录（含 `previous`）和 before-deploy 备份。

失败的 Actions run 会继续显示失败，这是预期结果。发布后不要再重跑它，否则会用同一程序再停服、备份一次。

### 尚未实施的改进

已出现：2026-09-24（多个应用）；2026-09-26 白天（RecipeBox，本机从 GitHub 下载 artifact 也曾 TLS 握手超时一次，重试成功）；2026-09-26 晚间逐个发布固定 runner 的提交时，Ledger、FeeTable、RecipeBox 超时，FabricWorld 18 秒上传成功，Yuyan（压缩、600 秒）正常，本机下载 RecipeBox artifact 读超时一次，重试成功。Yuyan 已经压缩上传并放宽到 600 秒。2026-09-27 的 HTTPS 发布中，另外四个应用的 CI 检查也全部通过，但上传均在 90 秒处失败；已按上述流程逐个补发同次 CI 产物并核对线上版本。Yuyan 的压缩上传正常完成。另四个应用仍经常超时，可照 Yuyan 的 `deploy/deploy-release.sh` 修改它们由 root 管理的发布脚本、测试与 CI，属于授权表中的先确认事项。

下载重试用新的临时目录：在 zsh 里清空空目录的 `rm -rf "$tmp"/*` 会因通配符没有匹配而中止脚本。

## 统一设备认证后的 CI 健康检查

五个业务服务的公网健康接口同样受 ServerPortal 保护。CI 未携带设备凭据时，不能再以公网 /healthz 返回 200 作为发布条件；该旧检查会在业务已成功发布后因 401 错误地标红。各应用发布脚本继续检查回环直连和回环 Nginx 页面，CI 的公网 HTTPS 检查验证 401，确认认证边界正常。不要为 CI 豁免公网健康接口或把设备口令放进工作流。

声明发布失败时，先核对 config/portal-source.json 与 /registry 回执。校验规则来自本技能 scripts/validate-portal.py；门户保留上一份有效内存配置，发布工具失败会恢复原声明。修正源码后可运行 portal_only=true，完成同步而不重启业务。具体协议见 [门户维护](portal.md)。

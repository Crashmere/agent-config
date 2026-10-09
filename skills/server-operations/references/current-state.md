# 当前服务器与应用清单

AICalendar 网页改版与备份范围调整最后核对：2026-10-09；全部七站健康与认证入口最后核对：2026-10-07（北京时间）。主机基础清单核对：2026-09-28，主机、五个业务应用、ServerPortal 及共享 HTTPS 入口均已现场复查，用户已确认正式设备登录成功。网页键盘与焦点策略于 2026-09-30 更新并发布，见下方共享配置。备份与数据保留于 2026-10-01 只读复核，另确认已运行的阿里云 Cloud Backup，见下方云备份。这是可覆盖更新的当前快照，不是历史日志。易变版本和状态须重新查；未列出的资源不能视为不存在。

## 主机

| 项目 | 当前状态 |
| --- | --- |
| 连接 | 本地 OpenSSH 别名 `ali`；管理员 root，端口 22；真实地址从受信 SSH 配置取得，不写入公开仓库 |
| 平台 | Alibaba Cloud ECS / KVM，x86_64，Ubuntu 26.04.1 LTS |
| 资源 | 2 vCPU，约 1.7 GiB 可见内存，40 GiB ext4 根盘；无 swap，无独立应用数据挂载盘 |
| 内核 | 核对时 7.0.0-30-generic；不是重建时必须固定的版本 |
| 时间 | Asia/Shanghai；chrony 提供时间同步，NTP 已同步 |
| SSH | 公钥认证开启、密码认证关闭、允许 root 登录 |
| HTTPS | Nginx 1.28.3，443 TLS 1.2/1.3 + HTTP/2；Let’s Encrypt 可信公网 IPv4 证书，无域名。80 提供 ACME 并 308 跳转；仅回环保留 HTTP 代理检查 |
| 主机防火墙 | UFW inactive；不能据此推断所有 netfilter 规则或云侧防护 |
| 云安全组 | SSH/HTTP/HTTPS 已从外网验证可达，未通过云 API 审计完整规则；未来改规则前另行核实 |
| 包源 | Ubuntu 签名仓库，当前使用阿里云内网镜像；换供应商时不要照抄该镜像地址 |

## 已部署应用（共享变更必须逐行核对）

| 应用 / 源码 | URL 前缀 → 本机监听 | 目录 / 身份 | systemd | 文档与验证 |
| --- | --- | --- | --- | --- |
| Ledger / [Crashmere/Ledger](https://github.com/Crashmere/Ledger) | `/ledger/` → `127.0.0.1:18080` | `/opt/ledger`；运行 `ledger`，发布 `ledger-deploy` | `ledger.service`、`ledger-backup.service`、`ledger-backup.timer` | `/opt/ledger/docs/README.md`；直连 `/healthz`、代理 `/ledger/healthz`、深链接 `/ledger/search` |
| FeeTable / [Crashmere/FeeTable](https://github.com/Crashmere/FeeTable) | `/feetable/` → `127.0.0.1:18081` | `/opt/feetable`；运行 `feetable`，发布 `feetable-deploy` | `feetable.service`、`feetable-backup.service`、`feetable-backup.timer` | `/opt/feetable/docs/README.md`；直连 `/healthz`、代理 `/feetable/healthz`、路由壳 `/feetable/tables/1`（浏览器验收用实际存在的月表或首页） |
| FabricWorld / [Crashmere/FabricWorld](https://github.com/Crashmere/FabricWorld) | `/fabricworld/` → `127.0.0.1:18082` | `/opt/fabricworld`；运行 `fabricworld`，发布 `fabricworld-deploy` | `fabricworld.service`、`fabricworld-backup.service`、`fabricworld-backup.timer` | `/opt/fabricworld/docs/README.md`；直连 `/healthz`、代理 `/fabricworld/healthz`、深链接 `/fabricworld/new` |
| RecipeBox / [Crashmere/RecipeBox](https://github.com/Crashmere/RecipeBox) | `/recipebox/` → `127.0.0.1:18083` | `/opt/recipebox`；运行 `recipebox`，发布 `recipebox-deploy` | `recipebox.service`、`recipebox-backup.service`、`recipebox-backup.timer` | `/opt/recipebox/docs/README.md`；直连 `/healthz`、代理 `/recipebox/healthz`、深链接 `/recipebox/new` |
| Yuyan / [Crashmere/Yuyan](https://github.com/Crashmere/Yuyan) | `/yuyan/` → `127.0.0.1:18084` | `/opt/yuyan`；运行 `yuyan`，发布 `yuyan-deploy` | `yuyan.service`、`yuyan-backup.service`、`yuyan-backup.timer` | `/opt/yuyan/docs/README.md`；直连 `/healthz`、代理 `/yuyan/healthz`、深链接 `/yuyan/search` |
| ServerPortal / [Crashmere/ServerPortal](https://github.com/Crashmere/ServerPortal) | `/portal/` → `127.0.0.1:18085` | `/opt/serverportal`；Web 用户 `serverportal`、root Unix socket 采集器 | `serverportal.service`、`serverportal-agent.service` | `/opt/serverportal/docs/README.md`；回环 `/healthz`；公网根跳转、登录与受保护 API |
| AICalendar / [Crashmere/AICalendar](https://github.com/Crashmere/AICalendar) | `/aicalendar/` → `127.0.0.1:18086` | `/opt/aicalendar`；运行 `aicalendar`，发布 `aicalendar-deploy` | `aicalendar.service`、`aicalendar-backup.service`、`aicalendar-backup.timer` | `/opt/aicalendar/docs/README.md`；直连 `/healthz`、代理 `/aicalendar/healthz`、页面 `/aicalendar/` |

| 应用 | 数据 | 每日备份（北京时间，+0–5 分钟随机，留 14 份） | 发布 | 其他 |
| --- | --- | --- | --- | --- |
| Ledger | SQLite | 03:00，一致性快照 | 本机 make deploy | — |
| FeeTable | SQLite | 03:15，一致性快照 | 本机 make deploy | — |
| FabricWorld | SQLite + 照片 | 03:30，快照 + 照片硬链接 + SHA-256 清单 | 本机 make deploy | libvips；CPUQuota=100%、MemoryMax=640M；隔离恢复演练用 19082 |
| RecipeBox | SQLite + 照片 | 03:45，同 FabricWorld | 本机 make deploy | libvips；CPUQuota=100%、MemoryMax=640M、照片配额 5 GiB；演练用 19083 |
| Yuyan | SQLite（含文档模板/内容片段）+ 画板包、图片与附件 | 04:00，同 FabricWorld；清单 v2 覆盖全部登记素材，恢复兼容 v1 图片备份 | 本机 make deploy（gzip） | CPUQuota=100%、MemoryMax=384M（GOMEMLIMIT=320MiB，MemoryCurrent 含页缓存）；演练用 19084 |
| ServerPortal | 设备状态 JSON、私有配置；整机材料压缩归档 | 网页手动创建独立完整包，默认 recovery，可选 all/docs；导出包不自动轮换或由门户异机同步 | 本机构建，管理员发布 | 新包无需密钥；本机保留旧包所需 age 私钥；无任意 SQL/命令接口 |
| AICalendar | SQLite（活动、注释、导入批次、完整聊天与原始资料分块/索引） | 04:15，核心三表一致性快照，保留 14 份；用户确认完整聊天存档不备份 | 本机 make deploy | MemoryMax=192M、GOMEMLIMIT=144MiB；独立手动导入凭据；演示用 19086 |

六个业务应用的浏览器页面/API 已接入统一设备认证；授权设备可执行各自支持的数据操作。各用独立数据库、运行和发布身份，自动备份均在同盘；2026-09-27 已另取一份全应用数据归档下载到维护电脑并校验（见下方手工数据归档），应用脚本不主动异机同步，主机另有阿里云文件备份（见下方云备份）；before-deploy 备份和发布历史按 [发布材料自动保留](retention.md) 清理：最近 5 份完整备份、最近 3 次成功发布及当前版本/对应备份保护。`server-context` 是文档包，不是应用。精确流程与限制以项目 docs 为准。

AICalendar 正式库已开始保存手动导入的真实历史与完整存档；实际来源和覆盖范围通过导入客户端 `status` 与查询接口核对，不在共享文档中保存私人统计。浏览器沿用门户认证，只有 `/aicalendar/ingest/v1/` 使用本应用的独立 Bearer 凭据；服务端保存 SHA-256，令牌原文和客户端配置仅在维护电脑 Git 外的 `~/.config/aicalendar/`。导入凭据支持日历摘要导入/核验，以及完整聊天分块上传、查询和下载，不提供日历摘要 export 或网页注释编辑。手动 skill `ai-calendar-import` 在本地整理，默认先保存完整会话和原始资料、再导入摘要，并保留用户指定的来源标签；不配置自动采集。

完整存档 gzip 按 384 KiB 分块上传；同内容去重，内容变化保留新旧快照，消息全文和原始字节可取回，原文不自动过期。所有块及阅读索引仍在同一 SQLite，无新数据根或 Nginx 限制变更。核心 schema 1 保持，archive_schema 1 已显式追加；升级前旧程序备份、迁移后新旧程序 check 及旧数据不变检查通过。旧程序可回退并完整备份该库，只是不提供存档 API。每日备份、发布前快照和发布保留沿用原契约；更新后的资源声明由门户动态加载。

Yuyan 附件上传已改为流式接收且不设文件大小上限；仅其 /yuyan/api/attachments 子 location 关闭大小检查和请求体缓冲，继承认证，其余请求保留原限制。临时上传写入既有 data/assets，无新数据根；图片与附件连续一小时未被正文（含回收站）、历史、模板/片段或媒体链接引用后自动回收，每分钟扫描，重新引用/上传重置计时。状态复用 meta；备份/上传共享目录锁与回收排他锁跨进程协调，已有备份硬链接保留。旧版备份程序不可与新版回收并行，诊断使用 gc --dry-run。附件阅读预览使用只读 `/api/attachments/{id}/preview`（类型、文本与压缩包目录）和 `/attachments/{id}/content`（受限位图/PDF/音视频），延续设备认证，下载接口仍强制下载。PDF.js 资源内嵌程序并按需加载，压缩包不解压落盘；无新服务器运行时、数据目录或备份契约，接口登记随项目 portal.json 发布，详细格式与限制见 Yuyan DESIGN 23.8。

新增应用必须在两张表中各加一行，并写明健康验证。退役后从当前清单删除，仍在迁移中的旧实例必须明确标注用途，不假装已经下线。

Yuyan 已实现 Excalidraw 文档画板：包和预览复用 assets/.bin，`POST/GET /api/drawings` 与 `/drawings/{id}/preview|file` 登记于项目门户声明，沿用设备认证和普通请求大小限制，包限 12 MiB。正文/历史/模板保护包并展开图片依赖，未引用包宽限期内也保护图片；v2 备份覆盖全部素材，未知或损坏包让当轮 GC 保守停止。前端和字体随 Go 发布，不增 Node/浏览器运行时、数据根或数据库迁移。旧客户端编辑保护、导入导出与程序回退约束见 Yuyan WHITEBOARD.md。

Yuyan 历史快照保留 30 天，每天北京时间 03:00 由应用清理，不保底保留；成功状态持久化，停机后启动补跑。当前正文、回收站正文、模板与片段不受影响，历史最后引用移除后媒体重新开始一小时宽限期。编辑前与恢复前快照同样适用 30 天，历史 ID 不重用；无数据库迁移或额外系统任务，诊断使用 history-gc --dry-run。已有备份仍按各自策略保留，隔离恢复后若要提取更早历史，先只读查看、不要启动自动清理服务，详见 Yuyan OPERATIONS。

Ledger → FabricWorld 联动：新建“副业 / 纺织”支出后由用户确认，Ledger 服务端通过本机 18082 的 /api/integrations/ledger 创建布料；成功可跳转同源布料编辑页。LEDGER_FABRICWORLD_URL 归 Ledger 配置，默认本机地址；FabricWorld operations 持久记录交易来源，避免重试重复创建。两个服务仍独立数据库、备份与发布，不共享数据库权限。更新先发布 FabricWorld 再发布 Ledger；长期回退旧版 FabricWorld 前需停用联动，避免旧清理逻辑删除来源记录。精确接口、验证和恢复限制见两项目 docs。FeeTable 和共享 Nginx 不受影响。

Yuyan 首页通过只读 `/api/stats` 显示存活文档的正文总字数及各知识库卡片字数，同一次查询返回全站 `chars` 与按知识库 ID 索引的 `bookChars`，空知识库为 0；沿用设备认证及现有 `plain_text`，无数据库迁移、数据根或运行时变化，接口随项目门户声明发布。

## 门户与统一认证

ServerPortal 已上线 /portal/ 与回环 18085；公网根路径跳转到门户。六个业务应用的 deploy/portal.json 已安装到各自 config 目录。用户口令只存 bcrypt 哈希，设备凭据使用 Secure/HttpOnly/SameSite=Strict Cookie；服务端授权永久有效，现有仍有效的授权已迁移，撤销仍立即生效。Cookie 设置 400 天且随门户或业务应用的有效请求续期，浏览器实际保留时间仍受自身限制。新备份为不加密 .tar.gz；旧加密包所需恢复私钥仍在维护电脑的 Git 目录之外。共享认证 include 来自 assets/nginx-portal-auth.conf，并已转发认证子请求的 Set-Cookie；未授权页面跳转登录，API/媒体返回 401，认证故障拒绝访问。ACME 与本机发布检查继续正常。未执行生产清理。门户真实完整包和增量已生成；用户暂缓完整包下载与恢复验收，部分下载文件保留且等待进程已停止，没有自动续传任务。备份覆盖、恢复验证与当前限制见 ServerPortal docs/VERIFICATION.md 和 docs/RESTORE.md；维护规则见 [门户维护](portal.md)。

门户永久授权与紧凑布局已上线。实际程序来源从 current-commit 与 releases/metadata 读取，文档版本由 docs/SOURCE 记录。

2026-10-01 已修复共享认证子请求误拦大请求的问题：仅在 `/_portal_device_check` 设置 `client_max_body_size 0`，继续禁止转发请求体，各应用 Nginx 与程序大小上限保持。RecipeBox、FabricWorld、Yuyan 的大图片、Yuyan 的大文档及 Ledger 的 1–2 MiB 请求不再被认证层默认 1 MiB 上限误拦；FeeTable 正常输入与门户自身认证不受原问题影响。全部 location 的 48 项隔离检查、线上 51 项只读 HTTP 检查和六站图标 GET/HEAD 检查通过；Nginx 平滑重载，各应用未重启、未写入合成业务数据。根因与维护方法见 [统一认证误拦大请求](common-issues.md#统一认证误拦大请求)。

门户已改用 /opt/serverportal/registry.d 的受控链接动态加载服务，共享校验器已安装到 /opt/server-context/scripts/validate-portal.py。六个业务应用的 root 发布脚本已支持 portal-check/portal 协议；更新不再需要手改中央 registry 数组或重启采集器。声明非法时保留上一份有效配置并报错。常规本机发布同步同提交声明，make portal 只更新门户信息；各业务应用通过本机 make portal 同步声明。

## 共享配置与所有权

七站均按[网页键盘与焦点约定](conventions.md#网页键盘与焦点)维护。FeeTable、FabricWorld、RecipeBox、Yuyan、ServerPortal 和 AICalendar 已上线普通 Tab / Shift+Tab 拦截并取消控件焦点高亮，覆盖页面、表单、菜单和弹窗。Ledger 保持用户认可的现有快捷键与焦点行为；Yuyan 保留正文/代码缩进和表格单元格导航。五站本地 Chromium 与 WebKit 的页面、弹窗、窄屏及深色模式检查通过，编辑例外与菜单按键另行验证；全局 AGENTS 和七个项目入口均记录默认规则。

七站都已提供独立的 favicon 和 180×180 apple-touch-icon；业务站点只对明确品牌图标（Ledger 含公开 manifest）开放匿名 GET/HEAD，页面、API 和用户媒体继续认证。AICalendar 已通过 Chromium 桌面与 375×667 窄屏交互检查，全部七站图标匿名 GET/HEAD 检查通过；真机添加桌面的最终效果待用户确认。新增网站从首次交付起遵循 conventions 的网站图标约定。

| 实际位置 | 维护源 / 含义 |
| --- | --- |
| `/etc/nginx/nginx.conf` | Ubuntu 包基础配置，改动需记录；不是业务项目所有 |
| `/etc/nginx/sites-available/apps` | 本技能 `assets/nginx-apps.conf` 渲染公网 IPv4，共享 80/443 与回环检查 server |
| `/etc/nginx/sites-enabled/apps` | 指向上面的启用链接 |
| `/etc/nginx/app-locations/ledger.conf` | 指向 `/opt/ledger/config/nginx-location.conf`，源在 Ledger deploy |
| `/etc/nginx/app-locations/feetable.conf` | 指向 `/opt/feetable/config/nginx-location.conf`，源在 FeeTable deploy |
| `/etc/nginx/app-locations/fabricworld.conf` | 指向 `/opt/fabricworld/config/nginx-location.conf`，源在 FabricWorld deploy |
| `/etc/nginx/app-locations/recipebox.conf` | 指向 `/opt/recipebox/config/nginx-location.conf`，源在 RecipeBox deploy |
| `/etc/nginx/app-locations/yuyan.conf` | 指向 `/opt/yuyan/config/nginx-location.conf`，源在 Yuyan deploy |
| `/etc/nginx/app-locations/serverportal.conf` | 指向 `/opt/serverportal/config/nginx-location.conf`，源在 ServerPortal deploy |
| `/etc/nginx/app-locations/aicalendar.conf` | 指向 `/opt/aicalendar/config/nginx-location.conf`，源在 AICalendar deploy |
| `/etc/nginx/snippets/portal-auth.conf` | 本技能 assets/nginx-portal-auth.conf，仅在公网 443 server 引用 |
| `/opt/serverportal/registry.d/<app>.json` | 指向应用自己的 config/portal.json；受限发布协议创建和校验 |
| `/opt/server-context/scripts/validate-portal.py` | 本技能脚本，维护电脑与服务器共用的资源声明策略 |
| `/var/log/nginx/access.log`、`error.log` | 共享 HTTP/HTTPS 请求日志；journal 主要反映 Nginx 生命周期 |
| `/opt/server-context/` | 本技能的文档/模板/检查脚本副本，root 管理 |
| `/opt/AGENTS.md` | 本技能 assets/AGENTS.md 的副本 |
| `/root/AGENTS.md` | 指向 `/opt/AGENTS.md`，便于在 root 登录目录发现 |
| `/etc/update-motd.d/30-server-context` | 交互登录提示；非交互 SSH 不依赖它 |

`SOURCE` 分别位于 `/opt/server-context/` 与每个项目的 `/opt/<app>/docs/`，记录各自来源提交和同步时间。应用的 `current-commit` 记录运行程序版本，`config/portal-source.json` 记录声明来源提交与 SHA-256，两者都不代表 docs 版本；只同步文档或声明不应改写程序版本。

## 手工数据归档

2026-09-27 已按用户要求生成五个应用的当前一致性数据快照，汇总为 `ali-data-<UTC时间>.tar.gz`，通过 SSH 下载到维护电脑的 `~/ali/backups/`（位于各项目 Git 仓库之外，目录 0700、文件 0600）。这是一次手工下载，不是持续同步到维护电脑；主机另有下述阿里云文件备份。准确生成时间、各应用运行提交、校验和与恢复说明在归档旁的 metadata、verification、SHA-256 和 README 文件中；实际数据及这些清单不进入公开仓库。

归档含五个数据库、所有已登记照片/知识库图片、数据库内历史与回收站内容，并保留 Ledger 数据目录内的历史迁移快照。各应用通过自身 backup 命令生成独立在线一致性快照；不是五个应用的同一事务时点。没有运行 daily 清理或轮换，也没有停止服务。下载后核对整包 SHA-256、全部文件清单、三个图片应用的原生 manifest、六个数据库的完整性/外键及数据库登记图片的覆盖。

服务器单应用快照保留在各自 `/opt/<app>/backups/manual-ali-data-*`，汇总包和解包目录位于 root 私有的 `/opt/backup-exports/`；它们不自动轮换。打包使用 tar --hard-dereference，让归档内图片成为独立文件。只下载已完成归档，传输先保留 .part 名称，通过整包校验后再改为正式文件名；恢复先解到全新隔离目录并按包内说明验证，正式恢复另行确认。归档为数据备份，应用程序、运行配置与凭据仍按各自重建流程维护。

## 云备份

2026-10-01 从现场进程与客户端任务日志确认：阿里云 Cloud Backup 的 `hbrclient.service` 与 `hbrclientupdater.service` 已运行，目录为 `/opt/alibabacloud/hbrclient`。它独立于五个应用的 daily timer 和 ServerPortal 下载流程；不能再将“应用脚本不主动上传”表述为整机没有自动异机备份。

- 最近三个任务均于北京时间约 01:44 开始；最新任务成功完成增量备份。此时间来自运行日志，控制台计划配置未核对。
- 文件备份目标为 `/`，排除系统程序、虚拟文件系统及客户端自身；现场排除列表未排除应用的 `/opt` 目录，应用数据、daily/manual/before-deploy、releases 和门户 exports 都在扫描范围内。
- 任务记录的保留期为 30 天，快照到期时间与之相符。云端已用空间、账单、保留策略的控制台配置以及实际到期删除结果尚未独立核对；日志中的逻辑扫描量不等于云端物理占用。
- 客户端启动日志显示本地旧元数据按 15 天清理；成功任务结束时回收旧文件缓存，最新日志保留最近两代缓存。客户端目录是第三方受管数据，不按应用垃圾处理。
- 云端保留期不会删除服务器源文件。未轮换的 releases/备份持续进入新快照，增量去重不能替代源目录保留策略。云端直接扫描活跃 SQLite/WAL 也不等于应用一致性快照；恢复仍优先使用已完成的原生备份，并按项目契约验证。

## 其他软件、后台任务和已知问题

- FabricWorld 与 RecipeBox 共用图片运行依赖：Ubuntu 官方签名源 libvips-tools/libvips42t64 8.18.0 与 libheif-plugin-libde265 1.21.2。/tmp 为约 868 MiB tmpfs，图片数据与容量验证放 /opt 的持久磁盘，不能按根盘余量推断 /tmp 容量。
- 已有工具：Git 2.53.0、root 的 `/root/.local/bin/uv` 0.12.15。它们不是任何应用的运行依赖，也不要因为应用不需要就删除。PATH 中没有 Node、Go、Docker、sqlite3，也没有数据库服务或自托管 Actions runner。
- Ubuntu 的 nodejs、npm 及随它们安装的依赖（共 492 个包，含 eslint、webpack 和一批 X11/Mesa/Perl 库）已于 2026-09-26 按用户要求卸载：Node 不是任何应用的依赖，却常让开发 agent 误以为可以在服务器上构建。卸载后四个应用的直连、代理与深链接健康正常，libvips 可用。
- 系统/厂商服务包含 `aliyun`（Aliyun Assist）、`hbrclient` / `hbrclientupdater`（阿里云 Cloud Backup）、chrony、cron、sshd、journald/rsyslog、resolved、networkd、tuned、ModemManager、multipathd 等，不是应用创建的。云备份详情见上节。
- `aegis.service`（Aegis Service，阿里云安全组件）重启前长期 failed（Result=signal），2026-09-24 重启后恢复 running；若再次失败，不要归因于应用。
- 系统 timer 包括 apt-daily/upgrade、logrotate、sysstat、fstrim、文件系统检查、fwupd、MOTD/update notifier 等；unattended-upgrades 会自动装安全更新，没有配置自动重启。
- 2026-09-24 已重启以应用 libc6 更新：四个应用、Nginx 与备份 timer 均自动恢复，直连与代理健康正常，约 25 秒恢复 SSH。以后出现 /var/run/reboot-required 时，按同样方法先检查没有发布/备份在运行，重启后逐项验证。
- 发布历史与发布前快照由 `ali-release-retention.timer` 每天北京时间 05:00 自动清理，保留最近 3 次成功发布和最近 5 份完整发布前备份，并保护当前版本、对应备份及待核对失败批次。每日备份共用清理锁，业务 daily 仍保留 14 份；手工/迁移备份和门户 exports 不在自动范围。配置、私有回执目录及验收见 [发布材料自动保留](retention.md)。
- Certbot 5.8.0 使用 Certbot Project 官方 snap（latest/stable），snap 自动更新；IP 证书 apps-ip 约 160 小时有效，snap.certbot.renew.timer 自动续期，deploy hook 验证配置后重载 Nginx。首次签发、续期演练和实际 timer service 检查已通过，配置与重建见 [共享 HTTPS](https.md)。
- 没有外部可用性或证书到期告警；inspect.sh 检查证书是否至少还有 48 小时有效。

## 重新核对

```sh
ssh ali 'cat /opt/AGENTS.md'
ssh ali 'bash /opt/server-context/scripts/inspect.sh'
~/agent-config/skills/server-operations/scripts/sync-docs.sh --check    # 在本地运行：各文档副本是否与仓库一致
ssh ali 'for a in ledger feetable fabricworld recipebox yuyan aicalendar; do echo "$a $(cat /opt/$a/current-commit)"; done'
```

2026-10-07 七个应用服务均健康，AICalendar 每日备份首跑与完整性检查成功，其余备份的最近完整核对仍为 2026-10-01；failed 列表另有旧的 systemd-run 身份/快照诊断单元，不应混为当前业务或定时备份失败。出现应用或备份 unit 时先查其 journal。检查脚本不访问业务数据库、私钥或账目 API。完整命令输出可能包含公网地址、主机名、PID；只保留必要结论，不能把原始输出直接提交到公开仓库。

## 本机发布与验证

七个应用使用 [本机发布](release.md)：GitHub Actions 关闭，只备份源码与配置。原 production Secrets 和旧 CI 公钥已移除，业务发布身份信任维护电脑专用发布公钥；门户沿用管理员 SSH。历史回归套件退役，本次功能在本地按需验证，不默认保留永久测试。构建、上传与健康/备份保护由脚本执行。

门户 root 私有 releases/ 与 backups/ 保存旧程序及停写后的 data/config 快照，纳入共享 3/5 发布保留策略；私有清理回执目录也由 ServerPortal/deploy/portal.example.json 登记。用户暂缓的真实备份下载和恢复验收保持暂缓。

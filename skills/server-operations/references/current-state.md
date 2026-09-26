# 当前服务器与应用清单

最后核对：2026-09-24（北京时间），主机、应用、入口与软件版本均在当天用 inspect.sh 复查。这是可覆盖更新的当前快照，不是历史日志。易变版本和状态须重新查；未列出的资源不能视为不存在。

## 主机

| 项目 | 当前状态 |
| --- | --- |
| 连接 | 本地 OpenSSH 别名 `ali`；管理员 root，端口 22；真实地址从受信 SSH 配置取得，不写入公开仓库 |
| 平台 | Alibaba Cloud ECS / KVM，x86_64，Ubuntu 26.04.1 LTS |
| 资源 | 2 vCPU，约 1.7 GiB 可见内存，40 GiB ext4 根盘；无 swap，无独立应用数据挂载盘 |
| 内核 | 核对时 7.0.0-30-generic；不是重建时必须固定的版本 |
| 时间 | Asia/Shanghai；chrony 提供时间同步，NTP 已同步 |
| SSH | 公钥认证开启、密码认证关闭、允许 root 登录 |
| HTTP | Nginx 1.28.3（Ubuntu 包 1.28.3-2ubuntu1.11），80 IPv4/IPv6；没有配置 TLS/域名 |
| 主机防火墙 | UFW inactive；不能据此推断所有 netfilter 规则或云侧防护 |
| 云安全组 | SSH/HTTP 已可达，未通过云 API 审计完整规则；改网络前从云控制台/授权 API 核实 |
| 包源 | Ubuntu 签名仓库，当前使用阿里云内网镜像；换供应商时不要照抄该镜像地址 |

## 已部署应用（共享变更必须逐行核对）

| 应用 / 源码 | URL 前缀 → 本机监听 | 目录 / 身份 | systemd | 文档与验证 |
| --- | --- | --- | --- | --- |
| Ledger / [Crashmere/Ledger](https://github.com/Crashmere/Ledger) | `/ledger/` → `127.0.0.1:18080` | `/opt/ledger`；运行 `ledger`，发布 `ledger-deploy` | `ledger.service`、`ledger-backup.service`、`ledger-backup.timer` | `/opt/ledger/docs/README.md`；直连 `/healthz`、代理 `/ledger/healthz`、深链接 `/ledger/search` |
| FeeTable / [Crashmere/FeeTable](https://github.com/Crashmere/FeeTable) | `/feetable/` → `127.0.0.1:18081` | `/opt/feetable`；运行 `feetable`，发布 `feetable-deploy` | `feetable.service`、`feetable-backup.service`、`feetable-backup.timer` | `/opt/feetable/docs/README.md`；直连 `/healthz`、代理 `/feetable/healthz`、深链接 `/feetable/tables/1` |
| FabricWorld / [Crashmere/FabricWorld](https://github.com/Crashmere/FabricWorld) | `/fabricworld/` → `127.0.0.1:18082` | `/opt/fabricworld`；运行 `fabricworld`，发布 `fabricworld-deploy` | `fabricworld.service`、`fabricworld-backup.service`、`fabricworld-backup.timer` | `/opt/fabricworld/docs/README.md`；直连 `/healthz`、代理 `/fabricworld/healthz`、深链接 `/fabricworld/new` |
| RecipeBox / [Crashmere/RecipeBox](https://github.com/Crashmere/RecipeBox) | `/recipebox/` → `127.0.0.1:18083` | `/opt/recipebox`；运行 `recipebox`，发布 `recipebox-deploy` | `recipebox.service`、`recipebox-backup.service`、`recipebox-backup.timer` | `/opt/recipebox/docs/README.md`；直连 `/healthz`、代理 `/recipebox/healthz`、深链接 `/recipebox/new` |

| 应用 | 数据 | 每日备份（北京时间，+0–5 分钟随机，留 14 份） | 发布 | 其他 |
| --- | --- | --- | --- | --- |
| Ledger | SQLite | 03:00，一致性快照 | 推 main 自动 | — |
| FeeTable | SQLite | 03:15，一致性快照 | 推 main 自动 | — |
| FabricWorld | SQLite + 照片 | 03:30，快照 + 照片硬链接 + SHA-256 清单 | 手动 Deploy 工作流 | libvips；CPUQuota=100%、MemoryMax=640M；隔离恢复演练用 19082 |
| RecipeBox | SQLite + 照片 | 03:45，同 FabricWorld | 手动 Deploy 工作流 | libvips；CPUQuota=100%、MemoryMax=640M、照片配额 5 GiB；演练用 19083 |

四个应用都无登录，用户分别确认知址可读写（及各自的导出/删除）。各用独立数据库、运行和发布身份，全部只有同盘备份、没有异机备份；before-deploy 备份与发布历史不自动轮换。`server-context` 是文档包，不是应用。精确流程与限制以项目 docs 为准。

新增应用必须在两张表中各加一行，并写明健康验证。退役后从当前清单删除，仍在迁移中的旧实例必须明确标注用途，不假装已经下线。

Ledger → FabricWorld 联动：新建“副业 / 纺织”支出后由用户确认，Ledger 服务端通过本机 18082 的 /api/integrations/ledger 创建布料；成功可跳转同源布料编辑页。LEDGER_FABRICWORLD_URL 归 Ledger 配置，默认本机地址；FabricWorld operations 持久记录交易来源，避免重试重复创建。两个服务仍独立数据库、备份与发布，不共享数据库权限。更新先发布 FabricWorld 再发布 Ledger；长期回退旧版 FabricWorld 前需停用联动，避免旧清理逻辑删除来源记录。精确接口、验证和恢复限制见两项目 docs。FeeTable 和共享 Nginx 不受影响。

## 共享配置与所有权

| 实际位置 | 维护源 / 含义 |
| --- | --- |
| `/etc/nginx/nginx.conf` | Ubuntu 包基础配置，改动需记录；不是业务项目所有 |
| `/etc/nginx/sites-available/apps` | 本技能 `assets/nginx-apps.conf`，80 默认 server |
| `/etc/nginx/sites-enabled/apps` | 指向上面的启用链接 |
| `/etc/nginx/app-locations/ledger.conf` | 指向 `/opt/ledger/config/nginx-location.conf`，源在 Ledger deploy |
| `/etc/nginx/app-locations/feetable.conf` | 指向 `/opt/feetable/config/nginx-location.conf`，源在 FeeTable deploy |
| `/etc/nginx/app-locations/fabricworld.conf` | 指向 `/opt/fabricworld/config/nginx-location.conf`，源在 FabricWorld deploy |
| `/etc/nginx/app-locations/recipebox.conf` | 指向 `/opt/recipebox/config/nginx-location.conf`，源在 RecipeBox deploy |
| `/var/log/nginx/access.log`、`error.log` | 共享 HTTP 请求日志；journal 主要反映 Nginx 生命周期 |
| `/opt/server-context/` | 本技能的文档/模板/检查脚本副本，root 管理 |
| `/opt/AGENTS.md` | 本技能 assets/AGENTS.md 的副本 |
| `/root/AGENTS.md` | 指向 `/opt/AGENTS.md`，便于在 root 登录目录发现 |
| `/etc/update-motd.d/30-server-context` | 交互登录提示；非交互 SSH 不依赖它 |

`SOURCE` 分别位于 `/opt/server-context/` 与每个项目的 `/opt/<app>/docs/`，记录各自来源提交和同步时间。应用的 `current-commit` 记录运行程序版本，不代表 docs 版本；文档更新不应伪造它。

## 其他软件、后台任务和已知问题

- FabricWorld 与 RecipeBox 共用图片运行依赖：Ubuntu 官方签名源 libvips-tools/libvips42t64 8.18.0 与 libheif-plugin-libde265 1.21.2。/tmp 为约 868 MiB tmpfs，图片数据与容量验证放 /opt 的持久磁盘，不能按根盘余量推断 /tmp 容量。
- 已有工具：Git 2.53.0、root 的 `/root/.local/bin/uv` 0.12.15。它们不是任何应用的运行依赖，也不要因为应用不需要就删除。PATH 中没有 Node、Go、Docker、sqlite3，也没有数据库服务或自托管 Actions runner。
- Ubuntu 的 nodejs、npm 及随它们安装的依赖（共 492 个包，含 eslint、webpack 和一批 X11/Mesa/Perl 库）已于 2026-09-26 按用户要求卸载：Node 不是任何应用的依赖，却常让开发 agent 误以为可以在服务器上构建。卸载后四个应用的直连、代理与深链接健康正常，libvips 可用。
- 系统/厂商服务包含 `aliyun`（Aliyun Assist）、chrony、cron、sshd、journald/rsyslog、resolved、networkd、tuned、ModemManager、multipathd 等，不是应用创建的。
- `aegis.service`（Aegis Service，阿里云安全组件）重启前长期 failed（Result=signal），2026-09-24 重启后恢复 running；若再次失败，不要归因于应用。
- 系统 timer 包括 apt-daily/upgrade、logrotate、sysstat、fstrim、文件系统检查、fwupd、MOTD/update notifier 等；unattended-upgrades 会自动装安全更新，没有配置自动重启。
- 2026-09-24 已重启以应用 libc6 更新：四个应用、Nginx 与备份 timer 均自动恢复，直连与代理健康正常，约 25 秒恢复 SSH。以后出现 /var/run/reboot-required 时，按同样方法先检查没有发布/备份在运行，重启后逐项验证。
- 发布历史不自动轮换，每次发布约保留两份程序（Ledger 约 35 MB/次）；根盘目前充裕，定期用 `du -sh /opt/*/releases /opt/*/backups` 查看。
- 没有外部可用性告警或集中监控；靠维护时的只读检查。

## 重新核对

```sh
ssh ali 'cat /opt/AGENTS.md'
ssh ali 'bash /opt/server-context/scripts/inspect.sh'
~/agent-config/skills/server-operations/scripts/sync-docs.sh --check    # 在本地运行：各文档副本是否与仓库一致
ssh ali 'for a in ledger feetable fabricworld recipebox; do echo "$a $(cat /opt/$a/current-commit)"; done'
```

inspect.sh 的 failed-services 当前为空；出现应用或备份 unit 时先查其 journal。检查脚本不访问业务数据库、私钥或账目 API。完整命令输出可能包含公网地址、主机名、PID；只保留必要结论，不能把原始输出直接提交到公开仓库。

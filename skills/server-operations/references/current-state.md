# 当前服务器与应用清单

应用与入口最后核对：2026-09-17（北京时间）；主机基础信息沿用 2026-09-16 核对。这是可覆盖更新的当前快照，不是历史日志。易变版本和状态须重新查；未列出的资源不能视为不存在。

## 主机

| 项目 | 当前状态 |
| --- | --- |
| 连接 | 本地 OpenSSH 别名 `ali`；管理员 root，端口 22；真实地址从受信 SSH 配置取得，不写入公开仓库 |
| 平台 | Alibaba Cloud ECS / KVM，x86_64，Ubuntu 26.04.1 LTS |
| 资源 | 2 vCPU，约 1.7 GiB 可见内存，40 GiB ext4 根盘；无 swap，无独立应用数据挂载盘 |
| 内核 | 核对时 7.0.0-30-generic；不是重建时必须固定的版本 |
| 时间 | Asia/Shanghai；chrony 提供时间同步，NTP 已同步 |
| SSH | 公钥认证开启、密码认证关闭、允许 root 登录；本次仅核对，未修改 |
| HTTP | Nginx 1.28.3（Ubuntu 包 1.28.3-2ubuntu1.11），80 IPv4/IPv6；没有配置 TLS/域名 |
| 主机防火墙 | UFW inactive；不能据此推断所有 netfilter 规则或云侧防护 |
| 云安全组 | SSH/HTTP 已可达，未通过云 API 审计完整规则；改网络前从云控制台/授权 API 核实 |
| 包源 | Ubuntu 签名仓库，当前使用阿里云内网镜像；换供应商时不要照抄该镜像地址 |

## 已部署应用（共享变更必须逐行核对）

| 应用 / 源码 | URL 前缀 → 本机监听 | 目录 / 身份 | systemd | 文档与验证 |
| --- | --- | --- | --- | --- |
| Ledger / [Crashmere/ledger](https://github.com/Crashmere/ledger) | `/ledger/` → `127.0.0.1:18080` | `/opt/ledger`；运行 `ledger`，发布 `ledger-deploy` | `ledger.service`、`ledger-backup.service`、`ledger-backup.timer` | `/opt/ledger/docs/README.md`；直连 `/healthz`、代理 `/ledger/healthz`、深链接 `/ledger/search` |
| FeeTable / [Crashmere/FeeTable](https://github.com/Crashmere/FeeTable) | `/feetable/` → `127.0.0.1:18081` | `/opt/feetable`；运行 `feetable`，发布 `feetable-deploy` | `feetable.service`、`feetable-backup.service`、`feetable-backup.timer` | `/opt/feetable/docs/README.md`；直连 `/healthz`、代理 `/feetable/healthz`、深链接 `/feetable/tables/1` |

Ledger 与 FeeTable 各用独立 SQLite、运行和发布身份。Ledger 每天北京时间 03:00 备份，FeeTable 为 03:15，均加 0–5 分钟随机延迟并保留 14 份 daily；各自 GitHub Actions 从 main、production 环境发布程序。FeeTable 从空库开始，用户明确确认无登录、知址可读写和导出；首份备份与隔离恢复已验证。`server-context` 是文档包，不是应用。精确流程与限制以项目 docs 为准。

新增应用必须增加一行，填明源码、前缀/端口、运行/发布身份、unit、项目文档、健康验证、数据/备份概况。退役后从当前清单删除，仍在迁移中的旧实例必须明确标注用途，不假装已经下线。

## 共享配置与所有权

| 实际位置 | 维护源 / 含义 |
| --- | --- |
| `/etc/nginx/nginx.conf` | Ubuntu 包基础配置，改动需记录；不是业务项目所有 |
| `/etc/nginx/sites-available/apps` | 本技能 `assets/nginx-apps.conf`，80 默认 server |
| `/etc/nginx/sites-enabled/apps` | 指向上面的启用链接 |
| `/etc/nginx/app-locations/ledger.conf` | 指向 `/opt/ledger/config/nginx-location.conf`，源在 Ledger deploy |
| `/etc/nginx/app-locations/feetable.conf` | 指向 `/opt/feetable/config/nginx-location.conf`，源在 FeeTable deploy |
| `/var/log/nginx/access.log`、`error.log` | 共享 HTTP 请求日志；journal 主要反映 Nginx 生命周期 |
| `/opt/server-context/` | 本技能的文档/模板/检查脚本副本，root 管理 |
| `/opt/AGENTS.md` | 本技能 assets/AGENTS.md 的副本 |
| `/root/AGENTS.md` | 指向 `/opt/AGENTS.md`，便于在 root 登录目录发现 |
| `/etc/update-motd.d/30-server-context` | 交互登录提示；非交互 SSH 不依赖它 |

`SOURCE` 分别位于 `/opt/server-context/` 与每个项目的 `/opt/<app>/docs/`，记录各自来源提交和同步时间。应用的 `current-commit` 记录运行程序版本，不代表 docs 版本；文档更新不应伪造它。

## 其他软件、后台任务和已知问题

- 已有工具：Node v22.22.1、npm 9.2.0、Git 2.53.0、root 的 `/root/.local/bin/uv` 0.12.15。它们不是 Ledger 依赖，也不是这次为 Ledger 安装的运行环境；不因 Ledger 不需要就删除。
- 核对时 PATH 未找到 Go、Docker、sqlite3；没有发现数据库服务或自托管 Actions runner unit。仅是核对范围内的结果，不替代新增项目时的检查。
- 系统/厂商服务包含 `aliyun`（Aliyun Assist）、chrony、cron、sshd、journald/rsyslog、resolved、networkd、tuned、ModemManager、multipathd 等；不是 Ledger 创建的。
- `aegis.service`（Aegis Service）当前 failed，Result=signal，原因未调查。本次只记录，未经授权未修复/移除；不要把所有 failed unit 都归因于应用。
- 系统 timer 包括 apt-daily/upgrade、logrotate、sysstat、fstrim、文件系统检查、fwupd、MOTD/update notifier 等；有 unattended-upgrades 组件。没有审计自动重启策略，维护窗口前需检查。
- 核对时存在 /var/run/reboot-required，关联包 libc6；系统需要安排重启，但本次未执行。应在用户同意的维护窗口检查全部应用自启/备份后重启，恢复后验证并删除此条过时状态。
- Ledger、FeeTable 与 Nginx 当前 active，应用和备份 timer enabled。备份 service 执行后 inactive 是正常的；用 journal/Result 判断结果。
- 目前没有配置应用外部可用性告警、集中监控或文档自动漂移检测；靠维护流程与只读检查。
- 目前只确认同盘备份，没有配置异机备份；发布历史和发布前备份不自动轮换，需关注磁盘。是否增设这些能力由实际需求决定，记录建议不代表已经实施。

## 重新核对

```sh
ssh ali 'cat /opt/AGENTS.md'
ssh ali 'bash /opt/server-context/scripts/inspect.sh'
ssh ali 'cat /opt/server-context/SOURCE; cat /opt/ledger/docs/SOURCE; cat /opt/ledger/current-commit'
ssh ali 'cat /opt/feetable/docs/SOURCE; cat /opt/feetable/current-commit'
```

检查脚本不访问业务数据库、私钥或账目 API。完整命令输出可能包含公网地址、主机名、PID；只保留必要结论，不能把原始输出直接提交到公开仓库。

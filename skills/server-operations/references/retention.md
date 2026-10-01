# 发布材料自动保留

2026-10-01 用户已授权六个服务按以下规则清理存量并持续自动执行。此授权仅覆盖发布历史与普通发布前备份；扩大范围或删除其他真实数据仍按 SKILL 授权表处理。

## 策略与实现

共享维护源为 `scripts/prune-releases.py`、`assets/ali-release-retention.service`、`.timer` 和 `.tmpfiles.conf`。Python 3 标准库实现，不安装依赖。服务从 ServerPortal 的受控 registry.d 读取五个应用，复用 validate-portal.py 验证声明；门户自身只使用明确登记的 backups/releases。新应用沿用同一发布与备份契约时纳入相同规则，其他契约先明确适配。

- 保留最近 3 次成功发布及当前运行版本；以 result 的完成时间排序，不按提交字符串或目录名称排序。
- 保留最近 5 份完整 before-deploy 备份，并额外保护仍保留的发布批次对应备份。因当前旧版本或失败保护而超过 3/5 是正常的，不为凑数量删除保护项。两次任务间新发布产生的材料也会暂时超过数量，在下次空闲清理时轮换。
- 失败批次仅在 recovery 为 healthy 或 not-needed、完成已超过 7 天、后续存在成功发布且应用当前健康时才可清理。六个 root 发布脚本在 finish 中写 recovery，再写终态 result。旧失败记录无回退结果时留作人工核对；未完成、未知格式、校验异常和符号链接均保护并记录原因。
- 只匹配 `<40位提交>.<6位发布后缀>` 以及它对应的 before-deploy 名称。不处理 daily、manual、迁移/恢复前快照、业务 data、门户 exports、本地构建目录或云端快照。
- 每次先校验备份结构、SQLite quick_check、媒体清单 SHA-256（相同硬链接只计算一次）、保留程序和 current-commit 对应的程序哈希。没有有效当前版本记录、保留程序损坏或运行状态异常时不删除。
- 备份优先于旧发布目录删除；每项执行前重新核对包含路径、inode、模式、大小与 mtime 的指纹，并用不跟随符号链接的目录描述符操作。回收估算只计算删除集合覆盖全部硬链接的文件及目录占用。

## 调度与并发

`ali-release-retention.timer` 每天北京时间 05:00 执行，Persistent=true。任务独立于应用发布，失败只反映为该维护 unit 失败，不改变发布结果或重启业务。

清理先独占 `/run/lock/ali-release-retention.lock`，再非阻塞获取全部应用既有的 `<app>-deploy.lock`。五个每日备份 unit 的 ExecStart 通过 `flock --shared` 持有前一把锁；先运行的备份使清理跳过，清理先运行时新备份等待锁释放。发布和门户归档/手动清理已使用发布锁；清理检查门户任务状态、每日备份状态、各应用回环健康，检测到云备份 ids 进程也跳过。忙碌跳过记入 journal，下次调度重试；不停止别人的任务。

清理 CPUQuota=50%、MemoryMax=256M、Nice=15、超时 15 分钟。只读预览同样获取锁和校验真实材料；目录较大时应避开正在进行的维护。

## 回执与日志

`/var/lib/ali-release-retention/state.json` 是 root 私有的小型来源回执，记录仍存在的发布前备份属于哪个已完成批次。在删除旧程序目录之前原子落盘，解决“保留 3 份程序、5 份备份”时后两份备份丢失发布元数据的问题；每次结束移除已删备份的回执，不累积历史。清理中断可重跑；回执缺失或指纹不匹配的无来源备份自动保护，不猜测它可删除。

状态目录在门户 shared 资源中登记为私有 config，随门户恢复材料备份；恢复导致 inode 改变时回执指纹失配，相关备份停止自动删除，需按现有完整材料核对来源。日志使用 journal，包含计划、跳过/保护原因、逐项删除意图与结果，不另建无限增长的审计文件。

## 安装、检查与停用

先提交推送共享源并运行 sync-docs.sh。首次安装共享锁及 state 目录，然后安装五个带 flock 的 backup unit 和六个记录 recovery 的发布脚本；应用脚本仍归所属项目维护，部署时核对旧脚本哈希并持有发布锁。无需重建或重启业务程序。新服务器先准备本节的锁文件，再启用任何 backup timer。

```sh
install -m 0644 /opt/server-context/assets/ali-release-retention.tmpfiles.conf /etc/tmpfiles.d/ali-release-retention.conf
systemd-tmpfiles --create /etc/tmpfiles.d/ali-release-retention.conf
install -d -m 0700 /var/lib/ali-release-retention
install -m 0644 /opt/server-context/assets/ali-release-retention.service /etc/systemd/system/ali-release-retention.service
install -m 0644 /opt/server-context/assets/ali-release-retention.timer /etc/systemd/system/ali-release-retention.timer
systemctl daemon-reload
python3 /opt/server-context/scripts/prune-releases.py                 # 只读预览
python3 /opt/server-context/scripts/prune-releases.py --apply --expect-plan <预览的plan_sha256>
systemctl enable --now ali-release-retention.timer
systemctl status ali-release-retention.timer
journalctl -u ali-release-retention.service --no-pager
```

首次先核对待删清单、保护项和实际回收估算，再按用户已确认策略执行。`--expect-plan` 拒绝与已核对预览不一致的计划；定时 unit 每次在锁内重新生成并执行当前策略。需要手工触发同一策略时 `systemctl start ali-release-retention.service`，完成后看 Result、删除日志与保留清单；不要以 unit inactive 判断失败。

暂停自动清理用 `systemctl disable --now ali-release-retention.timer`；已在执行的任务要单独检查 service。停用无需回退程序或恢复已删除材料。删除不可通过关闭 timer 撤销，数据恢复仍需从保留的原生/云端备份选择时点并验证。

## 部署与验收

2026-10-01 已安装六个发布脚本、五个每日备份锁入口、共享 tmpfiles/service/timer，并验证门户采集器加载私有回执资源。首次执行与预览清单完全一致：删除 164 个普通旧发布目录、151 份普通发布前备份，实际释放约 9.15 GiB，根盘使用率由 45% 降至 20%。Ledger 的 schema2 迁移发布材料作为特殊批次保留；daily、manual 和门户 exports 核对无变化。首次清理未改变六个业务程序版本或进程，timer 已启用。

隔离验证覆盖三种快照契约、重复轮换与回执续用、硬链接空间估算、当前版本/失败批次保护、符号链接/损坏材料/变化清单拒绝及发布失败恢复标记。五个备份 unit 在真实 Linux 沙箱下验证共享锁/独占锁互斥；连续 200 次 SQLite 校验无文件描述符增长。首次清理后再次只读校验成功；同期新增发布的超额材料仍按下一次定时任务处理。

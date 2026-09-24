---
name: server-operations
description: Maintain the user's personal Linux servers and multi-application deployments, including SSH host ali, shared Nginx/systemd infrastructure, application inventory, cross-project architecture changes, reproducible rebuilding, and current-state documentation. Use before inspecting, deploying, changing, or troubleshooting these servers or their hosted projects such as Ledger, and when adding another application or updating server maintenance context.
---

# 服务器与多应用维护

把本技能作为共享运维上下文的入口，不依赖之前的聊天。保持实现简单、可阅读、可重建；根据真实需求改进架构，不把今天的方案当成永久限制。

## 先读什么

1. 每次先读 [共享约定](references/conventions.md) 和 [当前服务器与应用清单](references/current-state.md)。
2. 读取目标项目的 `AGENTS.md`、`docs/README.md`、`docs/OPERATIONS.md`，按任务补读架构/API/CI 文档。清单给出仓库和服务器文档位置。
3. 变更、部署、补文档时必须读 [变更与文档闭环](references/maintenance.md)；新增应用、迁移或换服务器时再读 [重建与新增应用](references/rebuild.md)。
4. 发布失败或排障时先查 [共性问题与全局方案](references/common-issues.md)，已有方案直接按其执行。
5. 涉及技能本身或个人指令仓库结构，用 `personal-skill-management`；安装/更新软件用 `software-installation`；Python 环境操作用 `python-environment`。不要复制这些技能的完整流程。

## 授权：改完告知，还是先确认

这是唯一的授权规则，项目文档只链接这里。默认直接做完再告知用户，只有下面“先确认”一栏才停下来问。

| 直接做，结束时告知 | 先确认 |
| --- | --- |
| 只读检查：状态、日志、配置、哈希、网络连通与测速 | 删除、覆盖或恢复真实数据和备份；选择恢复时点；数据库迁移 |
| 所有项目与 agent-config 的文档：修改、提交、推送（纯文档用 `[skip ci]`）、同步服务器副本 | 公网暴露、鉴权、密钥、发布身份或 sudo 权限变化 |
| 清理已知垃圾：失败发布残留、暂存目录、`._*` 等非数据文件 | 修改 root 管理的发布脚本、共享 Nginx server 或其他应用的配置 |
| 用户要求实现或部署时：测试、提交、推送 main、重跑 CI、按 common-issues 已有方案发布 | 其他应用停机、主机重启、额外费用 |
| 修复自己本次操作引入的问题 | 用户只要求查看或诊断时，部署、重启或修复生产 |

不确定属于哪一栏时，可逆且不碰真实数据就按左栏处理。完成后在报告里列出做了什么、结果和遗留项。

## 开始工作

- 先看各仓库工作区和远端提交，再通过受信的 SSH 别名连接。
- SSH 远程命令不会自动加载远端指令；显式读取 `ssh ali 'cat /opt/AGENTS.md'`。不要把“存在 AGENTS.md”或登录提示当成所有客户端都会执行的保证。
- 按任务抽查事实：监听、unit、Nginx include、目录所有者、版本、备份和健康。可在服务器运行 `bash /opt/server-context/scripts/inspect.sh` 取得不含账目的基础状态；云安全组需另行核实。
- 文档是上次验证的快照，现场是实际状态，Git 是维护来源；不一致时调查差异，不能用文档盲目覆盖现场，也不能把意外漂移直接宣布为新约定。

## 实施与收尾

- 应用内部改动留在该项目；共享层改动先检查清单中全部应用，列出受影响的配置、代码、数据、CI、文档、验证与回退点。可以在任务范围内改进设计。
- 在任一项目遇到可能影响其他应用的共性问题（主机、网络、共享 Nginx、共同的发布/备份模式、运行时依赖等），解决方案一律写入 [common-issues](references/common-issues.md)，覆盖全部受影响应用；项目 docs 只保留本项目参数和链接，不各自维护副本。
- 收尾按 [maintenance](references/maintenance.md) 的完成条件：更新所有受影响项目与共享文档（覆盖过时内容，历史交给 Git），推送后运行 `scripts/sync-docs.sh`。分阶段迁移时写明真实共存状态，同步受阻时写明未完成项，不报告完全完成。

## 来源与发现入口

- 共享源：`Crashmere/agent-config` 的 `skills/server-operations/`。本地通常为 `~/agent-config`，不能假设所有电脑都是 `/Users/bytedance`。
- 服务器共享副本：`/opt/server-context/`；`SOURCE` 记录来源仓库、提交和同步时间，不是第二个可独立演进的源。
- 服务器入口：`/opt/AGENTS.md`，root 登录目录中的 `/root/AGENTS.md` 链接到它；各应用 `/opt/<app>/AGENTS.md` 指向项目文档。
- 交互 SSH 的提示由 `/etc/update-motd.d/30-server-context` 提供。不要改 sshd、shell 全局启动输出或 CI 强制命令来强制提示，这可能破坏非交互传输。
- 本地全局 AGENTS 路由到本技能；各项目入口补上离线/远端路径，避免只能从一个客户端发现。

共享配置模板在 [assets/nginx-apps.conf](assets/nginx-apps.conf)，服务器指令入口在 [assets/AGENTS.md](assets/AGENTS.md)，登录提示在 [assets/30-server-context](assets/30-server-context)。文档副本由 `scripts/sync-docs.sh` 同步；Nginx 模板改动属于授权表中的先确认事项，读取技能本身不会安装或重载它们。

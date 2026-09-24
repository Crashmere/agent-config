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

## 开始工作

- 先核对用户授权范围、各仓库工作区和远端提交，再通过受信的 SSH 别名连接。只读请求不授权部署或修复。
- SSH 远程命令不会自动加载远端指令；显式读取 `ssh ali 'cat /opt/AGENTS.md'`。不要把“存在 AGENTS.md”或登录提示当成所有客户端都会执行的保证。
- 按任务抽查事实：监听、unit、Nginx include、目录所有者、版本、备份和健康。可在服务器运行 `bash /opt/server-context/scripts/inspect.sh` 取得不含账目的基础状态；云安全组需另行核实。
- 文档是上次验证的快照，现场是实际状态，Git 是维护来源；不一致时调查差异，不能用文档盲目覆盖现场，也不能把意外漂移直接宣布为新约定。

## 实施与收尾

- 应用内部改动留在该项目；共享层改动先检查清单中全部应用。列出受影响的配置、代码、数据、CI、文档、验证与回退点。
- 在任一项目遇到可能影响其他应用的共性问题（主机、网络、共享 Nginx、共同的发布/备份模式、运行时依赖等），解决方案一律写入 [common-issues](references/common-issues.md)，覆盖全部受影响应用；项目 docs 只保留本项目参数和链接，不各自维护副本。
- 可以在任务范围内改进设计。涉及其他项目的停机、数据迁移、权限/公网暴露变化或额外费用，先解释并取得用户同意。不要以“架构统一”为由扩大授权。
- 落实后检查所有受影响应用，更新每个项目的源码配置和 docs，同时更新共享清单/约定；不要只改现场或新项目。分阶段迁移时记录真实共存状态和未完成项，不宣称全部已迁移。
- 每次变更完成前主动维护上下文文档，覆盖过时描述、删除无效章节；历史交给 Git，不在当前文档中追加流水账。若某层不受影响，报告核对过、无需更改即可。
- 同步 Git 与服务器文档副本，校验内容和链接；不把凭据、数据库、备份、账目统计放入文档或 Git。同步受阻时明确未同步的位置，不报告完全完成。

## 来源与发现入口

- 共享源：`Crashmere/agent-config` 的 `skills/server-operations/`。本地通常为 `~/agent-config`，不能假设所有电脑都是 `/Users/bytedance`。
- 服务器共享副本：`/opt/server-context/`；`SOURCE` 记录来源仓库、提交和同步时间，不是第二个可独立演进的源。
- 服务器入口：`/opt/AGENTS.md`，root 登录目录中的 `/root/AGENTS.md` 链接到它；各应用 `/opt/<app>/AGENTS.md` 指向项目文档。
- 交互 SSH 的提示由 `/etc/update-motd.d/30-server-context` 提供。不要改 sshd、shell 全局启动输出或 CI 强制命令来强制提示，这可能破坏非交互传输。
- 本地全局 AGENTS 路由到本技能；各项目入口补上离线/远端路径，避免只能从一个客户端发现。

共享配置模板在 [assets/nginx-apps.conf](assets/nginx-apps.conf)，服务器指令入口在 [assets/AGENTS.md](assets/AGENTS.md)，登录提示在 [assets/30-server-context](assets/30-server-context)。具体同步步骤见 maintenance；这些是供审阅后部署的材料，读取技能本身不授权安装或重载。

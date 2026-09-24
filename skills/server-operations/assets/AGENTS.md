# 服务器维护入口

操作这台服务器或部署新应用前，先读取 `/opt/server-context/SKILL.md`，然后按其导航读取共享约定、当前应用清单及目标项目文档。

- 共享文档来源：`https://github.com/Crashmere/agent-config` 的 `skills/server-operations/`；服务器 `/opt/server-context/` 是同步副本，来源见其中 `SOURCE`。
- 项目细节来源：各项目自己的仓库。当前有 Ledger、FeeTable、FabricWorld 与 RecipeBox；按共享应用清单定位 `/opt/<app>/AGENTS.md`、`/opt/<app>/docs/README.md`，来源见对应 `docs/SOURCE`。
- 先读当前状态再只读核实，不因文档记载某服务就假定现场未变化。不要读取或打印无关凭据/业务数据。
- 修改共享入口、端口、运行时、权限、备份或发布方案前，评估清单中的全部应用；按授权协调更新，不只修新项目。
- 发布失败或排障先查 `/opt/server-context/references/common-issues.md`。可能影响多个应用的问题，解决方案统一写在那里，项目文档只留参数和链接。
- 每次变更都主动更新所属源码配置和当前上下文文档，覆盖/删除过时信息，提交到对应仓库并同步服务器副本。只改服务器不回写仓库不能算完成。
- 可以根据复杂度改进架构；跨项目停机、破坏性操作、数据恢复、费用或权限范围变化先说明并确认。
- 项目数据库、备份、私钥、Token 不入 Git。当前 Git 仓库公开，不写可直接定位无鉴权账本的公网地址。

注意：非交互 SSH 不会自动加载本文件。远程操作 agent 应显式执行 `cat /opt/AGENTS.md`；交互登录提示只是辅助发现。

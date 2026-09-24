# 变更与文档闭环

哪些事直接做、哪些先确认，只看 [SKILL.md 的授权表](../SKILL.md#授权改完告知还是先确认)。本文只讲怎么做完。

## 每次维护的完成条件

1. 读取当前清单、目标项目入口和对应配置；检查各仓库未提交修改，不覆盖其他人的工作。
2. 实现和验证：应用变更检查该应用；共享变更检查所有依赖该组件的应用。数据写入测试用合成环境；生产只读验收。
3. 更新文档：代码/API/交互写项目文档；部署/目录/服务/权限/备份/CI 写项目运维文档；公共约定/软件/网络/应用增减写共享文档；可能影响多个应用的问题及方案写入 [common-issues](common-issues.md)，受影响项目只留链接。覆盖旧描述、删除失效内容，历史交给 Git，不在当前文档追加流水账；不把凭据、数据库、备份、账目统计写进文档或 Git。某层不受影响时，报告核对过即可。
4. 校验链接、配置语法、敏感内容和 `git diff --check`，提交并推送。推送前看清各项目 main 的 CI 触发规则：Ledger、FeeTable 推 main 会发布，纯文档提交加 `[skip ci]`。
5. 运行 `scripts/sync-docs.sh` 同步服务器副本。最终报告列出改了哪些层、是否改运行时或数据、验证结果和未完成项。

## 哪些变更需要跨项目处理

| 变更 | 必须一并检查/更新 |
| --- | --- |
| 公网入口、TLS、鉴权、IP/域名 | 全部应用 URL、资源/路由/API 前缀、Origin/Cookie、健康检查、CI secrets/SSH host keys、访问说明 |
| 公共目录/权限/运行时 | unit、启动命令、写目录、备份、恢复、发布、文档入口及每个应用的安装材料 |
| Nginx server/include/代理头 | 所有 location、重定向、深链接、API、上传/WebSocket（若有）、日志 |
| 备份或发布机制 | 所有采用该机制的应用工具、调度、轮换、恢复演练、权限、失败处理 |
| 新增/退役应用 | 应用清单、端口与路径占用、用户/unit/入口、项目 docs；删除资源需单独明确范围 |

先列统一目标、影响清单、执行顺序和回退方案，再实施；不能只实施新架构就称整机已统一。暂态只在确有共存期间写入当前状态，完成后删去，不维护“v1/v2/v3 方案对照表”。

## 文档同步

在本地已推送的 checkout 中运行（macOS 自带 bash 3.2 即可）：

```sh
~/agent-config/skills/server-operations/scripts/sync-docs.sh           # shared + 全部项目
~/agent-config/skills/server-operations/scripts/sync-docs.sh Ledger    # 只同步列出的目标
~/agent-config/skills/server-operations/scripts/sync-docs.sh --check   # 只读：漂移、落后、垃圾文件
```

脚本做的事：
- 只导出已推送提交中的受管理文件：shared 为 `skills/server-operations/` 全部文件，外加 `/opt/AGENTS.md` 和登录提示；项目为 `AGENTS.md` 与 `docs/*.md`。有未提交或未推送的文档修改时跳过该目标。
- 先把服务器副本与其 `SOURCE` 记录的提交比对，不一致就停下并显示差异。现场修改先回写仓库，确认后再用 `--force` 覆盖。
- 安装文件为 root 所有，文档 0644，脚本和登录提示 0755；删除旧提交中有、新提交中没有的受管理文件，删除副本目录里的 `._*`；最后写 `SOURCE`，逐文件核对哈希并清理暂存目录。
- 不会修改程序、unit、Nginx、数据库或 `current-commit`。

`PROJECTS_DIR` 指定项目 checkout 目录（默认 `~/ali`），`SYNC_HOST` 指定 SSH 别名（默认 `ali`）。不带参数时，项目列表来自服务器上已有的 `/opt/*/docs/SOURCE`；新应用首次同步时显式传入项目名，缺少的目录由脚本创建。

## 发现机制与验证

- 本地全局 AGENTS 和本技能客户端链接：按 `personal-skill-management` 的 repository workflow 同步，不另写一套客户端发现规则。
- `/root/AGENTS.md` 便于服务器上以 root 工作的 agent 发现；`/opt/AGENTS.md` 便于在 /opt 下工作的 agent 发现；应用入口还提供项目文档。
- 不同工具加载 AGENTS 的方式不同，不能声称任意 agent 一连接就必读。远程 SSH 命令必须从本地路由显式引导读取；交互 SSH 的 MOTD 只是提示。
- 首次安装入口时确认 `/root/AGENTS.md` 不存在后再链接到 `/opt/AGENTS.md`，MOTD 目标无冲突后再安装；之后由同步脚本维护。

## 提交前的最小检查

- 技能 frontmatter、shell `bash -n`、`git diff --check`；新脚本真实运行一次（同步脚本用 `--check`）。
- 搜索意外 Token/私钥/生产地址/真实数据；不要为了扫描秘密打印凭据内容。

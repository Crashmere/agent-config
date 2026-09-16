# 变更与文档闭环

## 每次维护的完成条件

1. 明确本次是查看、应用改动还是共享变更；读取当前清单、目标项目入口、对应配置。检查各仓库未提交修改，不覆盖其他人的工作。
2. 对照现场确认目标、前提和授权。把影响与验证项列在任务计划中；只读任务不顺手修复服务。
3. 实现和验证：应用变更检查该应用；共享变更检查所有依赖该组件的应用。数据写入测试用合成环境；生产默认只读健康验证。
4. 更新文档：代码/API/交互变动写项目文档；部署/目录/服务/权限/备份/CI 变动写项目运维文档；公共约定/软件/网络/应用增减写共享文档。纯代码改动若不改变共享状态，不无意义地刷新整份服务器快照日期。
5. 覆盖旧描述、移除失效链接和重复模板。已被替代的方案只存在 Git 历史中；仍在使用的兼容分支要标注现况。
6. 校验命令、链接、配置语法、敏感内容和 Git diff。提交到各自仓库，按授权推送；先检查项目 main 的 CI 触发规则，不能把推文档引发的发布视为无副作用。
7. 同步各自服务器副本，逐文件比对，更新 `SOURCE`；记录仍未完成的部署、文档同步、权限或验证，不能只报“已写文档”。

## 哪些变更需要跨项目处理

| 变更 | 必须一并检查/更新 |
| --- | --- |
| 公网入口、TLS、鉴权、IP/域名 | 全部应用 URL、资源/路由/API 前缀、Origin/Cookie、健康检查、CI secrets/SSH host keys、访问说明 |
| 公共目录/权限/运行时 | unit、启动命令、写目录、备份、恢复、发布、文档入口及每个应用的安装材料 |
| Nginx server/include/代理头 | 所有 location、重定向、深链接、API、上传/WebSocket（若有）、日志 |
| 备份或发布机制 | 所有采用该机制的应用工具、调度、轮换、恢复演练、权限、失败处理 |
| 新增/退役应用 | 应用清单、端口与路径占用、用户/unit/入口、项目 docs；删除资源需单独明确范围 |

先给出统一目标、影响清单、执行顺序和回退方案，再实施。若任务授权不足以动旧项目，停在方案/兼容准备层请求批准，不擅自让旧应用停机；也不能只实施新架构然后称整机已统一。

协调多仓库时，记录本次变更涉及的提交与未完成步骤。暂态只在确有共存期间写入当前状态，完成后删去。不要维护永久的“v1/v2/v3 方案对照表”。

## 文档与配置的同步方法

### 源码端

- 共享源：`Crashmere/agent-config/skills/server-operations`。项目源：各项目受 Git 跟踪的 `AGENTS.md`、`docs/*.md`、`deploy` 等；生产同步文档时只取文档白名单。
- 一律从确认过的提交导出，不上传整个工作区。Ledger 的 ignored 文档可能包含真实验收数据，不能 `scp -r docs`。
- 变更源码或部署配置需对应发布流程；下面的文档同步不改变程序、unit、Nginx 或数据库。共享模板更新后也不会自动应用到运行配置。

以本地已审阅并提交的两个 checkout 为例，先导出到新建暂存目录（由实际命令返回目录，后续显式使用它）：

```sh
mktemp -d /tmp/server-context-sync.XXXXXX
git -C /path/to/agent-config rev-parse HEAD
git -C /path/to/ledger rev-parse HEAD
```

使用 `git archive HEAD:skills/server-operations` 导出共享技能到暂存区的 `shared/`。项目用 `git ls-files AGENTS.md 'docs/*.md'` 审核列表后，`git archive HEAD -- <已审阅的相对路径>` 导出到 `project/`。不要把忽略文件、私钥或数据库塞进打包列表。

在暂存区为两份文档分别生成纯文本 `SOURCE`（不是源码仓库里的动态文件）：

```text
repository=https://github.com/Crashmere/agent-config
commit=<完整提交号>
subdirectory=skills/server-operations
synced_at=<UTC ISO 时间>
```

项目的 repository 改为项目 URL，subdirectory 为 `AGENTS.md,docs`。标记不能写一个尚未推送/无法找回的提交而不注明同步未完成。

### 服务器端

1. SSH 管理员在 `/tmp` 创建独立暂存目录，上传导出内容，校验文件清单/哈希；不要以运行用户或 CI 发布身份修改文档源。
2. 首次用 `install -d -m 0755` 创建 `/opt/server-context` 及所需子目录、应用 docs；后续先检查现有文件和 `SOURCE`，发现现场独有修改先回收到源码。
3. 安装已审阅的文件：文档 0644、目录 0755、检查脚本和 MOTD 0755，root 所有。共享导出映射到 `/opt/server-context/`；项目 docs 到 `/opt/<app>/docs/`，项目 AGENTS 到 `/opt/<app>/AGENTS.md`。
4. 安装共享 `assets/AGENTS.md` 到 `/opt/AGENTS.md`；首次确认 `/root/AGENTS.md` 不存在后链接过去；确认 MOTD 目标无冲突后安装 `assets/30-server-context`。以后更新只覆盖已知受管理文件。
5. 最后安装各自 `SOURCE`。用 `sha256sum`（macOS 可用 `shasum -a 256`）逐文件核对 Git 导出与远端；检查链接目标、0644/0755 权限、入口导航和 MOTD 输出。
6. 若源文件被删除，先列出上次副本与本次列表之差，明确只处理受管理的旧文档后移除；不能把整个 `/opt` 或应用目录做 `rsync --delete`。服务器不保留冗余旧手册，历史回 Git 查。

手动源端与服务器双向修改不可长期并存。紧急服务器编辑必须立即回写仓库再同步；网络或权限阻碍时明确报告待办，保留真实来源标记。

当前没有自动将 docs 上传服务器的 CI。管理员按上述流程同步是维护任务的必做收尾；今后若加入自动化，应限制到文档白名单和专用目标，不能给现有发布密钥任意写配置的权限。

## 发现机制与验证

- 本地全局 AGENTS 和本技能客户端链接：按 `personal-skill-management` 的 repository workflow 同步，不另写一套客户端发现规则。
- `/root/AGENTS.md` 便于服务器上以 root 工作的 agent 发现；`/opt/AGENTS.md` 便于在 /opt 下工作的 agent 发现；应用入口还提供项目文档。
- 不同工具加载 AGENTS 的方式不同，不能声称任意 agent 一连接就必读。远程 SSH 命令必须从本地路由显式引导读取；交互 SSH 的 MOTD 只是提示。
- 检查 `ssh ali 'cat /opt/AGENTS.md'`、共享及项目所有相对链接。MOTD 可直接执行查看，交互登录也应可见；不改变非交互 stdout，避免影响 SCP/CI。

## 提交前的最小检查

- 技能 frontmatter 验证、shell `bash -n`/`sh -n`、`git diff --check`；新检查脚本真实只读运行一次。
- 检查文档本地相对链接；`SOURCE` 提交与 GitHub 分支一致，远端文件与导出一致。
- 搜索意外 Token/私钥/生产地址/真实数据，检查暂存列表。不要为了扫描秘密打印凭据内容。
- 最终报告说明：改了哪些层、是否改运行时/账本、文档入口、验证与未完成项。历史提交不是当前状态的一部分。

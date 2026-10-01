# 本机发布与按需验证

适用当前个人服务 Ledger、FeeTable、FabricWorld、RecipeBox、Yuyan、ServerPortal。2026-09-28 用户决定：GitHub 仅备份源码与配置；构建和发布由维护电脑完成；本地验证本次功能后即可上线，不以全量历史回归为发布门槛，不默认积累永久测试代码。临时检查脚本用完即可移除。普通功能故障接受修复或程序回退；数据库迁移、批量写入/删除、导入覆盖和备份恢复先在隔离副本针对性验证。

## 维护电脑

取得 agent-config 与各项目仓库。使用 go.mod 指定的 Go 工具链、Node/npm、Git、OpenSSH、make、Python 3 标准库；无需 Python 第三方包。当前实测 Mac 为 Go 1.26.8、Node 26.10.0、npm 12.1.0；发布清单记录实际版本，不依赖云端 runner。前端依赖按 package-lock.json 安装。FabricWorld、RecipeBox 本地验证图片功能还需 libvips；Yuyan 导入/导出/roundtrip 等维护工具继续保留。

新电脑安装工具按 software-installation，不为保留已退役的 Linux 回归套件安装虚拟机。Go 默认 PATH 由 goenv 延迟加载时，发布入口自动补充 ~/.goenv/shims。

共享实现是 scripts/release.py。每个项目 deploy/release.sh 调用它，deploy/release.json 维护应用名、构建命令、产物位置和传输模式。默认共享源码位于 ~/agent-config/skills/server-operations，可用 SERVER_OPERATIONS_HOME 指定。不要在业务仓库复制整套发布实现。

## 验证、构建和部署

1. 本地验证本次修改。界面检查实际使用的桌面/手机场景；计算或导入逻辑用代表性样例。构建保留必要的类型检查。开发时已经验证的内容无需发布时重复完整测试。
2. 提交明确的源码快照并 git push origin main。推送只备份，不触发任何生产操作。
3. 在项目执行 make release：只导出 Git 已提交文件，在隔离构建目录安装锁定依赖并 make linux；生成静态 Linux amd64 程序。五个业务应用同时校验和保存同提交 deploy/portal.json。
4. make deploy 复用同提交构建产物；没有产物才构建。拒绝未提交的受跟踪修改、未备份到 origin/main 的提交及哈希不符的产物。未跟踪文件不进入快照。
5. 本机通过 SSH 上传，服务器固定脚本完成备份、候选校验、原子替换和启动健康检查；随后同步声明并核对门户回执，验证公网未授权接口返回 401。
6. 文档变更推送后运行 scripts/sync-docs.sh；只改文档无需部署程序。

本地 `.local/releases/<完整提交>/` 保存 program、manifest.json、业务应用的 portal.json 和 last-deployment.json；manifest 记录源码提交、SHA-256、工具版本及构建命令。它明确只证明构建/声明检查，不能冒充功能验证记录。材料不提交 Git，也不自动清理。可用 make releases 查看。

脚本中途失败会返回非零。程序成功而门户声明或公网检查失败时，运行程序可能已经更新，应按输出和 last-deployment.json 确认，不能盲目重复发布。只修声明执行 make portal，不构建或重启服务。源码、构建参数或工具链需要重新生成产物时，保留原材料，把对应版本目录移动到明确的新位置后重新 make release。

## 身份与传输

- RELEASE_HOST 默认 ali，使用本地已信任的 SSH 主机配置和严格指纹校验。
- 五个业务应用使用各自 <app>-deploy 受限身份，共用维护电脑的 ~/.ssh/ali_deploy_ed25519 发布密钥（可用 RELEASE_KEY 指定），私钥只留本机并独立保管。该密钥拥有五个业务应用的发布/数据权限，不拥有整机管理员权限；不复用到其他机器。
- 服务器 authorized_keys 设置 restrict 与固定 deploy-ssh.sh；只接受 deploy、portal-check、portal，sudo 仅允许本应用 root 管理的 deploy-release.sh。新服务器/新应用用各项目 setup-deploy.sh 建立身份；已有账号显式轮换公钥，不重复初始化。
- ServerPortal 使用现有管理员 SSH；它的采集器运行于 root，因此门户发布仍是管理员操作。其固定脚本由 ServerPortal/deploy 维护，不创建一个伪装成低权限的门户发布账号。
- GitHub Actions 在六个应用仓库均关闭，workflow 和五套 production Secrets 已移除，旧 CI 公钥已撤销。不要向 GitHub 上传生产发布私钥。GitHub 推送认证独立保留。
- SSH 启用压缩；Yuyan 继续传 gzip 流并校验未压缩哈希，其他应用沿用原始程序流。服务器不安装构建工具。

## 回退和数据保护

`make rollback COMMIT=<完整旧提交>` 使用本地保留的已校验版本，经同一个服务器脚本发布，仍执行升级前备份与健康检查。迁移时保存了各服务原有生产程序及哈希，便于首次本机发布回退；以后每次构建自然积累本地可选版本。

先确认目标旧程序兼容当前 schema/设备状态。程序回退不等于数据库恢复，不会自动恢复照片、数据库或门户凭据；真实恢复按项目文档选择时点并另行确认。服务器 releases 保存 previous/result/metadata/recovery，程序、数据与文档的来源版本分别记录。服务器发布材料由 [共享保留任务](retention.md) 每日清理；本地 .local/releases 不属于该范围。失败终态写入明确的回退结果，供 7 天后清理判断。

门户更新短暂停止 Web 和采集器，data/config 在停写后复制到 root 私有 backups/before-deploy-*。正在运行的归档任务会使更新拒绝；发布期间不要新开备份或清理。公网设备认证会短暂不可用，业务应用进程不重启。门户历史备份和发布目录已列入其私有配置模板的 shared 资源，不对网页开放浏览和清理。

发布机制、鉴权、备份格式发生变化时，针对改动验证正常路径与关键失败分支；检查脚本可以临时编写，不要求恢复永久全量测试。公共诊断工具与运行时保护按实际价值保留。

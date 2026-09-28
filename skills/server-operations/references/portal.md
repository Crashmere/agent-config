# 门户与资源声明维护

ServerPortal（Crashmere/ServerPortal，工作区 ~/ali/ServerPortal）负责应用门户、设备认证、只读资源、受限清理和备份。运行在 /opt/serverportal、回环 18085、/portal/，公网根路径跳转门户。共享认证覆盖业务公网页面/API；ACME、本机发布检查和服务间调用保留。

## 所有权与注册目录

- 各应用只在自己的 deploy/portal.json 维护名称、图标、仓库、入口、端口、用户、unit、数据库、备份类型、目录用途和主要 API；生产文件为 /opt/<app>/config/portal.json，由 root 管理。
- 门户使用 registryDir=/opt/serverportal/registry.d，每个 <app>.json 是指向 /opt/<app>/config/portal.json 的 root 管理链接。首次声明发布创建链接，无需维护中央 registry 路径数组。旧 registry 数组仅兼容迁移，不能与 registryDir 同时配置。
- 门户按请求检测声明变化，普通请求最多缓存 2 秒；/registry 生效检查强制重读。整组声明全部有效才替换内存快照，同时失效概览缓存与未执行清理预览。错误时保留运行中的上一份有效配置并显示提示；重启时仍要求磁盘声明有效。
- 自动发现的范围是注册目录。应用文件、数据库表和运行状态从现场读取；目录用途、API 说明、服务归属与浏览/清理边界必须显式维护，不能靠扫描猜测。

## 共用校验和发布协议

校验维护源只有 scripts/validate-portal.py（Python 3 标准库）。应用 CI checkout 固定提交的 agent-config 执行它；服务器从 /opt/server-context/scripts/validate-portal.py 使用同一规则。更新契约时同步该脚本、ServerPortal 适配和各 CI 固定提交，并验证已有声明。服务器不需要 Go/Node 或额外 Python 包。

每个应用的原有发布身份、authorized_keys 和 sudo 范围保留。root 管理的 deploy-ssh.sh / deploy-release.sh 新增两种固定命令：

- portal-check <source-commit> <declaration-sha256>：stdin 为最多 1 MiB JSON，校验声明归属、整体注册冲突和 SHA-256，不写文件；在替换业务程序之前执行。
- portal <source-commit> <declaration-sha256>：同样校验，取得本应用发布锁和注册锁，原子安装声明并建立受控链接，强制门户重新加载并核对实际 SHA-256。失败恢复原声明/链接；成功记录 config/portal-source.json。

这两个命令都通过该应用已有的固定 root 发布脚本调用 ServerPortal，应用名由脚本固定。不能上传校验器或发布脚本，不能指定其他应用、目录或任意命令。声明固定自身 root、运行用户和 URL 前缀，unit 必须属于本应用，资源不能越出自身目录，配置/秘密不能改为网页可读，清理仅允许自身 backups/releases。

普通 CI 把同提交 portal.json 与程序放进同一 artifact，先预检，程序成功发布后再同步声明。声明同步失败会使工作流失败；已成功发布的程序不自动回退，运维先检查 source marker 和门户回执，再修正声明。程序健康走服务器回环；公网 HTTPS 无凭据应返回 401。

只更新门户元数据时，可在 main 上手动运行：

```sh
gh workflow run ci-cd.yml --ref main -f portal_only=true
```

此模式仍执行 CI 验证和声明检查，保留业务程序与 current-commit，不停服务、不运行发布前数据快照；源码/数据库变更仍须普通发布。声明来源提交在 portal-source.json，运行程序来源在 current-commit，不能混写。

## 新服务与日常维护

1. 按共享重建规则准备服务、受限发布身份、文档和 Nginx location，继承公网认证，并默认完成 [网站图标约定](conventions.md#网站图标与手机桌面入口) 的图标、精确公开规则及自动检查；当前自动接入约定为 /opt/<id>、同名运行用户、单个 SQLite 与原生 backup 接口。不同存储/部署形态先实现明确适配。
2. 在项目中添加 deploy/portal.json、AGENTS 同步规则，CI 接入共享校验与上述发布协议；更新共享应用清单。首次声明发布会自动登记服务。
3. 数据根、接口、unit、端口、访问路径或备份契约变化，同一提交维护声明及对应 docs。普通文件、照片、备份文件和数据库记录增减不需要改声明。
4. 发布后核对门户加载回执、目录用途、只读数据表和未知目录提示。备份契约变化需要相应合成回归；真实恢复演练按用户安排，不自动恢复已暂缓任务。
5. 文档仍由 sync-docs.sh 同步，普通程序 CI 不发布 docs；新增/改名/退役服务的共享架构和真实数据处置按 SKILL 授权表。

## 安全与备份

设备凭据由服务器生成，使用 Secure/HttpOnly Cookie。网页浏览只读，清理必须预览并确认。根采集器仅监听本机 Unix socket，网页进程独立用户；不开放任意路径、SQL 或命令。

备份使用离线 age 公钥加密，包含一致性应用快照、程序/运行配置、发布公钥、共享配置、证书、AGENTS/docs、门户状态与 registry.d 链接。恢复私钥、云账号/安全组和 GitHub secrets 独立保管。备份格式、真实恢复验收状态与重建顺序以 ServerPortal docs/RESTORE.md、docs/VERIFICATION.md 为准。

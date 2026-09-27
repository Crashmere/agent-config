# 门户与恢复材料维护

ServerPortal（Crashmere/ServerPortal，工作区 ~/ali/ServerPortal）是应用门户、设备认证和只读资源展示的维护源。预计部署 /opt/serverportal、127.0.0.1:18085、/portal/，unit 为 serverportal 与 serverportal-agent。当前只有本地实现与接入材料，尚未安装到生产；五个应用现有访问方式没有改变。实际启用后覆盖本节和 current-state，不保留过期状态。

## 所有权与维护闭环

- 每个业务项目拥有自己的 deploy/portal.json，生产副本为 /opt/<app>/config/portal.json；门户配置只引用它们，不集中维护第二套应用目录/端口/API 清单。
- 声明记录应用图标/名称、仓库、URL、端口、运行身份、unit、数据库、原生备份类型、目录作用、浏览/清理边界、主要 API。程序实际文件和 systemd/证书状态由采集器读取。
- 数据根、schema/媒体、备份格式、部署目录、unit、端口、路径或 API 变更：同一提交更新项目声明与文档，更新共享清单，安装配置后重启采集器并检查资源覆盖、未知目录和恢复测试。普通业务 CI 不自动安装资源声明。
- 新增应用必须登记门户资源与备份契约，验证一致性快照和隔离恢复；不能仅加一张应用卡片就声称备份覆盖。退役应用先确认真实数据与备份处置，清理后再删除当前清单。
- 共享 Nginx auth include 属于本技能 assets/nginx-portal-auth.conf。门户自己的 location/unit/程序属于 ServerPortal。只在公网 HTTPS server 开启统一 auth_request，保留 ACME 与回环发布检查。

## 安全与备份

口令验证后由服务器签发随机设备凭据，使用 Secure/HttpOnly Cookie；不要改成客户端自报 device ID 或指纹。设备认证影响全部应用，正式激活按 SKILL 授权表处理。网页浏览只读，清理必须先预览具体路径并确认；用户请求开发清理功能不等于授权现在删除生产备份。

备份使用离线 age 公钥加密，私钥保存在服务器外；整机材料包含原生一致性数据快照、程序/版本、运行配置、部署公钥、共享配置、证书状态和 AGENTS/docs。数据库不复制活动 WAL 主文件。恢复以清单覆盖与实际演练为准，云账号/安全组、GitHub secrets 和本地私钥需独立保存。完整包、增量父链、删除记录、校验、合并与恢复步骤由 ServerPortal docs/RESTORE.md 维护，本技能只保留入口。

根权限采集进程仅监听本机 Unix socket；网页进程独立用户。鉴权、sudo/权限、共享 server 或其他应用配置变更仍按统一授权表；默认不给门户任意命令、SQL 或路径操作能力。

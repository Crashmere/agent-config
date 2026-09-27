# 共享 HTTPS 与 IP 证书

五个应用共用 Nginx 的公网 HTTPS 443，继续使用 /ledger/、/feetable/、/fabricworld/、/recipebox/、/yuyan/。证书由 Let's Encrypt 为服务器公网 IPv4 签发，无需域名。HTTP 80 只提供 ACME 验证文件和到固定公网 IP 的 308 跳转，保留路径、查询参数与请求方法；API 客户端直接使用 HTTPS，不能把首次明文请求也当成已加密。

HTTPS 提供传输加密，尚无登录认证。不同路径仍是同源；后续会话、Cookie、CSRF 和服务间鉴权需统一设计。IP 地址不能依赖浏览器 HSTS，当前不发送 HSTS，也不启用 preload。

## 配置与维护源

| 文件/服务 | 职责与维护源 |
| --- | --- |
| /etc/nginx/sites-available/apps | assets/nginx-apps.conf 渲染公网 IPv4；共享 80/443 和本机检查入口 |
| /opt/<app>/config/nginx-location.conf | 各项目 deploy；保留 Host，覆盖 X-Forwarded-Proto 为 $scheme |
| /etc/letsencrypt/live/apps-ip/ | Certbot 管理的证书链和私钥；不进入 Git/文档同步 |
| /var/lib/letsencrypt/.well-known/acme-challenge/ | HTTP-01 验证文件目录，Nginx 只读 |
| /etc/letsencrypt/renewal-hooks/deploy/reload-nginx | assets/certbot-reload-nginx，续期成功后先 nginx -t，再 reload |
| snap.certbot.renew.timer | 官方 Certbot snap 的自动续期调度 |

TLS 在 Nginx 终止，各 Go 服务继续只监听 127.0.0.1:18080–18084。Ledger 到 FabricWorld 的服务间调用保持本机 HTTP。127.0.0.1:80 与 [::1]:80 有独立 listen，供原有发布脚本检查代理页面；按实际目标地址选择且只允许回环来源，不能仅按可伪造的 Host 决定是否绕过公网跳转。

Ledger、FeeTable、FabricWorld、RecipeBox 的来源校验优先识别直接 TLS；对于 HTTP 连接，只接受回环对端传来的单个、值为 https 的 X-Forwarded-Proto。Nginx 必须覆盖该头，应用不能对外监听。缺失、重复、列表值或非本机连接的代理头不能提升为 HTTPS。Yuyan 已传此头，后续认证若使用它须遵守同样边界。

## 初次配置与重建

先按 SKILL.md 核对授权、所有应用、服务器指令和配置漂移；保留原共享 server 与五个 location 的 root 私有副本。以下只展示顺序，公网 IP 从受信 SSH 配置取得，不提交真实地址。

1. 使用 software-installation 安装官方 Certbot snap：snap install certbot --classic。需 Certbot 5.4+ 支持 IP 的 webroot；当前 Ubuntu 的 4.0 包不适用。不要混用 apt、pip 和 snap 的 Certbot。snap 自行更新。
2. 建立 /var/lib/letsencrypt/.well-known/acme-challenge（root 所有，目录 0755），先安装 assets/nginx-apps-bootstrap.conf。它只新增验证路径，保留现有 HTTP 应用。nginx -t 成功再 reload，检查原应用和外网验证文件。
3. 先用 staging 演练；--dry-run 不安装测试证书，不把 staging 证书提供给浏览器：

   ```sh
   /snap/bin/certbot certonly --dry-run --non-interactive --agree-tos \
     --register-unsafely-without-email --preferred-profile shortlived \
     --webroot -w /var/lib/letsencrypt --ip-address "$public_ipv4" --cert-name apps-ip
   ```

4. 演练成功后去掉 --dry-run，签发正式 apps-ip 证书。未提供联系邮箱时使用上述无邮箱注册方式；后续可按用户提供的邮箱更新 ACME 账户。
5. 四个应用的来源校验修复须经测试并完成发布；逐个安装已提交的 location。普通 CI 只替换程序，不会安装 Nginx 配置。检查所有应用本机健康和代理页面。
6. 将 assets/nginx-apps.conf 的 __PUBLIC_IPV4__ 替换为受信公网 IPv4。先用仍保留 HTTP 应用的临时配置加上 443，验证公网 TLS 可达、证书可信、全部应用正常后，再切换完整模板开启 308。云安全组需允许 TCP 443；不能因 UFW inactive 就假定云侧规则已核实。
7. 把 assets/certbot-reload-nginx 安装为上述 deploy hook（root 所有，0755）。核对 snap 的续期 timer active/enabled；运行 certbot renew --cert-name apps-ip --dry-run --run-deploy-hooks --no-random-sleep-on-renew，确认验证与重载成功。再实际运行一次 snap.certbot.renew.service 并核对 Result=success；未到续期窗口时跳过签发是正常结果。手工演练加 --no-random-sleep-on-renew 避免等待随机延迟；自动任务保留原有随机延迟。
8. 按下节完成全部验收，更新约定/current-state/项目文档，推送后同步文档副本。

安装配置时先 nginx -t，失败立即恢复该步的原配置；语法正确但公网验收失败时保持原 HTTP 入口，排除证书、网络或应用问题后再跳转。重载 Nginx 不需停止 Go 服务。

## 验收与日常检查

最近验收：2026-09-27。五个应用的 CI 检查与构建全部通过，四个来源校验中间件新增的 52 个 HTTPS/伪造头用例通过。五个应用均以正式可信证书通过外网 HTTP/2 健康检查，桌面 1360×900 与手机 375×667 的 Chromium 检查均为 TLS 1.3、安全上下文，无混合内容、脚本错误或资源请求失败。公网跳转、查询参数、Host 伪造、本机检查及切换后的续期/重载演练通过。

- 外网无 -k 访问五个健康接口、首页、深链接及脚本/样式；真实浏览器检查 secure context、HTTP/2、请求失败和 mixed content，包含桌面与 375×667。
- 公网 HTTP 首页、裸路径、深链接和 API 均 308 到固定 HTTPS 地址，完整保留查询参数；公网 Host: localhost/127.0.0.1 也不能访问本机 HTTP 入口。ACME 文件仍能经 HTTP 获取，缺失文件 404。
- 四个应用同源 HTTPS 请求能通过中间件；伪造非本机代理头、错误 Origin、错误协议等由仓库回归测试覆盖。生产使用不写数据的 OPTIONS 请求验证来源拒绝与通过，不提交测试记录。现有服务间调用保持回环。
- 从服务器核对五个直连 /healthz 与 127.0.0.1:80 的代理健康、页面资源；检查 nginx -t、所有 unit 及配置哈希。
- inspect.sh 检查证书颁发者、有效期、48 小时到期阈值和续期 timer。IP 证书约 160 小时有效；自动续期失败时须及时修复，不能等待到期。当前没有外部证书到期告警。

```sh
ssh ali '/snap/bin/certbot certificates'
ssh ali 'systemctl list-timers snap.certbot.renew.timer --all --no-pager'
ssh ali 'journalctl -u snap.certbot.renew.service -n 60 --no-pager'
ssh ali '/snap/bin/certbot renew --cert-name apps-ip --dry-run --run-deploy-hooks --no-random-sleep-on-renew'
ssh ali 'bash /opt/server-context/scripts/inspect.sh'
```

保留 80 的 ACME 路径：后续认证规则不能拦截它。不要编辑 Certbot 的 archive/live 链接或手工复制私钥；公私钥权限由 Certbot 管理。

## 故障与回退

证书续期失败先检查 HTTP-01 公网可达、系统时间、出站 ACME 网络、timer/hook 日志及 nginx -t。重载失败时修复配置并执行 deploy hook；只在证书实际需要更新时运行 renew，不循环强制签发以免触发限额。

共享配置回退到本次保存的原 server，nginx -t 成功后 reload，检查五个应用。来源校验兼容旧 HTTP，无需回退程序。回退到明文只作为故障恢复措施，报告真实状态；不要删除证书、数据或备份。公网 IP 改变时重新验证并签发覆盖新 IP 的证书，同时修改共享配置和客户端地址。

官方依据：[Certbot 的短期与 IP 证书](https://letsencrypt.org/2026/03/11/shorter-certs-certbot)、[160 小时证书](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability/)。

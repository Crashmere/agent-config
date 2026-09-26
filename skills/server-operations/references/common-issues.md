# 共性问题与全局方案

这里存放可能影响多个应用的问题及统一处理方案：主机与网络、共享 Nginx、共享的发布/备份模式、运行时依赖等。在任一项目遇到这类问题时，把方案写在这里并覆盖全部受影响应用；项目 docs 只保留本项目参数和指向本文的链接，不各自复制一份流程。只属于单个应用的问题留在该项目 docs。

每条写清现象与判断条件、适用应用、处理步骤、清理与验收，以及尚未实施的改进。方案被替代时直接改写本条，历史由 Git 保存。

## systemd 沙箱下照片硬链接备份失败

适用 FabricWorld、RecipeBox，以及今后任何“在备份目录里硬链接数据文件”的应用；Ledger、FeeTable 只备份 SQLite，不受影响。FabricWorld、RecipeBox 已于 2026-09-24 按下述方法修复并验证；Yuyan 于 2026-09-26 安装时即按此配置，并通过 unit 验证。

现象：`<app>-backup.service` 每次 failed，journal 为 `hard-link media backup: link ... invalid cross-device link`。安装时用 `runuser` 手动做的首份备份不经过 unit 沙箱，不会暴露这个问题；两应用因此从第一次定时运行起连续失败了 5 天才被发现。

原因：unit 使用 `ProtectSystem=strict` 和 `ReadWritePaths=/opt/<app>/data /opt/<app>/backups`，systemd 把两个目录各自绑定挂载成独立挂载点。Linux 不允许跨挂载点建硬链接（即使底层是同一文件系统），返回 EXDEV。

修复：备份 unit 使用 `ReadWritePaths=/opt/<app>`，让 data 与 backups 处于同一个可写挂载点。`/opt/<app>` 下其余内容由 root 所有，应用用户按文件权限本来就不能写，实际写入范围不变。改项目仓库 `deploy/<app>-backup.service` 并推送，安装到 `/opt/<app>/config/` 后 `systemctl daemon-reload`；常驻服务 unit 不需要改。失败的运行不会留下不完整的备份目录，无需清理。

验证：`systemctl start <app>-backup.service` 后 `systemctl show <app>-backup.service -p Result` 为 success；新的 `daily-*` 目录含 `manifest.json`，其中照片的硬链接数（`stat -c %h`）大于 1。新增应用启用备份 timer 后，也要像这样通过 unit 实际运行一次，不能只用 `runuser` 手动备份代替。

## Go 程序返回的 JavaScript 没有被 Nginx 压缩

适用在应用 location 中用 `gzip_types` 开启压缩的应用，目前只有 Yuyan；Ledger、FeeTable、FabricWorld、RecipeBox 没有设置 `gzip_types`，沿用 nginx.conf 默认只压缩 HTML，不受影响。以后任何 Go 应用开启 `gzip_types` 时都要按此配置。

现象：CSS、JSON 响应带 `Content-Encoding: gzip`，`.js` 没有。Yuyan 从安装起就是这样，2026-09-26 发布单页应用后才发现：应用脚本原样传输 297 KB（压缩后约 100 KB），编辑器分块约 930 KB（压缩后约 290 KB），按服务器约 0.5 MB/s 的下行速度多等 1 秒以上。

原因：Go 的 `http.FileServer` 按扩展名把 `.js` 返回为 `text/javascript; charset=utf-8`，而 `gzip_types` 只写了 `application/javascript`。

处理：在应用自己的 location 中让 `gzip_types` 同时包含 `text/javascript` 与 `application/javascript`。改项目仓库的 `deploy/nginx-location.conf` 并推送，安装到 `/opt/<app>/config/nginx-location.conf` 后 `nginx -t`，再 `systemctl reload nginx`；不需要改共享 server。

验收：`curl -sI -H 'Accept-Encoding: gzip'` 请求应用的一个 `.js` 资源，返回 `Content-Encoding: gzip`；reload 后逐个核对五个应用的直连、代理健康检查与深链接。Yuyan 已于 2026-09-26 按此修复并验证。

## GitHub 上传过慢时的备用发布

五个应用都由 GitHub 托管 runner 构建，再经受限 SSH 身份把程序通过 stdin 交给 root 管理的 `/opt/<app>/bin/deploy-release.sh`。Ledger、FeeTable、FabricWorld、RecipeBox 的脚本只等待 90 秒上传（`timeout 90 head -c ...`）；Yuyan 从安装起就上传 gzip 压缩后的程序，并等待 600 秒。runner 位于境外 Azure，到服务器的跨境线路可能突然变慢。2026-09-24 实测：同一 17.7 MB 程序此前 CI 上传约 8–10 秒，当天三次只有约 30–60 KB/s；同时服务器负载、网卡、防火墙正常，境内上传 3.5 秒完成，GitHub 状态页无故障。原因在跨境线路，不是应用或服务器配置。

遇到上传超时不反复重跑发布作业，直接由管理员从受信终端把同一提交的 CI 产物交给同一个发布脚本。锁、哈希校验、停服备份、候选检查/迁移、原子替换、健康检查和失败回退都与 CI 发布相同。

### 判断条件

以下全部成立才使用；哈希不符、候选 check/migrate 失败、健康检查失败或回退信息等其他错误先排查原因，不用本方案绕过。

- 发布作业的 SSH 步骤以 exit code 124 结束，耗时约 90–100 秒。
- 该应用最新发布目录 `result` 为 failed 且没有 `metadata`：脚本在上传阶段中止，从未停服，也没有 before-deploy 备份。
- `current-commit` 仍是旧提交，服务 active、健康检查正常。
- 待发布提交仍是 main 最新提交，且对应的测试/构建作业成功。

### 各应用参数

| 应用 | 产物来源 | artifact / 文件 | 验收路径 |
| --- | --- | --- | --- |
| Ledger | 失败的 `CI and deploy` run 本身 | `ledger-linux` / `ledger-linux-amd64` | `/ledger/healthz`、`/ledger/search` |
| FeeTable | 失败的 `CI and deploy` run 本身 | `feetable-linux` / `feetable-linux-amd64` | `/feetable/healthz`、`/feetable/tables/1` |
| FabricWorld | 失败的 `CI and deploy` run 本身 | `fabricworld-linux` / `fabricworld-linux-amd64` | `/fabricworld/healthz`、`/fabricworld/new` |
| RecipeBox | 失败的 `CI and deploy` run 本身 | `recipebox-linux` / `recipebox-linux-amd64` | `/recipebox/healthz`、`/recipebox/new` |
| Yuyan | 失败的 `CI and deploy` run 本身 | `yuyan-linux` / `yuyan-linux-amd64` | `/yuyan/healthz`、`/yuyan/search` |

Yuyan 的发布脚本读取 gzip 流：第 3 步改为 `gzip -9 -c "$tmp/yuyan-linux-amd64" | ssh ali '/opt/yuyan/bin/deploy-release.sh <commit> <sha256>'`，SHA-256 仍为未压缩程序的值。

下列命令中 `<app>` 为小写应用名，`<commit>` 为完整 40 位提交号；不要上传本地构建的程序。

### 步骤

1. 核对现场，并从受限入口的 sudo 日志取出失败发布传入的 SHA-256（第二个参数）：

   ```sh
   ssh ali 'cat /opt/<app>/current-commit; systemctl is-active <app>
     d=$(ls -1t /opt/<app>/releases | head -1); echo "$d"; cat "/opt/<app>/releases/$d/result"; ls "/opt/<app>/releases/$d"
     journalctl --since today --no-pager | grep "deploy-release.sh <commit>" | tail -1'
   ```

2. 下载产物到新的临时目录并核对。本地 SHA-256 必须等于 sudo 日志中的值；五个应用的发布作业都直接使用同一次检查构建的 artifact。服务器上已安装的脚本须与该项目仓库 `deploy/deploy-release.sh` 哈希相同。

   ```sh
   tmp=$(mktemp -d)
   gh run download <run-id> -R Crashmere/<Repo> -n <artifact> -D "$tmp"
   shasum -a 256 "$tmp/<file>" /path/to/<Repo>/deploy/deploy-release.sh
   ssh ali 'sha256sum /opt/<app>/bin/deploy-release.sh'
   ```

3. 以管理员身份发布。成功时脚本输出 `Deployed <commit>`；刚启动时可能出现一次本机端口连接失败，是等待健康前的探测。

   ```sh
   ssh ali '/opt/<app>/bin/deploy-release.sh <commit> <sha256>' < "$tmp/<file>"
   ```

4. 只读验收：`current-commit` 为新提交，服务 active，直连 `/healthz` 与上表验收路径正常，按改动核对页面或 API，不写测试数据。
5. 清理：逐个确认本次超时留下的发布目录 `result` 为 failed 且没有 `metadata` 后，按完整目录名删除；删除本地 `$tmp`。保留成功的发布目录（含 `previous`）和 before-deploy 备份。

失败的 Actions run 会继续显示失败，这是预期结果。发布后不要再重跑它，否则会用同一程序再停服、备份一次。

### 尚未实施的改进

已出现：2026-09-24（多个应用）、2026-09-26（RecipeBox，本机从 GitHub 下载 artifact 也曾 TLS 握手超时一次，重试成功）。Yuyan 已经压缩上传并放宽到 600 秒。若另外四个应用超时频繁出现，可照 Yuyan 的 `deploy/deploy-release.sh` 修改它们由 root 管理的发布脚本、测试与 CI，属于授权表中的先确认事项。

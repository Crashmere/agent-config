<a id="共性问题与全局方案"></a>
# Common Issues and Shared Solutions (Symptom Index)

This index routes shared multi-application issues to focused topic files so troubleshooting loads only the relevant domain. When one project encounters an issue that may affect multiple applications, document the solution in the matching topic file and update this index; project docs should retain only project-specific parameters and a link here.

For each issue, document symptoms and decision criteria, affected applications, handling steps, cleanup and acceptance checks, and unimplemented improvements. Rewrite superseded entries; Git preserves history.

## Topic files

| Topic file | Covers |
| --- | --- |
| [Host, OS, systemd, SQLite, and drivers](issues-host-os.md) | SQLite snapshot locks, AlmaLinux/Ubuntu notices, Snap unit-cache/download issues, GPU kernel cache, host freezes, wait-online, 203/EXEC, Nouveau-to-NVIDIA live transition |
| [Gateways, reverse-SSH tunnels, proxy, and upload throughput](issues-network-proxy.md) | Gateway IPv4 replacement, reverse-SSH key/stale session/outages/UDP comparison, sing-box `AF_NETLINK` sandbox, HTTP/2 upload flow control |
| [Portal, shared auth, Nginx, and web/mobile UI](issues-web-portal.md) | Refresh flashes, Portal API mismatch, shared auth 1 MiB limit & cookie renewal, iPhone icons/blur, manifest MIME, root collector, HTTPS 403, Nginx gzip/regex, stale-tab chunks |
| [Releases, doc sync, backups, and media processing](issues-release-backup-media.md) | Hard-link backup sandbox, doc sync errors & worktrees, local release & shutdown timeout, recovery/cold-backup staging, disk growth, media task limits, FFmpeg/CUDA/HDR/MP4 |

## Issue index and legacy anchor map

Existing project documentation links to anchors in this file; keep these entries intact so external links resolve cleanly to the right topic file.

### Host, OS, systemd, SQLite, and Drivers

- <a id="persistent-sqlite-snapshot-locks-with-healthy-reads"></a>[Persistent SQLite snapshot locks with healthy reads](issues-host-os.md#persistent-sqlite-snapshot-locks-with-healthy-reads)
- <a id="distribution-specific-inspection-and-login-notices"></a>[Distribution-specific inspection and login notices](issues-host-os.md#distribution-specific-inspection-and-login-notices)
- <a id="host-wide-stale-unit-cache-warnings-after-snap-refresh"></a>[Host-wide stale unit-cache warnings after Snap refresh](issues-host-os.md#host-wide-stale-unit-cache-warnings-after-snap-refresh)
- <a id="gpu-kernel-caches-in-a-read-only-service-sandbox"></a>[GPU kernel caches in a read-only service sandbox](issues-host-os.md#gpu-kernel-caches-in-a-read-only-service-sandbox)
- <a id="whole-host-freezes-with-no-retained-panic"></a>[Whole-host freezes with no retained panic](issues-host-os.md#whole-host-freezes-with-no-retained-panic)
- <a id="network-startup-waits-for-an-unplugged-interface"></a>[Network startup waits for an unplugged interface](issues-host-os.md#network-startup-waits-for-an-unplugged-interface)
- <a id="nas-asset-script-fails-with-203exec"></a>[NAS asset script fails with 203/EXEC](issues-host-os.md#nas-asset-script-fails-with-203exec)
- <a id="official-snap-downloads-are-too-slow"></a><a id="官方-snap-下载过慢"></a>[Official Snap Downloads Are Too Slow](issues-host-os.md#official-snap-downloads-are-too-slow)
- <a id="nvidia-modules-cycle-after-replacing-nouveau-live"></a>[NVIDIA modules cycle after replacing Nouveau live](issues-host-os.md#nvidia-modules-cycle-after-replacing-nouveau-live)

### Gateways, Reverse-SSH Tunnels, Proxy, and Upload Throughput

- <a id="interface-discovery-blocked-by-a-service-sandbox"></a>[Interface discovery blocked by a service sandbox](issues-network-proxy.md#interface-discovery-blocked-by-a-service-sandbox)
- <a id="public-gateway-ipv4-replacement-leaves-old-access-settings"></a>[Public gateway IPv4 replacement leaves old access settings](issues-network-proxy.md#public-gateway-ipv4-replacement-leaves-old-access-settings)
- <a id="restricted-reverse-ssh-key-is-unreadable"></a>[Restricted reverse-SSH key is unreadable](issues-network-proxy.md#restricted-reverse-ssh-key-is-unreadable)
- <a id="stale-reverse-ssh-session-blocks-tunnel-recovery"></a>[Stale reverse-SSH session blocks tunnel recovery](issues-network-proxy.md#stale-reverse-ssh-session-blocks-tunnel-recovery)
- <a id="reverse-ssh-transport-outages-and-retry-storms"></a><a id="tcp-comparison-findings"></a><a id="independent-udp-tunnel-comparison"></a>[Reverse-SSH transport outages and retry storms](issues-network-proxy.md#reverse-ssh-transport-outages-and-retry-storms)
- <a id="http2-flow-control-slows-streaming-uploads"></a>[HTTP/2 Flow Control Slows Streaming Uploads](issues-network-proxy.md#http2-flow-control-slows-streaming-uploads)

### Portal, Shared Authentication, Nginx, and Web/Mobile UI

- <a id="a-data-refresh-flashes-or-resets-the-page"></a>[A data refresh flashes or resets the page](issues-web-portal.md#a-data-refresh-flashes-or-resets-the-page)
- <a id="portal-api-list-does-not-match-the-service"></a><a id="门户-api-列表与服务不一致"></a>[Portal API List Does Not Match the Service](issues-web-portal.md#portal-api-list-does-not-match-the-service)
- <a id="shared-authentication-incorrectly-blocks-large-requests"></a><a id="统一认证误拦大请求"></a><a id="shared-authentication-rejects-large-requests"></a>[Shared Authentication Incorrectly Blocks Large Requests](issues-web-portal.md#shared-authentication-incorrectly-blocks-large-requests)
- <a id="cookie-renewal-with-shared-authentication"></a><a id="统一认证的-cookie-续期"></a>[Cookie Renewal with Shared Authentication](issues-web-portal.md#cookie-renewal-with-shared-authentication)
- <a id="missing-iphone-home-screen-icons-after-shared-authentication"></a><a id="统一认证后-iphone-桌面图标缺失"></a>[Missing iPhone Home-Screen Icons After Shared Authentication](issues-web-portal.md#missing-iphone-home-screen-icons-after-shared-authentication)
- <a id="web-manifest-returns-a-non-json-content-type"></a>[Web Manifest Returns a Non-JSON Content Type](issues-web-portal.md#web-manifest-returns-a-non-json-content-type)
- <a id="root-collector-cannot-switch-to-the-application-user"></a><a id="root-采集进程无法切换应用用户"></a>[Root Collector Cannot Switch to the Application User](issues-web-portal.md#root-collector-cannot-switch-to-the-application-user)
- <a id="https-page-loads-but-saving-returns-403"></a><a id="https-页面能打开但保存返回-403"></a>[HTTPS Page Loads but Saving Returns 403](issues-web-portal.md#https-page-loads-but-saving-returns-403)
- <a id="top-of-an-iphone-home-screen-page-appears-blurry"></a><a id="iphone-主屏幕页面顶部发虚"></a>[Top of an iPhone Home-Screen Page Appears Blurry](issues-web-portal.md#top-of-an-iphone-home-screen-page-appears-blurry)
- <a id="nginx-does-not-compress-javascript-returned-by-a-go-program"></a><a id="go-程序返回的-javascript-没有被-nginx-压缩"></a>[Nginx Does Not Compress JavaScript Returned by a Go Program](issues-web-portal.md#nginx-does-not-compress-javascript-returned-by-a-go-program)
- <a id="nginx-location-regex-quantifiers-require-quoting"></a>[Nginx Location Regex Quantifiers Require Quoting](issues-web-portal.md#nginx-location-regex-quantifiers-require-quoting)
- <a id="dynamic-module-loading-fails-in-a-stale-tab-after-deployment"></a><a id="发布后旧标签页的动态模块加载失败"></a>[Dynamic Module Loading Fails in a Stale Tab After Deployment](issues-web-portal.md#dynamic-module-loading-fails-in-a-stale-tab-after-deployment)

### Releases, Documentation Sync, Backups, and Media Processing

- <a id="photo-hard-link-backups-fail-in-a-systemd-sandbox"></a><a id="systemd-沙箱下照片硬链接备份失败"></a>[Photo Hard-Link Backups Fail in a systemd Sandbox](issues-release-backup-media.md#photo-hard-link-backups-fail-in-a-systemd-sandbox)
- <a id="first-documentation-sync-for-a-new-application-cannot-find-the-directory"></a><a id="新应用首次文档同步找不到目录"></a>[First Documentation Sync for a New Application Cannot Find the Directory](issues-release-backup-media.md#first-documentation-sync-for-a-new-application-cannot-find-the-directory)
- <a id="ssh-failure-is-treated-as-missing-sync-provenance"></a><a id="sync-provenance-ssh-failure"></a>[SSH Failure Is Treated as Missing Sync Provenance](issues-release-backup-media.md#ssh-failure-is-treated-as-missing-sync-provenance)
- <a id="minimal-gateway-rewrites-unchanged-documentation"></a>[Minimal gateway rewrites unchanged documentation](issues-release-backup-media.md#minimal-gateway-rewrites-unchanged-documentation)
- <a id="local-release-fails"></a><a id="本机发布失败"></a>[Local Release Fails](issues-release-backup-media.md#local-release-fails)
- <a id="shutdown-timeout-blocks-release"></a>[Shutdown Timeout Blocks Release](issues-release-backup-media.md#shutdown-timeout-blocks-release)
- <a id="recovery-capture-rejects-escaped-systemd-names"></a>[Recovery Capture Rejects Escaped Systemd Names](issues-release-backup-media.md#recovery-capture-rejects-escaped-systemd-names)
- <a id="cold-backup-misses-a-dependent-writer-during-resumption"></a>[Cold Backup Misses A Dependent Writer During Resumption](issues-release-backup-media.md#cold-backup-misses-a-dependent-writer-during-resumption)
- <a id="cold-staging-fails-later-content-verification"></a>[Cold Staging Fails Later Content Verification](issues-release-backup-media.md#cold-staging-fails-later-content-verification)
- <a id="retired-portal-backup-integrations"></a>[Retired Portal Backup Integrations](issues-release-backup-media.md#retired-portal-backup-integrations)
- <a id="documentation-sync-rejects-a-linked-git-worktree"></a>[Documentation Sync Rejects a Linked Git Worktree](issues-release-backup-media.md#documentation-sync-rejects-a-linked-git-worktree)
- <a id="backup-and-release-history-keeps-consuming-disk"></a><a id="备份与发布历史持续占用磁盘"></a>[Backup and Release History Keeps Consuming Disk](issues-release-backup-media.md#backup-and-release-history-keeps-consuming-disk)
- <a id="native-media-processing-exhausts-a-service-task-limit"></a>[Native media processing exhausts a service task limit](issues-release-backup-media.md#native-media-processing-exhausts-a-service-task-limit)
- <a id="ffmpeg-recompiles-cuda-kernels-for-every-short-job"></a>[FFmpeg recompiles CUDA kernels for every short job](issues-release-backup-media.md#ffmpeg-recompiles-cuda-kernels-for-every-short-job)
- <a id="unnecessary-video-transcoding-and-hdr-tone-mapping"></a>[Unnecessary video transcoding and HDR tone mapping](issues-release-backup-media.md#unnecessary-video-transcoding-and-hdr-tone-mapping)
- <a id="native-mp4-initialization-scans-inefficient-layouts"></a>[Native MP4 initialization scans inefficient layouts](issues-release-backup-media.md#native-mp4-initialization-scans-inefficient-layouts)
- <a id="seek-heavy-video-previews-and-canceled-candidate-generation"></a>[Seek-heavy video previews and canceled candidate generation](issues-release-backup-media.md#seek-heavy-video-previews-and-canceled-candidate-generation)

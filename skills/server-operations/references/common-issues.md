<a id="共性问题与全局方案"></a>
# Common Issues and Shared Solutions

This file records issues that may affect multiple applications and their shared solutions: hosts and networking, shared Nginx, common release and backup patterns, runtime dependencies, and similar concerns. When one project encounters such an issue, document the solution here and cover every affected application. Project docs should retain only project-specific parameters and a link here rather than duplicating the procedure. Keep issues that affect only one application in that project's docs.

For each issue, document the symptoms and decision criteria, affected applications, handling steps, cleanup and acceptance checks, and improvements that have not yet been implemented. Rewrite an entry when its solution is superseded; Git preserves the history.

## Distribution-specific inspection and login notices

The `vps` image is AlmaLinux, whereas `ali` and `nas` use Ubuntu. An absent UFW executable or Ubuntu Nginx directory does not establish a host failure. The shared `inspect.sh` selects the installed firewall tool and inspects Nginx directories only when present. Verify both active firewall rules and cloud-side access separately.

Ubuntu runs `/etc/update-motd.d` scripts; AlmaLinux's SSH PAM configuration uses `pam_motd.so` and reads static `/etc/motd.d` snippets. `sync-docs.sh` maps the notice according to `SYNC_HOST=vps`; it must not introduce unconditional shell startup output, which can break command and file transfers. All applications on `ali` keep their existing notice and configuration; this difference concerns `vps` host bootstrap only.

## Host-wide stale unit-cache warnings after Snap refresh

On `nas`, `NeedDaemonReload=yes` appeared on all seven business services, Portal Web/collector, Nginx, both tunnels, SSH, chrony, and journald while those services remained healthy. A completed automatic `snapd` refresh added its mount links under `multi-user.target.wants` and `snapd.mounts.target.wants` just after systemd finished reloading. No persistent loaded fragment, drop-in, or generator source had changed afterward. The unit lookup cache was stale; the warning did not identify an unapplied Portal service change. The active `ali` and `vps` gateway services were unaffected.

Before clearing a host-wide warning, inspect concrete units' `FragmentPath`, `DropInPaths`, `SourcePath`, and `NeedDaemonReload`, compare effective settings with their current definitions, and check the unit lookup directories and relevant package-operation history. Use the last completed PID1 reload's JSON journal `__REALTIME_TIMESTAMP` when comparing modification times: ordinary second-resolution output cannot distinguish links created milliseconds after that reload from its own generated files. Runtime `/proc` and transient `/run` records are not persistent source edits. Review unexplained configuration changes before loading them.

Once the differences are accounted for and `systemctl list-jobs` shows no pending jobs, run `systemctl daemon-reload` under the shared NAS maintenance lock. This refreshes unit definitions and dependencies without restarting services. Confirm `NeedDaemonReload=no`, no failed units, and unchanged main PIDs, start timestamps, and restart counters for business services, Portal, Nginx, tunnels, and management services. Then check NAS LAN HTTPS and both gateway entrances. The NAS fix preserved all 15 checked service processes; no unit edit, service restart, or host reboot was needed.

## Interface discovery blocked by a service sandbox

On `vps`, sing-box configuration validation passed but startup failed with `initialize network: create netlink socket: address family not supported by protocol`. The unit inherited an Xray-oriented `RestrictAddressFamilies` allowlist containing only `AF_INET AF_INET6 AF_UNIX`; sing-box also uses `AF_NETLINK` to discover network interfaces. Add only that family to the affected unit, validate the unit, reload systemd, and confirm startup and a real proxy request. Do not remove the whole allowlist or grant `CAP_NET_ADMIN` for read-only interface discovery. The source is [the vps proxy unit](../assets/vps/vps-proxy.service); all applications on `ali` and `nas` remain unchanged. Apply the same diagnosis to another daemon only when its logs show this failure.

## Whole-host freezes with no retained panic

On `nas`, both the local console and network have stopped responding, including an overnight idle episode; the user also reports freezes under Windows. Retained logs contained no conclusive panic, OOM, or storage failure. Preserve journals and hardware state before further resets, check activity and SMART/self-test evidence, and investigate hardware/firmware alongside Linux drivers when the symptom crosses operating systems. An abruptly ending journal does not identify the exact freeze time or prove a thermal, memory, or driver cause.

The NAS mitigation and diagnostic sources are maintained in [freeze diagnostics](nas-host.md#freeze-diagnostics): balanced firmware profile, disabled boost, C1 idle restriction, and persistent minute health records. A later home check showed roughly 35 hours of uninterrupted idle operation and no minute-sampling gap beyond 61 seconds. This does not identify the cross-OS freeze cause or establish loaded-service reliability. The user deferred further investigation and accepts proceeding with migration under that residual risk. If freezing recurs, preserve available evidence and inspect hardware/firmware alongside drivers; do not automatically reboot or change several power settings together.

## Network startup waits for an unplugged interface

On `nas`, Wi-Fi acquired an address but `systemd-networkd-wait-online.service` timed out after two minutes, leaving the host degraded. The installer configured the unplugged Ethernet interface as required, and Netplan generated a wait-online command that waited for it as well as Wi-Fi. This host-level delay would affect every application depending on `network-online.target`.

Mark the unused Ethernet interface `optional: true` in Netplan and enable `dhcp4` so it works when a cable is connected. Keep the working Wi-Fi configuration and its credentials intact. The source for this host is `assets/nas/ethernet.yaml`; install it mode 0600 at `/etc/netplan/80-nas-ethernet.yaml`, run `netplan generate`, then `systemctl daemon-reload`, `networkctl reload`, and `networkctl reconfigure enp2s0`. Reset and start the failed wait-online unit, then verify Result=success and a new SSH connection. This procedure avoids restarting the active Wi-Fi interface.

## Restricted reverse-SSH key is unreadable

On a gateway, a correct NAS tunnel key can still be rejected if the dedicated user's root-owned `.ssh` directory is mode 0700: OpenSSH reads authorized keys as that user and cannot traverse the directory. Follow [the restricted identity ownership/modes](nas-migration.md#host-roles-and-traffic), preserving root write control and group read/traverse access. Inspect authentication logs and effective Match settings, then validate a fresh tunnel with only the permitted loopback listeners. Do not work around unreadable files by enabling a shell, widening forwarding, or changing administrator keys. This applies independently to ALI and VPS.

## Stale reverse-SSH session blocks tunnel recovery

On `vps`, public TLS and Nginx remained available while application requests timed out. The `nas` tunnel client had disconnected and was repeatedly failing with `remote port forwarding failed for listen port 18080`; the gateway's old `nas-tunnel` SSH session still held all reverse listeners, with unacknowledged TCP data and repeated retransmissions. NAS applications and the independent `ali` tunnel remained healthy. Listener existence alone did not establish a working forwarding path. This failure affects all eight applications behind that gateway and its loopback NAS management route; the VPS proxy on TCP 443 is independent.

After authorized diagnosis, identify the exact stale session from `ss -ltnp`, confirm its `nas-tunnel` identity and failed upstream response, and send TERM only to that session. The supervised NAS client can then reconnect without changing ports, keys, Nginx, or application data. Do not terminate the main sshd process or unrelated sessions. Use the healthy alternate gateway's existing loopback management route if the failed gateway cannot reach NAS, retaining the verified NAS host key.

The maintained gateway SSH drop-in sets `ClientAliveInterval 15` and `ClientAliveCountMax 3` only within `Match User nas-tunnel`. NAS already uses the corresponding client-side server-alive settings. The server-side probes bound retention of an unresponsive session to roughly 45 seconds rather than waiting for TCP retransmission exhaustion; they do not prevent network interruptions. Validate with `sshd -t` and effective per-user `sshd -T -C` settings, confirm administrator settings are unchanged, and reload sshd. Existing sessions retain their old settings, so reconnect the affected tunnel after the reload. Verify direct forwarded health, public login/TLS, anonymous API rejection, the alternate gateway, and unchanged proxy/runtime processes. [NAS migration](nas-migration.md#host-roles-and-traffic) records rollout scope.

## NAS asset script fails with 203/EXEC

On `nas`, `nas-lan-tls.service` failed with `203/EXEC` and `Permission denied` for an existing root-owned `renew-lan-tls.sh`. Documentation synchronization installs assets as mode 0644, so a unit cannot execute the script directly. [The maintained TLS unit](../assets/nas/nas-lan-tls.service) invokes `/bin/bash` explicitly; the script requires Bash's `pipefail`. A one-off `chmod` would be reset by the next documentation sync. NAS power and health units already invoke `/bin/sh` and need no change.

Install the corrected unit after source synchronization, verify it with `systemd-analyze verify`, reload systemd, and run the renewal service. Confirm `Result=success`, a valid leaf/CA chain, and the enabled timer. All eight NAS applications share this LAN certificate; ALI/VPS public renewal is unaffected.

<a id="门户-api-列表与服务不一致"></a>
## Portal API List Does Not Match the Service

This applies to each service's `docs/API.md` and `deploy/portal.json.apis`. A successful portal receipt proves only that the declaration was loaded. The shared validator checks formatting, ownership, and resource boundaries; it does not compare declarations with business routes to verify that APIs really exist or that the list is complete. Documentation that puts multiple APIs in one table cell, extracts only the first table, or treats actions on the same path as separate APIs can leave errors and omissions even when the files synchronize successfully.

Use the current service's route registration and handlers as the authority for methods, internal paths, parameter locations, return values, and authentication notes. Inspect every route file, including endpoints registered in loops. List restricted media variants such as main and thumb separately. In the project API table, put only one method and path on each row; the path field must not contain a query string, enumeration comma, second method, or body action. Put parameters and actions in the description. Compare the portal declaration and API table item by item, add omissions, and remove nonexistent or duplicate entries. Do not extract paths from narrative prose merely by splitting on spaces.

After correcting source files, run the shared `validate-portal.py` and separately compare the entry set and semantics with the implementation; format validation does not replace that review. For documentation-only changes, first confirm that the relevant route code matches the deployed version, then run `make portal` according to the [portal release protocol](portal.md#shared-validation-and-release-protocol) and synchronize documentation with `sync-docs.sh <project-name>`. Verify the hash actually loaded by the portal and the documentation source. Do not restart a business service for a documentation correction or validate the list with production write requests.

There is currently no release gate that automatically compares each business route with its declaration. An agent changing an interface must still perform the review above. If a feature has not yet been deployed, release its declaration with the corresponding program version; do not describe a source-only API as already available in production.

<a id="统一认证误拦大请求"></a>
<a id="shared-authentication-rejects-large-requests"></a>
## Shared Authentication Incorrectly Blocks Large Requests

Symptom: a business request returns 500 while the Nginx error log contains `client intended to send too large body`, `subrequest: "/_portal_device_check"`, and `auth request unexpected status: 413`, with no corresponding request in the application's journal. This was confirmed on 2026-10-01 when RecipeBox uploaded an approximately 4.4 MiB photo and reproduced in isolated Nginx: 1 MiB passed, while one additional byte failed.

Cause: a business location's `client_max_body_size` does not propagate to the authentication subrequest location. `/_portal_device_check` previously inherited Nginx's 1 MiB default. Even with `proxy_pass_request_body off` and an empty `Content-Length`, Nginx checks that limit against the original request length before entering the proxy phase. A 413 from the authentication subrequest is not an authentication result accepted by auth_request, so the client ultimately sees 500.

| Application | Existing ingress and program limits | Impact |
| --- | --- | --- |
| RecipeBox, FabricWorld | Nginx 26 MiB; 25 MiB per image | Normal images over 1 MiB could be blocked incorrectly |
| Yuyan | Nginx 26 MiB; 25 MiB per image; 16 MiB JSON | Large images and large document saves could be blocked incorrectly |
| Ledger | Nginx and JSON both 2 MiB | Requests of 1–2 MiB could not reach business validation |
| FeeTable | Nginx 2 MiB; JSON 64 KiB | Normal business input was unaffected; the service still inherited shared authentication |
| ServerPortal | Nginx and JSON both 1 MiB; performs its own authentication | Does not use this subrequest and was unaffected |

Keep the fix only in `location = /_portal_device_check` in shared `assets/nginx-portal-auth.conf`: set `client_max_body_size 0;` while retaining `internal`, `proxy_pass_request_body off`, the empty `Content-Length`, and cookie validation. Each business location and backend continues to enforce its own size limits. Do not disable limits at the entire http/server layer or bypass authentication for business APIs to work around the failure.

Before applying the change, use all existing locations, an isolated loopback Nginx, and synthetic authentication and business upstreams to verify normal and large requests for every site, missing and forged credentials, requests exceeding business ingress limits, authentication failures, cookie renewal, and the inability to reach the internal authentication path externally. Confirm that the bytes and hashes received by the business upstream match and that the authentication upstream receives no request body; isolated checks need not write real business data. Install to `/etc/nginx/snippets/portal-auth.conf` according to the authorization table, retain the old configuration, and gracefully reload only after `nginx -t` succeeds; restore the old configuration on failure. Then verify health for all six sites, public icon GET/HEAD requests, unauthenticated page redirects, and API rejection. Source, live server configuration, and the `/opt/server-context` copy must agree. See [current-state](current-state.md#portal-and-shared-authentication) for deployment status.

<a id="统一认证的-cookie-续期"></a>
## Cookie Renewal with Shared Authentication

Five business applications use Nginx auth_request to validate devices; a Set-Cookie header from the subrequest does not automatically become a response header on the business request. Shared `assets/nginx-portal-auth.conf` captures that header with auth_request_set and forwards it with add_header Set-Cookie ... always, while the portal renews directly. Anonymous, forged, expired, and revoked credentials must not receive a renewal cookie. Do not weaken the Secure, HttpOnly, SameSite=Strict, or Path=/ attributes.

An application location that adds its own add_header directive overrides inheritance of the entire parent add_header set and may prevent renewal while that application is in continuous use. Explicitly retain the shared renewal header at that layer and check the other shared response headers. Run `scripts/test-cookie-renewal.py --locations /etc/nginx/app-locations --auth <pending-shared-auth-file>` to verify, with an isolated loopback Nginx and synthetic upstream, that valid requests renew exactly once and invalid requests do not renew. The script currently covers five business applications; extend its cases when adding an application. Do not temporarily weaken production authentication or print real device credentials in test logs.

<a id="统一认证后-iphone-桌面图标缺失"></a>
## Missing iPhone Home-Screen Icons After Shared Authentication

Diagnosis: the HTTPS resource URLs and existing PNGs were valid, but icons for all five business applications also inherited device authentication. Access logs showed that an iPhone received 200 for the Ledger page icon/manifest but 401 for the separate `icon-192.png` request. Do not assume the system carries the current browser cookie when adding an item to the home screen.

| Application | Icon configuration |
| --- | --- |
| Ledger | 180 px touch icon, 192/512 px manifest icons, and public manifest, with exact GET/HEAD exceptions |
| FeeTable | 180 px touch icon, with Vite hashed paths matched against three brand icon names |
| FabricWorld | 180 px touch icon, `favicon.ico`, and project SVG, with exact GET/HEAD exceptions |
| RecipeBox | 180 px touch icon, `favicon.ico`, and project SVG, with exact GET/HEAD exceptions |
| Yuyan | `static/favicon.svg` and supplemental `static/apple-touch-icon.png`, with exact GET/HEAD exceptions |
| ServerPortal | Public `static/favicon.svg` and supplemental `static/apple-touch-icon.png`, served by the web layer |

Resolution: each business project's own `nginx-location.conf` disables auth_request only for its named brand icons (and Ledger's public manifest), restricted to GET/HEAD. FeeTable matches only the three icon names and their build hashes. Do not expose whole `assets` or `static` trees, user-uploaded media, or APIs. Yuyan and the portal generate opaque 180×180 PNGs from existing SVGs and declare apple-touch-icon in every page head; this does not change their login, cookie, or business-data behavior.

When adding or changing icons, verify the actual HTML href, built path, PNG dimensions, Content-Type, anonymous requests, and version query parameters. Before deployment, run `scripts/test-public-icons.py` (see `--help` for arguments) with an isolated loopback Nginx and synthetic upstream to verify the rules. Keep the script's five service-icon cases aligned with icon routes. The portal web layer serves its own static files, so also confirm that unauthenticated `/portal/api/overview` still returns 401. The final result of adding the site to an iPhone home screen still requires user confirmation and cannot be inferred from server checks.

The icons and HTML heads for all six sites are deployed with their current programs, and each project location maintains the anonymous icon rules. Run `nginx -t` before reloading after a rule change. See current-state for deployment status; future projects should include these icons by default according to conventions.

Every new website must include this configuration in its initial delivery. See the complete [website icon conventions](conventions.md#website-icons-and-home-screen-shortcuts). The general `scripts/check-site-icons.py` discovers icons and manifests from real HTML and verifies anonymous GET/HEAD, media types, file signatures, and PNG dimensions; central lists do not need updates when build hashes change.

For mobile acceptance, first authenticate in the browser and return to the corresponding application page before adding it to the home screen; do not create an application shortcut from the shared login page. Existing shortcuts may retain old icons and need to be added again. If a home-screen application asks for device authorization again, follow the normal login flow without weakening cookie security attributes. See Apple's [Configuring Web Applications](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html) for PNG and page-icon rules.

<a id="root-采集进程无法切换应用用户"></a>
## Root Collector Cannot Switch to the Application User

The ServerPortal root collector uses `serverportal` as its non-root primary group so that only the web user can access its Unix socket. On ALI, combining this setup with NoNewPrivileges and RestrictAddressFamilies/LockPersonality left the process CapEff/CapPrm without CAP_SETUID; runuser reported `cannot set user id: Operation not permitted`, and native backups could not start. A successful direct run as root in a terminal does not prove that the operation works inside the unit.

For that historical ALI collector, explicitly configure `AmbientCapabilities=CAP_SETUID` while retaining the other sandbox settings. The current NAS Portal no longer runs backups or switches users; its unit has removed this capability. The historical source remains in ServerPortal Git history. The ALI system was checked for primary group, seccomp properties, and capabilities, and native snapshots were verified under an equivalent sandbox. Native backup units already running as fixed application users require no change. Current NAS backups use independent administrator SSH tooling; see [Agent backup and recovery](backup-recovery.md).

<a id="https-页面能打开但保存返回-403"></a>
## HTTPS Page Loads but Saving Returns 403

TLS terminates at Nginx while application upstreams see loopback HTTP. A check using only `r.TLS` rejects a real browser HTTPS Origin; stripping the explicit port through `$host` also breaks VPS HTTPS 8443. Keep one trusted `X-Forwarded-Proto: https` value and full `$http_host`, and configure the precise NAS/ALI/VPS Origin set in affected applications and Portal. Portal additionally requires a supplied Origin to equal the actual HTTPS Host/port. Check the specific rejected request and installed route source before changing a certificate or authentication rule. [HTTPS](https.md#authentication-and-proxy-trust) owns trust boundaries; do not remove Origin checks or relax CORS to hide a forwarded-header error. Validate affected wrong-origin/protocol/header cases with synthetic requests, not production writes.

<a id="iphone-主屏幕页面顶部发虚"></a>
## Top of an iPhone Home-Screen Page Appears Blurry

User report: after being added to the home screen from iPhone Chrome, Ledger, FeeTable, FabricWorld, and RecipeBox had a blurry area near the time and battery indicators, while Yuyan did not. The key code difference was positioning. Yuyan used `position: sticky; top: 0`; three older services used normal-flow headers. Although Ledger's header sat outside its inner content scroller and looked persistent, its CSS still used `position: relative`, which is not equivalent to a fixed or sticky element recognized by WebKit.

A [WebKit engineer's explanation of top-color extension](https://bugs.webkit.org/show_bug.cgi?id=301756#c2) says the browser extends a solid background from fixed or sticky elements at the viewport edge to avoid a gap above them during scrolling; the iPhone browser UI itself has a softer blur underneath. This provides a mechanism for the observed code difference. Desktop browser validation alone cannot prove that the home-screen appearance is fixed on a particular iPhone.

Resolution: all four services use a solid `sticky; top: 0` header. Ledger retains its internal content scrolling and header dimensions; the other three retain document scrolling, route restoration, and modal scroll locking. Applications receiving new sticky headers reserve top space for controls and anchors, and FabricWorld's desktop photo bar now sticks below navigation. All four viewports also match Yuyan and use the default safe-area layout. The user confirmed on a real device that removing only Ledger's `viewport-fit=cover` did not fix the blur, changing FeeTable to sticky fixed its top area, and then changing only Ledger from relative to `sticky; top: 0` fixed it as well. This confirms the role of explicit sticky positioning in this issue; safe-area settings alone are neither the cause nor the solution. Equivalent FabricWorld and RecipeBox changes have been released and passed browser regression checks but have not received separate real-device confirmation. No Nginx, PWA identity, database, or system-status-bar changes are needed.

Validate at two levels. Desktop Chromium/WebKit checks only the header position, scrolling, navigation, forms, and modals at 320/375 px and desktop sizes; it does not reproduce or prove removal of the native iPhone blur layer. Confirm the final result on a real iPhone by reopening the site from the home screen and scrolling in both directions. Prefer fully closing and reopening that home-screen window to load new HTML/CSS before clearing site data. The pages and Ledger manifest use no-cache, and no Service Worker is registered. Code differences alone cannot establish the native rendering cause for a particular iOS version, and they do not justify adding supposedly universal CSS to "disable system blur."

For safe-area behavior, see WebKit's official [Designing Websites for iPhone X](https://webkit.org/blog/7929/designing-websites-for-iphone-x/): `viewport-fit=cover` extends the page to the screen edges and requires developers to account for safe-area insets. These applications currently use the default layout.

<a id="官方-snap-下载过慢"></a>
## Official Snap Downloads Are Too Slow

A single connection from the server to the Snap Store may run at only tens of KB/s. During the 2026-09-27 Certbot installation, core24 and snapd completed, while the 75 MB Certbot package remained slow. The issue was the download path, not a post-installation startup failure.

On a trusted workstation, prefetch the package for the exact architecture and revision from the same Snap Store download URL, using ranges if needed. Verify the complete file against the store metadata's SHA3-384, transfer it to a separate staging directory on the server as `certbot_<revision>.snap`, and run `snap download certbot --revision=<revision> --target-directory=<directory>` there. This verifies and reuses the complete file while downloading the official assertion chain. After confirming that the `.assert` file exists, cancel the still-incomplete duplicate download and wait for it to exit, then run `snap ack <file.assert>` and `snap install <file.snap> --classic`. Never use `--dangerous` to skip signature verification. Check the version, publisher, stable tracking, and renewal timer, then remove only these identified installation staging files while retaining rollback configuration.

This method replaces only file transfer; official signatures and snap still manage installation and updates. Do not delete or rewrite snapd's internal cache, partial files, or state database. If the service is actually failed, troubleshoot it from the logs first.

<a id="systemd-沙箱下照片硬链接备份失败"></a>
## Photo Hard-Link Backups Fail in a systemd Sandbox

This applies to historical ALI native snapshots for FabricWorld, RecipeBox, Yuyan, and any explicitly authorized operation that hard-links data files into its backup directory. SQLite-only snapshots are unaffected. FabricWorld and RecipeBox were fixed and verified by the following method on 2026-09-24; Yuyan used this configuration at installation on 2026-09-26 and was verified through its unit. NAS full external backups cold-copy files instead and do not use this timer/hard-link workflow.

Symptom: `<app>-backup.service` fails every time, with `hard-link media backup: link ... invalid cross-device link` in the journal. The initial backup made manually with runuser during installation does not use the unit sandbox and therefore does not expose the issue. The two applications consequently failed for five days from their first scheduled runs before discovery.

Cause: the unit used `ProtectSystem=strict` and `ReadWritePaths=/opt/<app>/data /opt/<app>/backups`, causing systemd to bind-mount the two directories as separate mount points. Linux cannot create hard links across mount points, even when the underlying filesystem is the same, and returns EXDEV.

Fix: use `ReadWritePaths=/opt/<app>` in the backup unit, placing data and backups under one writable mount point. Everything else under `/opt/<app>` is owned by root, and file permissions already prevent the application user from writing there, so the effective write scope does not change. Update `deploy/<app>-backup.service` in the project repository and push it, install it to `/opt/<app>/config/`, then run `systemctl daemon-reload`; the resident service unit does not need a change. Failed runs leave no incomplete backup directory, so there is nothing to clean up.

When verifying an authorized legacy native-snapshot run, `systemctl show <app>-backup.service -p Result` must report success, its `daily-*` directory must contain `manifest.json`, and the photo hard-link count (`stat -c %h`) must be greater than 1. Verify the real unit sandbox, not only a manual runuser command. Do not enable a NAS backup timer for this check; [manual full backups](nas-migration.md#manual-full-backups) define the NAS operation.

<a id="go-程序返回的-javascript-没有被-nginx-压缩"></a>
## Nginx Does Not Compress JavaScript Returned by a Go Program

This applies to applications that enable compression with `gzip_types` in their application location, currently only Yuyan. Ledger, FeeTable, FabricWorld, and RecipeBox do not set `gzip_types` and inherit nginx.conf's default of compressing only HTML, so they are unaffected. Configure every future Go application that enables `gzip_types` in the same way.

Symptom: CSS and JSON responses include `Content-Encoding: gzip`, but `.js` does not. Yuyan behaved this way from installation, but it was discovered only after the single-page application release on 2026-09-26. The application script transferred 297 KB uncompressed (approximately 100 KB compressed), and the editor chunk transferred approximately 930 KB uncompressed (approximately 290 KB compressed), adding more than one second at the server's approximate 0.5 MB/s downstream rate.

Cause: Go's `http.FileServer` returns `.js` as `text/javascript; charset=utf-8` based on the extension, while `gzip_types` listed only `application/javascript`.

Resolution: include both `text/javascript` and `application/javascript` in `gzip_types` inside the application's own location. Update and push the project's `deploy/nginx-location.conf`, install it to `/opt/<app>/config/nginx-location.conf`, run `nginx -t`, and then run `systemctl reload nginx`; the shared server does not need a change.

Acceptance: request a `.js` resource from the application with `curl -sI -H 'Accept-Encoding: gzip'` and confirm `Content-Encoding: gzip`. After reloading, verify direct and proxied health checks and deep links for all five applications. Yuyan was fixed and verified this way on 2026-09-26.

<a id="发布后旧标签页的动态模块加载失败"></a>
## Dynamic Module Loading Fails in a Stale Tab After Deployment

After content-hashed frontend chunks are replaced with a Go program, an already open tab may still request lazy-loaded files from the previous version. This was confirmed in Yuyan on 2026-09-28: the Mermaid core, dependency chunk, and code-reading module all returned 404 in Nginx logs, while the new files referenced by the current manifest existed. This is an invalidated version reference, not a diagram-syntax error.

During diagnosis, first obtain the exact filename from the browser or access log and compare it with the current build manifest and loopback response. A 404 means the file does not exist; a 401 or login page points to shared authentication, and a connection error points to networking. Do not infer a Mermaid syntax problem from dynamic-import error text or expose static directories to bypass authentication and restore script loading.

The page shell must be revalidated while hashed resources may be cached long-term. Clearing only a JavaScript loading Promise cannot clear the browser's recorded failed module; provide an explicit full-page reload action. Editing forms must first wait for uploads and saves to complete, including input added while saving. Preserve the page and draft on failure or conflict instead of reloading immediately. When observing chunk-load failures, retain the original Promise rejection so callers do not believe the module loaded successfully. Handling only the route layer is insufficient because diagram and language modules contain nested imports.

Current scope: Yuyan uses a global prompt and reloads after saving; browser checks exercise real 404s for core and nested chunks. Ledger's lazy-loaded routes already have an error component and the “重新加载页面” (Reload page) action. Current FeeTable, FabricWorld, and RecipeBox sources do not use dynamic imports. ServerPortal uses embedded static scripts without this lazy-loading chain. This change does not alter application release scripts, asset directories, or shared Nginx. When introducing lazy loading later, test stale tabs, loading failures, and recovery of unsaved input together.

<a id="新应用首次文档同步找不到目录"></a>
## First Documentation Sync for a New Application Cannot Find the Directory

`sync-docs.sh` should create `/opt/<app>/docs` directly for a new application. The old implementation first ran find to scan for AppleDouble files; when the destination did not yet exist, find returned nonzero and pipefail stopped the script before installation. The service itself and completed targets were unaffected.

The shared script now prescans only directories that exist, and the later `install -D` creates the destination during the first synchronization. `--check` also permits a missing new destination and reports BEHIND. Read failures in existing directories remain errors and are not hidden with `|| true`. This was verified during AICalendar's real first documentation synchronization on 2026-10-07, while existing projects used the same flow. After the fix, retry only the incomplete target; there is no need to release the program again.

<a id="sync-provenance-ssh-failure"></a>
## SSH Failure Is Treated as Missing Sync Provenance

The initial `SOURCE` read in `sync-docs.sh` used `|| true` to allow first synchronization. This also hid an SSH timeout, leaving an empty recorded commit and starting another connection instead of stopping. An empty result after a transport failure cannot establish that provenance is absent or that the managed drift check can be skipped.

The remote command now checks whether `SOURCE` exists and reads it only when present. SSH failures and errors reading an existing file abort the local script immediately, including in `--check` mode. A genuinely missing file still permits first synchronization. This applies to shared context and every project's documentation on NAS, VPS, and other explicitly selected targets. Select the trusted `nas-via-vps` alias for authorized NAS maintenance from outside the LAN; do not change host-key verification, authentication, or public exposure to work around a connection timeout.

<a id="本机发布失败"></a>
## Local Release Fails

See [Local releases](release.md) for the current release entry point, identity, artifact reuse, and rollback. On upload failure, first check local SSH, networking, and release logs. The service continues running until verification passes; do not repeatedly stop it for network failures. Repair a declaration failure separately with `make portal`.

If the log already says `Deployed` and a later public HTTPS check times out, the program may have been released successfully. First compare `current-commit`, the unit and loopback health, and the local `last-deployment.json` `program` field. Then retry only the read-only unauthenticated API check, expecting 401. Once that succeeds, record the local release receipt without redeploying the program. The portal release was handled this way on 2026-09-30.

If new SSH connections from the maintenance workstation occasionally time out, first use a short `ConnectTimeout` for a read-only connectivity check. Documentation synchronization may temporarily use OpenSSH ControlMaster to reuse an established connection, while retaining the original SSH alias, identity, and host-key verification; close the temporary connection afterward. A connection timeout alone does not prove an application or server failure and does not justify restarting a service or changing authentication.

## Recovery Capture Rejects Escaped Systemd Names

On VPS, a full gateway capture failed with `invalid entry` before emitting its manifest because a systemd directory name contained the literal escape `\x2d`. POSIX filenames may contain backslashes; treating every backslash as a path separator rejects valid systemd configuration. This affects the shared recovery tool on NAS and VPS, including all applications captured by the combined workflow.

The maintained validator accepts literal backslashes on POSIX hosts while still rejecting NUL, absolute paths, parent traversal, non-canonical paths, duplicate entries and non-directory ancestors. Hosts with backslash path separators continue to reject them. Entry errors report the path and relevant metadata. A focused package/read-back/materialization regression preserves an escaped systemd directory and its symlink and checks traversal rejection. Build the maintained tool locally and hash-verify its installation on both hosts before retrying; do not rename production units or omit configuration roots. A pre-manifest failure leaves unaccepted NAS staging and no recovery package; inspect it and verify renewal/runtime state before a fresh capture, preserving failed material under the backup runbook.

## Cold Backup Misses A Dependent Writer During Resumption

On NAS, stopping `serverportal-agent.service` also stopped `serverportal.service` through its `Requires` dependency. Inspecting each unit immediately before stopping it therefore recorded Portal as already inactive and omitted it from resumption. The cold capture remained consistent, but Portal stayed stopped until the agent's independent health check detected and restarted it.

The recovery tool records and persists the complete initial active set before stopping any unit, stops timers before services, resumes that saved set and verifies every saved unit is active before clearing the paused receipt. This applies to all registered NAS writers and avoids order-dependent omissions. After a backup, compare every previously active unit and application/Portal health independently; a successful compression phase does not prove service resumption. Do not restart originally inactive units or recapture an already completed cold stage to repair a runtime omission.

## Cold Staging Fails Later Content Verification

The first real NAS/VPS external-backup attempt failed during compression because a staged AICalendar database no longer matched its content-addressed filename. The streaming cold-copy checksum had passed, but a later independent read-back confirmed a different SHA-256. No external package was published. The failure does not establish production database corruption or a hardware root cause; NAS's earlier freeze history remains relevant to investigation, not proof.

Archive mismatch errors include the logical path, staged blob, actual/expected byte count and hashes. Independently verify staged blob hashes and preserve failed staging/partial archives. Check application resumption and storage/kernel evidence, then resolve the integrity issue before an agreed fresh capture. Do not bypass hashes, modify the recorded manifest to accept changed bytes, reuse a claimed stage or overwrite production data. The external backup remains outstanding until a complete package passes publication/read-back acceptance.

## Retired Portal Backup Integrations

Removing Portal backup APIs can leave application-owned status widgets, links, polling or maintenance instructions behind. Aura had a web summary polling `/portal/api/recovery` and linking to `/portal/#/backups`; removing that component and its styles eliminates both requests and the broken navigation. Audit all inventory applications' frontend/server sources, entry build assets and `deploy/portal.json`, then compare the NAS declaration hashes with their maintained sources. Portal login assets are public; inspect business pages only through the trusted [view tunnel](conventions.md#agents-viewing-live-pages), without extracting user cookies.

Also check current READMEs, operations and limitation documents for daily native scheduling, Portal-driven backup, internal routine destinations and cache exclusions. NAS agent full packages include stored derivatives, while native historical formats may omit them. Dated verification records and archived design baselines describe their historical scope; do not erase valid evidence or present it as current readiness. Keep native compatibility commands and inactive unit files, but verify that backup services are inactive and timers are neither active nor enabled. FabricWorld and RecipeBox cleanup timers remain separate application writers, not backup jobs. Documentation synchronization targets active `nas`/`vps`, leaving frozen `ali` unchanged. See [Agent backup and recovery](backup-recovery.md) for the maintained capture/restore workflow.

<a id="备份与发布历史持续占用磁盘"></a>
## Backup and Release History Keeps Consuming Disk

First identify the host and actual activation phase. NAS has manual full external backups and temporary upgrade-only local protection; before cutover ALI still has legacy backup/retention tasks. The old daily count or five-upgrade limit does not authorize deleting historical or unresolved materials.

| Material | Contract |
| --- | --- |
| NAS routine recovery sets | One dual-host package staged/compressed/verified on NAS, then copied/read-back verified externally; successful task staging removed, no internal fallback or rotation |
| NAS `/var/lib/server-upgrades` and disposable candidate-check data | Complete upgrade protection; delete that job only after runtime and affected-data acceptance, retain failed/unverified protection |
| ALI `daily-*`, old `before-deploy-*` and release history | Legacy schedules stop during cutover; preserve existing copies rather than applying NAS rules retroactively |
| Manual/migration/recovery archives, `/opt/backup-exports`, maintenance Mac `backups/` | No automatic deletion or overwriting; inspect private manifests before selecting a recovery point |
| Historical Portal encrypted/incremental sets | Retain required keys and complete parent chains; folder age alone does not establish safe deletion |
| Application data/history/trash/media | Application-owned behavior, not backup rotation; full NAS backups include stored state even if the application can later rebuild or expire it |
| System logs/temporary files | Ordinary host maintenance may continue, but must not target real backup directories or root-private upgrade protection |

An unavailable external volume must leave agent backup unavailable. If the final export appears on NAS internal storage, inspect `/etc/server-recovery.json`, mount/UUID and the NAS role marker rather than accepting a fallback. Deliberate task staging under root-private `/var/lib/server-backups` is allowed only for the single-package external workflow; it is not a completed backup. A directory existing at the configured mountpoint is not proof that a drive is mounted.

Unexpected local data protection usually means failed/interrupted acceptance or cleanup. Read the release/upgrade receipts and journals before deleting anything; health alone does not prove no lost data. [Retention](retention.md) owns temporary-success deletion and historical ALI preservation, while [NAS migration](nas-migration.md#manual-full-backups) owns external recovery sets.

Measure actual disk blocks and file counts by directory, not only logical file sizes. Historical media snapshots may share inodes with live files; separate `du` totals can double-count them and removing one link does not free the whole logical size. Old backups can retain media removed from production. Portal's registered cleanup previews are not an automatic scheduler and must not include unresolved upgrade protection or unregistered root/private archives.

Cloud backup retention is independent of application/source-directory cleanup. [ALI HBR](current-state.md#cloud-backup) is stopped during migration without deleting historical cloud recovery points; stopping a client does not prove a provider-side billing/schedule item was canceled. Real backup deletion or restoration still follows the shared authorization table.

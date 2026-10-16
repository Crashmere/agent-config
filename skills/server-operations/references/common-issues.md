<a id="共性问题与全局方案"></a>
# Common Issues and Shared Solutions

This file records issues that may affect multiple applications and their shared solutions: hosts and networking, shared Nginx, common release and backup patterns, runtime dependencies, and similar concerns. When one project encounters such an issue, document the solution here and cover every affected application. Project docs should retain only project-specific parameters and a link here rather than duplicating the procedure. Keep issues that affect only one application in that project's docs.

For each issue, document the symptoms and decision criteria, affected applications, handling steps, cleanup and acceptance checks, and improvements that have not yet been implemented. Rewrite an entry when its solution is superseded; Git preserves the history.

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

The ServerPortal root collector uses `serverportal` as its non-root primary group so that only the web user can access its Unix socket. On the current host, combining this setup with NoNewPrivileges and RestrictAddressFamilies/LockPersonality leaves the process CapEff/CapPrm without CAP_SETUID; runuser reports `cannot set user id: Operation not permitted`, and native backups cannot start. A successful direct run as root in a terminal does not prove that the operation works inside the unit.

Explicitly configure `AmbientCapabilities=CAP_SETUID` in the collector unit while retaining the other sandbox settings. The source is ServerPortal's `deploy/serverportal-agent.service`. The live system was checked for primary group, seccomp properties, and capabilities, and native snapshots were verified under an equivalent sandbox. The five existing backup units that run as fixed application users require no change. Future verification must initiate a backup through the real collector rather than checking only `id` or `true`.

<a id="https-页面能打开但保存返回-403"></a>
## HTTPS Page Loads but Saving Returns 403

This applies to Ledger, FeeTable, FabricWorld, and RecipeBox. TLS terminates at shared Nginx, so Go sees local HTTP. The former check used only `r.TLS`, causing an HTTPS Origin from the browser to be classified as cross-site. All four projects have been fixed consistently; see [Shared HTTPS proxy trust boundaries and acceptance](https.md). Changing only the Nginx certificate does not complete the migration, and removing Origin validation or relaxing CORS is not an acceptable workaround. The applications listen only on loopback, Nginx overwrites X-Forwarded-Proto, and each application accepts only one valid value from a loopback peer. Regression coverage includes IPv4/IPv6, direct TLS, cross-site requests, and forged headers.

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

This applies to FabricWorld, RecipeBox, and any future application that hard-links data files into its backup directory. Ledger and FeeTable back up only SQLite and are unaffected. FabricWorld and RecipeBox were fixed and verified by the following method on 2026-09-24; Yuyan used this configuration at installation on 2026-09-26 and was verified through its unit.

Symptom: `<app>-backup.service` fails every time, with `hard-link media backup: link ... invalid cross-device link` in the journal. The initial backup made manually with runuser during installation does not use the unit sandbox and therefore does not expose the issue. The two applications consequently failed for five days from their first scheduled runs before discovery.

Cause: the unit used `ProtectSystem=strict` and `ReadWritePaths=/opt/<app>/data /opt/<app>/backups`, causing systemd to bind-mount the two directories as separate mount points. Linux cannot create hard links across mount points, even when the underlying filesystem is the same, and returns EXDEV.

Fix: use `ReadWritePaths=/opt/<app>` in the backup unit, placing data and backups under one writable mount point. Everything else under `/opt/<app>` is owned by root, and file permissions already prevent the application user from writing there, so the effective write scope does not change. Update `deploy/<app>-backup.service` in the project repository and push it, install it to `/opt/<app>/config/`, then run `systemctl daemon-reload`; the resident service unit does not need a change. Failed runs leave no incomplete backup directory, so there is nothing to clean up.

Verify that `systemctl show <app>-backup.service -p Result` reports success after `systemctl start <app>-backup.service`. The new `daily-*` directory must contain `manifest.json`, and the hard-link count for photos (`stat -c %h`) must be greater than 1. After enabling a backup timer for a new application, run it once through the unit in the same way; a manual runuser backup is not a substitute.

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

<a id="本机发布失败"></a>
## Local Release Fails

See [Local releases](release.md) for the current release entry point, identity, artifact reuse, and rollback. On upload failure, first check local SSH, networking, and release logs. The service continues running until verification passes; do not repeatedly stop it for network failures. Repair a declaration failure separately with `make portal`.

If the log already says `Deployed` and a later public HTTPS check times out, the program may have been released successfully. First compare `current-commit`, the unit and loopback health, and the local `last-deployment.json` `program` field. Then retry only the read-only unauthenticated API check, expecting 401. Once that succeeds, record the local release receipt without redeploying the program. The portal release was handled this way on 2026-09-30.

If new SSH connections from the maintenance workstation occasionally time out, first use a short `ConnectTimeout` for a read-only connectivity check. Documentation synchronization may temporarily use OpenSSH ControlMaster to reuse an established connection, while retaining the original SSH alias, identity, and host-key verification; close the temporary connection afterward. A connection timeout alone does not prove an application or server failure and does not justify restarting a service or changing authentication.

<a id="备份与发布历史持续占用磁盘"></a>
## Backup and Release History Keeps Consuming Disk

This applies to every registered application. On 2026-10-01, the code corresponding to deployed versions, live release scripts, directories, timers, and recent task results were checked. The current retention mechanisms are listed below; do not generalize the limit of 14 daily backups to the entire backups directory.

| Data | Current mechanism and growth conditions |
| --- | --- |
| Business-application `daily-*` | After a new backup succeeds, retain only the latest 14 complete daily backups. The count is bounded, but each backup still grows with its database and media |
| All applications' `before-deploy-*` and `releases/` | At 05:00 each day, follow [release-material retention](retention.md) to retain 5 complete backups and 3 successful releases while protecting the current version and its backup; skip while busy |
| Manual and pre-migration/pre-recovery snapshots; `/opt/backup-exports` | No automatic rotation; retained indefinitely after creation. Do not infer that they can be deleted from their names |
| ServerPortal `exports/` | Manually generated full bundles or old incremental chains; no automatic expiry, and old incrementals depend on parent chains |
| FabricWorld and RecipeBox in-data cleanup | Daily cleanup first removes trash and removed media older than 30 days, unbound/orphan uploads and upload staging older than 24 hours, then ordinary idempotency results older than 7 days. FabricWorld's Ledger-source records are retained indefinitely. Modification history for live business records has no separate rotation |
| Yuyan in-data history and media | History is retained for 30 days and cleaned daily at 03:00 Beijing time without a minimum retained count, with catch-up at startup after downtime. Current and trashed document bodies are retained independently; trash must be emptied manually. Images and attachments are reclaimed only after their final reference has been absent continuously for one hour, with scans every minute. Expired history restarts the grace period, while renewed references or uploads reset it. Existing backups follow their own policies. Directory locks coordinate backup and reclamation; see Yuyan OPERATIONS |
| Ledger and FeeTable deletions | Ledger soft-deleted records are retained indefinitely; FeeTable deletes records directly. Pages freed by SQLite deletes may be reused but do not necessarily shrink the file immediately, and production databases are not vacuumed automatically |
| System logs and temporary directories | Nginx rotates daily with 14 compressed copies; rsyslog rotates weekly with 4 copies; journald uses its default space limits; tmpfiles defaults to 10 days for `/tmp` and 30 days for `/var/tmp`, with system exclusions. None of these clean application history under `/opt` |

The portal provides manual candidates, preview, and confirmation only for registered backups/releases of business applications. It protects the running version, the two most recent entries, and incomplete or unknown formats, and rechecks the release lock and backup service at execution. It is not an automatic scheduler and does not cover the portal's own release history, export bundles, or root maintenance staging directories. Daily rotation in the three media applications does not reclaim directories left without a manifest after an abnormal interruption. Applications make a best effort to clean up normal failures; verify that any residue is unused before removing it.

For diagnosis, first check `df -h /`, each application's backup-service Result and last execution time, and `systemctl list-timers --all`, then measure actual disk blocks and file counts by directory. FabricWorld, RecipeBox, and Yuyan share inodes between media and backups through hard links. Adding separate du results double-counts them, while one cross-directory du attributes shared blocks to whichever directory it visits first. To estimate reclaimable space, deduplicate against production data first and then calculate the backup's additional use. Removing one link does not mean its full logical size is freed, and historical backups may retain photos already removed from production data.

On 2026-10-01, the user authorized implementation of [automatic retention of release materials](retention.md). Manual milestones, complete portal export chains, and business history still require separate handling. The automatic task processes only completed batches with a trusted source. Inspect its journal for protection and skip reasons; a retained count above 3 or 5 does not by itself prove that rotation failed. The host also has [30-day cloud backups](current-state.md#cloud-backup), whose expiration rules do not clean source directories. Native consistency-preserving backups must still be retained.

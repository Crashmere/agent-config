<a id="当前服务器与应用清单"></a>

# Current Server and Application Inventory

AICalendar's web redesign and backup scope changes were last checked on 2026-10-09; health and authentication entry points for all seven sites were last checked on 2026-10-07 (Beijing time). The baseline host inventory was checked on 2026-09-28: the host, five business applications, ServerPortal, and shared HTTPS entry point were all rechecked in the live environment, and the user confirmed successful login on the actual device. The web keyboard and focus policy was updated and deployed on 2026-09-30; see shared configuration below. Backups and data retention were reviewed read-only on 2026-10-01, also confirming that Alibaba Cloud Backup was already running; see cloud backup below. This is a current snapshot that may be overwritten with updates, not a historical log. Add or revise entries only for shared architecture, application inventory, runtime, data layout, backup or recovery, authentication or access, deployment, or another durable operational contract; keep routine feature and visual release history in Git or project design records. Recheck volatile versions and states; unlisted resources must not be assumed absent.

<a id="主机"></a>
<a id="host"></a>

## Host `ali`

| Item | Current state |
| --- | --- |
| Connection | Local OpenSSH alias `ali`; administrator root, port 22; obtain the real address from trusted SSH configuration and do not put it in the public repository |
| Platform | Alibaba Cloud ECS / KVM, x86_64, Ubuntu 26.04.1 LTS |
| Resources | 2 vCPU, approximately 1.7 GiB visible memory, 40 GiB ext4 root disk; no swap or separate application-data mount |
| Kernel | 7.0.0-30-generic when checked; not a version that must be pinned when rebuilding |
| Time | Asia/Shanghai; chrony provides time synchronization, NTP synchronized |
| SSH | Public-key authentication enabled, password authentication disabled, root login allowed |
| HTTPS | Nginx 1.28.3, port 443 TLS 1.2/1.3 + HTTP/2; trusted Let's Encrypt public IPv4 certificate, no domain. Port 80 serves ACME and 308 redirects; HTTP proxy inspection remains available only on loopback |
| Host firewall | UFW inactive; this does not establish the state of all netfilter rules or cloud-side protection |
| Cloud security group | SSH/HTTP/HTTPS reachability verified externally; complete rules have not been audited through the cloud API. Verify separately before future rule changes |
| Package sources | Signed Ubuntu repositories, currently using Alibaba Cloud's internal mirror; do not copy that mirror address when changing providers |

## Host `vps`

Prepared on 2026-10-29 as a separate AlmaLinux KVM VM; business applications remain on `ali`. `vps` runs a personal sing-box proxy, documented in [Personal proxy operations](vps-proxy.md). The local administrator alias is `ssh vps`, with strict host-key verification and an explicitly selected local key. Obtain its public address from local SSH configuration, not this public repository. See [VPS operations](vps-host.md) for configuration sources, update/reboot checks, recovery, and documentation synchronization.

| Item | Current state |
| --- | --- |
| Platform | AlmaLinux 9.8, x86_64, KVM; upgraded from the provider's 9.7 image |
| Resources | 2 vCPU; Intel Xeon SierraForest guest model; approximately 1 GiB visible memory, 544 MiB swap |
| Storage | 20 GiB QEMU virtual disk; separate approximately 1.4 GiB ext4 `/boot`, remainder ext4 `/`; no separate data mount |
| Kernel | Updated to 5.14.0-687.61.1.el9_8; inspect the live version after subsequent automatic updates |
| Time and network | Asia/Shanghai, chrony NTP; NetworkManager, DHCP on `eth0`, public IPv4, provider DNS; no configured global IPv6 |
| SSH | Root public-key authentication; password and keyboard-interactive authentication disabled; X11 forwarding disabled |
| Host firewall | Firewalld enabled, `eth0` in `public`, SSH and TCP 443 allowed; proxy reachability verified externally, complete cloud-side protection not audited |
| Update policy | Signed AlmaLinux BaseOS/AppStream/Extras; `dnf-automatic.timer` applies security updates; automatic reboot disabled |
| SELinux | Disabled by image boot parameter `selinux=0`; `audit=0` also retained |
| Services and backups | sing-box 1.14.4, `vps-proxy.service`, VLESS + REALITY + Vision on TCP 443, retained `xray` runtime user; private recovery archive and manual off-host copy; retired Xray service disabled; no business applications, Nginx, or scheduled application backups |
| Client configuration | Yuyan document 833 (`VPS配置`) on `ali` is the maintained connection/settings record; future changes directly revise it. User confirmed working iPhone Hiddify access on China Mobile 5G on 2026-10-29 |
| Context | `/opt/server-context`, `/opt/AGENTS.md`, `/root/AGENTS.md` link, and PAM static MOTD; synchronized from agent-config |

## Host `nas`

The ASUS G733 laptop was prepared as a separate Linux host on 2026-10-28. It runs Ubuntu 26.04.1 LTS, with a Ryzen 9 5900HX, 64 GB installed RAM, and two 1 TB NVMe SSDs. Both SSDs contribute to the linear LVM group `nasvg`; its `root` logical volume holds the single ext4 `/` filesystem, approximately 1.86 TiB before filesystem overhead. `/data` is an ordinary directory in the same filesystem, so applications share capacity without choosing a disk. The Intel SSD retains the EFI partition, and the Samsung SSD holds a separate 2 GiB ext4 `/boot` to preserve Secure Boot compatibility. This layout has no disk redundancy; failure of either SSD can make the entire root filesystem unavailable. The local SSH alias `nas` uses root public-key authentication and a dedicated maintenance-computer key. Obtain the address from local SSH configuration.

Networking currently uses Wi-Fi and DHCP; a router reservation has not been configured. The Ethernet interface supports DHCP and is optional during startup. Charging stops at 80%, CPU energy preference is `balance_power`, and lid closure keeps the host running. Following repeated freezes, including a user-reported history under Windows, the diagnostic power policy uses firmware `balanced`, disables CPU boost, and restricts the `acpi_idle` driver to C1. The running host disables deeper states through sysfs; the GRUB setting applies the limit before userspace on subsequent boots. NVIDIA runtime power management remains automatic. After the diagnostic reboot, the user reported approximately 14 W while idle, compared with the earlier approximately 11 W under `quiet` and unrestricted CPU idle states; measurement durations were not provided, and these are not load measurements. Persistent journal synchronization is set to 15 seconds, and sysstat plus temperature/fan sampling runs every minute. The cause remains unresolved; a successful short test or boot does not establish overnight stability. Time is Asia/Shanghai with chrony synchronization; automatic Ubuntu security updates and weekly SSD TRIM are enabled. See [NAS laptop operations](nas-host.md) for configuration sources, diagnostics, and recovery.

No business application, public HTTPS entry point, VPN, or application backup schedule has been installed on `nas`. All applications and the remaining host-specific sections below describe `ali`; preparation of `nas` and `vps` has not switched production.

## Resource Comparison: `vps` and `ali`

Resources were rechecked read-only on 2026-10-29. VM topology describes the guest view, not guaranteed physical core allocation. Package/kernel versions and disk usage can change; use `inspect.sh` to recheck them.

| Item | `vps` | `ali` |
| --- | --- | --- |
| OS | AlmaLinux 9.8, DNF | Ubuntu 26.04.1 LTS, APT |
| Virtualization | KVM | Alibaba Cloud ECS / KVM |
| CPU | 2 vCPU, Xeon SierraForest guest model; topology advertises 2 cores / 1 thread per core | 2 vCPU, Xeon Platinum guest model; topology advertises 1 core / 2 threads |
| Guest CPU features | AVX, no advertised AVX2/AVX-512 | AVX2 and AVX-512 advertised |
| Visible RAM / swap | Approximately 1 GiB / 544 MiB | Approximately 1.7 GiB / no swap |
| Virtual disk | 20 GiB; separate ext4 `/boot` and `/` | 40 GiB; ext4 `/`, EFI partition |
| SSH and host firewall | Key-only root login; active firewalld, SSH and TCP 443 | Key-only root login; UFW inactive; full cloud rule audit outstanding |
| Automatic updates | DNF security updates, no automatic reboot | Ubuntu security updates, no automatic reboot |
| Workload and backups | Personal sing-box proxy; manual off-host configuration archive, no scheduled backup | Eight applications; local native backups and Alibaba Cloud Backup |

`ali` provides more memory and twice the disk capacity for the current applications. `vps` is suited to small additional services within its memory/storage limits. CPU model labels and idle load do not establish relative throughput; no CPU, storage, or bandwidth benchmark was run for this comparison.

<a id="已部署应用共享变更必须逐行核对"></a>

## Deployed Applications (Check Every Row for Shared Changes)

| Application / source | URL prefix → local listener | Directory / identity | systemd | Documentation and verification |
| --- | --- | --- | --- | --- |
| Ledger / [Crashmere/Ledger](https://github.com/Crashmere/Ledger) | `/ledger/` → `127.0.0.1:18080` | `/opt/ledger`; runtime `ledger`, deployment `ledger-deploy` | `ledger.service`, `ledger-backup.service`, `ledger-backup.timer` | `/opt/ledger/docs/README.md`; direct `/healthz`, proxied `/ledger/healthz`, deep link `/ledger/search` |
| FeeTable / [Crashmere/FeeTable](https://github.com/Crashmere/FeeTable) | `/feetable/` → `127.0.0.1:18081` | `/opt/feetable`; runtime `feetable`, deployment `feetable-deploy` | `feetable.service`, `feetable-backup.service`, `feetable-backup.timer` | `/opt/feetable/docs/README.md`; direct `/healthz`, proxied `/feetable/healthz`, route shell `/feetable/tables/1` (use an existing monthly table or the home page for browser acceptance) |
| FabricWorld / [Crashmere/FabricWorld](https://github.com/Crashmere/FabricWorld) | `/fabricworld/` → `127.0.0.1:18082` | `/opt/fabricworld`; runtime `fabricworld`, deployment `fabricworld-deploy` | `fabricworld.service`, `fabricworld-backup.service`, `fabricworld-backup.timer` | `/opt/fabricworld/docs/README.md`; direct `/healthz`, proxied `/fabricworld/healthz`, deep link `/fabricworld/new` |
| RecipeBox / [Crashmere/RecipeBox](https://github.com/Crashmere/RecipeBox) | `/recipebox/` → `127.0.0.1:18083` | `/opt/recipebox`; runtime `recipebox`, deployment `recipebox-deploy` | `recipebox.service`, `recipebox-backup.service`, `recipebox-backup.timer` | `/opt/recipebox/docs/README.md`; direct `/healthz`, proxied `/recipebox/healthz`, deep link `/recipebox/new` |
| Yuyan / [Crashmere/Yuyan](https://github.com/Crashmere/Yuyan) | `/yuyan/` → `127.0.0.1:18084` | `/opt/yuyan`; runtime `yuyan`, deployment `yuyan-deploy` | `yuyan.service`, `yuyan-backup.service`, `yuyan-backup.timer` | `/opt/yuyan/docs/README.md`; direct `/healthz`, proxied `/yuyan/healthz`, deep link `/yuyan/search` |
| ServerPortal / [Crashmere/ServerPortal](https://github.com/Crashmere/ServerPortal) | `/portal/` → `127.0.0.1:18085` | `/opt/serverportal`; Web user `serverportal`, root Unix socket collector | `serverportal.service`, `serverportal-agent.service` | `/opt/serverportal/docs/README.md`; loopback `/healthz`; public root redirect, login, and protected APIs |
| AICalendar / [Crashmere/AICalendar](https://github.com/Crashmere/AICalendar) | `/aicalendar/` → `127.0.0.1:18086` | `/opt/aicalendar`; runtime `aicalendar`, deployment `aicalendar-deploy` | `aicalendar.service`, `aicalendar-backup.service`, `aicalendar-backup.timer` | `/opt/aicalendar/docs/README.md`; direct `/healthz`, proxied `/aicalendar/healthz`, page `/aicalendar/` |
| Aura / [Crashmere/Aura](https://github.com/Crashmere/Aura) | `/aura/` → `127.0.0.1:18087` | `/opt/aura`; runtime `aura`, deployment `aura-deploy` | `aura.service`, `aura-backup.service`, `aura-backup.timer` | `/opt/aura/docs/README.md`; direct `/healthz`, proxied `/aura/healthz`, page `/aura/`; initial health, Portal declaration, icons, authentication, and backup checks passed on 2026-10-27 |

| Application | Data | Daily backup (Beijing time, +0–5 minute randomized delay, retain 14) | Deployment | Other |
| --- | --- | --- | --- | --- |
| Ledger | SQLite | 03:00, consistent snapshot | Local make deploy | — |
| FeeTable | SQLite | 03:15, consistent snapshot | Local make deploy | — |
| FabricWorld | SQLite + photos | 03:30, snapshot + photo hard links + SHA-256 manifest | Local make deploy | libvips; CPUQuota=100%, MemoryMax=640M; isolated recovery drill uses 19082 |
| RecipeBox | SQLite + photos | 03:45, same as FabricWorld | Local make deploy | libvips; CPUQuota=100%, MemoryMax=640M, photo quota 5 GiB; drill uses 19083 |
| Yuyan | SQLite (including document templates/content snippets) + drawing packages, images, and attachments | 04:00, same as FabricWorld; manifest v2 covers all registered media, recovery supports v1 image backups | Local make deploy (gzip) | CPUQuota=100%, MemoryMax=384M (GOMEMLIMIT=320MiB, MemoryCurrent includes page cache); drill uses 19084 |
| ServerPortal | Device-state JSON, private configuration; compressed archives of whole-server materials | Manually create independent full packages from the web page, default recovery, optional all/docs; export packages are not automatically rotated or synchronized off-host by the portal | Local build, administrator deployment | New packages need no key; the age private key needed by old packages is retained locally; no arbitrary SQL/command interface |
| AICalendar | SQLite (activities, annotations, import batches, full conversations, and original-material chunks/indexes) | 04:15, consistent snapshot of the three core tables, retain 14; user confirmed full conversation archives are not backed up | Local make deploy | MemoryMax=192M, GOMEMLIMIT=144MiB; separate manual-import credential; demo uses 19086 |
| Aura | SQLite catalog + immutable SHA-256 photo/video originals | 04:35, +0–2 minute jitter, consistent snapshot + original hard links + shared-format SHA-256 manifest; retain 14 | Local make deploy | libvips, ExifTool, FFmpeg; rebuildable previews and incomplete uploads excluded from backups; Universal Mac PhotoKit companion; Mac DMG and iOS sideload IPA published through the client-only GitHub workflow |

The seven business applications' browser pages/APIs use shared device authentication; authorized devices can perform each application's supported data operations. Each has an independent database and runtime/deployment identity, and all automatic backups reside on the same disk. On 2026-09-27, a separate data archive of all applications was downloaded to the maintenance computer and verified (see manual data archives below). Application scripts do not proactively synchronize off-host; the host also has Alibaba Cloud file backup (see cloud backup below). before-deploy backups and deployment history are cleaned under [Automatic Retention of Deployment Materials](retention.md): the latest 5 complete backups and latest 3 successful deployments are retained, with the current version and its corresponding backup protected. `server-context` is a documentation package, not an application. Project docs govern exact procedures and limits.

AICalendar's production database has begun storing manually imported real history and complete archives. Check actual sources and coverage through the import client's `status` and query interfaces; do not keep private statistics in shared documentation. The browser uses portal authentication; only `/aicalendar/ingest/v1/` uses this application's separate Bearer credential. The server stores SHA-256, while the plaintext token and client configuration reside only in `~/.config/aicalendar/` on the maintenance computer, outside Git. The import credential supports calendar-summary import/verification and full-conversation chunk upload, query, and download; it does not provide calendar-summary export or web-annotation editing. The manual `ai-calendar-import` skill organizes data locally, saving complete conversations and original materials before importing summaries by default, and preserving user-specified source labels. It does not configure automatic collection.

Full archives are gzip-compressed and uploaded in 384 KiB chunks. Identical content is deduplicated; changed content retains both old and new snapshots. Full message text and original bytes are retrievable, and original text does not automatically expire. All chunks and reading indexes remain in the same SQLite database, with no new data root or changes to Nginx limits. Core schema 1 remains unchanged, and archive_schema 1 has been explicitly added. The old program's pre-upgrade backup, post-migration check by both old and new programs, and checks that existing data was unchanged all passed. The old program can be rolled back to and can fully back up this database; it simply does not offer the archive API. Daily backups, pre-deployment snapshots, and deployment retention follow the original contract; the portal dynamically loads the updated resource declaration.

Yuyan attachment uploads now use streaming reception with no file-size limit. Only its /yuyan/api/attachments sub-location disables size checks and request-body buffering; it inherits authentication, and other requests retain their original limits. Temporary uploads go to the existing data/assets, with no new data root. Images and attachments are automatically collected only after a continuous hour without references from document bodies (including the recycle bin), history, templates/snippets, or media links. Scans run every minute; new references/uploads reset the timer. State reuses meta; shared directory locks for backup/upload and exclusive collection locks coordinate across processes, while existing backup hard links remain. Old backup programs must not run concurrently with the new collector; use gc --dry-run for diagnosis. Attachment reading previews use read-only `/api/attachments/{id}/preview` (types, text, and archive listings) and `/attachments/{id}/content` (restricted bitmap/PDF/audio/video formats), retaining device authentication; the download interface still forces downloads. PDF.js assets are embedded in the program and loaded on demand, and archives are not extracted to disk. There is no new server runtime, data directory, or backup contract; interface registrations ship with the project's portal.json. See Yuyan DESIGN 23.8 for detailed formats and limits.

Add one row to each table for every new application, including health verification. Remove retired applications from the current inventory; explicitly label the purpose of old instances still being migrated rather than pretending they are already offline.

Yuyan has implemented Excalidraw document drawings: packages and previews reuse assets/.bin, and `POST/GET /api/drawings` and `/drawings/{id}/preview|file` are registered in the project's portal declaration. They retain device authentication and ordinary request-size limits, with a 12 MiB package limit. Document bodies/history/templates protect packages and expand their image dependencies; unreferenced packages also protect images during their grace period. v2 backups cover all media, and unknown or damaged packages conservatively stop that GC run. The frontend and fonts ship with Go, adding no Node/browser runtime, data root, or database migration. See Yuyan WHITEBOARD.md for old-client editing protections, import/export, and program rollback constraints.

Yuyan history snapshots are retained for 30 days and cleaned by the application daily at 03:00 Beijing time, with no minimum number retained. Successful cleanup state is persisted, and startup catches up after downtime. Current document bodies, recycle-bin bodies, templates, and snippets are unaffected. When history's final reference is removed, media begin a new one-hour grace period. Pre-edit and pre-restore snapshots also follow the 30-day policy, and history IDs are not reused. There is no database migration or additional system task; use history-gc --dry-run for diagnosis. Existing backups follow their own retention policies. To extract older history after an isolated restore, inspect it read-only first and do not start the automatic cleanup service; see Yuyan OPERATIONS.

Ledger → FabricWorld integration: after creating a “副业 / 纺织” expense and obtaining user confirmation, the Ledger server creates fabric through /api/integrations/ledger on local port 18082. On success, the user can open the same-origin fabric editing page. LEDGER_FABRICWORLD_URL belongs to Ledger configuration and defaults to the local address; FabricWorld operations persist the transaction source to prevent duplicate creation on retries. The two services still have independent databases, backups, and deployments and do not share database permissions. Deploy FabricWorld before Ledger for updates; disable the integration before a long-term rollback to an old FabricWorld version, so its old cleanup logic does not delete source records. See both projects' docs for exact interfaces, verification, and recovery limits. FeeTable and shared Nginx are unaffected.

Yuyan's home page uses read-only `/api/stats` to display total body character counts for live documents and character counts on each knowledge-base card. A single query returns site-wide `chars` and `bookChars` indexed by knowledge-base ID; empty knowledge bases return 0. It retains device authentication and the existing `plain_text`, with no database migration, data-root change, or runtime change. The interface ships with the project's portal declaration.

The Yuyan reading page's “最近修改” feature uses read-only `/api/docs/{id}/recent-changes` to return the historical baseline from before the latest edit/restore, with optional revision validation. “补丁” markers are independent browser overlays; deleted content is displayed through baseline copies temporarily inserted by the browser. Neither is written into the document body. The feature retains 30-day history retention, device authentication, and native backups, with no database migration, data-root change, or shared Nginx change. The interface ships with the project's resource declaration; see Yuyan DESIGN 13.2 for interaction and comparison boundaries.

Yuyan records the database table-layout version (`meta.layout`/`min_layout`, separate from the document-body format version). When opening an old layout, the program migrates it step by step; `backup`/`daily` copy it unchanged. Step 2 moves the body columns in docs and doc_versions to the end. It shipped with 4cc06f4 on 2026-10-14 and was completed by the new program during `check` after the before-deploy backup (4.5 seconds). Earlier programs are compatible with the new layout, so rollback does not require database restoration. After migration, yuyan.db was approximately 322 MB, including approximately 129 MB of free pages available for subsequent writes and excluded from backups. There are no data-root, interface, unit, or backup-format changes; see Yuyan DESIGN 26.1 and OPERATIONS “数据库布局迁移” for design and operations.

Yuyan's state calendar is provided only through independent `calendar` blocks inside documents. Release `82d9e2c` on 2026-10-18 removed the standalone page/redirect, four period APIs, global store, portal entries, and agent tooling after the user authorized disposal of the old data. Layout 4 drops the retired table/index and raises `min_layout` to 4; rollback requires a layout-4-capable program with document calendar support. The fixed release failure handler restores only the previous binary, so a compatible fixed program is required after a completed incompatible migration. The step took 14 ms in both isolated rehearsal and production; full copy checks and read-only production comparisons preserved all other business rows. Document calendars retain `YYCAL1:` copy/direct import, undo, revision checks, pending drafts, search, history, templates, and exports. Saves/cancel-edits retain the `calendar-v1`/`drawing-v1` client protection. Desktop/mobile checks, production document roundtrip, consistent backup/check/health, portal collector, and public authentication passed; retired addresses return 404. Portal SHA-256 is `c8a7a8c906f2e4d84a5d2614537473d3c975f986b40ef0ba4d4be27b32ad23ff`. Existing backup retention, runtime identity, service, Nginx, and authentication settings are unchanged. See Yuyan DESIGN 27 and VERIFICATION 27.4.

Yuyan's reading page loads documents in segments when rendered HTML exceeds 256 KiB. Read-only `/api/docs/{id}/segments` returns several consecutive HTML segments and image dimensions keyed by version marker (immutable caching); `/api/docs/{id}/segments/matches` lists segment numbers containing search terms. `/view` without parameters still returns the whole document. Segmentation is held in memory with the rendering cache, with no database migration, data-root, runtime, or shared Nginx changes. It retains device authentication, and the interfaces ship with the project's portal declaration. After deployment with ba6c941 on 2026-10-14, the longest document's page decreased from 15 MB (gzip 2.4 MB) to 214 KB (gzip 49 KB); see Yuyan DESIGN 26.2.

Yuyan web pages load image display variants according to display width and screen density. Bitmaps larger than 128 KiB produce 640/1280/1920-wide copies in `data/derived/images`; photographic lossless originals use JPEG when they pass an SSIM check. Screens at 2× density and above have an additional set of size tiers; for screenshots, JPEGs that pass checks after 2×2 averaging (`.hidpi.jpg`) replace larger lossless variants at each tier. Originals remain unchanged and are still used for export, native backups, and viewing the original image. This directory is a deletable derived cache, registered as cache in the portal declaration and excluded from both native backups and portal backup packages. After restoration or deletion, the service regenerates it on one thread, using at most half a CPU. Variant files retain the `/yuyan/assets/` route and device authentication, with no database migration, unit, Nginx, or permission changes. A manifest version change clears and rebuilds the cache at startup. The upgrade to version 2 shipped with 26003ce on 2026-10-14 and processed 653 images in approximately 10 minutes: 628 had variants, including 167 with high-density-screen tiers; variants totaled 195 MiB. Images read and written during regeneration entered the page cache; MemoryPeak reached the 384M limit, while anon peaked at approximately 86 MiB, with no OOM. Use `yuyan images --data` for diagnosis; see Yuyan DESIGN 26.3.

Yuyan full-text search scans lowercase full text in the service process's memory, rereads only changed documents according to `revision/created_at`, and warms up after `serve` starts. Interfaces, results, and snippets are unchanged, with no database migration, data-root, runtime, or shared Nginx changes. Deployed with c19a48f on 2026-10-14: the startup log `search index ready` showed 526 documents, 17.9 MiB, and 201 ms; anon was approximately 80 MiB after startup, and search time decreased from 90–143 ms to 4–13 ms. See Yuyan DESIGN 26.4.

<a id="门户与统一认证"></a>

## Portal and Shared Authentication

ServerPortal is deployed at /portal/ and loopback port 18085; the public root redirects to the portal. The seven business applications' deploy/portal.json files are installed in their respective config directories. User passwords are stored only as bcrypt hashes, and device credentials use Secure/HttpOnly/SameSite=Strict cookies. Server-side authorization is permanent; existing valid authorizations have been migrated, and revocation still takes effect immediately. Cookies are set for 400 days and renewed on valid portal or business-application requests; actual browser retention remains subject to browser limits. New backups are unencrypted .tar.gz files; the recovery private key needed by old encrypted packages remains outside Git directories on the maintenance computer. Resource declarations can register the cache type (data subdirectories containing no database). Since 2026-10-14 (d5ee4a2), backup packages skip these directories in every scope; Yuyan's data/derived and Aura's data/derived, data/incoming, and data/work. The shared authentication include comes from assets/nginx-portal-auth.conf and forwards the authentication subrequest's Set-Cookie. Unauthorized pages redirect to login; APIs/media return 401, and authentication failures deny access. ACME and local deployment checks continue to work. No production cleanup was performed. Real portal full and incremental packages have been generated; the user deferred full-package download and recovery acceptance. Partial downloads are retained, waiting processes have stopped, and there is no automatic resume task. See ServerPortal docs/VERIFICATION.md and docs/RESTORE.md for backup coverage, recovery verification, and current limitations; see [Portal Maintenance](portal.md) for maintenance rules.

Permanent portal authorization and the compact layout are deployed. Actual program provenance is read from current-commit and releases/metadata; the documentation version is recorded in docs/SOURCE.

The shared authentication subrequest's erroneous blocking of large requests was fixed on 2026-10-01: `client_max_body_size 0` is set only in `/_portal_device_check`, request-body forwarding remains disabled, and each application's Nginx and program size limits remain unchanged. Large images in RecipeBox, FabricWorld, and Yuyan, large documents in Yuyan, and Ledger requests of 1–2 MiB are no longer incorrectly blocked by the authentication layer's default 1 MiB limit. Normal FeeTable input and the portal's own authentication were unaffected by the original issue. All 48 isolated checks across every location, 51 live read-only HTTP checks, and icon GET/HEAD checks for six sites passed. Nginx was gracefully reloaded; no applications were restarted and no synthetic business data was written. For the root cause and maintenance procedure, see [Shared Authentication Incorrectly Blocks Large Requests](common-issues.md#shared-authentication-incorrectly-blocks-large-requests).

The portal now dynamically loads services through controlled links in /opt/serverportal/registry.d, and the shared validator is installed at /opt/server-context/scripts/validate-portal.py. Root deployment scripts for the six business applications support the portal-check/portal protocol; updates no longer require manually editing a central registry array or restarting the collector. Invalid declarations retain the last valid configuration and report an error. Normal local deployments synchronize the declaration from the same commit; make portal updates only portal information. Each business application synchronizes its declaration through local make portal.

<a id="共享配置与所有权"></a>

## Shared Configuration and Ownership

All seven sites follow the [Web Keyboard and Focus Conventions](conventions.md#web-keyboard-and-focus). FeeTable, FabricWorld, RecipeBox, Yuyan, ServerPortal, and AICalendar have deployed ordinary Tab / Shift+Tab interception and removed control focus highlights across pages, forms, menus, and dialogs. Ledger retains its existing user-approved shortcuts and focus behavior; Yuyan preserves document/code indentation and table-cell navigation. Local Chromium and WebKit checks passed for pages, dialogs, narrow screens, and dark mode on five sites; editing exceptions and menu keys were verified separately. The global AGENTS and all seven project entry points record the default rule.

All seven sites provide their own favicon and 180×180 apple-touch-icon. Business sites allow anonymous GET/HEAD only for explicit brand icons (Ledger also includes a public manifest); pages, APIs, and user media retain authentication. AICalendar passed Chromium desktop and 375×667 narrow-screen interaction checks, and anonymous icon GET/HEAD checks passed for all seven sites. The final result of adding to the home screen on a real device awaits user confirmation. New websites follow the website icon conventions from their first delivery.

| Actual location | Maintained source / meaning |
| --- | --- |
| `/etc/nginx/nginx.conf` | Ubuntu package baseline configuration; record changes. Not owned by a business project |
| `/etc/nginx/sites-available/apps` | This skill's `assets/nginx-apps.conf` rendered with the public IPv4; shared 80/443 and loopback inspection servers |
| `/etc/nginx/sites-enabled/apps` | Enablement link pointing to the above |
| `/etc/nginx/app-locations/ledger.conf` | Points to `/opt/ledger/config/nginx-location.conf`; source in Ledger deploy |
| `/etc/nginx/app-locations/feetable.conf` | Points to `/opt/feetable/config/nginx-location.conf`; source in FeeTable deploy |
| `/etc/nginx/app-locations/fabricworld.conf` | Points to `/opt/fabricworld/config/nginx-location.conf`; source in FabricWorld deploy |
| `/etc/nginx/app-locations/recipebox.conf` | Points to `/opt/recipebox/config/nginx-location.conf`; source in RecipeBox deploy |
| `/etc/nginx/app-locations/yuyan.conf` | Points to `/opt/yuyan/config/nginx-location.conf`; source in Yuyan deploy |
| `/etc/nginx/app-locations/serverportal.conf` | Points to `/opt/serverportal/config/nginx-location.conf`; source in ServerPortal deploy |
| `/etc/nginx/app-locations/aicalendar.conf` | Points to `/opt/aicalendar/config/nginx-location.conf`; source in AICalendar deploy |
| `/etc/nginx/snippets/portal-auth.conf` | This skill's assets/nginx-portal-auth.conf, included only in the public port 443 server |
| `/opt/serverportal/registry.d/<app>.json` | Points to the application's own config/portal.json; created and validated by the restricted deployment protocol |
| `/opt/server-context/scripts/validate-portal.py` | This skill's script; resource-declaration policy shared by the maintenance computer and server |
| `/var/log/nginx/access.log`, `error.log` | Shared HTTP/HTTPS request logs; the journal mainly reflects the Nginx lifecycle |
| `/opt/server-context/` | Copies of this skill's documentation/templates/check scripts, managed by root |
| `/opt/AGENTS.md` | Copy of this skill's assets/AGENTS.md |
| `/root/AGENTS.md` | Points to `/opt/AGENTS.md` for discovery in root's login directory |
| `/etc/update-motd.d/30-server-context` | Interactive-login notice; non-interactive SSH does not rely on it |

`SOURCE` exists in `/opt/server-context/` and each project's `/opt/<app>/docs/`, recording each source commit and synchronization time. An application's `current-commit` records the running program version, while `config/portal-source.json` records the declaration's source commit and SHA-256. Neither represents the docs version; synchronizing only documentation or declarations must not rewrite the program version.

<a id="手工数据归档"></a>

## Manual Data Archives

On 2026-09-27, current consistent data snapshots of five applications were generated at the user's request, combined into `ali-data-<UTC-time>.tar.gz`, and downloaded over SSH to `~/ali/backups/` on the maintenance computer (outside all project Git repositories; directory permissions 0700, file permissions 0600). This was a manual download, not continuous synchronization to the maintenance computer; the host also has the Alibaba Cloud file backup described below. Exact generation times, each application's running commit, checksums, and recovery instructions are in the metadata, verification, SHA-256, and README files beside the archive. Neither the actual data nor these manifests go into the public repository.

The archive contains five databases, all registered photos/knowledge-base images, history and recycle-bin content within the databases, and historical migration snapshots from Ledger's data directory. Each application generated its own independent online consistent snapshot through its backup command; these are not a single transactional point in time across all five applications. No daily cleanup or rotation ran, and no services were stopped. After download, verification covered the full-package SHA-256, the complete file listing, native manifests for the three image applications, integrity/foreign keys for six databases, and coverage of database-registered images.

Individual application snapshots remain on the server under their respective `/opt/<app>/backups/manual-ali-data-*`; the combined package and unpacked directory are in root-private `/opt/backup-exports/`. They are not automatically rotated. Packaging uses tar --hard-dereference so images are independent files inside the archive. Download only completed archives; keep the .part name during transfer and rename to the final filename only after full-package verification. For recovery, first extract into a new isolated directory and verify according to the package's instructions; production restoration requires separate confirmation. This archive backs up data; application programs, runtime configuration, and credentials remain maintained through their respective rebuilding procedures.

<a id="云备份"></a>

## Cloud Backup

Confirmed from live processes and client job logs on 2026-10-01: Alibaba Cloud Backup's `hbrclient.service` and `hbrclientupdater.service` were running from `/opt/alibabacloud/hbrclient`. This is independent of the five applications' daily timers and ServerPortal's download workflow. Do not continue describing "application scripts do not proactively upload" as meaning the whole server has no automatic off-host backup.

- The latest three jobs all started at approximately 01:44 Beijing time; the latest job successfully completed an incremental backup. This time comes from runtime logs; the schedule configuration in the console has not been checked.
- The file-backup target is `/`, excluding system programs, virtual filesystems, and the client itself. The live exclusion list did not exclude the applications' `/opt` directory, so application data, daily/manual/before-deploy backups, releases, and portal exports are all within the scan scope.
- Job records specify a 30-day retention period, consistent with snapshot expiration times. Cloud space used, billing, retention-policy configuration in the console, and actual deletion after expiration have not been independently checked. Logical scan volume in logs is not physical cloud storage usage.
- Client startup logs show local old metadata being cleaned after 15 days; old file caches are reclaimed after successful jobs, and the latest logs retain the most recent two cache generations. The client directory is third-party managed data, not application junk.
- Cloud retention does not delete server source files. Unrotated releases/backups keep entering new snapshots; incremental deduplication does not replace source-directory retention policies. Direct cloud scans of active SQLite/WAL files are also not equivalent to consistent application snapshots. Prefer completed native backups for recovery and verify them according to project contracts.

<a id="其他软件后台任务和已知问题"></a>

## Other Software, Background Tasks, and Known Issues

- FabricWorld and RecipeBox share image runtime dependencies: libvips-tools/libvips42t64 8.18.0 and libheif-plugin-libde265 1.21.2 from Ubuntu's official signed repositories. /tmp is an approximately 868 MiB tmpfs; use persistent storage under /opt for image data and capacity verification. Do not infer /tmp capacity from free space on the root disk.
- Aura additionally uses FFmpeg 8.0.1 and ExifTool 13.50 from the signed Ubuntu repositories. They add no background services; all processing runs as aura.
- Existing tools: Git 2.53.0 and root's `/root/.local/bin/uv` 0.12.15. They are not runtime dependencies of any application, but do not delete them simply because applications do not need them. Node, Go, Docker, and sqlite3 are absent from PATH; there is no database service or self-hosted Actions runner.
- Ubuntu's nodejs, npm, and dependencies installed with them (492 packages in total, including eslint, webpack, and a set of X11/Mesa/Perl libraries) were uninstalled at the user's request on 2026-09-26. Node was not a dependency of any application, but often led development agents to believe they could build on the server. After removal, direct, proxied, and deep-link health checks for four applications were normal, and libvips remained available.
- System/vendor services include `aliyun` (Aliyun Assist), `hbrclient` / `hbrclientupdater` (Alibaba Cloud Backup), chrony, cron, sshd, journald/rsyslog, resolved, networkd, tuned, ModemManager, multipathd, and others; they were not created by the applications. See the preceding section for cloud backup details.
- `aegis.service` (Aegis Service, Alibaba Cloud security component) had long been failed before reboot (Result=signal); it returned to running after the 2026-09-24 reboot. Do not attribute a recurrence to the applications.
- System timers include apt-daily/upgrade, logrotate, sysstat, fstrim, filesystem checks, fwupd, MOTD/update notifier, and others. unattended-upgrades automatically installs security updates; automatic reboot is not configured.
- The host was rebooted on 2026-09-24 to apply a libc6 update: four applications, Nginx, and backup timers all recovered automatically, direct and proxied health checks were normal, and SSH returned in approximately 25 seconds. When /var/run/reboot-required appears in the future, follow the same method: first check that no deployment/backup is running, then verify each item after reboot.
- Deployment history and pre-deployment snapshots are automatically cleaned daily at 05:00 Beijing time by `ali-release-retention.timer`. It retains the latest 3 successful deployments and latest 5 complete pre-deployment backups, protecting the current version, its corresponding backup, and failed batches pending review. Daily backups share the cleanup lock; business daily backups still retain 14. Manual/migration backups and portal exports are outside the automatic scope. For configuration, the private receipt directory, and acceptance, see [Automatic Retention of Deployment Materials](retention.md).
- Certbot 5.8.0 uses the Certbot Project's official snap (latest/stable), with automatic snap updates. The IP certificate apps-ip is valid for approximately 160 hours; snap.certbot.renew.timer renews it automatically, and the deploy hook validates configuration before reloading Nginx. Initial issuance, the renewal drill, and checks of the actual timer service passed; see [Shared HTTPS](https.md) for configuration and rebuilding.
- There are no external availability or certificate-expiration alerts; inspect.sh checks whether the certificate has at least 48 hours remaining.

<a id="重新核对"></a>

## Rechecking

```sh
ssh ali 'cat /opt/AGENTS.md'
ssh ali 'bash /opt/server-context/scripts/inspect.sh'
~/agent-config/skills/server-operations/scripts/sync-docs.sh --check    # Run locally: check whether documentation copies match the repository
ssh ali 'for a in ledger feetable fabricworld recipebox yuyan aicalendar; do echo "$a $(cat /opt/$a/current-commit)"; done'
```

On 2026-10-07, all seven application services were healthy, and AICalendar's first daily backup and integrity check succeeded. The latest complete check of the other backups remained 2026-10-01. The failed list also contained old systemd-run identity/snapshot diagnostic units; do not confuse these with current business-application or scheduled-backup failures. If an application or backup unit appears, inspect its journal first. The inspection script does not access business databases, private keys, or account APIs. Full command output may contain public addresses, hostnames, and PIDs; retain only necessary conclusions and do not commit raw output directly to the public repository.

<a id="本机发布与验证"></a>

## Local Deployment and Validation

The eight applications use [Local Deployment](release.md): Server-deployment GitHub Actions is disabled. Aura additionally publishes public Mac DMG and unsigned iOS IPA assets from its hosted Apple-client workflow, authorized on 2026-10-27; this has no server access or production secrets. Former production Secrets and old CI public keys have been removed. Business deployment identities trust dedicated deployment public keys from the maintenance computer; the portal continues to use administrator SSH. Historical regression suites are retired; verify the current functionality locally as needed without retaining permanent tests by default. Scripts handle builds, uploads, and health/backup protections.

The portal's root-private releases/ and backups/ retain old programs and data/config snapshots taken after writes stop, and follow the shared 3/5 deployment retention policy. The private cleanup-receipt directory is also registered by ServerPortal/deploy/portal.example.json. The user's deferral of real backup download and recovery acceptance remains in effect.

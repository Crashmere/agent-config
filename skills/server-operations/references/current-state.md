<a id="当前服务器与应用清单"></a>
# Current Server and Application Inventory

**Migration phase: application and gateway cutover accepted on 2026-10-30 (Asia/Shanghai).** All eight application instances and authoritative data are active on `nas`. The primary `vps` HTTPS 8443 entrance and compatibility `ali` HTTPS 443 entrance forward to that same NAS state; VPS's sing-box proxy retains TCP 443. The maintenance Mac's NAS browser CA setup is user-confirmed; other device/browser acceptance and a first external backup remain outstanding. [NAS migration](nas-migration.md) owns the shared topology, manual backup, and recovery contract.

The cutover stopped ALI writers before final capture and verified all 4,066 transferred data entries against the frozen source. Eight isolated candidates passed native checks without creating additional upgrade snapshots. Cold post-first-start validation preserved all previous SQLite columns, row multiplicities and BLOB content, non-database files, and five Portal device grants before the next history-retention slot. Runtime, three TLS/authenticated entrances, branding, isolated upload/streaming/Range behavior, and the existing VPS proxy passed acceptance; maintenance gates were removed. These checks do not establish physical device CA trust, every user-device login, or an external recovery set.

NAS application units, Portal collector, Nginx, both reverse tunnels, and certificate/power maintenance are active and enabled. Each gateway exposes only its approved public entrance; application listeners and NAS management 22022 remain loopback-only. The trusted `nas-via-vps` alias supplements the unchanged LAN `nas` alias after LAN bulk SSH transfers timed out during migration. That transport symptom does not establish another hardware freeze. This inventory records roles and consequential acceptance limits; recheck listeners, units, source markers, and recovery receipts before maintenance.

<a id="主机"></a>
<a id="host"></a>
## Hosts

| Host | Current role | State and recovery boundary |
| --- | --- | --- |
| `ali` | Compatibility public HTTPS 443 gateway to NAS | Original application programs/configuration/data/history remain frozen; retired application, backup, retention, and HBR units are inactive and disabled at boot |
| `nas` | Only active application host, authoritative data, LAN local-CA HTTPS 443, Portal Web/collector | Both gateways reach this state; agent-owned external backup; verified T7 is attached but unmounted |
| `vps` | Primary public web HTTPS 8443 gateway and independent sing-box REALITY/Vision TCP 443 proxy | Application/management forwarding stays loopback-only; current private gateway/proxy recovery has not been independently captured |

Use the trusted SSH aliases `ali`, `nas`, and `vps`; retrieve real addresses and selected identities from local SSH configuration. Strict host-key verification remains enabled. NAS initiates reverse SSH connections to both gateways because this deployment does not use IPv6 ingress or NAT hole punching.

### ALI Platform

Ubuntu 26.04.1 LTS / amd64 on Alibaba Cloud ECS/KVM; 2 vCPU, approximately 1.7 GiB visible RAM, 40 GiB ext4 root, no swap or separate application-data mount. Nginx 1.28.3 and Certbot's official snap provide trusted public-IP HTTPS on 443, HTTP-01/redirects on 80, and loopback inspection. Chrony uses Asia/Shanghai; signed Ubuntu security updates do not automatically reboot.

Root SSH is key-only. UFW was inactive when checked; complete cloud security-group/netfilter rules are not audited. Aliyun Assist/security components remain host/provider tools. HBR is stopped and disabled, as described below. Preserve the frozen ALI installation without further application upgrades, backup additions, documentation synchronization, or cleanup; its original unit definitions remain linked but inactive. Forwarding and public certificate renewal continue. The frozen state excludes subsequent NAS writes and is not an automatic failover target.

### NAS Platform

Ubuntu 26.04.1 LTS / amd64 on an ASUS G733 laptop, Ryzen 9 5900HX, 64 GB installed RAM, two 1 TB NVMe SSDs. Linear `nasvg/root` holds one approximately 1.86 TiB ext4 filesystem; `/opt` and `/data` share it. Intel retains EFI, Samsung a separate 2 GiB ext4 `/boot`; Secure Boot and LVM boot were verified. There is no disk redundancy: either SSD failure can make the entire root unavailable.

NAS currently uses Wi-Fi DHCP; Ethernet supports optional DHCP. The user deferred router address reservation and additional stability investigation, retaining the present address as the migration input. A DHCP address change requires coordinated SSH/Origin/leaf-certificate/shortcut updates. Fully unattended startup after complete power loss is unverified.

The power policy keeps lid closure awake, caps charging at 80%, uses `balance_power`/`balanced`, disables boost, and restricts `acpi_idle` to C1. Persistent journal and minute health sampling remain active. Pre-cutover idle sampling and migration runtime checks passed, but the earlier cross-OS freeze cause and long-term loaded-service stability remain unresolved. [NAS operations](nas-host.md) owns diagnostics, power sources, storage, and recovery.

### VPS Platform

AlmaLinux 9.8 x86_64/KVM, 2 vCPU with a Xeon SierraForest guest model, approximately 1 GiB RAM, 544 MiB swap, 20 GiB disk with ext4 `/boot` and `/`. NetworkManager DHCP on `eth0`, public IPv4, provider DNS, Asia/Shanghai/chrony. Guest CPU features/topology do not establish dedicated cores or superiority to ALI; provider bandwidth, quotas, billing, filtering, and storage redundancy remain unverified.

Root SSH is key-only. Firewalld allows SSH, proxy TCP 443, ACME HTTP 80, and web HTTPS 8443. Nginx and public certificate renewal are active; the proxy's 443 listener and client parameters were unchanged by migration. DNF security updates never reboot automatically; the image retains `selinux=0 audit=0`. Do not copy Ubuntu APT/snap/UFW or Alibaba-agent assumptions. [VPS operations](vps-host.md) and [Proxy operations](vps-proxy.md) own host/proxy details.

The proxy is sing-box 1.14.4, `vps-proxy.service`, using the retained `xray` runtime identity and VLESS + REALITY + Vision. Yuyan document 833, titled `VPS配置`, is the client's maintained settings record. The installed macOS Hiddify 4.1.1 app's real core passed a public proxy HTTPS request alongside web acceptance; user-confirmed iPhone/China Mobile 5G access remains separate evidence. Approved pre-change archives and retired Xray software were removed without changing live proxy/gateway configuration or restarting either service; preserve the active `xray` identity.

<a id="已部署应用共享变更必须逐行核对"></a>
## Application Inventory

Paths, users, and ports below belong to the active NAS instances and are unchanged from the frozen ALI installation. ALI has no active business instance or collector; its public routes use NAS reverse forwards. Legacy backup unit files remain inactive source assets, not enabled NAS schedules.

| Application / source | Prefix / loopback port | Root / identities | Main units and dependencies |
| --- | --- | --- | --- |
| [Ledger](https://github.com/Crashmere/Ledger) | `/ledger/` / 18080 | `/opt/ledger`; `ledger`, `ledger-deploy` | `ledger.service`; local FabricWorld integration |
| [FeeTable](https://github.com/Crashmere/FeeTable) | `/feetable/` / 18081 | `/opt/feetable`; `feetable`, `feetable-deploy` | `feetable.service` |
| [FabricWorld](https://github.com/Crashmere/FabricWorld) | `/fabricworld/` / 18082 | `/opt/fabricworld`; `fabricworld`, `fabricworld-deploy` | `fabricworld.service`, native `fabricworld-cleanup.service/timer`; libvips; 640 MiB memory limit |
| [RecipeBox](https://github.com/Crashmere/RecipeBox) | `/recipebox/` / 18083 | `/opt/recipebox`; `recipebox`, `recipebox-deploy` | `recipebox.service`, native `recipebox-cleanup.service/timer`; libvips; 640 MiB limit; 5 GiB photo quota |
| [Yuyan](https://github.com/Crashmere/Yuyan) | `/yuyan/` / 18084 | `/opt/yuyan`; `yuyan`, `yuyan-deploy` | `yuyan.service`; 384 MiB limit, GOMEMLIMIT 320 MiB; gzip deployment |
| [ServerPortal](https://github.com/Crashmere/ServerPortal) | `/portal/` / 18085 | `/opt/serverportal`; Web user `serverportal`, administrator deployment | `serverportal.service`, root `serverportal-agent.service`; local Unix socket |
| [AICalendar](https://github.com/Crashmere/AICalendar) | `/aicalendar/` / 18086 | `/opt/aicalendar`; `aicalendar`, `aicalendar-deploy` | `aicalendar.service`; 192 MiB limit, GOMEMLIMIT 144 MiB; independent Bearer ingest |
| [Aura](https://github.com/Crashmere/Aura) | `/aura/` / 18087 | `/opt/aura`; `aura`, `aura-deploy` | `aura.service`; libvips, ExifTool, FFmpeg; PhotoKit clients |

Every project owns `AGENTS.md`, `docs/README.md`, operational/API/restore details, `deploy/nginx-location.conf`, and `deploy/portal.json`. The latter records complete data roots, units, ports, APIs, and resource purposes. Inspect direct `/healthz`, prefixed health/routes, actual media/API paths, and declaration receipts rather than inferring activation from integration files.

The NAS full recovery scope includes all application database tables and files: Ledger/FeeTable records; FabricWorld/RecipeBox photos; Yuyan documents/history/trash/templates/snippets/drawings/images/attachments/derivatives; AICalendar activities/annotations/imports/full conversations/original chunks/indexes/incomplete uploads; Aura catalogs/original photo-video objects/derivatives/upload state; Portal device grants/private configuration/registry. Old summary-only AICalendar snapshots do not meet that scope. The new native full-copy contract does not retroactively complete an old backup.

Ledger creates FabricWorld items through local port 18082 with explicit user confirmation and idempotent source records. AICalendar `/ingest/v1/` remains separately Bearer-authenticated; browser APIs use Portal. Yuyan attachment uploads are streamed without an application-size ceiling only in the registered attachment location, while drawings retain their existing limits. Application cleanup policies remain application behavior, distinct from disabled backup schedules.

<a id="门户与统一认证"></a>
## Portal and Shared Authentication

NAS hosts both Portal processes and its controlled `registry.d` links. The collector remains local, not a cross-host monitoring/root-execution API. Business access through NAS/ALI/VPS preserves device authentication, indefinite server grants, revocation, and secure browser-cookie renewal. Configure precise Origins for NAS HTTPS, ALI HTTPS, and VPS HTTPS with `:8443`; preserve full forwarded Host/port. ACME, exact brand assets, and independently authenticated ingest retain their limited exceptions.

Portal's public `/portal/connect` setup page and its four fixed GET/HEAD children distribute the current public NAS root, root-only Apple profile, metadata, and canonical VPS setup QR. NAS configuration owns `onboarding.caCertificate`, `lanOrigin`, and `publicOrigin`; both Origins are members of the existing allowed set. Windows, Android, macOS, and iPhone/iPad guidance retains user-operated installation/trust and the separate NAS login. No business endpoint, private material, automatic CA-trust detection, or cross-Origin login is added. [Portal maintenance](portal.md#public-nas-device-setup) owns the contract. On 2026-10-30, the user confirmed completing NAS local-CA onboarding through Portal in the maintenance Mac's browser. That confirms the reported browser flow only; Aura native-client trust, other NAS browser/app/platform flows, and VPS Portal device logins remain unverified.

Loopback inspection is available only through authorized SSH. It can access real data and is not inherently read-only. The default Tab/focus policy and Ledger/Yuyan explicit editing exceptions remain defined by [conventions](conventions.md).

<a id="共享配置与所有权"></a>
## Shared Configuration and Ownership

| Resource | Maintenance source and scope |
| --- | --- |
| Active gateway/LAN Nginx server | Shared role-specific templates; public IP certificate or NAS local-CA TLS; application location sources remain in each application |
| Application route includes | `/etc/nginx/app-locations`, deployed from each project's `deploy/nginx-location.conf`; copied to each active gateway |
| Portal authentication include | `assets/nginx-portal-auth.conf`; enabled for every user-facing entrance, never for public unauthenticated inspection |
| `/opt/serverportal/registry.d/<app>.json` | Root-managed link to application `config/portal.json`; validated publication receipt |
| `/etc/nas-ca` | Private local CA/signing/leaf materials; manual recovery package, never Git |
| `/etc/server-maintenance-host` | Root-managed NAS role marker; content `nas` |
| `/run/lock/server-maintenance.lock` | Shared upgrade/registry operations; exclusive full backup maintenance |
| `/var/lib/server-upgrades` | Root-private temporary upgrade protection; unresolved failures are preserved |
| `/opt/server-context`, `/opt/AGENTS.md` | Pushed agent-config source and synchronization provenance |
| `/root/AGENTS.md` | Link to `/opt/AGENTS.md`; remote instructions still require explicit reading |
| Application `current-commit`, `config/portal-source.json`, `docs/SOURCE` | Program, declaration, and documentation provenance respectively; do not substitute one for another |

<a id="手工数据归档"></a>
## Manual Data Archives

Routine NAS backups are agent-only, using `/opt/server-recovery` and private `/etc/server-recovery.json`. The attached Samsung T7 data partition is exFAT, label `T7`, UUID `BCDD-941E`, with approximately 652 GB free when inspected; it contains existing user files and remains unmounted. Backup creation therefore reports disconnected, with no internal fallback. No real recovery set has yet been created. Portal backup/recovery UI, APIs, commands, receipts and volume settings have been retired; historical receipt files and real archives are preserved. The user waived an additional retained migration recovery point: task-created Mac seeds/private packages and temporary gateway recovery material were removed after acceptance. Accepted NAS candidates, migration staging, and obsolete historical data copies were also removed; small acceptance receipts remain. The frozen ALI installation remains the migration-point fallback; it cannot recover later NAS writes. [NAS migration](nas-migration.md#manual-full-backups) owns the pause/copy/resume/compress/verify workflow and separately agent-collected gateway package.

Protected pre-existing materials include maintenance-computer `~/ali/backups/`, frozen ALI native/manual/Portal exports and `/opt/backup-exports`, the older five-application `ali-data-*` archive, and the verified approximately 2.3 GiB pre-LVM NAS root archive and diagnostics on the maintenance Mac. Private manifests record their historical recovery points and coverage. They are preserved, outside Git, and do not provide a current eight-application NAS/CA/tunnel or VPS private gateway/proxy recovery set. Redundant NAS pre-LVM/storage/diagnostic copies were removed only after byte verification against the protected Mac material; the Mac originals remain intact.

NAS retains no routine backup data, backup staging, or backup archive cache internally. Normal application data and derived caches remain part of live state. Temporary local upgrade protection is the explicit exception and is removed only after runtime and affected-data acceptance; unresolved failures remain protected. No current independent NAS/VPS private recovery set has been captured. Manual recovery restores application state rather than an OS/disk image, and writes after a selected recovery point can be lost.

<a id="云备份"></a>
## Cloud Backup

ALI's `hbrclient.service` and `hbrclientupdater.service` at `/opt/alibabacloud/hbrclient` are inactive and disabled. They were independent of application timers and Portal exports. Their historical file-backup scan included application `/opt` state and local snapshots; direct live SQLite/WAL scans were not equivalent to consistent native snapshots. Job records showed 30-day retention; console scheduling, storage usage, billing, and actual expiration were not audited.

Cutover preserved vendor files and historical cloud recovery points. Stopping local clients does not delete cloud backups or establish that a provider-side schedule/billing item was canceled. Further cloud account, retention, or subscription cleanup requires its own review and confirmation. No Alibaba backup/security agent is copied to VPS.

<a id="其他软件后台任务和已知问题"></a>
## Maintenance and Known Constraints

- Applications are locally built static Go amd64 programs with embedded frontend assets. NAS uses signed Ubuntu runtime packages for libvips/HEIF, ExifTool, and FFmpeg where needed; VPS runs only gateway/proxy dependencies. Do not add Node/Go build environments, Docker, database services, or CI deploy keys.
- NAS diagnostic/power, chrony, security updates, SSD TRIM, and active public certificate renewal remain enabled. Manual backup policy does not stop unrelated system maintenance. Host reboot and changes outside the authorized migration use the shared authorization table.
- NAS routine backup and backup/release-pruning schedules are disabled. FabricWorld and RecipeBox native cleanup timers are active and enabled for their existing expired-record/media rules, coordinated with full backups and deployments through shared locks; they create no snapshots or backup-pruning work. Retired ALI application/backup/retention/HBR tasks remain inactive and disabled with frozen material preserved. [Retention](retention.md) describes temporary upgrade protection and historical ALI materials.
- The ASUS laptop's freeze cause, full-power-loss restart behavior, DHCP permanence, gateway provider limits, external-drive readiness, and other device/browser acceptance remain explicit constraints. There is no automatic old-ALI data failover or external availability alert.
- Yuyan 833 does not contain the VPS server private key. A complete external gateway recovery package must capture current private proxy state, Nginx, certificates, and access configuration; client links and historical pre-change archives do not establish this coverage.

AICalendar import clients default to direct NAS LAN HTTPS. A LAN connection failure stops the task without automatically switching to VPS, ALI, or a tunnel. VPS uploads require an explicit user instruction, `--via-vps`, and the separate private `client-vps.json`; `--config` alone does not authorize a public route. Historical read-only TLS/Bearer status checks passed through NAS, ALI, and VPS, with command-scoped NAS CA trust. Yuyan agent operations default to the trusted `vps` SSH alias. The Mac Aura preference remains at the compatibility ALI entrance with its existing client state; changing to NAS/VPS requires that client's new-origin login, and NAS requires device CA trust. Do not extract browser cookies or rewrite fixed upload plans to change endpoints.

<a id="重新核对"></a>
## Rechecking

Read each target's `/opt/AGENTS.md`, then inspect enabled units/listeners, Nginx syntax and role-specific certificate/Origin settings, tunnel endpoints, source markers, and agent-owned external package evidence. `scripts/inspect.sh` provides non-business host status; full output can contain addresses and must not be committed raw. Documentation-only checks use `scripts/sync-docs.sh --check`, with explicit host selection.

<a id="本机发布与验证"></a>
## Local Deployment and Validation

[Local releases](release.md) separate the application deployment host NAS from public gateway URLs. Seven business applications use restricted identities; Portal uses authorized administrator SSH for its root collector. Program release, declaration publication, documentation synchronization, and data restoration are distinct operations.

GitHub backs up source/configuration and never production state or credentials. Server deployment Actions/secrets are retired; Aura's separately authorized Apple-client workflow publishes DMG/IPA installers without server access. Validate affected behavior locally, build from pushed committed source, preserve upgrade safeguards, and sync managed docs only after actual source/contract changes. Real data replacement/recovery uses an approved recovery point and isolated validation.

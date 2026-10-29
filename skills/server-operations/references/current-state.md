<a id="当前服务器与应用清单"></a>
# Current Server and Application Inventory

**Migration phase: preparation/staging; production cutover is not recorded as complete.** The source production applications remain on `ali` until the final consistent transfer and NAS activation are accepted. The authorized target is all eight application instances and authoritative data on `nas`, with `ali` HTTPS 443 and `vps` HTTPS 8443 forwarding to that same NAS state. VPS's existing sing-box proxy keeps TCP 443. [NAS migration](nas-migration.md) owns the shared topology, cutover, manual backup, and recovery contract.

This inventory records durable roles and constraints, not a release log. Recheck actual listeners, enabled units, source markers, and recovery receipts; a committed template or staging copy is not an active production instance.

Verified preparation has installed the NAS local CA/leaf renewal timer and eight runtime accounts with empty application roots. NAS-to-VPS reverse forwarding has all eight loopback application listeners plus management 22022, and the trusted `nas-via-vps` maintenance alias works while the existing LAN `nas` alias remains unchanged. VPS has an HTTP-01-only Nginx bootstrap on public 80, an isolated Certbot 5.8 environment, and its production IP certificate; proxy 443 is unchanged. These listeners have no active NAS application upstreams yet, and ALI's eight production applications remain running. LAN bulk SSH copies have timed out despite continuous NAS health sampling; use the verified maintenance route without treating the symptom as a confirmed freeze or silently changing network configuration.

<a id="主机"></a>
<a id="host"></a>
## Hosts

| Host | Current role before cutover | Role after accepted cutover |
| --- | --- | --- |
| `ali` | Eight production applications, public HTTPS 443, local application backups/retention and independent HBR client | Public HTTPS 443 gateway to NAS; old application units and backup/retention/HBR clients stopped and disabled, existing materials retained |
| `nas` | Prepared Ubuntu laptop; migration configuration/artifacts are staging | Only active application host, authoritative data, LAN local-CA HTTPS 443, Portal Web/collector, manual external backup operation |
| `vps` | AlmaLinux VM with working sing-box REALITY/Vision on TCP 443 | Existing proxy unchanged plus public web HTTPS 8443 and restricted loopback forwarding to NAS |

Use the trusted SSH aliases `ali`, `nas`, and `vps`; retrieve real addresses and selected identities from local SSH configuration. Strict host-key verification remains enabled. NAS initiates reverse SSH connections to both gateways because this deployment does not use IPv6 ingress or NAT hole punching.

### ALI Platform

Ubuntu 26.04.1 LTS / amd64 on Alibaba Cloud ECS/KVM; 2 vCPU, approximately 1.7 GiB visible RAM, 40 GiB ext4 root, no swap or separate application-data mount. Nginx 1.28.3 and Certbot's official snap provide trusted public-IP HTTPS on 443, HTTP-01/redirects on 80, and loopback inspection. Chrony uses Asia/Shanghai; signed Ubuntu security updates do not automatically reboot.

Root SSH is key-only. UFW was inactive when checked; complete cloud security-group/netfilter rules are not audited. Aliyun Assist/security components are host/provider tools, not application dependencies. Retain their files unless separately authorized. The HBR client is a separate backup mechanism, described below.

### NAS Platform

Ubuntu 26.04.1 LTS / amd64 on an ASUS G733 laptop, Ryzen 9 5900HX, 64 GB installed RAM, two 1 TB NVMe SSDs. Linear `nasvg/root` holds one approximately 1.86 TiB ext4 filesystem; `/opt` and `/data` share it. Intel retains EFI, Samsung a separate 2 GiB ext4 `/boot`; Secure Boot and LVM boot were verified. There is no disk redundancy: either SSD failure can make the entire root unavailable.

NAS currently uses Wi-Fi DHCP; Ethernet supports optional DHCP. The user deferred router address reservation and additional stability investigation, retaining the present address as the migration input. A DHCP address change requires coordinated SSH/Origin/leaf-certificate/shortcut updates. Fully unattended startup after complete power loss is unverified.

The power policy keeps lid closure awake, caps charging at 80%, uses `balance_power`/`balanced`, disables boost, and restricts `acpi_idle` to C1. Persistent journal and minute health sampling remain active. The latest home check showed about 35 hours of uninterrupted runtime, 2,095 samples with a largest 61-second gap, no failed services, and zero media-integrity errors on both SSDs. This is idle-operation evidence, not confirmation of the earlier cross-OS freeze cause or loaded-service stability. [NAS operations](nas-host.md) owns diagnostics, power sources, storage, and recovery.

### VPS Platform

AlmaLinux 9.8 x86_64/KVM, 2 vCPU with a Xeon SierraForest guest model, approximately 1 GiB RAM, 544 MiB swap, 20 GiB disk with ext4 `/boot` and `/`. NetworkManager DHCP on `eth0`, public IPv4, provider DNS, Asia/Shanghai/chrony. Guest CPU features/topology do not establish dedicated cores or superiority to ALI; provider bandwidth, quotas, billing, filtering, and storage redundancy remain unverified.

Root SSH is key-only. Firewalld is active; TCP 443 serves the proxy. Web migration adds HTTP 80 and HTTPS 8443 under the approved gateway setup, without changing the proxy's 443 listener. DNF security updates never reboot automatically; the image retains `selinux=0 audit=0`. Do not copy Ubuntu APT/snap/UFW or Alibaba-agent assumptions. [VPS operations](vps-host.md) and [Proxy operations](vps-proxy.md) own host/proxy details.

The proxy is sing-box 1.14.4, `vps-proxy.service`, using retained `xray` runtime identity and VLESS + REALITY + Vision. Yuyan document 833, titled `VPS配置`, is the client's maintained settings record. Retired Xray is stopped and disabled. User-confirmed iPhone/China Mobile 5G access belongs to proxy acceptance, not web gateway acceptance.

<a id="已部署应用共享变更必须逐行核对"></a>
## Application Inventory

Paths, users, and ports below are shared by the ALI source and NAS target. Before cutover, ALI remains the active source; NAS copies must not accept independent writes. The seven business backup unit files may remain as inactive historical assets, but no such timer is enabled on NAS.

| Application / source | Prefix / loopback port | Root / identities | Main units and dependencies |
| --- | --- | --- | --- |
| [Ledger](https://github.com/Crashmere/Ledger) | `/ledger/` / 18080 | `/opt/ledger`; `ledger`, `ledger-deploy` | `ledger.service`; local FabricWorld integration |
| [FeeTable](https://github.com/Crashmere/FeeTable) | `/feetable/` / 18081 | `/opt/feetable`; `feetable`, `feetable-deploy` | `feetable.service` |
| [FabricWorld](https://github.com/Crashmere/FabricWorld) | `/fabricworld/` / 18082 | `/opt/fabricworld`; `fabricworld`, `fabricworld-deploy` | `fabricworld.service`; libvips; 640 MiB memory limit |
| [RecipeBox](https://github.com/Crashmere/RecipeBox) | `/recipebox/` / 18083 | `/opt/recipebox`; `recipebox`, `recipebox-deploy` | `recipebox.service`; libvips; 640 MiB limit; 5 GiB photo quota |
| [Yuyan](https://github.com/Crashmere/Yuyan) | `/yuyan/` / 18084 | `/opt/yuyan`; `yuyan`, `yuyan-deploy` | `yuyan.service`; 384 MiB limit, GOMEMLIMIT 320 MiB; gzip deployment |
| [ServerPortal](https://github.com/Crashmere/ServerPortal) | `/portal/` / 18085 | `/opt/serverportal`; Web user `serverportal`, administrator deployment | `serverportal.service`, root `serverportal-agent.service`; local Unix socket |
| [AICalendar](https://github.com/Crashmere/AICalendar) | `/aicalendar/` / 18086 | `/opt/aicalendar`; `aicalendar`, `aicalendar-deploy` | `aicalendar.service`; 192 MiB limit, GOMEMLIMIT 144 MiB; independent Bearer ingest |
| [Aura](https://github.com/Crashmere/Aura) | `/aura/` / 18087 | `/opt/aura`; `aura`, `aura-deploy` | `aura.service`; libvips, ExifTool, FFmpeg; PhotoKit clients |

Every project owns `AGENTS.md`, `docs/README.md`, operational/API/restore details, `deploy/nginx-location.conf`, and `deploy/portal.json`. The latter records complete data roots, units, ports, APIs, and resource purposes. Inspect direct `/healthz`, prefixed health/routes, actual media/API paths, and declaration receipts rather than inferring activation from integration files.

The NAS full recovery scope includes all application database tables and files: Ledger/FeeTable records; FabricWorld/RecipeBox photos; Yuyan documents/history/trash/templates/snippets/drawings/images/attachments/derivatives; AICalendar activities/annotations/imports/full conversations/original chunks/indexes/incomplete uploads; Aura catalogs/original photo-video objects/derivatives/upload state; Portal device grants/private configuration/registry. Old summary-only AICalendar snapshots do not meet that scope. The new native full-copy contract does not retroactively complete an old backup.

Ledger creates FabricWorld items through local port 18082 with explicit user confirmation and idempotent source records. AICalendar `/ingest/v1/` remains separately Bearer-authenticated; browser APIs use Portal. Yuyan attachment uploads are streamed without an application-size ceiling only in the registered attachment location, while drawings retain their existing limits. Application cleanup policies remain application behavior, distinct from disabled backup schedules.

<a id="门户与统一认证"></a>
## Portal and Shared Authentication

NAS hosts both Portal processes and its controlled `registry.d` links. The collector remains local, not a cross-host monitoring/root-execution API. User-facing NAS/ALI/VPS entrances preserve device authentication, indefinite server grants, revocation, and secure browser-cookie renewal. Configure precise Origins for NAS HTTPS, ALI HTTPS, and VPS HTTPS with `:8443`; preserve full forwarded Host/port. ACME, exact brand assets, and independently authenticated ingest retain their limited exceptions.

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

Routine NAS backups require a real external mount/UUID. That external volume is not yet identified, so the Portal job is intentionally unavailable until configured. It must not create an internal fallback. The migration's initial independent cold Mac recovery archive is a separate protection step, not a successful external-drive backup or real-device recovery drill. Completion and coverage must be recorded when actually verified. [NAS migration](nas-migration.md#manual-full-backups) owns the pause/copy/resume/compress/verify workflow and agent-only gateway package.

Existing real materials remain protected: maintenance-computer `~/ali/backups/`, ALI native/manual/Portal exports and `/opt/backup-exports`, the older five-application `ali-data-*` archive, and the verified approximately 2.3 GiB pre-LVM NAS root archive under `backups/nas-lvm-*`. Their adjacent private manifests record recovery points and coverage; older partial/five-app packages are not substitutes for the new eight-app full scope. None enters Git, is overwritten, or is deleted by this migration.

After cutover, NAS retains no routine backup data or archive cache internally. Temporary local upgrade protection is the explicit exception and is removed only after runtime and affected-data acceptance. Manual recovery restores application state rather than an OS/disk image; writes after the last successful complete backup can be lost.

<a id="云备份"></a>
## Cloud Backup

ALI's `hbrclient.service` and `hbrclientupdater.service` at `/opt/alibabacloud/hbrclient` are independent of application timers and Portal exports. Their file-backup scan included application `/opt` state and local snapshots; direct live SQLite/WAL scans are not equivalent to consistent native snapshots. Job records showed 30-day retention; console scheduling, storage usage, billing, and actual expiration were not audited.

The authorized cutover stops and disables both clients, preserving local vendor files and historical cloud recovery points. Stopping local clients does not delete cloud backups or establish that a provider-side schedule/billing item was canceled. Further cloud account, retention, or subscription cleanup requires its own review and confirmation. No Alibaba backup/security agent is copied to VPS.

<a id="其他软件后台任务和已知问题"></a>
## Maintenance and Known Constraints

- Applications are locally built static Go amd64 programs with embedded frontend assets. NAS uses signed Ubuntu runtime packages for libvips/HEIF, ExifTool, and FFmpeg where needed; VPS runs only gateway/proxy dependencies. Do not add Node/Go build environments, Docker, database services, or CI deploy keys.
- NAS diagnostic/power, chrony, security updates, SSD TRIM, and active public certificate renewal remain enabled. Manual backup policy does not stop unrelated system maintenance. Host reboot and changes outside the authorized migration use the shared authorization table.
- No backup/retention scheduler is enabled on NAS. Legacy ALI application/retention/HBR tasks stop after final capture; their retained material is not routine junk. [Retention](retention.md) describes temporary upgrade protection and historical ALI materials.
- The ASUS laptop's freeze cause, full-power-loss restart behavior, DHCP permanence, gateway provider limits, and actual external-drive/device-trust acceptance remain explicit constraints. There is no automatic old-ALI data failover or external availability alert.
- VPS proxy recovery archives currently remain on its own disk; Yuyan 833 does not contain the server private key. A complete gateway recovery package must include current private proxy state, not only client links or Nginx configuration.

<a id="重新核对"></a>
## Rechecking

Read each target's `/opt/AGENTS.md`, then inspect enabled units/listeners, Nginx syntax and role-specific certificate/Origin settings, tunnel endpoints, source markers, and backup receipts. `scripts/inspect.sh` provides non-business host status; full output can contain addresses and must not be committed raw. Documentation-only checks use `scripts/sync-docs.sh --check`, with explicit host selection.

<a id="本机发布与验证"></a>
## Local Deployment and Validation

[Local releases](release.md) separate the application deployment host NAS from public gateway URLs. Seven business applications use restricted identities; Portal uses authorized administrator SSH for its root collector. Program release, declaration publication, documentation synchronization, and data restoration are distinct operations.

GitHub backs up source/configuration and never production state or credentials. Server deployment Actions/secrets are retired; Aura's separately authorized Apple-client workflow publishes DMG/IPA installers without server access. Validate affected behavior locally, build from pushed committed source, preserve upgrade safeguards, and sync managed docs only after actual source/contract changes. Real data replacement/recovery uses an approved recovery point and isolated validation.

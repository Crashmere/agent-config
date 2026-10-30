<a id="重建服务器与新增应用"></a>
# Rebuilding Hosts and Adding Applications

Rebuild the selected host role from maintained source and either verified recovery materials, a complete frozen-source migration transfer, or an explicitly selected empty installation. NAS is the Ubuntu application host; ALI and VPS are public gateways, with VPS on AlmaLinux and its existing proxy unchanged. [Current-state](current-state.md) records activation and [NAS migration](nas-migration.md) owns topology/cutover/recovery. This sequence does not authorize overwriting a live host or selecting a recovery point without confirmation.

## Sources and Recovery Point

Determine whether this is an empty new service, backup recovery, or migration of an existing authoritative installation. Obtain agent-config, every affected application's source/docs, trusted SSH identities, and verified host fingerprints. Backup recovery also requires the selected verified private recovery packages; a cold-source migration instead transfers complete state after the authoritative writers stop. Git supplies code/configuration templates, not data, secrets, cloud access, or the chosen recovery point.

For backup recovery, verify the complete package and inspect it in an isolated path first. For migration, verify the final complete transfer against the frozen source before accepting the NAS state. Never use initialization to hide missing data or restore a selected-table AICalendar snapshot as a complete conversation recovery point. Older encrypted/incremental packages keep their original keys and parent-chain requirements; [Agent backup and recovery](backup-recovery.md) owns package and recovery checks.

The current migration does not retain a local recovery archive: task-created Mac seeds/private packages are relay and acceptance materials removed after automatable acceptance. The original ALI application installation remains frozen as the last migration-point fallback, without further upgrades, backup additions, documentation maintenance, or cleanup; it cannot recover subsequent NAS writes. Preserve pre-existing Mac backups and pre-LVM NAS material unless explicitly proven redundant. A claimed full-topology recovery set needs a completed manual capture of current NAS authentication/CA/tunnel materials, ALI/VPS gateway private configuration, and the VPS proxy's private configuration; migration activation alone does not provide that set.

## Host Foundation

- Read the target's remote `/opt/AGENTS.md` explicitly. Verify actual OS, resources/storage, listeners, enabled units, ownership, time, package sources, and network/access before installing anything.
- Use signed Ubuntu runtime packages on NAS and DNF/AlmaLinux sources on VPS. Reuse installed NAS libvips/HEIF, ExifTool, and FFmpeg as needed; VPS requires gateway/certificate/proxy components, not app media/build runtimes. Use `software-installation` and isolated `python-environment` workflows where applicable.
- Keep builds on the maintenance computer, producing committed static Linux amd64 programs with embedded frontend assets. Do not add server Go/Node/Docker/database services or resurrect CI deployment keys.
- Sync pushed shared context with an explicit host to create `/opt/server-context`, `/opt/AGENTS.md`, and the correct Ubuntu/PAM login notice; link `/root/AGENTS.md` only without replacing an existing conflicting file. Documentation synchronization does not install runtime assets.
- NAS uses the root-managed marker `/etc/server-maintenance-host=nas`, `/run/lock/server-maintenance.lock`, and private `/var/lib/server-upgrades` protection. Follow [retention](retention.md) and [local releases](release.md); do not enable old application backup/ALI retention timers.
- Preserve existing administrator access, proxy TCP 443, Wi-Fi/private credentials, and security/time-maintenance settings. Reboots or unrelated access changes still follow the shared authorization table.

## Application State on NAS

Each application retains its own runtime user, `/opt/<app>` data/config/bin/docs layout, loopback port, URL prefix, and controlled deployment identity. Portal Web and its root collector are restored together with local Unix socket and `registry.d`; seven business releases remain restricted. For a genuinely new empty service, initialize only after explicit selection of that mode. A migration restores the final consistent source, not a preliminary staging copy.

After writes stop, cold-copy complete databases/files or use verified complete native snapshots; include WAL-aware state, conversations, original chunks, incomplete uploads, stored derivatives, annotations, and credentials/configuration needed for the role. Restore ownership/permissions before activation. Inspect old Yuyan history/media before cleanup runs, and reconcile Aura client upload receipts after recovery.

Publish each application's own `deploy/portal.json` through the validated protocol, preserving separate program/declaration/documentation provenance. Install application-owned route includes from the same source to every active entrance; do not maintain independent copies of business routing in gateway code. Icons, authentication exceptions, upload/streaming, and Ledger-to-FabricWorld remain existing application contracts.

## HTTPS and Forwarding

[HTTPS](https.md) owns platform-specific certificate issuance/renewal and proxy trust. NAS uses the restored/local CA at `/etc/nas-ca` for LAN 443. ALI uses its own public IPv4 certificate on 443; VPS uses a new certificate on 8443 and HTTP-01 on 80, without taking proxy 443. Each user-facing entrance uses Portal and the exact NAS/ALI/VPS Origin set, preserving the explicit VPS port in `$http_host`.

NAS initiates two dedicated restricted reverse-SSH connections. Gateway loopback 18080-18087 reaches the corresponding NAS apps, and 22022 supplies restricted maintenance SSH. Inspection uses each gateway's loopback HTTP 80 and the same locations; internal ports are not opened publicly. Read host/tunnel sources in [NAS migration](nas-migration.md#host-roles-and-traffic), and keep strict fingerprint verification and forwarding-bind failure checks.

The user deferred DHCP reservation and further freeze investigation. Retain the selected LAN address as an input with coordinated change instructions; do not treat it as guaranteed fixed or claim diagnostic mitigation solved hardware. Configure routing without redirecting heavy LAN work through a public gateway.

## Backup Readiness and Acceptance

Routine NAS/VPS backup requires a real independently mounted external filesystem and its verified UUID. A missing/unknown volume keeps the standalone tool unavailable without affecting Portal authentication. The agent identifies/mounts the known disk without formatting, gathers live VPS gateway/proxy material and complete cold NAS state on NAS, creates one compressed package, then copies and verifies it externally. Temporary internal staging is removed only after success, not used as a fallback. [Agent backup and recovery](backup-recovery.md) owns execution and host-selected isolated restoration; no remote-root web interface is added.

Validate the affected state and entrances: direct service health/data, three TLS/authenticated paths, correct Origin/Host/protocol, representative upload/download/integration/Bearer contracts, tunnel listeners/reconnect, and continuity of existing proxy 443. Actual device CA trust/logins and the first real external-volume recovery check remain distinct from synthetic/CLI validation. No full historical regression or permanent test accumulation is required.

During cutover, pause writers, drain operations, and stop old ALI application/Portal/background jobs for final consistent capture. Verify the complete frozen-source transfer to NAS, then disable retired ALI application/backup/retention/HBR units and assign the freed application ports to reverse forwarding before validating the ALI entrance. Activate those exact NAS copies and the gateways, complete runtime/data acceptance, then allow new NAS writes. Both public gateways must refer to this same NAS state. Once NAS writes occur, a return to old ALI data is not a program rollback; confirm a new complete transfer or recovery point and accept any resulting data loss.

After all automatable migration acceptance succeeds, remove task-created Mac relay materials and confirmed redundant NAS/VPS staging, obsolete backups, and outdated files while preserving current runtime/configuration/keys, protected existing backups, frozen ALI materials, and unresolved failed-upgrade protection. Report actual device/drive acceptance and uncaptured recovery scope separately.

Update owning source, active application declarations/docs, shared roles, and managed host copies after actual activation without maintaining frozen ALI application materials. Host/data recovery, program release, declaration publication, and documentation synchronization are separate operations.

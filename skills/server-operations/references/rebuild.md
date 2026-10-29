<a id="重建服务器与新增应用"></a>
# Rebuilding Hosts and Adding Applications

Restore the selected application state from verified recovery materials and maintained source, using the platform of each role. NAS is the Ubuntu application host; ALI and VPS are public gateways, with VPS on AlmaLinux and its existing proxy unchanged. [Current-state](current-state.md) records activation and [NAS migration](nas-migration.md) owns topology/cutover/recovery. This sequence does not authorize overwriting a live host or selecting a recovery point without confirmation.

## Sources and Recovery Point

Obtain agent-config and every affected application's source/docs, private recovery packages, trusted SSH identities and verified host fingerprints. Determine whether this is an empty new service, a full host recovery, or migration of an existing authoritative database. Git supplies code/configuration templates, not data, secrets, cloud access, or the chosen recovery point.

For existing data, verify the complete package and inspect it in an isolated path first. Never use initialization to hide missing data or restore a selected-table AICalendar snapshot as a complete conversation recovery point. Older encrypted/incremental packages keep their original keys and parent-chain requirements; ServerPortal docs/RESTORE.md owns format/recovery checks.

The migration's independent cold ALI archive on the maintenance Mac protects its frozen eight-application source point. New NAS CA/tunnel and VPS gateway/proxy private state need their own verified manual capture. Preserve old ALI and pre-LVM NAS archives throughout preparation.

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

Routine NAS backup requires a real independently mounted external filesystem and its verified UUID. A missing/unknown volume keeps Portal backup unavailable while ordinary Portal startup/authentication work. Do not format the drive by default or create an internal fallback. Agent and Portal use the same manual full cold-copy/compress/verify operation; agent supplements live gateway/proxy packages without adding a remote-root web interface.

Validate the affected state and entrances: direct service health/data, three TLS/authenticated paths, correct Origin/Host/protocol, representative upload/download/integration/Bearer contracts, tunnel listeners/reconnect, and continuity of existing proxy 443. Actual device CA trust/logins and the first real external-volume recovery check remain distinct from synthetic/CLI validation. No full historical regression or permanent test accumulation is required.

During cutover, pause writers, drain operations, and stop old ALI application/Portal/background jobs for final consistent capture. Verify independent recovery protection and the exact NAS transfer, then disable retired ALI application/backup/retention/HBR units and assign the freed application ports to reverse forwarding before validating the ALI entrance. Activate those exact NAS copies and the gateways, complete runtime/data acceptance, then allow new NAS writes. Both public gateways must refer to this same NAS state. Once NAS writes occur, a return to old ALI data is not a program rollback; confirm a new complete transfer or recovery point. Preserve material and report incomplete recovery/backup prerequisites rather than silently recreating empty state.

Update owning source, application declarations/docs, shared active roles, and managed host copies after actual activation. Host/data recovery, program release, declaration publication, and documentation synchronization are separate operations.

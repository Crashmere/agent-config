# NAS Applications and Public Gateways

This reference owns the shared application placement, gateway, manual backup, and recovery contract for `nas`, `ali`, and `vps`. Implementation is being prepared; [current-state](current-state.md) records which host actually serves production. Yuyan document 832 under document 375 contains the user's complete Chinese migration plan. Public repositories contain templates and SSH aliases, not private addresses, credentials, or recovery packages.

## Host Roles and Traffic

In the target topology, `nas` runs the only active instances of Ledger, FeeTable, FabricWorld, RecipeBox, Yuyan, ServerPortal, AICalendar, and Aura and owns their authoritative data. Paths, application users, and loopback ports 18080-18087 remain unchanged. Portal Web and its local Unix-socket collector stay together on `nas`; Ledger-to-FabricWorld calls remain local. There are no duplicated lightweight databases or automatic failover to old ALI data.

| Entrance | TLS and routing | Upstream |
| --- | --- | --- |
| `nas` LAN IPv4, HTTPS 443 | Local-CA certificate, Portal authentication, application-owned Nginx locations | NAS loopback application ports |
| `ali` public IPv4, HTTPS 443 | Existing trusted IP certificate, Portal authentication, same application locations | Individual loopback reverse-SSH listeners to NAS |
| `vps` public IPv4, HTTPS 8443 | Its own trusted IP certificate, Portal authentication, same application locations | Individual loopback reverse-SSH listeners to NAS |
| `vps` TCP 443 | Existing sing-box REALITY/Vision proxy | Independent proxy traffic; not an HTTP application gateway |

NAS initiates supervised OpenSSH reverse forwarding to both gateways. Dedicated restricted identities, separate managed connections, strict gateway host-key verification, loopback-only remote listeners, keepalives, reconnect, and forwarding-bind failure detection are required. Forward application ports rather than adding another HTTP rewriting hop. Gateway maintenance access to NAS uses a separately restricted loopback management forward; it does not expose NAS SSH publicly. Deployment still targets NAS, independently of the selected public URL.

Sources are `assets/nas/reverse-tunnel@.service`, `assets/nas/tunnel.conf.template`, and `assets/gateway/30-nas-tunnel.conf`. NAS runtime identity `nas-tunnel` reads root-managed `/etc/nas-tunnels/{ali,vps}.conf`, corresponding `.key` files, and `known_hosts`. Gateways allow that identity only the listed remote listeners, no local forwarding/shell/PTY/agent. Ports 18080-18087 map to the same NAS ports; gateway loopback 22022 maps to NAS SSH 22. Each gateway's own loopback HTTP 80 includes the application locations, so inspection uses those application forwards without another HTTP-tunnel port. An optional maintenance-computer NAS-via-VPS alias can use 22022 while preserving the local NAS alias.

On each gateway, the dedicated identity's `.ssh` directory is root-owned with group `nas-tunnel` and mode 0750; `authorized_keys` uses the same ownership and mode 0640. OpenSSH must be able to read it as the authenticating user while that user cannot edit the key restrictions. A root-only 0700 directory blocks that read. Validate the effective Match configuration and a fresh restricted connection after changes.

Both public gateways reach the same NAS data. ALI retains old programs, databases, and backups with its retired application units disabled after cutover. Continuing ALI forwarding preserves the old public address and cookies; it does not keep an old writable application instance. Ending that forwarding or canceling ALI is separate from this migration.

Family devices use the NAS address directly for large imports and media transfers. Relative application/media URLs keep LAN traffic local. Public throughput is bounded by the home uplink and gateway route/provider limits. NAS remains locally usable if either public gateway or the Internet is unavailable. The existing proxy and its client imports are preserved; Hiddify's LAN bypass rules must keep private NAS traffic direct.

## HTTPS and Authentication

`ali` and `vps` each obtain a public certificate for their own IPv4. An ALI certificate cannot cover a different VPS address. HTTP-01 uses gateway port 80; a certificate issued there can serve VPS HTTPS on 8443 without taking the proxy's 443 listener. Public IP certificates have roughly 160-hour validity and require automated renewal. Certificate/security/time-maintenance timers continue under the manual backup policy.

NAS uses `/etc/nas-ca` for private CA and leaf-certificate materials. The leaf SAN includes the selected LAN IPv4. Devices import and trust only the CA root; the private signing key remains server-side and enters manual recovery materials. Leaf renewal under the same CA does not require importing another root. Use normal OS trust, including iOS full trust where required, and validate both the browser and Aura client; do not bypass certificate checks. [HTTPS](https.md) owns signing/renewal details.

The user deferred a router reservation, wired-network migration, and further stability investigation. The present DHCP address remains the migration input, not a guaranteed fixed address. If DHCP changes it, update trusted connection settings, NAS leaf SAN, configured Origins, and LAN shortcuts together. The unresolved freeze history and unverified automatic startup after complete power loss remain operational risks, not blockers that have silently been declared solved.

All user-facing entrances retain Portal authentication and exact HTTPS Origin checks. Include NAS, ALI, and VPS with `:8443` in the configured set. Preserve `__Host-portal_device`, Secure/HttpOnly/SameSite behavior, grants, renewal, and revocation. The three server IPs require separate initial logins because cookies are host-bound; Origin checks also include the port, although cookies themselves are not isolated by port. Nginx overwrites the forwarded protocol and preserves the full request Host, including port, with `$http_host`. Bearer-authenticated AICalendar ingest remains independent. Unauthenticated inspection stays loopback-only and SSH-authorized; it is not a LAN entrance or inherently read-only.

## Manual Full Backups

The normal destination is an external filesystem attached to NAS. Portal configuration uses `manualBackup.mount` and `manualBackup.uuid`, with `exports` strictly below that mount. The expected UUID is currently unknown; an empty UUID makes routine backup visibly unavailable rather than reverting to the NAS root disk. Portal must still start, authenticate, and show resource state without a drive. Inserting a drive does not trigger a job.

Every routine recovery set is standalone, complete, and compressed. Include all database tables, committed conversations, original chunks, incomplete uploads, stored derivatives, programs, configuration, identities/ownership, Portal state/registry, local CA, and shared NAS recovery materials. Exclude process sockets/locks and the routine backup destination itself. Historical backup/release directories are not recursively included as application data; unresolved upgrade protection is an explicitly registered recovery resource. Compression does not add a new encryption-key workflow.

The controlled job takes `/run/lock/server-maintenance.lock` exclusively, then application deployment and registry locks. It verifies the actual mounted filesystem, UUID, independent device, writability, and capacity; a directory's existence is insufficient. It drains writes, gracefully pauses previously active business/background units, and captures stable complete state to external staging while coordinating Portal device-state capture. Only units that were running are resumed. Compression reads immutable external staging after services resume, not changing production data. Full read-back checks and flush precede completion; delete only successful job staging and safely unmount. Failures or drive removal never publish a complete archive or fall back to internal storage, and service-resume failure is separately reported.

Portal and an agent use the same controlled NAS operation. Agent-maintained gateway packages separately capture current VPS and ALI Nginx/certificate/tunnel/access materials, including the existing VPS proxy private configuration and recovery assets. Portal has no general remote-root interface and must not claim that a NAS-only job captured live gateway state. Record the host, versions, scope, collection time, permissions, content checks, and actual recovery validation of each package.

Until a real external volume is configured, the migration uses an independent complete cold recovery archive on the maintenance Mac as its initial protection. Its successful validation must be recorded separately; it is not a completed external-drive Portal job. Preserve existing `backups/`, pre-LVM NAS recovery material, and ALI archives. Manual recovery points mean writes after the last successful complete backup can be lost.

The initial archive is a unique private `~/ali/backups/ali-to-nas-*` recovery set with all eight frozen ALI application data/config/bin/docs/source markers and shared ALI gateway material, excluding routine backup history and release junk. It protects that ALI application recovery point. New NAS CA/tunnel keys and current VPS private gateway/proxy materials require separate manual capture before claiming a complete recovery set for the new topology.

## Upgrade and Recovery Boundaries

Upgrade-only local protection uses the explicit NAS marker `/etc/server-maintenance-host`, root-private `/var/lib/server-upgrades`, and the shared maintenance/deployment locks. It preserves complete data while runtime and affected-data checks run. Success deletes that upgrade's protection immediately; failure, incomplete verification, or cleanup errors retain identified protection. [Retention](retention.md) and [Local releases](release.md) own this lifecycle. Legacy daily application backup/retention tasks and ALI HBR clients are stopped during cutover without deleting historical materials.

An agent performs recovery through trusted SSH. Verify and extract into an isolated path, inspect databases, complete media/archive coverage, versions, permissions, and credentials, then confirm the recovery point before production replacement. Do not start restored Yuyan cleanup before inspecting older history/media that would expire. After Aura recovery, reconcile Origin-keyed upload receipts so missing server originals are not treated as already uploaded.

Restore NAS applications on compatible Ubuntu amd64; rebuild VPS gateway/proxy on AlmaLinux with that platform's package, firewall, and certificate mechanisms. Do not copy Ubuntu APT/snap/UFW assumptions or Alibaba agents to VPS. A new gateway IP requires a matching certificate and client settings. Preserve both local administrative access and a restricted remote maintenance route; an application tunnel being down must not be treated as permission to expose internal services.

## Cutover and Acceptance

Stage source, artifacts, identities, certificates, gateways, and tunnel configuration while ALI production stays authoritative. Any preliminary data copy is staging, not the final recovery point. During the authorized cutover, pause clients and writes, drain operations, stop old applications/background jobs, capture complete consistent state, verify independent recovery protection and the final NAS transfer, then activate those exact NAS copies. Stop the old Portal Web/collector and disable retired ALI application/backup/retention/HBR units before reassigning their original ports to forwarding.

Validate direct NAS state, all three authenticated entrances, trusted TLS, path/header/streaming behavior, uploads/downloads, Ledger integration, AICalendar Bearer ingest, and proxy 443 continuity. Record the absent external-volume prerequisite and device trust/login results rather than treating CLI TLS checks as actual-device acceptance. Sync owning source configuration, declarations, project docs, and shared copies to the hosts whose role actually changed.

If NAS has accepted no new writes, failure can return to the frozen ALI source after stopping conflicting NAS listeners. Once NAS has accepted new writes, it is the latest source: repair gateways or use a compatible program rollback; reverting to old ALI databases would lose data. Any host/data rollback then requires a fresh consistent transfer or separately confirmed recovery point. Do not enable automatic stale-data failover.

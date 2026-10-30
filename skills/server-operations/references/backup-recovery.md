# Agent Backup and Recovery

The agent exclusively handles NAS/VPS backup, verification and restoration through trusted administrator SSH. Portal provides none of these operations, archive downloads, volume settings or recovery receipts. A manual backup gathers both hosts on NAS, creates one standalone compressed package on NAS, then copies and verifies it on the external disk. It protects application state and the configuration needed to rebuild services, not an OS/disk image.

## Request Defaults

The user only needs to say `通过 nas 备份到外接硬盘` or `通过 vps 备份到外接硬盘`. These phrases select the **NAS management transport, not the backup scope**:

| Request | NAS SSH alias | VPS SSH alias | Default coverage |
| --- | --- | --- | --- |
| `通过 nas 备份到外接硬盘` | `nas`, direct LAN | `vps` | All current NAS application/shared state and VPS gateway/proxy recovery material |
| `通过 vps 备份到外接硬盘` | `nas-via-vps`, via VPS | `vps` | The same complete dual-host set |

Do not silently switch transports after connection failure or reduce coverage when either host is unavailable. Read this runbook and the shared skill, explicitly read `/opt/AGENTS.md` on NAS and VPS, and use trusted aliases with host-key verification. The maintenance computer needs administrator access to both hosts and the maintained scripts; no Portal login or application import token is needed.

A backup request includes the scoped permission in the [sole authorization table](../SKILL.md#authorization): identify and mount the known disk without formatting, write a new package under its dedicated export subtree, temporarily pause required registered writers/timers, resume only previously active units, remove only this successful job's temporary staging, and safely unmount the disk if this task mounted it. Do not ask the user to repeat these defaults. Inspecting a disk or editing backup documentation does not authorize creating a real backup.

Stop and ask if the disk identity/destination differs, privileges are missing, capacity is insufficient, an unresolved maintenance job needs a recovery decision, or additional downtime is needed. Do not format, overwrite/delete existing user files or historic backups, select a production recovery point, restore production data, change authentication/keys/permissions, or maintain frozen ALI as part of backup. Failures retain useful staging for investigation, not automatic deletion. Packages contain private configuration and keys and remain unencrypted: protect the physical drive and keep packages/receipts out of public storage and Git.

## Coverage and Destination

Always include all eight NAS applications from the current inventory: complete databases and BLOBs, conversations/raw chunks, originals, incomplete uploads, derivatives, durable work state, programs and private configuration. Also include Portal grants/configuration/registry, system identities/ownership, NAS CA/private keys, tunnels and unresolved failed-upgrade protection. Ordinary historical backups/releases and this job's own staging are excluded. Data outside registered application roots needs an explicit configured source. Maintenance-computer credentials and user material not yet uploaded require separate retention.

VPS coverage includes Nginx, certificate/ACME state, SSH/tunnel credentials, firewall, systemd/custom renewal hooks, sing-box binary and private proxy configuration, identities and maintained recovery sources. Verify explicit roots in `scripts/backup-system.sh` against the live inventory. Record runtime/package versions separately: AlmaLinux packages and Certbot's environment are reinstalled, not copied from NAS's Ubuntu host. Frozen ALI is untouched. The two captures have separate timestamps, not a cross-host atomic snapshot; writes after their respective capture can be lost.

The known external disk is Samsung Portable SSD T7, 4 TB, exFAT partition label `T7`, UUID `BCDD-941E`. The controlled mount is `/mnt/nas-backup`, with exports under `/mnt/nas-backup/agent`. It contains existing user files. Last inspection found about 652 GB free and the partition unmounted; recheck identity, filesystem, mount state, writability and space each time. Mount the verified partition by UUID without formatting, using only the dedicated export subtree. If mounted elsewhere, investigate rather than overlaying or moving a user's mount automatically.

NAS temporary recovery material lives in root-owned 0700 `/var/lib/server-backups/gateway-<id>/`. This is deliberate task-limited staging, **not an internal fallback or retained backup**. Before receiving VPS data, compare estimated source sizes with free space on NAS and the external disk, allowing for NAS cold state, received VPS blobs, a potentially incompressible combined archive and operating headroom. The tool checks capacity again before pausing NAS. Missing/mismatched/read-only/insufficient external storage stops the job; an internal-only result is never successful. There is no schedule, insertion trigger, incremental chain, automatic rotation or new encryption-key workflow.

## Tools and Preflight

Source: `scripts/recovery-tool/`, a standalone Go module without a Portal dependency. Build on the maintenance computer with `scripts/build-recovery-tool.sh /absolute/path/server-recovery`; install a hash-verified root-owned 0755 `/opt/server-recovery` on NAS and VPS. Servers need no Go installation. Document synchronization carries source scripts, not the installed binary.

NAS root-private 0600 `/etc/server-recovery.json`, based on `assets/nas/server-recovery.json`, owns mount/UUID, exports, expected apps and shared roots. Apps/writer units come from root-managed registry links; Portal Web/collector are explicit additions. Deployment declarations describe resources, not backup kinds or public backup roots. The NAS role marker must be `nas`.

Inspect live coverage, prior active units, health, space, mount identity, `/run/lock/agent-backup-paused.json`, task staging and any active `agent-system-backup-*`/maintenance job. Resolve active jobs without duplicating them. An old stage is not a completed recovery point. A receipt after SIGKILL requires unit-state inspection and supervised `/opt/server-recovery resume` before another capture.

```sh
ssh nas '/opt/server-recovery status'
# Use nas-via-vps for the VPS-selected transport.
```

The tool pins the external mount/export through open descriptors. A directory at the mountpoint is not proof of a mounted disk. UUID/device and pinned-device agreement are rechecked before successful internal cleanup. Keep the drive connected until verification, flushing and any task-owned unmount finish.

## Capture, Compress and Copy

Run on the maintenance computer after preflight and authorized disk mounting:

```sh
bash ~/agent-config/skills/server-operations/scripts/backup-system.sh nas
# Or, for the explicitly selected VPS management transport:
bash ~/agent-config/skills/server-operations/scripts/backup-system.sh vps
```

`backup-vps.sh [nas|vps]` is a compatibility wrapper for the same combined workflow, defaulting to `vps`. A bare NAS `server-recovery backup` is rejected because it lacks the acknowledged VPS capture.

1. Under the VPS maintenance lock, wait for active certificate renewal, pause only its previously active renewal timer, scan/hash the roots and send an **uncompressed tar transport stream** to NAS. Keep sing-box, Nginx, tunnels and SSH running; coordinate configuration edits with the lock. Source-change detection is not an atomic snapshot. Restore the renewal timer on normal exit.
2. NAS verifies external readiness before receiving, validates every manifest/blob into its private internal stage, then returns a stage ID. The maintenance pipeline uses `pipefail`; successful exit of both SSH commands is required for separate acknowledgement. Neither VPS nor the maintenance Mac stores recovery payloads. Failed transfers leave unaccepted NAS staging, not a package.
3. Start a unique detached NAS transient unit `agent-system-backup-gateway-<id>`, limited to 2 GiB memory with `GOMEMLIMIT=1536MiB` and reduced CPU priority. Its exclusive stage claim prevents duplicate capture. It survives maintenance SSH loss; no persistent daemon or timer is installed.
4. Acquire the global exclusive maintenance lock, then registry/application deployment locks; reject drift or insufficient space. Stop active NAS timers before writers, recording units in volatile `/run/lock/agent-backup-paused.json`. Cold-scan/hash and copy complete NAS state into the same private stage. Portal briefly stops, interrupting shared authentication; reverse tunnels and SSH remain running.
5. Combine manifests under `hosts/nas/rootfs/...` and `hosts/vps/rootfs/...`, scope `nas-vps/full`, with separate capture times and host-isolated hard-link groups. Resume only previously active NAS units **before compression** and check health while the job continues.
6. Compress staged dual-host state into one `.tar.gz` on NAS. Read the full archive and verify manifest/blobs/gzip checksum without creating another uncompressed payload copy. Its manifest is embedded, not exported as a second file/package.
7. Copy the compressed package to pinned external `.copy-<id>/package.tar.gz.part`, flush it, then fully read it back and compare SHA-256 with the NAS copy stream. Publish `<id>.tar.gz` without overwriting existing backups and flush the export directory. After mount/device recheck, remove only this successful job's external temporary directory and internal stage/package. Existing archives/user files are untouched.
8. Check exit status, final path/size/hash, prior active NAS units/application health and VPS renewal timer/gateway/proxy state. Record evidence outside Git. If this task mounted the disk, safely unmount after handles/jobs finish; report a failed/busy unmount, never force it. Return package location, scope, size/hash, runtime status and whether the disk can be disconnected.

Signals attempt service resumption. After SIGKILL, host/storage failure or resume error, inspect the receipt/units before supervised `server-recovery resume`. Portal restart does not resume agent jobs. Failed compression retains internal `.part`/source staging; failed copying/verification retains useful internal/external staging. Report paths and phase. Do not clear the job claim, blindly rerun a used stage or clean old packages. Investigate and agree on retained-data cleanup/retry; a new request starts a fresh full capture after resolving the previous job.

## Progress Reporting

During long transfer, staging, compression, copy and read-back phases, **poll the job and update the user at least every 30 seconds**, plus phase changes, failures and completion. Do not launch and wait silently. The tool emits JSON to stderr/journal at start, every 10 seconds including stalled I/O, and end: `phase`, `state`, `doneBytes`, `totalBytes`, `percent`, `bytesPerSecond`, `elapsedSeconds`, `outputBytes`, `etaSeconds`.

```sh
ssh nas 'journalctl -u agent-system-backup-gateway-<id> --no-pager -n 20'
ssh nas 'systemctl show agent-system-backup-gateway-<id> -p ActiveState -p SubState -p Result -p ExecMainStatus'
```

Use `nas-via-vps` for the VPS-selected transport. Compression reports **uncompressed input** against total input, input MiB/s, current compressed size and phase ETA. External copying/read-back reports compressed bytes, MiB/s and phase ETA. Example: `nas 压缩：已处理 28/80 GiB，约 110 MiB/s，压缩包当前 12 GiB，本阶段预计剩余约 8 分钟。`

ETA uses recent throughput and describes the current phase, not an unsupported whole-job promise. If total/rate is unknown or stalled, say ETA is unavailable and report elapsed time/last progress; investigate persistent stalls. At 100% bytes, flush, verification or publication may still be pending. Announce success only after complete acceptance. After SSH loss reconnect to the same unit/journal. A collected transient unit may no longer have queryable systemctl state; use its persistent journal exit records, completed phase/final path and external package evidence. An absent unit alone is not success.

## Verification and Isolated Restore

Use explicit absolute scratch parents, never implicit `/tmp`. On NAS use pinned external scratch or explicit root-private 0700 scratch under `/var/lib/server-backups`. exFAT stores compressed packages but cannot materialize Unix ownership/hard links: isolated targets need a POSIX filesystem and must not exist. A combined restore requires **one selected host**:

```sh
/opt/server-recovery verify --work-dir /mnt/nas-backup/agent /mnt/nas-backup/agent/<id>.tar.gz
/opt/server-recovery restore --host nas --work-dir /var/lib/server-backups --out /var/lib/server-backups/isolated-nas /mnt/nas-backup/agent/<id>.tar.gz
/opt/server-recovery restore --host vps --work-dir /var/lib/server-backups --out /var/lib/server-backups/isolated-vps /mnt/nas-backup/agent/<id>.tar.gz
```

The selected prefix is stripped to `rootfs/...`. The tool verifies the whole package/chain, rejects unsafe paths, creates files/directories before symlinks and restores real hard-link groups. It never applies either host into production. It retains the selected manifest at the isolated target and applies permissions/times. Use `--ownership` as root after recreating users/groups by name; missing identities/POSIX support is failure. Do not recursively chown Portal state: devices/state lock belong to `serverportal`, historical root audit/receipt files retain their owners. Task scratch is removed; incomplete restore targets remain.

Inspect SQLite integrity/foreign keys and expected records/BLOBs, media/uploads/derivatives, grants/configuration, binaries, identities and TLS/tunnels. Use native read-only checks on isolated copies. Keep Yuyan cleanup stopped until older history/media is reviewed; reconcile Aura Origin-keyed receipts and deletion intents against originals. Record package ID/scope/host, both capture times and distinct verification/isolated-restore evidence externally. Package integrity alone is not a production drill.

Before production replacement, obtain the exact recovery point and downtime/overwrite scope, preserve current state in the authorized destination, stop writers and apply the validated host copy. Rebuild compatible NAS Ubuntu amd64/VPS AlmaLinux identities/runtime/configuration first. Review Origins, IP SANs, mounts and permissions; verify LAN/VPS runtime/data without adding an unauthenticated entrance. Recovery remains agent-operated.

## Legacy Archives and Upgrade Protection

The tool retains Portal's version-1 content-addressed format and age/incremental-chain reader. Legacy single-host packages restore without `--host`; encrypted packages require the original identity and complete ordered chain:

```sh
server-recovery verify --work-dir /absolute/scratch --identity /private/recovery.key full.tar.gz.age delta.tar.gz.age
server-recovery restore --work-dir /absolute/scratch --identity /private/recovery.key --out /absolute/new-staging full.tar.gz.age delta.tar.gz.age
server-recovery merge --work-dir /absolute/scratch --identity /private/recovery.key --out /absolute/new-full.tar.gz full.tar.gz.age delta.tar.gz.age
```

Native archives use application compatibility commands. Historical full-chain download/decryption/restore acceptance remains deferred; do not infer completion or resume it implicitly. Preserve original packages, chains, keys and inert Portal receipts. Upgrade protection remains separate `upgrade-state.py`: cold protection, candidate/runtime/affected-data acceptance, then immediate deletion of only successful protection; uncertain/failed batches remain. See [Retention](retention.md).

Focused synthetic acceptance on 2026-10-31 covered host isolation/hard links, raw transfers and corrupted/missing blobs, one-package compression/read-back, no-overwrite copying/interrupted staging, gzip/age/incremental compatibility and periodic stalled-progress events. No real NAS/VPS package or production restore drill was performed; the first real external backup remains outstanding in [current-state](current-state.md).

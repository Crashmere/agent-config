# Agent Backup and Recovery

The agent exclusively handles NAS/VPS backup, package verification and restoration through trusted SSH. Portal provides neither these operations nor backup status, archive downloads, volume configuration or recovery receipts. Read the shared authorization table before external writes, service pauses, selecting a recovery point, overwriting data or deleting archives. A request to inspect an attached drive is not a request to create a backup.

## Recovery Set

Routine backup means a new standalone full compressed package on NAS external storage. No schedule, insertion trigger, internal fallback, incremental chain, encryption-key workflow or automatic archive rotation is enabled. Application-state recovery is the objective, not an OS/disk image. Programs/configuration and all current data are included: complete databases and BLOBs, conversations/raw chunks, originals, incomplete uploads, derivatives and work state. Portal grants/configuration/registry, identities, NAS CA/private keys, tunnel materials and failed-upgrade protection are included. Ordinary historical backups/releases are excluded. Maintenance-computer credentials and not-yet-uploaded user materials require separate retention.

NAS and VPS have separate packages because a local NAS capture cannot read live gateway/proxy materials. Frozen ALI is untouched and remains only the old migration-point fallback. NAS writes after the selected backup can be lost. The unencrypted packages contain private configuration/keys; protect the physical drive and never upload them to public storage or Git.

## Tool and Configuration

Source: `scripts/recovery-tool/`, with its own Go module and no Portal dependency. Build on the maintenance computer with `scripts/build-recovery-tool.sh /absolute/path/server-recovery`; copy the hash-verified Linux amd64 binary as root-owned 0755 `/opt/server-recovery` on NAS/VPS. Servers need no Go installation. Shared document synchronization carries source, not the binary.

NAS root-private 0600 `/etc/server-recovery.json` is based on `assets/nas/server-recovery.json`. It owns mount, UUID, exports, expected applications and shared recovery roots. Apps are read directly from root-managed registry links, including their writer units; Portal Web/collector are added explicitly. Validate all inventory applications, external-volume identity and every shared path before capture. New data outside an application root requires an explicit source. Deployment/cleanup declarations no longer define backup kinds or expose backup roots.

The identified external disk is Samsung Portable SSD T7, 4 TB; its exFAT data partition is label `T7`, UUID `BCDD-941E`. Last read-only inspection found approximately 652 GB free, clean filesystem and healthy media. It contains user files and was not mounted. Recheck device/UUID, mount state and free space each time; do not infer readiness from this snapshot. Never format it or change/delete its existing content by default.

After an authorized backup request, mount that verified filesystem at `/mnt/nas-backup` without formatting, and set its UUID in the private configuration. exFAT supports the regular compressed archives/blobs but not Unix ownership/hard links. The archive manifest preserves those attributes; isolated materialization needs a POSIX filesystem. Use only the dedicated `agent/` export subtree, not unrelated drive contents.

## NAS Capture

Read `/opt/AGENTS.md`, check previously active units and no unresolved maintenance/job, verify mount/UUID, then inspect:

```sh
ssh nas '/opt/server-recovery status'
```

Use `nas-via-vps` only when the VPS management transport is selected. Missing/unconfigured/mismatched/read-only storage is a stopping condition, not internal fallback. The backup command is root-only on a host marked `nas`.

```sh
ssh nas 'systemd-run --unit=agent-nas-backup --collect --property=Type=exec --property=MemoryMax=2G --property=Environment=GOMEMLIMIT=1536MiB /opt/server-recovery backup'
ssh nas 'journalctl -u agent-nas-backup --no-pager'
```

Use a unique transient unit name if a previous job still exists. A transient job survives loss of the maintenance SSH connection; do not start a duplicate while it is running. There is no timer or persistent backup daemon.

The tool pins the verified external mount/export through open descriptors, acquires the global exclusive maintenance lock before registry/application locks, rejects registry drift, pauses active timers/writers, records stopped units in volatile `/run/lock/agent-backup-paused.json`, and cold-copies/hash-checks every included regular file. Portal also pauses, briefly interrupting shared authentication during capture. Previously running services resume before compression. Full archive read-back and flush precede publication of the package and manifest; only successful task-owned staging is deleted. Failed staging remains external and is reported.

Normal signals attempt service resumption. After SIGKILL, host/storage failure or a resume error, inspect the receipt and running units, then use `/opt/server-recovery resume` under agent supervision. The receipt names units, not backup data. Portal restart does not resume backup jobs. Check all previously active units and application health after capture; a package success message is not runtime acceptance.

## VPS Capture

First verify every source root in `scripts/backup-vps.sh` against the live VPS inventory. Include Nginx, certificate/ACME state, SSH/tunnel credentials, firewall, systemd/custom renewal hooks, sing-box binary and private proxy configuration, and maintenance sources. Check package/runtime versions separately; AlmaLinux packages and Certbot's environment are reinstalled rather than copied from an Ubuntu host.

The streaming tool refuses an active certificate renewal, pauses only its previously active timer and resumes it on exit. Wait for an active renewal before retrying. Retain sing-box/Nginx/reverse tunnels and administrative connectivity, and coordinate other configuration edits with the maintenance lock. Confirm any additional application downtime under the authorization table. The tool detects changes to regular-file contents; it is not an atomic filesystem snapshot of actively changing configuration.

```sh
NAS_HOST=nas-via-vps VPS_HOST=vps bash scripts/backup-vps.sh
```

This maintenance-computer pipeline streams the compressed archive directly from VPS to the pinned NAS external destination. Neither VPS nor Mac stores recovery data. Both SSH commands must finish successfully before a separate acceptance call publishes the verified package. A failed transport leaves an external gateway stage without publishing completion; inspect it rather than treating it as a recovery point or deleting it automatically.

## Verification and Isolated Restore

Use explicit absolute scratch paths. On NAS, the tool verifies scratch belongs to the configured external volume; it never defaults to `/tmp`. New isolated targets must not exist. No command writes into production paths automatically.

```sh
/opt/server-recovery verify --work-dir /mnt/nas-backup/agent /mnt/nas-backup/agent/package.tar.gz
/opt/server-recovery restore --work-dir /mnt/nas-backup/agent --out /absolute/new-posix-staging /mnt/nas-backup/agent/package.tar.gz
```

Restoration verifies every archive blob and chain, rejects unsafe paths, then creates files/directories before symlinks and restores only real source hard-link groups. It retains the complete manifest at the isolated target. File permissions/times are applied; add `--ownership` as root after recreating required users/groups by name. Missing identities or POSIX metadata support is a restore failure, not permission to ignore it. Do not recursively chown all Portal state: devices and the state lock belong to `serverportal`, while historical root-owned audit/receipt files retain their own owners. Work scratch is task-owned and removed; an incomplete restore target is retained for inspection.

Inspect all SQLite integrity/foreign keys and actual expected records/BLOBs; check complete media/uploads/derivatives, grants/configuration, binary versions, identity mapping and TLS/tunnel material. Use each application's native read-only `check` on the restored copy where available. Keep Yuyan cleanup stopped until older history/media is reviewed, and reconcile Aura's Origin-keyed upload receipts against restored originals. Record package ID/scope/host, capture/check time and separate isolated-restore evidence in an external receipt; never mark a full production drill complete based only on package checks.

Before production replacement, ask for the exact recovery point and downtime/data overwrite scope, preserve the current state in the authorized destination, then stop affected writers and apply the validated copy. Rebuild compatible NAS Ubuntu amd64 and VPS AlmaLinux identities/runtime/configuration before starting applications and tunnels. Review actual Origins, IP SANs, mounts and permissions. Verify runtime/data through LAN and VPS without exposing a new unauthenticated entrance.

## Legacy Archives and Upgrade Protection

The standalone tool retains the former Portal version-1 content-addressed manifest and age/incremental-chain reader. Old encrypted packages still need the original identity and complete ordered chain:

```sh
server-recovery verify --work-dir /absolute/scratch --identity /private/recovery.key full.tar.gz.age delta.tar.gz.age
server-recovery restore --work-dir /absolute/scratch --identity /private/recovery.key --out /absolute/new-staging full.tar.gz.age delta.tar.gz.age
server-recovery merge --work-dir /absolute/scratch --identity /private/recovery.key --out /absolute/new-full.tar.gz full.tar.gz.age delta.tar.gz.age
```

Old native application archives use each application's compatibility commands, not this manifest reader. Historical full-chain download/decryption/restore acceptance was deferred; generating an archive or verifying an incremental transfer does not establish a complete off-machine recovery point. Preserve the original packages, parent chains and keys. Do not resume that deferred task implicitly.

Upgrade-only local protection remains the separate `upgrade-state.py` workflow: cold protection, candidate/runtime/affected-data validation, then immediate deletion of only successful protection; uncertain/failed batches remain. See [Retention](retention.md). Removing Portal features does not delete real archives, inert old receipt files or retained failures.

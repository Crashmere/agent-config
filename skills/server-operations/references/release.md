<a id="本机发布与按需验证"></a>
# Local Releases and On-Demand Validation

Applies to the current personal services Ledger, FeeTable, FabricWorld, RecipeBox, Yuyan, ServerPortal, AICalendar, Aura, and Curio. On 2026-09-28, the user decided: GitHub backs up source code and configuration; the maintenance computer handles server builds and deployments; deployment may proceed after local validation of the current feature, without requiring the full historical regression suite or accumulating permanent test code by default. Temporary check scripts may be removed after use. Ordinary feature failures can be handled by fixes or program rollback; database migrations, bulk writes/deletions, import overwrites, and backup restoration require focused validation on an isolated copy first.

<a id="维护电脑"></a>
## Maintenance computer

Obtain agent-config and each project repository. Use the Go toolchain specified by go.mod, Node/npm, Git, OpenSSH, make, and the Python 3 standard library; no third-party Python packages are needed. The currently verified Mac has Go 1.26.8, Node 26.10.0, and npm 12.1.0. Release manifests record the actual versions, without relying on a cloud runner. Install frontend dependencies according to package-lock.json. Aura releases additionally compile the Swift PhotoKit companion with Apple Command Line Tools; Aura and Curio media validation use libvips, ExifTool, and FFmpeg. Local image-feature validation for FabricWorld and RecipeBox also requires libvips; retain Yuyan's import/export/roundtrip and other maintenance tools.

Follow software-installation to install tools on a new computer; do not install a VM to preserve the retired Linux regression suite. When goenv lazily loads Go's default PATH, the release entry point automatically adds ~/.goenv/shims.

The shared implementation is scripts/release.py. Each project's deploy/release.sh calls it, while deploy/release.json maintains the application name, build commands, artifact location, and transfer mode. Shared source defaults to ~/agent-config/skills/server-operations and can be specified with SERVER_OPERATIONS_HOME. NAS upgrade-state protection belongs to scripts/upgrade-state.py; application scripts retain their own candidate checks and health checks. Do not copy the shared implementations into business repositories.

<a id="验证构建和部署"></a>
## Validation, build, and deployment

1. Validate the current changes locally. For UI, check the affected interaction and only the viewport or input modes that could realistically behave differently; do not default every cosmetic or reversible change to desktop, mobile, keyboard, screenshots, and multiple browsers. For calculation or import logic, use representative examples. Retain necessary type checks in the build. Stop when the focused checks pass, and do not repeat work already validated during development at release time.
2. Commit a clear source snapshot and run git push origin main. Pushing only backs up the source and triggers no production operation.
3. Run make release in the project: export only Git-committed files, install locked dependencies in an isolated build directory, and run make linux to produce a static Linux amd64 program. Business applications also validate and save deploy/portal.json from the same commit.
4. make deploy reuses build artifacts from the same commit and builds only if none exist. It rejects uncommitted tracked changes, commits not backed up to origin/main, and artifacts with mismatched hashes. Untracked files are excluded from the snapshot.
5. Upload from the local machine over SSH to `nas`, then synchronize the declaration, verify the portal receipt, and check that unauthorized public endpoints on `vps` return 401. Temporary backup policy is database-only and conditional on a concrete deletion or overwrite risk; the fixed scripts use the database selection and acceptance flow described below. During compatibility, `ali` forwards to the same NAS instances rather than receiving new application releases.
6. Run scripts/sync-docs.sh after pushing managed documentation changes; a routine release does not itself require an operations, verification, or current-state entry, and documentation-only changes do not require program deployment.

The local `.local/releases/<full-commit>/` directory stores program, manifest.json, business applications' portal.json, and last-deployment.json. The manifest records the source commit, SHA-256, tool versions, and build commands. It proves only build/declaration checks and must not be presented as a functional validation record. These materials are neither committed to Git nor automatically cleaned up. Use make releases to inspect them.

The script returns nonzero if it fails partway through. If program deployment succeeds but the portal declaration or public checks fail, the running program may already be updated; confirm from the output and last-deployment.json rather than blindly repeating deployment. To fix only a declaration, run make portal without building or restarting the service. When source, build arguments, or toolchain changes require regenerating artifacts, preserve the existing materials by moving that version directory to a clearly identified new location, then rerun make release.

<a id="身份与传输"></a>
## Identities and transfer

- `RELEASE_HOST` defaults to `nas`, using locally trusted SSH host configuration and strict fingerprint verification. Explicit `RELEASE_HOST=ali` retains the legacy path; it must not be used to create a second active data writer after cutover.
- Business applications use their own restricted `<app>-deploy` identities and the maintenance computer's `~/.ssh/nas_deploy_ed25519` key. Explicit `ali` releases select `~/.ssh/ali_deploy_ed25519`; `RELEASE_KEY` overrides either, and other SSH aliases require an explicit key. Keep private keys only on the maintenance computer and safeguard them independently. These keys have business-application deployment/data permissions, not whole-server administrator permissions; do not reuse the ALI key on NAS.
- With literal `RELEASE_HOST=nas` (the default), public acceptance resolves SSH alias `vps` and uses HTTPS 8443; sing-box retains TCP 443. For the custom maintenance alias `nas-via-vps`, set `RELEASE_PUBLIC_ORIGIN` explicitly to the primary VPS HTTPS 8443 Origin, independently of the SSH target. Otherwise the current driver derives `https://127.0.0.1` from that alias, so public acceptance can fail after the program is published. Business applications using the alias also require the NAS `RELEASE_KEY`; Portal uses the alias's administrator identity. For NAS LAN acceptance, provide its HTTPS Origin plus `RELEASE_CA_FILE=<local-CA-root.pem>`; curl still validates certificates, never with `-k`.
- Server authorized_keys sets restrict and the fixed deploy-ssh.sh; only deploy, portal-check, and portal are accepted, and sudo permits only this application's root-managed deploy-release.sh. Use each project's setup-deploy.sh to create identities for new servers/applications; explicitly rotate public keys for existing accounts rather than reinitializing them.
- ServerPortal uses the existing administrator SSH access. Its collector runs as root, so portal deployment remains an administrator operation. Its fixed scripts are maintained under ServerPortal/deploy; do not create a portal deployment account that pretends to have low privileges.
- Production-deployment GitHub Actions is disabled in every application repository; workflows and the former production Secrets have been removed, and old CI public keys revoked. Do not upload production deployment private keys to GitHub. GitHub push authentication remains separate. Aura has a user-authorized Apple-client installer workflow on hosted macOS: it builds a universal DMG and unsigned iOS device IPA, verifies them, and publishes public GitHub Releases after client-source updates. It has no server access or deployment secrets; Aura docs/CLIENT-RELEASE.md owns its versioning and packaging contract.
- SSH compression is enabled. Yuyan continues to transfer a gzip stream and verify the uncompressed hash; other applications retain raw program streams. Do not install build tools on the server.

<a id="回退和数据保护"></a>
## Rollback and data protection

`make rollback COMMIT=<full-old-commit>` uses a locally retained, verified version and deploys it through the same server script and health checks. Evaluate database deletion or overwrite risk before choosing temporary protection; a program rollback alone does not justify another backup. The fixed scripts skip capture unless a database is selected. The original production program and hash of each migrated service were saved during migration to support rollback of its first local release; Curio starts from its new NAS installation and has no migration-saved ALI program. Subsequent builds naturally accumulate locally available versions.

First confirm the target older program is compatible with the current schema/device state. Program rollback is not database restoration and does not automatically restore photos, databases, or portal credentials. For actual restoration, select a recovery point according to project docs and obtain separate confirmation. Server releases store previous/result/metadata/recovery; source versions for program, data, and documentation are recorded separately. NAS has no retained routine internal application backup or automatic archive/failed-upgrade pruning; task-limited manual backup staging follows [Agent backup and recovery](backup-recovery.md). The [shared retention task](retention.md) describes the legacy ALI policy only; local .local/releases is outside its scope.

Portal updates briefly stop the NAS Web process and collector. An active archive task causes the update to be rejected; do not start new backups or cleanup during deployment. Public device authentication is briefly unavailable; business application processes are not restarted. Portal upgrade snapshots and release directories are private shared resources, not web browse/cleanup targets. ServerPortal's fixed release script owns its coordinated pause and acceptance flow.

## NAS Temporary Upgrade State

Follow [temporary upgrade backup scope](retention.md#temporary-upgrade-backups): skip capture when existing database data is not at risk, otherwise protect only the affected databases. Never temporarily back up non-database files, including private configuration and Portal grant/registry files. Avoid duplicate copies, whole-file-tree hashing, compression and external transfers; use focused checks and reuse a consistent database snapshot where practical.

### Database backup selection

The default is no temporary database backup. For a known deletion or overwrite operation, record its selection in the release commit's `deploy/release.json`:

```json
"database_backups": [
  {"path": "aura.sqlite", "reason": "Rewrite affected catalog rows during startup migration"}
]
```

Remove the declaration when that transition is complete; ordinary later releases must not keep an obsolete migration backup requirement. The local build stores declarations in `manifest.json`, so rollback uses the selected old artifact's declaration. For a one-time authorized operation, pass comma-separated relative paths through `RELEASE_BACKUP_DATABASES` and describe the operation in `RELEASE_BACKUP_REASON`. The local driver validates the request and sends it as a bounded base64url argument in the existing restricted `deploy` command. The server accepts only real SQLite files below the application's `data`; a declaration cannot select other files or another application's data. Original two-argument deployments and portal commands remain supported.

Yuyan additionally runs the candidate's `migrate --dry-run` as `yuyan` before capture. Its pending table rebuild/drop steps automatically select `yuyan.db`; no pending step means no automatic backup. FabricWorld's current migration is additive and does not select a backup by itself. New destructive startup/migration behavior in other applications must declare its affected databases in the same commit before release.

### Deployment and acceptance

Root installs `/etc/server-maintenance-host` containing exactly `nas` and synchronizes the shared helper to `/opt/server-context/scripts/upgrade-state.py`. NAS releases hold a nonblocking shared `/run/lock/server-maintenance.lock`, then the exclusive `/run/lock/<app>-deploy.lock`. A manual external full backup holds the global lock exclusively before taking application locks, so it cannot capture during a program/configuration switch.

After upload and hash verification, the fixed release gracefully stops the affected application and calls `begin`. With no selection, the helper records only upgrade metadata and returns the existing data directory; candidate checks operate there without a temporary data copy. Portal's device state is JSON, so ordinary Portal releases create no temporary backup. Its configuration and runtime/registry checks remain part of normal acceptance.

With selected databases, the helper captures complete committed SQLite content under root-private `/var/lib/server-upgrades/<app>/<release>/`, records paths/reasons/hashes, and excludes all other files. It creates a writable database copy only when Yuyan or FabricWorld needs migration rehearsal. The recovery snapshot remains root-private; candidate checks run as the application identity. Yuyan links existing assets into its rehearsal directory so checks can find them without copying payloads. Intentional migrations require authorization and focused rehearsal before applying them to stopped live data.

After atomic replacement, the script starts the application and checks direct/proxied runtime health. When no backup exists, it records `current-commit` and calls `accept` immediately, without a second stop or full data comparison. When a database backup exists, it stops the application again and runs `verify` for those databases only: SQLite integrity, foreign keys, previous columns and full row multiplicity including BLOBs. It then restarts, checks health, records `current-commit`, and accepts. `accept` verifies the candidate hash and active units, records selected paths/reasons and acceptance, and removes only that upgrade's temporary database snapshot and rehearsal copy.

Failure, interruption or unexplained database changes retain any captured protection. Restarting the previous program does not restore data. An incompatible schema change can prevent the previous binary from running; use a compatible fix or separately authorized restoration. For an intentional transformation rejected by preservation checks, independently validate the selected database and runtime, then root may use `accept --manual-validation '<specific validation evidence>'` under the same maintenance/deploy locks. This is unavailable through the restricted protocol. Existing legacy snapshots remain verifiable with their original complete scope. Original ALI backups and maintenance-computer `backups/` remain preserved.

Application installers default to disabled native backup timers and do not create a first internal daily snapshot. `ENABLE_APP_BACKUP_TIMER=true` is an explicit legacy-host option requiring its retention lock; installers reject it on a host marked `nas`. Native backup/restore commands remain usable for existing archives and isolated checks, but NAS routine complete compressed backups use the external-drive agent-only cold-copy workflow.

When release mechanisms, authentication, or backup formats change, validate the normal path and key failure branches relevant to the change. Check scripts may be temporary; there is no requirement to restore a permanent full test suite. Retain shared diagnostic tools and runtime safeguards according to their actual value.

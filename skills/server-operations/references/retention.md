<a id="发布材料自动保留"></a>
# Automatic Retention of Release Materials

On 2026-10-01, the user authorized cleanup of existing materials for six services under the following rules and continued automatic execution. This authorization covers only release history and ordinary pre-release backups; expanding the scope or deleting other real data still follows the SKILL authorization table.

<a id="策略与实现"></a>
## Policy and implementation

The shared maintenance sources are `scripts/prune-releases.py`, `assets/ali-release-retention.service`, `.timer`, and `.tmpfiles.conf`. The implementation uses only the Python 3 standard library and installs no dependencies. The service reads registered applications from ServerPortal's controlled registry.d and reuses validate-portal.py to validate declarations; for the portal itself, it uses only explicitly registered backups/releases. New applications using the same release and backup contracts follow the same rules; other contracts require explicit adaptation first.

- Retain the latest 3 successful releases and the currently running version; sort by completion time in result, not by commit string or directory name.
- Retain the latest 5 complete before-deploy backups and additionally protect backups corresponding to retained release batches. Exceeding 3/5 because an older current version or failed batch is protected is normal; do not delete protected items to meet a count. Materials from new releases between runs may also temporarily exceed the counts and rotate during the next idle cleanup.
- A failed batch may be cleaned only when recovery is healthy or not-needed, completion was more than 7 days ago, a later successful release exists, and the application is currently healthy. Each application's root release script writes recovery in finish before writing the terminal result. Retain old failure records without rollback results for manual review; protect unfinished batches, unknown formats, validation anomalies, and symlinks, recording the reason.
- Match only `<40-character-commit>.<6-character-release-suffix>` and its corresponding before-deploy name. Do not process daily, manual, pre-migration/pre-restoration snapshots, business data, portal exports, local build directories, or cloud snapshots.
- Each run first validates backup structure, SQLite quick_check, media-manifest SHA-256 (hashing identical hard links only once), retained programs, and the program hash corresponding to current-commit. Delete nothing if the current-version record is invalid, a retained program is damaged, or runtime status is abnormal.
- Delete backups before old release directories. Before acting on each item, recheck its fingerprint, including path, inode, mode, size, and mtime, and operate through directory descriptors that do not follow symlinks. Reclaimed-space estimates count only files whose entire hard-link set is covered by the deletion set, plus directory space.

<a id="调度与并发"></a>
## Scheduling and concurrency

`ali-release-retention.timer` runs daily at 05:00 Beijing time with Persistent=true. The task is independent of application releases; failure marks only this maintenance unit as failed and does not change release results or restart business services.

Cleanup first takes an exclusive lock on `/run/lock/ali-release-retention.lock`, then acquires every application's existing `<app>-deploy.lock` without blocking. Business applications' daily backup units hold the former lock through `flock --shared` in ExecStart. A backup that starts first causes cleanup to skip; if cleanup starts first, new backups wait for the lock to be released. Releases and portal archives/manual cleanup already use deployment locks. Cleanup checks portal task status, daily backup status, and each application's loopback health, and also skips when it detects a cloud backup ids process. Busy skips are recorded in the journal and retried at the next scheduled run; do not stop other tasks.

Cleanup uses CPUQuota=50%, MemoryMax=256M, Nice=15, and a 15-minute timeout. Read-only previews also acquire locks and validate real materials; avoid overlapping active maintenance when directories are large.

<a id="回执与日志"></a>
## Receipts and logs

`/var/lib/ali-release-retention/state.json` is a small root-private provenance receipt recording which completed batch owns each remaining pre-release backup. It is written atomically before deleting old program directories, preventing the last two backups from losing release metadata when retaining 3 programs and 5 backups. Each run removes receipts for deleted backups rather than accumulating history. Interrupted cleanup can be rerun; backups without provenance because of a missing receipt or mismatched fingerprint are automatically protected, not assumed safe to delete.

The state directory is registered as private config in the portal's shared resources and backed up with portal recovery materials. If restoration changes inodes, receipt fingerprints no longer match and automatic deletion of the relevant backups stops; verify provenance against the complete materials available. Logs use the journal and include plans, skip/protection reasons, and per-item deletion intent and results; do not create a separate indefinitely growing audit file.

<a id="安装检查与停用"></a>
## Installation, checks, and disabling

First commit and push the shared source and run sync-docs.sh. On initial installation, install the shared lock and state directory, then each application's backup unit with flock and release script that records recovery. Application scripts remain maintained by their owning projects; check the previous script's hash and hold the deployment lock while deploying them. No business program rebuild or restart is needed. On new servers, prepare the lock file in this section before enabling any backup timer.

```sh
install -m 0644 /opt/server-context/assets/ali-release-retention.tmpfiles.conf /etc/tmpfiles.d/ali-release-retention.conf
systemd-tmpfiles --create /etc/tmpfiles.d/ali-release-retention.conf
install -d -m 0700 /var/lib/ali-release-retention
install -m 0644 /opt/server-context/assets/ali-release-retention.service /etc/systemd/system/ali-release-retention.service
install -m 0644 /opt/server-context/assets/ali-release-retention.timer /etc/systemd/system/ali-release-retention.timer
systemctl daemon-reload
python3 /opt/server-context/scripts/prune-releases.py                 # read-only preview
python3 /opt/server-context/scripts/prune-releases.py --apply --expect-plan <preview-plan_sha256>
systemctl enable --now ali-release-retention.timer
systemctl status ali-release-retention.timer
journalctl -u ali-release-retention.service --no-pager
```

Before the first run, review the deletion list, protected items, and estimated actual reclaimed space, then execute under the policy already confirmed by the user. `--expect-plan` rejects a plan that differs from the reviewed preview; each scheduled unit run regenerates and executes the current policy while holding the lock. To trigger the same policy manually, run `systemctl start ali-release-retention.service`, then inspect Result, deletion logs, and the retained list after completion; an inactive unit does not imply failure.

Pause automatic cleanup with `systemctl disable --now ali-release-retention.timer`; check the service separately for any task already running. Disabling requires neither program rollback nor restoration of deleted materials. Turning off the timer cannot undo deletion; data restoration still requires selecting a point from retained native/cloud backups and validating it.

<a id="部署与验收"></a>
## Deployment and acceptance

On 2026-10-01, six release scripts, five daily-backup lock entry points, and the shared tmpfiles/service/timer were installed, and the portal collector was verified to load the private receipt resource. The first execution matched the preview list exactly: 164 ordinary old release directories and 151 ordinary pre-release backups were deleted, reclaiming about 9.15 GiB and reducing root-disk usage from 45% to 20%. Ledger's schema2 migration release materials were retained as a special batch; daily, manual, and portal exports were verified unchanged. The first cleanup changed neither the versions nor processes of the six business programs, and the timer is enabled.

Isolated validation covered three snapshot contracts, repeated rotation and receipt reuse, hard-link space estimates, current-version/failed-batch protection, rejection of symlinks/damaged materials/changed manifests, and release-failure recovery markers. Five backup units verified mutual exclusion between shared and exclusive locks in real Linux sandboxes; 200 consecutive SQLite validations showed no file-descriptor growth. A repeat read-only validation after the first cleanup succeeded; excess materials from releases added during the same period remain subject to the next scheduled run.

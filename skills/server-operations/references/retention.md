<a id="发布材料自动保留"></a>
# Upgrade Protection and Retained Materials

The `nas` contract replaces retained pre-deployment data backups with temporary upgrade protection. Routine application backups are manual, full, compressed recovery sets on external storage. [NAS migration and recovery](nas-migration.md) owns that cross-host workflow; [Local releases](release.md) owns the release commands and validation sequence. The actual cutover phase is recorded in [current-state](current-state.md).

## NAS Upgrade Protection

The root-managed marker `/etc/server-maintenance-host` contains `nas`. The shared helper `scripts/upgrade-state.py` accepts only that marked host and known application names. Callers hold the shared `/run/lock/server-maintenance.lock` and the application's deployment lock. A manual full backup takes the global lock exclusively so it cannot overlap an upgrade.

After affected services stop gracefully, the helper cold-copies complete application `data`, `config`, and `bin` into root-private `/var/lib/server-upgrades/<app>/<release>/`, with Portal registry and source markers when applicable. Copies include archive BLOBs, stored derivatives, and unfinished uploads. The candidate is checked against a disposable copy; it must not initialize missing production data or rely on an old summary-only backup.

An unchanged-data upgrade validates previous SQLite tables, columns, row multiplicities and BLOB content, remaining data files, and Portal grants before final runtime acceptance. An intentional data transformation requires targeted independent validation and recorded agent evidence; generic health or row counts alone do not authorize deleting protection.

After both affected-data and runtime validation succeed, delete only that upgrade's protection and disposable candidate-check data. Keep small acceptance/source records and program artifacts needed for rollback. Failure, interruption, uncertain data preservation, or cleanup failure retains explicitly identified protection and is reported. There is no five-backup retention rule, automatic backup rotation, or age-based cleanup for these retained failures.

Application declarations must not expose unresolved upgrade snapshots to ordinary Portal cleanup. `/var/lib/server-upgrades` is a private recovery resource, not a directory for routine full backups. A native program rollback restores the program, not the database.

## Manual Backup Staging

Manual dual-host backups temporarily gather cold NAS state, VPS blobs and one compressed package under root-private `/var/lib/server-backups/gateway-<id>/`. Only a successfully verified/flushed external package permits removal of that job's internal stage and external `.copy-<id>` directory. Interrupted/failed stages remain identified for agent review; no age-based pruning or Portal cleanup applies. This does not make internal staging an independent recovery point. See [Agent backup and recovery](backup-recovery.md) for the owning workflow.

## Historical ALI Materials

Before cutover, legacy `ali` still has application backup timers and `ali-release-retention.timer`. Cutover stops and disables those tasks while preserving their existing data. The old implementation sources remain `scripts/prune-releases.py`, `assets/ali-release-retention.service`, `.timer`, and `.tmpfiles.conf`; they are not the NAS policy and must not be installed or enabled on `nas`.

The old task retains three successful program releases and five pre-deployment backups with current-version and failure protection. Its lock and private receipt are `/run/lock/ali-release-retention.lock` and `/var/lib/ali-release-retention/state.json`. Keep existing receipts with historical materials; a missing receipt, restored inode, unknown batch, or excess directory count is not deletion approval. Source ownership and rollback provenance remain useful even when the scheduler is stopped.

Manual/pre-migration/pre-recovery archives, `/opt/backup-exports`, historical Portal exports, cloud backups, and maintenance-computer `backups/` are outside automatic cleanup. Do not remove them to meet a retained count. Existing old incremental or encrypted recovery sets keep their parent-chain and key requirements.

## Operational Checks

Inspect the marker, actual enabled timers, active backup/release jobs, and private upgrade directories before cleanup. Complete or failed job receipts determine what happened; an inactive oneshot service is not a failure, and a health endpoint does not prove data preservation. Log and system temporary-file maintenance may continue, but must not target application backups, `/var/lib/server-upgrades` or `/var/lib/server-backups`.

Stop the legacy ALI scheduler with `systemctl disable --now ali-release-retention.timer` during the authorized cutover, then separately check whether its service is still running. Turning off the timer does not undo earlier deletion or authorize deleting retained archives. Any real restoration still requires a confirmed recovery point and isolated validation.

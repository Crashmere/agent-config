<a id="发布材料自动保留"></a>
# Upgrade Protection and Retained Materials

The `nas` contract replaces retained pre-deployment data backups with temporary upgrade protection. Routine application backups are manual, full, compressed recovery sets on external storage. [NAS migration and recovery](nas-migration.md) owns that cross-host workflow; [Local releases](release.md) owns the release commands and validation sequence. The actual cutover phase is recorded in [current-state](current-state.md).

## Data-protection scope

### Temporary upgrade backups

On `nas`, minimize backup volume and time spent waiting for upgrade protection. Before capture, identify the exact database and upgrade operation that can delete or overwrite existing data, such as a destructive migration, table rebuild, bulk rewrite, or startup cleanup. Create no temporary backup when the release only replaces the program, changes presentation, or adds schema without putting existing data at risk. A version change, restart, or rollback alone does not justify a snapshot.

For a concrete database deletion or overwrite risk, capture only the affected databases with a consistent native snapshot or verified cold copy after their writers stop. Preserve their complete committed content, including BLOBs and any journal state required for recovery. Do not select unrelated databases or fall back to copying the application root. Record the selected database paths and the operation that requires protection.

Never create temporary upgrade backups of non-database files: originals, photos, videos, attachments, conversation files, upload chunks, derivatives, work directories, configuration, credentials, device-grant JSON, registry links, models, runtime environments, caches, or existing backups. Keep these files in place; their exclusion from temporary backup is not permission to delete or overwrite them. Destructive file operations still require the applicable authorization.

Reuse one consistent database snapshot for protection and checks wherever possible. Create a second writable database copy only when an authorized migration rehearsal needs it; read-only checks should use the existing copy. Do not add whole-directory copying, media hashing, archive compression, or external transfers to an ordinary upgrade. Keep required locks, atomic program replacement, targeted checks and health acceptance; limit the stopped-writer interval to the necessary database capture or migration.

### Manual external backups and recovery

A full NAS/VPS external recovery request retains complete business-data and recovery-critical private-configuration coverage, including databases/BLOBs, originals, durable uploads/work, stored derivatives, credentials and identity records. Its temporary staging has the same full scope as the requested recovery package; the database-only upgrade rule does not apply to it.

For those recovery copies, exclude downloadable model weights and model source, Python/CUDA environments, dependency/download caches and benchmark fixtures. Record source commits, model checksums, dependency locks and installation commands needed to rebuild those components. Program rollback uses separately retained verified release artifacts. Do not copy an entire `bin` or runtime tree merely because it is under an application's root. These exclusions govern new copies and do not authorize deleting live models, working runtimes, existing backups or unresolved protection.

<a id="tool-alignment"></a>
## Capture implementation

The current `upgrade-state.py` implementation has not adopted the database-only upgrade rule. Its `begin` action still copies application `data`, `config`, Portal `registry.d` and the available `current-commit` marker, then creates a second complete candidate data copy. It excludes `bin`, but has no database-selection or no-backup mode; its verification still compares all previous database content and non-database files. Existing fixed release scripts call this helper for every NAS release. Updating this maintenance policy does not change that automatic behavior. Adoption requires a separately authorized change to the root-managed release flow; do not add another backup around the existing helper or bypass its checks by hand.

The external-backup tool `server-recovery` excludes top-level application `bin`, `staging`, `backups` and `releases` before estimating sizes or scanning/hashing source files. It also excludes `<app>/<release>/bin` when capturing retained upgrade protection through the shared `/var/lib/server-upgrades` source. Existing snapshots and archives are not edited.

Keep downloadable models, runtime environments, dependency caches and benchmark fixtures under the application's `bin` tree. For full external recovery captures, the exclusions are based on directory responsibility, not extensions: a user original or upload in `data` remains included even if its name ends in `.pth` or `.bin`. Current source commits, managed project docs and private configuration remain available for reconstruction. Use the read-only `server-recovery capture-plan` command on nas to inspect selected source sizes and exclusions without mounting storage, stopping services or creating a backup.

## NAS Upgrade Protection

The root-managed marker `/etc/server-maintenance-host` contains `nas`. The shared helper `scripts/upgrade-state.py` accepts only that marked host and known application names. Callers hold the shared `/run/lock/server-maintenance.lock` and the application's deployment lock. A manual full backup takes the global lock exclusively so it cannot overlap an upgrade.

New temporary upgrade protection follows the database selection above and uses root-private `/var/lib/server-upgrades/<app>/<release>/` only when an affected database needs it. A candidate must not initialize missing production data or use a summary-only snapshot that omits committed database content. The current helper's broader capture remains the implementation limitation described above.

Validate the database behavior affected by the change and runtime health before final acceptance. An intentional data transformation requires targeted independent validation and recorded agent evidence; generic health or row counts alone do not authorize deleting its protection. File checks must follow the affected interaction or concrete failure risk, without expanding the temporary backup scope.

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

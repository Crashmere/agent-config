# Common Issues: Releases, Documentation Sync, Backups, and Media Processing

Shared solutions for local releases, doc sync, recovery/cold-backup staging, disk retention, and FFmpeg/libvips/NVIDIA media workloads. See the [symptom index](common-issues.md) for all topics.


<a id="systemd-沙箱下照片硬链接备份失败"></a>

## Photo Hard-Link Backups Fail in a systemd Sandbox

This applies to historical ALI native snapshots for FabricWorld, RecipeBox, Yuyan, and any explicitly authorized operation that hard-links data files into its backup directory. SQLite-only snapshots are unaffected. FabricWorld and RecipeBox were fixed and verified by the following method on 2026-09-24; Yuyan used this configuration at installation on 2026-09-26 and was verified through its unit. NAS full external backups cold-copy files instead and do not use this timer/hard-link workflow.

Symptom: `<app>-backup.service` fails every time, with `hard-link media backup: link ... invalid cross-device link` in the journal. The initial backup made manually with runuser during installation does not use the unit sandbox and therefore does not expose the issue. The two applications consequently failed for five days from their first scheduled runs before discovery.

Cause: the unit used `ProtectSystem=strict` and `ReadWritePaths=/opt/<app>/data /opt/<app>/backups`, causing systemd to bind-mount the two directories as separate mount points. Linux cannot create hard links across mount points, even when the underlying filesystem is the same, and returns EXDEV.

Fix: use `ReadWritePaths=/opt/<app>` in the backup unit, placing data and backups under one writable mount point. Everything else under `/opt/<app>` is owned by root, and file permissions already prevent the application user from writing there, so the effective write scope does not change. Update `deploy/<app>-backup.service` in the project repository and push it, install it to `/opt/<app>/config/`, then run `systemctl daemon-reload`; the resident service unit does not need a change. Failed runs leave no incomplete backup directory, so there is nothing to clean up.

When verifying an authorized legacy native-snapshot run, `systemctl show <app>-backup.service -p Result` must report success, its `daily-*` directory must contain `manifest.json`, and the photo hard-link count (`stat -c %h`) must be greater than 1. Verify the real unit sandbox, not only a manual runuser command. Do not enable a NAS backup timer for this check; [manual full backups](nas-migration.md#manual-full-backups) define the NAS operation.


<a id="新应用首次文档同步找不到目录"></a>

## First Documentation Sync for a New Application Cannot Find the Directory

`sync-docs.sh` should create `/opt/<app>/docs` directly for a new application. The old implementation first ran find to scan for AppleDouble files; when the destination did not yet exist, find returned nonzero and pipefail stopped the script before installation. The service itself and completed targets were unaffected.

The shared script now prescans only directories that exist, and the later `install -D` creates the destination during the first synchronization. `--check` also permits a missing new destination and reports BEHIND. Read failures in existing directories remain errors and are not hidden with `|| true`. This was verified during AICalendar's real first documentation synchronization on 2026-10-07, while existing projects used the same flow. After the fix, retry only the incomplete target; there is no need to release the program again.


<a id="sync-provenance-ssh-failure"></a>

## SSH Failure Is Treated as Missing Sync Provenance

The initial `SOURCE` read in `sync-docs.sh` used `|| true` to allow first synchronization. This also hid an SSH timeout, leaving an empty recorded commit and starting another connection instead of stopping. An empty result after a transport failure cannot establish that provenance is absent or that the managed drift check can be skipped.

The remote command now checks whether `SOURCE` exists and reads it only when present. SSH failures and errors reading an existing file abort the local script immediately, including in `--check` mode. A genuinely missing file still permits first synchronization. This applies to shared context and every project's documentation on NAS, VPS, and other explicitly selected targets. Select the trusted `nas-via-vps` alias for authorized NAS maintenance from outside the LAN; do not change host-key verification, authentication, or public exposure to work around a connection timeout.


## Minimal gateway rewrites unchanged documentation

On `vps`, the minimal AlmaLinux image lacks `cmp`. The synchronization script suppressed comparison errors and therefore installed every managed file even when its content and mode were unchanged; the later manifest verification still passed. The skip check now compares file content through the already-required `sha256sum` and retains the mode check, without adding a diffutils package dependency. Verify with a real shared-context synchronization: only changed files should be installed and the complete final manifest must still match the pushed source. This concerns controlled source copies, not application programs, live Nginx/SSH configuration or the tunnel transport.


<a id="本机发布失败"></a>

## Local Release Fails

See [Local releases](release.md) for the current release entry point, identity, artifact reuse, and rollback. On upload failure, first check local SSH, networking, and release logs. The service continues running until verification passes; do not repeatedly stop it for network failures. Repair a declaration failure separately with `make portal`.

If the log already says `Deployed` and a later public HTTPS check times out, the program may have been released successfully. First compare `current-commit`, the unit and loopback health, and the local `last-deployment.json` `program` field. Then retry only the read-only unauthenticated API check, expecting 401. Once that succeeds, record the local release receipt without redeploying the program. The portal release was handled this way on 2026-09-30.

If new SSH connections from the maintenance workstation occasionally time out, first use a short `ConnectTimeout` for a read-only connectivity check. Documentation synchronization may temporarily use OpenSSH ControlMaster to reuse an established connection, while retaining the original SSH alias, identity, and host-key verification; close the temporary connection afterward. A connection timeout alone does not prove an application or server failure and does not justify restarting a service or changing authentication.


<a id="shutdown-timeout-blocks-release"></a>

## Shutdown Timeout Blocks Release

On `nas`, a Lilt release stopped the old process, but its bounded HTTP shutdown returned `context deadline exceeded` and exited with status 1. Systemd retained `ActiveState=failed`; the shared upgrade helper requires exactly `inactive`, so it rejected publication and the fixed release script restored the healthy old program. No database protection was selected and no data rollback occurred. The shutdown deadline identifies unfinished HTTP shutdown, not the request responsible. Source inspection found the same returned-shutdown-error pattern in Ledger, FeeTable and Yuyan; their deployments were not implicated in this incident.

After confirming the old program is healthy, inspect the shutdown journal and current connections before retrying. If this failure repeats, stop only the affected service under the shared maintenance and application deployment locks. Verify `MainPID=0`, an empty service cgroup and no application listener. A confirmed shutdown-deadline `exit-code` result may be cleared with `systemctl reset-failed <app>.service` after those checks; investigate other exit causes instead. Release the locks and promptly retry the existing restricted publication with its verified artifact. Restart the previous program if publication cannot proceed. Lilt's separately verified stop returned `inactive` normally and the next restricted release succeeded. Keep the helper's stopped-state check and root-managed publication scripts unchanged.


## Recovery Capture Rejects Escaped Systemd Names

On VPS, a full gateway capture failed with `invalid entry` before emitting its manifest because a systemd directory name contained the literal escape `\x2d`. POSIX filenames may contain backslashes; treating every backslash as a path separator rejects valid systemd configuration. This affects the shared recovery tool on NAS and VPS, including all applications captured by the combined workflow.

The maintained validator accepts literal backslashes on POSIX hosts while still rejecting NUL, absolute paths, parent traversal, non-canonical paths, duplicate entries and non-directory ancestors. Hosts with backslash path separators continue to reject them. Entry errors report the path and relevant metadata. A focused package/read-back/materialization regression preserves an escaped systemd directory and its symlink and checks traversal rejection. Build the maintained tool locally and hash-verify its installation on both hosts before retrying; do not rename production units or omit configuration roots. A pre-manifest failure leaves unaccepted NAS staging and no recovery package; inspect it and verify renewal/runtime state before a fresh capture, preserving failed material under the backup runbook.


## Cold Backup Misses A Dependent Writer During Resumption

On NAS, stopping `serverportal-agent.service` also stopped `serverportal.service` through its `Requires` dependency. Inspecting each unit immediately before stopping it therefore recorded Portal as already inactive and omitted it from resumption. The cold capture remained consistent, but Portal stayed stopped until the agent's independent health check detected and restarted it.

The recovery tool records and persists the complete initial active set before stopping any unit, stops timers before services, resumes that saved set and verifies every saved unit is active before clearing the paused receipt. This applies to all registered NAS writers and avoids order-dependent omissions. After a backup, compare every previously active unit and application/Portal health independently; a successful compression phase does not prove service resumption. Do not restart originally inactive units or recapture an already completed cold stage to repair a runtime omission.


## Cold Staging Fails Later Content Verification

The first real NAS/VPS external-backup attempt failed during compression because a staged AICalendar database no longer matched its content-addressed filename. The streaming cold-copy checksum had passed. Read-only comparison subsequently found exactly one changed byte, with one flipped bit, in the staged database; the production file still matched the captured manifest hash and both files' size/modification metadata were unchanged during comparison. No external package was published.

Buffered and direct-disk reads returned the same staged hash, as did the system SHA-256 tool and Go with CPU acceleration enabled and disabled. Staged SQLite `quick_check` passed; structural checks cannot establish unchanged BLOB/content bytes. Both NAS SSDs reported zero media/data-integrity errors and no relevant kernel/OOM evidence was recorded. A bounded locked 4 GiB memory check passed stuck-address, random-value, XOR and subtraction tests; it covers only that allocation, not all 64 GiB. These results locate a real byte mismatch in the copy/write-back path but do not identify RAM, CPU, storage, or a software defect as its cause. NAS's earlier cross-OS freeze history remains relevant to hardware/firmware investigation, not proof.

Archive mismatch errors include the logical path, staged blob, actual/expected byte count and hashes. Independently verify staged blob hashes, compare byte/page differences without exposing business content, and preserve failed staging/partial archives. Check application resumption and storage/kernel evidence, then obtain an explicit retry decision before a fresh capture if the underlying cause remains unresolved. Persistent or recurring mismatches justify an authorized offline full-memory test and, if errors occur, testing the DIMMs separately. Do not bypass hashes, repair the failed blob in place, modify the recorded manifest to accept changed bytes, reuse a claimed stage or overwrite production data. A later user-authorized fresh capture passed archive/external read-back acceptance while the failed stage remained preserved; that success does not identify or eliminate the earlier bit-flip cause. [Current-state](current-state.md#manual-data-archives) owns the accepted external recovery point.


## Retired Portal Backup Integrations

Removing Portal backup APIs can leave application-owned status widgets, links, polling or maintenance instructions behind. Aura had a web summary polling `/portal/api/recovery` and linking to `/portal/#/backups`; removing that component and its styles eliminates both requests and the broken navigation. Audit all inventory applications' frontend/server sources, entry build assets and `deploy/portal.json`, then compare the NAS declaration hashes with their maintained sources. Portal login assets are public; inspect business pages only through the trusted [view tunnel](conventions.md#agents-viewing-live-pages), without extracting user cookies.

Also check current READMEs, operations and limitation documents for daily native scheduling, Portal-driven backup, internal routine destinations and cache exclusions. NAS agent full packages include stored derivatives, while native historical formats may omit them. Dated verification records and archived design baselines describe their historical scope; do not erase valid evidence or present it as current readiness. Keep native compatibility commands and inactive unit files, but verify that backup services are inactive and timers are neither active nor enabled. FabricWorld and RecipeBox cleanup timers remain separate application writers, not backup jobs. Application-documentation synchronization targets active NAS instances and leaves frozen ALI applications unchanged; shared gateway context follows its separately maintained infrastructure contract. See [Agent backup and recovery](backup-recovery.md) for the maintained capture/restore workflow.


## Documentation Sync Rejects a Linked Git Worktree

A linked Git worktree has a `.git` file rather than a directory, and detached HEAD has no branch upstream. A directory-only checkout check rejects it as missing; an unconditional `@{upstream}` check rejects a detached commit even when it is already published. These assumptions affect the shared documentation sync for every project on `nas`, `vps` and `ali`.

The maintained `sync-docs.sh` accepts both checkout forms and verifies a detached commit against the fetched `origin/main`; configured branch upstreams retain their existing check. For concurrent development, select a clean worktree named for the project through `PROJECTS_DIR`. Managed documentation must still be clean, and server drift/hash checks remain required. [Documentation synchronization](maintenance.md#文档同步) owns the command and source-selection contract.


<a id="备份与发布历史持续占用磁盘"></a>

## Backup and Release History Keeps Consuming Disk

First identify the host and actual activation phase. NAS has manual full external backups and temporary upgrade-only local protection; before cutover ALI still has legacy backup/retention tasks. The old daily count or five-upgrade limit does not authorize deleting historical or unresolved materials.

| Material | Contract |
| --- | --- |
| NAS routine recovery sets | One dual-host package staged/compressed/verified on NAS, then copied/read-back verified externally; successful task staging removed, no internal fallback or rotation |
| NAS `/var/lib/server-upgrades` and disposable candidate-check data | Identified upgrade protection; delete that job only after runtime and affected-data acceptance, retain failed/unverified protection; new capture follows the database-only policy in [Retention](retention.md#temporary-upgrade-backups) |
| ALI `daily-*`, old `before-deploy-*` and release history | Legacy schedules stop during cutover; preserve existing copies rather than applying NAS rules retroactively |
| Manual/migration/recovery archives, `/opt/backup-exports`, maintenance Mac `backups/` | No automatic deletion or overwriting; inspect private manifests before selecting a recovery point |
| Historical Portal encrypted/incremental sets | Retain required keys and complete parent chains; folder age alone does not establish safe deletion |
| Application data/history/trash/media | Application-owned behavior, not backup rotation; full NAS backups include stored state even if the application can later rebuild or expire it |
| System logs/temporary files | Ordinary host maintenance may continue, but must not target real backup directories or root-private upgrade protection |

An unavailable external volume must leave agent backup unavailable. If the final export appears on NAS internal storage, inspect `/etc/server-recovery.json`, mount/UUID and the NAS role marker rather than accepting a fallback. Deliberate task staging under root-private `/var/lib/server-backups` is allowed only for the single-package external workflow; it is not a completed backup. A directory existing at the configured mountpoint is not proof that a drive is mounted.

Unexpected local data protection usually means failed/interrupted acceptance or cleanup. Read the release/upgrade receipts and journals before deleting anything; health alone does not prove no lost data. [Retention](retention.md) owns temporary-success deletion and historical ALI preservation, while [NAS migration](nas-migration.md#manual-full-backups) owns external recovery sets.

Measure actual disk blocks and file counts by directory, not only logical file sizes. Historical media snapshots may share inodes with live files; separate `du` totals can double-count them and removing one link does not free the whole logical size. Old backups can retain media removed from production. Portal's registered cleanup previews are not an automatic scheduler and must not include unresolved upgrade protection or unregistered root/private archives.

Cloud backup retention is independent of application/source-directory cleanup. [ALI HBR](current-state.md#cloud-backup) records the live vendor-client state independently of disabled native backup units; migration and stopping a client do not delete historical cloud recovery points or prove a provider-side billing/schedule item was canceled. Real backup deletion or restoration still follows the shared authorization table.


## Native media processing exhausts a service task limit

On `nas`, Aura bulk imports exhausted its former `TasksMax=128` budget. The limit counts threads in the entire service cgroup, including Go, codecs, FFmpeg and private Python workers. Symptoms included `Resource temporarily unavailable`, failed `fork`/`pthread_create`, stuck decoder children and Go `fatal error: newosproc`, followed by systemd restarts. An `active` unit or a successful health request between restarts does not establish processing health.

Compare `systemctl show aura -p TasksCurrent -p TasksMax -p LimitNPROC -p NRestarts` with `/sys/fs/cgroup/system.slice/aura.service/pids.{current,max,events}` and `ps -e -o pid,ppid,nlwp,comm --sort=-nlwp`. A rising cgroup `max` event counter identifies task-budget rejections independently of free RAM. `VIPS_CONCURRENCY=2` does not cap all codec-owned threads; individual HEIC subprocesses reached 15–28 threads. Do not raise user-wide limits when the service cgroup is the actual constraint.

Aura's source unit now uses a 1024-task budget, with eight jobs, at most four ExifTool/libvips/CPU video operations and four GPU operations. Upload capture-date extraction shares the CPU bound. Native helper pools have explicit thread settings, and command/request deadlines cancel stalled children and release slots. Install the maintained project unit under the shared maintenance and application deployment locks, reload systemd, and restart only Aura. Validate HEIC/RAW and mixed-media queues under the real runtime identity/cgroup, including interruption recovery and cgroup task events, then retry failed resources through the application's bounded API. Preserve accepted originals. Curio uses eight jobs and four CPU/GPU operations each in its separate 1024-task unit. Both applications reserve one operation in each budget from background work for playback; these are application-level limits, not a host-global semaphore. Future applications using native codec pools should measure their complete process trees rather than copying Aura's task count.

RecipeBox on `nas` also exhausted its former `TasksMax=64` budget during photo uploads. On November 7, its resident Go process occupied 24 tasks, leaving only 40 for native helpers; `pids.events` recorded 14 task-limit rejections and `memory.events` recorded no OOM or memory-limit events. Two uploads at 20:41:36 and 20:43:06 (Asia/Shanghai) reached the local application and ended with `vips failed: signal: killed`, producing HTTP 422 and a client-aborted 499 respectively. Minute samples in that interval showed more than 95% CPU idle and about 59 GiB available memory, so the evidence does not support host exhaustion by Aura.

An isolated instance using the installed RecipeBox binary and a synthetic Apple-encoded 12-megapixel HEIC reproduced the failure when given the same remaining 40-task native budget: the decoder stalled at the cgroup limit, recorded four rejections and returned 422 at its 40-second deadline. With `TasksMax=256`, the same upload completed in about 1.2 seconds, peaked at 59 tasks and recorded no rejection or OOM. A fresh Go process starts with fewer threads than a resident service; a successful cold-start upload under 64 tasks does not rule out this failure after ordinary service use.

RecipeBox's maintained unit uses 256 tasks while retaining serialized uploads, 640 MiB memory and 100% CPU limits. Install its own source unit under the shared maintenance and RecipeBox deployment locks, reload systemd and restart only RecipeBox; no gateway, GPU-runtime or original-data change is needed. FabricWorld retains a 64-task unit and the same libvips/HEIC pipeline, so inspect its task budget if the symptom appears there; its task counter had no rejection during this investigation. Do not change other applications solely because they have the same configured number.


## FFmpeg recompiles CUDA kernels for every short job

On `nas`, FFmpeg's `scale_cuda` repeatedly JIT-compiles CUDA kernels when its runtime user cannot write the driver cache. Aura and Curio have root-owned, read-only service homes at `/opt/aura` and `/opt/curio`, so the default `~/.nv/ComputeCache` is unavailable. CUDA/NVENC can still succeed while this startup cost dominates short segment generation.

Check the runtime user's `HOME`, `CUDA_CACHE_PATH`, `CUDA_CACHE_DISABLE`, cache ownership and systemd write restrictions. Repeat one identical synthetic `lavfi` CUDA-scaling/NVENC command under that identity and sandbox, using the same private writable cache for both runs; compare elapsed time and cache-file growth. An isolated NAS one-frame check under `aura` took about 6.9 seconds cold and 0.4 seconds warm, with about 5.1 MiB of cached kernels. Administrator-run GPU success alone does not check the service's cache access.

Keep the sandbox and select a bounded, application-owned cache outside originals, installed models and recovery data. Both NAS units set `CUDA_CACHE_MAXSIZE=33554432`. Aura uses the private disk path `/opt/aura/bin/cuda-cache`, declared in its Portal resources and writable under its service sandbox, so compiled kernels survive releases and restarts; its HLS scratch remains disposable tmpfs at `/run/aura/playback`. The surrounding programs and image environment remain read-only, and the existing recovery exclusion for reconstructible `bin` files also excludes this cache. Curio retains `CUDA_CACHE_PATH=/run/curio/playback` with `RuntimeDirectory=curio`, which systemd removes on service stop. An exact two-second Aura CUDA/NVENC check took 7.03 seconds with an empty task-owned cache and 0.54 seconds on reuse, producing about 5.1 MiB of compiled cache. Empty or driver-invalidated disk caches still have a first-use compilation cost. Create the affected application's private directory before installing its maintained unit, reload systemd under the shared maintenance/deployment locks, and restart only that application through its guarded deployment. Verify cache ownership, sandbox access and warm reuse afterward.


## Unnecessary video transcoding and HDR tone mapping

Aura and Curio on `nas` prefer browser-playable originals and use bounded HLS windows for compatibility. A browser's codec hint is an admission estimate, not a decoder test: Mac Chrome rejected bare `hvc1`/`hev1` and `av01` hints while supporting complete codec strings and actual native playback. Try an eligible original when either its codec hint or container MIME is supported, then fall back on a media error or zero video width after `loadedmetadata`. The latter catches a supported audio track playing alone when the video decoder is unavailable. Preserve each application's timeline, saved-direction and alpha contracts; do not remove audio gates indiscriminately. Full-range 8-bit H.264 and QuickTime PCM16 (`pcm_s16le`) do not inherently require video conversion. A synthetic HEVC/P3/PCM16 MOV passed actual picture, autorotation and non-silent audio playback in Mac Chrome; other browser engines still require their own playback evidence.

WebCodecs exposes the client's available decoders; it does not add missing HEVC support or container demuxing. Fix unnecessary fallback before introducing a software decoder or restoring persistent whole-video transcoding. Cold compatibility windows still wait for a complete requested segment, and the first CUDA operation after service restart can also pay the separate [kernel-cache startup cost](#ffmpeg-recompiles-cuda-kernels-for-every-short-job). The separate [native layout repair](#native-mp4-initialization-scans-inefficient-layouts) preserves encoded samples rather than adding another transcoding path.

Distinguish the movie origin from the first video-track timestamp. A synthetic H.264/AAC MP4 with audio/movie start zero and video start 66.7 ms retained Chrome's zero-based movie clock and correct seek/frame timestamps. Curio admits a movie origin within 1 ms of zero and a video-track lead between -1 ms and 250 ms, using movie-relative duration, audio checks, cover times and HLS seeks. It retains compatibility for larger leads or nonzero movie origins; a common positive-origin synthetic file exposed a nonzero native clock. Aura retains its existing near-zero video-start admission. The Curio contract does not establish equivalent timestamp behavior in every browser or authorize relaxing Aura's contract without its own affected-path validation.

Independent HLS windows also need a consistent client time origin. Seeking the first input to its video keyframe can omit earlier audio, while AAC encoder priming can move the earliest packet before the nominal window start. HLS clients then rebase differently depending on the first loaded window. Curio retains first-window audio and uses FFmpeg's `noise` bitstream filter to discard negative-PTS AAC priming packets before applying its transport bias. It preserves video timestamp phase with a 90 kHz encoder time base: a non-grid synthetic source had 59 frames before a two-second boundary; default CPU/NVENC timing retained only 58, while 90 kHz timing retained all 59 on `nas`. Encoding-recipe URL versions separate old browser caches. Cold boundary seeks still have the first-frame availability limit of an independent window; these fixes do not introduce cross-window preroll or change Aura's pipeline.

FFmpeg 8 `zscale` removes color-dependent side data when converting HDR transfer to linear. A following automatic `tonemap` therefore loses MaxCLL, mastering luminance and the original transfer default. Capture the source peak before linearization and pass it explicitly: MaxCLL, valid mastering maximum, then FFmpeg's source defaults of PQ 10,000 nits or HLG 1,000 nits, divided by the pipeline's 100-nit reference white. The applications cache a bounded first-decoded-frame probe with each HDR specification; an unavailable optional peak probe retains the transfer default. Preserve rotation only from entries that actually contain it, because other side-data entries have no display matrix.

For HDR resizing, use separate transfer and dimension operations: linearize, select float RGB, resize in linear light, tone-map with the retained peak, and convert to limited-range BT.709. Combining resize and transfer in one `zscale` can resize before linearization. Reducing the float frame before tone mapping avoids applying the nonlinear mapper and final color conversion to pixels that will be discarded. Generic Mobius SDR output does not apply Dolby Vision's dynamic RPU; native HDR playback remains the preferred representation on supporting clients.

Diagnose reported brightness changes with properly tagged full/limited-range and color-managed synthetic sources under each affected runtime identity. Do not add a gain reduction or alter the tone curve without evidence. The exact NAS CUDA/NVENC and software-decoded NVENC SDR paths retained full/limited range and P3/BT.709 tags in the focused color-ramp check, with at most one RGB code-value difference. Mac Chrome's native-original and native-HLS SDR patch colors also matched. These SDR checks do not establish Dolby Vision rendering equivalence. Relevant implementation references are [FFmpeg zscale side-data removal](https://github.com/FFmpeg/FFmpeg/blob/n8.0/libavfilter/vf_zscale.c#L887), [source peak selection](https://github.com/FFmpeg/FFmpeg/blob/n8.0/libavfilter/colorspace.c#L153), and [zimg resize/conversion ordering](https://github.com/sekrit-twc/zimg/blob/release-3.0.6/src/zimg/graph/graphbuilder.cpp#L877).


## Native MP4 initialization scans inefficient layouts

On `nas`, an H.264/AAC original can satisfy native codec and timestamp admission yet remain expensive to initialize. Curio's affected MP4s had valid front-loaded movie indexes, zero-based clocks, hundreds of separate `mdat` boxes and audio/video chunks spanning several seconds. A single-video Chrome comparison without application preview code still made many mostly forward Range requests before `loadedmetadata`. That establishes original initialization as the bottleneck; it does not identify the exact browser parser branch or imply playback-time packet-by-packet backtracking. Check box layout and packet positions before blaming GPU load, missing fast-start or a long GOP. A Range proxy or a moved `moov` does not repair coarse interleaving.

Curio uses one lossless normalizer for a conservative subset of inefficient MP4s, including supported files with movie metadata at the tail. FFmpeg stream-copy reorganizes encoded samples; Curio retains original movie metadata, sample timing, edit lists and display information, changing only chunk mapping and offsets. Bare stream-copy can rewrite AAC declared duration, edit-list rounding and creation-time epochs even when packet payloads and demuxed clocks match. Compare encoded sample identity and logical metadata before publication, then verify browser initialization against the same source. New uploads normalize before processing readiness; explicitly selected existing videos can use the same module. Under Curio's user-authorized policy, verified output becomes a canonical object under its actual SHA-256, while stable asset IDs and source fingerprints remain in the catalog. A durable mapping commits before obsolete source deletion; downloads then return normalized bytes, not the discarded container. Legacy playback discovery can still create a separate derivative without deleting its source. One bounded CPU/I/O repair runs at a time, and ordinary layouts are not copied. Curio's project operations own eligibility, recovery and rollback compatibility. Aura preserves its own original/HLS contract and has no automatic layout normalization; do not extend Curio's deletion authorization to Aura.

Curio also observes explicit native play and paused-frame startup for five foreground seconds before compatibility fallback, distinct from its existing buffered-playback clock check. Failure memory uses the native URL rather than the asset hash, so a repaired revision is tried afresh. Background time, explicit suspension, rejected gestures and sources without a fidelity-preserving fallback do not turn initial waiting into an automatic opaque conversion.


## Seek-heavy video previews and canceled candidate generation

On `nas`, compare original Range request counts/bytes, cold atlas generation and cached-atlas reuse before blaming codec complexity or host capacity. Ordinary H.264 can transfer an original repeatedly when independent playback/preview decoders seek open-ended byte ranges. A long GOP adds decode work, but short files can also wait when preview jobs are repeatedly canceled. Access-log timestamps without request durations measure observed completion intervals, not server execution time.

Curio shares one serial leased browser decoder between timeline refinement and provisional cover thumbnails, while leaving the main player independent. Cached atlas pixels appear immediately; native hover refinement waits for a stable target. Client atlas fetches tolerate a two-second gap between consumers, with at most two orphan fetches, and server atlas jobs tolerate three seconds. Backgrounding/invalidation abort client work; permanent deletion and shutdown cancel server jobs immediately. Aura retains its own preview implementation and must be investigated separately if the symptom appears there.

Long Curio SDR GPU atlas generation groups up to three seek-local inputs in one FFmpeg process with one CUDA device and an aggregate source-pixel bound of one 4K frame. It avoids repeated process/device startup without decoding intervening long-video footage; CPU/HDR and short-video paths remain unchanged. Read-only NAS comparisons of two 15-frame workloads reduced roughly 7.1-8.5 seconds to 3.5-3.6 seconds while retaining emitted original-frame timestamps. These extraction measurements exclude queueing, PNG-atlas assembly and network transfer. Cold-atlas success logs record hash, elapsedMs, candidates, actual engine and decodePasses. Keep source media, existing atlas recipes and bounded processing slots; no new runtime, shared configuration or Aura restart is required.

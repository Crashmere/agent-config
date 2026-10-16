# Queries, Planning, and Downloads

Navigation: [Prepare the directory](#1-prepare-the-task-directory) · [Query](#2-find-users-and-complete-track-lists) · [Set difference](#3-analyze-overlap-and-build-the-set-difference) · [Download and substitute](#4-download-and-controlled-substitution) · [Resume and deliver](#5-resuming-output-and-delivery)

## 1. Prepare the task directory

Use existing Node.js 20+, curl, ffmpeg, and ffprobe. Examples use a POSIX shell; invoke scripts with `node`, without installing the upstream repository or starting a web service.

```bash
mscd_skill="$HOME/agent-config/skills/mscd-music-download"
mscd_work="$(mktemp -d "${TMPDIR:-/tmp}/mscd-task.XXXXXX")"
command -v node curl ffmpeg ffprobe
node "$mscd_skill/scripts/library.mjs" --help
node "$mscd_skill/scripts/download.mjs" --help
```

Choose the music output directory for this task, preferring the location explicitly specified by the user. The work directory stores query snapshots, plans, and substitution rules; `.mscd` inside the final output stores the state needed to resume. Retain snapshots and reports the user needs at completion, without committing them to the skill repository.

## 2. Find users and complete track lists

Fill the variables below with values verified for this task; do not write personal accounts into the skill:

```bash
node "$mscd_skill/scripts/library.mjs" search-users "$mscd_nickname" --out "$mscd_work/users.json"
node "$mscd_skill/scripts/library.mjs" user-playlists "$mscd_uid" --out "$mscd_work/playlists.json"
node "$mscd_skill/scripts/library.mjs" playlist "$mscd_playlist_id" --out "$mscd_work/target.json"
node "$mscd_skill/scripts/library.mjs" playlist "$mscd_liked_id" --out "$mscd_work/liked.json"
```

Select the matching numeric UID from `users.json`; do not use a nickname as a UID. `createdByUser` distinguishes created and saved playlists. Liked-playlist names vary by user; do not choose one based on a fixed name or historical count. When the user specifies playlists named with a few characters, retrieve their IDs individually and save snapshots.

`playlist` fills in `/song/detail` in `trackIds` order and preserves `declaredCount`, `returnedIds`, `unresolvedIds`, and `countGap`. It does not automatically use every cross-check API; when gaps appear, read the API troubleshooting reference and investigate. `--out` in all query commands refuses to overwrite existing files; use a new filename to refresh.

## 3. Analyze overlap and build the set difference

```bash
node "$mscd_skill/scripts/library.mjs" overlap \
  --snapshot "$mscd_work/target-a.json" --snapshot "$mscd_work/target-b.json" \
  --snapshot "$mscd_work/liked.json" --out "$mscd_work/overlap.json"
node "$mscd_skill/scripts/library.mjs" plan \
  --snapshot "$mscd_work/target-a.json" --snapshot "$mscd_work/target-b.json" \
  --exclude "$mscd_work/liked.json" --out "$mscd_work/plan.json"
```

- Repeat `--snapshot` to add targets and `--exclude` to add excluded playlists. A single-playlist download needs only one `--snapshot`; omit `--exclude` when no exclusions are needed.
- The matrix in `overlap.json` follows the order of `playlists`, with each cell an array of shared song IDs; `unique` counts unique IDs, and `records` is the total number of records across lists.
- The plan's `items` merges target playlists by ID, `memberships` preserves every original position, and `skipped` records exclusion reasons.
- `versionCandidates` compares only target and excluded playlists: matching titles and artists, duration differences of at most 20 ms, and different IDs. Download these by default; use `--dedupe-versions` only when the user explicitly accepts deduplication based on this metadata match. It does not prove identical recordings or merge releases with different IDs within target playlists.
- `--exclude` excludes by playlist membership and does not scan local disks. If the user wants exclusions based on actual local files, verify manifests and files first; add only genuinely valid original/substitute IDs to the working plan and retain traceable exclusion records.
- Incomplete snapshots block plan generation by default. If IDs remain missing after investigation, use `--allow-partial` to download the resolved portion; this flag does not eliminate gaps, which must appear in the final report. Known IDs in exclusion snapshots are excluded even without details, but IDs omitted by the API cannot be inferred.

## 4. Download and controlled substitution

```bash
node "$mscd_skill/scripts/download.mjs" \
  --plan "$mscd_work/plan.json" --out "$mscd_output" --jobs 3
```

Add `--allow-mp3` when the user permits lossy fallback. The script first tries Meting lossless, then NetEase-compatible lossless/legacy URLs and Meting 320; the first valid FLAC takes priority. Without FLAC, compare actual MP3 bitrates, which may be only 192 or 128 kbps and must not be reported as 320. This workflow does not search every platform or guarantee the highest sample rate among multiple FLACs.

When failed entries need another release, search first, then retrieve normalized candidate details:

```bash
node "$mscd_skill/scripts/library.mjs" search-songs "$mscd_search_text" --out "$mscd_work/candidates.json"
node "$mscd_skill/scripts/library.mjs" song "$mscd_candidate_id" --out "$mscd_work/candidate.json"
```

In this task's `replacements.json`, use the original ID as the key, put the complete candidate object in `song`, and describe verified differences and the substitution reason in `note`:

```json
{
  "10001": {
    "song": {
      "id": "10002", "title": "示例歌曲",
      "artists": [{"id": "20001", "name": "示例歌手"}],
      "album": {"id": "30002", "name": "示例专辑", "cover": "https://example.com/cover.jpg"},
      "durationMs": 180000, "track": 1, "disc": "1", "publishTime": 0
    },
    "note": "原单曲不可用；已核对艺人、时长及版本信息，使用获准的专辑发行。"
  }
}
```

Example IDs/URLs illustrate the format only and cannot be downloaded directly. Use `--replacements "$mscd_work/replacements.json"` and supply it again for subsequent resumes and audits. The script requires matching artists, a duration difference of at most 2 seconds, and a note; different titles also require `acceptTitleDifference: true`. Set that boolean only after actual verification and any necessary authorization. The script cannot replace listening or release judgment. A substitute source conflicting with another song or excluded ID in this plan is rejected in advance; adjust the plan or exclusion policy before proceeding, without duplicate downloads.

## 5. Resuming, output, and delivery

Repeat the original command to resume. Audit with the same plan, quality, and substitution arguments, plus `--audit`; auditing fetches no audio, lyrics, or cover art, but updates verification records and reports. After moving the entire output directory, only `--out` needs to change; relative paths and M3U references remain usable.

| File | Purpose |
| --- | --- |
| `<playlist-name> [ID]/<position> - <song> [original-ID].flac/mp3` | Verified audio; shared tracks go in the first target playlist's directory |
| Each playlist's `playlist.m3u8` | Current supplemental download results, referencing shared files in original order; excluded songs do not appear in this M3U |
| `manifest.json`, `results.csv` | Success/failure, actual quality, lyrics, cover art, source IDs, substitution notes, and relative paths |
| `.mscd/plan.json` | Fixed original download plan; use a new output directory for a different task |
| `.mscd/records/<original-ID>.json` | Per-song progress, hashes, and verification results |
| `.mscd/summary.json`, `running.lock` | Summary and process lock; the lock is removed on normal completion |

Exit code `0` means the entire plan succeeded with no unavailable lyrics or snapshot gaps; `2` means song failures, unavailable lyrics, or snapshot gaps require reading the report and handling each category; `1` means argument, lock, or other global errors. Instrumental tracks do not count as unavailable lyrics.

Resuming existing successful files checks tags, lyric hashes, duration, file size, and audio packet hashes; `--audit` also performs full decoding. Ordinary resuming does not fetch lyrics again for successful audio whose lyrics were temporarily unavailable; follow the troubleshooting instructions to add them, rather than expecting endless reruns to recover automatically. Preserve corrupted files and mark failure instead of silently overwriting them.

Finally, provide links to the output directory and manifest, and distinguish completion of the resolvable plan from completeness against the playlist's original total. Report the actual MP3 bitrate distribution, lyrics/instrumental/missing status, substitute releases, and unresolved errors; do not commit personal accounts, music, or runtime state to the repository.

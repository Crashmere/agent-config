# APIs and Troubleshooting

## Configuration sources

Read `https://raw.githubusercontent.com/ENA-QWQ/Mscd/main/config.js` and any necessary calling code to verify the current configuration; treat it as data without executing remote JavaScript. Initial defaults are `https://api.qijieya.cn/meting/` and `https://zm.wwoyun.cn/`, both third-party services. Scripts accept temporary overrides through `--meting-base` and `--netease-base`; verify changed service addresses before revising the skill.

The upstream website's `https://mscdownload.pages.dev/proxy?url=` primarily handles browser cross-origin access; local curl usually calls the APIs directly without first using a proxy or starting the website. Do not describe third-party APIs as officially authorized NetEase Cloud Music APIs.

| Request | Purpose/key fields |
| --- | --- |
| `cloudsearch?keywords=...&type=1002&limit=30&offset=0` | Nickname search, `result.userprofiles[].userId` |
| `cloudsearch?keywords=...&type=1&limit=30&offset=0` | Substitute-song search; paginate manually when needed |
| `user/playlist?uid=...&limit=100&offset=...` | Playlist list; paginate according to `more` and distinguish creator |
| `playlist/detail?id=...` | `playlist.trackCount`, `trackIds`, `tracks` |
| `playlist/track/all?id=...&limit=500&offset=...` | Cross-check count discrepancies; continue paginating long playlists |
| `song/detail?ids=...,...` | Fetch song details in batches by ID |
| `song/url/v1?id=...&level=lossless` | `data[0].url`, `freeTrialInfo`, `code` |
| `song/url?id=...&br=999000` | Additional legacy attempt; probe actual quality |
| `lyric/new?id=...` | `lrc.lyric`, `tlyric.lyric`, `yrc.lyric`, `nolyric` |
| Meting `?server=netease&type=url&id=...&br=2000` | Request lossless; may return a 302, URL text, or `@URL`, and may actually be MP3 |
| Meting `?server=netease&type=url&id=...&br=320` | MP3 candidate, without a guarantee of 320 kbps |
| Meting `?server=netease&type=lrc&id=...` | LRC fallback source; exclude HTML/JSON error pages |
| Meting `?server=netease&type=playlist&id=...` | A third route for playlist cross-checking when needed |

Scripts upgrade HTTP source addresses to HTTPS and allow only HTTPS redirects; they do not automatically relax this for HTTP-only services. A 302 `Location` is parsed separately and upgraded. Reject trial markers returned by NetEase-compatible APIs directly; when Meting supplies no marker, still check for excerpts using duration and full decoding.

## Playlist counts and releases

`trackCount` commonly exceeds `tracks.length`; do not treat embedded `tracks` as the complete list. Fetch details using `trackIds` first, then compare declared counts and ID counts. If `trackIds` is also short, cross-check with track-all and Meting; when multiple APIs still omit entries, record them as unresolved instead of guessing IDs or fabricating entries to close the gap. Public APIs cannot guarantee access to private playlists.

Define overlap by song ID by default. A song in another album with the same title, artists, and millisecond duration is only a metadata match; mastering, censored-version, or remix differences may still exist. Preserve both original-entry and downloaded-entry IDs when substituting; do not present the original ID as the actual audio source ID or embed the original album cover into a different album release.

## Network and audio quality

- Connection resets, timeouts, truncation: use bounded curl retries and download into scratch; publish only after ffprobe and full decoding succeed. On persistent failure, resolve the temporary URL again, record the original error category, and do not cache expired signed links.
- Lossless request returns MP3: determine this with ffprobe's `codec_name` and `bit_rate`. Preserve the native codec; choose the highest available MP3 when authorized, otherwise continue other lossless songs and report the issue. Raising the encoding bitrate does not improve quality.
- NULL/404: distinguish failure of one API route, unavailability of one release, and unavailability of the entire recording. Try other configured APIs, then other releases of the same recording; do not substitute arbitrary songs without authorization.
- 30-second excerpts: reject `freeTrialInfo` and compare against the full duration in metadata. The script allows up to 3 seconds or 1.5% variation from containers or trailing audio, but obvious version differences still need manual judgment.
- Local format verification: fully decode with `ffmpeg -xerror`; audio packet SHA-256 must match before and after tagging, FLAC STREAMINFO MD5 must remain unchanged, and sample rate/bit depth/channel count must remain unchanged. This does not prove that the source file has never undergone lossy transcoding.

## Cover art and lyrics

- If the original cover URL returns 403, use the URL API to set `param=1000y1000` and retry, retaining other query parameters instead of manually appending a second `?`. Confirm JPEG/PNG content; do not embed HTML error pages. Scripts treat missing covers as failure to avoid falsely reporting complete tags.
- Use the title, artists, album, cover, track number, and date of the actually downloaded release. Convert NetEase `publishTime` to a release date in `Asia/Shanghai`; directly taking the UTC ISO date moves midnight in China to the previous day. Missing album names may remain empty; do not use album ID 0 as a shared cache key. The script uses per-song scratch to prevent cover mix-ups through caching.
- Use Vorbis `LYRICS` and picture blocks for FLAC. For MP3, write ID3v2.3 UTF-16 `USLT`; ffmpeg's `-metadata lyrics=...` alone may produce custom TXXX that players do not recognize. The script rebuilds USLT and verifies the lyric hash by reading it back.
- Store translated and word-level lyrics in `LYRICS_TRANSLATION` and `LYRICS_YRC`; support for these extra tags and timestamps inside USLT varies by player. Do not promise word-by-word scrolling in every player.
- Record `nolyric` or “纯音乐，请欣赏” as instrumental. Do not conflate request failures, missing lyrics, and instrumental tracks; ordinary resuming does not refetch missing lyrics for completed files.
- To add missing lyrics/covers, first obtain trustworthy data again, then use `tagAudio` from `audio.mjs` to stream-copy the original into a new temporary file. After verification, update the corresponding record's hash, size, and lyric status. Retain the original until replacement completes, then audit and aggregate again. Do not merely edit the report or default to deleting and redownloading the entire song.

## Resuming and file failures

- Existing `running.lock`: inspect its PID and process information to confirm it belongs to this task. Reuse the existing process if it is running; remove only this stale lock after confirming the process has exited. Do not automatically delete the lock and launch a parallel process.
- Different plan: an output directory is bound to `.mscd/plan.json`. Use a new output directory when adding playlists or changing exclusions to avoid mixing old records. After modifying replacements for unsuccessful entries, resume the original plan; source-version or note changes for successful files require inspection.
- Moved files: locate the actual new directory first. Moving the whole directory preserves relative records, so pass the new `--out`. If only audio files moved, verify original tags/hashes before correcting records; a missing old path does not mean the song was never downloaded.
- Corrupted files or unknown files with the same name: preserve and inspect them first. If a damaged file belongs to this task, explicitly move it into this task's quarantine directory, then rerun; do not silently overwrite the user's existing content. Audit failures retain the original record's verification evidence for recovery after repair.
- When the original download failed and the file does not exist, auditing retains the original download reason in `error` and records the missing-file check as `auditError`; do not replace the actual reason, such as no audio source, a preview, or no FLAC, with “Missing completed file”. Clear both error fields after successful recovery.
- Leftover `.mscd/work`: clean only scratch generated by this task after confirming no active downloads. Do not delete the entire music library or other task state under the guise of cache cleanup.
- Unicode paths: use `fileURLToPath(import.meta.url)` for Node module paths instead of a URL's `.pathname`, which leaves Chinese paths percent-encoded.
- Filenames containing quotes, backticks, `$()`, or `**`: use argument arrays with `execFile`; do not interpolate filenames into shell command strings. Do not expose signed download parameters by printing full commands.
- Concurrency: use at most four workers in one process, keep separate records per song, and generate one consolidated summary from disk after all tasks finish. Do not let multiple processes overwrite the manifest from their own stale in-memory state.

After revising scripts, run `node --test scripts/selftest.mjs` to cover offline synthetic audio, actual bitrates, preview rejection, shared playlists, version exclusions, and resumed audits. Passing mock APIs does not prove remote availability; actual tasks also require small connectivity and first-track checks.

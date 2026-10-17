---
name: mscd-music-download
description: "Use ENA-QWQ/Mscd APIs to analyze and download NetEase Cloud Music playlists with exclusions, metadata, lyrics, cover art, and verification."
---

# MSCD Music Download

Treat [ENA-QWQ/Mscd](https://github.com/ENA-QWQ/Mscd) as the source of API configuration and request patterns. It is a web frontend; this skill's Node.js scripts are personally maintained helpers and must not be described as an upstream CLI. Third-party services may change, so do not promise that every song, lossless source, or complete playlist will be available.

## Workflow

1. Recover the scope, destination, deduplication criteria, audio quality, and release-substitution preferences from the current conversation. Do not ask again about already authorized MP3 fallback or specific substitutions; do not generalize authorization for one past song to remixes, live versions, or other releases. Prefer native FLAC for the original entry by default; if a downgrade is not authorized, retain MP3 candidates and ask while continuing with the remaining songs.
2. Read [references/workflow.md](references/workflow.md) and proceed through queries, snapshots, planning, downloading, and auditing in that order. Keep all outputs and runtime state in the current task directory, and music at the user's specified destination; do not write them into this skill or `agent-config`.
3. Check free space at the output destination and the existing `node`, `curl`, `ffmpeg`, and `ffprobe`. Scripts use only built-in Node modules; do not install npm or Python dependencies. Use `software-installation` for missing tools; use `python-environment` only if third-party Python is separately needed.
4. Resolve nicknames to numeric UIDs, verify identity, and distinguish playlists the user created from those they saved. Paginate lists. Use `trackIds` as the track index, fetch missing song details, and record declared counts, returned ID counts, and missing details; cross-check discrepancies using [references/api-and-troubleshooting.md](references/api-and-troubleshooting.md).
5. Generate a download plan first. Deduplicate by NetEase song ID by default, downloading an ID shared across target playlists only once. For exclusions based on songs already in the liked playlist, use that playlist's snapshot; for exclusions based on local downloads, verify actual files and manifests instead of relying on filenames or old paths. Different IDs with matching titles, artists, and durations are only release candidates; verify them before deciding on exclusion or substitution.
6. Download with low concurrency into a temporary directory, identify actual codecs and durations, embed tags, and fully decode before publishing files. A `br=2000` request, file extension, or API label does not prove lossless audio; never convert MP3 to FLAC and present it as lossless. When MP3 is allowed, choose the highest actual bitrate among candidates available in this attempt.
7. Run a full audit after completion, read the final manifest, and report successes/failures, FLAC/MP3 counts, actual MP3 bitrates, lyrics/instrumental/unavailable status, cover art, and release substitutions. Retain playlist gaps and failure reasons; success for every planned song must not hide songs omitted by the API.

## Required behavior

- Preserve the original playlist ID, actual download ID, title, artists, album, duration, and substitution notes; substituted songs retain the original entry's playlist position. Even when the user approves an album version, verify artists, duration, and release differences.
- Reject previews; check `freeTrialInfo`, actual duration, and full decoding. FLAC checks can establish only the local encoding and that tagging did not damage the audio, not the provenance of the source master.
- Write lyrics and cover art into music files. Use `LYRICS` and picture blocks for FLAC, and standard ID3 `USLT` and cover frames for MP3. A custom `TXXX:lyrics` alone is insufficient to establish correct MP3 lyrics. Translated and word-level lyrics may be saved additionally, with support varying by player.
- Classify “纯音乐，请欣赏” separately; it is not actual lyrics. Explicitly report songs that truly lack lyrics without inventing lyrics or claiming all lyrics are complete.
- Discard temporary links after use. Use HTTPS, encoded parameters, controlled retries, and argument arrays; do not save signed download URLs, Cookies, or tokens in logs or manifests. Scripts require no account login and accept no credential parameters; separately explain content unavailable through public APIs.
- Save progress per song and use one process to aggregate the manifest; do not run multiple download processes for the same output directory. Skip existing files only after verifying metadata, duration, size, and audio hashes.
- Do not overwrite unknown files with the same name or silently change already successful versions. For corruption, stale locks, or relocated files, establish the actual state first, then recover according to the troubleshooting reference.

## Resources

- [references/workflow.md](references/workflow.md): commands, deduplication boundaries, substitution rules, output structure, resuming, and auditing.
- [references/api-and-troubleshooting.md](references/api-and-troubleshooting.md): upstream configuration, API routes, count discrepancies, cover-art 403 errors, quality fallback, tagging, and recovery details.
- `scripts/library.mjs`: user/song search, playlist retrieval, overlap analysis, and download planning; read `--help` first.
- `scripts/download.mjs`: downloading, tagging, resuming, aggregation, and `--audit`; read `--help` first.
- `scripts/common.mjs`, `scripts/audio.mjs`: reusable network, path, metadata, and audio-verification functions for the scripts.
- `scripts/selftest.mjs`: after script changes, run `node --test scripts/selftest.mjs` to verify with synthetic audio and mock APIs, without connecting to external services.

When real use exposes a skill or script error, complete the current task first, then use `personal-skill-management` to correct the source files, perform focused validation, and synchronize the repository.

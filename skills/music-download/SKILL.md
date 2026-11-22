---
name: music-download
description: "Download music, lyrics or album covers via NetEase, Apple Music and LRCLIB, including authorized Apple Music playback capture."
---

# Music Download

Acquire music and its supporting materials through one task-specific workflow.
Reuse the NetEase download path and the Apple Music recording/packaging path;
neither is an automatic fallback for the other.

## Choose the requested output

| Request | Read and run |
| --- | --- |
| A NetEase song, playlists, exclusions, lossless download or resume | [NetEase download](references/netease.md); `scripts/netease/library.mjs` and `download.mjs` |
| Only lyrics, TXT/LRC, translations or word timing | [Lyrics](references/lyrics.md); `scripts/lyrics.mjs` or `scripts/apple/fetch_metadata.py` |
| Only an album/single cover | [Covers](references/covers.md); `scripts/covers.mjs` |
| New authorized Apple Music playback recording on macOS | [Recording](references/recording.md), then [Packaging](references/packaging.md) |
| Albums/new Apple downloads, resume, or per-song Lilt upload | [Apple batch workflow](references/apple-batch.md), then Recording/Packaging as needed |
| An existing WAV/ALAC/FLAC recording | [Packaging](references/packaging.md); do not record again |
| Add lyrics/artwork to an existing FLAC/MP3 | [Material enrichment](references/enrichment.md); `scripts/retag.mjs` |

Lyrics-only work uses Node and curl, or the existing Gamdl environment for
Apple lyrics. It does not fetch audio or artwork, control Music, or require
FFmpeg/BlackHole. Cover-only work uses catalog/image requests and FFprobe/FFmpeg,
not lyric, audio, donor or playback requests. Install missing tools only through
`software-installation`; select Python environments through `python-environment`.
Never install packages into global Python or modify a healthy Gamdl environment
for tagging/alignment dependencies.

## Matching and source selection

- Recover scope, destination, quality, requested language/format, cover size and
  accepted substitutions from the conversation. Respect explicit sources.
- Match title, main/featured artists, release, duration and ISRC where available.
  Resolve Clean/Explicit, Remix, Live, acoustic, remaster and regional differences
  before combining sources. Similar metadata establishes a candidate, not audio
  identity. Keep provider IDs namespaced; do not equate NetEase and Apple IDs.
- For an explicit platform link, begin with that platform. For unqualified TXT/LRC
  requests, LRCLIB is a useful no-login first source. Prefer accessible Apple
  official TTML when official text, translations or word timing are requested.
  Skip unavailable credentials instead of initiating login for a public lyric task.
- NetEase download companions can use matching LRCLIB lyrics when their platform
  sources are unavailable. Report the community source; `--no-lrclib` disables it.
  Multiple eligible releases remain candidates until reviewed. Authentication
  failures stop that provider attempt; public fallbacks do not retry credentials
  or imply permission to record or download audio.
- Keep audio, catalog metadata, lyrics and cover provenance separate. Do not
  relabel a community lyric as official or use another release's cover on the
  downloaded release. Preserve `ARTIST` versus `ALBUMARTIST`, dates, label and
  source IDs. Do not invent composer/songwriter credits or reinterpret one as
  the other. Service-side library maintenance belongs to `server-operations`.

## Output and verification

- **Cover default:** target a 1600-pixel long edge, normally 1600 x 1600 for a
  square. Preserve aspect ratio, never crop/stretch/upscale, and keep a smaller
  source at its actual resolution. Support a requested size or `max`. The same
  default applies to standalone and embedded artwork. Report actual dimensions
  and format; requested server dimensions do not establish original image detail.
- Preserve raw TTML/YRC/Lyricsfile and available plain/line/word variants. Keep
  original and translated text separately. Use complete official translation
  replacements when available; do not generate or relabel a translation as
  official. Distinguish unavailable text, request failure and instrumental songs;
  empty responses and Meting placeholders are not lyrics.
- Preserve source timestamps unless alignment is measured or an explicit offset
  is supplied. For a recording, measure alignment per song; a previously used
  offset is not reusable. Report source timing as unmeasured when there is no
  matching local audio. LRC timing does not establish every player's word support.
- Prefer native FLAC on NetEase; ask before unapproved MP3 fallback or release
  substitution. Check actual codec, duration, trial markers and full decoding.
  Never convert MP3 to FLAC and call it lossless. Playback capture preserves its
  recording PCM after packaging, not the original stream/master or bit-perfect
  playback. Preserve recording rate, channels and integer bit depth; floating PCM
  quantization requires separate approval.
- Embed FLAC `LYRICS` and native pictures; use MP3 ID3 `USLT` and cover frames.
  Verify metadata, artwork and unchanged audio packets/PCM as appropriate.
  Standalone files get a source/status sidecar. Do not claim text accuracy from
  a successful HTTP request or timeline parsing alone.
- Keep task state, music, pictures and credentials outside this repository.
  Use private staging, HTTPS, encoded arguments and bounded retries. Do not log
  cookies, tokens or signed media URLs. Publish without overwriting unknown files.
  Retain originals when enriching/packaging. Apple recordings require verified
  device/player restoration and explicit approval of intermediate cleanup.

## Existing downloads and checks

NetEase schema-1 plans, `.mscd` journals and relative paths remain supported.
Use the migrated `scripts/netease/` commands to resume; do not move user libraries
or regenerate old plans simply because the skill name changed. Preserve original
playlist positions, downloaded IDs, substitutions, gaps and failure reasons.
Successful audio with missing lyrics needs explicit enrichment rather than a
redownload; see [enrichment](references/enrichment.md).

Read helper `--help` before use. After code changes, run
`node --test scripts/netease/selftest.mjs scripts/selftest.mjs`; for Apple changes
also use the focused checks in [Apple batch workflow](references/apple-batch.md).
These use synthetic fixtures, not live playback. The native helper still needs a short sample and restoration
check before its first actual recording. Use `personal-skill-management` for
real-use corrections and repository/client synchronization.

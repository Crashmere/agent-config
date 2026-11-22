# Apple Batch Capture and Delivery

Use this workflow for albums, newly downloaded Music songs, resumable captures,
and per-song Lilt delivery. Playback capture is real-time: optimize preparation,
recovery and transfer rather than speeding up playback or implying original-ALAC
extraction. This reference adds orchestration to the existing recording,
packaging and server-operations workflows; it does not replace their safeguards.

## Plan once, prepare once

Read local Music library entries with one JXA/AppleScript call, recording each
persistent ID, title, artist, album, disc/track number, duration and file location.
Only the official app determines downloaded/playable status; encrypted `.movpkg`
contents are not an audio-conversion input. Inspect the requested destination
once and resolve already-present tracks by catalog IDs/ISRC and release/version,
with artist, title, duration and album as supporting evidence. Title-only matching
can confuse guest performances, live versions and re-recordings. Save this
inventory and a namespaced ID plan in private task staging.

Before routing audio, obtain materials for the selected missing songs:

```sh
"$GAMDL_PYTHON" "$SKILL/scripts/apple/fetch_metadata.py" \
  --song-ids "$SONG_ID_1" "$SONG_ID_2" --cookies "$COOKIES" \
  --storefront cn --language zh-CN --output-dir "$WORK/materials"
```

Use the actual storefront/language. The batch command processes IDs in one API
session, caches albums within that session, and creates `materials/<song-id>/`.
Single-song and metadata-only album commands remain supported. A lyric
authorization failure retains fetched materials and stops the remaining batch;
do not record before inspecting the returned issues. Missing lyrics and request
failure remain distinct. On resume, select only IDs without validated bundles,
and use a new output root; never infer completeness from directory existence.

Reuse one verified cover per storefront/catalog album ID, size and format.
Preserve its provenance sidecar and actual dimensions. Fetch it through
`covers.mjs --catalog`, not another audio download. Retain complete cached
bundles; avoid logging or rereading entire nested catalog responses just to
inspect title, IDs, lyric timing or status. Reuse installed tools, suitable Python
environments and an inspected native helper rather than reinstalling or compiling
for each track. Repeat a short capture only when the audio route, rate, helper or
relevant processing settings change.

## Record, package, upload

Use [Recording](recording.md) for device/player snapshots, processing controls,
single-track queue isolation, readiness and recovery. Persist playlist ownership
and expected contents before reuse; leave user-added entries untouched. Preserve
the original streaming track's catalog URL/identity when it is not a library
entry, so restoration can reopen that exact release at volume zero. Poll for
the saved track and advancing position before seeking and pausing it.

Persist separate per-song phases with atomic JSON replacement:

| Phase | Evidence required before advancing |
| --- | --- |
| `prepared` | Unique library/catalog match; validated materials and issues |
| `captured` | Expected player observations, closed WAV, full duration/decode/signal checks |
| `packaged` | No-overwrite FLAC publication; format, tags, artwork, timing and PCM equality |
| `uploaded` | Active remote track and verified original audio/metadata receipt |

Use `PlaybackMonitor` from `scripts/apple/playback.mjs` inside the managed
controller. Read all monitored Music fields in one call per observation, rather
than starting separate processes for every property. Its normal-EOF handling
retains the last verified expected-song position when Music clears currentTrack.
For a failed controller with a complete WAV, inspect the failure, player progress,
isolated queue, full decoding and natural ending before accepting it. Duration
alone cannot prove song identity. A reusable capture receipt prevents an upload
failure or false EOF alarm from forcing another full-song recording.

Use [Packaging](packaging.md); publish all tags and artwork before hashing the
finished FLAC for upload. For guest credits missing from the catalog display,
use verified performer evidence and retain original catalog credit separately;
do not replace `ALBUMARTIST` with a guest singer. Prefer timed official standard
or enhanced TTML. If only plain text remains, perform lyric-only enrichment
through the existing matching workflow instead of redownloading audio. Keep the
original timeline until a reliable per-song alignment or explicit offset exists.

When the user requests upload after every song, finish and verify that upload
before starting the next recording. Otherwise independent preparation may run
ahead without changing playback or weakening checkpoints. Report capture specs
separately from Music's download-quality preference: a 192 kHz ALAC setting does
not establish a 192 kHz recording. Rounded `volumedetect` output of 0 dB is not a
clipping verdict; inspect integer peak counts/runs when actual saturation needs
diagnosis, and do not promise no clipping from a rounded peak alone.

## Lilt on NAS

Use `server-operations`, read `nas:/opt/AGENTS.md` and Lilt's current API/operations
docs before live access. Prefer an existing authorized LAN route or a task-owned
SSH loopback tunnel directly to NAS, not a public-gateway detour. Origin and
authorization must already be valid; do not change public access or server Origin
configuration to make an upload work. Preserve existing read-only viewing tunnels.

```sh
node "$SKILL/scripts/apple/upload-lilt.mjs" --file "$FINAL_FLAC" \
  --verification "$PACKAGE_RECEIPT" --base "$LILT_API_BASE" \
  --origin "$ALLOWED_ORIGIN" --target nas --receipt "$WORK/upload.json"
```

The base includes the API prefix, such as a trusted loopback URL ending in
`/lilt/api`. Store the packaging command's JSON output as `$PACKAGE_RECEIPT`.
The upload helper hashes the final file once, sends sequential chunks of at most
32 MiB, validates durable acknowledgments, and reopens by fingerprint after an
uncertain response or 409. Transient chunk failures have at most three retries;
authorization/client errors stop. A rerun resumes from the server's offset and
retains unfinished publication state. It does not delete or replace tracks.

Publication checks include file hash/size, audio format, title/artist/album,
duration, expected artwork/timed lyrics, original-audio Range `206` and `fLaC`
signature, and cover accessibility. Duplicate recognition may return an owner-
edited current version for a historical input hash: preserve that metadata and
mark `expectedMetadataChecked: false` rather than claiming equality with the
submitted package. Trash duplicates are not restored automatically. Explicit
replacement/deletion remains a separately confirmed server-operations action.

## Recovery, completion and cleanup

Resume at the first unverified phase, not at the first song: validate and reuse
an existing WAV, packaged FLAC or remote receipt before repeating work. Recover
CoreAudio before relying on UI recovery. Attempt independent restoration steps
even if one fails; capture success and restoration success are separate states.
Maintain a standalone recovery entry point with the original snapshots available
if the controller is terminated. Final acceptance follows settled player/device
verification and active-library checks of this batch's IDs, not an old failure
file, a previous receipt, or the whole library's total count.

Stop managed recorders/uploaders and close only task-owned tunnels. Keep local
sources, recordings, companions, intermediate materials and recovery snapshots
until the user approves their exact cleanup scope. The cleanup rules are in
[Packaging](packaging.md); neither upload success nor a skill update authorizes
deletion. Leave installed dependencies and credentials outside cleanup.

## Focused validation

These checks use synthetic audio and mocked APIs; they neither play Music nor
upload to NAS. Run them only for the affected code, using the existing selected
environments without installing packages into global Python:

```sh
node --test "$SKILL/scripts/apple/selftest.mjs"
PYTHONPATH="$SKILL/scripts/apple" "$PACKAGING_PYTHON" -m unittest selftest.LyricsTests selftest.PackagingTests
PYTHONPATH="$SKILL/scripts/apple" "$GAMDL_PYTHON" -m unittest selftest.MaterialFetchTests
```

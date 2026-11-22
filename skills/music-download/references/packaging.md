# Metadata and FLAC Packaging

Use task-local paths in these commands. `SKILL` is the absolute skill folder;
`WORK` is a private staging folder outside Git. Do not alter the installed
Gamdl environment to add tagging dependencies. Through `python-environment`,
reuse a healthy environment with `mutagen` and, for alignment, `numpy`. Create
a task environment only when no suitable environment exists:

```sh
uv venv --python 3.12 "$WORK/env"
uv pip install --python "$WORK/env/bin/python" mutagen numpy
```

## Obtain materials and an optional matching donor

For recording packaging, prefer the metadata/TTML helper below when no donor
audio is needed. An accessible matching donor is useful for measured alignment;
it is not required to obtain catalog tags, official lyrics or a catalog cover.
Fetch several songs with `--song-ids` to reuse one API session and album data;
see [Apple batch workflow](apple-batch.md). Do not retry a known unavailable
donor path for every song in an album.

Inspect `gamdl --version` and `gamdl rip --help`. With the inspected 4.1.1 CLI,
the following scopes downloads and avoids changes to its media index:

```sh
gamdl rip "$SONG_URL" --auth-mode cookies --cookies-path "$COOKIES" \
  --song-codec aac-web --output-dir "$WORK/donor" --temp-path "$WORK/download" \
  --save-cover --file-cover-size 1600 --embedded-cover-size 1600 \
  --lyrics-file-format lrc --no-database --no-overwrite --no-tracebacks
```

Use the smallest compatible donor encoding. If that path is unavailable, fetch
catalog/lyrics without audio; do not install wrapper or acquire decryption
devices as an automatic fallback. A metadata-only run needs the catalog JSON
and user-supplied/previously obtained cover for packaging. An absent lyric or
cover is a reported limitation, not permission to use an unrelated release.

Find Gamdl's interpreter from its existing installation (for a uv tool,
`uv tool dir` then `gamdl/bin/python`), rather than using a global interpreter.
The fetch helper requires an empty/new output directory and prints only a
bounded summary or sanitized exception type/status:

```sh
"$GAMDL_PYTHON" "$SKILL/scripts/apple/fetch_metadata.py" \
  --song-id "$SONG_ID" --cookies "$COOKIES" --storefront cn --language zh-CN \
  --output-dir "$WORK/metadata"
```

Choose the actual storefront and language; `cn` and `zh-CN` are examples, not
account requirements. Authentication/network errors stop the attempt. Do not
dump exception objects, debug headers, cookies or token-bearing URLs. Standard
and enhanced lyrics can fail independently; the summary records missing modes.

For supplied TTML, render it separately with `scripts/apple/lyrics.py INPUT OUTPUT_DIR`,
adding `--enhanced` for syllable-timed input. The helper writes original and
complete official language variants, preserving TTML for details LRC cannot
represent. It does not convert Traditional Chinese by guessing a translation.

## Align the recording

```sh
"$WORK/env/bin/python" "$SKILL/scripts/apple/align_audio.py" \
  --recording "$RECORDING" --reference "$DONOR_M4A" \
  --output "$WORK/alignment.json"
```

The JSON includes three independent windows, correlations and signed offsets.
Check that the donor is the same recording and that `reliable` is true. A
uniform offset is only appropriate when the windows agree; a different intro,
editing, silence or drift may need manual correction. If unreliable, omit the
alignment input and report unaligned lyrics; do not treat zero as measured.
`--offset` on the packaging helper is an explicit manual alternative.

## Build and validate

```sh
"$WORK/env/bin/python" "$SKILL/scripts/apple/package_flac.py" \
  --source "$RECORDING" --donor "$DONOR_M4A" --song-id "$SONG_ID" \
  --catalog "$WORK/metadata/catalog.json" --lyrics-dir "$WORK/metadata" \
  --cover "$COVER" --alignment "$WORK/alignment.json" \
  --audio-source "Apple Music official playback captured through BlackHole" \
  --output "$FINAL_FLAC"
```

For metadata-only acquisition, omit `--donor`; `--catalog` then establishes the
catalog identity and supplies available common tags. Omit optional cover or
lyrics inputs only when unavailable. `--lyrics-language zh-Hans` is preferred
when a complete official variant exists; otherwise the original is used.
The helper selects a nonempty timed variant before a plain one, including
enhanced-only lyrics when the standard response is plain or unavailable. A
`.lrc` extension alone does not establish timing. It reports `lyrics_timed_lines`,
omits `SYNCEDLYRICS` for plain text, and writes `LYRICS_ALIGNMENT_STATUS`; a
zero offset without measured alignment remains `source_timestamps_unmeasured`.

Fetch separate artwork through [covers](covers.md). The default embedded cover
long edge is 1600 pixels, keeping aspect ratio and smaller source dimensions;
`--cover-size max` or a requested pixel size overrides it. Catalog maximum art
is an optional user choice, not the default. Preserve original cover/source
files when downsizing. A no-audio, no-lyrics catalog request can use
`fetch_metadata.py --metadata-only` without cookies.

Keep `ARTIST` separate from `ALBUMARTIST`: compilation/soundtrack album credits
can correctly differ from track singers. Preserve album release dates, label,
copyright, track/disc totals, compilation flags and catalog IDs. Do not invent
missing composer credits. Catalog-only packaging takes track totals from the
album's `trackCount`; disc totals use `discCount` or a complete, unpaginated track
relationship with known disc numbers. A partial track list cannot establish a
disc total. Keep the song's `DATE` distinct from `ALBUM_RELEASE_DATE`.
TTML `songwriter` stays `SONGWRITER`, not automatically
`COMPOSER` or `LYRICIST`. The package retains donor non-picture MP4 tags in a
reversible JSON representation and source-key aliases, plus cleaned catalog
JSON. Its Gamdl integration targets the inspected 4.1.1 API; inspect a changed
installed interface before use rather than modifying a healthy environment.

The script stages beside the destination, accepts 16/24-bit integer sources,
checks PCM SHA-256 before publication, and refuses an existing destination.
32-bit floating WAV must first undergo separately approved integer conversion;
that quantization is not covered by the lossless claim. The final tagged FLAC
contains standard tags, a native cover, display LRC, plain lyrics and preserved
source TTML. Word-synced lyrics are retained even if a consumer only supports
line-level lyrics. Raw TTML remains on the original source timeline.

After delivery, distinguish encoding specs from source/master quality. By
default keep final FLACs, recording backups and official `.movpkg` downloads.
If cleanup is requested, inventory only known task paths and await confirmation
of the exact scope, distinguishing intermediates, final music and Apple offline
downloads. Use Music's Remove Download action for authorized offline removal,
not Delete from Library. Preserve shared tools, credentials, package caches,
unrelated music and the remote library unless explicitly included.

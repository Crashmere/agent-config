# Metadata and FLAC Packaging

Use task-local paths in these commands. `SKILL` is the absolute skill folder;
`WORK` is a private staging folder outside Git. Do not alter the installed
Gamdl environment to add tagging dependencies. Through `python-environment`,
select/create a task environment with `mutagen` and, for alignment, `numpy`.

```sh
uv venv --python 3.12 "$WORK/env"
uv pip install --python "$WORK/env/bin/python" mutagen numpy
```

## Obtain a matching donor

Inspect `gamdl --version` and `gamdl rip --help`. With the inspected 4.1.1 CLI,
the following scopes downloads and avoids changes to its media index:

```sh
gamdl rip "$SONG_URL" --auth-mode cookies --cookies-path "$COOKIES" \
  --song-codec aac-web --output-dir "$WORK/donor" --temp-path "$WORK/download" \
  --save-cover --file-cover-size max --embedded-cover-size max \
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
"$GAMDL_PYTHON" "$SKILL/scripts/fetch_metadata.py" \
  --song-id "$SONG_ID" --cookies "$COOKIES" --storefront cn --language zh-CN \
  --output-dir "$WORK/metadata"
```

Choose the actual storefront and language; `cn` and `zh-CN` are examples, not
account requirements. Authentication/network errors stop the attempt. Do not
dump exception objects, debug headers, cookies or token-bearing URLs. Standard
and enhanced lyrics can fail independently; the summary records missing modes.

For supplied TTML, render it separately with `lyrics.py INPUT OUTPUT_DIR`,
adding `--enhanced` for syllable-timed input. The helper writes original and
complete official language variants, preserving TTML for details LRC cannot
represent. It does not convert Traditional Chinese by guessing a translation.

## Align the recording

```sh
"$WORK/env/bin/python" "$SKILL/scripts/align_audio.py" \
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
"$WORK/env/bin/python" "$SKILL/scripts/package_flac.py" \
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

The script stages beside the destination, accepts 16/24-bit integer sources,
checks PCM SHA-256 before publication, and refuses an existing destination.
32-bit floating WAV must first undergo separately approved integer conversion;
that quantization is not covered by the lossless claim. The final tagged FLAC
contains standard tags, a native cover, display LRC, plain lyrics and preserved
source TTML. Word-synced lyrics are retained even if a consumer only supports
line-level lyrics. Raw TTML remains on the original source timeline.

After delivery, distinguish encoding specs from source/master quality. Cleanup
must list only known task outputs, then await confirmation. Keep the final FLAC,
the agreed recording backup and official `.movpkg` downloads. Do not delete
shared package caches or other music as part of this workflow.

# Standalone Lyrics and Source Selection

Use only the requested lyric formats. Do not download audio, artwork or an AAC
donor merely to get lyrics. Prefer a platform's source for its explicit link;
without a chosen platform, LRCLIB is a useful public TXT/LRC source. Apple TTML
is the authorized official option for available word timing/translations.

## LRCLIB

[LRCLIB](https://lrclib.net) is a community lyric database with public machine-
readable queries. Read [current API documentation](https://lrclib.net/docs) when
the service changes. `GET /api/search` finds candidates by `track_name`,
`artist_name` and optional `album_name`; `GET /api/get/<id>` reads a selected
record. `plainLyrics`, `syncedLyrics`, `instrumental`, duration and release
metadata are independent fields. Preserve `lyricsfile` when actually returned;
its availability does not imply every track has word timing or translations.

```sh
node "$SKILL/scripts/lyrics.mjs" --title "$TITLE" --artist "$ARTIST" \
  --album "$ALBUM" --duration "$SECONDS" --formats txt,lrc --out "$WORK/lyrics"
```

Supply known album/duration instead of guessing. With only a name/artist, inspect
the candidates and release evidence. The helper excludes differing version
qualifiers, compares artists including title features, requires a supplied album
to match, and uses a 2-second duration tolerance when a duration is supplied.
It does not identify masters, audio edits or falsely labeled records.

`--formats` selects any of `txt,lrc,translation,yrc,source`; without it, all
available source variants are preserved. A provider's absent language field
stays null. Inspect the returned text and actual language variants for a requested
language; do not label community lyrics English or Chinese merely from the query.

Multiple eligible entries produce `status: ambiguous`, a candidate list and exit
code 2, without lyric files. After review, use a new output directory and add
`--id "$LRCLIB_ID"` with the expected title/artist/album/duration to verify the
chosen record. An explicitly supplied ID without expected metadata is a direct
record request, not a validated cross-platform match. Do not pick the first
result or silently remove album constraints to force a match.

## NetEase / Meting

```sh
node "$SKILL/scripts/lyrics.mjs" --provider netease --id "$NETEASE_SONG_ID" \
  --lrclib-fallback --out "$WORK/lyrics"
```

The helper gets song identity, then `lyric/new`, followed by Meting LRC if
needed. See [NetEase API details](netease-api.md) for current service addresses
and overrides. This route needs no account credentials. `--lrclib-fallback`
enables a metadata-matched public fallback; it does not replace the audio release.
For official-only requests do not enable a community fallback.

`nolyric` and the known instrumental marker are separate from actual lyrics.
Meting's “这似乎是一首纯音乐呢，请尽情欣赏它吧！” indicates missing lyrics even
for vocal songs. Do not embed it or report the track as instrumental.

## Apple Music

Use the existing Gamdl interpreter, not global Python. Cookies must already be
authorized. Choose the actual storefront and a verified catalog song ID:

```sh
"$GAMDL_PYTHON" "$SKILL/scripts/apple/fetch_metadata.py" \
  --song-id "$APPLE_SONG_ID" --cookies "$COOKIES" \
  --storefront "$STOREFRONT" --language "$LANGUAGE" --output-dir "$WORK/apple-lyrics"
```

This fetches catalog metadata and standard/enhanced TTML without audio or cover
downloads. Both modes can be unavailable independently. A valid metadata response
or `hasLyrics: true` does not guarantee accessible TTML. Stop authentication
failures for that source and report the sanitized error, then use an allowed
public source if it satisfies the request. Do not ask for passwords.

For supplied TTML, use `scripts/apple/lyrics.py INPUT NEW_DIR [--enhanced]`.
Preserve source text, word spans and original TTML. Apple's official translations
refer to internal paragraph `key`, not necessarily `xml:id`; replace all lines
only when the official variant is complete. Keep partial variants as unavailable,
not a mixture of original and translated text.

## Files and Status

Standalone results include `lyrics.json`: status, provider, origin, namespaced
source ID, matched/requested track, available formats, source timing and issues.
Statuses are `available`, `instrumental`, `unavailable`, `request_failed` or
`ambiguous`. Apple also preserves per-mode summaries and original TTML.

TXT/LRC requests save `lyrics.txt` and an LRC only when actual timing exists.
Translations/YRC/Lyricsfile are additional source files, not generated upgrades.
The public helper checks timestamp ordering/range in its report; investigate
failed checks before embedding LRC, or use plain text while retaining raw timing.
Format and metadata checks do not establish every word's correctness. Report
timing as unmeasured unless checked against the actual recording.

Use new output directories: files are never silently overwritten. Public helper
exit 0 means available/instrumental; 2 means unavailable, ambiguous or request
failure requiring the report; 1 means invocation/publication failure. Apple
exit 0 confirms catalog acquisition only; read its `lyrics.json` and mode issues.

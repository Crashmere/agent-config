# Standalone and Embedded Album Covers

Default to a 1600-pixel **long edge**, normally 1600 x 1600 for square artwork.
Keep a non-square image's aspect ratio. Do not crop, stretch or upscale a smaller
image. A smaller source is delivered at its actual dimensions with `belowTarget`.
The same policy applies to download companions, enrichment and Apple packaging.

## Resolve the release

Start from the specified song/album URL or verified catalog ID. Check album
title, album artist, release date and edition where available; a song's single
and album releases may use different art. Name-based queries find candidates,
not permission to select the first release. NetEase album/song detail and Apple
catalog/iTunes are the initial sources; LRCLIB is not a cover source.

```sh
node "$SKILL/scripts/covers.mjs" --netease-album-id "$ALBUM_ID" --out "$WORK/cover"
node "$SKILL/scripts/covers.mjs" --apple-id "$APPLE_ALBUM_ID" \
  --storefront "$STOREFRONT" --out "$WORK/cover"
```

`--netease-song-id` uses the selected song's album. `--apple-id` accepts a song or
album and uses public iTunes lookup without cookies. Its artwork URL is a catalog
candidate; verify actual downloaded pixels instead of relying on URL labels.
Metadata queries do not request lyrics, audio or donors.

For Apple catalog templates and known maximum dimensions:

```sh
"$GAMDL_PYTHON" "$SKILL/scripts/apple/fetch_metadata.py" \
  --album-id "$APPLE_ALBUM_ID" --metadata-only --storefront "$STOREFRONT" \
  --output-dir "$WORK/catalog"
node "$SKILL/scripts/covers.mjs" --catalog "$WORK/catalog/catalog.json" \
  --out "$WORK/cover" --size max
```

`--metadata-only` skips lyric requests and accepts public catalog access without
cookies. `--song-id` is also supported. If public token discovery/catalog access
fails, report it rather than installing a wrapper or initiating login.

## Size, format and output

Use `--size 1600`, another positive pixel size, or `max`. Request the provider's
corresponding size first; if unavailable, try the original public image and
downsize only when it exceeds the target. NetEase uses `param=1600y1600`; Apple
supports size templates. For `max` Apple templates need actual catalog dimensions,
not an invented large number. Low-resolution pixels returned by a server are
not proof of original image detail, even when a requested size was honored.

`--url` accepts a user-supplied public HTTPS image; `--file` processes local art.
For these routes the agent must establish release identity from the supplied
context. JPEG/PNG are preserved when no conversion is needed; WebP is converted
to PNG for native audio embedding. Unsupported/error-page inputs are rejected.

The helper creates a new output directory with `cover.jpg` or `cover.png` and
`cover.json`, recording release/source IDs, dimensions, format, resize state and
whether the source fell below target. It does not write music tags. Originals
are retained for local input. For embedded artwork, pass the verified file to
the relevant packaging/enrichment path. Neither path enlarges it by default.

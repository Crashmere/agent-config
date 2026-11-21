# Add Materials Without Redownloading Audio

Read actual local metadata before querying. Match its song/version to the chosen
lyric and album cover; filenames and old manifests alone do not establish the
current file. Acquire only missing/requested materials through [lyrics](lyrics.md)
and [covers](covers.md). Do not record or redownload otherwise valid audio.

## FLAC / MP3

```sh
node "$SKILL/scripts/retag.mjs" --source "$ORIGINAL_AUDIO" --out "$NEW_AUDIO" \
  --lyrics "$WORK/lyrics/lyrics.json" --cover "$WORK/cover/cover.jpg"
```

Omit either material when not requested; an existing picture is retained when
there is no new cover. A raw TXT/LRC is also accepted. Check the source identity
and any `timingCheck` failures before using a result. The helper performs no
network calls or automatic matching. It retains readable input metadata, writes
FLAC `LYRICS` or MP3 `USLT`, and verifies full decoding, unchanged audio packets,
audio properties, lyric readback and cover presence before publishing a new file.
It never replaces the original or changes the native FLAC/MP3 codec. FFmpeg's
metadata round trip is not a promise to preserve every nonstandard ID3 frame;
keep the original for recovery. Use `--cover-size max` only when requested.

Apple `lyrics.json` can be used for its selected original-language variant.
To select a complete official translation, pass its specific rendered TXT/LRC
or use the recording packaging path's language option. Raw TTML/YRC remain
separate because player support differs.

## Existing NetEase journal

An ordinary resume verifies successful audio but does not refresh missing lyrics.
For files managed by `.mscd`, acquire trustworthy companions, then stream-copy
into a new temporary output using `scripts/netease/audio.mjs` `tagAudio` with
the verified song and original playlist ID. After verification, update the
corresponding record's lyric/source status, size, lyric hash and unchanged packet
hash. Retain the original until any requested replacement completes, then audit
and aggregate through the original plan. Do not merely edit reports to claim a
new embedded lyric, or use the standalone retag output as if the old journal
already pointed to it. Use one writer for the state directory.

For existing WAV/ALAC recordings use [packaging](packaging.md), which verifies
decoded PCM equality and preserves Apple catalog metadata and source TTML.

---
name: apple-music-capture
description: "Capture Apple Music playback through BlackHole on macOS and package recordings as lossless FLAC with Gamdl metadata."
---

# Apple Music Capture

Produce one tagged FLAC from authorized Apple Music playback or an existing
recording. Use the recording for audio and the matching Gamdl catalog item for
metadata, cover art and lyrics. This is loopback capture, not extraction of the
original Apple Music stream: a 24-bit recording does not establish a 24-bit
master or bit-perfect playback.

## Choose the entry point

- For an existing WAV, ALAC/M4A or FLAC recording, start with metadata matching
  and packaging. Do not record the song again merely to use this skill.
- For a new macOS recording, read [Recording](references/recording.md). The
  native helper records bounded 24-bit integer PCM and snapshots/restores
  CoreAudio device settings; the agent controls Music playback separately.
- For donor acquisition, lyric preparation and packaging, read
  [Packaging](references/packaging.md).

Use `software-installation` for installing or removing tools, and
`python-environment` for Python environment selection and dependencies. Reuse
healthy Gamdl/FFmpeg/BlackHole installations. Installing BlackHole or granting
microphone/automation permissions remains a separate authorized action. The
workflow does not depend on wrapper, emulators or Docker.

## Execution contract

1. Identify the song and the source recording. Resolve ambiguous releases,
   live versions, remasters or regional catalog matches before merging.
   Prefer an exact catalog song ID and compare artist, album, duration and
   ISRC when available; matching titles alone is insufficient.
2. Use a private task staging directory. Cookies must already be authorized;
   read them locally without printing their contents or copying them into
   the skill/repository. Never request an account password for this workflow.
   A cookie expiry date is not a guarantee that its session remains valid.
3. For recording, verify the actual source quality, disable playback effects
   that alter the intended sound, avoid competing media and capture a short
   sample before a full run. Snapshot devices/rates and Music volume/state
   before changing them; retain the restoration state until recovery is
   verified, including after failure or interruption.
4. Fetch only metadata for the selected catalog recording. A temporary AAC
   donor may supply tags and alignment evidence but must never become the
   final FLAC audio. Preserve the largest artwork actually returned; do not
   upscale it or assume it is square.
5. Preserve official lyric text and original TTML. Apple's translations refer
   to body paragraphs by the internal `key` attribute, not necessarily
   `xml:id`. Use complete official replacements when present; otherwise keep
   the available language rather than relabeling it. Preserve word spans and
   timing. Measure alignment for each recording; never reuse a previous
   song's offset. Apply a positive offset when recording events occur later.
6. Package without overwriting the recording or an existing final file.
   Preserve sample rate, channels and integer bit depth. FLAC cannot represent
   floating-point PCM losslessly: explain any proposed quantization and get
   approval instead of silently calling it lossless. No upsampling or bit
   depth inflation to claim better quality.
7. Verify decoded PCM equality against the input recording, reread the tags
   and cover, and report available/unavailable metadata and measured lyric
   alignment. Only then propose the exact task-intermediate cleanup scope and
   obtain confirmation before deleting it. Preserve official offline packages,
   credentials, working tool installations and agreed recording backups.

## Metadata semantics

Keep `ARTIST` separate from `ALBUMARTIST`: a soundtrack/compilation may correctly
have a named singer and `群星` as its album artist. Services can show album
credits on album cards while correctly reading the track singer. Diagnose the
actual tags and service record before changing credits; service maintenance
belongs to its project and `server-operations`.

Do not invent missing composer credits. A TTML `songwriter` is preserved as
`SONGWRITER`, not automatically treated as `COMPOSER` or `LYRICIST`. Keep source
release dates, compilation flags, copyright, label and catalog identifiers.
The package script retains all donor non-picture MP4 tags in a reversible JSON
representation and source-key aliases, plus cleaned public catalog JSON when
provided. Artwork is embedded as a native front-cover picture.

## Helpers and verification boundary

- `scripts/coreaudio.swift`: device listing, state save/restore and bounded
  AudioQueue recording. Compile into task staging, not into the skill tree.
- `scripts/fetch_metadata.py`: standard/enhanced TTML and cleaned catalog
  metadata through the installed Gamdl API. Its API integration targets the
  inspected Gamdl 4.1.1 interface; inspect an incompatible version before use.
- `scripts/lyrics.py`: official translation replacement and plain/line/word
  lyric rendering, without external translation services.
- `scripts/align_audio.py`: independent waveform windows; an unreliable
  estimate is reported rather than applied automatically.
- `scripts/package_flac.py`: lossless integer-audio conversion, metadata
  transfer, cover embedding, PCM/tag validation and no-overwrite publication.

The originating workflow successfully captured official playback and verified
ALAC-to-FLAC PCM equality. The bundled native helper was subsequently rebuilt
and checked without starting another playback/capture session. Its first use
still requires the short capture and device-restoration checks above. Packaging
and alignment helpers have focused synthetic audio checks; this is not a
promise of compatibility with every Music/macOS/Gamdl release.

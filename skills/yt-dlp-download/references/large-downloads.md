# Large Files, Parallel Downloads, and Recovery

## Contents

- [Diagnose the problem](#diagnose-the-problem)
- [Choose a downloader and preserve progress](#choose-a-downloader-and-preserve-progress)
- [Parallel video/audio and final merging](#parallel-videoaudio-and-final-merging)
- [Verification boundaries](#verification-boundaries)

## Diagnose the problem

First identify the failing stage: search/page retrieval, player metadata, media transfer, subtitle/thumbnail downloads, merging, or verification. Preserve the specific error and completed progress, and redact before displaying them; access to the player page does not mean every media CDN is healthy.

| Symptom | Next step | Do not infer |
|---|---|---|
| Search with `--print` produces no output for a long time | Remove quiet output to observe the current stage; set request timeouts; test the existing configuration, `--ignore-config`, and `--force-ipv4` separately | No output does not mean the process never started; success with combined options does not identify one root cause |
| curl can read the page while yt-dlp stalls | Compare the same URL, network configuration, and IP family; check versions and existing proxy settings | Do not independently change system proxies or permanently disable IPv6 |
| `bytes read, ... more expected` | The data connection ended early; observe whether retries recover, retain format and filename, and test HTTP chunk sizes on a small scale if needed | Do not immediately conclude disk corruption, file completeness, or a DNS-only problem |
| Media requests return 403 | Extract links again from the stable video URL; check link validity, client support, and content accessibility; confirm the applicable identity method when an account is required | A 403 is not always expiration; identity or site-client changes may be involved. Do not substitute repeated signature-parameter changes for diagnosis |
| One aria2 connection returns 500 | Check whether overall progress continues and other connections remain alive; preserve control files and retry within limits after the whole item fails | A single-connection error does not mean all data failed or require immediately restarting healthy connections |
| Byte count changes after `FixupM4a` | Verify the remuxed file using tracks, duration, and decoding | Do not mistake normal container repair for missing audio |
| A final file exists while temporary files for the task remain | Inspect tool exit status, control files, and final media; confirm no active writer remains | Do not skip verification based only on `ls` size or an already-exists message |

Keep causal claims bounded: a successful recovery method can be recorded as a method; report a root cause only when supported by a controlled comparison or error evidence. Public pages do not require reading browser Cookies by default. When login is actually needed, follow current authorization and avoid exporting Cookies into the repository, reports, or shared directories.

## Choose a downloader and preserve progress

### Decide whether switching is worthwhile

Continue using the native downloader while it keeps progressing; for segmented protocols, consider its native concurrency. `--concurrent-fragments` does not add connections to an ordinary single-file HTTPS download. Do not treat aria2 as mandatory or change runtimes or dependencies solely to test acceleration.

Before choosing aria2, inspect local capabilities with `aria2c --version` and the relevant `--help`. Use `software-installation` for missing tools; package managers may install or upgrade dependencies, so report actual changes afterward instead of promising to change only one binary.

For selected HTTP(S) single-file formats, add the following to the main workflow command:

```bash
--downloader aria2c \
--downloader-args 'aria2c:-x16 -s16 -k1M --continue=true --file-allocation=none --summary-interval=30 --show-console-readout=false --console-log-level=warn --retry-wait=3 --max-tries=20'
```

Choose 8–16 connections according to network conditions, reducing concurrency if sustained speed falls or request errors increase. These are aria2 arguments; add `--force-ipv4` to yt-dlp and `--disable-ipv6=true` to aria2 together only when evidence supports the IPv4 path. Do not apply these tunings to every site or protocol by default.

aria2's `--max-tries` / `--retry-wait` do not mean every HTTP error will be retried. The aria2 1.37.0 version verified here has no `--retry-on-http-error`; check version-specific help in future instead of copying another downloader's options.

### Preserve state before switching

1. Identify the current task's PID, parent/child processes, formats, destination paths, and downloader. Stop only this task; do not affect other downloads with broad `pkill` commands.
2. Prefer a normal interruption so the tool can save state; wait for the original writer to exit before handing over. If needed, preserve a separate copy of this task's temporary data or use a new output path; do not overwrite unknown files.
3. Native yt-dlp's contiguous `.part` is not aria2's chunk control state. `yt-dlp --continue` alone does not guarantee aria2 can resume; some versions' external download commands allow overwriting an old file without a control file. Explicitly pass `--continue=true`, but still verify that progress was actually inherited.
4. An aria2 `.part` may have a logical length close to the final size from the start; completed ranges are tracked in the matching `.aria2` control file. Preserve both together with identical paths and formats. Diagnose a missing control file before proceeding; do not hand that file to the native downloader to resume from EOF.
5. Compare completed bytes/chunks before and after handover; do not hide a fresh download behind a recalculated percentage. If safe resuming cannot be established, continue with the old downloader or use an independent new output, retaining the original data until recovery is confirmed.

### Bounded refresh retries

Keep the output template, format IDs, and downloader unchanged. After each whole-item failure, extract fresh media URLs through the stable video URL, then let the downloader read the original control file. Bound outer attempts reasonably, for example to 3–5 with increasing backoff; repeated failures for the same reason require evidence-based parameter changes or a report of the missing conditions.

Keep observing when one connection errors but the task continues progressing. Do not blindly start a second writer whenever stderr contains `ERROR`. Do not put temporary signed URLs into the skill, persistent task configuration, or public logs.

## Parallel video/audio and final merging

### Give each track a single writer

Determine video and audio IDs from the format list first; do not hard-code a previously successful `299+140`. Use the same stable template and start two separate single-format tasks from the outset:

```bash
# Set YT_VIDEO_ID and YT_AUDIO_ID from the current -F results; monitor each command separately.
yt-dlp --no-playlist --abort-on-error --continue --no-overwrites \
  --format "$YT_VIDEO_ID" --paths "$YT_OUT" \
  --output '%(id)s.f%(format_id)s.%(ext)s' "$YT_URL"

yt-dlp --no-playlist --abort-on-error --continue --no-overwrites \
  --format "$YT_AUDIO_ID" --paths "$YT_OUT" \
  --output '%(id)s.f%(format_id)s.%(ext)s' "$YT_URL"
```

Add timeouts, retries, and the selected downloader arguments from the main workflow. Keep the same output template during final merging: the basename is the video ID, and intermediate tracks add `.f<format-id>`.

**Do not** run a `video+audio` task alongside another task writing the same audio track. The former may begin writing audio after video finishes or fails, creating a race. If already started this way, stop overlapping writers, confirm they have exited, then switch to non-overlapping single-format tasks.

Do not add orchestration for a very small audio track by default; use independent parallel tasks only when they materially help during a large-file wait. Do not merge or report overall success before all tasks complete.

### Merge downloaded tracks

First verify both tracks' formats and durations. For unprocessed original tracks, compare against the `filesize` extracted in this task; if the tool performed `FixupM4a`, use media verification instead of the original byte count.

Save local `.info.json` obtained for the same video and format selection. It may contain temporary signed links; keep it in the task directory and out of the repository. Once both tracks pass verification and output naming matches exactly, merge and embed chapters using the existing metadata:

```bash
yt-dlp --ignore-config --continue --no-overwrites \
  --format "$YT_VIDEO_ID+$YT_AUDIO_ID" --merge-output-format "$YT_CONTAINER" \
  --embed-metadata --embed-chapters \
  --paths "$YT_OUT" --output '%(id)s.%(ext)s' \
  --load-info-json "$INFO_FILE"
```

This skeleton handles video, audio, and chapters; for subtitles, thumbnails, and descriptions, prepare sidecar files with the same basename and add the corresponding arguments from the main workflow. If intermediate files used a different template, first make the final template match existing tracks; do not silently rename unknown files.

`--load-info-json` alone does not guarantee offline operation: missing tracks or mismatched naming may still trigger downloads from its old links. Confirm that logs show reuse of verified existing files; if additional downloads are needed, obtain fresh metadata from the stable video URL. `--skip-download` cannot replace the merge command.

## Verification boundaries

- Use `ffprobe` to confirm duration, codecs, dimensions, frame rate, tracks, and chapters. Audio/video durations may differ slightly due to encoded frame boundaries; investigate meaningful differences instead of automatically relaxing tolerances.
- Verify final media with `scripts/verify_media.py`. `--info-json` supplies the expected duration and, in full video/audio mode, compares source chapter counts, titles, and start/end times; `--expect-chapters` alone checks only counts. Explicitly select required streams for silent source videos or separate audio tracks.
- Add `-progress pipe:1` to tail decoding and inspect actual output duration and video frame count. Exit code 0 alone may still represent an empty decode that produced no frames.
- Tail verification does not prove every frame throughout the video is intact. When there is evidence of missing segments, decoding errors, truncation, or source-duration mismatch, investigate the affected area or perform a full decode; do not fully decode every otherwise normal video lasting more than ten hours by default.
- Merging, container repair, and metadata embedding change byte counts without necessarily re-encoding. Preserving original codecs also does not justify claims that game footage has undergone content review or contains the entire original story.

### MP4 chapter count is correct but navigation is wrong

MP4 can store both a Nero `chpl` list and a QuickTime `text` chapter track. A complete former does not guarantee a correct latter; `ffprobe` may still show the correct total when reading them together, while durations are zero, titles are misaligned, or entries are duplicated.

First compare source chapter titles and times, then inspect the data track's `time_base`, sample count, and remuxing warnings. For `Application provided duration ... is invalid` or `Packet duration ... is out of range`, check whether the automatically selected movie timescale makes long chapters exceed the sample-duration limit. Do not vaguely attribute this to cumulative overflow merely because a value exceeds 32 bits; use actual values or small experiments to distinguish causes.

Reproduced in FFmpeg 9.0.2: with video timescale 15360 and audio timescale 44100, the default automatic movie timescale is 11289600; a 200-second chapter becomes 2257920000 ticks, exceeding the signed 32-bit limit, producing warnings and losing text samples while the program still exits 0. Explicit output `-movie_timescale 1000` restores samples, titles, and times. Do not generalize this result to every FFmpeg version; inspect current behavior.

For yt-dlp tasks producing final MP4 output in that environment, add the following argument to the Metadata step before downloading to prevent incorrect writes. This argument scope was verified in yt-dlp 2026.08.19; check help after version changes. Do not pass this MP4-specific option to other containers such as MKV.

```bash
--postprocessor-args 'Metadata+ffmpeg_o:-movie_timescale 1000'
```

Generate UTF-8 FFmetadata from source chapters, convert to milliseconds, and correctly escape backslashes, equals signs, semicolons, hash signs, and newlines in titles. Write a separate new file first and retain the original. For files confirmed to require only one video stream and the main audio track, explicitly rebuild chapters:

```bash
ffmpeg -n -nostdin -i "$ORIGINAL_FILE" -f ffmetadata -i "$CHAPTERS_FILE" \
  -map 0:v:0 -map 0:a:0 -map_metadata 0 -map_chapters 1 \
  -c copy -movie_timescale 1000 -movflags +faststart "$REPAIRED_FILE"
```

Confirm that the current FFmpeg supports `-movie_timescale` before using this repair option. If other audio tracks, subtitles, or cover art must be retained, map them explicitly; do not discard content by blindly copying the two-stream mapping or copy old chapter data tracks known to be corrupt. FFmetadata's `TIMEBASE=1/1000` alone does not guarantee a low timescale in MP4 output tracks.

After repair, compare every chapter's title, start/end times, video/audio durations, and tail output again. If needed, run `ffmpeg -i ... -map 0:v:0 -map 0:a:0 -c copy -f streamhash -hash sha256 -` on both original and repaired files and compare compressed audio/video packet digests to confirm only the container changed. Replace only after all checks pass and the original has not been modified by another task; do not use exit code 0 to conceal the timestamp warnings above.

When option semantics change, first check current `yt-dlp --help`, `aria2c --help`, the [official yt-dlp documentation](https://github.com/yt-dlp/yt-dlp#readme), and the [official aria2 manual](https://aria2.github.io/manual/en/html/aria2c.html).

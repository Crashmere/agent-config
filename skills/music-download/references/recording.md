# macOS Playback Recording

Use official Music playback with BlackHole 2ch as the loopback device. Confirm
the requested song/version and available source quality in Music. Do not parse
encrypted offline packages into playable audio. Capture inherits Music's
decoder, mixer, volume and system processing; it is not a bit-exact extraction.

## Preparation and recovery

Inspect `system_profiler SPAudioDataType`, `gamdl --version`, `ffmpeg -version`
and the Music app. Install missing software only through the applicable skill;
BlackHole installation and microphone/automation access need authorization.
Read the native helper's `--help` before changing any device.

```sh
swiftc "$SKILL/scripts/apple/coreaudio.swift" -o "$WORK/coreaudio"
"$WORK/coreaudio" list
"$WORK/coreaudio" save "$WORK/audio-state.json"
```

Snapshot Music player state, current track/position and sound volume with
AppleScript before changes. Resolve the target track by ID or validated title,
artist and album rather than assuming a title search returns one item. Saved
state and recordings belong in private task staging, not the skill repository.

Arm restoration in the controlling process before selecting BlackHole. Keep
the saved state available for explicit recovery if the agent/tool is killed.
The following trap covers normal shell exit/INT/TERM, not power loss or SIGKILL:

```sh
trap '"$WORK/coreaudio" restore "$WORK/audio-state.json"' EXIT INT TERM
"$WORK/coreaudio" select "$BLACKHOLE_DEVICE_ID" "$SAMPLE_RATE"
```

Wait with a bounded deadline for the actual settings controls before reading or
clicking them. A fixed delay after opening Music settings can expire before its
Playback window is ready, even when the same UI worked during preparation.

Use the source sample rate where known and supported, usually 44100 or 48000;
do not force a high rate to imply higher source quality. The helper routes the
default playback output and input to the selected device, leaving system-alert
output alone. Nevertheless stop competing audio and notification sounds. Check
headphone/Bluetooth/aggregate-device behavior instead of assuming defaults.
Disable equalizer, Sound Check, crossfade and sound enhancement when they alter
the intended recording, preserving the user's original settings for recovery.
Music volume controls affect captured amplitude. Choose a nonclipping level
and report the capture path; do not normalize the finished recording silently.

## Capture and control playback

The native helper uses AudioQueue input and writes interleaved 24-bit integer
stereo WAV. It selects the exact device UID obtained from `list`. It has a hard
duration bound, exclusive output creation, a ready marker and an optional stop
marker. `SECONDS` includes startup/tail allowance; it is not source duration
metadata. Inspect errors before accepting a recording.

```sh
"$WORK/coreaudio" record "$RECORDING_WAV" "$BLACKHOLE_DEVICE_UID" \
  "$SAMPLE_RATE" "$SECONDS" "$WORK/ready" "$WORK/stop"
```

Run the recorder in a managed process/session. Wait for the ready marker before
starting the selected Music track at position zero. Keep the player on the
target track, stop at its end before the next track/crossfade, and create the
stop marker or terminate the managed recorder gracefully. SIGINT/SIGTERM close
the WAV; do not kill it with SIGKILL. A readiness timeout, Music failure or
early input error stops the workflow and triggers restoration rather than
starting a silent full-length recording.

Music 1.7.2 can continue to another song despite AppleScript's `once true`.
Snapshot and disable Autoplay (`自动连播`) separately from shuffle and repeat;
verify the UI control by its `AXIdentifier` (`autoplay`) instead of assuming a
fixed checkbox position on another version. A task-owned temporary playlist
containing exactly one verified library track prevents ordinary queue advance.
Before changing its contents, verify the playlist ID, count and previous track
ID so user-added items are not removed. Retain that playlist after capture unless
cleanup is authorized. Monitor the actual player state and track ID throughout
capture; elapsed time alone does not establish that the expected song played.

First capture a short sample. Check codec, sample rate, channels, duration,
nonzero signal and peak level with FFprobe/FFmpeg (`astats` or `volumedetect`),
and listen when possible. macOS microphone privacy may block AudioQueue until
the invoking terminal/app receives permission; ask the user to grant it through
System Settings instead of modifying TCC databases. Native format/device errors
require inspecting supported rates and channels, not repeated blind retries.

For a full capture, preserve the WAV until FLAC PCM equality is established.
Do not trim leading/trailing silence without checking whether it belongs to the
song. If trimming is requested, retain the source and include that timeline
change in lyric alignment; a trimmed file is no longer PCM-identical to the
whole untrimmed source.

## Restore and finish

Pause Music and stop recording before restoring CoreAudio. Restore every saved
device and nominal rate, reread defaults and compare them to the snapshot. If a
saved device is missing, report it and retain the snapshot rather than silently
substituting another device. Silence Music and restore CoreAudio before UI-based
preference recovery. Attempt independent recovery steps even if another fails,
collect their errors, and mark recovery verified only after every required step
passes. A settings-window error must not leave default devices on BlackHole.
Restore Music volume and processing preferences;
restore its prior track/position, and clarify whether to resume audible playback
when the user did not explicitly request it. Do not delete restoration state
until recovery has been checked.

Restoring a prior track is asynchronous: playing it can finish after an immediate
pause and seek. Keep volume at zero, wait with a bounded deadline for the saved
track ID and advancing position, then seek and pause. Reread the final player
state after a short settling delay and verify track ID, position, volume,
shuffle/repeat, EQ, processing preferences and Autoplay against the snapshots.
Keep playback paused unless audible resumption was explicitly requested. Retain
the recovery snapshots and report any mismatch rather than marking restoration
successful from command exit codes alone.

Proceed to [Packaging](packaging.md). A consumer showing album-artist credits
such as `群星` may still read the track singer correctly; verify `ARTIST`
separately before treating it as a capture/tagging failure.

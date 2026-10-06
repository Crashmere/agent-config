#!/usr/bin/env python3
"""Read-only media structure and tail-decode check; Python stdlib + FFmpeg."""

import argparse
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def positive(value):
    result = number(value)
    return result if result is not None and result > 0 else None


def positive_arg(value):
    result = positive(value)
    if result is None:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return result


def rate(value):
    try:
        return positive(float(Fraction(str(value))))
    except (ValueError, ZeroDivisionError):
        return None


def run(command, timeout):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise ValueError(f"{command[0]} failed ({result.returncode}): {result.stderr[-2000:].strip()}")
    return result.stdout


def verify(args):
    path = args.file.expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Media file is missing or empty")
    if path.suffix in (".part", ".aria2") or ".temp." in path.name:
        raise ValueError("Select the completed media file, not a temporary/control file")
    active = [str(p) for p in (
        Path(str(path) + ".part"), Path(str(path) + ".aria2"),
        Path(str(path) + ".part.aria2"),
    ) if p.exists()]
    if active:
        raise ValueError(f"Matching download state remains; resolve before verification: {active}")
    if ((args.width is not None and args.width <= 0)
            or (args.height is not None and args.height <= 0)):
        raise ValueError("Expected width and height must be positive")
    if args.expect_chapters is not None and args.expect_chapters < 0:
        raise ValueError("Expected chapter count must not be negative")
    if args.fps is not None and rate(args.fps) is None:
        raise ValueError("Expected fps must be a positive number or fraction")

    source = {}
    if args.info_json:
        source = json.loads(args.info_json.expanduser().read_text(encoding="utf-8"))
        if not isinstance(source, dict):
            raise ValueError("Source info JSON must contain an object")
    expected = args.expect_duration
    if expected is None and args.info_json:
        expected = positive(source.get("duration"))
        if expected is None:
            raise ValueError("Source duration is unavailable; provide --expect-duration explicitly")

    probe = json.loads(run([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-show_chapters",
        "-of", "json", str(path),
    ], args.timeout))
    duration = positive(probe.get("format", {}).get("duration"))
    if duration is None:
        raise ValueError("Final container duration is unavailable or invalid")
    if expected is not None and abs(duration - expected) > args.tolerance:
        raise ValueError(f"Duration mismatch: expected {expected}s, found {duration}s")

    kinds = ("video", "audio") if args.streams == "av" else (args.streams,)
    selected = {}
    warnings = []
    for kind in kinds:
        stream = next((s for s in probe.get("streams", [])
                       if s.get("codec_type") == kind and not
                       s.get("disposition", {}).get("attached_pic")), None)
        if stream is None:
            raise ValueError(f"Required {kind} stream is missing")
        stream_duration = positive(stream.get("duration"))
        if stream_duration is None:
            warnings.append(f"{kind} stream duration unavailable; separate duration comparison skipped")
        elif abs(stream_duration - duration) > args.tolerance:
            raise ValueError(f"{kind} stream duration {stream_duration}s differs from container {duration}s")
        selected[kind] = stream

    video = selected.get("video")
    if any(value is not None for value in (args.width, args.height, args.fps)) and video is None:
        raise ValueError("Video expectations require --streams av or video")
    if video:
        for key in ("width", "height"):
            expected_dimension = getattr(args, key)
            if expected_dimension is not None and video.get(key) != expected_dimension:
                raise ValueError(f"{key} mismatch: expected {expected_dimension}, found {video.get(key)}")
        actual_fps = rate(video.get("avg_frame_rate")) or rate(video.get("r_frame_rate"))
        if args.fps is not None and (actual_fps is None or abs(actual_fps - rate(args.fps)) > 0.05):
            raise ValueError(f"FPS mismatch: expected {args.fps}, found {actual_fps}")
    chapters = probe.get("chapters", [])
    chapter_count = len(chapters)
    if args.expect_chapters is not None and chapter_count != args.expect_chapters:
        raise ValueError(f"Chapter mismatch: expected {args.expect_chapters}, found {chapter_count}")
    source_chapters = source.get("chapters") if args.streams == "av" else None
    if source_chapters is not None and not isinstance(source_chapters, list):
        raise ValueError("Source chapters must be a list")
    if source_chapters is not None and len(source_chapters) != chapter_count:
        raise ValueError(f"Source chapter mismatch: expected {len(source_chapters)}, found {chapter_count}")
    previous_start = -1.0
    for index, chapter in enumerate(chapters):
        start = number(chapter.get("start_time"))
        end = number(chapter.get("end_time"))
        if (start is None or end is None or start < 0 or end <= start
                or start < previous_start or end > duration + args.chapter_tolerance):
            raise ValueError(f"Invalid chapter timing at chapter {index + 1}: start={start}, end={end}")
        previous_start = start
        if source_chapters is None:
            continue
        original = source_chapters[index]
        if not isinstance(original, dict):
            raise ValueError(f"Invalid source chapter {index + 1}")
        for key, actual in (("start_time", start), ("end_time", end)):
            expected_time = number(original.get(key))
            if expected_time is None or expected_time < 0:
                raise ValueError(f"Missing/invalid source {key} at chapter {index + 1}")
            if abs(actual - expected_time) > args.chapter_tolerance:
                raise ValueError(f"Chapter {index + 1} {key} mismatch: expected {expected_time}s, found {actual}s")
        title = original.get("title")
        if isinstance(title, str):
            actual_title = chapter.get("tags", {}).get("title", "")
            if actual_title != title:
                raise ValueError(f"Chapter {index + 1} title mismatch: expected {title!r}, found {actual_title!r}")
        else:
            warnings.append(f"Source chapter {index + 1} has no title; title comparison skipped")

    tail_seconds = min(args.tail_seconds, duration)
    command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-xerror",
               "-sseof", str(-tail_seconds), "-i", str(path), "-t", str(tail_seconds)]
    for stream in selected.values():
        command += ["-map", f"0:{stream['index']}"]
    command += ["-progress", "pipe:1", "-f", "null", "-"]
    output = run(command, args.timeout)
    progress = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    decoded = positive(progress.get("out_time_us"))
    decoded = decoded / 1_000_000 if decoded is not None else 0
    frames = int(progress.get("frame", "0"))
    if progress.get("progress") != "end" or decoded <= 0:
        raise ValueError("Tail decode produced no completed output")
    if decoded < tail_seconds - min(0.5, tail_seconds * 0.1):
        raise ValueError(f"Tail decode is too short: expected about {tail_seconds}s, got {decoded}s")
    if video and frames <= 0:
        raise ValueError("Tail decode produced no video frames")

    if expected is None:
        warnings.append("No expected/source duration supplied; source completeness was not compared")
    keys = ("codec_name", "width", "height", "avg_frame_rate", "r_frame_rate",
            "sample_rate", "channels", "duration")
    return {
        "ok": True, "path": str(path), "size_bytes": path.stat().st_size,
        "duration_seconds": duration, "expected_duration_seconds": expected,
        "streams": {kind: {key: stream[key] for key in keys if key in stream}
                    for kind, stream in selected.items()},
        "chapter_count": chapter_count, "source_chapters_compared": source_chapters is not None,
        "tail_decode": {"seconds": decoded, "video_frames": frames if video else None},
        "coverage": "Container/selected streams and tail decode only; not a full-file decode",
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--info-json", type=Path, help="Local yt-dlp metadata; compare duration and source chapters (av mode)")
    parser.add_argument("--expect-duration", type=positive_arg, help="Override expected source seconds")
    parser.add_argument("--streams", choices=("av", "video", "audio"), default="av")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--fps", help="Expected frame rate, e.g. 60 or 60000/1001")
    parser.add_argument("--expect-chapters", type=int)
    parser.add_argument("--chapter-tolerance", type=positive_arg, default=0.25, help="Chapter timestamp tolerance in seconds")
    parser.add_argument("--tolerance", type=positive_arg, default=2.0, help="Duration tolerance in seconds")
    parser.add_argument("--tail-seconds", type=positive_arg, default=10.0)
    parser.add_argument("--timeout", type=positive_arg, default=120.0, help="Timeout per FFmpeg/ffprobe call")
    args = parser.parse_args()
    try:
        report = verify(args)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

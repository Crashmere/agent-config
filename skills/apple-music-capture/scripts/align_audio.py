"""Estimate recording delay from independent normalized waveform correlations."""

import argparse
import json
from pathlib import Path
import subprocess

import numpy as np

RATE = 8000


def duration(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "json", str(path)], capture_output=True, text=True,
                            check=True, timeout=60)
    return float(json.loads(result.stdout)["format"]["duration"])


def read(path, start, length):
    result = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(start),
                             "-i", str(path), "-t", str(length), "-map", "0:a:0",
                             "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
                            capture_output=True, check=True, timeout=60)
    return np.frombuffer(result.stdout, dtype="<f4").astype(np.float64)


def estimate(recording, reference, start, window, max_offset):
    beginning = max(0, start - max_offset)
    ref = read(reference, start, window)
    capture = read(recording, beginning, window + start - beginning + max_offset)
    if len(ref) < RATE or len(capture) < len(ref):
        raise ValueError("Audio is too short for the alignment window")
    ref -= ref.mean()
    energy = np.dot(ref, ref)
    if energy < 1e-9:
        raise ValueError("Silent reference window")
    # FFT convolution supplies every sliding dot product without a quadratic loop.
    size = 1 << (len(capture) + len(ref) - 2).bit_length()
    dots = np.fft.irfft(np.fft.rfft(capture, size) * np.fft.rfft(ref[::-1], size), size)
    dots = dots[len(ref)-1:len(capture)]
    sums = np.concatenate(([0.0], np.cumsum(capture)))
    squares = np.concatenate(([0.0], np.cumsum(capture * capture)))
    n = len(ref)
    variance = squares[n:] - squares[:-n] - (sums[n:] - sums[:-n])**2 / n
    correlations = dots / np.sqrt(energy * np.maximum(variance, 1e-20))
    index = int(np.argmax(correlations))
    offset = beginning + index / RATE - start
    return {"window_start": start, "offset_seconds": offset,
            "correlation": float(correlations[index])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recording", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--window", type=float, default=5)
    parser.add_argument("--max-offset", type=float, default=5)
    args = parser.parse_args()
    if args.window < 1 or args.max_offset <= 0 or args.output.exists():
        parser.error("Use a new output file and positive window/offset bounds")
    available = min(duration(args.recording), duration(args.reference))
    if available < args.window + 2 * args.max_offset + 1:
        parser.error("Audio too short; reduce window and maximum offset")
    starts = np.linspace(args.max_offset, available - args.window - args.max_offset, 3)
    checks = [estimate(args.recording, args.reference, float(start), args.window,
                       args.max_offset) for start in starts]
    offsets = [check["offset_seconds"] for check in checks]
    spread = max(offsets) - min(offsets)
    reliable = (spread <= 0.03 and min(c["correlation"] for c in checks) >= 0.85
                and max(abs(x) for x in offsets) < args.max_offset - 0.02)
    result = {"offset_seconds": float(np.median(offsets)), "reliable": reliable,
              "offset_spread_seconds": spread, "independent_window_checks": checks,
              "meaning": "Positive offsets move donor lyrics later on the recording timeline"}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

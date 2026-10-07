#!/usr/bin/env python3
"""Read-only preflight for image batches. Standard library only; no model calls."""

import argparse
import json
import math
import stat
from pathlib import Path

MIB = 1024 * 1024
IMAGE_ENVELOPE_BYTES = 512


def mib_bytes(value):
    try:
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            raise ValueError
        result = int(number * MIB)
        if result <= 0:
            raise ValueError
        return result
    except (ValueError, OverflowError):
        raise argparse.ArgumentTypeError("MiB must be a finite positive number")


def positive_int(value):
    try:
        number = int(value)
        if number <= 0:
            raise ValueError
        return number
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer")


def inspect_manifest(manifest):
    manifest = Path(manifest).resolve(strict=True)
    count = raw_bytes = encoded_bytes = 0
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        path = Path(line)
        if not path.is_absolute():
            path = manifest.parent / path
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size == 0:
            raise ValueError(f"{manifest}:{line_number}: expected a nonempty regular file")
        count += 1  # Repeated embeddings count even when they use the same path.
        raw_bytes += info.st_size
        encoded_bytes += 4 * ((info.st_size + 2) // 3) + IMAGE_ENVELOPE_BYTES
    return {"images": count, "raw_bytes": raw_bytes, "encoded_bytes": encoded_bytes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retained", required=True, help="images still in this context; one path per line")
    parser.add_argument("--next", required=True, dest="pending", help="all images proposed for the next batch")
    parser.add_argument("--max-images", type=positive_int, default=4)
    parser.add_argument("--batch-mib", type=mib_bytes, default=8 * MIB, dest="batch_bytes")
    parser.add_argument("--request-mib", type=mib_bytes, default=40 * MIB, dest="request_bytes")
    parser.add_argument("--reserve-mib", type=mib_bytes, default=8 * MIB, dest="reserve_bytes")
    args = parser.parse_args()
    try:
        if args.reserve_bytes >= args.request_bytes:
            raise ValueError("reserve must be smaller than request budget")
        retained = inspect_manifest(args.retained)
        pending = inspect_manifest(args.pending)
        if not pending["images"]:
            raise ValueError("next manifest must contain at least one image")
    except (OSError, ValueError, UnicodeError) as error:
        print(json.dumps({"allowed": False, "error": str(error)}, ensure_ascii=False))
        return 2

    projected = retained["encoded_bytes"] + pending["encoded_bytes"] + args.reserve_bytes
    violations = []
    if pending["images"] > args.max_images:
        violations.append("batch_image_count")
    if pending["encoded_bytes"] > args.batch_bytes:
        violations.append("batch_media_bytes")
    if projected > args.request_bytes:
        violations.append("request_estimate_bytes")
    print(json.dumps({
        "allowed": not violations,
        "estimate_only": True,
        "retained": retained,
        "next": pending,
        "projected_request_bytes": projected,
        "limits": {
            "max_batch_images": args.max_images,
            "batch_encoded_bytes": args.batch_bytes,
            "request_bytes": args.request_bytes,
            "non_media_reserve_bytes": args.reserve_bytes,
        },
        "violations": violations,
    }, ensure_ascii=False))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())

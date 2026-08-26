from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRICING_AS_OF = "2026-08-26"
PRICING_SOURCE = "https://developers.openai.com/api/docs/pricing#image-generation"
MODEL_TOKEN_RATES = {
    "gpt-image-2": {
        "text_input": 5.0 / 1_000_000,
        "image_input": 8.0 / 1_000_000,
        "image_output": 30.0 / 1_000_000,
    }
}

OUTPUT_COST_TABLE = {
    ("low", "1024x1024"): 0.006,
    ("low", "1024x1536"): 0.005,
    ("low", "1536x1024"): 0.005,
    ("medium", "1024x1024"): 0.053,
    ("medium", "1024x1536"): 0.041,
    ("medium", "1536x1024"): 0.041,
    ("high", "1024x1024"): 0.211,
    ("high", "1024x1536"): 0.165,
    ("high", "1536x1024"): 0.165,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call the OpenAI Image API and emit a cost summary."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--model", default="gpt-image-2")
        subparser.add_argument("--prompt", required=True)
        subparser.add_argument("--size", default="1024x1024")
        subparser.add_argument(
            "--quality",
            default="high",
            choices=["low", "medium", "high", "auto"],
        )
        subparser.add_argument(
            "--output-format",
            default="png",
            choices=["png", "jpeg", "webp"],
        )
        subparser.add_argument("--out", required=True)
        subparser.add_argument("--n", type=positive_int, default=1)
        subparser.add_argument("--report-json")
        subparser.add_argument("--dry-run", action="store_true")

    generate = subparsers.add_parser("generate", help="Generate a new image")
    add_common(generate)

    edit = subparsers.add_parser("edit", help="Edit one or more input images")
    add_common(edit)
    edit.add_argument("--image", action="append", required=True)

    return parser.parse_args()


def ensure_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return api_key
    print("OPENAI_API_KEY is missing in the current shell.", file=sys.stderr)
    raise SystemExit(2)


def to_plain(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {key: to_plain(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_plain(value) for value in obj]
    return obj


def pick_number(mapping: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def build_output_paths(out_value: str, count: int, output_format: str) -> list[Path]:
    out_path = Path(out_value)
    allowed_suffixes = {"png": {".png"}, "jpeg": {".jpg", ".jpeg"}, "webp": {".webp"}}
    if not out_path.suffix:
        suffix = ".jpg" if output_format == "jpeg" else f".{output_format}"
        out_path = out_path.with_suffix(suffix)
    elif out_path.suffix.lower() not in allowed_suffixes[output_format]:
        expected = ", ".join(sorted(allowed_suffixes[output_format]))
        raise ValueError(
            f"Output path suffix {out_path.suffix!r} does not match "
            f"--output-format {output_format}; expected {expected}."
        )
    if count == 1:
        return [out_path]
    stem = out_path.stem
    suffix = out_path.suffix
    return [out_path.with_name(f"{stem}-{index}{suffix}") for index in range(1, count + 1)]


def save_images(data_items: list[Any], output_paths: list[Path]) -> list[str]:
    if len(data_items) != len(output_paths):
        raise RuntimeError(
            f"Image response returned {len(data_items)} item(s); "
            f"expected {len(output_paths)}."
        )
    saved_paths: list[str] = []
    for item, output_path in zip(data_items, output_paths):
        record = to_plain(item)
        image_base64 = record.get("b64_json")
        if not image_base64:
            raise RuntimeError("Image response did not include b64_json output.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(image_base64))
        saved_paths.append(str(output_path.resolve()))
    return saved_paths


def summarize_cost(args: argparse.Namespace, response: Any) -> dict[str, Any]:
    response_dict = to_plain(response)
    usage = response_dict.get("usage") or {}
    input_details = to_plain(usage.get("input_tokens_details") or {})
    output_details = to_plain(usage.get("output_tokens_details") or {})

    input_text_tokens = pick_number(
        input_details,
        "input_text_tokens",
        "text_tokens",
        "text",
    )
    input_image_tokens = pick_number(
        input_details,
        "input_image_tokens",
        "image_tokens",
        "image",
    )
    output_image_tokens = pick_number(
        output_details,
        "output_image_tokens",
        "image_tokens",
        "image",
    )

    if output_image_tokens is None:
        output_image_tokens = pick_number(usage, "output_tokens")

    rates = MODEL_TOKEN_RATES.get(args.model)
    exact_output_cost = None
    if rates is not None and output_image_tokens is not None:
        exact_output_cost = output_image_tokens * rates["image_output"]

    exact_total_cost = None
    if (
        rates is not None
        and input_text_tokens is not None
        and input_image_tokens is not None
        and exact_output_cost is not None
    ):
        exact_total_cost = (
            input_text_tokens * rates["text_input"]
            + input_image_tokens * rates["image_input"]
            + exact_output_cost
        )

    per_image_output_cost = (
        OUTPUT_COST_TABLE.get((args.quality, args.size))
        if args.model == "gpt-image-2"
        else None
    )
    table_output_cost = (
        per_image_output_cost * args.n
        if per_image_output_cost is not None
        else None
    )

    if exact_total_cost is not None:
        basis = "exact"
        display_cost = exact_total_cost
    elif exact_output_cost is not None:
        basis = "partial"
        display_cost = exact_output_cost
    elif table_output_cost is not None:
        basis = "estimate"
        display_cost = table_output_cost
    else:
        basis = "unknown"
        display_cost = None

    notes: list[str] = []
    if basis == "partial":
        notes.append("Exact output cost confirmed from API usage; total request cost was not fully exposed.")
    elif basis == "estimate":
        notes.append(
            "Output-only estimate from the published gpt-image-2 price table; "
            "input tokens are not included."
        )
    elif basis == "unknown":
        notes.append(
            "No supported model rate, usable usage details, or standard output price match was available."
        )

    return {
        "basis": basis,
        "display_cost_usd": round(display_cost, 6) if display_cost is not None else None,
        "exact_total_cost_usd": round(exact_total_cost, 6) if exact_total_cost is not None else None,
        "exact_output_cost_usd": round(exact_output_cost, 6) if exact_output_cost is not None else None,
        "table_output_cost_usd": round(table_output_cost, 6) if table_output_cost is not None else None,
        "pricing_as_of": PRICING_AS_OF,
        "pricing_source": PRICING_SOURCE,
        "usage": usage,
        "notes": notes,
    }


def report_path_for(args: argparse.Namespace, output_paths: list[Path]) -> Path:
    if args.report_json:
        return Path(args.report_json)
    if len(output_paths) == 1:
        return output_paths[0].with_suffix(output_paths[0].suffix + ".cost.json")
    return output_paths[0].parent / "request-cost.json"


def request_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
        "quality": args.quality,
        "output_format": args.output_format,
        "n": args.n,
    }
    if args.mode == "edit":
        payload["image_count"] = len(args.image)
    return payload


def print_summary(summary: dict[str, Any]) -> None:
    print(f"Model: {summary['model']}")
    print(f"Mode: {summary['mode']}")
    print(f"Saved: {', '.join(summary['saved_paths'])}")
    if summary["cost"]["display_cost_usd"] is None:
        print("Cost: unavailable")
    else:
        print(f"Cost: ${summary['cost']['display_cost_usd']:.4f}")
    print(f"Basis: {summary['cost']['basis']}")
    for note in summary["cost"]["notes"]:
        print(f"Note: {note}")


def main() -> None:
    args = parse_args()
    try:
        output_paths = build_output_paths(args.out, args.n, args.output_format)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    payload = request_payload(args)

    if args.dry_run:
        per_image_output_cost = (
            OUTPUT_COST_TABLE.get((args.quality, args.size))
            if args.model == "gpt-image-2"
            else None
        )
        table_output_cost = (
            per_image_output_cost * args.n
            if per_image_output_cost is not None
            else None
        )
        summary = {
            "mode": args.mode,
            "model": args.model,
            "saved_paths": [str(path.resolve()) for path in output_paths],
            "request": payload,
            "cost": {
                "basis": "estimate" if table_output_cost is not None else "unknown",
                "display_cost_usd": table_output_cost,
                "exact_total_cost_usd": None,
                "exact_output_cost_usd": None,
                "table_output_cost_usd": table_output_cost,
                "pricing_as_of": PRICING_AS_OF,
                "pricing_source": PRICING_SOURCE,
                "usage": {},
                "notes": (
                    [
                        "Dry run only. No API call was made.",
                        "Estimate covers output images only; input tokens are not included.",
                    ]
                    if table_output_cost is not None
                    else [
                        "Dry run only. No API call was made.",
                        "No static estimate is available for this model, size, or quality.",
                    ]
                ),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": 0.0,
        }
        report_path = report_path_for(args, output_paths)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print_summary(summary)
        return

    ensure_api_key()
    try:
        from openai import OpenAI
    except ImportError as error:
        print(
            "The 'openai' package is required for live API calls. "
            "Install it in an isolated environment.",
            file=sys.stderr,
        )
        raise SystemExit(3) from error

    started = time.time()
    client = OpenAI()

    if args.mode == "generate":
        response = client.images.generate(
            model=args.model,
            prompt=args.prompt,
            size=args.size,
            quality=args.quality,
            output_format=args.output_format,
            n=args.n,
        )
    else:
        with ExitStack() as stack:
            image_handles = [stack.enter_context(open(path, "rb")) for path in args.image]
            response = client.images.edit(
                model=args.model,
                image=image_handles,
                prompt=args.prompt,
                size=args.size,
                quality=args.quality,
                output_format=args.output_format,
                n=args.n,
            )

    saved_paths = save_images(to_plain(response.data), output_paths)
    elapsed = round(time.time() - started, 3)
    cost = summarize_cost(args, response)

    summary = {
        "mode": args.mode,
        "model": args.model,
        "saved_paths": saved_paths,
        "request": payload,
        "cost": cost,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
    }

    report_path = report_path_for(args, output_paths)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print_summary(summary)


if __name__ == "__main__":
    main()

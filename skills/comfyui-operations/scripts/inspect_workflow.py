#!/usr/bin/env python3
"""Inspect ComfyUI workflow JSON or metadata embedded in a PNG."""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from pathlib import Path
from typing import Any


def read_png_text(path: Path) -> dict[str, str]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG file: {path}")
    result: dict[str, str] = {}
    offset = 8
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"tEXt" and b"\0" in payload:
            key, value = payload.split(b"\0", 1)
            result[key.decode("latin-1")] = value.decode("utf-8", "replace")
        elif kind == b"zTXt" and b"\0" in payload:
            key, value = payload.split(b"\0", 1)
            if value[:1] == b"\0":
                result[key.decode("latin-1")] = zlib.decompress(value[1:]).decode(
                    "utf-8", "replace"
                )
        elif kind == b"IEND":
            break
    return result


def load_artifact(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".png":
        text = read_png_text(path)
        loaded: dict[str, Any] = {"source": str(path), "metadata_keys": sorted(text)}
        for key in ("prompt", "workflow"):
            if key in text:
                try:
                    loaded[key] = json.loads(text[key])
                except json.JSONDecodeError:
                    loaded[key] = text[key]
        return loaded
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, dict) and "prompt" in raw and isinstance(raw["prompt"], dict):
        return {"source": str(path), "prompt": raw["prompt"], "raw": raw}
    if is_api_prompt(raw):
        return {"source": str(path), "prompt": raw, "raw": raw}
    return {"source": str(path), "workflow": raw, "raw": raw}


def is_api_prompt(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and bool(value)
        and all(
            isinstance(node, dict) and isinstance(node.get("class_type"), str)
            for node in value.values()
        )
    )


def summarize_prompt(prompt: dict[str, Any]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    for node_id, node in prompt.items():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {})
        item: dict[str, Any] = {
            "id": str(node_id),
            "type": node.get("class_type"),
            "title": node.get("_meta", {}).get("title"),
        }
        selected = {}
        for key in (
            "ckpt_name", "vae_name", "text", "seed", "steps", "cfg",
            "sampler_name", "scheduler", "denoise", "width", "height",
            "batch_size", "filename_prefix",
        ):
            if key in inputs:
                value = inputs[key]
                if key == "text" and isinstance(value, str):
                    value = {"characters": len(value), "value": value}
                selected[key] = value
        links = {key: value for key, value in inputs.items() if is_link(value)}
        if selected:
            item["inputs"] = selected
        if links:
            item["links"] = links
        nodes.append(item)
    return {"node_count": len(nodes), "nodes": nodes}


def is_link(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], (str, int))
        and isinstance(value[1], int)
    )


def normalized_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"source": artifact["source"]}
    if "metadata_keys" in artifact:
        result["metadata_keys"] = artifact["metadata_keys"]
    prompt = artifact.get("prompt")
    if isinstance(prompt, dict):
        result["api_prompt"] = summarize_prompt(prompt)
    workflow = artifact.get("workflow")
    if isinstance(workflow, dict):
        nodes = workflow.get("nodes")
        result["workflow"] = {
            "node_count": len(nodes) if isinstance(nodes, list) else None,
            "link_count": len(workflow.get("links", []))
            if isinstance(workflow.get("links"), list)
            else None,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    summaries = [normalized_summary(load_artifact(path)) for path in args.artifacts]
    output: Any = summaries[0] if len(summaries) == 1 else summaries
    print(json.dumps(output, ensure_ascii=False, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)

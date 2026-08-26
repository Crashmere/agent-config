#!/usr/bin/env python3
"""Submit a ComfyUI API prompt and wait for its outputs."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


SAMPLER_TYPES = {
    "KSampler",
    "KSamplerAdvanced",
    "SamplerCustom",
    "SamplerCustomAdvanced",
}


def request_json(url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt_json", type=Path)
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--poll-interval", type=float, default=1)
    parser.add_argument("--download-dir", type=Path)
    parser.add_argument(
        "--require-execution",
        action="store_true",
        help="fail if every critical generation node was returned from cache",
    )
    parser.add_argument(
        "--require-node",
        action="append",
        default=[],
        metavar="NODE_ID",
        help="node that must execute; repeat for multiple critical nodes",
    )
    args = parser.parse_args()

    base = args.server.rstrip("/")
    loaded = json.loads(args.prompt_json.read_text(encoding="utf-8-sig"))
    prompt = loaded.get("prompt", loaded) if isinstance(loaded, dict) else loaded
    if not isinstance(prompt, dict):
        raise ValueError("prompt JSON must be an API-format object or contain a prompt object")

    submitted = request_json(
        base + "/prompt", {"prompt": prompt, "client_id": str(uuid.uuid4())}
    )
    prompt_id = submitted["prompt_id"]
    deadline = time.monotonic() + args.timeout
    record: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        history = request_json(base + "/history/" + urllib.parse.quote(prompt_id))
        if prompt_id in history:
            record = history[prompt_id]
            if record.get("status", {}).get("completed"):
                break
        time.sleep(args.poll_interval)
    if record is None or not record.get("status", {}).get("completed"):
        raise TimeoutError(f"prompt {prompt_id} did not complete within {args.timeout}s")

    messages = record.get("status", {}).get("messages", [])
    cached = []
    for event in messages:
        if isinstance(event, list) and len(event) == 2 and event[0] == "execution_cached":
            cached.extend(event[1].get("nodes", []))
    cached_set = {str(node_id) for node_id in cached}
    explicit_required_nodes = {str(node_id) for node_id in args.require_node}
    required_nodes = set(explicit_required_nodes)
    if args.require_execution and not explicit_required_nodes:
        required_nodes = {
            str(node_id)
            for node_id, node in prompt.items()
            if isinstance(node, dict) and node.get("class_type") in SAMPLER_TYPES
        }
    executed_required_nodes = sorted(required_nodes - cached_set)
    if not args.require_execution:
        execution_verified = True
    elif explicit_required_nodes:
        execution_verified = explicit_required_nodes.isdisjoint(cached_set)
    else:
        execution_verified = bool(required_nodes) and bool(executed_required_nodes)

    images = []
    for node_id, output in record.get("outputs", {}).items():
        for image in output.get("images", []):
            item = {"node_id": node_id, **image}
            query = urllib.parse.urlencode(
                {
                    "filename": image["filename"],
                    "subfolder": image.get("subfolder", ""),
                    "type": image.get("type", "output"),
                }
            )
            view_url = base + "/view?" + query
            try:
                with urllib.request.urlopen(view_url, timeout=30) as response:
                    content = response.read()
                    item["http_status"] = response.status
            except urllib.error.HTTPError as error:
                content = b""
                item["http_status"] = error.code
            if args.download_dir and content:
                args.download_dir.mkdir(parents=True, exist_ok=True)
                destination = args.download_dir / image["filename"]
                destination.write_bytes(content)
                item["downloaded_to"] = str(destination)
            images.append(item)

    result = {
        "prompt_id": prompt_id,
        "status": record.get("status", {}).get("status_str"),
        "cached_nodes": cached,
        "required_execution_nodes": sorted(required_nodes),
        "executed_required_nodes": executed_required_nodes,
        "execution_verified": execution_verified,
        "images": images,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return (
        0
        if result["status"] == "success"
        and execution_verified
        and bool(images)
        and all(image.get("http_status") == 200 for image in images)
        else 1
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TimeoutError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)

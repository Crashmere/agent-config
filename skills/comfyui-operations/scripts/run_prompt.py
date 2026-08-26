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
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


SAMPLER_TYPES = {
    "KSampler",
    "KSamplerAdvanced",
    "SamplerCustom",
    "SamplerCustomAdvanced",
}


def node_links(node: dict[str, Any], prompt: dict[str, Any]) -> set[str]:
    """Return direct upstream node IDs referenced by a prompt node."""
    links: set[str] = set()
    inputs = node.get("inputs", {})
    if not isinstance(inputs, dict):
        return links
    for value in inputs.values():
        if isinstance(value, list) and len(value) == 2:
            upstream = str(value[0])
            if upstream in prompt and isinstance(value[1], int):
                links.add(upstream)
    return links


def output_ancestors(prompt: dict[str, Any], output_nodes: set[str]) -> set[str]:
    """Return nodes that contribute to one of the outputs in this history record."""
    ancestors: set[str] = set()
    pending = list(output_nodes)
    while pending:
        node_id = pending.pop()
        if node_id in ancestors:
            continue
        node = prompt.get(node_id)
        if not isinstance(node, dict):
            continue
        ancestors.add(node_id)
        pending.extend(node_links(node, prompt) - ancestors)
    return ancestors


def execution_events(messages: list[Any]) -> tuple[set[str], set[str]]:
    """Extract cached nodes and any explicit per-node execution evidence."""
    cached: set[str] = set()
    executed: set[str] = set()
    for event in messages:
        if not isinstance(event, list) or len(event) != 2 or not isinstance(event[1], dict):
            continue
        event_name, data = event
        if event_name == "execution_cached":
            cached.update(str(node_id) for node_id in data.get("nodes", []))
        elif event_name in {"executing", "executed"} and data.get("node") is not None:
            executed.add(str(data["node"]))
    return cached, executed


def safe_download_destination(root: Path, image: dict[str, Any]) -> Path:
    """Build a non-traversing local path for a ComfyUI image response."""
    filename = image.get("filename")
    subfolder = image.get("subfolder", "")
    if not isinstance(filename, str) or not filename:
        raise ValueError("image filename must be a non-empty string")
    if not isinstance(subfolder, str):
        raise ValueError("image subfolder must be a string")

    filename_posix = PurePosixPath(filename)
    filename_windows = PureWindowsPath(filename)
    if (
        filename_posix.is_absolute()
        or filename_windows.is_absolute()
        or filename_posix.name != filename
        or filename_windows.name != filename
        or filename in {".", ".."}
    ):
        raise ValueError(f"unsafe image filename: {filename!r}")

    subfolder_posix = PurePosixPath(subfolder)
    subfolder_windows = PureWindowsPath(subfolder)
    if (
        subfolder_posix.is_absolute()
        or subfolder_windows.is_absolute()
        or subfolder_windows.drive
        or any(part in {"..", ""} for part in subfolder_posix.parts)
        or any(part == ".." for part in subfolder_windows.parts)
    ):
        raise ValueError(f"unsafe image subfolder: {subfolder!r}")

    relative = Path(*subfolder_posix.parts, filename)
    resolved_root = root.resolve()
    destination = (resolved_root / relative).resolve()
    try:
        destination.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError("image destination escapes download directory") from error
    return destination


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
        "--overwrite",
        action="store_true",
        help="replace existing downloaded files (disabled by default)",
    )
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
    if args.overwrite and args.download_dir is None:
        parser.error("--overwrite requires --download-dir")

    base = args.server.rstrip("/")
    loaded = json.loads(args.prompt_json.read_text(encoding="utf-8-sig"))
    prompt = loaded.get("prompt", loaded) if isinstance(loaded, dict) else loaded
    if not isinstance(prompt, dict):
        raise ValueError("prompt JSON must be an API-format object or contain a prompt object")
    prompt = {str(node_id): node for node_id, node in prompt.items()}

    explicit_required_nodes = {str(node_id) for node_id in args.require_node}
    missing_required_nodes = sorted(explicit_required_nodes - prompt.keys())
    if missing_required_nodes:
        raise ValueError(
            "required node(s) not found in submitted prompt: "
            + ", ".join(missing_required_nodes)
        )
    require_execution = args.require_execution or bool(explicit_required_nodes)

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
    cached_set, event_executed_nodes = execution_events(messages)
    output_nodes = {str(node_id) for node_id in record.get("outputs", {})}
    ancestors = output_ancestors(prompt, output_nodes)
    required_nodes = set(explicit_required_nodes)
    if require_execution and not explicit_required_nodes:
        required_nodes = {
            str(node_id)
            for node_id, node in prompt.items()
            if isinstance(node, dict) and node.get("class_type") in SAMPLER_TYPES
        } & ancestors
    unreachable_required_nodes = sorted(explicit_required_nodes - ancestors)
    if unreachable_required_nodes:
        raise ValueError(
            "required node(s) do not contribute to returned outputs: "
            + ", ".join(unreachable_required_nodes)
        )

    # A successful returned descendant plus absence from the authoritative cache event
    # is the strongest evidence available from the history API when it omits per-node
    # events. Preserve direct events separately when the server supplies them.
    successful = record.get("status", {}).get("status_str") == "success"
    inferred_executed_nodes = (ancestors - cached_set) if output_nodes and successful else set()
    evidenced_executed_nodes = (event_executed_nodes | inferred_executed_nodes) - cached_set
    executed_required_nodes = sorted(required_nodes & evidenced_executed_nodes)
    if not require_execution:
        execution_verified = True
    elif explicit_required_nodes:
        execution_verified = explicit_required_nodes <= evidenced_executed_nodes
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
                destination = safe_download_destination(args.download_dir, image)
                destination.parent.mkdir(parents=True, exist_ok=True)
                mode = "wb" if args.overwrite else "xb"
                try:
                    with destination.open(mode) as output_file:
                        output_file.write(content)
                except FileExistsError as error:
                    raise FileExistsError(
                        f"refusing to overwrite existing file: {destination}"
                    ) from error
                item["downloaded_to"] = str(destination)
            images.append(item)

    result = {
        "prompt_id": prompt_id,
        "status": record.get("status", {}).get("status_str"),
        "cached_nodes": sorted(cached_set),
        "required_execution_nodes": sorted(required_nodes),
        "executed_required_nodes": executed_required_nodes,
        "direct_execution_event_nodes": sorted(event_executed_nodes),
        "output_ancestor_nodes": sorted(ancestors),
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

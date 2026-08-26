#!/usr/bin/env python3
"""Offline regression tests for run_prompt.py."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
from unittest import mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_prompt.py"
SPEC = importlib.util.spec_from_file_location("run_prompt", SCRIPT)
assert SPEC and SPEC.loader
RUN_PROMPT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN_PROMPT)


class MockComfyUIServer:
    def __init__(
        self,
        *,
        cached: list[str] | None = None,
        image: dict[str, Any] | None = None,
        output_node: str = "3",
    ) -> None:
        self.cached = cached or []
        self.image = image or {"filename": "result.png", "type": "output"}
        self.output_node = output_node
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                self._reply_json({"prompt_id": "test-prompt"})

            def do_GET(self) -> None:  # noqa: N802
                if self.path.startswith("/history/test-prompt"):
                    messages: list[Any] = []
                    if owner.cached:
                        messages.append(
                            ["execution_cached", {"nodes": owner.cached}]
                        )
                    self._reply_json(
                        {
                            "test-prompt": {
                                "status": {
                                    "completed": True,
                                    "status_str": "success",
                                    "messages": messages,
                                },
                                "outputs": {
                                    owner.output_node: {"images": [owner.image]}
                                },
                            }
                        }
                    )
                elif self.path.startswith("/view?"):
                    content = b"mock-png"
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_error(404)

            def _reply_json(self, value: Any) -> None:
                content = json.dumps(value).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            def log_message(self, format: str, *args: Any) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> "MockComfyUIServer":
        self.thread.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class RunPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.prompt_file = self.root / "prompt.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_prompt(self, prompt: dict[str, Any] | None = None) -> None:
        prompt = prompt or {
            "1": {"class_type": "KSampler", "inputs": {}},
            "2": {"class_type": "KSamplerAdvanced", "inputs": {}},
            "3": {
                "class_type": "SaveImage",
                "inputs": {"images": ["1", 0], "aux": ["2", 0]},
            },
        }
        self.prompt_file.write_text(json.dumps(prompt), encoding="utf-8")

    def run_main(
        self, server: MockComfyUIServer, *arguments: str
    ) -> tuple[int, dict[str, Any]]:
        argv = [
            str(SCRIPT),
            str(self.prompt_file),
            "--server",
            server.url,
            "--poll-interval",
            "0",
            *arguments,
        ]
        output = io.StringIO()
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(
            output
        ):
            code = RUN_PROMPT.main()
        return code, json.loads(output.getvalue())

    def test_require_node_alone_enables_verification_and_rejects_cached(self) -> None:
        self.write_prompt()
        with MockComfyUIServer(cached=["1"]) as server:
            code, result = self.run_main(server, "--require-node", "1")
        self.assertEqual(code, 1)
        self.assertFalse(result["execution_verified"])

    def test_nonexistent_required_node_is_rejected_before_submission(self) -> None:
        self.write_prompt()
        with MockComfyUIServer() as server:
            with self.assertRaisesRegex(ValueError, "not found.*999"):
                self.run_main(server, "--require-node", "999")

    def test_required_node_outside_output_graph_is_rejected(self) -> None:
        self.write_prompt(
            {
                "1": {"class_type": "KSampler", "inputs": {}},
                "2": {"class_type": "KSampler", "inputs": {}},
                "3": {"class_type": "SaveImage", "inputs": {"images": ["1", 0]}},
            }
        )
        with MockComfyUIServer() as server:
            with self.assertRaisesRegex(ValueError, "do not contribute.*2"):
                self.run_main(server, "--require-node", "2")

    def test_automatic_multi_sampler_accepts_one_executed_sampler(self) -> None:
        self.write_prompt()
        with MockComfyUIServer(cached=["1"]) as server:
            code, result = self.run_main(server, "--require-execution")
        self.assertEqual(code, 0)
        self.assertTrue(result["execution_verified"])
        self.assertEqual(result["executed_required_nodes"], ["2"])

    def test_explicit_multi_node_requires_every_node(self) -> None:
        self.write_prompt()
        with MockComfyUIServer(cached=["1"]) as server:
            code, result = self.run_main(
                server, "--require-node", "1", "--require-node", "2"
            )
        self.assertEqual(code, 1)
        self.assertFalse(result["execution_verified"])

    def test_download_preserves_safe_subfolder(self) -> None:
        self.write_prompt()
        image = {"filename": "result.png", "subfolder": "batch/one"}
        download = self.root / "downloads"
        with MockComfyUIServer(image=image) as server:
            code, result = self.run_main(
                server, "--download-dir", str(download)
            )
        expected = download / "batch" / "one" / "result.png"
        self.assertEqual(code, 0)
        self.assertEqual(expected.read_bytes(), b"mock-png")
        self.assertEqual(
            Path(result["images"][0]["downloaded_to"]), expected.resolve()
        )

    def test_download_rejects_absolute_filename(self) -> None:
        self.write_prompt()
        with MockComfyUIServer(image={"filename": "/tmp/result.png"}) as server:
            with self.assertRaisesRegex(ValueError, "unsafe image filename"):
                self.run_main(server, "--download-dir", str(self.root / "downloads"))

    def test_download_rejects_windows_absolute_filename(self) -> None:
        self.write_prompt()
        with MockComfyUIServer(image={"filename": "C:\\temp\\result.png"}) as server:
            with self.assertRaisesRegex(ValueError, "unsafe image filename"):
                self.run_main(server, "--download-dir", str(self.root / "downloads"))

    def test_download_rejects_filename_traversal(self) -> None:
        self.write_prompt()
        with MockComfyUIServer(image={"filename": "../result.png"}) as server:
            with self.assertRaisesRegex(ValueError, "unsafe image filename"):
                self.run_main(server, "--download-dir", str(self.root / "downloads"))

    def test_download_rejects_subfolder_traversal(self) -> None:
        self.write_prompt()
        image = {"filename": "result.png", "subfolder": "../outside"}
        with MockComfyUIServer(image=image) as server:
            with self.assertRaisesRegex(ValueError, "unsafe image subfolder"):
                self.run_main(server, "--download-dir", str(self.root / "downloads"))

    def test_download_refuses_existing_file_and_overwrite_is_explicit(self) -> None:
        self.write_prompt()
        download = self.root / "downloads"
        download.mkdir()
        destination = download / "result.png"
        destination.write_bytes(b"old")
        with MockComfyUIServer() as server:
            with self.assertRaises(FileExistsError):
                self.run_main(server, "--download-dir", str(download))
            code, _ = self.run_main(
                server, "--download-dir", str(download), "--overwrite"
            )
        self.assertEqual(code, 0)
        self.assertEqual(destination.read_bytes(), b"mock-png")


if __name__ == "__main__":
    unittest.main()

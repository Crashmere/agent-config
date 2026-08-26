#!/usr/bin/env python3
"""Offline regression tests for openai_image_with_cost.py."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "openai_image_with_cost.py"
SPEC = importlib.util.spec_from_file_location("openai_image_with_cost", SCRIPT)
assert SPEC and SPEC.loader
IMAGE_COST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMAGE_COST)


class OpenAIImageWithCostTests(unittest.TestCase):
    def cost_args(self) -> argparse.Namespace:
        return argparse.Namespace(
            model="gpt-image-2", quality="high", size="1024x1024", n=1
        )

    def run_dry_run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.pop("OPENAI_API_KEY", None)
        return subprocess.run(
            [sys.executable, str(SCRIPT), "generate", "--prompt", "test", *arguments, "--dry-run"],
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )

    def test_dry_run_refuses_existing_report_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "image.png"
            report = Path(str(output) + ".cost.json")
            report.write_text("sentinel", encoding="utf-8")

            result = self.run_dry_run("--out", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to overwrite", result.stderr)
            self.assertEqual(report.read_text(encoding="utf-8"), "sentinel")

    def test_dry_run_overwrite_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "image.png"
            report = Path(str(output) + ".cost.json")
            report.write_text("sentinel", encoding="utf-8")

            result = self.run_dry_run("--out", str(output), "--overwrite")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["mode"], "generate")

    def test_multi_image_report_uses_output_prefix(self) -> None:
        args = argparse.Namespace(report_json=None)
        outputs = IMAGE_COST.build_output_paths("album.png", 3, "png")

        self.assertEqual(
            IMAGE_COST.report_path_for(args, outputs),
            Path("album.cost.json"),
        )

    def test_image_write_refuses_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "image.png"
            output.write_bytes(b"old")

            with self.assertRaises(FileExistsError):
                IMAGE_COST.save_images([{"b64_json": "bmV3"}], [output], False)

            self.assertEqual(output.read_bytes(), b"old")

    def test_atomic_overwrite_preserves_old_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "image.png"
            output.write_bytes(b"old")

            with mock.patch.object(IMAGE_COST.os, "replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    IMAGE_COST.atomic_write_bytes(output, b"new", True)

            self.assertEqual(output.read_bytes(), b"old")
            self.assertEqual(list(Path(directory).glob(".image.png.*")), [])

    def test_exact_cost_requires_and_prices_cached_input_details(self) -> None:
        response = {
            "usage": {
                "input_tokens_details": {
                    "text_tokens": 100,
                    "image_tokens": 200,
                    "cached_text_tokens": 40,
                    "cached_image_tokens": 50,
                },
                "output_tokens_details": {"image_tokens": 300},
            }
        }

        cost = IMAGE_COST.summarize_cost(self.cost_args(), response)

        self.assertEqual(cost["basis"], "exact")
        self.assertEqual(cost["display_cost_usd"], 0.01065)

    def test_missing_cache_details_downgrades_total_to_partial(self) -> None:
        response = {
            "usage": {
                "input_tokens_details": {"text_tokens": 100, "image_tokens": 200},
                "output_tokens_details": {"image_tokens": 300},
            }
        }

        cost = IMAGE_COST.summarize_cost(self.cost_args(), response)

        self.assertEqual(cost["basis"], "partial")
        self.assertEqual(cost["display_cost_usd"], 0.009)
        self.assertIsNone(cost["exact_total_cost_usd"])

    def test_invalid_cached_counts_are_rejected(self) -> None:
        response = {
            "usage": {
                "input_tokens_details": {
                    "text_tokens": 10,
                    "image_tokens": 0,
                    "cached_text_tokens": 11,
                    "cached_image_tokens": 0,
                },
                "output_tokens": 1,
            }
        }

        with self.assertRaisesRegex(ValueError, "cached input token counts"):
            IMAGE_COST.summarize_cost(self.cost_args(), response)


if __name__ == "__main__":
    unittest.main()

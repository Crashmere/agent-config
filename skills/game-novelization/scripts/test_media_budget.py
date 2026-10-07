"""Exercise CLI budgeting and failure paths without images or model requests."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("check-media-budget.py")
MIB = 1024 * 1024


class MediaBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.retained = self.root / "retained.txt"
        self.pending = self.root / "next.txt"
        self.retained.write_text("")

    def image(self, name, size):
        path = self.root / name
        with path.open("wb") as stream:
            stream.truncate(size)
        return path

    def run_check(self, *extra):
        return subprocess.run([
            sys.executable, str(SCRIPT), "--retained", str(self.retained),
            "--next", str(self.pending), *extra,
        ], capture_output=True, text=True, check=False)

    def test_small_batch_and_relative_unicode_paths(self):
        self.image("场景 1.jpg", 1024)
        self.pending.write_text("场景 1.jpg\n", encoding="utf-8")
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["allowed"])
        self.assertEqual(data["next"]["encoded_bytes"], 4 * 342 + 512)
        self.assertEqual(self.retained.read_text(), "")
        self.assertEqual(self.pending.read_text(), "场景 1.jpg\n")

    def test_repeated_embeddings_are_not_deduplicated(self):
        path = self.image("same.jpg", MIB)
        self.retained.write_text(f"{path}\n{path}\n")
        self.pending.write_text(f"{path}\n")
        data = json.loads(self.run_check().stdout)
        self.assertEqual(data["retained"]["images"], 2)
        self.assertEqual(data["retained"]["raw_bytes"], 2 * MIB)
        self.assertEqual(data["projected_request_bytes"], 3 * (4 * ((MIB + 2) // 3) + 512) + 8 * MIB)

    def test_large_parallel_batch_is_rejected(self):
        path = self.image("sheet.jpg", 2 * MIB)
        self.pending.write_text(f"{path}\n" * 12)
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(set(json.loads(result.stdout)["violations"]),
                         {"batch_image_count", "batch_media_bytes", "request_estimate_bytes"})

    def test_small_batch_can_overflow_retained_context(self):
        path = self.image("sheet.jpg", 2 * MIB)
        self.retained.write_text(f"{path}\n" * 11)
        self.pending.write_text(f"{path}\n" * 2)
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["violations"], ["request_estimate_bytes"])

    def test_fewer_images_can_still_exceed_byte_budget(self):
        path = self.image("large.png", 7 * MIB)
        self.pending.write_text(f"{path}\n")
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["violations"], ["batch_media_bytes"])

    def test_invalid_or_missing_input_fails_closed(self):
        for entry in ["missing.jpg\n", f"{self.root}\n", ""]:
            with self.subTest(entry=entry):
                self.pending.write_text(entry)
                result = self.run_check()
                self.assertEqual(result.returncode, 2)
                self.assertFalse(json.loads(result.stdout)["allowed"])
        self.retained.unlink()
        self.assertEqual(self.run_check().returncode, 2)

    def test_invalid_limits_are_rejected(self):
        for args in [("--batch-mib", "nan"), ("--request-mib", "inf"),
                     ("--max-images", "0"), ("--reserve-mib", "40")]:
            with self.subTest(args=args):
                self.assertEqual(self.run_check(*args).returncode, 2)


if __name__ == "__main__":
    unittest.main()

"""Small local media fixtures; no network, third-party Python packages or user files."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CHECKER = Path(__file__).with_name("verify_media.py")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools required")
class MediaVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="yt-dlp-verifier-test-")
        cls.root = Path(cls.workspace.name)
        cls.raw = cls.root / "raw.mp4"
        cls.media = cls.root / "video [with spaces].mp4"
        cls.video_only = cls.root / "video-only.mp4"
        cls.source = {"duration": 3, "chapters": [
            {"title": "开场", "start_time": 0, "end_time": 1.5},
            {"title": "结束", "start_time": 1.5, "end_time": 3},
        ]}
        cls.info = cls.root / "source.json"
        cls.info.write_text(json.dumps(cls.source), encoding="utf-8")
        metadata = cls.root / "chapters.ffmetadata"
        metadata.write_text(";FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=1500\n"
                            "title=开场\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=1500\nEND=3000\ntitle=结束\n",
                            encoding="utf-8")
        cls.ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=320x180:r=30:d=3",
                   "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
                   "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(cls.raw))
        cls.ffmpeg("-i", str(cls.raw), "-f", "ffmetadata", "-i", str(metadata),
                   "-map", "0:v:0", "-map", "0:a:0", "-map_chapters", "1",
                   "-c", "copy", "-movie_timescale", "1000", str(cls.media))
        cls.ffmpeg("-i", str(cls.raw), "-map", "0:v:0", "-c", "copy", str(cls.video_only))

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    @staticmethod
    def ffmpeg(*args):
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", *args],
                       check=True, capture_output=True, text=True, timeout=30)

    def check_media(self, path, success, *args, env=None):
        result = subprocess.run([sys.executable, str(CHECKER), str(path), *args],
                                capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        report = json.loads(result.stdout if success else result.stderr)
        self.assertEqual(report["ok"], success)
        return report

    def test_valid_media_and_source_chapters(self):
        report = self.check_media(self.media, True, "--info-json", str(self.info),
                                  "--width", "320", "--height", "180", "--fps", "30")
        self.assertTrue(report["source_chapters_compared"])
        self.assertEqual(report["chapter_count"], 2)
        self.assertGreater(report["tail_decode"]["video_frames"], 0)

    def test_same_count_wrong_chapter_title(self):
        source = json.loads(json.dumps(self.source))
        source["chapters"][0]["title"] = "不同标题"
        path = self.root / "wrong-title.json"
        path.write_text(json.dumps(source))
        report = self.check_media(self.media, False, "--info-json", str(path))
        self.assertIn("title mismatch", report["error"])

    def test_long_chapters_with_explicit_mp4_timescale(self):
        raw = self.root / "long-raw.mp4"
        output = self.root / "long-chapters.mp4"
        metadata = self.root / "long-chapters.ffmetadata"
        info = self.root / "long-source.json"
        metadata.write_text(";FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=200000\n"
                            "title=First\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=200000\nEND=300000\ntitle=Last\n")
        info.write_text(json.dumps({"duration": 300, "chapters": [
            {"title": "First", "start_time": 0, "end_time": 200},
            {"title": "Last", "start_time": 200, "end_time": 300},
        ]}))
        self.ffmpeg("-f", "lavfi", "-i", "color=c=black:s=16x16:r=1:d=300",
                    "-f", "lavfi", "-i", "sine=sample_rate=44100:duration=300",
                    "-c:v", "libx264", "-preset", "ultrafast", "-video_track_timescale", "15360",
                    "-c:a", "aac", "-shortest", str(raw))
        self.ffmpeg("-i", str(raw), "-f", "ffmetadata", "-i", str(metadata),
                    "-map", "0:v:0", "-map", "0:a:0", "-map_chapters", "1",
                    "-c", "copy", "-movie_timescale", "1000", str(output))
        report = self.check_media(output, True, "--info-json", str(info))
        self.assertEqual(report["chapter_count"], 2)

    def test_same_count_wrong_chapter_time(self):
        source = json.loads(json.dumps(self.source))
        source["chapters"][0]["end_time"] = 1
        source["chapters"][1]["start_time"] = 1
        path = self.root / "wrong-time.json"
        path.write_text(json.dumps(source))
        report = self.check_media(self.media, False, "--info-json", str(path))
        self.assertIn("end_time mismatch", report["error"])

    def test_duration_dimensions_and_chapter_count(self):
        for arguments in (("--expect-duration", "30"), ("--width", "1920"),
                          ("--fps", "60"), ("--expect-chapters", "28")):
            with self.subTest(arguments=arguments):
                self.check_media(self.media, False, *arguments)

    def test_missing_audio_and_explicit_video_only(self):
        self.check_media(self.video_only, False)
        self.check_media(self.video_only, True, "--streams", "video", "--expect-duration", "3")

    def test_partial_and_control_file(self):
        part = self.root / "unfinished.mp4.part"
        part.write_bytes(b"partial")
        self.check_media(part, False)
        control = Path(str(self.media) + ".aria2")
        try:
            control.write_bytes(b"in-progress")
            self.check_media(self.media, False)
        finally:
            control.unlink()

    def test_truncated_media(self):
        path = self.root / "truncated.mp4"
        path.write_bytes(self.media.read_bytes()[:128])
        self.check_media(path, False)

    def test_invalid_source_duration(self):
        path = self.root / "invalid-source.json"
        path.write_text('{"duration":NaN}')
        self.check_media(self.media, False, "--info-json", str(path))

    def test_success_exit_without_decoded_output(self):
        directory = self.root / "fake-bin"
        directory.mkdir()
        program = directory / "ffmpeg"
        program.write_text('#!/bin/sh\nprintf "frame=0\\nout_time_us=0\\nprogress=end\\n"\n')
        program.chmod(0o755)
        env = dict(os.environ)
        env["PATH"] = str(directory) + os.pathsep + env.get("PATH", "")
        report = self.check_media(self.media, False, env=env)
        self.assertIn("no completed output", report["error"])


if __name__ == "__main__":
    unittest.main()

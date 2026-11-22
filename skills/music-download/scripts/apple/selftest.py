"""Focused synthetic checks; run packaging and metadata cases in their existing environments."""

import asyncio
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lyrics import select_bundle, write_bundle

PLAIN = '<tt xmlns="http://www.w3.org/ns/ttml" xml:lang="en"><body><p>First</p><p>Last</p></body></tt>'
TIMED = PLAIN.replace('<p>', '<p begin="0s">', 1).replace('<p>Last', '<p begin="1s">Last')


class LyricsTests(unittest.TestCase):
    def test_enhanced_timing_beats_plain_standard_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            write_bundle(PLAIN, directory)
            write_bundle(TIMED, directory, enhanced=True)
            selected = select_bundle(directory)
            self.assertEqual(selected["name"], "lyrics-enhanced")
            self.assertEqual(selected["timed_lines"], 2)


class PackagingTests(unittest.TestCase):
    def test_timed_fallback_and_plain_only_tags_preserve_recording_format(self):
        from mutagen.flac import FLAC

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.2",
                            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(source)], check=True)
            catalog = root / "catalog.json"
            catalog.write_text(json.dumps({"song": {"id": "1", "attributes": {
                "name": "Fixture", "artistName": "Lead", "albumName": "Demo"}}, "album": {}}))
            for timed in (False, True):
                materials = root / str(timed)
                write_bundle(PLAIN, materials)
                if timed:
                    write_bundle(TIMED, materials, enhanced=True)
                output = root / f"{timed}.flac"
                result = subprocess.run([sys.executable, str(Path(__file__).with_name("package_flac.py")),
                    "--source", str(source), "--catalog", str(catalog), "--song-id", "1",
                    "--lyrics-dir", str(materials), "--output", str(output)], check=True, capture_output=True, text=True)
                receipt = json.loads(result.stdout)
                audio = FLAC(output)
                self.assertEqual((audio.info.sample_rate, audio.info.bits_per_sample, audio.info.channels), (48000, 24, 2))
                self.assertEqual(receipt["lyrics_timed_lines"], 2 if timed else 0)
                self.assertEqual(audio.get("SYNCEDLYRICS") is not None, timed)
                self.assertEqual(audio["LYRICS_ALIGNMENT_STATUS"], ["source_timestamps_unmeasured"])
                self.assertEqual(receipt["title"], "Fixture")


class MaterialFetchTests(unittest.TestCase):
    def run_batch(self, denied=False):
        import fetch_metadata

        requests = []
        class FakeAPI:
            async def __aenter__(self):
                requests.append("session-open")
                return self

            async def __aexit__(self, *_):
                requests.append("session-close")

            async def get_song(self, song_id, **_):
                requests.append("song-" + song_id)
                return {"data": [{"id": song_id, "attributes": {"name": "Fixture"},
                                  "relationships": {"albums": {"data": [{"id": "album"}]}}}]}

            async def get_album(self, *_args, **_kwargs):
                requests.append("album")
                return {"data": [{"id": "album", "attributes": {"name": "Demo"}}]}

        class Denied(Exception):
            status_code = 403

        class FakeSong:
            async def get_lyrics(self, syllable, **_):
                requests.append("enhanced" if syllable else "standard")
                if denied:
                    raise Denied()
                return SimpleNamespace(source_ttml=TIMED if syllable else PLAIN)

        async def create(*_args, **_kwargs):
            return FakeAPI()

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "batch"
            args = SimpleNamespace(song_ids=["1", "2"], song_id=None, album_id=None, cookies=Path("unused"),
                                   storefront="cn", language="zh-CN", metadata_only=False, output_dir=output)
            with patch.object(fetch_metadata.AppleMusicApi, "from_cookies", create), \
                    patch.object(fetch_metadata.Song, "from_metadata", return_value=FakeSong()), redirect_stdout(io.StringIO()):
                if denied:
                    with self.assertRaises(PermissionError):
                        asyncio.run(fetch_metadata.fetch(args))
                    self.assertTrue((output / "1/catalog.json").exists())
                    self.assertFalse((output / "2").exists())
                else:
                    asyncio.run(fetch_metadata.fetch(args))
                    for song_id in ("1", "2"):
                        exported = json.loads((output / song_id / "lyrics.json").read_text())
                        self.assertEqual(exported["timing"], "line_synced")
                        self.assertIn("[00:01.00]Last", exported["lrc"])
        return requests

    def test_batch_reuses_session_and_album_and_exports_timed_variant(self):
        requests = self.run_batch()
        self.assertEqual(requests.count("session-open"), 1)
        self.assertEqual(requests.count("album"), 1)

    def test_authorization_failure_retains_receipt_and_stops_remaining_requests(self):
        requests = self.run_batch(denied=True)
        self.assertNotIn("song-2", requests)
        self.assertNotIn("enhanced", requests)
        self.assertEqual(requests[-1], "session-close")


if __name__ == "__main__":
    unittest.main()

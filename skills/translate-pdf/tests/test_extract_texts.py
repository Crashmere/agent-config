"""Behavior checks for evidence preservation, not semantic segmentation guesses."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pymupdf

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'extract_texts.py'
spec = importlib.util.spec_from_file_location('extract_texts', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExtractionTests(unittest.TestCase):
    def make_source(self, path):
        with pymupdf.open() as doc:
            page = doc.new_page(width=400, height=300)
            # Store bottom text first: neither PDF order nor geometry is treated as semantic truth.
            page.insert_text((30, 230), 'The researchers could')
            page.insert_text((30, 50), 'Report')
            page.insert_text((250, 50), 'Report')
            page.insert_text((30, 90), 'A two-line\nparagraph.')
            page.insert_link({'kind': pymupdf.LINK_URI, 'from': pymupdf.Rect(30, 30, 90, 55),
                              'uri': 'https://example.org/reference'})
            page = doc.new_page(width=400, height=300)
            page.insert_text((30, 50), 'support the project, but success was not observed.')
            page.set_rotation(90)
            page = doc.new_page(width=400, height=300)
            pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 10, 10))
            pix.clear_with(210)
            page.insert_image((30, 40, 100, 110), pixmap=pix)
            doc.save(path)

    def test_structured_preserves_occurrences_order_lines_images_links_and_warnings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.pdf'
            self.make_source(path)
            result = module.extract_document(str(path))
            self.assertEqual(result['source']['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(result['page_count'], 3)
            first, second, third = result['pages']
            spans = [s for b in first['blocks'] for line in b['lines'] for s in line['spans']]
            repeats = [s for s in spans if s['text'] == 'Report']
            self.assertEqual(len(repeats), 2)
            self.assertNotEqual(repeats[0]['id'], repeats[1]['id'])
            self.assertNotEqual(repeats[0]['bbox'], repeats[1]['bbox'])
            self.assertIn('could', first['blocks'][0]['text'])
            self.assertNotEqual(first['blocks'][0]['id'], first['geometric_order_hint'][0])
            self.assertTrue(any('two-line\nparagraph.' in b['text'] for b in first['blocks']))
            self.assertTrue(second['blocks'][0]['text'].startswith('support the project'))
            self.assertEqual(second['rotation'], 90)
            self.assertEqual(first['links'][0]['uri'], 'https://example.org/reference')
            self.assertEqual(len(third['images']), 1)
            self.assertEqual(third['blocks'], [])
            self.assertEqual(result['warnings'][0]['page'], 3)
            self.assertEqual(result, json.loads(json.dumps(result)))

    def test_cli_default_is_contextual_json_and_legacy_mode_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.pdf'
            self.make_source(path)
            run = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(run.stdout)['page_count'], 3)
            legacy = subprocess.run([sys.executable, str(SCRIPT), str(path), '--format', 'strings'],
                                    capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(legacy.stdout).count('Report'), 1)
            self.assertIn('omit context', legacy.stderr)
            before = path.read_bytes()
            rejected = subprocess.run([sys.executable, str(SCRIPT), str(path), '-o', str(path)], capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()

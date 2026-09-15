"""Regressions for PDF text matching, CJK metrics, and retained graphics."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import pymupdf

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'translate_pdf.py'
spec = importlib.util.spec_from_file_location('translate_pdf', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TranslationTests(unittest.TestCase):
    def test_trimmed_keys_keep_images_graphics_links_and_fit_cjk(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = (Path(folder) / name for name in ('source.pdf', 'translated.pdf'))
            doc = pymupdf.open()
            page = doc.new_page(width=400, height=250)
            page.draw_rect((25, 25, 375, 150), fill=(0.8, 0.85, 0.9), color=None)
            pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 10, 10))
            pix.clear_with(210)
            page.insert_image((25, 25, 375, 150), pixmap=pix)
            page.insert_text((40, 60), 'Report title  ', fontsize=16)
            page.insert_text((40, 95), 'Keep this line', fontsize=12)
            page.insert_link({'kind': pymupdf.LINK_URI, 'from': pymupdf.Rect(40, 40, 135, 66),
                              'uri': 'https://example.org/report'})
            doc.save(source)
            doc.close()
            translation = '中文标题 Claude 2026'
            mapping = {'Report title': translation, 'Keep this line': 'Keep this line',
                       'Absent label': 'Unused translation'}
            result = module.translate_pdf(str(source), mapping, str(output), 'china-ss')
            self.assertEqual(result['translated'], 1)
            self.assertEqual(result['unmatched_keys'], ['Absent label'])
            original, translated = pymupdf.open(source), pymupdf.open(output)
            text = translated[0].get_text()
            self.assertIn(translation, text)
            self.assertIn('Keep this line', text)
            self.assertNotIn('Report title', text)
            self.assertEqual(len(translated[0].get_images()), 1)
            self.assertTrue(any(item.get('fill') for item in translated[0].get_drawings()))
            self.assertEqual(translated[0].get_links()[0]['uri'], 'https://example.org/report')
            before = original[0].search_for('Report title')[0]
            after = translated[0].search_for(translation)[0]
            self.assertLessEqual(after.x1, before.x1 + 10)
            self.assertLessEqual(after.y1, before.y1 + 0.5)
            original.close()
            translated.close()

    def test_input_path_is_never_overwritten(self):
        with self.assertRaisesRegex(ValueError, 'new path'):
            module.translate_pdf('same.pdf', {}, 'same.pdf')

    def test_rejects_structured_data_empty_values_and_ambiguous_trimmed_keys(self):
        for mapping in ({'pages': []}, {'Title': ''}, {'Title': '甲', 'Title ': '乙'}):
            with self.subTest(mapping=mapping), self.assertRaises(ValueError):
                module.translate_pdf('unused.pdf', mapping, 'output.pdf')

    def test_tiny_type_is_rejected_without_saving_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = (Path(folder) / name for name in ('source.pdf', 'output.pdf'))
            with pymupdf.open() as doc:
                page = doc.new_page()
                page.insert_text((40, 60), 'Label')
                doc.save(source)
            before = source.read_bytes()
            with self.assertRaisesRegex(ValueError, 'Use paragraph layout'):
                module.translate_pdf(str(source), {'Label': 'This full translation cannot fit the original label.'}, str(output))
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()

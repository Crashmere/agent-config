#!/usr/bin/env python3
"""
Replace self-contained PDF labels using a flat mapping, not prose paragraphs.

Usage:
    python translate_pdf.py <input.pdf> <translations.json> <output.pdf> [--font <fontname>]

Arguments:
    input.pdf         Input PDF file path
    translations.json JSON file with translation mappings: {"original": "translated", ...}
    output.pdf        Output PDF file path
    --font            Font name for target language (default: helv, use china-ss for Chinese, japan for Japanese)
"""

import json
import sys
import argparse
import math
from pathlib import Path

try:
    import pymupdf
except ImportError:
    print("Error: pymupdf not installed. Use python-environment to select an isolated environment with pymupdf.")
    sys.exit(1)


def translate_pdf(input_path: str, translations: dict, output_path: str, fontname: str = "helv",
                  min_font_size: float = 8.0):
    """
    Translate text in PDF using provided translation mappings.

    Args:
        input_path: Path to input PDF
        translations: Dict mapping original text to translated text
        output_path: Path for output PDF
        fontname: Font name for translated text (helv, china-ss, japan, korea, etc.)
        min_font_size: Refuse unreadable fitting below this point size (default 8).
    """
    if Path(input_path).resolve() == Path(output_path).resolve():
        raise ValueError("Save the translation to a new path; do not overwrite the source PDF.")
    if not isinstance(translations, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in translations.items()
    ):
        raise ValueError("Expected a flat string-to-string mapping for labels; structured documents require paragraph layout.")
    if not math.isfinite(min_font_size) or min_font_size <= 0:
        raise ValueError("min_font_size must be a finite positive number.")
    normalized = {}
    for key, value in translations.items():
        key = key.strip()
        if not key or not value.strip():
            raise ValueError("Empty keys or translations are not allowed; retain content explicitly instead of deleting it.")
        if key in normalized and normalized[key] != value:
            raise ValueError(f"Conflicting translations for the same trimmed label: {key!r}")
        normalized[key] = value
    # extract_texts strips spans, so replacement must use the same normalization.
    translations = normalized
    font = pymupdf.Font(fontname)
    doc = pymupdf.open(input_path)

    translated_count = 0
    total_spans = 0
    matched = set()

    for page in doc:
        text_dict = page.get_text("dict")
        replacements = []

        for block in text_dict["blocks"]:
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    total_spans += 1
                    original_text = span.get("text", "").strip()

                    if not original_text.strip():
                        continue

                    if original_text in translations:
                        matched.add(original_text)
                        new_text = translations[original_text]

                        if new_text != original_text:
                            bbox = span["bbox"]
                            font_size = span["size"]
                            color = span.get("color", 0)

                            if isinstance(color, int):
                                r = (color >> 16 & 0xFF) / 255
                                g = (color >> 8 & 0xFF) / 255
                                b = (color & 0xFF) / 255
                                text_color = (r, g, b)
                            else:
                                text_color = (0, 0, 0)

                            # Measure and render with the same embedded font. The PDF
                            # built-in CJK font can use different Latin glyph widths.
                            lines = new_text.splitlines() or [""]
                            scale = 0.9 if fontname in ["china-ss", "china-ts", "japan", "korea"] else 1
                            rect = pymupdf.Rect(bbox)
                            fs = font_size * scale
                            longest = max(font.text_length(line, fontsize=1) for line in lines)
                            if longest:
                                fs = min(fs, rect.width / longest)
                            fs = min(fs, rect.height / (
                                font.ascender - font.descender + 1.35 * (len(lines) - 1)))
                            if fs <= 0:
                                raise ValueError(f"Cannot fit translation on page {page.number + 1}: {original_text!r}")
                            if fs < min_font_size:
                                doc.close()
                                raise ValueError(
                                    f"Translation would require {fs:.2f} pt, below {min_font_size:g} pt. "
                                    "Use paragraph layout; do not shorten the translation to fit."
                                )
                            replacements.append({
                                "bbox": bbox,
                                "new_text": new_text,
                                "font_size": fs,
                                "text_color": text_color
                            })
                            translated_count += 1

        # Step 1: Remove old text with transparent fill
        for repl in replacements:
            rect = pymupdf.Rect(repl["bbox"])
            page.add_redact_annot(rect, fill=False)

        links = page.get_links()
        if replacements:
            # Transparent fill alone does not preserve intersecting images or vectors.
            page.apply_redactions(images=0, graphics=0, text=0)

        # Step 2: Insert translated text
        for repl in replacements:
            bbox = repl["bbox"]
            fs = repl["font_size"]
            baseline = bbox[1] + font.ascender * fs
            writer = pymupdf.TextWriter(page.rect)
            for line in repl["new_text"].splitlines():
                writer.append((bbox[0], baseline), line, font=font, fontsize=fs)
                baseline += fs * 1.35
            writer.write_text(page, color=repl["text_color"])

        # Redaction removes hyperlinks intersecting old text; preserve their targets.
        remaining_links = page.get_links()
        for link in links:
            if not any(existing.get("uri") == link.get("uri") and
                       existing.get("page") == link.get("page") and
                       existing["from"] == link["from"] for existing in remaining_links):
                page.insert_link({key: value for key, value in link.items()
                                  if key not in ("xref", "id")})

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    return {"total_spans": total_spans, "translated": translated_count,
            "unmatched_keys": sorted(set(translations) - matched)}


def extract_texts(input_path: str) -> list:
    """
    Extract all unique text strings from PDF.

    Args:
        input_path: Path to input PDF

    Returns:
        List of unique text strings
    """
    doc = pymupdf.open(input_path)
    all_texts = set()

    for page in doc:
        text_dict = page.get_text("dict")

        for block in text_dict["blocks"]:
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        all_texts.add(text)

    doc.close()
    return sorted(all_texts)


def main():
    parser = argparse.ArgumentParser(description="Replace simple PDF labels; use paragraph layout for prose")
    parser.add_argument("input_pdf", help="Input PDF file")
    parser.add_argument("translations_json", help="JSON file with translations")
    parser.add_argument("output_pdf", help="Output PDF file")
    parser.add_argument("--font", default="helv", help="Font name (helv, china-ss, japan, korea)")
    parser.add_argument("--min-font-size", type=float, default=8.0,
                        help="Minimum allowed fitted type size in points (default 8)")

    args = parser.parse_args()

    with open(args.translations_json, "r", encoding="utf-8") as f:
        translations = json.load(f)

    result = translate_pdf(args.input_pdf, translations, args.output_pdf, args.font, args.min_font_size)

    print("Label replacement saved; semantic and visual review are still required.")
    print(f"Total text spans: {result['total_spans']}")
    print(f"Translated: {result['translated']}")
    print(f"Output: {args.output_pdf}")
    if result["unmatched_keys"]:
        print(f"Warning: {len(result['unmatched_keys'])} mapping keys were not found in the PDF.", file=sys.stderr)


if __name__ == "__main__":
    main()

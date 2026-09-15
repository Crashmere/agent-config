#!/usr/bin/env python3
"""Extract PDF evidence with occurrence context; opt in to legacy unique strings."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

try:
    import pymupdf
except ImportError:
    print("Use python-environment to select an isolated environment with pymupdf.", file=sys.stderr)
    sys.exit(1)


def extract_texts(input_path: str) -> list:
    """Legacy API: unique trimmed spans, unsuitable as context for prose translation."""
    with pymupdf.open(input_path) as doc:
        texts = set()
        for page in doc:
            for block in page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if text := span.get("text", "").strip():
                            texts.add(text)
        return sorted(texts)


def json_geometry(value):
    """Convert PyMuPDF link geometry without discarding destination fields."""
    if isinstance(value, (pymupdf.Rect, pymupdf.Point, pymupdf.Matrix)):
        return list(value)
    if isinstance(value, dict):
        return {key: json_geometry(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_geometry(item) for item in value]
    return value


def extract_document(input_path: str) -> dict:
    """Preserve raw page/block order and geometry; do not guess semantic structure."""
    source = Path(input_path)
    result = {
        "schema_version": 1,
        "source": {"filename": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "pages": [],
        "warnings": [],
    }
    with pymupdf.open(source) as doc:
        result["page_count"] = len(doc)
        for page in doc:
            page_id = f"p{page.number + 1:04d}"
            raw = page.get_text("dict", sort=False, flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
            blocks = []
            for block in raw["blocks"]:
                if block["type"] != 0:
                    continue
                block_id = f"{page_id}-b{block['number']:04d}"
                lines = []
                for line_index, line in enumerate(block["lines"]):
                    line_id = f"{block_id}-l{line_index:04d}"
                    spans = [
                        {"id": f"{line_id}-s{index:04d}", **span}
                        for index, span in enumerate(line["spans"])
                    ]
                    lines.append({
                        "id": line_id, "bbox": line["bbox"], "direction": line["dir"],
                        "writing_mode": line["wmode"],
                        "text": "".join(span["text"] for span in spans), "spans": spans,
                    })
                blocks.append({
                    "id": block_id, "source_order": block["number"], "kind": "text",
                    "bbox": block["bbox"], "text": "\n".join(line["text"] for line in lines),
                    "lines": lines,
                })
            images = []
            for index, info in enumerate(page.get_image_info(hashes=True)):
                images.append({
                    "id": f"{page_id}-i{index:04d}", "bbox": info["bbox"],
                    "transform": info["transform"], "width": info["width"], "height": info["height"],
                    "content_digest": info["digest"].hex(),
                })
            result["pages"].append({
                "id": page_id, "page": page.number + 1,
                "width": page.rect.width, "height": page.rect.height,
                "rotation": page.rotation, "cropbox": list(page.cropbox),
                "blocks": blocks,
                "geometric_order_hint": [b["id"] for b in sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))],
                "images": images, "links": json_geometry(page.get_links()),
            })
            if not any(block["text"].strip() for block in blocks):
                result["warnings"].append({
                    "page": page.number + 1, "code": "no_selectable_text",
                    "message": "Inspect this page: it may be blank, figure-only, or require OCR.",
                })
    return json_geometry(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_pdf")
    parser.add_argument("--format", choices=("structured", "strings"), default="structured",
                        help="Default: occurrence-preserving JSON; strings: legacy unique spans for labels only")
    parser.add_argument("--output", "-o", help="Write JSON to a new file instead of stdout")
    args = parser.parse_args()
    if args.output and Path(args.input_pdf).resolve() == Path(args.output).resolve():
        parser.error("Save extraction to a new path; do not overwrite the source PDF.")
    data = extract_document(args.input_pdf) if args.format == "structured" else extract_texts(args.input_pdf)
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(serialized, encoding="utf-8")
        print(f"Saved {args.format} extraction to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(serialized)
    if args.format == "strings":
        print("Unique strings omit context. Use structured extraction for prose.", file=sys.stderr)


if __name__ == "__main__":
    main()

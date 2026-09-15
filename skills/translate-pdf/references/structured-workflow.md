# Structured extraction and layout

Use this path for prose, tables, repeated words with different meanings, or cross-page sentences. Keep extraction evidence separate from reviewed translation units.

## What the extractor provides

Run extract_texts.py input.pdf --output source.json with the selected Python environment. The default structured format contains:

- schema_version, source filename and SHA-256, and page count.
- Pages with 1-based numbers, dimensions, rotation, and stable page IDs.
- Text blocks with original PDF order, stable block/line/span IDs, bounding boxes, raw line text, and font/style information. Repeated text remains present at every occurrence.
- A per-page geometric_order_hint, sorted by top/left coordinates. This is **not** validated reading order, especially for columns and tables.
- Image placements and content digests, original links, and warnings for pages without selectable text. No OCR or image descriptions are generated.

Coordinates follow PyMuPDF conventions: extracted geometry is unrotated, while the displayed page rectangle reflects rotation. Normalize coordinates when adapting the renderer for rotated or cropped pages.

Do not translate a sorted list of unique spans as prose. --format strings exists only for the legacy simple-label mapping workflow; it intentionally discards position and occurrence context.

## Build semantic units

1. Inspect page images and raw text to establish column and paragraph order. Recognize recurring page furniture and separate it from sentence continuations.
2. Join layout-wrapped lines within a paragraph, retaining meaningful hyphens and identifiers. Join cross-page continuations before translation. Never merge unrelated table columns, bullets, or captions.
3. For tables, establish cells and include the relevant header, row label, and notes in translation context. Raw PDF blocks may contain several cells or only part of one.
4. Assign task-local unit IDs and preserve the covered source span IDs. Use span IDs when one source block contains several semantic units. Record intentionally retained content explicitly.
5. Translate and review these complete units, then map them back into reviewed layout regions. Do not force the target-language text to follow the source's line breaks.

An illustrative task-local record (not a bundled renderer's API):

    {
      "unit_id": "u0042",
      "source_ids": ["p0005-b0006-l0000-s0000", "p0006-b0000-l0000-s0000"],
      "kind": "paragraph",
      "section": "Methods",
      "source_text": "A sentence restored across its page break.",
      "target_text": "...",
      "status": "translated",
      "semantic_review": "pending",
      "readability_review": "pending"
    }

Neither bundled script automatically constructs or reviews these units. Do not mark guessed joins or table structures as verified.

## Render and validate

The bundled translate_pdf.py only accepts a flat string-to-string mapping. It cannot consume this manifest, join paragraphs, select context-specific translations, or reflow tables. Do not pass structured extraction to it or flatten paragraph translations into fragment keys. Build or adapt paragraph/table layout for long documents.

Retain images and vector graphics, use consistent font measurement and rendering, and wrap complete target paragraphs inside planned regions. Check that redacting one region does not remove neighboring text. Adjust line breaks, spacing, columns, and available regions before shrinking type. Respect user constraints on page count; expose an unresolved fit conflict instead of deleting content or producing unreadably small type.

Keep three distinct checks:

1. Every requested source span is assigned to a translated unit or an explicit retained-content entry; unresolved spans remain visible in the manifest.
2. The reviewed target text appears in the final PDF after appropriate Unicode/whitespace normalization; inspect differences such as bidirectional punctuation separately.
3. Rendered pages remain readable with correct figure/caption and table relationships. Verify image digests and positions when preserving original layout, link destinations, and clickable regions.

A manifest with complete coverage can still contain mistranslations. Run the semantic and readability passes in SKILL.md independently.

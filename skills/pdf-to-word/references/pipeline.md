# Execution and configuration

## Contents

- Workspace and dependencies
- Main workflow commands
- Document configuration
- Second OCR engine and formula tools
- Tool maintenance and validation

## Workspace and dependencies

Run the code in the repository's scripts directory directly, keeping work data outside the repository. PDF_WORD_WORKSPACE defaults to the current directory; the main entry point refuses to run if it is inside the skill repository. Do not create .venv, models, inputs, outputs, or OCR caches inside the skill directory.

| Path in the task directory | Contents |
| --- | --- |
| input/ | PDFs to convert; use a unique filename for each and retain provenance |
| config/overrides.json | Optional document configuration; use the default policy when absent |
| `work/batch/<filename>/` | Hashes, layout, OCR, images, audits, and check results |
| work/batch/rendered/ | Previews actually exported by LibreOffice |
| output/ | Word files, summary reports, and an optional delivery archive |
| models/ | Default local OCR model cache; can point to a shared external path |

Use python-environment to select a healthy isolated environment, and confirm that PyMuPDF, python-docx, Pillow, OpenCV, RapidOCR, ONNX Runtime, and other dependencies import successfully. If installation is needed, use the verified dependency set in [scripts/requirements.txt](../scripts/requirements.txt) and follow that skill's installation method. Do not rebuild an existing usable environment just to run this skill.

Use the docx skill's office/validate.py for XSD validation. By default, it is located at .trae/skills/docx/scripts/office/validate.py under the user's home directory; set DOCX_VALIDATOR to its actual installation path if needed. If a required skill is missing, investigate its source through personal-skill-management; do not skip validation and claim it passed.

Export previews with LibreOffice; Microsoft Word activation is not required. SOFFICE can specify the executable path; otherwise, discovery uses PATH and macOS application paths. Current default Chinese fonts are Songti SC/Heiti SC, and the English font is Times New Roman. Outside macOS, first confirm fonts and the rendering environment. Apple Vision is available only on macOS.

## Main workflow commands

Run these examples in the actual task directory. Set PDF_WORD_SKILL and PDF_WORD_PY to the current skill location and isolated-environment interpreter; avoid copying paths from an old machine.

~~~sh
PDF_WORD_SKILL="$HOME/agent-config/skills/pdf-to-word"
PDF_WORD_PY="$PWD/.venv/bin/python"
export PDF_WORD_WORKSPACE="$PWD"
export PYTHONDONTWRITEBYTECODE=1

"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/convert_batch.py" --help
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/convert_batch.py" prepare
# Compare layout.txt in work/batch with the source images before choosing configuration or OCR.
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/convert_batch.py" build
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/convert_batch.py" render
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/convert_batch.py" check
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/batch_coverage.py"
~~~

Append a filename after a stage to process only that document, for example prepare example --mode ocr. The supported modes are auto, native, and ocr; mode affects only prepare or all. The all stage chains the main stages; its output still needs visual review and source-coverage checks. Do not blindly apply defaults to a full batch of an unfamiliar document type without trial conversion.

Running build again overwrites generated Word files with the same names. Save user-edited files separately rather than making them rebuild targets. Caches are bound to source hashes, audits to Word hashes, and rendering records to Word and preview hashes. If a source file changes under the same name, use a new filename or remove that file's work directory only after confirming that the old cache may be deleted, then run prepare again.

## Document configuration

Use [assets/overrides.example.json](../assets/overrides.example.json) as a reference to create config/overrides.json in the task directory. The example illustrates the format only; do not copy its page counts or cover policy without inspection.

| Field | Meaning |
| --- | --- |
| source_sha256 | Source PDF hash; nonempty configuration must bind to the current source file |
| cover_image | Defaults to true: preserve the first page as a cover image; explicitly set false when there is no cover |
| page_methods | Optional native/ocr entries by physical page; length must equal the total page count |
| full_image_pages | Additional pages to preserve as full-page images, numbered from 1 |
| regions | Page-number strings mapped to lists of rectangles in [x0,y0,x1,y1] format |
| replace | Text replacements verified against the source images; document-specific configuration, not automatically generalized |

Rectangles use the top-left corner as the origin and a normalized page width of 595.276 pt, with height calculated from the source aspect ratio. Crops must fully cover every text box replaced by an image; check captions and edge markers too. Preserving an image does not make its text editable.

| Environment variable | Purpose |
| --- | --- |
| PDF_WORD_WORKSPACE | External task directory; defaults to the current directory |
| PDF_WORD_MODELS | External model cache; defaults to models/ in the task directory |
| SOFFICE | LibreOffice executable |
| DOCX_VALIDATOR | Validation script from the installed docx skill |

Keep source code read-only during execution. Use PYTHONDONTWRITEBYTECODE=1 to avoid generating caches in the source directory. Models download on first use according to the RapidOCR configuration. Point PDF_WORD_MODELS to an existing cache for reuse; do not copy models into the repository.

The generator substitutes default fonts, limits body and table font sizes, and heuristically aligns headers and first columns. It prioritizes content and stable pagination. When design fidelity matters, adjust against the source styling and validate; editability alone does not establish format fidelity.

## Second OCR engine and formula tools

On macOS, you can compile the Vision helper into the task directory:

~~~sh
mkdir -p work/bin
swiftc "$PDF_WORD_SKILL/scripts/vision_ocr.swift" -o work/bin/vision_ocr
work/bin/vision_ocr work/batch/example/page-*.png
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/batch_scan_review.py" example
~~~

Scan comparison selects OCR pages from the layout and writes differences to scan-review.json. Each engine's strengths depend on language and glyphs; do not blindly overwrite the primary results with the second engine's output.

word_math.py provides text, subscript, superscript, fraction, and append_equation functions for creating OMML after manual confirmation. It does not recognize PDF formulas. Each XML node can be inserted only once; assemble formulas with fresh elements, then verify subscripts, superscripts, fractions, and rendering. Exact line spacing may clip formulas.

## Tool maintenance and validation

| Script | Responsibility |
| --- | --- |
| convert_batch.py / pipeline_config.py | Stage orchestration, external workspaces, hashes, and document settings |
| batch_layout.py | Text, font repair, physical lines, tables, and OCR layout |
| batch_convert.py | DOCX paragraphs, tables, headings, images, and pagination |
| ocr_batch.py / vision_ocr.swift | Primary local OCR and optional second OCR engine |
| batch_check.py / batch_coverage.py | Rendering and structure; source glyph and table coverage |
| batch_scan_review.py | Scan-text disagreements and clues about region coverage |
| package_results.py | Verify current file hashes and assemble the delivery archive without inventing manual review |
| word_math.py | Helpers for editable mathematical structures |
| smoke_pipeline.py | Validation with temporary synthetic input; no real documents retained |

After changing the shared conversion workflow, run synthetic validation using an existing external environment and models; no real PDF is needed:

~~~sh
"$PDF_WORD_PY" "$PDF_WORD_SKILL/scripts/smoke_pipeline.py"
# Add --with-vision on macOS when the second OCR engine needs validation.
~~~

The self-check covers native text, editable numeric tables, Chinese scans, blank pages, rendering, XSD, coverage, hash protection, packaging, and formulas. Apple Vision is compiled and run in a temporary directory only with --with-vision. Explicitly report branches that were not run; do not expand checks to unrelated skills.

---
name: translate-pdf
description: |
  Translate PDF documents to any language while preserving original structure, layout, and styling (colors, backgrounds, positions).
  Use when user wants to: (1) translate a PDF to another language, (2) convert PDF from one language to another, (3) create translated version of PDF document.
  Triggers: "translate PDF", "PDF翻译", "把PDF翻译成", "translate this PDF to Chinese/English/Japanese", "翻译成中文/英文"
---

# PDF Translation

Translate PDF text while preserving structure, colors, and background styling.

## Setup and scope

- Use `python-environment` to select an isolated Python environment with `pymupdf` before running the scripts. Run the commands below with that environment's interpreter; do not install dependencies globally.
- Use PDFs with selectable text. The bundled scripts do not perform OCR or automatic paragraph reflow.
- Save the translated PDF to a new path and inspect it for missing text, overlap, and clipping before delivery; preserving every element of a complex layout is not guaranteed.

## Workflow

### Step 1: Extract texts

```bash
python {skill_path}/scripts/extract_texts.py <input.pdf>
```

Review output to see all unique text strings in the PDF.

### Step 2: Create translation mapping

Translate each text to target language. Create JSON file:

```json
{
  "Original Text 1": "Translated 1",
  "Original Text 2": "Translated 2"
}
```

Save as `translations.json` next to input PDF.

### Step 3: Apply translations

```bash
python {skill_path}/scripts/translate_pdf.py <input.pdf> translations.json <output.pdf> --font <fontname>
```

**Font options:**
| Font | Language |
|------|----------|
| `helv` | Latin (English, Spanish, Portuguese, French, German, etc.) |
| `china-ss` | Simplified Chinese |
| `china-ts` | Traditional Chinese |
| `japan` | Japanese |
| `korea` | Korean |

## Output naming

Append language suffix: `filename_EN.pdf`, `filename_ZH.pdf`, `filename_JA.pdf`

## Tips

- Keep proper nouns, abbreviations, technical terms unchanged when appropriate
- CJK fonts auto-scale to 90% for better fit
- Use transparent fill to preserve original background colors

## Source

Personally maintained adaptation of [wshuyi/translate-pdf-skill](https://github.com/wshuyi/translate-pdf-skill), imported from the user's downloaded skill. Preserve the bundled MIT [LICENSE](LICENSE) when redistributing.

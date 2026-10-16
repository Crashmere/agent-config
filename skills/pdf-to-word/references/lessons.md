# Known issues and methods

Treat these lessons as clues with defined applicability, not rules for every PDF. Record observable symptoms, evidence for the cause, verified corrections, and limits for new findings. Add scripts when deterministic operations are needed rather than adding explanations while leaving tools broken.

| Symptom | Cause or diagnostic clue | Verified method and limits |
| --- | --- | --- |
| Direct conversion in one pass splits the cover, joins English words, or loses formula denominators | Page-position data does not reliably become paragraph or formula structure | Use direct conversion as a trial baseline; use native extraction and reconstruction when needed. General converters still work for simple files; always inspect the result. |
| A text layer exists but is incomplete | Some scanned PDFs have incomplete text layers | Compare against the visible source images and switch pages to OCR as needed; do not judge by character count alone. |
| English in Founder (方正) E-* fonts becomes rare Chinese characters | Observed ToUnicode mappings incorrectly map CID 0x42–0x7B to U+7280–U+72FF | Under this condition, recover ASCII as CID−1. Aggregate across all pages and handle Identity-H aliases in font names. Do not generalize this pattern to other fonts or arbitrary Chinese characters. |
| Reported font size is roughly twice the visible size, inflating page count | Anomalous font metadata | Estimate a scale from consecutive Chinese-character spans, character count, and font size; apply it only to clear anomalies. Verify against source images and actual rendering. |
| English, Chinese, and subscripts or superscripts on one line are split into multiple blocks | The PDF splits content by font or baseline | Reconstruct physical lines from vertical overlap and baselines while preserving horizontal order. Multicolumn pages need separate column segmentation; do not apply single-column rules directly. |
| Confusion between μ, γ, 氮/氨, 钴/钻, or c/C | OCR is unreliable for similar glyphs and specialized symbols | Compare the primary engine with a second engine and source images, especially for numeric units, chemical symbols, and variable case. Retain source images when uncertain. |
| Both OCR engines misread a person's name | Blurred or rare glyphs | Use the complete source-image region; do not guess based on familiar names. General font-mapping repairs must not hard-code a particular person's name either. |
| Websites, source credits, or markers at the bottom of a page disappear | Content lies outside the body crop boundary | Compare page edges; add page-anchored images when needed to avoid creating extra pages by inserting them into the body. |
| Page dimensions are huge or crops are displaced | The scanned PDF's MediaBox differs from ordinary pages | Normalize width to 595.276 pt while preserving aspect ratio; use one coordinate system for all OCR, images, and crops. |
| Covers or illustrations become thin lines | Word's exact line spacing is smaller than the image height | Use automatic line spacing for ordinary illustrations and page anchoring for full-page images. Check horizontal and vertical offsets as well as image dimensions. |
| An entire text passage is removed, but its image crop cuts off the final characters | Exclusion is based on the text-box center while the crop is smaller than the full text box | Expand crops to include the full boundaries of all replaced text boxes, merge overlapping regions, and inspect the source image again. |
| OCR body text gains extra line breaks and pages | Right indents follow short source lines and font size is unstable | Use a stable baseline font size and the available page width with limited scaling; reconsider the layout when substantial shrinking is needed. |
| Subscripts or superscripts are too small | Applying Word subscript or superscript shrinks an already small source-PDF font again | Restore the baseline font size when applying Word subscript or superscript; verify the result in body text and tables. |
| Legend numbers are mistaken for bold headings | Detection checks only for a leading number | Distinguish a section number plus title from a number followed by an explanation. Heading detection remains heuristic; review new formats. |
| Chinese text disappears in headless LibreOffice | Fontconfig is not loaded correctly in the current macOS environment | Check Chinese fonts and explicitly set the Homebrew font configuration if needed. Do not treat its path as fixed across platforms. |
| Word opens normally, but XSD validation fails | XML children such as table indentation, borders, or margins are out of specification order | Insert in schema order instead of appending arbitrarily; both actual rendering and structural validation must pass. |
| Increasing left cell margins shifts the table left in the LibreOffice preview | Renderer table positioning interacts with cell margins and table indentation | Check the outer table position whenever margins change. Compensate with corresponding table indentation if needed, then check cell content. This was verified in a trial with a simple native table; it is not a fixed compensation value for every renderer. |
| Zoom validation fails for a new default python-docx document | w:zoom lacks w:percent | Set percent explicitly, for example to 100; formula-helper tests also require compliant document settings. |
| LibreOffice reports success, but the preview is still the old file | Conversion produced no new file and an old preview remains | Remove the identified derived target before conversion, confirm a new preview exists, and bind source-Word and preview hashes. Preserve inputs. |
| Old OCR is reused after an input changes under the same name | Caching uses only the filename | Write a source fingerprint before OCR starts and reject reuse when the source changes. Consider cache-invalidation rules when adding engines or parameter policies too. |

## Current capability limits

- The default generator uses uniform fonts, body and table font-size caps, and heuristic header and first-column alignment. This can improve pagination stability for technical documents but does not guarantee preservation of the source design. For higher layout fidelity, extract source styles or add verified configuration; do not unconditionally apply a one-off fix to all new documents.
- Validation has mainly covered Chinese single-column technical documents with stable physical page order. Multicolumn, vertical, handwritten, complex cross-page tables, and nested structures still require additional rules.
- Heuristic scanned-table detection may miss tables. Standalone vector figures without a text layer may not appear in the image list. Visually confirm them before preserving or rebuilding them.
- Character coverage compares counts and cannot establish order or meaning; numeric serialization checks cannot establish that OCR numbers are correct either.
- Mapping physical lines to paragraphs helps preserve pagination but is unsuitable for extensive text reflow. Merge semantic paragraphs in a separate step when needed and review the entire rendered document.
- The batch tools do not automatically convert formulas to OMML. Confirm formula structure manually before building editable formulas with word_math.py.
- Current text and Word font settings favor macOS. Adapt fonts and tool paths before moving to another system, and record the new validation results.

## Maintaining these lessons

When an uncovered problem appears, first verify the correction, then decide whether it reflects a general mechanism or a task-specific case. Revise affected existing entries and update the corresponding scripts, minimal synthetic validation, and execution instructions. Remove contradictory or obsolete rules, and do not retain real document content as examples. Complete repository synchronization through personal-skill-management; do not wait for another request to record lessons.

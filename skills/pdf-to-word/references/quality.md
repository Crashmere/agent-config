# Quality checks and delivery

## Check different problems independently

| Check | Can detect | Cannot establish |
| --- | --- | --- |
| OOXML/XSD | Invalid structure, child-element order, and similar issues | Correct layout and content |
| Actual rendering and page count | Files that cannot open, overflow, extra page breaks | No missing characters and correct order |
| Per-page text from Word to preview | Characters lost during serialization, text not rendered | Correct source extraction or OCR |
| Source glyph coverage | Native text omitted outside images or tables | Correct reading order from matching character counts |
| Cell-character and numeric serialization | Incorrect cells, some misplaced or missing values | Completely correct font mapping or semantics for every symbol |
| Comparison between two OCR engines | Recognition disagreements, regions missed by one engine | Omissions shared by both engines or zero errors throughout the text |
| Thumbnails of every page and enlarged inspection | Missing images, crop errors, font-size issues, misalignment, table anomalies | Exact text without character-by-character proofreading |

Comparing expected text and output text generated through the same path is not independent source verification. Return to the source PDF or image for evidence in high-risk areas containing numbers and specialized symbols.

## Visual and content review

1. Inspect thumbnails of every page for blank areas, page order, figures and tables, content density, margins, and pagination.
2. Enlarge the densest tables, formulas, retained source-image regions, low-confidence text, and all anomalies flagged by automated checks. Check full crop boundaries, legends, units, subscripts, and superscripts.
3. Compare specialized symbols, variable case, names, standard identifiers, numeric ranges, and decimal points against the source images; do not guess based on plausibility.
4. Change the extraction route when the text layer disagrees with visible content. Vector figures may not appear in the image list and must be manually added to retained regions.
5. Check reading order, relationships between table columns, cross-page sentences, and edge markers. Recheck after normalizing fonts or dimensions.
6. After fixing content, coordinates, formulas, or layout, regenerate the affected Word files, render them, and check again; do not reuse invalidated manual-review records.

For unfamiliar layouts, expand the representative-page trial. Record limitations for unverified capabilities; turning the entire file into images does not fulfill an editable-document requirement.

## Record the actual review scope

Store audit.json, checks.json, coverage.json, and optional scan-review.json in `work/batch/<filename>/` under the task directory. Audits and checks still contain source content and are task data; keep them out of the skill repository.

After actually performing visual or content review, optionally write manual-review.json:

~~~json
{
  "source_sha256": "current source file hash",
  "word_sha256": "current Word file hash",
  "preview_sha256": "current preview hash",
  "status": "reviewed",
  "scope": "scope actually inspected and checked",
  "notes": ["remaining limitations or reasons for retaining images"]
}
~~~

Record only checks that were performed. Without a record, the packaging tool marks manual review as not_recorded; it does not claim review automatically. If current file hashes do not match, correct the workflow and review again rather than changing hashes to pretend an earlier review is still valid.

## Delivery

- Deliver the editable Word file, a PDF preview exported from the final Word file, and a per-file explanation of editable content and retained images.
- Report the checks performed and their actual results, including remaining OCR, reading-order, font-substitution, or editing limitations. State unresolved significant errors explicitly; do not summarize failed areas as having passed checks.
- Explain that image text cannot be edited directly, that organizing batch body text by physical lines affects extensive reflow, and that other office applications may paginate differently.
- If an archive is needed, run package_results.py after review. It verifies current hashes and generates output/quality-report.json and delivery.zip; it does not replace manual inspection.
- This skill preserves source files by default. When the user requests cleanup, precisely identify and delete the documents and content caches while retaining reusable tools and sanitized lessons. Do not leave broken sample-reuse code or hard-coded document settings after deletion.
- After completing the current task, review reusable new findings and write them back to the repository under the continuous-improvement requirements in SKILL.md.

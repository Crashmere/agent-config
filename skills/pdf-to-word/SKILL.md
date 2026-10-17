---
name: pdf-to-word
description: "Convert PDFs to accurate, usable DOCX files with editable content where reliable and verified rendering, including batch, scanned, or broken-text PDFs."
---

# PDF to Word

Prioritize accurate, complete, editable content. Choose methods for the actual document before refining the layout. Treat these tools as a starting point validated through use, not a complete set of rules or a promise of lossless one-click conversion for every PDF.

## Responsibilities and dependencies

- Use this skill to orchestrate PDF-to-Word conversion and quality checks. Reuse the installed official pdf and docx skills for general file operations and OOXML validation; do not copy their installation directories or third-party scripts into this repository.
- Use python-environment for third-party Python dependencies and environment selection; use software-installation to install or troubleshoot software such as LibreOffice.
- Use translate-pdf for meaning, terminology, and translation review when translation is needed. Format conversion must not independently rewrite, translate, or correct facts in the source.
- Use personal-skill-management when improving this skill or its scripts, following its repository workflow for validation, discovery-link synchronization, commits, and pushes.

## Core workflow

1. **Confirm the goal and inspect the input.** Infer the scope, editing needs, and layout tradeoffs from the request. Inventory files, hashes, page counts, dimensions, duplicates, text layers, and images. Compare body text, tables, formulas, page edges, and blank pages with the source images; a text layer is not necessarily reliable merely because it exists.
2. **Choose a method for each page.** Prefer native extraction for reliable text layers and OCR for scans or damaged text layers. Rebuild body text and reliably recoverable tables as Word objects; preserve source images for complex formulas, diagrams, chemical structures, and uncertain glyphs. Use an entire document of page images as the final Word file only when the user explicitly accepts that result.
3. **Trial-convert representative pages first.** For unfamiliar or anomalous documents, include dense tables, formulas, low-resolution areas, cross-page content, and page edges. Check reading order, missing characters, font sizes, crops, and pagination before expanding to the full batch. Adjust or extend the tools when the existing method does not fit; do not force new input into old rules.
4. **Generate output and retain evidence for comparison.** Separate task configuration from general code; bind document-specific replacements, crop coordinates, and OCR caches to the source hash. When replacing text with source images, include complete text boxes and captions in the crop; do not guess unclear characters. Preserve genuine blank pages and content order.
5. **Complete the verification cycle.** Perform structural validation, actual Word rendering, per-page text transfer checks, source-content coverage checks, cell-by-cell comparisons, and visual inspection separately. For scans, focus on numbers, units, symbols, and names; a second OCR engine can expose disagreements for resolution against the source image. After fixes, rerun only affected checks; expand the scope when shared layout logic changes.
6. **Deliver and explain limitations.** Provide the Word file and a PDF preview actually exported from the final Word file. For each document, state which content is editable or retained as images, the checks performed, and remaining issues. Matching character counts, page counts, or OCR results do not establish complete textual accuracy. An unactivated Word installation does not prevent Python generation or LibreOffice verification.
7. **Record reusable findings.** Review new findings as described below and complete relevant skill maintenance after delivery. Do not leave reusable solutions only in the task directory or this conversation.

## Continuous improvement during use is required

The user requires this skill to improve through conversion practice. Future inputs will encounter cases not covered by current experience, layout rules, or scripts. Identify these gaps proactively; having an existing skill must not lower the inspection standard.

- Before finishing each conversion, review whether it revealed a new PDF type, encoding or font anomaly, OCR confusion, table or formula structure, platform difference, verification blind spot, or reusable operation.
- When a reusable finding, tool defect, or new solution emerges, **first finish and verify the fix for the current task, then use personal-skill-management to update this skill in the same turn; do not wait for another request to update the skill.** If the task is still underway, record points to retain and complete the write-back after delivery.
- Put generalizable decisions and boundaries in SKILL.md; add the specific symptom, cause, verified correction, and applicability to references; add or correct repeated deterministic operations in scripts. Add scripts when new tools are needed, and update entry points, parameter documentation, and dependency records.
- For changes that affect content, routing, or verification conclusions, add a minimal reproducible sanitized or synthetic case and run the affected checks. Correct old descriptions when rules are overgeneralized or insufficiently validated, and merge duplicate lessons instead of mechanically accumulating cases.
- Keep coordinates, proper-name corrections, and layout settings that apply to one document in the task workspace. When generalizing, retain the mechanism and synthetic examples, not source text, real screenshots, OCR output, or document hashes. Keep models, environments, compiled artifacts, and caches out of the skill repository as well.
- When there are no new findings, do not manufacture changes for continuous improvement; state that the existing rules applied. If an improvement is not yet verified, record its limits explicitly and do not claim support.
- After maintenance, validate and synchronize through the personal-skill-management repository workflow. Briefly report the new capability or lesson, validation, and synchronization results. This requirement applies to this skill; it does not authorize changes to unrelated skills or expand task permissions.

## Reading and execution entry points

- **Before running the tools for the first time or changing workspaces**, read [Execution and configuration](references/pipeline.md) for external workspaces, dependencies, stage commands, crop settings, editable formulas, and the script inventory.
- **When deciding check scope, recording manual review, or delivering results**, read [Quality checks](references/quality.md) for the limits of coverage checks, visual inspection, and delivery records.
- **When investigating anomalies or preparing to record new lessons**, read [Known issues and methods](references/lessons.md) for font mapping, OCR, image crops, font sizes, subscript and superscript, and rendering problems.
- Run the main workflow with [scripts/convert_batch.py](scripts/convert_batch.py); see the execution reference for parameters and helper tools. After changing the shared workflow, you can run [scripts/smoke_pipeline.py](scripts/smoke_pipeline.py) for synthetic validation.

## Operational boundaries

- Keep source PDFs and output in the task directory; leave source files unchanged by default. Delete specific document artifacts only when the user authorizes cleanup; do not apply cleanup permission from another task to the current one.
- Prefer local extraction, OCR, and rendering. Downloading models does not upload documents. Before using an external conversion service that uploads documents, confirm that the task already authorizes the upload.
- Keep runtime data outside the skill repository. Maintain the repository scripts as the single source of truth instead of independently fixing copies in multiple directories and letting them diverge.
- Explain the editing limits of organizing body text by physical lines. If extensive reflow is needed, merge semantic paragraphs in a separate step and validate the result. Check the default cover-image policy, single-column assumptions, fonts, and platform limits against each new document.

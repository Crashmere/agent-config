# Reading, writing, and targeted edits

Use `YUYAN_DOC` as defined in the entry point. Below, `work_dir` denotes this task's dedicated temporary directory; replace example IDs with actual query results. Keep the instance selected by `--server`/`YUYAN_SERVER` consistent throughout the task.

## Reading and locating content

```sh
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/yuyan-doc.XXXXXX")
node "$YUYAN_DOC" api --path books
node "$YUYAN_DOC" api --path 'search?q=部署'
node "$YUYAN_DOC" read --doc 42 --scope outline --out "$work_dir/before.json"
node "$YUYAN_DOC" read --doc 42 --scope section --path 3
node "$YUYAN_DOC" read --doc 42 --scope keyword --keyword 超时
node "$YUYAN_DOC" read --doc 42 --scope node --path 3/0
```

- `full` returns complete native JSON by default; `outline` returns all headings and paths; `keyword` performs case-insensitive literal matching, returning at most 30 hits and indicating truncation.
- A `node` path consists of `content` array indexes from the root, for example `3/0` = `doc.content[3].content[0]`; the root path is an empty string. The returned node hash can be an additional patch `expect` value.
- `section` accepts only a top-level heading path and includes that heading up to, but not including, the next heading of the same or higher level. For headings inside containers, use `node` to read the enclosing container; do not assume they are top-level.
- `--out` always writes a full snapshot regardless of the scope displayed on screen; use a new path for each output. Read results include a revision; ensure it matches the snapshot when preparing a patch.
- `--format markdown` is only for full-document reading and may include HTML for complex formatting. Do not remove escapes or treat this reading output as a lossless editing snapshot.

## Creating documents

Query the knowledge base and parent first. If no destination is specified, infer it from the current task context; clarify only when several destinations are reasonable. The title is a separate field and need not be repeated as an H1 in the body.

```sh
node "$YUYAN_DOC" create --book 1 --parent 10 --title '部署指南' --input "$work_dir/article.md" --format markdown --out "$work_dir/created.json"
node "$YUYAN_DOC" create --book 1 --title '资料分组' --kind group
node "$YUYAN_DOC" create --book 1 --title '新周记' --template TEMPLATE_ID
```

`create` includes conversion and format validation. Without input, it creates an empty document. Groups have only a title and accept no body. Run `validate --input article.md --format markdown --out article.json` separately only to inspect the converted JSON in advance or troubleshoot format errors; it parses locally without accessing the service and is not a prerequisite for every creation. Images in Markdown must first be uploaded and reference `/assets/...`; `[[名称]]` must first be resolved to a real document link. Converter reports of degradation or unresolved bold prevent writing. Resolve diagnostics first, then use native JSON for confirmed formatting that Markdown cannot express.

## Markdown bold checks

The project converter already supports Chinese punctuation boundaries such as `**标签：**正文`. Internal whitespace in `**重点 **`, a missing closing `**`, and a single `*` in a body formula being confused with emphasis pairing are distinct problems. The converter reports remaining unescaped `**` using original text positions in the syntax tree. `fromMarkdown`, `validate`, and `create --format markdown` return `conversion_error` with line and column positions and stop before application writes.

- Correct a working copy against the original material. For example, change `**重点 **` to `**重点** `; escape a multiplication sign as `\*` to preserve it literally, or use inline code for a complete formula. When a closing marker is missing, establish the intended bold span before editing; do not blindly append a marker at the paragraph end.
- Use code or `\*\*字面\*\*` when intentionally displaying Markdown syntax. Checks preserve code, formulas, HTML, link URLs, and escaped asterisks; not every `**` is an error. Native JSON does not automatically interpret or remove literal asterisks.
- For residual markers in saved documents, return to the original import material to check them. Read the latest snapshot again and `replace` only affected paragraphs, preserving other marks, media, and links. Do not substitute already-escaped Markdown exports for the original source, or reimport the whole document over later edits.
- Verify batch repairs in an isolated instance and run `edit --dry-run` before saving. Use the result snapshot to check that confirmed residual markers are gone and multiplication signs and code remain. Spot-check the corresponding reading sections only when fixing an actual display problem; do not download the entire knowledge base again.

These diagnostics belong to the shared converter; the skill reuses the project implementation rather than copying a second set of Markdown parsing rules. The older `migrate-strong` handles only differences between strict rules and Chinese punctuation rules; it cannot repair these source syntax problems.

## Migration semantics and screenshot handling

When migration includes preserving layout, reducing screenshots, or repairing styles from the original editor, check the following against the source in addition to structural validation. Conversion or save success alone is not enough to establish completion.

- **Distinguish code from text emphasis.** Authors may use inline code colors in editors such as Typora to emphasize ordinary text. List candidates with context first; after confirming the meaning, change such `code` to `textColor` (for example pink `#d63384`), preserving bold, links, and other marks. Do not globally remove code merely because it contains Chinese characters: Chinese strings in SQL, commands, identifiers, file paths, formulas, syntax placeholders, and query results may still be real code.
- **Split mixed content.** For example, in “自增字段 itemnumber”, color only the explanatory text and keep `itemnumber` as code; do the same for Chinese explanations after parameter assignments. Preserve the text itself, code whitespace, and order. Do not change site-wide inline-code CSS to accommodate individual materials, or treat adding color alongside `code` as conversion to ordinary text.
- **Inspect mixed screenshots.** Do not classify images only as text-only or keep-whole. Check combinations such as explanatory paragraphs plus diagrams, SQL editor areas plus execution plans, and tables plus graphics. Use the original image to reconstruct separable portions as body text, native tables, or code blocks. OCR is only an aid; check symbols, column alignment, and code. Keep necessary labels, arrows, and legends inside graphics.
- **Crop according to the purpose.** When the user wants extracted text removed or uploaded content reduced, physically crop a working copy, `upload` it, and replace the media reference; keep the source for comparison. Reuse the `crop` attribute only for partial display during reading or complementary splits. Use the new file's real dimensions for `sourceWidth/sourceHeight`, set a sensible display width and `height:null` to avoid stretching or excessive enlargement, and do not leave SQL fragments outside the diagram area in the crop.
- **Check completeness.** Before batch repairs, keep an inventory of classifications, transcriptions, and crop boundaries, then make targeted changes against the original snapshot. Combine changes in the same chapter to reduce repeated saves. Check that color changes have not rewritten text order, actual code, tables, or links, and that extracted text is no longer duplicated in images. After `verified:true`, reuse the result snapshot and perform only the necessary focused visual checks of this change's colors and image proportions.

## Patch format

Save JSON in a separate patch file. `operations` apply sequentially to the preceding result, so adjust later indexes after insertion/deletion; editing separate locations from end to start is often useful. All operations are ultimately submitted in a single body save with a revision.

```json
{
  "operations": [
    {"op":"text","path":"1/0","text":"修改后的文字"},
    {"op":"attrs","path":"2","attrs":{"textAlign":"center"}},
    {"op":"splice","path":"","index":4,"deleteCount":0,"nodes":[
      {"type":"paragraph","content":[{"type":"text","text":"新增段落"}]}
    ]}
  ]
}
```

| Operation | Fields | Meaning |
|---|---|---|
| `text` | path, text | Replace a text node's complete nonempty text, preserving its marks; remove empty text with splice on the parent |
| `attrs` | path, attrs | Merge node attributes; set an attribute to null to restore its default where its definition permits |
| `replace` | path, node | Replace one complete node; use this to change text marks while preserving other marks. Replacing the root path rewrites the whole document and must clearly fit the user's goal |
| `splice` | path, index, deleteCount, nodes | Insert, delete, or replace consecutive children in the target container's content; nodes may be an empty array |

Add `expect` (the node hash returned by reading) to any operation to check its target before execution. To change the title, add `"title":"新标题"` at the top level; `operations:[]` is still required. Do not use raw PATCH renaming to bypass the revision protection described here.

```sh
# Preview batch rewrites, full replacements, or structural reorganization first; ordinary text edits can use edit directly.
node "$YUYAN_DOC" edit --snapshot "$work_dir/before.json" --patch "$work_dir/patch.json" --dry-run
node "$YUYAN_DOC" edit --snapshot "$work_dir/before.json" --patch "$work_dir/patch.json" --out "$work_dir/after.json"
```

Reusing an old snapshot causes a conflict; start the next round from the latest after.json. Patches that do not change content neither write nor increment revision. Images are inline nodes and belong in a paragraph in ordinary body content; tables, code, attachments, and columns are block nodes. Every container must retain its minimum valid structure; for example, a collapsible block always contains a title and body, even when the title is empty.

Before creating/editing, the script checks that every image and attachment URL is accessible. Edits protect the original with `baseRevision` and `sessionRevision`, then read back and compare the title and complete body after saving and request a result snapshot. Success returns `verified:true`; the agent need not repeat these checks with another round of requests. A successful write followed by failure returns a receipt. If only recording the snapshot failed, check the current body, then call `api --method POST --path docs/42/snapshot` without resubmitting the body. Read the history list separately only when troubleshooting a snapshot failure or when the user requests history.

## Verification and stopping conditions

| Situation | Required checks and stopping conditions |
| --- | --- |
| Ordinary creation, wording changes, polishing, code edits, or content changes in existing tables | Review content and user requirements before submission; deliver when create/edit returns `ok:true, verified:true`, without additional body/history reads or opening the reading page |
| User requests a complete import, a specified character count, batch reorganization, or cross-document links | Check the relevant completeness, counts, order, or link targets once using inputs and `--out` snapshots; for tree changes, read the affected tree once more. Stop if no new issue remains |
| This change introduces/alters a layout that requires rendering to judge, or the user explicitly requests layout acceptance | Prefer [Local preview](preview.md) with the saved snapshot. Check only affected sections and required viewports; after a fix, recheck only the affected portion. Use the real page to check online access behavior |
| Errors, 409, writeReceipt, unconfirmed write outcomes, or actual defects found | Reread, repair, and verify according to the error and specific issue; do not use stopping rules to hide unfinished work |

The `--out` snapshot contains the full result already read back by the script. Prefer it for additional content checks rather than downloading the same body again. Repeated GETs just for reassurance, downloading each image to compute hashes, opening every link, exporting and reimporting, inspecting version lists, or running the project roundtrip are not ordinary document delivery steps. If the user explicitly requests byte-for-byte media integrity or a complete migration, perform one targeted verification for that requirement.

Visual checks can reveal layout problems that JSON consistency cannot prove absent, but need a clear purpose, such as imported image proportions on narrow screens or a merged table just changed. `preview` does not fetch the remote body or write to production; it reuses local media and reads missing images as needed. Attachments are checked only as cards. Its `checksPassed` only means automated checks found no rendering errors; inspect the screenshots relevant to this task. Allow at most one evidence-based correction/retry for a failed optional check, then disclose that visuals remain unverified and deliver the saved content. Do not switch to building proxies, installing browsers, or debugging the project runtime. Explicitly report any unresolved user-requested visual acceptance or known layout defect; do not claim full acceptance.

## Media and export

```sh
node "$YUYAN_DOC" upload --input ./diagram.png --kind image
node "$YUYAN_DOC" upload --input ./report.pdf --kind attachment --timeout 0
node "$YUYAN_DOC" download --src /attachments/CONTENT_ID --out "$work_dir/report.pdf" --timeout 0
node "$YUYAN_DOC" export --doc 42 --out "$work_dir/export"
```

upload returns media metadata and an insertable native node. Images can add attributes such as caption, shadow, crop, and placement; see the format reference. The tool streams file uploads. Images are limited to 25 MiB; the tool imposes no attachment size limit. Renaming an attachment changes only the current node's name, not the stored object. There is no workflow for downloading and executing attachments.

export exports the current single document's Markdown/HTML, native JSON, and actually referenced files, including service media referenced only by text links. Local file paths replace media links in Markdown; external links remain unchanged and are not downloaded. Document links remain usable web links. The output directory must not already exist. On failure, it may contain only partial files and must not be treated as a complete export; retry with a new directory. Export excludes child documents, history, the template library, and the database. For full-library exports or consistent backups, use Yuyan's existing project tools and server-operations.

Generate and review drawings locally with `drawing`. `upload --kind drawing` returns the complete block, which create/edit can insert; see [Editable drawings](drawing.md). Text inside drawings is derived from the scene and cannot be changed with text operations; use attrs for caption, width, or alignment. export also enumerates drawing packages and their image dependencies; keep the package and images in the same directory when reimporting.

## Format validation

Commands such as `schema --node tableCell` read attributes and defaults from the current checkout. `validate` checks Tiptap parent/child structure, unknown attributes, and common attribute values without executing arbitrary HTML, code, or formulas. Valid structure does not prove table spans, diagram meaning, or layout match the user's intent. Check affected content according to [Verification and stopping conditions](#verification-and-stopping-conditions); existing complex blocks alone do not justify expanding to whole-document layout acceptance.

All writes undergo final server-side validation. Report the reason for incompatibility or garbage-collected media. Do not delete attributes you do not understand or convert complex containers to plain text merely to pass checks.

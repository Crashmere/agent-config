# Native document format

Contents: basic structure and text, code and formulas, containers, tables, images and compositions, attachments, links, compatibility boundaries.

This reference describes the current format and common patterns. Actual nodes/attributes are defined by the output of `schema [--node TYPE]` from the Yuyan checkout. The format source is Yuyan's `web/src/schema`; do not copy or maintain a second schema when modifying this skill. Use `validate` / `create` / `edit` for writes; do not reconstruct the original body from DOM HTML.

## Basic structure and text

The document root is `doc`, whose content contains at least one block. An empty document is `{"type":"doc","content":[{"type":"paragraph"}]}`. Nodes use `type / attrs / content / text / marks`. A `text` node has nonempty text and no content.

| Node | Content / attributes |
|---|---|
| paragraph | Inline content; textAlign: null / left / center / right |
| heading | Inline content; level: 1–6; no paragraph alignment attribute |
| hardBreak | Inline line break, no content |
| horizontalRule | Block-level separator |
| blockquote | One or more blocks |
| bulletList / orderedList | One or more listItem nodes; ordered-list start defaults to 1, and type normally retains its default null |
| listItem | Must start with paragraph, followed optionally by blocks or nested lists |
| taskList / taskItem | taskList contains taskItem nodes, with content like list items; taskItem.checked is boolean |

Text marks: `bold`, `italic`, `strike`, `underline`, `code`; `highlight` has no color value by default and corresponds to `==高亮==`. Store marks in text.marks, not as nodes.

`**文字**` in native text remains literal body content; the reading page does not reinterpret it as bold. Markdown import diagnoses unresolved bold; fix boundary whitespace, closing markers, or multiplication-sign ambiguity before saving. See [Markdown bold checks](editing.md#markdown-bold-checks); do not simulate marks by globally deleting asterisks.

```json
{"type":"paragraph","content":[
  {"type":"text","text":"重要内容","marks":[{"type":"bold"},{"type":"highlight"}]},
  {"type":"text","text":"链接","marks":[{"type":"link","attrs":{"href":"/docs/42"}}]}
]}
```

Use the `textColor` mark for text color, with color and optional gradient in attrs; use `highlight.color` for text background. Prefer #rrggbb for solid colors. Arbitrary CSS, transparent backgrounds, and custom gradients are unsupported. Fixed text gradients are ocean, violet, sunset, and flame; read their matching solid-color fallbacks from textGradients returned by `schema`. For example, ocean uses color `#14b8a6`. Each mark type appears only once; preserve links, bold, and other marks when changing colors.

Ordinary text emphasis can be written as `{"type":"text","text":"性能损耗","marks":[{"type":"textColor","attrs":{"color":"#d63384"}}]}`. If a migration source uses inline code to simulate color, confirm that it is ordinary text and remove `code`; merely adding color is insufficient. Preserve `code` for actual code and split mixed sentences into multiple text nodes. See [Migration semantics](editing.md#migration-semantics-and-screenshot-handling).

## Code, Mermaid, and formulas

`codeBlock` contains only unformatted text. Put code in text, preserving newlines and spaces without parsing Markdown inside it. attrs: language, title, titleHidden, collapsed. A null title means no title bar; an empty string means an empty title bar. Provide a visible title bar when the block needs to collapse.

```json
{"type":"codeBlock","attrs":{"language":"go","title":"示例","collapsed":false,"titleHidden":false},"content":[{"type":"text","text":"fmt.Println(\"hello\")\n"}]}
```

Mermaid uses `codeBlock` with language set to `mermaid`, not a separate node. Markdown code fences support `go title="示例" collapsed`; title and collapse state are preserved. Code font colors, search, zoom, and editing shortcuts are web UI behavior, not body attributes.

Formulas use `inlineMath` (inside paragraph) or `blockMath`, with the expression in attrs.latex and no content. Escape backslashes in JSON, for example `{"type":"blockMath","attrs":{"latex":"E=mc^2"}}`. Do not treat formulas as executable programs.

## Callouts, collapsible blocks, highlighted blocks, and columns

- `callout`: content must contain calloutTitle followed by calloutContent. The former holds inline content; the latter holds at least one block. Common attrs.type values are note, info, tip, warning, danger, success, question, example, and quote. fold is `""` (not collapsible), `"+"` (expanded), or `"-"` (collapsed). Use codeBlock for code; do not create the old `[!code]` style.
- `foldBlock`: content contains foldTitle followed by foldContent; the title is inline and the body has at least one block. attrs.collapsed is boolean.
- `highlightBlock`: at least one block; backgroundColor uses the fixed palette. Query the ten light colors with `schema`; do not use arbitrary values. The default is blue `#e1efff`.
- `columns`: 2–4 column nodes, each containing at least one block. attrs.widths contains positive integer proportional weights matching the column count, each 1–1000; null means equal widths. For example, `[1,2]`. Columns stack vertically on phones.

```json
{"type":"foldBlock","attrs":{"collapsed":true},"content":[
  {"type":"foldTitle","content":[{"type":"text","text":"展开查看"}]},
  {"type":"foldContent","content":[{"type":"paragraph","content":[{"type":"text","text":"说明内容"}]}]}
]}
```

These containers can hold tables, code, columns, and other schema-valid blocks. When reducing the number of columns or removing a container, move all content out in its original order; do not keep only the first column. Include required containers when saving a snippet; expand the selection if it cannot form a complete valid structure.

## Tables

Structure: `table → tableRow → tableCell / tableHeader → block+`. Actual tableHeader nodes determine headers; a table may have no header, and the first row need not be one. Do not set nonexistent rows, columns, width, or height attributes on table.

| Location | Attributes |
|---|---|
| table | blockAlign: left / center / right alignment of the whole table within the body |
| tableRow | height: positive pixels or null |
| tableCell / tableHeader | colspan, rowspan (positive integers, default 1); colwidth (pixel-width array for each spanned column, or null) |
| Cell | align (column default alignment), cellAlign (override for this cell), backgroundColor (solid color or null) |

After merging, remove covered cells while preserving all their content; when splitting, add the actual cells needed. Check spans against the occupied grid so every row covers the same number of columns. `colwidth` length equals colspan; widths and align for the same logical column must be consistent across rows. If column widths are already fixed, set a width for new columns as well. cellAlign is an independent override; do not change the whole column's align to align just one cell.

```json
{"type":"table","content":[
  {"type":"tableRow","content":[
    {"type":"tableHeader","attrs":{"colspan":2,"colwidth":[180,180],"backgroundColor":"#e1efff"},"content":[{"type":"paragraph","content":[{"type":"text","text":"合并表头"}]}]}
  ]},
  {"type":"tableRow","attrs":{"height":48},"content":[
    {"type":"tableCell","attrs":{"colwidth":[180]},"content":[{"type":"paragraph","content":[{"type":"text","text":"左"}]}]},
    {"type":"tableCell","attrs":{"colwidth":[180],"cellAlign":"right"},"content":[{"type":"paragraph","content":[{"type":"text","text":"右"}]}]}
  ]}
]}
```

Complex tables export as HTML to preserve dimensions, merges, and colors; ordinary tables can export as Markdown.

The web editor supports “按内容适配列宽”. Click inside a table to adjust it from the floating toolbar, or select content spanning tables to adjust every table intersecting the selection, including tables in containers. Browser layout determines the column widths needed to avoid automatic wrapping, preserving manual line breaks, merges, and row heights. Wide tables scroll horizontally, and the entire operation can be undone in one step. It writes only the existing `colwidth`, not continuous auto-sizing or a `nowrap` attribute; there is no new API. When modifying JSON directly, continue to set consistent `colwidth` values for cells according to the actual grid. Do not promise no wrapping based on character-count estimates or add nonexistent fields such as `autoFit`.

## Images, cropping, splitting, and composition

image is an inline node; put it in paragraph or another container permitting inline content. imageBoard holds image nodes directly. Obtain the real src through upload first; never guess content IDs. src is `/assets/<32-character-id>.<extension>`, without a `/yuyan` prefix. The web UI also loads display variants according to screen width and density at `/assets/<id>-<width>.<jpg|png|hidpi.jpg>`. These may be rebuilt or disappear at any time; do not write them into src. Always use original images for downloads, checks, and exports.

- Basic attributes: src, alt, title, width, height, caption, shadow, blockAlign. caption is visible explanatory text, independent of alt/title; shadow is an optional boolean shadow border.
- crop: `{x,y,width,height}` relative to the original image, in the 0–1 range. x+width and y+height must not exceed 1; null means the whole image. sourceWidth/sourceHeight store original pixel dimensions; width/height are display dimensions. After cropping, update the display aspect ratio appropriately; the original media remains unchanged.
- Physical cropping: after extracting separate text from a mixed screenshot, crop a working copy and upload it when the text area must be removed from the uploaded media. Set the new image's `crop:null`, use its actual dimensions for `sourceWidth/sourceHeight`, set display width for readability, and use `height:null` to preserve proportions. Unlike the reading mask provided by `crop`, this makes the actual file smaller.
- Complementary splitting: reuse the same src and divide regions with nonoverlapping crop rectangles. For example, left and right halves are `{x:0,y:0,width:0.5,height:1}` and `{x:0.5,y:0,width:0.5,height:1}`. Do not modify or reupload the original image. If crop already exists, calculate within the current region.
- `imageBoard`: attrs.width and height are canvas dimensions; blockAlign positions the whole board. content contains one or more actual image nodes. Each image's placement is `{x,y,width,height}` relative to the canvas. List order also determines stacking order. Content outside the canvas is clipped.
- Resizing the canvas differs from scaling the whole composition. To preserve image pixel positions when resizing the canvas, recalculate placement for the new dimensions; scaling the whole composition can preserve proportions. Choose according to the user's intent. Batch styling only merges the same attrs into selected images and does not change unrelated images.

## Editable drawings

`drawing` is an atomic block, separate from imageBoard, which contains only images. attrs include src `/drawings/<32-character-ID>`, version 1, width 100–2400 (on initial creation, do not enlarge small drawings or exceed 800), blockAlign left/center/right, caption, and server-derived text, previewWidth, previewHeight, and previewMime. Obtain the complete node from `upload --kind drawing`; do not fabricate derived values. Display attributes can be edited individually; graphic changes require generating and uploading a new package.

Native shapes, text, bound connectors, freehand strokes, and images are supported; the package retains the Excalidraw scene. Markdown export preserves an HTML figure, preview, and source-file link; a complete export also needs the package and image files. See [Editable drawings](drawing.md) for generation, review, editing, and import across instances.

## Attachments

attachment is a block node that can be nested in tables, columns, and collapsible bodies. upload --kind attachment returns a complete node: src `/attachments/<32-character-id>`, name, size (nonnegative bytes), and mime. Empty files can be uploaded; renaming a card changes only name. Copying a node reuses the original file without another upload.

The reading page supports previews of bitmaps, PDFs, text, audio/video, and common archive directory listings. Tools can call the preview API for text/listings; use the relevant domain tools for complex formats. Treat HTML/SVG/XML attachments as source code, not executable web pages. Deleting a card does not immediately collect files still referenced by history, trash, or templates.

## Document and section links

link.attrs.href stores `/docs/<id>` or `/docs/<id>#<encoded-slug>`; the service supplies the web prefix. Find real section anchors through link-targets/preview; do not guess slugs. Moving or renaming a document does not change its ID; renaming sections or reordering same-name sections may change their slugs.

Reference links are ordinary text link marks, without Lark-style @mentions, comments, or synced blocks. Backlinks are derived from live bodies and need no manual maintenance. Inserted templates/snippets are independent content copies and do not automatically sync with their sources later.

## Compatibility and capability boundaries

Native JSON covers implemented body capabilities. Markdown is convenient for ordinary writing; content beyond Markdown is preserved through the project's existing HTML rules. Arbitrary web applications, scripts, and custom CSS are not accepted. Temporary UI states such as visual code formatting, keyboard selection, hover previews, and reading position need not be reproduced as CLI commands. Fulfill the user's intent by changing the final document structure.

During maintenance, compare nodes, attributes, marks, and actual APIs to determine whether new formats require updates to this reference's examples/validation. An unchanged schemaVersion of 1 does not mean capabilities are unchanged. Prefer the shared schema; keep only this skill's operation orchestration in scripts.

## Document calendars

`calendar` is an atomic block with no child content or marks. Each occurrence owns its periods inside the document body; copied calendars remain independent. Use document create/edit with revision checks for these blocks.

Attributes: `version: 1`, `title` (up to 120 Unicode characters), `grain: year|month|day`, `center` (an ISO date, or an empty string for today), optional booleans `collapsed` and `workdaysOnly` (both default false), optional numeric `cellWidth` (missing/null uses the grain default), optional integer `width` (280–10000 pixels; missing/null means full available width), and `periods` (up to 2,000 entries). The UI calls each period an `事件` (event). Every entry has a unique positive safe-integer `id` within that block, required `title` (1–120 characters), `note` (0–2,000 characters), `startDate`, `endDate`, `precision`, and `color`. Dates are inclusive ISO dates from 1000 through 9999. Year precision requires January 1 and December 31 boundaries; month precision requires the first and last days of its boundary months. Colors: `emerald`, `blue`, `violet`, `amber`, `rose`, `cyan`, `slate`, `lime`. Periods may overlap. IDs have no meaning outside their own component.

```json
{"type":"calendar","attrs":{"version":1,"title":"学习与休整","grain":"month","center":"2026-10-18","periods":[{"id":1,"title":"专注学习","note":"完成基础课程","startDate":"2026-09-01","endDate":"2026-12-31","precision":"month","color":"blue"},{"id":2,"title":"休整","note":"与学习状态重叠","startDate":"2026-10-16","endDate":"2026-10-25","precision":"day","color":"rose"}]}}
```

To edit a calendar, read the block from the full snapshot, preserve its other attributes and period IDs, and replace `attrs.periods` in one document patch. Rename through `attrs.title`; set the default ruler cell width through `attrs.cellWidth` in pixels (year 56–240, month 48–220, day 36–180; defaults 88/80/48). Editing zoom saves this attribute with document undo; reading reopens at the saved width and any reading zoom stays local. Changing the configured grain in the editor resets width to its grain default. Set the component width through `attrs.width`, or reset it with null. The UI defaults to the full page area before the sidebar/pinned outline and clamps saved widths to available space. Editing offers left/right resize handles with one-step undo on release, cancel without writes, and double-click to restore full width. Nested calendars stay within their parent. Fold/unfold through `attrs.collapsed: true|false`, preserving every event. Set `attrs.workdaysOnly: true` to count only Monday through Friday in displayed day totals; false/missing counts all inclusive dates. Weekends are excluded, with no holiday or compensatory-workday adjustment. A weekend-only event displays 0 workdays. The editor exposes `仅统计工作日`; reading uses the saved setting. Month/year duration labels, date ranges, movement spans, and quick-duration buttons keep their calendar-unit meaning. `schema --node calendar` discovers defaults; `validate`, `create`, and `edit` reuse the project's calendar validator. Keyword reads include titles, dates, and notes. Export embeds the complete model, including collapse state, default cell width, component width, and workday counting, in a `section[data-calendar]` HTML block with a readable fallback table; retain `data-calendar-content` for editable reimport. The interactive reading page hides that source table and uses its event list for browsing and search. Document history, templates, snippets, copies, and native backup preserve the block. Once used, rollback requires a program that recognizes `calendar`; older calendar programs may discard collapse state, width settings, or workday counting when editing, so use a program that recognizes these attributes.

### Calendar clipboard strings

The component's `复制日历` action exports `YYCAL1:` plus compact JSON `[title, grain, center, periods, cellWidth?, width?, workdaysOnly?]`. Grain is `y|m|d`; center is an ISO date or empty for today. The optional fifth field carries the saved cell width in pixels; four-field strings remain valid and use the grain default. The optional sixth field carries component width; use null for the fifth field when only component width is set. Missing/null component width opens at full width. The optional seventh field is boolean `workdaysOnly`: true enables workday counting, false/missing counts all dates. Use null placeholders for unset widths before this field; legacy four-to-six-field strings remain valid, and encoding omits a false trailing setting. For example, `YYCAL1:["项目","d","",[["冲刺","2026-10-23","2026-10-26"]],null,null,true]` counts 2 workdays across the four-date Friday-to-Monday range. Each period is `[title, start, end?, color?, note?]`. Dates use `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` and retain precision. End has the same precision; empty/missing end means the starting unit. Empty/missing color means `emerald`; missing note means empty. Trailing empty fields are omitted. JSON escaping preserves all text and multiline notes in one line. IDs, revisions, timestamps, and collapse state do not travel; decoding assigns local sequential IDs and an expanded calendar. Unknown versions and invalid content fail without mutation.

Example: `YYCAL1:["学习与休整","m","2026-10-18",[["专注学习","2026-09","2026-12","blue","完成基础课程"],["休整","2026-10-16","2026-10-25","rose","与学习状态重叠"]]]`.

`calendar --input FILE --format string|json [--out FILE]` converts locally, using Yuyan's actual codec and validator through `document.mjs`; `--format` specifies the output format. String output accepts one `calendar` node JSON; JSON output accepts a complete clipboard string and produces one insertable `calendar` node. Output files must be new; stdin is supported. There is no service connection or write. Use normal revisioned document edits to insert or replace the decoded node; see [editing](editing.md#calendar-string-transfer).

In the UI, reading and editing both allow copying. Editing imports directly from the clipboard into that component with one-step undo, without a preview or confirmation; clipboard/read errors alone open a correction prompt. Valid pending edits are preserved before replacement; incomplete pending edits stay visible until completed.

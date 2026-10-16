# Editable drawings

Use for trees, data pages, scan paths, architecture, and transaction diagrams requiring a specified spatial layout. Prefer native document blocks for ordinary explanations, SQL, and tables; use Mermaid for automatically laid-out flows. `imageBoard` only composes images, while `drawing` stores editable graphics; they are not interchangeable.

## Generate, review, and insert

Drawing generation uses Yuyan's own Excalidraw adapter, avoiding manually populated internal fields such as random seeds and versions. On first use, prepare the browser and a build from committed source as described in the preview reference; do not reinstall existing dependencies:

```sh
node "$YUYAN_DOC" preview-setup
node "$YUYAN_DOC" drawing --input "$work_dir/spec.json" --out "$work_dir/drawing"
node "$YUYAN_DOC" upload --kind drawing --input "$work_dir/drawing/drawing.yuyan.json" --dry-run
node "$YUYAN_DOC" upload --kind drawing --input "$work_dir/drawing/drawing.yuyan.json"
```

`drawing` defaults to Chromium and supports `--browser webkit`; the default total deadline is 60000 milliseconds. Generation starts only a temporary local instance, restricts browser access to the same origin, and neither connects to production nor modifies user documents. It reuses the `preview-setup` cache and fails immediately if it is missing or stale relative to source, without implicit builds or installation. The output directory must not exist. It contains the package, preview, and required images; the result reports package/image byte counts and searchable text. The package already contains the preview, so do not count the preview file size again when calculating long-term storage use.

Simple input: `{"template":"tree"}`. Templates support `page` (data page), `tree` (B+ tree), `scan` (index scan), and `timeline` (transaction timeline). A blank canvas is for interactive drawing and cannot be persisted as an element-free package. You can also replace template with an `elements` array using Excalidraw element skeletons:

```json
{
  "background": "#ffffff",
  "elements": [
    {"id":"root","type":"rectangle","x":20,"y":20,"width":160,"height":70,"label":{"text":"索引页"}},
    {"id":"leaf","type":"rectangle","x":20,"y":180,"width":160,"height":70,"label":{"text":"数据页"}},
    {"id":"edge","type":"arrow","x":100,"y":90,"width":0,"height":90,"points":[[0,0],[0,90]],"start":{"id":"root"},"end":{"id":"leaf"}}
  ]
}
```

When images are needed, `files` uses the engine's BinaryFiles (fileId, dataURL, mimeType, created), with image elements referencing fileId. Only PNG/JPEG/GIF/WebP/BMP are supported. Base64 is used only in memory during generation/editing and in standalone exports; images in uploaded packages use Yuyan content-addressed references.

Actually inspect the preview first, checking Chinese text, numbers, arrow directions, endpoints, and legends. View SVG in a browser or PNG with an image tool. If whole-document layout needs checking, preview the relevant section after insertion as described in the preview reference. Successful generation does not replace checking the diagram's meaning.

Generated previews use a fixed 1x export scale; dimensions do not vary with device pixel density. SVG uses XML serialization, preserving nonbreaking spaces and frame clipping. If an older web page reports `unsupported or unsafe SVG preview` even for simple graphics on a high-density screen, first preserve the unapplied drawing through “下载 → 可编辑文件”, then load the fixed web page and restore the draft or import the file. Update the CLI generation cache with `preview-setup` against committed Yuyan source as well. Do not manually change preview dimensions or disable server-side safety validation to bypass the error.

upload first reads images beside the package and verifies their hashes, then uploads the images and package and returns a complete `node`. `--dry-run` checks only local input and does not connect to production. Next, `read --out` the current document and insert the whole block with `edit` splice/replace operations; use create for a new document. The server checks the package, derived text, and preview attributes; do not fabricate src/text to bypass upload.

## Editing and reading

- Use `schema --node drawing` to inspect attributes. `read --scope keyword` can match derived text inside a drawing and return the containing drawing.
- For display changes, edit only width (100–2400), blockAlign (left/center/right), and caption; do not change src or derived fields.
- To edit graphics, open the drawing in the web UI, or read `api --path drawings/ID`, modify elements, regenerate, and review. Upload the new package and replace only the original node, preserving caption, width, and alignment.
- Text inside drawings does not directly participate in body text replacement. Do not modify derived text to simulate changing a diagram; new text must enter the scene and its preview must be rebuilt.
- Copies within the same instance can reuse the original package. Across instances, upload the complete package and dependencies; do not directly reuse another instance's media URLs.

## Export, preview, and compatibility

A single-document export includes native JSON, Markdown/HTML, drawing packages, one copy of each preview, and images. Drawing files are `<ID>.yuyan.json`, with images in the same directory; the HTML figure preserves preview and source-file links. `download --src /drawings/ID/file|preview --out FILE` downloads the corresponding content. Download standalone `.excalidraw` files through “可编辑文件” in the web drawing UI; required images are temporarily embedded in them.

Use project import tools to reimport a complete Markdown folder, rehearsing only on an empty isolated instance. For partial restoration into an existing knowledge base, use upload plus revision-protected edit; do not reimport a whole library over existing edits. Stop on missing source files, missing images, or hash mismatches.

`preview --media-dir <export-directory-or-attachments-directory> --offline` can reuse local packages and images. Remote reads only GET actual media from the snapshot's instance. Mismatched packages/images are rejected for preview. For unknown format/engine versions, retain the original package and stop writes; do not delete unknown content. The service may still provide a safe static preview.

Drawing packages and dependent images are protected by references in bodies, trash, history, and templates. The one-hour grace period for unreferenced packages also protects their images. Insert uploads into documents promptly; unreferenced media is not long-term storage. Redrawing existing images requires separate review of each image; placing images inside a drawing does not by itself reduce bitmap storage.

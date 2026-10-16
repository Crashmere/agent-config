# Local reading page preview

Use only when this change requires judging actual layout or the user requests visual acceptance. Deliver ordinary writing directly after `verified:true`; do not automatically add a preview.

## Initial setup and version updates

Preview reuses Yuyan's Go program, Vue reading page, CSS, formulas, and diagram enhancements; it does not implement another HTML renderer. Install optional browser dependencies only in this skill directory and maintain them through software-installation; do not add them to Yuyan's package.json. Skip installation when dependencies and browsers already exist:

```sh
skill_dir="$HOME/agent-config/skills/yuyan-doc"
npm --prefix "$skill_dir" ci --ignore-scripts
# Run only if the browser is not installed; do not reinstall for every preview.
node "$skill_dir/node_modules/playwright/cli.js" install webkit
node "$YUYAN_DOC" preview-setup
```

macOS/Linux arm64 and x64 are supported. The default is WebKit; use `--browser chromium` if desired after installing the corresponding Playwright browser. `preview-setup` requires committed code in the Yuyan checkout, existing web dependencies installed from the lockfile, and an available Go toolchain and module cache. It does not download the Go toolchain/modules or install npm dependencies. It exports an isolated source copy from Git, reuses the original web/node_modules, and builds only in the copy. The project directory remains read-only.

The build cache defaults to `~/.cache/yuyan-doc/preview` and honors `XDG_CACHE_HOME`; override it with `YUYAN_PREVIEW_CACHE`. Cache keys include the OS, architecture, and Go/web source-tree fingerprints; documentation-only changes do not trigger a rebuild. Run `preview-setup` again after code changes; cache hits return immediately. Normal `preview` fails immediately if the build is missing or stale, without building on demand.

The report records the build's source commit and fingerprint. It verifies layout in the local version, not whether that version is deployed. For exact comparison with the production page, first confirm matching code from project release records; do not repeatedly check deployment for every document preview.

## Preview from a saved snapshot

```sh
# Captures the first 1280×900 viewport by default; out must be a new directory.
node "$YUYAN_DOC" preview --snapshot "$work_dir/after.json" --out "$work_dir/preview"

# Check only the section starting at top-level heading path=3; collect only images referenced in that section.
# One startup and one media preparation produce the two required viewports.
node "$YUYAN_DOC" preview --snapshot "$work_dir/after.json" \
  --scope section --path 3 --viewport 1280x900,375x667 \
  --media-dir "$work_dir/images" --out "$work_dir/section-preview"
```

- Input must be the full original snapshot from `read/create/edit --out`; the script checks integrity. It neither rereads the remote body nor modifies the snapshot. Only documents are previewed, not tree groups.
- `--scope` is `full` (default) or `section`; section paths follow the editing reference. `--viewport` accepts at most four distinct sizes, with width 320–3840 and height 320–2160. Explicitly request narrow screens when needed; checking both desktop and mobile is not the default.
- By default, capture only the viewport. Add `--full-page` only when checking the entire selected scope. Collapsible blocks retain the document's collapsed state; a screenshot does not imply hidden content was visually inspected.
- `--theme light|dark` defaults to light; `--browser webkit|chromium` defaults to webkit.
- The default total preview deadline is 45 seconds; build preparation defaults to 180 seconds. `--timeout` accepts 1000–600000 milliseconds, not 0. There are no implicit retries.

## Media and connections

Prefer reusing local image files, verifying their content hashes against Yuyan media IDs. Prepare images only once for repeated references or multiple viewports. Fetch missing images with at most four concurrent reads; each retains the platform's 25 MiB limit.

- `--media-dir DIR` searches `DIR/<media-ID>.<extension>`, `DIR/assets/...`, or `DIR/attachments/...`, supporting already-downloaded media and single-document export directories.
- If originals retain their original filenames, use `--media-map FILE`: a JSON object maps `/assets/<ID>.png` to file paths, with relative paths resolved from the map file's directory. Missing specified files or incorrect hashes cause errors; images are not silently substituted.
- If no local image is found, reuse the original task's `--server`/`--ssh`/authentication parameters to GET only the needed images from the snapshot's service. Do not download externally linked images, read the remote full body, or write to the original service. Remote reads still follow server-operations connection rules.
- `--offline` completely disables connections to the original service and fails immediately if local images are missing. With no images or all media available locally, the original service is not contacted even without this option.
- For drawings, read the exact original package and verify its content hash, register the package and dependencies again in the temporary instance, and use the same static preview. `--media-dir` supports packages and images directly in that directory or its attachments subdirectory; `/drawings/ID/file` in a map can explicitly specify the package. Missing local files are read only as media from the snapshot's service; offline mode fails immediately. Unknown versions cannot be reimported locally; retain source files and update the program.
- Attachments retain the node's name, size, and MIME and use local placeholder resources to display cards, without downloading actual attachments. Attachment previews, download contents, and text-link targets are not checked.

## Output and stopping conditions

The output directory contains `<width>x<height>.png` and `report.json`, with directory mode 0700 and file mode 0600; existing paths are not overwritten. View screenshots directly with `view_image` rather than taking another screenshot through browser MCP. Success, failure, timeout, or Ctrl+C all close the browser, temporary service, and tunnel, then delete the temporary database and media. Output screenshots and reports remain for inspection. Forced SIGKILL or host power loss prevents cleanup.

The report includes source document revision, build provenance, media source counts, screenshot scope, image dimensions, loading/rendering errors, and warnings. The browser permits only GET/HEAD access to the temporary instance, with no access to production, external addresses, or other local services. Screenshots wait for formulas and Mermaid to render and for fonts and images to be ready.

- `rendered:true` means screenshots were produced for the selected viewports. `checksPassed:true` means no loading or rendering errors were detected; **it does not mean layout has passed visual acceptance**. Inspect screenshots relevant to this change, then stop.
- Image failures, formula/diagram errors, unexpected network requests, or page errors produce a nonzero exit code. The error receipt's `preview` points to the existing report and screenshots; do not rewrite the document.
- Horizontal page overflow and browser ResizeObserver loop notifications are recorded as warnings. Do not hide them or automatically treat them as layout failures; use screenshots to judge their impact on this task's goal.
- Follow the editing stopping rules for missing dependencies, stale builds, or preview failures. Do not install an environment on the spot or expand optional checks into site-wide troubleshooting. Report honestly if user-requested acceptance or known defects remain unresolved.

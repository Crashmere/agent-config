import { createHash } from 'node:crypto';
import { access, mkdir, mkdtemp, readFile, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { connect, assert, Failure, jsonInput, outputFile, json } from './runtime.mjs';
import { formatTools, hash, select, walk } from './document.mjs';
import { sourceInfo, preparedBinary, preparePreview, browserEngine, localInstance, stopChild } from './preview-runtime.mjs';

export async function previewCommand(options, setup = false) {
  const timeout = Number(options.timeout ?? (setup ? 180000 : 45000));
  assert(Number.isSafeInteger(timeout) && timeout >= 1000 && timeout <= 600000, 'Preview timeout must be 1000–600000 ms (default: 45000; setup: 180000).');
  assert(!options['dry-run'], 'preview and preview-setup do not accept --dry-run; preview only writes an isolated local instance.');
  const controller = new AbortController(), { signal } = controller;
  const interrupted = () => controller.abort(new Failure('preview_interrupted', 'Preview interrupted; temporary processes and data will be cleaned up.'));
  const timer = setTimeout(() => controller.abort(new Failure('preview_timeout', `Preview exceeded ${timeout} ms.`)), timeout);
  process.once('SIGINT', interrupted); process.once('SIGTERM', interrupted);
  try {
    const engine = browserEngine(options.browser);
    try { await access(engine.executablePath()); }
    catch { throw new Failure('preview_browser_missing', 'The selected Playwright browser is not installed. See references/preview.md; previews never install it automatically.'); }
    return setup ? await preparePreview(options, signal) : await renderPreview(options, engine, signal, timeout);
  } catch (error) { throw signal.aborted ? Object.assign(signal.reason, { details: error.details || {} }) : error; }
  finally { clearTimeout(timer); process.removeListener('SIGINT', interrupted); process.removeListener('SIGTERM', interrupted); }
}

async function renderPreview(options, engine, signal, timeout) {
  assert(options.snapshot && options.snapshot !== '-' && options.out, 'preview requires --snapshot FILE and --out NEW_DIRECTORY.');
  assert(!options.scope || ['full', 'section'].includes(options.scope), 'Preview scope must be full or section (with --path of a top-level heading).');
  const viewports = (options.viewport || '1280x900').split(',').map(value => {
    const match = /^(\d+)x(\d+)$/.exec(value);
    assert(match, '--viewport must be WIDTHxHEIGHT, or a comma-separated list.');
    const width = Number(match[1]), height = Number(match[2]);
    assert(width >= 320 && width <= 3840 && height >= 320 && height <= 2160, 'Viewport must be within 320–3840 by 320–2160.');
    return { width, height };
  });
  assert(viewports.length <= 4 && new Set(viewports.map(v => `${v.width}x${v.height}`)).size === viewports.length, 'Use at most four distinct viewports.');
  const theme = options.theme || 'light'; assert(['light', 'dark'].includes(theme), '--theme must be light or dark.');
  const original = await jsonInput(options.snapshot);
  assert(original.kind === 'yuyan-doc-snapshot' && original.version === 1 && original.hash === hash(original.document), 'Invalid or manually modified snapshot. Use the unmodified --out snapshot from read/create/edit.');
  assert(original.document.kind === 'doc', 'Only documents have a reading-page preview.');
  const info = await sourceInfo(options), manifest = await preparedBinary(info), fmt = await formatTools(info.repo);
  const selection = select(original.document.content, options);
  const content = structuredClone(options.scope === 'section' ? { type: 'doc', content: selection.content } : original.document.content);
  fmt.validate(content);
  const map = options['media-map'] ? await jsonInput(options['media-map']) : {};
  assert(map && typeof map === 'object' && !Array.isArray(map) && Object.values(map).every(v => typeof v === 'string'), '--media-map must map app-relative image URLs to local file paths.');
  const directory = resolve(options.out);
  await mkdir(dirname(directory), { recursive: true, mode: 0o700 });
  await mkdir(directory, { mode: 0o700 }); // Exclusive ownership; never overwrite a previous run.
  let work, local, remote, remotePromise, browser;
  const report = { rendered: false, checksPassed: false, visualReviewRequired: true, sourceDocument: { id: original.document.id, revision: original.document.revision }, renderer: { ...manifest, productionVersionChecked: false }, scope: options.scope || 'full', ...(options.scope === 'section' ? { path: options.path } : {}), browser: options.browser || 'webkit', theme, media: { local: 0, downloaded: 0, attachmentCards: 0 }, views: [], issues: [], warnings: [], limitations: ['Local body layout only; production authentication, link targets, directory/backlinks and attachment contents are not checked.'] };
  const started = performance.now();
  const closeBrowser = () => { void browser?.close().catch(() => {}); };
  const killOnExit = () => { if (local?.child.pid) { try { process.kill(-local.child.pid, 'SIGTERM'); } catch {} } };
  process.once('exit', killOnExit);
  try {
    work = await mkdtemp(join(tmpdir(), 'yuyan-preview-'));
    local = await localInstance(info.binary, join(work, 'data'), signal);
    const entries = walk(content);
    const images = [...new Set(entries.filter(e => e.node.type === 'image').map(e => e.node.attrs.src))];
    const imageBytes = async src => {
      assert(/^\/assets\/[0-9a-f]{32}\.(png|jpg|gif|webp|bmp)$/.test(src), 'Preview only accepts native Yuyan image URLs.');
      const mapped = map[src] && resolve(dirname(resolve(options['media-map'])), map[src]);
      const candidates = mapped ? [mapped] : options['media-dir'] ? [join(resolve(options['media-dir']), basename(src)), join(resolve(options['media-dir']), 'assets', basename(src)), join(resolve(options['media-dir']), 'attachments', basename(src))] : [];
      for (const file of candidates) {
        try {
          const details = await stat(file);
          assert(details.isFile() && details.size <= 25 * 1024 ** 2, 'Local preview image must be a file of at most 25 MiB.');
          const bytes = await readFile(file); report.media.local++; return bytes;
        } catch (error) { if (error.code !== 'ENOENT' || mapped) throw error; }
      }
      assert(!options.offline, `Missing local image ${src}; provide --media-map/--media-dir or omit --offline.`, 'preview_media_missing');
      remotePromise ??= connect(options, { manageSignals: false, signal }).then(client => {
        remote = client;
        assert(original.source === client.source, 'Snapshot belongs to another service. Use the original connection options before downloading images.', 'preview_source_mismatch');
        return client;
      });
      const client = await remotePromise;
      const response = await client.request(src.slice(1), { raw: true }); // Only GET image bytes, never GET the document or write upstream.
      const chunks = []; let size = 0;
      for await (const chunk of response.body) { size += chunk.length; assert(size <= 25 * 1024 ** 2, 'Preview image exceeds 25 MiB.'); chunks.push(chunk); }
      report.media.downloaded++; return Buffer.concat(chunks);
    };
    // Small bounded batches; duplicate references and multiple viewports reuse each image.
    for (let start = 0; start < images.length; start += 4) {
      const results = await Promise.allSettled(images.slice(start, start + 4).map(async src => {
        const bytes = await imageBytes(src);
        assert(createHash('sha256').update(bytes).digest('hex').slice(0, 32) === basename(src).split('.')[0], `Image content does not match its Yuyan ID: ${src}`, 'preview_media_mismatch');
        const form = new FormData(); form.append('file', new Blob([bytes]), basename(src));
        const uploaded = await local.request('api/assets', { method: 'POST', body: form });
        assert(uploaded.url === src, 'Local renderer changed the image identity.', 'preview_media_mismatch');
      }));
      const failed = results.find(r => r.status === 'rejected'); if (failed) throw failed.reason;
    }
    const drawings = entries.filter(e => e.node.type === 'drawing');
    for (const { node } of drawings) {
      const id = node.attrs.src.split('/').pop();
      const mapped = map[node.attrs.src + '/file'] && resolve(dirname(resolve(options['media-map'])), map[node.attrs.src + '/file']);
      const candidates = mapped ? [mapped] : options['media-dir'] ? [join(resolve(options['media-dir']), id + '.yuyan.json'), join(resolve(options['media-dir']), 'attachments', id + '.yuyan.json')] : [];
      let bytes;
      for (const file of candidates) {
        try {
          const info = await stat(file); assert(info.isFile() && info.size <= 12 * 1024 ** 2, 'Drawing package exceeds 12 MiB.');
          bytes = await readFile(file); report.media.local++; break;
        } catch (error) { if (error.code !== 'ENOENT' || mapped) throw error; }
      }
      if (!bytes) {
        assert(!options.offline, `Missing offline drawing ${id}.`);
        remotePromise ??= connect(options, { manageSignals: false, signal }).then(client => { remote = client; assert(original.source === client.source, 'Snapshot belongs to another service.', 'preview_source_mismatch'); return client; }); remote = await remotePromise;
        const response = await remote.request(`drawings/${id}/file`, { raw: true });
        const chunks = []; let size = 0;
        for await (const chunk of response.body) { size += chunk.length; assert(size <= 12 * 1024 ** 2, 'Drawing package exceeds 12 MiB.'); chunks.push(chunk); }
        bytes = Buffer.concat(chunks); report.media.downloaded++;
      }
      assert(createHash('sha256').update(bytes).digest('hex').slice(0, 32) === id, 'Drawing package identity mismatch.');
      const pkg = JSON.parse(bytes.toString('utf8'));
      for (const file of Object.values(pkg.files)) {
        const data = await imageBytes(file.src);
        assert(createHash('sha256').update(data).digest('hex').slice(0, 32) === basename(file.src).split('.')[0], 'Drawing image identity mismatch.');
        const form = new FormData(); form.append('file', new Blob([data]), basename(file.src));
        const uploaded = await local.request('api/assets', { method: 'POST', body: form });
        assert(uploaded.url === file.src, 'Drawing dependency changed in local preview.');
      }
      const published = await local.request('api/drawings', { method: 'POST', body: pkg });
      assert(published.attrs.text === node.attrs.text && published.attrs.previewWidth === node.attrs.previewWidth && published.attrs.previewHeight === node.attrs.previewHeight, 'Drawing preview metadata mismatch.');
      node.attrs.src = published.attrs.src;
    }
    const attachments = entries.filter(e => e.node.type === 'attachment');
    if (attachments.length) {
      // Card name/size/MIME come from the original node. Real bytes are unnecessary for screenshots.
      const form = new FormData(); form.append('file', new Blob(['Local preview placeholder; attachment body omitted.']), 'preview.txt');
      const placeholder = await local.request('api/attachments', { method: 'POST', body: form });
      for (const { node } of attachments) node.attrs.src = placeholder.url;
      report.media.attachmentCards = attachments.length;
    }
    const book = await local.request('api/books', { method: 'POST', body: { name: 'Preview' } });
    const doc = await local.request('api/docs', { method: 'POST', body: { bookId: book.id, kind: 'doc', title: original.document.title, content } });
    assert(hash(fmt.schema.nodeFromJSON(doc.content).toJSON()) === hash(fmt.schema.nodeFromJSON(content).toJSON()), 'Local preview did not preserve the selected content.', 'preview_content_mismatch');
    signal.throwIfAborted();
    browser = await engine.launch({ headless: true, timeout: Math.min(timeout, 15000) });
    signal.addEventListener('abort', closeBrowser, { once: true }); signal.throwIfAborted();
    const counts = { math: entries.filter(e => ['inlineMath', 'blockMath'].includes(e.node.type)).length, mermaid: entries.filter(e => e.node.type === 'codeBlock' && fmt.normalizeLanguage(e.node.attrs?.language || '') === 'mermaid').length };
    for (const viewport of viewports) {
      signal.throwIfAborted();
      const context = await browser.newContext({ viewport, colorScheme: theme, isMobile: viewport.width < 600, hasTouch: viewport.width < 600, serviceWorkers: 'block' });
      try {
        await context.addInitScript(theme => localStorage.setItem('yuyan:theme', theme), theme);
        // Browser traffic never reaches production, third-party media, or other local services.
        await context.route('**/*', async route => {
          const url = new URL(route.request().url());
          if (url.origin === local.origin && ['GET', 'HEAD'].includes(route.request().method())) return route.continue();
          report.issues.push({ type: 'blocked_request', resource: `${url.protocol}//${url.host}${url.pathname}` });
          await route.abort();
        });
        const page = await context.newPage(); page.setDefaultTimeout(Math.min(timeout, 15000));
        page.on('pageerror', error => {
          const item = { type: 'page_error', viewport, message: error.message };
          if (/^ResizeObserver loop (completed with undelivered notifications\.|limit exceeded)$/.test(error.message)) report.warnings.push(item);
          else report.issues.push(item);
        });
        page.on('response', response => { if (response.status() >= 400) report.issues.push({ type: 'http_error', status: response.status(), path: new URL(response.url()).pathname }); });
        page.on('requestfailed', request => report.issues.push({ type: 'request_failed', path: new URL(request.url()).pathname, message: request.failure()?.errorText }));
        await page.goto(`${local.origin}/yuyan/docs/${doc.id}`, { waitUntil: 'load' });
        await page.locator('.yy-content').waitFor();
        await page.waitForFunction(({ math, mermaid }) => {
          const root = document.querySelector('.yy-content');
          const formulas = [...root.querySelectorAll('[data-type="inline-math"], [data-type="block-math"]')];
          return formulas.length === math && formulas.every(e => e.querySelector('.katex, .katex-error')) && root.querySelectorAll('.yy-mermaid > svg, .yy-mermaid-error').length === mermaid;
        }, counts);
        const checks = await page.evaluate(async () => {
          const root = document.querySelector('.yy-content');
          await document.fonts.ready;
          const images = [...root.querySelectorAll('img')];
          for (const image of images) image.loading = 'eager';
          const failures = [];
          await Promise.all(images.map(async image => { try { await image.decode(); } catch { failures.push(image.getAttribute('src')); } }));
          await new Promise(ok => requestAnimationFrame(() => requestAnimationFrame(ok)));
          return { pageWidth: document.documentElement.scrollWidth, viewportWidth: innerWidth, imageCount: images.length, failedImages: failures, renderErrors: [...root.querySelectorAll('.katex-error, .yy-mermaid-error')].map(e => e.getAttribute('title') || e.textContent), images: images.map(e => ({ src: e.getAttribute('src'), naturalWidth: e.naturalWidth, naturalHeight: e.naturalHeight, width: e.getBoundingClientRect().width, height: e.getBoundingClientRect().height })) };
        });
        for (const message of checks.renderErrors) report.issues.push({ type: 'content_render_error', viewport, message });
        if (checks.failedImages.length) report.issues.push({ type: 'image_decode_failed', viewport, images: checks.failedImages });
        if (checks.pageWidth > viewport.width + 1) report.warnings.push({ type: 'page_overflow', viewport, width: checks.pageWidth });
        const screenshot = await outputFile(join(directory, `${viewport.width}x${viewport.height}.png`), await page.screenshot({ fullPage: !!options['full-page'], animations: 'disabled' }));
        report.views.push({ viewport, screenshot, fullPage: !!options['full-page'], ...checks });
      } finally { await context.close(); }
    }
    report.rendered = true; report.checksPassed = report.issues.length === 0;
    if (!report.checksPassed) throw new Failure('preview_check_failed', 'Preview images were produced, but rendering errors need attention. Inspect report.json and the screenshots.');
  } catch (error) {
    report.error = { code: signal.aborted ? signal.reason.code : error.code || 'preview_failed', message: signal.aborted ? signal.reason.message : error.message };
    error.details = { ...error.details, preview: { directory, report: join(directory, 'report.json'), screenshots: report.views.map(v => v.screenshot) } };
    throw error;
  } finally {
    signal.removeEventListener('abort', closeBrowser); process.removeListener('exit', killOnExit);
    try { await browser?.close(); } finally {
      try { await stopChild(local?.child); } finally {
        remote?.close(); if (work) await rm(work, { recursive: true, force: true });
        report.elapsedMs = Math.round(performance.now() - started);
        await outputFile(join(directory, 'report.json'), json(report));
      }
    }
  }
  return { directory, report: join(directory, 'report.json'), rendered: report.rendered, checksPassed: report.checksPassed, visualReviewRequired: true, screenshots: report.views.map(v => v.screenshot), media: report.media, warningCount: report.warnings.length, elapsedMs: report.elapsedMs };
}

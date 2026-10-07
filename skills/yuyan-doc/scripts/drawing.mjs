import { access, mkdir, mkdtemp, readFile, rm } from 'node:fs/promises';
import { basename, dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import { assert, jsonInput, outputFile, json } from './runtime.mjs';
import { sourceInfo, preparedBinary, browserEngine, localInstance, stopChild } from './preview-runtime.mjs';

export async function uploadDrawing(options, client) {
  assert(options.input && options.input !== '-', 'Drawing upload requires a package file beside its image dependencies.');
  const file = resolve(options.input), pkg = await jsonInput(file);
  assert(pkg.format === 'yuyan-drawing' && pkg.version === 1 && pkg.engineVersion === '0.18.1', 'Unsupported drawing package; use drawing or a Yuyan export.');
  const images = [];
  for (const [id, image] of Object.entries(pkg.files || {})) {
    assert(/^\/assets\/[0-9a-f]{32}\.(png|jpg|gif|webp|bmp)$/.test(image.src), 'Invalid drawing image reference.');
    const data = await readFile(join(dirname(file), basename(image.src)));
    assert(createHash('sha256').update(data).digest('hex').slice(0, 32) === basename(image.src).split('.')[0], 'Drawing image differs from its content-addressed name.');
    images.push({ id, data, image });
  }
  if (options['dry-run']) return { dryRun: true, kind: 'drawing', images: images.length, packageBytes: (await readFile(file)).length };
  for (const { id, data, image } of images) {
    const form = new FormData(); form.append('file', new Blob([data]), basename(image.src));
    const asset = await client.request('api/assets', { method: 'POST', body: form });
    pkg.files[id] = { src: asset.url, mimeType: asset.mime };
  }
  const node = await client.request('api/drawings', { method: 'POST', body: pkg });
  return { node, hint: 'Insert this block into a document/template with create/edit. Its immutable source and image dependencies are protected together; unreferenced uploads have a one-hour grace period.' };
}

// Source shapes and generated previews share the interactive browser adapter. A
// temporary local instance receives uploads; the configured production server is
// never contacted. The returned package is reviewed before a separate upload/edit.
export async function generateCommand(options) {
  assert(options.input && options.out, 'drawing needs --input spec.json and --out NEW_DIRECTORY.');
  assert(!options['dry-run'], 'drawing already generates local files only; review them before a separate upload.');
  const spec = await jsonInput(options.input), info = await sourceInfo(options);
  await preparedBinary(info);
  const engine = browserEngine(options.browser || 'chromium');
  await access(engine.executablePath());
  const timeout = Number(options.timeout || 60000);
  assert(Number.isInteger(timeout) && timeout >= 1000 && timeout <= 600000, 'drawing timeout must be 1000–600000 ms.');
  const controller = new AbortController(), timer = setTimeout(() => controller.abort(), timeout);
  const interrupted = () => controller.abort();
  process.once('SIGINT', interrupted); process.once('SIGTERM', interrupted);
  let work, local, browser;
  try {
    work = await mkdtemp(join(tmpdir(), 'yuyan-drawing-'));
    local = await localInstance(info.binary, join(work, 'data'), controller.signal);
    browser = await engine.launch({ headless: true });
    controller.signal.addEventListener('abort', () => { void browser?.close(); }, { once: true });
    const page = await browser.newPage(); page.setDefaultTimeout(timeout);
    await page.route('**/*', route => new URL(route.request().url()).origin === local.origin ? route.continue() : route.abort());
    await page.goto(local.origin + '/yuyan/');
    const meta = await local.request('api/meta');
    assert(meta.drawingTool?.module, 'Prepared Yuyan build has no drawing generator; update source and run preview-setup.');
    const pkg = await page.evaluate(async ({ spec, module }) => {
      const engine = await import('/yuyan/static/' + module);
      return engine.generate(spec);
    }, { spec, module: meta.drawingTool.module });
    const node = await local.request('api/drawings', { method: 'POST', body: pkg });
    const id = node.attrs.src.split('/').pop();
    const response = await fetch(local.origin + '/yuyan/drawings/' + id + '/file', { signal: controller.signal });
    assert(response.ok, 'Generated package could not be exported.');
    const packageData = Buffer.from(await response.arrayBuffer()), stored = JSON.parse(packageData.toString('utf8'));
    const out = resolve(options.out); await mkdir(dirname(out), { recursive: true, mode: 0o700 }); await mkdir(out, { mode: 0o700 });
    await outputFile(join(out, 'drawing.yuyan.json'), packageData);
    await outputFile(join(out, stored.preview.mime === 'image/png' ? 'preview.png' : 'preview.svg'), stored.preview.mime === 'image/png' ? Buffer.from(stored.preview.data, 'base64') : stored.preview.data);
    let bytes = 0;
    for (const file of Object.values(stored.files)) {
      const response = await fetch(local.origin + '/yuyan' + file.src, { signal: controller.signal });
      assert(response.ok, 'Generated drawing image could not be exported.');
      const data = Buffer.from(await response.arrayBuffer()); bytes += data.length;
      await outputFile(join(out, basename(file.src)), data);
    }
    return { directory: out, generated: true, productionWritten: false, packageBytes: packageData.length, imageBytes: bytes, text: stored.text, hint: 'Review preview and labels/connections, then upload --kind drawing and insert the returned node with revision-protected edit.' };
  } finally {
    clearTimeout(timer); process.removeListener('SIGINT', interrupted); process.removeListener('SIGTERM', interrupted);
    await browser?.close(); await stopChild(local?.child); if (work) await rm(work, { recursive: true, force: true });
  }
}

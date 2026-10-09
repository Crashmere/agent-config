#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { openAsBlob, createWriteStream } from 'node:fs';
import { stat, rm, lstat } from 'node:fs/promises';
import { basename, resolve } from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { connect, Failure, assert, input, jsonInput, outputFile, json, positiveID } from './runtime.mjs';
import { formatTools, applyPatch, select, walk, hash, canonical } from './document.mjs';

const help = `Yuyan personal document tool (Node >=22; no dependencies installed by this command).

node <skill>/scripts/yuyan-doc.mjs <command> [options]

doctor                              Check local schema and service connection
schema [--node TYPE]                 Describe actual node/mark attributes
api --path PATH [--method GET]       Existing JSON API; PATH is relative to api/
    [--input body.json] [--confirm]  See references/api.md for allowed writes
read --doc ID_OR_URL [--out snapshot.json]
    [--scope full|outline|node|section|keyword] [--path 2/0] [--keyword TEXT]
    [--format json|markdown]        Snapshot always contains complete original JSON
validate --input FILE [--format json|markdown] [--out content.json]
create --book ID --title TITLE [--parent ID] [--kind doc|group]
    [--input FILE --format json|markdown | --template ID] [--out snapshot.json]
edit --snapshot FILE --patch FILE [--out next-snapshot.json]
drawing --input spec.json --out NEW_DIRECTORY  Generate with the local engine; no production write
upload --input FILE [--kind image|attachment|drawing] [--name NAME]
download --src /assets/...|/attachments/...|/drawings/ID/file|preview --out FILE
export --doc ID_OR_URL --out NEW_DIRECTORY
preview-setup                       Prepare a cached local build (no installs)
preview --snapshot FILE --out NEW_DIRECTORY
    [--scope section --path 3] [--viewport 1280x900,375x667] [--full-page]
    [--media-map FILE] [--media-dir DIRECTORY] [--offline]
    [--browser webkit|chromium] [--theme light|dark]

Common: --repo PATH (default YUYAN_REPO or ~/ali/Yuyan)
        --ssh ALIAS (default YUYAN_SSH or ali; uses an ephemeral SSH tunnel)
        --server URL (YUYAN_SERVER; bypass SSH, useful for isolated instances)
        --public-url URL (YUYAN_PUBLIC_URL; document links)
        --cookie-file FILE (optional one-line Cookie header; never print it)
        --timeout MS (default 120000; 0 removes the total deadline)
                     Preview: 45000; setup: 180000; drawing: 60000; all require 1000–600000
        --dry-run (validate and preview writes without sending them)
        --confirm (only after the user's deletion/restore request is clear)
FILE may be - for stdin except upload/snapshot. Output files must not exist.
Patches use text, attrs, replace, splice; see references/editing.md.
JSON success on stdout; JSON error on stderr with nonzero exit. Never retry writes blindly.
`;
const strings = ['repo', 'ssh', 'server', 'public-url', 'cookie-file', 'timeout', 'node', 'path', 'method', 'input', 'doc', 'out', 'scope', 'keyword', 'format', 'book', 'title', 'parent', 'kind', 'template', 'snapshot', 'patch', 'name', 'src', 'viewport', 'media-map', 'media-dir', 'browser', 'theme'];
let parsed;
try { parsed = parseArgs({ options: Object.fromEntries([...strings.map(key => [key, { type: 'string' }]), ...['help', 'dry-run', 'confirm', 'offline', 'full-page'].map(key => [key, { type: 'boolean' }])]), allowPositionals: true }); }
catch (error) { console.error(json({ ok: false, error: { code: 'invalid_arguments', message: error.message } }).trimEnd()); process.exit(2); }
const o = parsed.values, command = parsed.positionals[0];
let client, receipt;
const tools = () => formatTools(o.repo);
const service = async () => client ??= await connect(o);
const snapshot = (doc) => ({ kind: 'yuyan-doc-snapshot', version: 1, source: client.source, document: doc, hash: hash(doc) });
const saveSnapshot = async doc => o.out ? outputFile(o.out, json(snapshot(doc))) : undefined;
const baseline = doc => ({ id: doc.id, bookId: doc.bookId, parentId: doc.parentId, kind: doc.kind, title: doc.title, revision: doc.revision, content: doc.content });
const contentKey = (doc, fmt) => hash({ title: doc.title, content: fmt.schema.nodeFromJSON(doc.content).toJSON() });

async function contentInput(fmt) {
  if (!o.input) return { type: 'doc', content: [{ type: 'paragraph' }] };
  assert(!o.format || ['json', 'markdown'].includes(o.format), 'format must be json or markdown.');
  const data = await input(o.input);
  const content = o.format === 'markdown' ? fmt.fromMarkdown(data) : JSON.parse(data);
  fmt.validate(content); return content;
}
async function verifyDoc(id, intended, fmt) {
  const actual = await client.request(`api/docs/${id}`);
  assert(contentKey(actual, fmt) === contentKey(intended, fmt), 'Saved content differs from the expected result. Read the current document before editing again.', 'verification_failed');
  return actual;
}
async function checkMedia(content) {
  for (const { node } of walk(content)) if (node.type === 'drawing') await client.request(`api/drawings/${node.attrs.src.split('/').pop()}`);
  const media = new Set(walk(content).filter(e => ['image', 'attachment'].includes(e.node.type)).map(e => e.node.attrs.src));
  for (const src of media) await client.request(src.slice(1), { method: 'HEAD', raw: true });
}

async function exportMedia(content, publicBase) {
  const resources = new Map(), links = new Map(), drawings = new Map();
  function add(href, name) {
    if (typeof href !== 'string') return;
    let url; try { url = new URL(href, publicBase); } catch { return; }
    if (url.origin !== publicBase.origin) return;
    const path = url.pathname.startsWith(publicBase.pathname)
      ? '/' + url.pathname.slice(publicBase.pathname.length) : url.pathname;
    const drawing = /^\/drawings\/([0-9a-f]{32})(?:\/(file|preview))?$/.exec(path);
    if (drawing) {
      const src = '/drawings/' + drawing[1], refs = drawings.get(src) || [];
      refs.push({ href, preview: drawing[2] === 'preview', hash: url.hash }); drawings.set(src, refs); return;
    }
    const match = /^\/(assets\/[0-9a-f]{32}\.(?:png|jpg|gif|webp|bmp)|attachments\/[0-9a-f]{32})(?:\/content)?$/.exec(path);
    if (!match) return;
    const src = '/' + match[1];
    let resource = resources.get(src);
    if (!resource) {
      // Keep even long Unicode attachment names within common filesystem component limits.
      let label = basename((name || url.searchParams.get('name') || 'attachment').replaceAll('\\', '/')).replace(/[^\p{L}\p{N}._-]/gu, '_');
      const extension = /\.[a-zA-Z0-9]{1,12}$/.exec(label)?.[0] ?? '';
      let stem = extension ? label.slice(0, -extension.length) : label;
      while (Buffer.byteLength(stem + extension) > 180) stem = Array.from(stem).slice(0, -1).join('');
      label = stem + extension;
      resource = { src, path: `attachments/${basename(src)}${src.startsWith('/attachments/') ? '-' + (label || 'attachment') : ''}` };
      resources.set(src, resource);
    }
    links.set(href, resource.path + url.hash);
  }
  const entries = walk(content);
  // Prefer card metadata when the same file also appears as a text link.
  for (const { node } of entries) if (['image', 'attachment'].includes(node.type)) add(node.attrs.src, node.attrs.name);
  for (const { node } of entries) for (const mark of node.marks ?? []) if (mark.type === 'link') add(mark.attrs?.href);
  for (const { node } of entries) if (node.type === 'drawing') add(node.attrs.src);
  for (const [src, refs] of drawings) {
    const id = src.split('/').pop();
    const pkg = await client.request(`api/drawings/${id}`);
    const sourcePath = `attachments/${id}.yuyan.json`;
    resources.set(src, { src: src + '/file', path: sourcePath });
    const previewPath = `attachments/${id}.${pkg.preview.mime === 'image/png' ? 'png' : 'svg'}`;
    resources.set(src + '/preview', { src: src + '/preview', path: previewPath });
    for (const ref of refs) links.set(ref.href, (ref.preview ? previewPath : sourcePath) + ref.hash);
    for (const file of Object.values(pkg.files)) add(file.src);
  }
  return { resources: [...resources.values()], links };
}

async function api() {
  assert(o.path && !o.path.startsWith('/') && !o.path.split('?')[0].includes('..') && !o.path.split('?')[0].includes('%') && !o.path.includes('\\'), 'Use a relative API path, e.g. books/1/tree. Put query values in a URL-encoded query.');
  const method = (o.method || 'GET').toUpperCase();
  const route = o.path.split('?')[0];
  // A bounded escape hatch for product operations; document content always uses validated commands.
  const read = /^(meta|books(?:\/\d+(?:\/tree)?)?|book-groups|recent|stats|titles|link-targets|search|trash|templates(?:\/[a-f0-9]{32})?|docs\/\d+(?:\/view|\/preview|\/backlinks|\/versions)?|versions\/\d+(?:\/view)?|attachments\/[a-f0-9]{32}\/preview|drawings\/[a-f0-9]{32})$/;
  const writes = {
    POST: /^(books|templates|docs\/batch|docs\/\d+\/(move|restore|snapshot)|books\/\d+\/restore|versions\/\d+\/restore)$/,
    PATCH: /^(books\/\d+|templates\/[a-f0-9]{32})$/,
    PUT: /^(books\/order|book-groups)$/,
    DELETE: /^(books\/\d+|docs\/\d+|templates\/[a-f0-9]{32}|trash(?:\/(?:books|docs)\/\d+)?)$/,
  };
  assert(method === 'GET' ? read.test(route) : writes[method]?.test(route), 'Unsupported API operation. Use create/edit for document content and title.');
  assert(method !== 'GET' || !o.input, 'GET does not accept a body.');
  const body = o.input ? await jsonInput(o.input) : undefined;
  if (method === 'POST' && route === 'templates') { const fmt = await tools(); fmt.validate(body?.content); }
  if ((route === 'book-groups' && method === 'PUT') || (/^templates\//.test(route) && method !== 'GET') || /^versions\/\d+\/restore$/.test(route)) {
    assert(Number.isSafeInteger(body?.baseRevision) && body.baseRevision >= 0, 'This operation requires the current baseRevision.');
  }
  const destructive = method === 'DELETE' || /\/restore$/.test(route) || (route === 'docs/batch' && body?.action === 'trash');
  if (destructive && !o['dry-run']) assert(o.confirm, 'Deletion/restoration requires an explicit user request; then pass --confirm.', 'confirmation_required');
  if (o['dry-run']) return { dryRun: true, method, path: o.path, body };
  await service();
  if (method === 'POST' && route === 'templates') await checkMedia(body.content);
  const data = await client.request(`api/${o.path}`, { method, body });
  if (method !== 'GET') receipt = { method, path: o.path, response: data };
  return { data, ...(method !== 'GET' ? { hint: 'For organization changes, read the affected tree/list to verify the requested result.' } : {}) };
}

async function main() {
  if (o.help || !command) { console.log(help); return; }
  assert(parsed.positionals.length === 1, 'Unexpected positional arguments.');
  assert(!o['dry-run'] || ['api', 'create', 'edit', 'upload'].includes(command), '--dry-run applies to api, create, edit and upload.');
  if (o.out) {
    let exists = false;
    try { await lstat(o.out); exists = true; } catch (error) { if (error.code !== 'ENOENT') throw error; }
    assert(!exists, 'Output already exists. Choose a new path; files are never overwritten.');
  }
  let result;
  if (command === 'preview' || command === 'preview-setup') result = await (await import('./preview.mjs')).previewCommand(o, command === 'preview-setup');
  else if (command === 'drawing') result = await (await import('./drawing.mjs')).generateCommand(o);
  else if (command === 'schema') result = (await tools()).describe(o.node);
  else if (command === 'validate') {
    assert(o.input, 'validate requires --input.');
    const fmt = await tools(), content = await contentInput(fmt);
    result = { valid: true, ...fmt.validate(content), ...(o.out ? { file: await outputFile(o.out, json(content)) } : {}), sourceRevision: fmt.revision };
  } else if (command === 'doctor') {
    const fmt = await tools(); await service();
    const meta = await client.request('api/meta');
    result = { connected: true, schemaVersion: meta.schemaVersion, sourceRevision: fmt.revision, nodeTypes: Object.keys(fmt.schema.nodes), markTypes: Object.keys(fmt.schema.marks) };
  } else if (command === 'api') result = await api();
  else if (command === 'read') {
    const fmt = await tools(); await service();
    const id = client.docID(o.doc), doc = await client.request(`api/docs/${id}`);
    const selection = select(doc.content, o);
    if (o.format === 'markdown') {
      assert(!o.scope || o.scope === 'full', 'Markdown display supports full scope; use JSON for editing and precise paths.');
      selection.content = fmt.toMarkdown(doc.content);
    } else assert(!o.format || o.format === 'json', 'format must be json or markdown.');
    result = { id, title: doc.title, revision: doc.revision, url: client.docURL(id), ...selection, snapshot: await saveSnapshot(doc) };
  } else if (command === 'create') {
    const fmt = await tools();
    assert(o.title?.trim(), 'create requires --title.');
    assert(!o.template || !o.input, 'Use either --template or --input.');
    const kind = o.kind || 'doc'; assert(['doc', 'group'].includes(kind), 'kind must be doc or group.');
    assert(kind !== 'group' || (!o.input && !o.template), 'Groups do not carry document content.');
    const body = { bookId: positiveID(o.book), parentId: o.parent ? positiveID(o.parent) : null, kind, title: o.title.trim(), content: await contentInput(fmt) };
    if (o.template) { await service(); body.content = (await client.request(`api/templates/${o.template}`)).content; }
    fmt.validate(body.content);
    if (o['dry-run']) result = { dryRun: true, body };
    else {
      await service(); await checkMedia(body.content);
      const created = await client.request('api/docs', { method: 'POST', body });
      receipt = { id: created.id, url: client.docURL(created.id), action: 'created' };
      const actual = await verifyDoc(created.id, body, fmt);
      result = { ...receipt, revision: actual.revision, verified: true, snapshot: await saveSnapshot(actual) };
    }
  } else if (command === 'edit') {
    const original = await jsonInput(o.snapshot), patch = await jsonInput(o.patch), fmt = await tools();
    assert(original.kind === 'yuyan-doc-snapshot' && original.version === 1 && original.hash === hash(original.document), 'Invalid or manually modified snapshot. Read the document again.');
    const doc = original.document;
    const desired = { title: patch.title === undefined ? doc.title : patch.title, content: applyPatch(doc.content, patch) };
    assert(typeof desired.title === 'string' && desired.title.trim(), 'Document title must not be empty.');
    desired.title = desired.title.trim(); fmt.validate(desired.content);
    await service(); assert(original.source === client.source, 'Snapshot belongs to another service. Use the same connection options.');
    const latest = await client.request(`api/docs/${doc.id}`);
    assert(canonical(baseline(latest)) === canonical(baseline(doc)), 'Document changed after this snapshot. Read it again and rebuild the patch.', 'conflict');
    if (contentKey(latest, fmt) === contentKey(desired, fmt)) result = { id: doc.id, revision: doc.revision, url: client.docURL(doc.id), unchanged: true, verified: true, ...(!o['dry-run'] ? { snapshot: await saveSnapshot(latest) } : {}) };
    else if (o['dry-run']) result = { dryRun: true, id: doc.id, baseRevision: doc.revision, operations: patch.operations.length, ...desired };
    else {
      await checkMedia(desired.content);
      const saved = await client.request(`api/docs/${doc.id}`, { method: 'PUT', body: { ...desired, baseRevision: doc.revision, sessionRevision: doc.revision } });
      receipt = { id: doc.id, revision: saved.revision, url: client.docURL(doc.id), action: 'saved' };
      const actual = await verifyDoc(doc.id, desired, fmt);
      await client.request(`api/docs/${doc.id}/snapshot`, { method: 'POST' });
      result = { ...receipt, verified: true, snapshot: await saveSnapshot(actual) };
    }
  } else if (command === 'upload' && o.kind === 'drawing') {
    if (!o['dry-run']) await service();
    result = await (await import('./drawing.mjs')).uploadDrawing(o, client);
    if (!o['dry-run']) receipt = { action: 'uploaded', node: result.node };
  } else if (command === 'upload') {
    assert(o.input && o.input !== '-', 'upload requires a real file path.');
    const file = resolve(o.input), info = await stat(file), kind = o.kind || 'image';
    assert(info.isFile() && ['image', 'attachment'].includes(kind), 'Expected a file and kind image or attachment.');
    assert(kind !== 'image' || (info.size > 0 && info.size <= 25 * 1024 ** 2), 'Images must be 1 byte–25 MiB; use attachment for larger files.');
    if (o['dry-run']) result = { dryRun: true, kind, name: o.name || basename(file), size: info.size };
    else {
      await service();
      const form = new FormData(); form.append('file', await openAsBlob(file), o.name || basename(file));
      const media = await client.request(`api/${kind === 'image' ? 'assets' : 'attachments'}`, { method: 'POST', body: form });
      const node = kind === 'image' ? { type: 'image', attrs: { src: media.url, alt: '', width: media.width, height: media.height } } : { type: 'attachment', attrs: { src: media.url, name: media.originalName, size: media.size, mime: media.mime } };
      result = { media, node, hint: 'Insert this node into a document/template. Unreferenced uploads are eligible for collection after one hour. Images are inline: put them in a paragraph or imageBoard.' };
    }
  } else if (command === 'download') {
    assert(/^\/(?:assets\/[0-9a-f]{32}\.(?:png|jpg|gif|webp|bmp)|attachments\/[0-9a-f]{32}(?:\/content)?|drawings\/[0-9a-f]{32}\/(?:file|preview))(?:\?name=[^#]*)?$/.test(o.src ?? ''), 'Use an existing app-relative media URL.');
    assert(o.out, 'download requires --out.'); await service();
    const response = await client.request(o.src.slice(1), { raw: true });
    const target = resolve(o.out), stream = createWriteStream(target, { flags: 'wx', mode: 0o600 });
    let opened = false; stream.on('open', () => { opened = true; });
    try { await pipeline(Readable.fromWeb(response.body), stream); } catch (error) { if (opened) await rm(target, { force: true }); throw error; }
    result = { file: target, bytes: (await stat(target)).size };
  } else if (command === 'export') {
    assert(o.out, 'export requires a new output directory.');
    const fmt = await tools(); await service();
    const id = client.docID(o.doc), doc = await client.request(`api/docs/${id}`), directory = resolve(o.out);
    fmt.validate(doc.content);
    const { mkdir } = await import('node:fs/promises');
    await mkdir(directory, { mode: 0o700 });
    const { resources, links } = await exportMedia(doc.content, client.publicBase);
    if (resources.length) await mkdir(`${directory}/attachments`, { mode: 0o700 });
    for (const { src, path } of resources) {
      const response = await client.request(src.slice(1), { raw: true });
      await pipeline(Readable.fromWeb(response.body), createWriteStream(`${directory}/${path}`, { flags: 'wx', mode: 0o600 }));
    }
    const markdown = fmt.toMarkdown(doc.content, { drawingSrc: src => links.get(src) ?? src, imageSrc: src => links.get(src) ?? src, attachmentSrc: src => links.get(src) ?? src, linkHref: href => links.get(href) ?? (href.startsWith('/docs/') ? new URL(href.slice(1), client.publicBase).href : href) });
    await outputFile(`${directory}/document.md`, markdown);
    await outputFile(`${directory}/document.json`, json({ title: doc.title, content: doc.content }));
    result = { directory, id, mediaCount: resources.length, hint: 'document.json retains native formatting; document.md plus attachments is portable. This is a single-document export, not a backup of history or templates.' };
  } else throw new Failure('invalid_command', `Unknown command ${command}. Use --help.`);
  console.log(json({ ok: true, ...result }).trimEnd());
}

try { await main(); }
catch (error) {
  console.error(json({ ok: false, error: { code: error.code || 'error', message: error.message, ...error.details }, ...(receipt ? { writeReceipt: receipt, hint: 'The write succeeded before a later step failed. Inspect the target; do not repeat create/edit blindly.' } : {}) }).trimEnd());
  process.exitCode = 1;
} finally { client?.close(); }

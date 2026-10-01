import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { join, resolve } from 'node:path';
import { homedir } from 'node:os';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { assert, Failure } from './runtime.mjs';

export const canonical = value => Array.isArray(value) ? `[${value.map(canonical).join(',')}]` : value && typeof value === 'object' ? `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}` : JSON.stringify(value);
export const hash = value => createHash('sha256').update(canonical(value)).digest('hex');
export const textOf = node => node.text ?? (node.type === 'attachment' ? node.attrs?.name ?? '' : node.type === 'image' ? node.attrs?.caption ?? node.attrs?.alt ?? '' : node.type.endsWith('Math') ? node.attrs?.latex ?? '' : (node.content ?? []).map(textOf).join(node.type === 'doc' ? '\n' : ''));
export function walk(node, path = '', out = []) {
  assert(node && typeof node.type === 'string' && (!node.content || Array.isArray(node.content)), `Malformed node at ${path || 'root'}.`, 'invalid_document');
  assert(!path || path.split('/').length <= 64, 'Document nesting exceeds 64 levels.', 'invalid_document');
  out.push({ path, node });
  for (const [i, child] of (node.content ?? []).entries()) walk(child, path ? `${path}/${i}` : String(i), out);
  return out;
}
export function at(doc, path) {
  assert(typeof path === 'string' && (path === '' || /^(0|[1-9]\d*)(\/(0|[1-9]\d*))*$/.test(path)), 'Paths are zero-based content indices, e.g. 3/0/1; root is "".');
  let node = doc;
  if (path) for (const part of path.split('/')) { node = node.content?.[Number(part)]; assert(node, `Node does not exist at ${path}.`); }
  return node;
}

let loaded;
export async function formatTools(repoArg) {
  if (loaded) return loaded;
  const repo = resolve(repoArg || process.env.YUYAN_REPO || join(homedir(), 'ali/Yuyan'));
  const web = join(repo, 'web');
  try {
    const require = createRequire(join(web, 'package.json'));
    const { register } = await import(pathToFileURL(require.resolve('tsx/esm/api')).href);
    register(); // One loader: separate tsImport namespaces create incompatible ProseMirror classes.
    const load = path => import(pathToFileURL(join(web, path)).href);
    const { getSchema } = await import(pathToFileURL(require.resolve('@tiptap/core')).href);
    const { schemaExtensions } = await load('src/schema/extensions.ts');
    const markdown = await load('src/schema/markdown.ts');
    const colors = await load('src/schema/colors.ts');
    const { blockColors } = await load('src/schema/blockContainers.ts');
    const { Window } = await import(pathToFileURL(require.resolve('happy-dom')).href);
    // Only used for parsing supported HTML into Yuyan nodes; never executes imported scripts.
    const window = new Window({ settings: { enableJavaScriptEvaluation: false, disableCSSFileLoading: true, disableIframePageLoading: true } });
    globalThis.document = window.document;
    globalThis.DOMParser = window.DOMParser;
    const schema = getSchema(schemaExtensions());
    let revision = 'unknown';
    try { revision = execFileSync('git', ['-C', repo, 'rev-parse', 'HEAD'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); } catch {}
    function validate(content) {
      assert(content?.type === 'doc', 'Input must be a complete Tiptap doc object.');
      for (const { path, node } of walk(content)) {
        const fail = message => { throw new Failure('invalid_document', `${path || 'root'} (${node.type}): ${message}`); };
        if (!schema.nodes[node.type]) fail('Unknown node type.');
        for (const key of Object.keys(node)) if (!['type', 'attrs', 'content', 'text', 'marks'].includes(key)) fail(`Unknown node field ${key}.`);
        const attrs = node.attrs ?? {};
        for (const key of Object.keys(attrs)) if (!(key in schema.nodes[node.type].attrs)) fail(`Unknown attribute ${key}; it would be discarded by the editor.`);
        for (const [key, value] of Object.entries(attrs)) {
          if (value == null) continue;
          if (['textAlign', 'blockAlign', 'align', 'cellAlign'].includes(key) && !['left', 'center', 'right'].includes(value)) fail(`Invalid ${key}.`);
          if (['width', 'height', 'sourceWidth', 'sourceHeight'].includes(key) && !(Number.isFinite(value) && value > 0)) fail(`Invalid ${key}.`);
          if (['collapsed', 'titleHidden', 'checked', 'shadow'].includes(key) && typeof value !== 'boolean') fail(`${key} must be boolean.`);
          if (key === 'backgroundColor' && !colors.normalizeColor(value)) fail('Invalid background color.');
        }
        const level = attrs.level ?? schema.nodes.heading.attrs.level.default;
        if (node.type === 'heading' && !(Number.isInteger(level) && level >= 1 && level <= 6)) fail('Heading level must be 1–6.');
        if (node.type === 'columns' && attrs.widths != null && !(Array.isArray(attrs.widths) && attrs.widths.length === node.content?.length && attrs.widths.every(w => Number.isInteger(w) && w >= 1 && w <= 1000))) fail('Invalid column weights.');
        if (node.type === 'callout' && attrs.fold != null && !['', '+', '-'].includes(attrs.fold)) fail('fold must be empty, + or -.');
        if (node.type === 'highlightBlock' && attrs.backgroundColor != null && !blockColors.some(c => c.value === attrs.backgroundColor)) fail('Use the fixed highlight-block palette.');
        if (node.type === 'image') {
          if (!/^\/assets\/[0-9a-f]{32}\.(png|jpg|gif|webp|bmp)$/.test(attrs.src ?? '')) fail('Upload the image first; use its /assets/... URL.');
          for (const key of ['crop', 'placement']) if (attrs[key] != null) {
            const r = attrs[key];
            if (!['x', 'y', 'width', 'height'].every(k => Number.isFinite(r[k])) || r.x < 0 || r.y < 0 || r.width <= 0 || r.height <= 0 || (key === 'crop' && (r.x + r.width > 1.000001 || r.y + r.height > 1.000001))) fail(`Invalid ${key} rectangle.`);
          }
        }
        if (node.type === 'attachment' && (!/^\/attachments\/[0-9a-f]{32}$/.test(attrs.src ?? '') || !Number.isSafeInteger(attrs.size) || attrs.size < 0 || typeof attrs.name !== 'string' || !attrs.name.trim() || typeof attrs.mime !== 'string')) fail('Invalid attachment metadata.');
        if (node.type === 'tableCell' || node.type === 'tableHeader') {
          for (const key of ['colspan', 'rowspan']) if (attrs[key] != null && !(Number.isInteger(attrs[key]) && attrs[key] > 0)) fail(`Invalid ${key}.`);
          if (attrs.colwidth != null && !(Array.isArray(attrs.colwidth) && attrs.colwidth.length === (attrs.colspan ?? 1) && attrs.colwidth.every(w => Number.isInteger(w) && w > 0))) fail('colwidth must have one positive pixel width per spanned column.');
        }
        for (const mark of node.marks ?? []) {
          const type = schema.marks[mark.type];
          if (!type) fail(`Unknown mark ${mark.type}.`);
          for (const key of Object.keys(mark)) if (!['type', 'attrs'].includes(key)) fail(`Unknown mark field ${key}.`);
          for (const key of Object.keys(mark.attrs ?? {})) if (!(key in type.attrs)) fail(`Unknown ${mark.type} attribute ${key}.`);
          if (mark.type === 'textColor' && !colors.normalizeColor(mark.attrs?.color)) fail('textColor needs a valid solid fallback color.');
          if (mark.type === 'textColor' && mark.attrs?.gradient && !colors.textGradient(mark.attrs.gradient)) fail('Unknown text gradient.');
          if (mark.type === 'highlight' && mark.attrs?.color && !colors.normalizeColor(mark.attrs.color)) fail('Invalid text background color.');
          if (mark.type === 'link' && /^(?:javascript|data|vbscript):/i.test(String(mark.attrs?.href).trim())) fail('Unsafe link protocol.');
        }
      }
      const node = schema.nodeFromJSON(content); node.check();
      return { nodes: walk(content).length, characters: Array.from(textOf(content)).length };
    }
    function fromMarkdown(text) {
      const issues = [];
      const content = markdown.markdownToDoc(text, { issue: message => issues.push(message), resolveImage: src => src, resolveLink: (href, kind) => { if (kind === 'wiki') { issues.push('Resolve [[wiki links]] to actual /docs/<id> links first.'); return null; } return href; } });
      assert(!issues.length, `Markdown conversion requires attention: ${issues.join('; ')}`, 'conversion_error');
      validate(content); return content;
    }
    loaded = { repo, revision, schema, validate, fromMarkdown, toMarkdown: markdown.docToMarkdown,
      describe(name) {
        const describe = types => Object.fromEntries(Object.entries(types).filter(([key]) => !name || key === name).map(([key, value]) => [key, { content: value.spec.content ?? '', inline: !!value.isInline, attrs: Object.fromEntries(Object.entries(value.attrs).map(([key, spec]) => [key, spec.hasDefault ? spec.default : { required: true }])) }]));
        return { sourceRevision: revision, nodes: describe(schema.nodes), marks: describe(schema.marks), highlightBlockColors: blockColors.map(c => ({ name: c.label, value: c.value })), textGradients: colors.textGradients };
      },
    };
    return loaded;
  } catch (error) {
    if (error instanceof Failure) throw error;
    throw new Failure('schema_unavailable', `Cannot load Yuyan schema from ${repo}: ${error.message}`, { hint: 'Use --repo or YUYAN_REPO for an existing Yuyan checkout with its locked web dependencies installed. Do not copy the schema into this skill.' });
  }
}

export function applyPatch(original, patch) {
  assert(patch && !Array.isArray(patch) && typeof patch === 'object', 'Patch must be an object with operations and optional title.');
  assert(Object.keys(patch).every(k => ['title', 'operations'].includes(k)), 'Unknown patch field.');
  assert(Array.isArray(patch.operations), 'Patch requires an operations array (empty is allowed for renaming).');
  const content = structuredClone(original);
  for (const op of patch.operations) {
    assert(op && typeof op.path === 'string', 'Every operation needs a path.');
    const target = at(content, op.path);
    if (op.expect) assert(hash(target) === op.expect, `Expected content differs at ${op.path}.`, 'patch_conflict');
    if (op.op === 'attrs') {
      assert(op.attrs && typeof op.attrs === 'object' && !Array.isArray(op.attrs), 'attrs requires an object.');
      target.attrs = { ...target.attrs, ...op.attrs };
    } else if (op.op === 'text') {
      assert(target.type === 'text' && typeof op.text === 'string' && op.text.length > 0, 'text replaces one nonempty text node; use splice to delete it.');
      target.text = op.text;
    } else if (op.op === 'replace') {
      assert(op.node && typeof op.node === 'object', 'replace requires node.');
      if (!op.path) { for (const key of Object.keys(content)) delete content[key]; Object.assign(content, structuredClone(op.node)); }
      else {
        const parts = op.path.split('/'), index = Number(parts.pop());
        at(content, parts.join('/')).content[index] = structuredClone(op.node);
      }
    } else if (op.op === 'splice') {
      const children = target.content ?? [];
      assert(Number.isInteger(op.index) && op.index >= 0 && op.index <= children.length && Number.isInteger(op.deleteCount) && op.deleteCount >= 0 && op.index + op.deleteCount <= children.length && Array.isArray(op.nodes), 'splice needs a valid index, deleteCount and nodes array.');
      target.content = children;
      children.splice(op.index, op.deleteCount, ...structuredClone(op.nodes));
    } else throw new Failure('invalid_patch', `Unknown operation ${op.op}; use text, attrs, replace or splice.`);
  }
  return content;
}

export function select(content, options) {
  const entries = walk(content);
  const scope = options.scope || 'full';
  if (scope === 'full') return { content };
  if (scope === 'outline') return { headings: entries.filter(e => e.node.type === 'heading').map(e => ({ path: e.path, level: e.node.attrs?.level, text: textOf(e.node) })) };
  if (scope === 'node') { const node = at(content, options.path); return { path: options.path, hash: hash(node), content: node }; }
  if (scope === 'section') {
    const path = options.path;
    assert(/^(0|[1-9]\d*)$/.test(path ?? ''), 'section needs the path of a top-level heading. For nested headings use scope=node on the enclosing container.');
    const first = at(content, path); assert(first.type === 'heading', 'Section start must be a heading.');
    const start = Number(path); let end = start + 1;
    while (end < content.content.length && !(content.content[end].type === 'heading' && content.content[end].attrs.level <= first.attrs.level)) end++;
    return { parentPath: '', index: start, count: end - start, content: content.content.slice(start, end) };
  }
  assert(scope === 'keyword' && options.keyword, 'Use full, outline, node, section, or keyword with --keyword.');
  const hits = entries.filter(e => ['paragraph', 'heading', 'codeBlock', 'attachment', 'image', 'calloutTitle', 'foldTitle', 'inlineMath', 'blockMath'].includes(e.node.type) && textOf(e.node).toLocaleLowerCase().includes(options.keyword.toLocaleLowerCase()));
  return { total: hits.length, matches: hits.slice(0, 30).map(e => ({ path: e.path, hash: hash(e.node), content: e.node })), truncated: hits.length > 30 };
}

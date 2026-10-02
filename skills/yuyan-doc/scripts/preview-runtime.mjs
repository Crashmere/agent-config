import { spawn, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { access, mkdir, mkdtemp, readFile, rename, rm, symlink } from 'node:fs/promises';
import { constants } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { createRequire } from 'node:module';
import net from 'node:net';
import { setTimeout as delay } from 'node:timers/promises';
import { assert, Failure, json, outputFile } from './runtime.mjs';

const sourcePaths = ['cmd', 'internal', 'web', 'go.mod', 'go.sum'];
export async function sourceInfo(options) {
  assert(['darwin', 'linux'].includes(process.platform) && ['arm64', 'x64'].includes(process.arch), 'Local preview supports macOS/Linux on arm64 or x64.', 'preview_platform_unsupported');
  const repo = resolve(options.repo || process.env.YUYAN_REPO || join(homedir(), 'ali/Yuyan'));
  const git = args => execFileSync('git', ['-C', repo, ...args], { encoding: 'utf8', timeout: 10000, stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  assert(!git(['status', '--porcelain', '--untracked-files=normal', '--', ...sourcePaths]), 'Commit or isolate Yuyan code changes before preparing/using a preview build.', 'preview_source_dirty');
  const sourceRevision = git(['rev-parse', 'HEAD']);
  const fingerprint = createHash('sha256').update(git(['ls-tree', '-r', 'HEAD', '--', ...sourcePaths])).digest('hex');
  const cache = resolve(process.env.YUYAN_PREVIEW_CACHE || join(process.env.XDG_CACHE_HOME || join(homedir(), '.cache'), 'yuyan-doc/preview'));
  const directory = join(cache, `${process.platform}-${process.arch}-${fingerprint}`);
  return { repo, sourceRevision, fingerprint, directory, binary: join(directory, 'yuyan') };
}

export async function stopChild(child) {
  if (!child?.pid || child.exitCode !== null || child.signalCode !== null) return;
  const kill = signal => { try { process.kill(-child.pid, signal); } catch { child.kill(signal); } };
  const exited = new Promise(ok => child.once('exit', ok));
  kill('SIGTERM');
  const timer = setTimeout(() => kill('SIGKILL'), 2000);
  try { await exited; } finally { clearTimeout(timer); }
}

async function run(command, args, options, signal) {
  signal.throwIfAborted();
  const child = spawn(command, args, { ...options, detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
  let output = '';
  for (const stream of [child.stdout, child.stderr]) stream.on('data', chunk => { output = (output + chunk).slice(-6000); });
  const abort = () => { void stopChild(child); };
  signal.addEventListener('abort', abort, { once: true });
  try {
    const code = await new Promise((ok, fail) => { child.once('error', fail); child.once('exit', ok); });
    signal.throwIfAborted();
    assert(code === 0, `${command} failed: ${output}`, 'preview_setup_failed');
  } finally { signal.removeEventListener('abort', abort); await stopChild(child); }
}

export async function preparedBinary(info) {
  try {
    const manifest = JSON.parse(await readFile(join(info.directory, 'manifest.json'), 'utf8'));
    assert(manifest.fingerprint === info.fingerprint && manifest.platform === process.platform && manifest.arch === process.arch, 'Preview build metadata does not match this checkout.');
    await access(info.binary, constants.X_OK);
    return manifest;
  } catch (error) {
    throw new Failure('preview_setup_required', 'No prepared preview build for this Yuyan code. Run preview-setup once; normal previews never build or install dependencies.', { cause: error.message });
  }
}

export function browserEngine(name = 'webkit') {
  assert(['webkit', 'chromium'].includes(name), '--browser must be webkit or chromium.');
  try { return createRequire(import.meta.url)('playwright')[name]; }
  catch { throw new Failure('preview_browser_missing', 'Install the optional dependencies in the yuyan-doc skill directory, then the selected Playwright browser. See references/preview.md.'); }
}

export async function preparePreview(options, signal) {
  const info = await sourceInfo(options);
  try { return { prepared: true, reused: true, ...(await preparedBinary(info)), binary: info.binary }; }
  catch (error) { if (error.code !== 'preview_setup_required') throw error; }
  await access(join(info.repo, 'web/node_modules/typescript/package.json'));
  await mkdir(dirname(info.directory), { recursive: true, mode: 0o700 });
  const work = await mkdtemp(join(dirname(info.directory), '.build-'));
  try {
    const source = join(work, 'source'), output = join(work, 'output');
    await mkdir(source); await mkdir(output);
    await run('git', ['-C', info.repo, 'archive', '--format=tar', '--output', join(work, 'source.tar'), info.sourceRevision], {}, signal);
    await run('tar', ['-xf', join(work, 'source.tar'), '-C', source], {}, signal);
    // Reuse locked dependencies; all generated files stay in the build copy, never the project.
    await symlink(join(info.repo, 'web/node_modules'), join(source, 'web/node_modules'), 'dir');
    await run('npm', ['--prefix', join(source, 'web'), 'run', 'build'], {}, signal);
    const env = { ...process.env, PATH: `${join(homedir(), '.goenv/shims')}:${process.env.PATH}`, GOPROXY: 'off', GOTOOLCHAIN: 'local', GOOS: process.platform, GOARCH: process.arch === 'x64' ? 'amd64' : process.arch };
    await run('go', ['build', '-trimpath', '-o', join(output, 'yuyan'), './cmd/yuyan'], { cwd: source, env }, signal);
    const manifest = { fingerprint: info.fingerprint, sourceRevision: info.sourceRevision, platform: process.platform, arch: process.arch };
    await outputFile(join(output, 'manifest.json'), json(manifest));
    try { await rename(output, info.directory); }
    catch (error) { if (!['EEXIST', 'ENOTEMPTY'].includes(error.code)) throw error; await preparedBinary(info); }
    return { prepared: true, reused: false, ...manifest, binary: info.binary };
  } finally { await rm(work, { recursive: true, force: true }); }
}

export async function localInstance(binary, data, signal) {
  await run(binary, ['init', '--data', data], {}, signal);
  const listener = net.createServer();
  await new Promise((ok, fail) => { listener.once('error', fail); listener.listen(0, '127.0.0.1', ok); });
  const port = listener.address().port;
  await new Promise(ok => listener.close(ok));
  signal.throwIfAborted();
  const child = spawn(binary, ['serve', '--data', data, '--listen', `127.0.0.1:${port}`, '--with-prefix'], { detached: true, stdio: ['ignore', 'ignore', 'pipe'] });
  let log = '', spawnError;
  child.stderr.on('data', chunk => { log = (log + chunk).slice(-1500); });
  child.on('error', error => { spawnError = error; });
  const origin = `http://127.0.0.1:${port}`;
  const request = async (path, { method = 'GET', body } = {}) => {
    signal.throwIfAborted();
    const form = body instanceof FormData;
    const response = await fetch(`${origin}/yuyan/${path}`, { method, body: body === undefined ? undefined : form ? body : JSON.stringify(body), headers: form ? {} : { 'Content-Type': 'application/json' }, signal, redirect: 'error' });
    if (!response.ok) throw new Failure('preview_local_error', `Local preview API ${path}: ${response.status} ${await response.text()}`);
    return response.json();
  };
  try {
    for (let n = 0; n < 100; n++) {
      signal.throwIfAborted();
      if (spawnError || child.exitCode !== null || child.signalCode !== null) throw new Failure('preview_start_failed', spawnError?.message || log);
      try { await request('api/books'); return { child, origin, request }; } catch (error) { if (error.code === 'preview_local_error') throw error; }
      await delay(50, undefined, { signal });
    }
    throw new Failure('preview_start_failed', 'Local preview server did not become ready.');
  } catch (error) { await stopChild(child); throw error; }
}

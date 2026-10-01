import { spawn, execFileSync } from 'node:child_process';
import net from 'node:net';
import { setTimeout as delay } from 'node:timers/promises';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

export class Failure extends Error {
  constructor(code, message, details = {}) { super(message); this.code = code; this.details = details; }
}
export function assert(condition, message, code = 'invalid_input') {
  if (!condition) throw new Failure(code, message);
}
export async function input(path) {
  assert(path, 'Specify an input file (or - for stdin).');
  if (path !== '-') return readFile(resolve(path), 'utf8');
  let text = ''; for await (const chunk of process.stdin) text += chunk; return text;
}
export async function jsonInput(path) { return JSON.parse(await input(path)); }
export async function outputFile(path, content) {
  const target = resolve(path);
  await mkdir(dirname(target), { recursive: true, mode: 0o700 });
  await writeFile(target, content, { flag: 'wx', mode: 0o600 });
  return target;
}
export const json = value => JSON.stringify(value, null, 2) + '\n';

function baseURL(value) {
  const url = new URL(value.endsWith('/') ? value : value + '/');
  assert(['http:', 'https:'].includes(url.protocol) && !url.username && !url.password && !url.search && !url.hash, 'Invalid server URL.');
  return url;
}

export async function connect(options) {
  const timeout = Number(options.timeout ?? 120000);
  assert(Number.isSafeInteger(timeout) && timeout >= 0, '--timeout must be milliseconds, or 0 for no total deadline.');
  let cookie;
  if (options['cookie-file']) {
    cookie = (await readFile(options['cookie-file'], 'utf8')).trim();
    assert(!/[\r\n]/.test(cookie), 'Cookie file must contain one Cookie header value.');
  }
  let child, cleanup = () => {};
  let base, publicBase, source;
  if (options.server || process.env.YUYAN_SERVER) {
    base = baseURL(options.server || process.env.YUYAN_SERVER);
    publicBase = baseURL(options['public-url'] || process.env.YUYAN_PUBLIC_URL || base.href);
    source = base.href;
  } else {
    const host = options.ssh || process.env.YUYAN_SSH || 'ali';
    assert(/^[a-zA-Z0-9][a-zA-Z0-9_.-]*$/.test(host), 'Use a configured SSH host alias.');
    const sshOptions = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10'];
    const config = execFileSync('ssh', ['-G', ...sshOptions, host], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    const hostname = /^hostname (.+)$/m.exec(config)?.[1];
    assert(hostname, 'Cannot resolve the SSH hostname.');
    publicBase = baseURL(options['public-url'] || process.env.YUYAN_PUBLIC_URL || `https://${hostname.includes(':') ? `[${hostname}]` : hostname}/yuyan/`);
    source = `ssh:${host}:127.0.0.1:18084`;
    const listener = net.createServer();
    await new Promise((ok, fail) => { listener.once('error', fail); listener.listen(0, '127.0.0.1', ok); });
    const port = listener.address().port;
    await new Promise(ok => listener.close(ok));
    let exited = false, reason = '';
    child = spawn('ssh', [...sshOptions, '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=2', '-NT', '-L', `127.0.0.1:${port}:127.0.0.1:18084`, host], { stdio: ['ignore', 'ignore', 'pipe'] });
    child.stderr.on('data', data => { reason = (reason + data.toString()).slice(-1500); });
    child.on('error', error => { exited = true; reason = error.message; });
    child.on('exit', () => { exited = true; });
    const stop = () => child.kill();
    const interrupted = () => { stop(); process.exit(130); };
    process.once('exit', stop); process.once('SIGINT', interrupted); process.once('SIGTERM', interrupted);
    cleanup = () => { stop(); process.removeListener('exit', stop); process.removeListener('SIGINT', interrupted); process.removeListener('SIGTERM', interrupted); };
    try {
      let ready = false;
      for (let n = 0; n < 200 && !ready; n++) {
        if (exited) throw new Failure('connection_failed', `SSH connection failed: ${reason.trim()}`);
        ready = await new Promise(ok => {
          const socket = net.connect({ host: '127.0.0.1', port });
          socket.setTimeout(100);
          socket.once('connect', () => { socket.destroy(); ok(true); });
          socket.once('error', () => { socket.destroy(); ok(false); });
          socket.once('timeout', () => { socket.destroy(); ok(false); });
        });
        if (!ready) await delay(100);
      }
      assert(ready && !exited, 'SSH tunnel did not become ready.', 'connection_failed');
    } catch (error) { cleanup(); throw error; }
    base = baseURL(`http://127.0.0.1:${port}/`);
  }
  return {
    source, publicBase, close: cleanup,
    docID(value) {
      if (/^\d+$/.test(value ?? '')) return positiveID(value);
      const url = new URL(value);
      assert(url.origin === publicBase.origin && url.pathname.startsWith(publicBase.pathname), 'Document URL belongs to another configured service.');
      const match = /^docs\/(\d+)(?:\/edit|\/history)?\/?$/.exec(url.pathname.slice(publicBase.pathname.length));
      assert(match, 'Expected a Yuyan document ID or /yuyan/docs/<id> URL.');
      return positiveID(match[1]);
    },
    docURL(id) { return new URL(`docs/${id}`, publicBase).href; },
    async request(path, { method = 'GET', body, raw = false } = {}) {
      assert(typeof path === 'string' && !path.startsWith('/') && !path.includes('\\') && !/(^|\/)\.\.(\/|$)/.test(path), 'Use an application-relative path.');
      const url = new URL(path, base);
      assert(url.origin === base.origin && url.pathname.startsWith(base.pathname), 'Request escaped the configured application.');
      const headers = {};
      if (cookie) headers.Cookie = cookie;
      let payload = body;
      if (body !== undefined && !(body instanceof FormData)) { payload = JSON.stringify(body); headers['Content-Type'] = 'application/json'; }
      let response;
      try {
        response = await fetch(url, { method, headers, body: payload, redirect: 'error', signal: timeout ? AbortSignal.timeout(timeout) : undefined });
      } catch (error) {
        throw new Failure(method === 'GET' || method === 'HEAD' ? 'network_error' : 'write_outcome_unknown', error.message, { method, path, hint: 'Do not blindly retry a write. Read the target to determine whether it was applied.' });
      }
      if (!response.ok) {
        const text = await response.text();
        let data; try { data = JSON.parse(text); } catch { data = { message: text.slice(0, 500) }; }
        throw new Failure(response.status === 409 ? 'conflict' : response.status === 401 ? 'unauthorized' : 'http_error', data.message || `HTTP ${response.status}`, { status: response.status, method, path, response: data });
      }
      if (raw) return response;
      if (response.status === 204) return null;
      assert(response.headers.get('content-type')?.includes('application/json'), 'Expected JSON; check the server prefix or authentication.', 'unexpected_response');
      return response.json();
    },
  };
}

export function positiveID(value) {
  const number = Number(value);
  assert(/^\d+$/.test(String(value)) && Number.isSafeInteger(number) && number > 0, 'Expected a positive integer ID.');
  return number;
}

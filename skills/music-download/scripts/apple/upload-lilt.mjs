import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {parseArgs} from 'node:util';
import {fileURLToPath} from 'node:url';
import {setTimeout as sleep} from 'node:timers/promises';

function writeReceipt(file, value) {
  const temporary = file + '.tmp';
  fs.writeFileSync(temporary, JSON.stringify(value, null, 2), {mode: 0o600});
  fs.renameSync(temporary, file);
}

export async function uploadFlac({file, verification, base, origin, target, receipt,
  chunkSize = 32 * 1024 * 1024, fetchImpl = fetch, sleepImpl = sleep, onEvent = () => {}}) {
  file = path.resolve(file);
  if (path.resolve(verification.output) !== file || !verification.pcm_sha256 ||
      !verification.title || !verification.artist?.length || !verification.sample_rate ||
      !verification.bits || !verification.channels || !(verification.duration > 0)) {
    throw new Error('A matching completed FLAC packaging verification is required');
  }
  const url = new URL(base), loopback = ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback)) {
    throw new Error('Use HTTPS or a trusted loopback SSH tunnel');
  }
  if (url.username || url.password || url.search || url.hash || new URL(origin).origin !== origin || !target || !receipt) {
    throw new Error('Explicit service Origin, target and private receipt path are required');
  }
  if (!Number.isSafeInteger(chunkSize) || chunkSize < 1 || chunkSize > 32 * 1024 * 1024) {
    throw new Error('Upload chunks must be at most 32 MiB');
  }
  const before = fs.statSync(file), hasher = createHash('sha256');
  for await (const bytes of fs.createReadStream(file)) hasher.update(bytes);
  const unchanged = () => {
    const after = fs.statSync(file);
    if (before.size !== after.size || before.mtimeMs !== after.mtimeMs || before.ino !== after.ino) {
      throw new Error('Local FLAC changed during upload');
    }
  };
  unchanged();
  const fingerprint = hasher.digest('hex');
  const input = {filename: path.basename(file), size: before.size, fingerprint};
  const state = {target, file, fingerprint, size: before.size, status: 'uploading'};
  writeReceipt(receipt, state);

  async function request(route, {method = 'GET', json, body, headers = {}} = {}) {
    const response = await fetchImpl(base.replace(/\/$/, '') + route, {method,
      headers: {Origin: origin, ...(json === undefined ? {} : {'Content-Type': 'application/json'}), ...headers},
      body: json === undefined ? body : JSON.stringify(json), signal: AbortSignal.timeout(660000)});
    if (!response.ok) {
      await response.body?.cancel();
      const error = new Error(`Lilt request failed: HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return response;
  }
  async function json(route, options) {return (await request(route, options)).json();}
  function check(upload) {
    if (!upload?.id || upload.size !== input.size || upload.fingerprint !== fingerprint ||
        !Number.isSafeInteger(upload.offset) || upload.offset < 0 || upload.offset > input.size ||
        (!upload.duplicate && !['uploading', 'complete'].includes(upload.status))) {
      throw new Error('Invalid authoritative upload acknowledgment');
    }
    Object.assign(state, {uploadId: upload.id, offset: upload.offset});
    writeReceipt(receipt, state);
    return upload;
  }
  const open = async () => check((await json('/uploads', {method: 'POST', json: input})).upload);
  try {
    let upload = await open(), failures = 0;
    const handle = await fs.promises.open(file, 'r');
    try {
      while (!upload.duplicate && upload.status === 'uploading' && upload.offset < input.size) {
        const offset = upload.offset, bytes = Buffer.allocUnsafe(Math.min(chunkSize, input.size - offset));
        if ((await handle.read(bytes, 0, bytes.length, offset)).bytesRead !== bytes.length) {
          throw new Error('Local FLAC ended before the expected size');
        }
        try {
          const acknowledgment = await json(`/uploads/${encodeURIComponent(upload.id)}`, {
            method: 'PATCH', body: bytes, headers: {'Content-Type': 'application/octet-stream', 'Upload-Offset': String(offset)},
          });
          if (acknowledgment.upload?.offset !== offset + bytes.length) {
            throw new Error('Durable upload offset mismatch');
          }
          upload = check(acknowledgment.upload);
          failures = 0;
          onEvent({event: 'upload-ack', target, offset: upload.offset, size: input.size});
        } catch (error) {
          if (++failures > 3 || (error.status && error.status < 500 && error.status !== 409)) throw error;
          await sleepImpl(1000 * 2 ** failures);
          // A lost response may follow a durable write; always recover the server's offset.
          upload = await open();
        }
      }
    } finally {await handle.close();}
    unchanged();
    const completed = await json(`/uploads/${encodeURIComponent(upload.id)}/complete`, {method: 'POST', json: {}});
    if (!completed.track?.id) throw new Error('Missing publication receipt');
    Object.assign(state, {trackId: completed.track.id, status: 'published'});
    writeReceipt(receipt, state);
    const {track} = await json(`/tracks/${encodeURIComponent(state.trackId)}`);
    if (!track || track.deletedAt || track.format !== 'flac') throw new Error('Published FLAC is not active');
    const duplicate = Boolean(upload.duplicate || completed.duplicate);
    if (!duplicate) {
      const expected = {audioVersion: fingerprint, size: input.size, format: 'flac',
        title: verification.title, album: verification.album, artist: verification.artist.join(' / '),
        sampleRate: verification.sample_rate, bitDepth: verification.bits, channels: verification.channels};
      for (const [key, value] of Object.entries(expected)) {
        if (value !== undefined && track[key] !== value) throw new Error(`Published track mismatch: ${key}`);
      }
      if (Math.abs(track.duration - verification.duration) > 0.1 ||
          (verification.cover?.length && !track.coverUrl) ||
          (verification.lyrics_lines > 0 && (!track.hasLyrics || !track.lyricsText?.trim())) ||
          (verification.lyrics_timed_lines > 0 && (!track.hasLyrics || track.lyricsType !== 'lrc' ||
            !/^\[\d+:\d{2}(?:\.\d+)?\].*\S/m.test(track.lyricsText ?? '')))) {
        throw new Error('Published duration, cover or timed lyrics failed verification');
      }
    }
    const original = await request(`/tracks/${encodeURIComponent(track.id)}/stream?quality=original`, {headers: {Range: 'bytes=0-3'}});
    if (original.status !== 206) {
      await original.body?.cancel();
      throw new Error('Original FLAC range request was not honored');
    }
    if (Buffer.from(await original.arrayBuffer()).toString('ascii') !== 'fLaC') throw new Error('Original FLAC signature mismatch');
    if (track.coverUrl) {
      const cover = await request(`/tracks/${encodeURIComponent(track.id)}/cover`, {method: 'HEAD'});
      if (!cover.headers.get('content-type')?.startsWith('image/')) throw new Error('Published cover is not accessible');
    }
    Object.assign(state, {status: 'complete', verified: true, duplicate, currentFingerprint: track.audioVersion,
      expectedMetadataChecked: !duplicate, verifiedAt: new Date().toISOString()});
    writeReceipt(receipt, state);
    onEvent({event: 'uploaded', target, trackId: track.id, duplicate});
    return state;
  } catch (error) {
    Object.assign(state, {verified: false, error: error.message});
    writeReceipt(receipt, state);
    throw error;
  }
}

async function main() {
  const {values} = parseArgs({options: Object.fromEntries(
    ['file', 'verification', 'base', 'origin', 'target', 'receipt'].map(key => [key, {type: 'string'}])
  ), strict: true, allowPositionals: false});
  if (Object.values(values).length !== 6) throw new Error('Required: --file --verification --base --origin --target --receipt');
  const verification = JSON.parse(fs.readFileSync(values.verification, 'utf8'));
  await uploadFlac({...values, verification, onEvent: value => console.log(JSON.stringify(value))});
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.includes('--help')) {
    console.log('Upload one verified FLAC to Lilt; resume by rerunning the same command.\n' +
      'Required: --file PATH --verification JSON --base API_URL --origin ORIGIN --target HOST --receipt PRIVATE_JSON\n' +
      'Use an already authorized HTTPS entrance or loopback SSH tunnel. No deletion or replacement is performed.');
  } else {
    main().catch(error => {console.error(error.message); process.exitCode = 1;});
  }
}

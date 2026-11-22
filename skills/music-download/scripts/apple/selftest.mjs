import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {PlaybackMonitor} from './playback.mjs';
import {uploadFlac} from './upload-lilt.mjs';

const playing = position => ({state: 'playing', track: {id: 'expected', position}});
test('normal EOF can clear Music currentTrack without invalidating the full recording', () => {
  const monitor = new PlaybackMonitor({trackId: 'expected', duration: 20});
  monitor.update(playing(0.2), 0.3);
  monitor.update(playing(19.4), 19.5);
  assert.equal(monitor.update({state: 'stopped'}, 20.2).complete, true);
});
test('early stop, another song and unbounded playback still reject the recording', () => {
  for (const [state, elapsed] of [[{state: 'stopped'}, 5],
    [{state: 'playing', track: {id: 'different', position: 0}}, 20], [playing(4), 50]]) {
    const monitor = new PlaybackMonitor({trackId: 'expected', duration: 20});
    monitor.update(playing(0.2), 0.3);
    assert.throws(() => monitor.update(state, elapsed));
  }
});
test('probe duration follows actual song progress rather than startup wall time', () => {
  const monitor = new PlaybackMonitor({trackId: 'expected', duration: 20, probeSeconds: 3});
  assert.equal(monitor.update({state: 'stopped'}, 8).started, false);
  assert.equal(monitor.update(playing(0.2), 8.2).complete, false);
  assert.equal(monitor.update(playing(3), 11).complete, true);
});

function fixture() {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), 'music-upload-check-'));
  const file = path.join(work, 'audio.flac'), bytes = Buffer.from('fLaCfixture-audio');
  fs.writeFileSync(file, bytes);
  const fingerprint = createHash('sha256').update(bytes).digest('hex');
  const verification = {output: file, pcm_sha256: 'verified-by-packager', title: 'Fixture', album: 'Demo',
    artist: ['Lead'], sample_rate: 44100, bits: 16, channels: 2, duration: 4, cover: [{width: 1600}], lyrics_timed_lines: 2};
  const track = {id: 'fixture-track', audioVersion: fingerprint, size: bytes.length, format: 'flac',
    title: 'Fixture', album: 'Demo', artist: 'Lead', sampleRate: 44100, bitDepth: 16, channels: 2,
    duration: 4, coverUrl: '/cover', hasLyrics: true, lyricsType: 'lrc', lyricsText: '[00:00.00]First\n[00:03.00]Last'};
  return {work, file, bytes, fingerprint, track, options: {file, verification, base: 'http://127.0.0.1/lilt/api',
    origin: 'http://127.0.0.1', target: 'fixture', receipt: path.join(work, 'receipt.json'), chunkSize: 5, sleepImpl: async () => {}}};
}
const response = (value, status = 200) => new Response(JSON.stringify(value), {status, headers: {'Content-Type': 'application/json'}});
test('lost chunk acknowledgment resumes at the durable server offset, without replaying bytes', async () => {
  const f = fixture();
  let offset = 0, opens = 0, lost = false;
  const chunks = [];
  try {
    const result = await uploadFlac({...f.options, fetchImpl: async (url, options) => {
      if (url.endsWith('/uploads')) {
        opens++;
        return response({upload: {id: 'session', size: f.bytes.length, fingerprint: f.fingerprint, offset, status: 'uploading'}});
      }
      if (options.method === 'PATCH') {
        assert.equal(Number(options.headers['Upload-Offset']), offset);
        chunks.push(Buffer.from(options.body)); offset += options.body.length;
        if (!lost) {lost = true; throw new Error('Response lost after durable write');}
        return response({upload: {id: 'session', size: f.bytes.length, fingerprint: f.fingerprint, offset, status: 'uploading'}});
      }
      if (url.endsWith('/complete')) return response({track: f.track});
      if (url.includes('/stream?')) return new Response('fLaC', {status: 206});
      if (url.endsWith('/cover')) return new Response(null, {headers: {'Content-Type': 'image/jpeg'}});
      return response({track: f.track});
    }});
    assert.deepEqual(Buffer.concat(chunks), f.bytes);
    assert.equal(opens, 2);
    assert.equal(result.verified, true);
    assert.equal(JSON.parse(fs.readFileSync(f.options.receipt)).status, 'complete');
  } finally {fs.rmSync(f.work, {recursive: true});}
});
test('authorization rejection stops without chunk retries or publication', async () => {
  const f = fixture(); let requests = 0;
  try {
    await assert.rejects(() => uploadFlac({...f.options, fetchImpl: async () => {requests++; return response({}, 403);}}), /403/);
    assert.equal(requests, 1);
    assert.equal(JSON.parse(fs.readFileSync(f.options.receipt)).verified, false);
  } finally {fs.rmSync(f.work, {recursive: true});}
});
test('a lyric-type label cannot substitute for actual timestamped lyric text', async () => {
  const f = fixture();
  f.track.lyricsText = 'First\nLast';
  try {
    await assert.rejects(() => uploadFlac({...f.options, fetchImpl: async url => {
      if (url.endsWith('/uploads')) return response({upload: {id: 'session', size: f.bytes.length,
        fingerprint: f.fingerprint, offset: f.bytes.length, status: 'uploading'}});
      return response({track: f.track});
    }}), /timed lyrics failed verification/);
    assert.equal(JSON.parse(fs.readFileSync(f.options.receipt)).verified, false);
  } finally {fs.rmSync(f.work, {recursive: true});}
});
test('historical-hash duplicate preserves current edited metadata and transfers no chunks', async () => {
  const f = fixture(), methods = [];
  f.track.title = 'Owner edited title'; f.track.audioVersion = 'current-edited-fingerprint';
  try {
    const result = await uploadFlac({...f.options, fetchImpl: async (url, options) => {
      methods.push(options.method);
      if (url.endsWith('/uploads')) return response({upload: {id: 'duplicate', size: f.bytes.length,
        fingerprint: f.fingerprint, offset: f.bytes.length, status: 'complete', duplicate: true}});
      if (url.endsWith('/complete')) return response({track: f.track, duplicate: true});
      if (url.includes('/stream?')) return new Response('fLaC', {status: 206});
      if (url.endsWith('/cover')) return new Response(null, {headers: {'Content-Type': 'image/jpeg'}});
      return response({track: f.track});
    }});
    assert.equal(result.duplicate, true);
    assert.equal(result.expectedMetadataChecked, false);
    assert.equal(result.currentFingerprint, f.track.audioVersion);
    assert.equal(methods.includes('PATCH'), false);
    assert.equal(methods.includes('DELETE'), false);
  } finally {fs.rmSync(f.work, {recursive: true});}
});

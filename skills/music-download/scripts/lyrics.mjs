#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {errorText, isMain} from './netease/common.mjs';
import {lrclibLyrics, neteaseLyrics, neteaseTrack, writeLyrics} from './materials.mjs';

async function main() {
  const {values: v} = parseArgs({options: {provider: {type: 'string', default: 'lrclib'}, id: {type: 'string'},
    title: {type: 'string'}, artist: {type: 'string'}, album: {type: 'string'}, duration: {type: 'string'},
    out: {type: 'string'}, 'lrclib-fallback': {type: 'boolean'}, 'netease-base': {type: 'string'},
    'meting-base': {type: 'string'}, 'lrclib-base': {type: 'string'}, formats: {type: 'string', default: 'txt,lrc,translation,yrc,source'}, help: {type: 'boolean'}}});
  if (v.help) {console.log(`Usage: node lyrics.mjs --title TITLE --artist ARTIST [--album ALBUM] [--duration SECONDS] [--id LRCLIB_ID] --out NEW_DIR
  --provider netease --id SONG_ID [--lrclib-fallback] --out NEW_DIR
Default provider: lrclib. Ambiguous matches are saved as candidates, not selected automatically.
Optional: --formats txt,lrc (or a subset of txt,lrc,translation,yrc,source).
For Apple TTML use scripts/apple/fetch_metadata.py in the existing Gamdl environment.
No audio, cover, player control, account login, or audio tools are used.`); return;}
  if (!v.out || !['lrclib', 'netease'].includes(v.provider)) throw new Error('Specify --out and provider lrclib or netease');
  if (v.duration && (!Number.isFinite(Number(v.duration)) || Number(v.duration) <= 0)) throw new Error('Invalid duration');
  if ((v.title && !v.artist) || (!v.title && v.artist)) throw new Error('Supply title and artist together');
  if (v.provider === 'netease' && !v.id) throw new Error('NetEase requires a song ID');
  if (v.provider === 'lrclib' && !v.id && !(v.title && v.artist)) throw new Error('Supply LRCLIB ID or title and artist');
  const formats = v.formats.split(',').map(x => x.trim());
  if (!formats.length || formats.some(x => !['txt', 'lrc', 'translation', 'yrc', 'source'].includes(x))) throw new Error('Invalid formats');
  const output = path.resolve(v.out); await fs.mkdir(output, {mode: 0o700});
  const work = await fs.mkdtemp(path.join(output, '.lyrics-work-'));
  try {
    const expected = v.title ? {title: v.title, artists: [{name: v.artist}], album: {name: v.album || ''},
      durationMs: v.duration ? Number(v.duration) * 1000 : null} : null;
    let result;
    try {result = v.provider === 'netease' ? await neteaseLyrics(await neteaseTrack(v.id, v), work, v) : await lrclibLyrics(expected, v);}
    catch (e) {result = {status: 'request_failed', provider: v.provider, issues: [{error: errorText(e)}]};}
    const report = await writeLyrics(result, output, formats);
    console.log(JSON.stringify({out: output, status: report.status, provider: report.provider, files: report.files,
      sourceId: report.sourceId, candidates: report.candidates, timingCheck: report.timingCheck, issues: report.issues}, null, 2));
    if (!['available', 'instrumental'].includes(report.status)) process.exitCode = 2;
  } finally {await fs.rm(work, {recursive: true, force: true});}
}
if (isMain(import.meta.url)) main().catch(e => {console.error(errorText(e)); process.exitCode = 1;});

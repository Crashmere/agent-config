#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {errorText, isMain, readJSON, run} from './netease/common.mjs';
import {audioInfo, decode, embedUSLT, packetsHash, probe} from './netease/audio.mjs';
import {coverSize, prepareCover} from './image.mjs';

async function main() {
  const {values: v} = parseArgs({options: {source: {type: 'string'}, out: {type: 'string'}, lyrics: {type: 'string'},
    cover: {type: 'string'}, 'cover-size': {type: 'string', default: '1600'}, help: {type: 'boolean'}}});
  if (v.help) {console.log('Usage: node retag.mjs --source AUDIO.flac|mp3 --out NEW_AUDIO [--lyrics LRC_TXT_OR_LYRICS_JSON] [--cover IMAGE] [--cover-size 1600|max]\nStream-copy existing audio, keep readable metadata and verify unchanged audio packets. Original is retained. No network requests.'); return;}
  if (!v.source || !v.out || !(v.lyrics || v.cover)) throw new Error('Specify source, new output, and lyrics or cover');
  const source = path.resolve(v.source), output = path.resolve(v.out), before = audioInfo(await probe(source));
  if (!['flac', 'mp3'].includes(before.codec) || path.extname(output).toLowerCase() !== '.' + before.codec) throw new Error('Keep native FLAC/MP3 and its extension');
  let lyrics, translation = '', yrc = '';
  if (v.lyrics) {
    if (path.extname(v.lyrics).toLowerCase() === '.json') {
      const result = await readJSON(v.lyrics);
      if (result.status !== 'available') throw new Error('Lyrics result is not available');
      lyrics = result.lrc || result.text; translation = result.translation || ''; yrc = result.yrc || '';
    } else {lyrics = await fs.readFile(v.lyrics, 'utf8');}
    if (!lyrics?.trim() || /这似乎是一首纯音乐呢|纯音乐[，,]?请欣赏/.test(lyrics)) throw new Error('Not usable lyric text');
  }
  await fs.mkdir(path.dirname(output), {recursive: true});
  const work = await fs.mkdtemp(path.join(path.dirname(output), '.retag-work-'));
  try {
    const candidate = path.join(work, 'audio.' + before.codec), args = ['-v', 'error', '-nostdin', '-n', '-i', source];
    let cover;
    if (v.cover) {cover = await prepareCover(path.resolve(v.cover), work, coverSize(v['cover-size'])); args.push('-i', cover.file);}
    args.push('-map', '0:a:0', '-map', cover ? '1:v:0' : '0:v?', '-map_metadata', '0', '-c', 'copy');
    if (before.codec === 'mp3') args.push('-id3v2_version', '3');
    if (cover) args.push('-disposition:v:0', 'attached_pic');
    if (lyrics && before.codec === 'flac') args.push('-metadata', 'LYRICS=' + lyrics);
    if (translation) args.push('-metadata', 'LYRICS_TRANSLATION=' + translation);
    if (yrc) args.push('-metadata', 'LYRICS_YRC=' + yrc);
    args.push(candidate); await run('ffmpeg', args);
    if (lyrics && before.codec === 'mp3') await embedUSLT(candidate, lyrics);
    await decode(candidate);
    const hash = await packetsHash(source), after = audioInfo(await probe(candidate));
    if (hash !== await packetsHash(candidate)) throw new Error('Audio packets changed');
    for (const key of ['codec', 'sampleRate', 'bits', 'channels']) if (before[key] !== after[key]) throw new Error('Audio properties changed');
    const check = await probe(candidate), tags = Object.fromEntries(Object.entries(check.format.tags || {}).map(([k, value]) => [k.toLowerCase(), value]));
    if (lyrics && (tags.lyrics || tags['lyrics-und'] || '') !== lyrics) throw new Error('Lyrics tag readback mismatch');
    if (cover && !check.streams.some(s => s.disposition?.attached_pic === 1)) throw new Error('Cover tag missing');
    await fs.link(candidate, output);
    console.log(JSON.stringify({output, originalRetained: source, packetHash: hash, audio: after,
      lyricsSource: v.lyrics || null, cover: cover ? {width: cover.width, height: cover.height} : null}));
  } finally {await fs.rm(work, {recursive: true, force: true});}
}
if (isMain(import.meta.url)) main().catch(e => {console.error(errorText(e)); process.exitCode = 1;});

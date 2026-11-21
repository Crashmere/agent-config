#!/usr/bin/env node
import test, {before, after} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {run, readJSON} from './netease/common.mjs';
import {packetsHash, probe, tagsOf} from './netease/audio.mjs';

const scripts = path.dirname(fileURLToPath(import.meta.url));
let temp, oldPath;
before(async () => {
  temp = await fs.mkdtemp(path.join(os.tmpdir(), 'music-materials-check-')); oldPath = process.env.PATH;
  await run('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=4000x2000', '-frames:v', '1', path.join(temp, 'large.png')]);
  await run('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=400x300', '-frames:v', '1', path.join(temp, 'small.png')]);
  for (const codec of ['flac', 'mp3']) await run('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=4',
    '-metadata', 'title=Original title', '-metadata', 'artist=Original artist', '-metadata', 'album=Original album',
    '-c:a', codec === 'mp3' ? 'libmp3lame' : codec, path.join(temp, 'source.' + codec)]);
  const bin = path.join(temp, 'bin'); await fs.mkdir(bin);
  const stub = `#!${process.execPath}\n` + String.raw`
const fs=require('node:fs'),path=require('node:path');
const args=process.argv.slice(2),url=new URL(args.at(-1)),out=args[args.indexOf('--output')+1],root=process.env.MUSIC_FIXTURE_ROOT;
if(url.hostname!=='fixture.invalid')throw new Error('External request forbidden');
fs.appendFileSync(path.join(root,'requests.log'),url.pathname+'\n');
const put=x=>fs.writeFileSync(out,typeof x==='string'?x:JSON.stringify(x));
const record=id=>({id,trackName:'Signal (feat. Guest)',artistName:'Lead',albumName:'Demo',duration:4,instrumental:false,
 plainLyrics:'First line\nLast line',syncedLyrics:'[00:00.00]First line\n[00:03.00]Last line'});
if(url.pathname==='/api/search'){const list=[record(10),{...record(20),trackName:'Signal (Clean)'}];
 if(process.env.MUSIC_FIXTURE_AMBIGUOUS)list.push(record(11));put(list);}
else if(url.pathname==='/api/get/10')put(record(10));
else if(url.pathname==='/song/detail')put({code:200,songs:[{id:1,name:'Signal',ar:[{id:2,name:'Lead'},{id:3,name:'Guest'}],al:{id:4,name:'Demo',picUrl:'https://fixture.invalid/cover.png'},dt:4000}]});
else if(url.pathname==='/lyric/new')put({code:200,lrc:{lyric:''}});
else if(url.pathname==='/meting/')put('[00:00.00]这似乎是一首纯音乐呢，请尽情欣赏它吧！');
else throw new Error('Unexpected request '+url.pathname);
`;
  await fs.writeFile(path.join(bin, 'curl'), stub, {mode: 0o755});
  process.env.MUSIC_FIXTURE_ROOT = temp;
  process.env.PATH = bin + path.delimiter + oldPath;
});
after(async () => {
  process.env.PATH = oldPath; delete process.env.MUSIC_FIXTURE_ROOT; delete process.env.MUSIC_FIXTURE_AMBIGUOUS;
  if (temp) await fs.rm(temp, {recursive: true, force: true});
});
const cli = (name, ...args) => run(process.execPath, [path.join(scripts, name), ...args]);

test('standalone NetEase lyrics fall back to matched LRCLIB without audio tools or audio requests', async () => {
  const previous = process.env.PATH; process.env.PATH = path.join(temp, 'bin');
  const out = path.join(temp, 'lyrics');
  try {await cli('lyrics.mjs', '--provider', 'netease', '--id', '1', '--lrclib-fallback', '--netease-base', 'https://fixture.invalid/',
    '--meting-base', 'https://fixture.invalid/meting/', '--lrclib-base', 'https://fixture.invalid/', '--out', out);}
  finally {process.env.PATH = previous;}
  const report = await readJSON(path.join(out, 'lyrics.json'));
  assert.equal(report.provider, 'lrclib'); assert.equal(report.origin, 'community'); assert.equal(report.status, 'available');
  assert.equal(await fs.readFile(path.join(out, 'lyrics.txt'), 'utf8'), 'First line\nLast line\n');
  assert.equal(report.timingCheck.withinDuration, true);
  const requests = await fs.readFile(path.join(temp, 'requests.log'), 'utf8');
  assert.doesNotMatch(requests, /song\/url|cover|playback|audio/);
});

test('ambiguous records and explicit-ID wrong versions never publish lyrics', async () => {
  process.env.MUSIC_FIXTURE_AMBIGUOUS = '1';
  const out = path.join(temp, 'ambiguous');
  try {await assert.rejects(() => cli('lyrics.mjs', '--title', 'Signal', '--artist', 'Lead feat. Guest', '--album', 'Demo',
    '--duration', '4', '--lrclib-base', 'https://fixture.invalid/', '--out', out));}
  finally {delete process.env.MUSIC_FIXTURE_AMBIGUOUS;}
  const report = await readJSON(path.join(out, 'lyrics.json'));
  assert.equal(report.status, 'ambiguous'); assert.equal(report.candidates.length, 2);
  await assert.rejects(() => fs.stat(path.join(out, 'lyrics.lrc')));
  const wrong = path.join(temp, 'wrong-version');
  await assert.rejects(() => cli('lyrics.mjs', '--id', '10', '--title', 'Signal (Clean)', '--artist', 'Lead',
    '--lrclib-base', 'https://fixture.invalid/', '--out', wrong));
  await assert.rejects(() => fs.stat(path.join(wrong, 'lyrics.txt')));
});

test('covers preserve aspect ratio, default to 1600, and never enlarge small art', async () => {
  for (const [name, width, height] of [['large', 1600, 800], ['small', 400, 300]]) {
    const out = path.join(temp, 'cover-' + name);
    await cli('covers.mjs', '--file', path.join(temp, name + '.png'), '--out', out);
    const report = await readJSON(path.join(out, 'cover.json'));
    const image = (await probe(path.join(out, report.file))).streams[0];
    assert.equal(image.width, width); assert.equal(image.height, height);
    assert.equal(report.belowTarget, name === 'small');
  }
  const out = path.join(temp, 'cover-max');
  await cli('covers.mjs', '--file', path.join(temp, 'large.png'), '--size', 'max', '--out', out);
  assert.equal((await readJSON(path.join(out, 'cover.json'))).width, 4000);
  await assert.rejects(() => cli('covers.mjs', '--file', path.join(temp, 'small.png'), '--out', out));
});

test('FLAC/MP3 enrichment preserves original audio and metadata while embedding lyrics and resized cover', async () => {
  for (const codec of ['flac', 'mp3']) {
    const source = path.join(temp, 'source.' + codec), out = path.join(temp, 'tagged.' + codec);
    await cli('retag.mjs', '--source', source, '--out', out, '--lyrics', path.join(temp, 'lyrics', 'lyrics.json'),
      '--cover', path.join(temp, 'large.png'));
    assert.equal(await packetsHash(source), await packetsHash(out));
    const parsed = await probe(out), tags = tagsOf(parsed);
    assert.equal(tags.title, 'Original title'); assert.equal(tags.artist, 'Original artist'); assert.equal(tags.album, 'Original album');
    assert.equal(tags.lyrics || tags['lyrics-und'], '[00:00.00]First line\n[00:03.00]Last line');
    const picture = parsed.streams.find(s => s.disposition?.attached_pic === 1);
    assert.equal(picture.width, 1600); assert.equal(picture.height, 800);
    if (codec === 'mp3') assert.ok((await fs.readFile(out)).includes(Buffer.from('USLT')));
    await assert.rejects(() => cli('retag.mjs', '--source', source, '--out', out, '--lyrics', path.join(temp, 'lyrics', 'lyrics.json')));
    assert.equal(await packetsHash(source), await packetsHash(out));
  }
});

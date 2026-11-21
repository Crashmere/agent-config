import fs from 'node:fs/promises';
import path from 'node:path';
import {apiURL, bases, errorText, fetchFile, fetchJSON, id} from './netease/common.mjs';
import {song, validateSong} from './netease/library.mjs';

const normalize = value => String(value || '').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
function titleParts(value) {
  const features = [];
  const title = String(value).replace(/[([]\s*(?:feat\.?|ft\.?|featuring)\s+([^\])]+)[\])]/gi, (_, artist) => {
    features.push(artist); return '';
  });
  return {title: normalize(title), features};
}
function artists(values) {
  return values.flatMap(value => String(value).split(/\s+(?:feat\.?|ft\.?|featuring)\s+|\s*[\/,&]\s*/i)).map(normalize).filter(Boolean);
}
function versions(value) {
  return [...new Set(String(value).toLowerCase().match(/\b(?:clean|explicit|remix|live|acoustic|instrumental|remaster(?:ed)?)\b/g) || [])].sort().join('|');
}
export function matchesTrack(expected, candidate) {
  const e = titleParts(expected.title), c = titleParts(candidate.title);
  if (e.title !== c.title || versions(expected.title + ' ' + (expected.album?.name || '')) !==
      versions(candidate.title + ' ' + (candidate.album?.name || ''))) return false;
  const wanted = artists([...expected.artists.map(a => a.name), ...e.features]);
  const found = artists([...candidate.artists.map(a => a.name), ...c.features]);
  if (!wanted.length || !wanted.every(a => found.includes(a))) return false;
  if (wanted.length > 1 && found.some(a => !wanted.includes(a))) return false;
  if (expected.album?.name && normalize(expected.album.name) !== normalize(candidate.album?.name)) return false;
  if (expected.durationMs && (!candidate.durationMs || Math.abs(expected.durationMs - candidate.durationMs) > 2000)) return false;
  return true;
}
export const lrcPlain = text => text.split(/\r?\n/).filter(line => !/^\[(?:ar|al|ti|by|offset|re|ve|length):/i.test(line))
  .map(line => line.replace(/\[\d+:\d+(?:\.\d+)?\]/g, '').trim()).join('\n').trim();

export function lyricPayload(data) {
  const text = data.lrc?.lyric?.trim() || '';
  if (/这似乎是一首纯音乐呢/.test(text) && /请尽情欣赏它吧/.test(text)) {
    return {text: '', translation: '', yrc: '', status: 'unavailable'};
  }
  const instrumental = data.nolyric || /纯音乐[，,]?请欣赏/.test(text);
  return {text: instrumental ? '' : text, translation: data.tlyric?.lyric?.trim() || '', yrc: data.yrc?.lyric?.trim() || '',
    status: instrumental ? 'instrumental' : text ? 'available' : 'unavailable'};
}

export async function neteaseTrack(songId, options = {}) {
  const data = await fetchJSON(apiURL(bases(options).netease, 'song/detail', {ids: id(songId)}));
  const raw = data.songs?.find(s => String(s.id) === String(songId));
  if (data.code !== 200 || !raw) throw new Error('NetEase song metadata unavailable');
  const track = song(raw); validateSong(track); return track;
}

export async function neteaseLyrics(track, work, options = {}) {
  const b = bases(options), issues = [];
  let payload, provider = 'netease', origin = 'third-party-api';
  try {
    const raw = await fetchJSON(apiURL(b.netease, 'lyric/new', {id: track.id}));
    if (raw.code !== 200) throw new Error('Lyrics API status ' + raw.code);
    payload = lyricPayload(raw);
  } catch (e) {issues.push({provider, error: errorText(e)});}
  if (!payload || payload.status === 'unavailable') {
    try {
      const file = path.join(work, 'meting-response.txt');
      await fetchFile(apiURL(b.meting, '', {server: 'netease', type: 'lrc', id: track.id}), file);
      const raw = (await fs.readFile(file, 'utf8')).trim();
      if (!raw || /^[<{]/.test(raw) || !/\[\d+:\d+/.test(raw)) throw new Error('Invalid Meting lyric response');
      payload = lyricPayload({lrc: {lyric: raw}}); provider = 'meting';
    } catch (e) {issues.push({provider: 'meting', error: errorText(e)});}
  }
  const status = payload?.status || 'request_failed';
  const result = {status, provider, origin, sourceId: track.id, track, text: payload?.text ? lrcPlain(payload.text) : '',
    lrc: payload?.text && /\[\d+:\d+/.test(payload.text) ? payload.text : '', translation: payload?.translation || '',
    yrc: payload?.yrc || '', language: null, alignment: 'source_timestamps_unmeasured', issues};
  if (status === 'available' && !result.text) result.status = 'unavailable';
  if (options['lrclib-fallback'] && ['unavailable', 'request_failed'].includes(result.status)) {
    try {
      const fallback = await lrclibLyrics(track, {...options, id: undefined});
      fallback.issues = [...issues, {provider, status: result.status}, ...fallback.issues];
      return fallback;
    } catch (e) {result.issues.push({provider: 'lrclib', error: errorText(e)});}
  }
  return result;
}

export function lrclibTrack(record) {
  return {id: String(record.id), title: record.trackName, artists: [{name: record.artistName}],
    album: {name: record.albumName || ''}, durationMs: Number(record.duration) * 1000};
}
export async function lrclibLyrics(expected, options = {}) {
  const base = options['lrclib-base'] || 'https://lrclib.net/';
  let record;
  if (options.id) {
    record = await fetchJSON(apiURL(base, 'api/get/' + id(options.id)));
    if (String(record.id) !== String(options.id)) throw new Error('Unexpected LRCLIB record ID');
    if (expected?.title && !matchesTrack(expected, lrclibTrack(record))) throw new Error('LRCLIB record does not match requested version/metadata');
  } else {
    if (!expected?.title || !expected.artists?.length) throw new Error('LRCLIB search requires title and artist');
    const records = await fetchJSON(apiURL(base, 'api/search', {track_name: titleParts(expected.title).title,
      artist_name: expected.artists[0].name, album_name: expected.album?.name || undefined}));
    if (!Array.isArray(records)) throw new Error('Invalid LRCLIB search response');
    const eligible = records.filter(r => matchesTrack(expected, lrclibTrack(r)));
    if (eligible.length !== 1) return {status: eligible.length ? 'ambiguous' : 'unavailable', provider: 'lrclib', origin: 'community',
      track: expected, candidates: (eligible.length ? eligible : records).map(r => ({...lrclibTrack(r), instrumental: r.instrumental,
        hasPlainLyrics: Boolean(r.plainLyrics), hasSyncedLyrics: Boolean(r.syncedLyrics)})), issues: []};
    record = eligible[0];
  }
  if (!record.trackName || !record.artistName || !Number.isFinite(Number(record.duration))) throw new Error('Incomplete LRCLIB metadata');
  const text = record.plainLyrics?.trim() || lrcPlain(record.syncedLyrics || '');
  const lrc = record.syncedLyrics?.trim() || '';
  return {status: record.instrumental ? 'instrumental' : text ? 'available' : 'unavailable', provider: 'lrclib', origin: 'community',
    sourceId: String(record.id), sourceUrl: 'https://lrclib.net/api/get/' + record.id, track: lrclibTrack(record),
    requestedTrack: expected || null, text: record.instrumental ? '' : text, lrc: record.instrumental ? '' : lrc,
    translation: '', yrc: '', lyricsfile: record.lyricsfile || null, language: null,
    alignment: 'source_timestamps_unmeasured', issues: []};
}

export async function writeLyrics(result, output, formats = ['txt', 'lrc', 'translation', 'yrc', 'source']) {
  await fs.mkdir(output, {mode: 0o700, recursive: true});
  const files = [];
  if (result.status === 'available') {
    for (const [format, name, text] of [['txt', 'lyrics.txt', result.text], ['lrc', 'lyrics.lrc', result.lrc],
      ['translation', 'lyrics-translation.lrc', result.translation], ['yrc', 'lyrics.yrc', result.yrc], ['source', 'lyrics.source.yaml', result.lyricsfile]]) {
      if (!text || !formats.includes(format)) continue;
      await fs.writeFile(path.join(output, name), text + '\n', {flag: 'wx'}); files.push(name);
    }
  }
  const report = {...result, files, retrievedAt: new Date().toISOString(), timing: result.yrc ? 'word' : result.lrc ? 'line' : 'none'};
  if (result.lrc) {
    const times = [...result.lrc.matchAll(/\[(\d+):(\d+(?:\.\d+)?)\]/g)].map(m => Number(m[1]) * 60 + Number(m[2]));
    report.timingCheck = {events: times.length, lastSeconds: times.at(-1),
      ordered: times.every((time, index) => index === 0 || time >= times[index - 1]),
      withinDuration: !result.track?.durationMs || times.every(t => t <= result.track.durationMs / 1000 + 3)};
  }
  await fs.writeFile(path.join(output, 'lyrics.json'), JSON.stringify(report, null, 2) + '\n', {flag: 'wx'});
  return report;
}

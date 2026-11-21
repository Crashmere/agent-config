#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {apiURL, bases, errorText, fetchJSON, id, isMain, readJSON} from './netease/common.mjs';
import {neteaseTrack} from './materials.mjs';
import {coverSize, fetchCover, prepareCover} from './image.mjs';

async function main() {
  const {values: v} = parseArgs({options: {'netease-song-id': {type: 'string'}, 'netease-album-id': {type: 'string'},
    'apple-id': {type: 'string'}, storefront: {type: 'string', default: 'us'}, catalog: {type: 'string'},
    url: {type: 'string'}, file: {type: 'string'}, out: {type: 'string'}, size: {type: 'string', default: '1600'},
    'netease-base': {type: 'string'}, help: {type: 'boolean'}}});
  if (v.help) {console.log(`Usage: node covers.mjs (--netease-album-id ID | --netease-song-id ID | --apple-id ALBUM_OR_SONG_ID | --catalog CATALOG_JSON | --url HTTPS_URL | --file IMAGE) --out NEW_DIR [--size 1600|max] [--storefront us]
Use a verified release ID, not the first album with a matching title.
Default: longest edge at most 1600 px, preserve aspect ratio, never upscale.
Apple public iTunes lookup requires no cookies. No audio or lyrics are fetched.`); return;}
  const sources = ['netease-song-id', 'netease-album-id', 'apple-id', 'catalog', 'url', 'file'].filter(k => v[k]);
  if (!v.out || sources.length !== 1) throw new Error('Specify one cover source and --out');
  const size = coverSize(v.size), source = sources[0];
  let url, dimensions, identity;
  if (source === 'netease-song-id') {
    const track = await neteaseTrack(v[source], v); url = track.album.cover;
    identity = {provider: 'netease', songId: track.id, albumId: track.album.id, album: track.album.name, artists: track.artists};
  } else if (source === 'netease-album-id') {
    const data = await fetchJSON(apiURL(bases(v).netease, 'album', {id: id(v[source])}));
    if (data.code !== 200 || String(data.album?.id) !== v[source]) throw new Error('Album metadata unavailable');
    url = data.album.picUrl; identity = {provider: 'netease', albumId: v[source], album: data.album.name,
      artists: data.album.artists || [data.album.artist].filter(Boolean)};
  } else if (source === 'apple-id') {
    if (!/^[a-z]{2}$/i.test(v.storefront)) throw new Error('Use a two-letter storefront');
    const data = await fetchJSON(apiURL('https://itunes.apple.com/', 'lookup', {id: id(v[source]), country: v.storefront}));
    const record = data.results?.find(r => String(r.trackId || r.collectionId) === v[source]);
    if (!record?.artworkUrl100) throw new Error('Apple artwork unavailable in this storefront');
    url = record.artworkUrl100;
    if (!size) throw new Error('For max Apple artwork use a catalog JSON containing original dimensions');
    identity = {provider: 'apple', catalogId: v[source], albumId: String(record.collectionId), album: record.collectionName,
      artist: record.artistName, storefront: v.storefront};
  } else if (source === 'catalog') {
    const catalog = await readJSON(v.catalog), resource = catalog.album?.attributes ? catalog.album : catalog.song;
    const artwork = resource?.attributes?.artwork;
    if (!artwork?.url) throw new Error('Catalog has no artwork');
    const isAlbum = resource === catalog.album;
    url = artwork.url; dimensions = artwork; identity = {provider: 'apple',
      albumId: isAlbum ? resource.id : resource.relationships?.albums?.data?.[0]?.id,
      songId: isAlbum ? undefined : resource.id,
      album: isAlbum ? resource.attributes.name : resource.attributes.albumName, artist: resource.attributes.artistName};
  } else {url = v.url; identity = {provider: source === 'file' ? 'local' : 'user-supplied-url'};}
  const output = path.resolve(v.out); await fs.mkdir(output, {mode: 0o700});
  const work = await fs.mkdtemp(path.join(output, '.cover-work-'));
  try {
    const result = v.file ? await prepareCover(path.resolve(v.file), work, size) : await fetchCover(url, work, {size, dimensions, provider: identity.provider});
    const filename = 'cover.' + result.extension; await fs.copyFile(result.file, path.join(output, filename), fs.constants.COPYFILE_EXCL);
    const {file, ...details} = result;
    const report = {...details, file: filename, source: identity, retrievedAt: new Date().toISOString()};
    await fs.writeFile(path.join(output, 'cover.json'), JSON.stringify(report, null, 2) + '\n', {flag: 'wx'});
    console.log(JSON.stringify({out: output, ...report}, null, 2));
  } finally {await fs.rm(work, {recursive: true, force: true});}
}
if (isMain(import.meta.url)) main().catch(e => {console.error(errorText(e)); process.exitCode = 1;});

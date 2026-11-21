import path from 'node:path';
import {fetchFile, httpsURL, run} from './netease/common.mjs';
import {probe} from './netease/audio.mjs';

export function coverSize(value = '1600') {
  if (value === 'max') return null;
  const size = Number(value);
  if (!Number.isInteger(size) || size < 1 || size > 20000) throw new Error('Cover size must be 1..20000 or max');
  return size;
}
export function coverURL(value, size = 1600, dimensions) {
  const u = new URL(httpsURL(value));
  const edge = size || (dimensions ? Math.max(dimensions.width, dimensions.height) : null);
  const scale = dimensions && size ? Math.min(1, size / Math.max(dimensions.width, dimensions.height)) : 1;
  const width = dimensions ? Math.max(1, Math.round(dimensions.width * scale)) : edge;
  const height = dimensions ? Math.max(1, Math.round(dimensions.height * scale)) : edge;
  if (u.hostname.endsWith('music.126.net') && !size) u.searchParams.delete('param');
  if (u.hostname.endsWith('music.126.net') && size) u.searchParams.set('param', `${size}y${size}`);
  if (u.pathname.includes('{w}') || /%7Bw%7D/i.test(u.pathname)) {
    if (!edge) throw new Error('Original artwork dimensions are required for max Apple template size');
    u.pathname = u.pathname.replace(/(?:\{w\}|%7Bw%7D)/gi, String(width)).replace(/(?:\{h\}|%7Bh%7D)/gi, String(height));
  } else if (u.hostname.endsWith('mzstatic.com') && edge) {
    u.pathname = u.pathname.replace(/\/\d+x\d+([^/]*)$/, `/${width}x${height}$1`);
  }
  return u.href;
}
export async function prepareCover(input, work, size = 1600) {
  const stream = (await probe(input)).streams.find(s => ['mjpeg', 'png', 'webp'].includes(s.codec_name));
  if (!stream?.width || !stream?.height) throw new Error('Artwork is not a supported JPEG/PNG/WebP image');
  const {width, height} = stream, edge = Math.max(width, height), scale = size && edge > size ? size / edge : 1;
  const targetWidth = Math.max(1, Math.round(width * scale)), targetHeight = Math.max(1, Math.round(height * scale));
  const extension = stream.codec_name === 'mjpeg' ? 'jpg' : 'png';
  let file = input;
  if (scale < 1 || stream.codec_name === 'webp') {
    file = path.join(work, 'prepared-cover.' + extension);
    await run('ffmpeg', ['-v', 'error', '-nostdin', '-n', '-i', input, '-vf', `scale=${targetWidth}:${targetHeight}`,
      '-frames:v', '1', '-q:v', '2', file]);
  }
  const checked = (await probe(file)).streams[0];
  if (checked.width !== targetWidth || checked.height !== targetHeight) throw new Error('Artwork dimensions changed unexpectedly');
  return {file, extension, width: targetWidth, height: targetHeight, sourceWidth: width, sourceHeight: height,
    targetLongEdge: size, resized: scale < 1, belowTarget: Boolean(size && edge < size)};
}
export async function fetchCover(url, work, {size = 1600, dimensions, provider} = {}) {
  const input = path.join(work, 'source-cover.image');
  const requestURL = new URL(coverURL(url, size, dimensions));
  if (provider === 'netease' && size) requestURL.searchParams.set('param', `${size}y${size}`);
  const requested = requestURL.href;
  try {await fetchFile(requested, input);}
  catch (firstError) {
    if (requested === httpsURL(url)) throw firstError;
    await fetchFile(url, input);
  }
  return {...await prepareCover(input, work, size), sourceHost: new URL(httpsURL(url)).hostname};
}

import fs from 'node:fs/promises';
import {run,digest} from './common.mjs';

export async function probe(file){return JSON.parse((await run('ffprobe',['-v','error','-show_format','-show_streams','-of','json',file],60000)).stdout);}
export function audioInfo(p){
  const a=p.streams.find(s=>s.codec_type==='audio');if(!a)throw new Error('No audio stream');
  return {codec:a.codec_name,sampleRate:Number(a.sample_rate),bits:Number(a.bits_per_raw_sample||a.bits_per_sample),channels:a.channels,bitRate:Number(a.bit_rate||p.format.bit_rate),duration:Number(p.format.duration||a.duration)};
}
export function checkDuration(info,expectedMs){
  if(!Number.isFinite(info.duration)||!Number.isFinite(expectedMs)||expectedMs<=0||Math.abs(info.duration-expectedMs/1000)>Math.max(3,expectedMs/1000*.015))throw new Error(`Duration mismatch: ${info.duration}s, expected ${expectedMs/1000}s`);
}
export async function decode(file){await run('ffmpeg',['-hide_banner','-loglevel','error','-xerror','-nostdin','-i',file,'-map','0:a:0','-f','null','-'],180000);}
export async function packetsHash(file){return (await run('ffmpeg',['-v','error','-i',file,'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-'],120000)).stdout.trim();}
export async function streamInfoMD5(file){
  const h=await fs.open(file,'r');try{const b=Buffer.alloc(42);const {bytesRead}=await h.read(b,0,42,0);if(bytesRead!==42||b.toString('ascii',0,4)!=='fLaC'||(b[4]&127)!==0||b.readUIntBE(5,3)!==34)throw new Error('Invalid FLAC STREAMINFO');return b.subarray(26,42).toString('hex');}finally{await h.close();}
}
export async function embedUSLT(file,text){
  if(!text)return;
  const original=await fs.readFile(file);
  if(original.toString('ascii',0,3)!=='ID3'||original[3]!==3||original[5]!==0)throw new Error('Expected unflagged ID3v2.3 from ffmpeg');
  const size=(original[6]<<21)|(original[7]<<14)|(original[8]<<7)|original[9];
  if(size+10>original.length)throw new Error('Truncated ID3 tag');
  let cursor=10;const frames=[];
  while(cursor+10<=size+10&&/^[A-Z0-9]{4}$/.test(original.toString('ascii',cursor,cursor+4))){
    const end=cursor+10+original.readUInt32BE(cursor+4);if(end>size+10)throw new Error('Invalid ID3 frame');
    if(original.toString('ascii',cursor,cursor+4)!=='USLT')frames.push(original.subarray(cursor,end));cursor=end;
  }
  const payload=Buffer.concat([Buffer.from([1]),Buffer.from('und'),Buffer.from([255,254,0,0,255,254]),Buffer.from(text,'utf16le')]);
  const frame=Buffer.alloc(10);frame.write('USLT');frame.writeUInt32BE(payload.length,4);
  const body=Buffer.concat([...frames,frame,payload,Buffer.alloc(1024)]);if(body.length>=2**28)throw new Error('ID3 tag too large');
  const header=Buffer.from(original.subarray(0,10));for(let i=0;i<4;i++)header[9-i]=(body.length>>>(i*7))&127;
  await fs.writeFile(file+'.id3.tmp',Buffer.concat([header,body,original.subarray(10+size)]));await fs.rename(file+'.id3.tmp',file);
}
export function tagsOf(p){return Object.fromEntries(Object.entries(p.format.tags||{}).map(([k,v])=>[k.toLowerCase(),v]));}
export async function verify(file,song,{lyricHash,requireCover=true,fullDecode=true}={}){
  const p=await probe(file),info=audioInfo(p),tags=tagsOf(p);
  if(!['flac','mp3'].includes(info.codec))throw new Error('Unsupported actual codec: '+info.codec);
  checkDuration(info,song.durationMs);
  if(tags.title!==song.title||tags.artist!==song.artists.map(a=>a.name).join(' / ')||(song.album.name&&tags.album!==song.album.name)||tags.netease_song_id!==song.id)throw new Error('Embedded metadata mismatch');
  const text=tags.lyrics||tags['lyrics-und']||'';
  if(lyricHash!==undefined&&digest(text)!==lyricHash)throw new Error('Embedded lyrics mismatch');
  const cover=p.streams.some(s=>s.disposition?.attached_pic===1);
  if(requireCover&&!cover)throw new Error('Missing embedded cover');
  if(fullDecode)await decode(file);
  return {audio:info,cover,lyricCharacters:text.length,lyricHash:digest(text)};
}
export async function tagAudio(source,target,song,{cover,lyrics='',translation='',yrc='',originalId=song.id}={}){
  const before=audioInfo(await probe(source));
  if(!['flac','mp3'].includes(before.codec))throw new Error('Only native FLAC or MP3 is supported');checkDuration(before,song.durationMs);
  const metadata={title:song.title,artist:song.artists.map(a=>a.name).join(' / '),album:song.album.name,track:song.track?String(song.track):'',disc:song.disc||'',date:song.publishTime>0?new Date(song.publishTime).toISOString().slice(0,10):'',NETEASE_SONG_ID:song.id,NETEASE_PLAYLIST_SONG_ID:originalId,NETEASE_ALBUM_ID:song.album.id,lyrics:before.codec==='flac'?lyrics:'',LYRICS_TRANSLATION:translation,LYRICS_YRC:yrc};
  const args=['-hide_banner','-loglevel','error','-nostdin','-n','-i',source];if(cover)args.push('-i',cover);
  args.push('-map','0:a:0');if(cover)args.push('-map','1:v:0');args.push('-map_metadata','-1','-c','copy');
  if(before.codec==='mp3')args.push('-id3v2_version','3');
  if(cover)args.push('-disposition:v:0','attached_pic','-metadata:s:v:0','title=Album cover','-metadata:s:v:0','comment=Cover (front)');
  for(const[k,v]of Object.entries(metadata))if(v)args.push('-metadata',k+'='+v);args.push(target);
  await run('ffmpeg',args);if(before.codec==='mp3')await embedUSLT(target,lyrics);
  const after=await verify(target,song,{lyricHash:digest(lyrics),requireCover:Boolean(cover)});
  for(const k of ['codec','sampleRate','bits','channels'])if(after.audio[k]!==before[k])throw new Error('Audio properties changed during tagging');
  // Packet hashing also detects changes when a FLAC STREAMINFO MD5 is all zeros.
  const hash=await packetsHash(source);if(hash!==await packetsHash(target))throw new Error('Audio packets changed during tagging');
  if(before.codec==='flac'&&await streamInfoMD5(source)!==await streamInfoMD5(target))throw new Error('FLAC STREAMINFO MD5 changed');
  return {...after,packetHash:hash,integrity:'full_decode_passed'};
}

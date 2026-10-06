#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import {parseArgs} from 'node:util';
import {apiURL,bases,csv,digest,errorText,exists,fetchFile,fetchJSON,httpsURL,id,inside,isMain,readJSON,safeName,writeJSON} from './common.mjs';
import {audioInfo,checkDuration,packetsHash,probe,tagAudio,verify} from './audio.mjs';
import {validateSong,versionKey} from './library.mjs';

export function replacementFor(item,overrides){
  const rule=overrides[item.song.id];if(!rule)return {song:item.song,note:''};
  if(typeof rule.note!=='string'||!rule.note.trim())throw new Error('Replacement requires an explicit note');
  validateSong(rule.song);
  const original=item.song,s=rule.song;
  const artists=x=>x.artists.map(a=>a.id&&a.id!=='0'?a.id:a.name.normalize('NFKC').trim().toLowerCase()).sort().join('|');
  if(artists(original)!==artists(s)||Math.abs(original.durationMs-s.durationMs)>2000)throw new Error('Replacement artists or duration differ');
  if(versionKey(original)!==versionKey(s)&&rule.acceptTitleDifference!==true)throw new Error('Replacement title differs; explicit review required');
  return {song:s,note:rule.note};
}
export async function metingURL(songId,base,work,quality=2000){
  const body=path.join(work,'resolve.body'),headers=path.join(work,'resolve.headers');
  await fetchFile(apiURL(base,'',{server:'netease',type:'url',id:id(songId),br:quality}),body,{follow:false,headers,maxBytes:1024*1024});
  const h=await fs.readFile(headers,'utf8'),locations=[...h.matchAll(/^location:\s*(.+)$/gim)];
  if(locations.length)return httpsURL(new URL(locations.at(-1)[1].trim(),base).href);
  const text=(await fs.readFile(body,'utf8')).trim().replace(/^@/,'');
  if(/^https?:\/\//.test(text))return httpsURL(text);
  throw new Error('Meting returned no audio URL');
}
async function neteaseURL(songId,base,legacy=false){
  const d=await fetchJSON(apiURL(base,legacy?'song/url':'song/url/v1',legacy?{id:songId,br:999000}:{id:songId,level:'lossless'})),s=d.data?.[0];
  if(!s?.url)throw new Error('Netease audio URL unavailable: '+s?.code);
  if(s.freeTrialInfo)throw new Error('Netease returned a trial excerpt');
  return httpsURL(s.url);
}
async function audioSource(song,b,work,allowMp3){
  const seen=new Set(),issues=[],mp3=[];
  const resolvers=[['meting-lossless',()=>metingURL(song.id,b.meting,work)],['netease-lossless',()=>neteaseURL(song.id,b.netease)],['netease-legacy',()=>neteaseURL(song.id,b.netease,true)],['meting-320',()=>metingURL(song.id,b.meting,work,320)]];
  for(const [label,resolve] of resolvers){
    try{
      const url=await resolve();if(seen.has(url))continue;seen.add(url);
      const file=path.join(work,label+'.audio');await fetchFile(url,file,{timeout:180,maxBytes:400*1024*1024});
      const info=audioInfo(await probe(file));checkDuration(info,song.durationMs);
      if(info.codec==='flac')return {file,info,source:label};
      if(info.codec==='mp3')mp3.push({file,info,source:label});else issues.push(label+': unsupported codec '+info.codec);
    }catch(e){issues.push(label+': '+errorText(e));}
  }
  if(allowMp3&&mp3.length)return mp3.sort((a,b)=>b.info.bitRate-a.info.bitRate)[0];
  throw new Error((mp3.length?'No FLAC available; MP3 fallback '+(allowMp3?'failed':'not enabled')+'. ':'')+issues.join('; '));
}
function lyricPayload(d){
  const text=d.lrc?.lyric?.trim()||'';
  return {text,translation:d.tlyric?.lyric?.trim()||'',yrc:d.yrc?.lyric?.trim()||'',status:d.nolyric||/纯音乐[，,]?请欣赏/.test(text)?'instrumental':text?'embedded':'unavailable'};
}
async function companions(song,b,work){
  const jobs=await Promise.allSettled([
    (async()=>{
      if(!song.album.cover)throw new Error('No cover URL in song metadata');
      const file=path.join(work,'cover.image');
      try{await fetchFile(song.album.cover,file);}catch{const u=new URL(song.album.cover);u.searchParams.set('param','1000y1000');await fetchFile(u.href,file);}
      if(!(await probe(file)).streams.some(s=>['mjpeg','png'].includes(s.codec_name)))throw new Error('Cover is not a supported JPEG/PNG image');return file;
    })(),
    (async()=>{
      try{const d=await fetchJSON(apiURL(b.netease,'lyric/new',{id:song.id}));if(d.code===200){const l=lyricPayload(d);if(l.text||l.status==='instrumental')return l;}}catch{}
      const file=path.join(work,'lyric.txt');
      try{await fetchFile(apiURL(b.meting,'',{server:'netease',type:'lrc',id:song.id}),file);const text=(await fs.readFile(file,'utf8')).trim();if(text&&!/^[<{]/.test(text)&&/\[\d+:\d+/.test(text))return lyricPayload({lrc:{lyric:text}});}catch{}
      return {text:'',translation:'',yrc:'',status:'unavailable'};
    })(),
  ]);
  if(jobs[0].status==='rejected')throw jobs[0].reason;
  if(jobs[1].status==='rejected')throw jobs[1].reason;
  return {cover:jobs[0].value,lyric:jobs[1].value};
}
export function validatePlan(plan){
  if(plan.schema!==1||!Array.isArray(plan.items)||!Array.isArray(plan.playlists)||!Array.isArray(plan.excludedIds)||!Array.isArray(plan.skipped)||!Array.isArray(plan.exclusions))throw new Error('Invalid plan schema');
  const seen=new Set(),playlists=new Set(plan.playlists.map(p=>id(p.id)));
  if(playlists.size!==plan.playlists.length||new Set(plan.playlists.map(p=>p.directory)).size!==plan.playlists.length)throw new Error('Duplicate playlist or directory');
  for(const p of plan.playlists)if(p.directory!==safeName(p.directory,200)||p.directory==='.mscd')throw new Error('Unsafe playlist directory');
  for(const item of plan.items){validateSong(item.song);if(seen.has(item.song.id)||plan.excludedIds.includes(item.song.id))throw new Error('Duplicate or excluded ID in plan');seen.add(item.song.id);if(!item.memberships?.length)throw new Error('Missing membership');for(const m of item.memberships)if(!playlists.has(m.playlistId)||!Number.isInteger(m.position)||m.position<1)throw new Error('Invalid playlist membership');}
}
async function processItem(item,context){
  const {out,state,b,allowMp3,overrides,plan,audit}=context,original=item.song,recordFile=path.join(state,'records',original.id+'.json');
  const replacement=replacementFor(item,overrides),s=replacement.song;
  if(plan.excludedIds.includes(s.id))throw new Error('Replacement source is already excluded');
  const sourceKey=digest(JSON.stringify({song:s,note:replacement.note}));
  let prior;try{prior=await readJSON(recordFile);}catch(e){if(e.code!=='ENOENT')throw e;}
  if(prior?.path&&prior.packetHash&&await exists(inside(out,prior.path))){
    if(prior.sourceKey!==sourceKey)throw new Error('Source or quality settings changed; inspect existing file instead of silently skipping');
    const file=inside(out,prior.path),checked=await verify(file,s,{lyricHash:prior.lyricHash,fullDecode:audit});
    if((await fs.stat(file)).size!==prior.bytes||await packetsHash(file)!==prior.packetHash)throw new Error('Completed file changed or is corrupt');
    if(!allowMp3&&checked.audio.codec!=='flac')throw new Error('Existing file is not lossless');
    const recovered={...prior,status:'ok',checkedAt:new Date().toISOString()};delete recovered.error;await writeJSON(recordFile,recovered);return recovered;
  }
  if(audit)throw new Error('Missing completed file');
  const work=await fs.mkdtemp(path.join(state,'work',original.id+'-'));
  try{
    const [audioResult,companionResult]=await Promise.allSettled([audioSource(s,b,work,allowMp3),companions(s,b,work)]);
    if(audioResult.status==='rejected')throw audioResult.reason;if(companionResult.status==='rejected')throw companionResult.reason;
    const source=audioResult.value,{cover,lyric}=companionResult.value;
    const target=path.join(work,'tagged.'+source.info.codec);
    const checked=await tagAudio(source.file,target,s,{cover,lyrics:lyric.text,translation:lyric.translation,yrc:lyric.yrc,originalId:original.id});
    const member=item.memberships[0],p=plan.playlists.find(p=>p.id===member.playlistId);
    const filename=String(member.position).padStart(3,'0')+' - '+safeName(s.title+' - '+s.artists.map(a=>a.name).join(', '))+` [${original.id}].${checked.audio.codec}`;
    const relative=path.join(p.directory,filename),destination=inside(out,relative);await fs.mkdir(path.dirname(destination),{recursive:true});
    const result={id:original.id,originalSong:original,song:s,replacementNote:replacement.note,sourceKey,status:'ok',path:relative,bytes:(await fs.stat(target)).size,...checked,lyrics:lyric.status,translatedLyrics:Boolean(lyric.translation),memberships:item.memberships,source:source.source,checkedAt:new Date().toISOString()};
    // Commit the journal first: a crash before linking is safely redownloadable.
    // link() fails atomically if an unrelated file already has this destination.
    if(await exists(destination))throw new Error('Untracked destination exists; preserve it and inspect before retrying');
    await writeJSON(recordFile,result);await fs.link(target,destination);return result;
  }finally{await fs.rm(work,{recursive:true,force:true});}
}
async function reports(plan,out,state){
  const records=[];for(const item of plan.items){try{records.push(await readJSON(path.join(state,'records',item.song.id+'.json')));}catch{records.push({id:item.song.id,song:item.song,status:'missing'});}}
  const ok=records.filter(r=>r.status==='ok'),failed=records.filter(r=>r.status!=='ok');
  const snapshotGaps=[...plan.playlists,...plan.exclusions].filter(p=>p.countGap!==0||p.unresolvedIds?.length).map(p=>({id:p.id,name:p.name,countGap:p.countGap,unresolvedIds:p.unresolvedIds}));
  const summary={total:plan.items.length,complete:ok.length,failed:failed.length,flac:ok.filter(r=>r.audio.codec==='flac').length,mp3:ok.filter(r=>r.audio.codec==='mp3').length,bytes:ok.reduce((n,r)=>n+r.bytes,0),lyrics:ok.filter(r=>r.lyrics==='embedded').length,instrumental:ok.filter(r=>r.lyrics==='instrumental').length,lyricsUnavailable:ok.filter(r=>r.lyrics==='unavailable').length,covers:ok.filter(r=>r.cover).length,skipped:plan.skipped.length,snapshotGaps,checkedAt:new Date().toISOString()};
  for(const p of plan.playlists){const dir=inside(out,p.directory);await fs.mkdir(dir,{recursive:true});const list=ok.filter(r=>r.memberships.some(m=>m.playlistId===p.id)).sort((a,b)=>a.memberships.find(m=>m.playlistId===p.id).position-b.memberships.find(m=>m.playlistId===p.id).position);await fs.writeFile(path.join(dir,'playlist.m3u8'),'#EXTM3U\n'+list.map(r=>'#EXTINF:'+Math.round(r.audio.duration)+','+r.song.title+'\n'+path.relative(dir,inside(out,r.path)).split(path.sep).join('/')).join('\n')+'\n');}
  await writeJSON(path.join(out,'manifest.json'),{...summary,records,skipped:plan.skipped,versionCandidates:plan.versionCandidates});
  await fs.writeFile(path.join(out,'results.csv'),csv([['id','source_id','title','artists','album','status','codec','bits','sample_rate','bit_rate','lyrics','cover','path','replacement_note','error'],...records.map(r=>[r.id,r.song.id,r.song.title,r.song.artists.map(a=>a.name).join(' / '),r.song.album.name,r.status,r.audio?.codec,r.audio?.bits,r.audio?.sampleRate,r.audio?.bitRate,r.lyrics,r.cover,r.path,r.replacementNote,r.error])]));
  await writeJSON(path.join(state,'summary.json'),summary);return summary;
}
async function main(){
  const {values:v}=parseArgs({options:{plan:{type:'string'},out:{type:'string'},replacements:{type:'string'},'allow-mp3':{type:'boolean'},jobs:{type:'string',default:'3'},audit:{type:'boolean'},'netease-base':{type:'string'},'meting-base':{type:'string'},help:{type:'boolean'}}});
  if(v.help||!v.plan||!v.out){console.log('Usage: node download.mjs --plan plan.json --out /absolute/library [--allow-mp3] [--jobs 3] [--replacements replacements.json] [--audit]\nOptional: --netease-base URL --meting-base URL. Resume by rerunning the same command.');if(!v.help)process.exitCode=1;return;}
  const jobs=Number(v.jobs);if(!Number.isInteger(jobs)||jobs<1||jobs>4)throw new Error('--jobs must be 1..4');
  const plan=await readJSON(v.plan);validatePlan(plan);
  const overrides=v.replacements?await readJSON(v.replacements):{};
  const chosen=new Set();for(const item of plan.items){const s=replacementFor(item,overrides).song;if(chosen.has(s.id)||plan.excludedIds.includes(s.id))throw new Error('Replacement creates a duplicate/excluded source ID');chosen.add(s.id);}
  const out=path.resolve(v.out),state=path.join(out,'.mscd');await fs.mkdir(state,{recursive:true});
  const lock=path.join(state,'running.lock');const handle=await fs.open(lock,'wx');
  await handle.writeFile(JSON.stringify({pid:process.pid,startedAt:new Date().toISOString()}));await handle.close();
  try{
    const saved=path.join(state,'plan.json');if(await exists(saved)){if(digest(JSON.stringify(await readJSON(saved)))!==digest(JSON.stringify(plan)))throw new Error('Output belongs to another plan; use a new output directory');}else await writeJSON(saved,plan);
    for(const d of ['records','work'])await fs.mkdir(path.join(state,d),{recursive:true});
    const context={out,state,plan,overrides,b:bases(v),allowMp3:Boolean(v['allow-mp3']),audit:Boolean(v.audit)};
    let cursor=0,complete=0,failures=0;
    const timer=setInterval(()=>console.log(JSON.stringify({processed:complete+failures,total:plan.items.length,complete,failures})),15000);
    try{
      await Promise.all(Array.from({length:jobs},async()=>{while(cursor<plan.items.length){const item=plan.items[cursor++];try{const r=await processItem(item,context);complete++;console.log('OK '+item.song.id+' '+r.audio.codec+' '+r.song.title);}catch(e){failures++;const file=path.join(state,'records',item.song.id+'.json');let prior={};try{prior=await readJSON(file);}catch{}await writeJSON(file,{...prior,id:item.song.id,song:prior.song||item.song,originalSong:item.song,memberships:item.memberships,status:'failed',error:errorText(e),checkedAt:new Date().toISOString()});console.log('FAIL '+item.song.id+' '+errorText(e));}}}));
    }finally{clearInterval(timer);}
    const summary=await reports(plan,out,state);console.log(JSON.stringify(summary,null,2));if(summary.failed||summary.lyricsUnavailable||summary.snapshotGaps.length)process.exitCode=2;
  }finally{await fs.unlink(lock);}
}
if(isMain(import.meta.url))main().catch(e=>{console.error(errorText(e));process.exitCode=1;});

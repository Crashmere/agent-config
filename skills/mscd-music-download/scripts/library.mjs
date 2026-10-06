#!/usr/bin/env node
import fs from 'node:fs/promises';
import {parseArgs} from 'node:util';
import {apiURL,bases,fetchJSON,id,isMain,readJSON,safeName} from './common.mjs';

export function song(raw) {
  return {id:id(raw.id),title:raw.name||'',artists:(raw.ar||raw.artists||[]).map(a=>({id:String(a.id||''),name:a.name||''})),album:{id:String((raw.al||raw.album)?.id||''),name:(raw.al||raw.album)?.name||'',cover:(raw.al||raw.album)?.picUrl||''},durationMs:Number(raw.dt??raw.duration),track:raw.no||null,disc:raw.cd||'',publishTime:raw.publishTime||0};
}
export function versionKey(s) {
  const norm=x=>String(x).normalize('NFKC').trim().toLowerCase();
  return JSON.stringify([norm(s.title),s.artists.map(a=>a.id&&a.id!=='0'?'id:'+a.id:'name:'+norm(a.name)).sort()]);
}
export function validateSong(s) {
  id(s.id);
  if(typeof s.id!=='string'||typeof s.title!=='string'||!s.title||!Array.isArray(s.artists)||!s.artists.length||s.artists.some(a=>typeof a.id!=='string'||typeof a.name!=='string'||!a.name)||!Number.isFinite(s.durationMs)||s.durationMs<=0||!s.album||['id','name','cover'].some(k=>typeof s.album[k]!=='string'))throw new Error('Incomplete song metadata: '+s.id);
}
export async function playlistSnapshot(playlistId,base) {
  const data=await fetchJSON(apiURL(base,'playlist/detail',{id:id(playlistId)}));
  if(data.code!==200||!data.playlist)throw new Error('Playlist detail failed: '+data.code);
  const p=data.playlist,ids=(p.trackIds||[]).map(t=>id(t.id));
  if(!Array.isArray(p.trackIds))throw new Error('Playlist has no trackIds field');
  const songs=new Map((p.tracks||[]).map(t=>[id(t.id),song(t)]));
  const missing=ids.filter(i=>!songs.has(i));
  for(let i=0;i<missing.length;i+=200){
    const d=await fetchJSON(apiURL(base,'song/detail',{ids:missing.slice(i,i+200).join(',')}));
    if(d.code!==200)throw new Error('Song detail failed: '+d.code);
    for(const t of d.songs||[])songs.set(id(t.id),song(t));
  }
  const tracks=ids.filter(i=>songs.has(i)).map(i=>songs.get(i));
  return {schema:1,id:id(p.id),name:p.name,declaredCount:p.trackCount,returnedIds:ids,tracks,unresolvedIds:ids.filter(i=>!songs.has(i)),countGap:p.trackCount-ids.length,checkedAt:new Date().toISOString()};
}
export function makePlan(snapshots,exclusions=[],{dedupeVersions=false,allowPartial=false}={}) {
  if(new Set(snapshots.map(p=>p.id)).size!==snapshots.length)throw new Error('Repeated target playlist');
  for(const p of [...snapshots,...exclusions]){
    if(!Array.isArray(p.tracks)||!Array.isArray(p.returnedIds))throw new Error('Expected snapshot from library.mjs playlist');
    if(!allowPartial&&(p.countGap!==0||p.unresolvedIds.length))throw new Error(`Incomplete snapshot ${p.name}; investigate counts or explicitly use --allow-partial`);
    if(new Set(p.returnedIds).size!==p.returnedIds.length)throw new Error('Duplicate IDs in playlist '+p.name);
    for(const s of p.tracks)validateSong(s);
  }
  const byId=new Set(exclusions.flatMap(p=>p.returnedIds)),versions=new Map();
  for(const p of exclusions)for(const s of p.tracks){const k=versionKey(s);if(!versions.has(k))versions.set(k,[]);versions.get(k).push(s);}
  const items=new Map(),skipped=[],versionCandidates=[];
  const playlists=snapshots.map(p=>({id:id(p.id),name:p.name,directory:safeName(p.name,70)+' ['+id(p.id)+']',declaredCount:p.declaredCount,returnedCount:p.returnedIds.length,countGap:p.countGap,unresolvedIds:p.unresolvedIds}));
  for(const p of snapshots)for(const s of p.tracks){
    const member={playlistId:id(p.id),position:p.returnedIds.indexOf(s.id)+1};
    const similar=(versions.get(versionKey(s))||[]).find(x=>Math.abs(x.durationMs-s.durationMs)<=20);
    if(similar && similar.id!==s.id)versionCandidates.push({id:s.id,matchedId:similar.id,title:s.title,album:s.album.name,matchedAlbum:similar.album.name,metadataOnly:true});
    if(byId.has(s.id)||(dedupeVersions&&similar)){
      skipped.push({...member,id:s.id,title:s.title,matchedId:byId.has(s.id)?s.id:similar.id,reason:byId.has(s.id)?'excluded_id':'excluded_version_candidate'});continue;
    }
    if(!items.has(s.id))items.set(s.id,{song:s,memberships:[]});
    items.get(s.id).memberships.push(member);
  }
  return {schema:1,createdAt:new Date().toISOString(),dedupeVersions,playlists,exclusions:exclusions.map(p=>({id:p.id,name:p.name,countGap:p.countGap,unresolvedIds:p.unresolvedIds})),excludedIds:[...byId.keys()],items:[...items.values()],skipped,versionCandidates};
}
export function overlap(snapshots) {
  const memberships=new Map();
  for(const p of snapshots)for(const s of p.tracks){if(!memberships.has(s.id))memberships.set(s.id,[]);memberships.get(s.id).push(p.id);}
  const matrix=snapshots.map(a=>snapshots.map(b=>{const ids=new Set(b.tracks.map(t=>t.id));return a.tracks.filter(t=>ids.has(t.id)).map(t=>t.id);}));
  return {schema:1,playlists:snapshots.map(p=>({id:p.id,name:p.name,declared:p.declaredCount,returned:p.tracks.length,countGap:p.countGap,unresolvedIds:p.unresolvedIds})),unique:memberships.size,records:snapshots.reduce((n,p)=>n+p.tracks.length,0),shared:[...memberships].filter(([,ps])=>ps.length>1).map(([id,playlistIds])=>({id,playlistIds})),matrix};
}
async function main(){
  const {values:v,positionals:p}=parseArgs({allowPositionals:true,options:{out:{type:'string'},snapshot:{type:'string',multiple:true},exclude:{type:'string',multiple:true},'dedupe-versions':{type:'boolean'},'allow-partial':{type:'boolean'},'netease-base':{type:'string'},help:{type:'boolean'}}});
  if(v.help||!p.length){console.log(`Usage: node library.mjs <command> [argument] [options]
  search-users <nickname> | search-songs <keywords> | user-playlists <uid>
  playlist <id> --out snapshot.json
  song <id> --out song.json
  plan --snapshot a.json [--snapshot b.json] [--exclude liked.json]
       [--dedupe-versions] [--allow-partial] --out plan.json
  overlap --snapshot a.json --snapshot b.json --out overlap.json
All network commands accept --netease-base URL. No audio is downloaded.`);return;}
  const base=bases(v).netease;let result;
  if(p[0]==='search-users'||p[0]==='search-songs'){
    if(!p[1])throw new Error('Search text required');const d=await fetchJSON(apiURL(base,'cloudsearch',{keywords:p[1],type:p[0]==='search-users'?1002:1,limit:30,offset:0}));
    if(d.code!==200)throw new Error('Search failed '+d.code);
    result=p[0]==='search-users'?{total:d.result?.userprofileCount,users:(d.result?.userprofiles||[]).map(u=>({uid:String(u.userId),nickname:u.nickname}))}:{total:d.result?.songCount,songs:(d.result?.songs||[]).map(song)};
  }else if(p[0]==='user-playlists'){
    const uid=id(p[1]),seen=new Set(),rows=[];let more=true,offset=0;
    for(let page=0;more&&page<100;page++){
      const d=await fetchJSON(apiURL(base,'user/playlist',{uid,limit:100,offset}));if(d.code!==200||!Array.isArray(d.playlist))throw new Error('User playlists failed');
      let added=0;for(const x of d.playlist)if(!seen.has(String(x.id))){seen.add(String(x.id));added++;rows.push({id:String(x.id),name:x.name,trackCount:x.trackCount,createdByUser:String(x.creator?.userId)===uid});}
      more=d.more===true;offset+=d.playlist.length;if(more&&!added)throw new Error('Pagination stalled');
    }
    if(more)throw new Error('Pagination safety limit reached');result={uid,playlists:rows,more:false};
  }else if(p[0]==='playlist')result=await playlistSnapshot(p[1],base);
  else if(p[0]==='song'){const d=await fetchJSON(apiURL(base,'song/detail',{ids:id(p[1])}));if(d.code!==200||!d.songs?.[0])throw new Error('Song not found');result=song(d.songs[0]);}
  else if(p[0]==='plan'||p[0]==='overlap'){
    if(!v.snapshot?.length)throw new Error('--snapshot required');const snaps=await Promise.all(v.snapshot.map(readJSON));
    result=p[0]==='plan'?makePlan(snaps,await Promise.all((v.exclude||[]).map(readJSON)),{dedupeVersions:v['dedupe-versions'],allowPartial:v['allow-partial']}):overlap(snaps);
  }else throw new Error('Unknown command '+p[0]);
  if(v.out){await fs.writeFile(v.out,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({out:v.out,items:result.items?.length,skipped:result.skipped?.length,countGap:result.countGap,unresolvedIds:result.unresolvedIds}));}
  else console.log(JSON.stringify(result,null,2));
}
if(isMain(import.meta.url))main().catch(e=>{console.error(e.message);process.exitCode=1;});

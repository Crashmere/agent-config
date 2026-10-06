#!/usr/bin/env node
// Offline regression checks: synthetic audio, fixture APIs, no external requests.
import test, {before,after} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {run,writeJSON,readJSON,safeName,inside,httpsURL,digest} from './common.mjs';
import {makePlan,overlap} from './library.mjs';
import {replacementFor,validatePlan} from './download.mjs';
import {checkDuration,tagAudio,verify,packetsHash,probe,tagsOf} from './audio.mjs';

const scripts=path.dirname(fileURLToPath(import.meta.url));
const mkSong=(id,extras={})=>({id,title:'测试曲目 '+id,artists:[{id:'10',name:'测试歌手'}],album:{id:'20',name:'测试专辑',cover:'https://fixture.invalid/cover.png'},durationMs:4000,track:1,disc:'1',publishTime:0,...extras});
const snapshot=(id,tracks,extras={})=>({schema:1,id,name:'✧ '+id,declaredCount:tracks.length,returnedIds:tracks.map(s=>s.id),tracks,unresolvedIds:[],countGap:0,...extras});
let temp,oldPath,oldFixture;
before(async()=>{
  temp=await fs.mkdtemp(path.join(os.tmpdir(),'mscd-验证-'));
  oldPath=process.env.PATH;oldFixture=process.env.MSCD_FIXTURE_DIR;
  await run('ffmpeg',['-v','error','-f','lavfi','-i','sine=frequency=440:duration=4','-c:a','flac',path.join(temp,'flac')+'.flac']);
  for(const rate of [128,192,320])await run('ffmpeg',['-v','error','-i',path.join(temp,'flac.flac'),'-c:a','libmp3lame','-b:a',rate+'k',path.join(temp,'mp3-'+rate+'.mp3')]);
  await run('ffmpeg',['-v','error','-f','lavfi','-i','color=c=blue:s=64x64','-frames:v','1',path.join(temp,'cover.png')]);
  const bin=path.join(temp,'bin');await fs.mkdir(bin);
  const stub=String.raw`#!/usr/bin/env node
const fs=require('node:fs');
const path=require('node:path');
const args=process.argv.slice(2),root=process.env.MSCD_FIXTURE_DIR;
const val=k=>args[args.indexOf(k)+1],url=new URL(args.at(-1));
if(url.hostname!=='fixture.invalid')throw new Error('Fixture blocks external requests');
fs.appendFileSync(path.join(root,'requests.log'),url.pathname+url.search+'\n');
const out=val('--output'),headers=args.includes('--dump-header')?val('--dump-header'):null;
const put=x=>fs.writeFileSync(out,typeof x==='string'?x:JSON.stringify(x));
if(process.env.MSCD_FORBID_FETCH)throw new Error('Unexpected fetch during resume/audit');
const sid=url.searchParams.get('id'),p=url.pathname;
const raw=id=>({id:Number(id),name:'测试曲目 '+id,ar:[{id:10,name:'测试歌手'}],al:{id:20,name:'测试专辑',picUrl:'https://fixture.invalid/cover.png'},dt:4000,no:1,cd:'1'});
if(p==='/cloudsearch')put({code:200,result:{userprofileCount:1,userprofiles:[{userId:101,nickname:'样例昵称'}]}});
else if(p==='/user/playlist'){const first=url.searchParams.get('offset')==='0';put({code:200,more:first,playlist:[{id:first?201:202,name:first?'Created':'Collected',trackCount:3,creator:{userId:first?101:102}}]});}
else if(p==='/playlist/detail')put({code:200,playlist:{id:201,name:'★',trackCount:4,trackIds:[{id:1},{id:2},{id:3}],tracks:[raw('1')]}});
else if(p==='/song/detail')put({code:200,songs:url.searchParams.get('ids').split(',').filter(x=>x!=='3').map(raw)});
else if(p==='/meting/'){
  if(url.searchParams.get('type')==='lrc'){put('[00:00.00]Fallback lyric');}
  else {const name=sid==='2'?(url.searchParams.get('br')==='320'?'mp3-192.mp3':'mp3-128.mp3'):'flac.flac';
    if(headers){fs.writeFileSync(headers,'HTTP/1.1 302 Found\r\nLocation: http://fixture.invalid/'+name+'\r\n\r\n');put('');}
    else throw new Error('Expected redirect resolver');}
}else if(p==='/song/url/v1')put({data:[{url:'https://fixture.invalid/mp3-192.mp3'}]});
else if(p==='/song/url')put({data:[{url:'https://fixture.invalid/mp3-320.mp3',freeTrialInfo:{start:0,end:1}}]});
else if(p==='/lyric/new')put(sid==='4'?{code:200,nolyric:true}:{code:200,lrc:{lyric:'[00:00.00]中文歌词\n[00:02.00]第二句'},tlyric:{lyric:'[00:00.00]Translation'}});
else if(p==='/protected.png'&&url.searchParams.get('param')==='1000y1000')fs.copyFileSync(path.join(root,'cover.png'),out);
else if(['/flac.flac','/mp3-128.mp3','/mp3-192.mp3','/mp3-320.mp3','/cover.png'].includes(p))fs.copyFileSync(path.join(root,p.slice(1)),out);
else throw new Error('Unknown fixture route '+p);
`;
  await fs.writeFile(path.join(bin,'curl'),stub,{mode:0o755});
  process.env.PATH=bin+path.delimiter+oldPath;process.env.MSCD_FIXTURE_DIR=temp;
});
after(async()=>{
  process.env.PATH=oldPath;
  if(oldFixture===undefined)delete process.env.MSCD_FIXTURE_DIR;else process.env.MSCD_FIXTURE_DIR=oldFixture;
  delete process.env.MSCD_FORBID_FETCH;
  if(temp)await fs.rm(temp,{recursive:true,force:true});
});

test('exact exclusions, shared playlist memberships, and version candidates',()=>{
  const a=mkSong('1'),b=mkSong('2'),release={...a,id:'3',album:{...a.album,name:'另一个发行'}};
  const targets=[snapshot('101',[a,b,release]),snapshot('102',[b])],liked=[snapshot('103',[a])];
  const plan=makePlan(targets,liked);validatePlan(plan);
  assert.deepEqual(plan.items.map(i=>i.song.id),['2','3']);
  assert.equal(plan.items[0].memberships.length,2);assert.equal(plan.skipped.length,1);
  assert.equal(plan.versionCandidates.length,1);
  assert.deepEqual(makePlan(targets,liked,{dedupeVersions:true}).items.map(i=>i.song.id),['2']);
  assert.equal(overlap(targets).unique,3);
  assert.throws(()=>makePlan([targets[0],targets[0]]),/Repeated/);
});
test('incomplete snapshots stay visible and unresolved excluded IDs remain excluded',()=>{
  const missing=snapshot('101',[],{declaredCount:2,returnedIds:['1'],unresolvedIds:['1'],countGap:1});
  assert.throws(()=>makePlan([snapshot('102',[mkSong('1')])],[missing]),/Incomplete/);
  const partial=makePlan([snapshot('102',[mkSong('1')])],[missing],{allowPartial:true});
  assert.equal(partial.items.length,0);assert.deepEqual(partial.excludedIds,['1']);
});
test('replacement review, output paths, and full-duration guards',()=>{
  const original=mkSong('1'),release={...original,id:'4'};
  assert.equal(replacementFor({song:original},{1:{song:release,note:'专辑版'}}).song.id,'4');
  assert.throws(()=>replacementFor({song:original},{1:{song:release}}),/note/);
  assert.throws(()=>replacementFor({song:original},{1:{song:{...release,title:'Remix'},note:'x'}}),/review/);
  assert.throws(()=>replacementFor({song:original},{1:{song:{...release,durationMs:150000},note:'x',acceptTitleDifference:true}}),/duration/);
  assert.throws(()=>checkDuration({duration:30},180000),/Duration/);
  assert.throws(()=>inside(temp,'../escape'),/escapes/);
  assert.equal(httpsURL('http://example.com/a'),'https://example.com/a');
  assert.equal(safeName('a/b:曲名'), 'a_b_曲名');
});
test('native FLAC and MP3 keep audio packets and embed Unicode lyrics/cover',async()=>{
  const s=mkSong('1',{title:'中文 $() `标题` \' ☀',album:{id:'0',name:'',cover:''}}),lyrics='[00:00.00]中文歌词\n[00:02.00]English';
  for(const [codec,source] of [['flac','flac.flac'],['mp3','mp3-320.mp3']]){
    const input=path.join(temp,source),output=path.join(temp,'写入 元数据.'+codec);
    s.publishTime=Date.parse('2026-06-16T00:00:00+08:00');
    const result=await tagAudio(input,output,s,{cover:path.join(temp,'cover.png'),lyrics});
    assert.equal(tagsOf(await probe(output)).date,'2026-06-16');
    assert.equal(result.audio.codec,codec);assert.equal(result.lyricHash,digest(lyrics));assert.equal(result.cover,true);
    assert.equal(await packetsHash(input),await packetsHash(output));
    if(codec==='mp3')assert.ok((await fs.readFile(output)).includes(Buffer.from('USLT')));
    await assert.rejects(()=>verify(output,s,{lyricHash:digest('wrong')}),/lyrics mismatch/);
  }
});
test('query CLI paginates created/collected playlists and preserves metadata/count gaps',async()=>{
  const query=async(...args)=>JSON.parse((await run(process.execPath,[path.join(scripts,'library.mjs'),...args,'--netease-base','https://fixture.invalid/'])).stdout);
  const users=await query('search-users','样例昵称');assert.equal(users.users[0].uid,'101');
  const playlists=await query('user-playlists','101');assert.deepEqual(playlists.playlists.map(p=>p.createdByUser),[true,false]);assert.equal(playlists.more,false);
  const p=await query('playlist','201');assert.equal(p.declaredCount,4);assert.equal(p.returnedIds.length,3);assert.equal(p.tracks.length,2);assert.equal(p.countGap,1);assert.deepEqual(p.unresolvedIds,['3']);
});
test('download CLI selects available bitrate, resumes offline, audits, and preserves failures',async()=>{
  const a=mkSong('1'),b=mkSong('2'),c=mkSong('3'),release={...c,id:'4',album:{...c.album,cover:'https://fixture.invalid/protected.png'}};
  const plan=makePlan([snapshot('101',[a,b,c]),snapshot('102',[b])]);
  const planFile=path.join(temp,'plan.json'),replacements=path.join(temp,'replacements.json'),out=path.join(temp,'音乐 输出');
  await writeJSON(planFile,plan);await writeJSON(replacements,{3:{song:release,note:'同一录音的专辑发行'}});
  const args=[path.join(scripts,'download.mjs'),'--plan',planFile,'--out',out,'--replacements',replacements,'--allow-mp3','--netease-base','https://fixture.invalid/','--meting-base','https://fixture.invalid/meting/'];
  await run(process.execPath,args,180000);
  const manifest=await readJSON(path.join(out,'manifest.json'));
  assert.equal(manifest.complete,3);assert.equal(manifest.failed,0);assert.equal(manifest.flac,2);assert.equal(manifest.mp3,1);
  assert.equal(manifest.instrumental,1);assert.equal(manifest.lyrics,2);assert.equal(manifest.covers,3);
  const mp3=manifest.records.find(r=>r.id==='2');assert.equal(mp3.audio.bitRate,192000);
  assert.equal(manifest.records.find(r=>r.id==='3').song.id,'4');
  const m3u=await fs.readFile(path.join(out,plan.playlists[1].directory,'playlist.m3u8'),'utf8');
  assert.match(m3u,/\.\.\//);assert.match(m3u,/\[2\]\.mp3/);
  const log=await fs.readFile(path.join(temp,'requests.log'),'utf8');assert.doesNotMatch(log,/^\/mp3-320.mp3/m);
  process.env.MSCD_FORBID_FETCH='1';
  await run(process.execPath,args);await run(process.execPath,[...args,'--audit']);
  // A policy mismatch must not destroy the successful record or prevent recovery.
  await assert.rejects(()=>run(process.execPath,args.filter(x=>x!=='--allow-mp3')));
  await run(process.execPath,args);
  // A corrupt file must stay on disk, be excluded from successful reports, and avoid fetching.
  const file=inside(out,mp3.path);await fs.appendFile(file,'broken');
  await assert.rejects(()=>run(process.execPath,[...args,'--audit']));
  const failed=await readJSON(path.join(out,'manifest.json'));assert.equal(failed.complete,2);assert.equal(failed.failed,1);
  assert.ok((await fs.stat(file)).size>mp3.bytes);
  delete process.env.MSCD_FORBID_FETCH;
});

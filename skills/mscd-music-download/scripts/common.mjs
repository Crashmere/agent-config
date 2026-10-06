import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

export const run = (bin, args, timeout = 120000) => promisify(execFile)(bin, args, {timeout, encoding:'utf8', maxBuffer:16*1024*1024});
export const readJSON = async file => JSON.parse(await fs.readFile(file,'utf8'));
export const exists = async file => {try {return (await fs.stat(file)).isFile();} catch {return false;}};
export const digest = data => createHash('sha256').update(data).digest('hex');
export const errorText = e => String(e.stderr || e.message || e).replace(/https?:\/\/\S+/g,'[URL]').slice(0,1200);
export const isMain = url => process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(url);
export async function writeJSON(file, data) {
  await fs.mkdir(path.dirname(file),{recursive:true});
  await fs.writeFile(file+'.tmp',JSON.stringify(data,null,2)+'\n');
  await fs.rename(file+'.tmp',file);
}
export function id(value) {
  const text=String(value ?? '');
  if(!/^\d+$/.test(text))throw new Error('Expected a numeric music ID: '+text);
  return text;
}
export function safeName(value, maxBytes=160) {
  let s=String(value).normalize('NFC').replace(/[\\/:*?"<>|\x00-\x1f\x7f]/g,'_').replace(/\s+/g,' ').replace(/[ .]+$/,'').trim();
  if(!s || /^\.+$/.test(s))s='unnamed';
  if(/^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)/i.test(s))s='_'+s;
  const chars=[...s];while(Buffer.byteLength(chars.join(''))>maxBytes)chars.pop();
  return chars.join('');
}
export function inside(root, relative) {
  if(typeof relative!=='string'||path.isAbsolute(relative))throw new Error('Expected a relative output path');
  const result=path.resolve(root,relative),rel=path.relative(root,result);
  if(rel==='..'||rel.startsWith('..'+path.sep))throw new Error('Path escapes output directory');
  return result;
}
export const httpsURL = value => {
  const u=new URL(value);
  if(u.protocol==='http:')u.protocol='https:';
  if(u.protocol!=='https:'||u.username||u.password)throw new Error('Expected HTTPS URL without credentials');
  return u.href;
};
export function apiURL(base, route='', params={}) {
  const u=new URL(httpsURL(base));
  u.pathname=u.pathname.replace(/\/$/,'')+(route?'/'+route.replace(/^\//,''):'/');
  for(const[k,v]of Object.entries(params))if(v!==undefined)u.searchParams.set(k,String(v));
  return u.href;
}
export async function fetchFile(url,file,{timeout=30,follow=true,headers,maxBytes=20*1024*1024,range}={}) {
  const args=['--silent','--show-error','--fail','--connect-timeout','10','--max-time',String(timeout),'--retry','2','--retry-all-errors','--retry-delay','2','--retry-max-time',String(timeout*2),'--proto','=https','--proto-redir','=https','--max-filesize',String(maxBytes)];
  if(follow)args.push('--location','--max-redirs','5');
  if(headers)args.push('--dump-header',headers);
  if(range)args.push('--range',range);
  args.push('--output',file,httpsURL(url));
  await run('curl',args,(timeout*4+20)*1000);
}
export async function fetchJSON(url) {
  const dir=await fs.mkdtemp(path.join(os.tmpdir(),'mscd-json-'));
  try{const file=path.join(dir,'response.json');await fetchFile(url,file);return await readJSON(file);}
  finally{await fs.rm(dir,{recursive:true,force:true});}
}
export const bases = options => ({netease:options['netease-base']||'https://zm.wwoyun.cn/',meting:options['meting-base']||'https://api.qijieya.cn/meting/'});
export const csv = rows => '\uFEFF'+rows.map(row=>row.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';

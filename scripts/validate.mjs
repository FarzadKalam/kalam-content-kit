import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {ROOT,readJson} from './lib/paths.mjs';
import {sharedFiles} from './shared-files.mjs';
import {python} from './lib/studio-runtime.mjs';
let failures=0; const fail=m=>{console.error(m);failures++};
for(const name of fs.readdirSync(path.join(ROOT,'brands')).filter(n=>n.endsWith('.json'))) {
  const b=readJson(path.join(ROOT,'brands',name));
  if(!b.id||!b.name||!['ready','partial','client-brief'].includes(b.status))fail('Invalid brand: '+name);
  for(const asset of Object.values(b.assets||{}))if(asset&&!fs.existsSync(path.join(ROOT,asset)))fail('Missing brand asset: '+asset);
}
const fonts=readJson(path.join(ROOT,'assets/fonts/catalog.json'));
const bundledPacks=Object.values(readJson(path.join(ROOT,'vendor/manifest.json'))).filter(v=>v&&typeof v==='object'&&v.files);
const upstreamSkillFiles=new Set(bundledPacks.flatMap(pack=>pack.files.map(item=>item.path)).filter(p=>p.startsWith('.agents/skills/')));
for(const name of fs.readdirSync(path.join(ROOT,'brands')).filter(n=>n.endsWith('.json'))) {
  const brand=readJson(path.join(ROOT,'brands',name));
  for(const [role,choice] of Object.entries(brand.fontPolicy?.roles||{})) {
    const family=fonts.find(f=>f.family===choice.family&&f.status==='available');
    if(!family) {fail(`Unavailable font for ${name}:${role}: ${choice.family}`);continue;}
    for(const weight of choice.weights||[])if(!family.files.some(f=>f.weight===weight||f.weightRange&&weight>=f.weightRange[0]&&weight<=f.weightRange[1]))fail(`Missing real font weight for ${name}:${role}: ${weight}`);
  }
}
for(const family of fonts)for(const f of family.files||[]) {
  const p=path.join(ROOT,'assets/fonts',f.path);
  if(!fs.existsSync(p))fail('Missing font: '+f.path);
  else if(f.sha256&&crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')!==f.sha256)fail('Font hash mismatch: '+f.path);
}
for(const pack of bundledPacks)for(const item of pack.files) {
  const p=path.join(ROOT,item.path);
  if(!fs.existsSync(p)||crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')!==item.sha256)fail('Bundled skill snapshot changed: '+item.path);
}
for(const entry of readJson(path.join(ROOT,'library/catalog.json')))if(entry.code&&!fs.existsSync(path.join(ROOT,entry.code)))fail('Missing example: '+entry.code);
for(const f of sharedFiles()) {
  const sharedVendorSfx=/^\.agents\/skills\/media-use\/audio\/assets\/sfx\/[^/]+\.mp3$/.test(f);
  if(!sharedVendorSfx&&/(^|\/)\.env($|\.)|(^|\/)(node_modules|\.local|\.cache)\/|\.(mp4|mov|mkv|mp3|m4a|pem|key)$/i.test(f))fail('Private or generated file in Git candidate: '+f);
  if(/\.(md|json|mjs|cjs|jsx|html|ps1|sh|yml|yaml|toml|py|ts|tsx|txt|css)$/.test(f)) {
    const p=path.join(ROOT,f); if(!fs.existsSync(p))continue;
    const t=fs.readFileSync(p,'utf8');
    try { new TextDecoder('utf-8',{fatal:true}).decode(fs.readFileSync(p)); } catch { fail('Invalid UTF-8 bytes: '+f); }
    const upstream=upstreamSkillFiles.has(f);
    if(!upstream&&(t.includes('\uFFFD')||/\?{4,}/.test(t)))fail('Invalid text encoding: '+f);
    if(/(?:gh[pousr]_[A-Za-z0-9]{25,}|sk-(?:proj-|ant-)?[A-Za-z0-9_-]{32,})/.test(t))fail('Possible credential in: '+f);
  }
}
console.log(failures?`failed: ${failures}`:'passed: brands, fonts, sample paths, UTF-8 and Git content checks');
process.exitCode=failures?1:0;
if(!failures)await import('./validate-content.mjs');
if(!failures) {try {console.log(python(['scripts/validate-agent-team.py']).trim());}catch(error){fail(error.message);process.exitCode=1;}}

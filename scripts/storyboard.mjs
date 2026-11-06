import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import sharp from 'sharp';
import {ROOT,inside,safeId,readJson,writeJson} from './lib/paths.mjs';

const digest=value=>crypto.createHash('sha256').update(value).digest('hex');
const fileHash=file=>digest(fs.readFileSync(file));
const slash=value=>value.replaceAll('\\','/');
const excluded=new Set(['analysis','renders','history','.hyperframes','node_modules','settings','.git']);
const metadataOnly=new Set(['DECISIONS.md','REVIEW.md']);
const projectFields=['id','kind','brand','engine','mode','width','height','fps','duration','durationSeconds','durationInFrames','audio','music','motion','production','fonts'];

function order(id,root) {
  const dest=inside(path.join(root,'.local/projects'),safeId(id));
  if(!fs.existsSync(path.join(dest,'project.json')))throw new Error('سفارش برای استوری‌بورد پیدا نشد.');
  return dest;
}

function localFile(dest,value,{required=true}={}) {
  if(typeof value!=='string'||!value.trim()||path.isAbsolute(value)||/^[a-z][a-z0-9+.-]*:/i.test(value)||value.includes('\\'))throw new Error('فایل استوری‌بورد باید مسیر نسبی محلی با / داخل سفارش باشد.');
  const absolute=inside(dest,value),relative=slash(path.relative(dest,absolute));
  if(!relative||relative==='project.json')throw new Error('مسیر فایل تولید معتبر نیست.');
  if(fs.existsSync(absolute)) {
    if(!fs.statSync(absolute).isFile())throw new Error('مسیر باید فایل واقعی باشد.');
  } else if(required)throw new Error('فایل لازم موجود نیست: '+relative);
  return {path:relative,absolute,sha256:fs.existsSync(absolute)?fileHash(absolute):null};
}

function nonempty(value,label,max=10000) {
  if(typeof value!=='string'||!value.trim()||value.length>max)throw new Error(label+' باید متن روشن و غیرخالی باشد.');
  return value.trim();
}

function inputSnapshot(dest) {
  const files=[];
  function walk(dir,relative='') {
    for(const entry of fs.readdirSync(dir,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name,'en'))) {
      if(excluded.has(entry.name))continue;
      const rel=relative?relative+'/'+entry.name:entry.name;
      if(!relative&&(metadataOnly.has(entry.name)||entry.name==='project.json'))continue;
      const absolute=inside(dest,rel);
      if(entry.isSymbolicLink())throw new Error('لینک در ورودی تولید مجاز نیست: '+rel);
      if(entry.isDirectory())walk(absolute,rel);
      else if(entry.isFile())files.push({path:rel,sha256:fileHash(absolute)});
      else throw new Error('ورودی تولید باید فایل یا پوشهٔ واقعی باشد: '+rel);
    }
  }
  walk(dest);
  const project=readJson(inside(dest,'project.json'));
  const production=Object.fromEntries(projectFields.filter(key=>project[key]!==undefined).map(key=>[key,project[key]]));
  files.push({path:'project.json#production',sha256:digest(JSON.stringify(production))});
  files.sort((a,b)=>a.path.localeCompare(b.path,'en'));
  return {files,fingerprint:digest(JSON.stringify(files))};
}

function validatePlan(dest,plan) {
  if(!plan||!Array.isArray(plan.scenes)||!plan.scenes.length||plan.scenes.length>240)throw new Error('استوری‌بورد باید یک تا ۲۴۰ صحنه داشته باشد.');
  if(!plan.copy||typeof plan.copy!=='object')throw new Error('فایل متن تأییدشده لازم است.');
  const dependencies=[],names=new Set();
  const dependency=(file,usage,required=true)=>{
    const record=localFile(dest,file,{required});
    dependencies.push({path:record.path,sha256:record.sha256,usage});
    return record;
  };
  const copy=dependency(plan.copy.file,'approved-copy');
  nonempty(plan.copy.approvalReference,'مرجع تأیید متن');
  if(!fs.readFileSync(copy.absolute,'utf8').replace(/^\uFEFF/,'').trim())throw new Error('فایل متن تأییدشده خالی است.');
  const scenes=plan.scenes.map(scene=>{
    safeId(scene.id);
    if(names.has(scene.id))throw new Error('شناسهٔ صحنه تکراری است.');names.add(scene.id);
    const times=typeof scene.time==='number'?[scene.time]:[scene.time?.start,scene.time?.end];
    if(!times.every(n=>Number.isFinite(n)&&n>=0)||times.length===2&&times[1]<times[0])throw new Error('زمان صحنه معتبر نیست.');
    if(typeof scene.onScreenText!=='string'||typeof scene.narrationPhrase!=='string')throw new Error('متن تصویر و عبارت نریشن هر صحنه باید مشخص باشند؛ برای صحنهٔ بی‌متن رشتهٔ خالی بده.');
    const frame=dependency(scene.image,'storyboard-frame:'+scene.id);
    if(!['.png','.jpg','.jpeg','.webp'].includes(path.extname(frame.path).toLowerCase()))throw new Error('فریم استوری‌بورد باید PNG/JPEG/WebP باشد.');
    return {...scene,image:frame.path};
  });
  if(!Array.isArray(plan.media))throw new Error('فهرست رسانه باید آرایه باشد؛ برای کار بدون رسانه آرایهٔ خالی بده.');
  for(const media of plan.media)dependency(media.file,nonempty(media.usage,'کاربرد رسانه',1000));
  if(!['file','existing-speech','none','silent'].includes(plan.narration?.mode))throw new Error('وضعیت نریشن صریح لازم است.');
  if(['file','existing-speech'].includes(plan.narration.mode))dependency(plan.narration.file,'narration',false);
  else if(plan.narration.file)throw new Error('در حالت بدون نریشن، فایل نریشن نده.');
  if(!['none','file','external-prompt'].includes(plan.music?.mode))throw new Error('وضعیت موسیقی صریح لازم است.');
  if(plan.music.mode==='file')dependency(plan.music.file,'music',false);
  if(plan.music.mode==='external-prompt') {
    dependency(plan.music.promptFile,'music-prompt');
    if(plan.music.file)dependency(plan.music.file,'music',false);
  }
  if(plan.narration.mode==='silent'&&plan.music.mode!=='none')throw new Error('سفارش کاملاً بی‌صدا موسیقی ندارد.');
  return {plan:structuredClone({...plan,scenes}),dependencies};
}

function latestVersion(dest) {
  const dir=inside(dest,'analysis');
  if(!fs.existsSync(dir))return 0;
  return Math.max(0,...fs.readdirSync(dir).map(name=>/^storyboard-v([1-9]\d*)$/.exec(name)).filter(Boolean).map(match=>Number(match[1])));
}

/** Register rendered frames and bind the visual proposal to its production inputs. */
export async function registerStoryboard(id,plan,root=ROOT) {
  const dest=order(id,root),validated=validatePlan(dest,plan);
  const thumbnails=[];
  for(const scene of validated.plan.scenes) {
    const frame=localFile(dest,scene.image);
    const metadata=await sharp(frame.absolute,{limitInputPixels:40000000}).metadata();
    if(!['png','jpeg','webp'].includes(metadata.format)||!metadata.width||!metadata.height||metadata.pages>1)throw new Error('فریم باید تصویر ثابت واقعی PNG/JPEG/WebP باشد.');
    // Decode pixels: file extension or header alone is insufficient evidence of a rendered frame.
    thumbnails.push(await sharp(frame.absolute,{limitInputPixels:40000000}).rotate().resize(300,300,{fit:'contain',background:'#f4f4f4'}).png().toBuffer());
  }
  const snapshot=inputSnapshot(dest);
  const version=latestVersion(dest)+1,relative='analysis/storyboard-v'+version,folder=inside(dest,relative);
  fs.mkdirSync(folder,{recursive:false});
  const contactSheets=[];
  for(let start=0;start<thumbnails.length;start+=12) {
    const page=thumbnails.slice(start,start+12),rows=Math.ceil(page.length/3),overlays=[];
    for(let i=0;i<page.length;i++) {
      const left=(i%3)*320+10,top=Math.floor(i/3)*336+28;
      overlays.push({input:page[i],left,top});
      const label=Buffer.from(`<svg width="300" height="22"><text x="8" y="17" font-family="sans-serif" font-size="16" fill="#111">${start+i+1}</text></svg>`);
      overlays.push({input:label,left,top:top-24});
    }
    const name=`contact-sheet-${Math.floor(start/12)+1}.png`,file=inside(folder,name);
    await sharp({create:{width:960,height:rows*336,channels:3,background:'#ffffff'}}).composite(overlays).png().toFile(file);
    contactSheets.push({path:relative+'/'+name,sha256:fileHash(file)});
  }
  writeJson(inside(folder,'plan.json'),validated.plan);
  const manifest={schemaVersion:1,id,version,createdAt:new Date().toISOString(),planSha256:fileHash(inside(folder,'plan.json')),
    inputFingerprint:snapshot.fingerprint,inputs:snapshot.files,dependencies:validated.dependencies,contactSheets};
  writeJson(inside(folder,'manifest.json'),manifest);
  const state={schemaVersion:1,id,version,manifestPath:relative+'/manifest.json',manifestSha256:fileHash(inside(folder,'manifest.json'))};
  writeJson(inside(dest,'analysis/storyboard.json'),state);
  return {...state,contactSheets:contactSheets.map(sheet=>sheet.path),inputFingerprint:snapshot.fingerprint,ready:false,
    next:'تصویرها را به کاربر نشان بده؛ سپس version/reference/response/presentedReference را از تأیید واقعی همان نسخه ثبت کن.'};
}

function readCurrent(dest,id) {
  const state=readJson(inside(dest,'analysis/storyboard.json'));
  if(state.id!==id||!Number.isInteger(state.version)||state.version<1||state.version!==latestVersion(dest))throw new Error('نسخهٔ استوری‌بورد جاری نیست.');
  const expected=`analysis/storyboard-v${state.version}/manifest.json`;
  if(state.manifestPath!==expected)throw new Error('مسیر manifest استوری‌بورد معتبر نیست.');
  const manifestFile=localFile(dest,expected);
  if(fileHash(manifestFile.absolute)!==state.manifestSha256)throw new Error('manifest استوری‌بورد تغییر کرده است.');
  const manifest=readJson(manifestFile.absolute),folder=path.dirname(manifestFile.absolute),planFile=inside(folder,'plan.json');
  if(manifest.id!==id||manifest.version!==state.version||fileHash(planFile)!==manifest.planSha256)throw new Error('طرح یا نسخهٔ استوری‌بورد تغییر کرده است.');
  if(inputSnapshot(dest).fingerprint!==manifest.inputFingerprint)throw new Error('متن، منبع، رسانه یا تنظیمات تولید تغییر کرده؛ استوری‌بورد جدید لازم است.');
  for(const record of [...manifest.dependencies,...manifest.contactSheets]) {
    const current=localFile(dest,record.path,{required:record.sha256!==null});
    if(current.sha256!==record.sha256)throw new Error('فایل وابسته یا تصویر استوری‌بورد تغییر کرده: '+record.path);
  }
  const plan=readJson(planFile);
  validatePlan(dest,plan);
  return {state,manifest,plan,folder};
}

/** Recorded references are evidence supplied by the agent, not automatic user authentication. */
export async function approveStoryboard(id,{version,reference,response,presentedReference}={},root=ROOT) {
  const dest=order(id,root),current=readCurrent(dest,id);
  if(Number(version)!==current.state.version)throw new Error('تأیید باید برای نسخهٔ جاری استوری‌بورد باشد.');
  const approval={schemaVersion:1,version:current.state.version,manifestSha256:current.state.manifestSha256,inputFingerprint:current.manifest.inputFingerprint,
    reference:nonempty(reference,'مرجع پاسخ کاربر',2000),response:nonempty(response,'پاسخ تأیید کاربر'),
    presentedReference:nonempty(presentedReference,'مرجع نمایش تصویرها به کاربر',2000),at:new Date().toISOString()};
  const output=inside(current.folder,'approval.json');
  fs.writeFileSync(output,JSON.stringify(approval,null,2)+'\n',{encoding:'utf8',flag:'wx'});
  return checkProduction(id,root);
}

/** Synchronous so render wrappers cannot launch before checking this evidence. */
export function checkProduction(id,root=ROOT) {
  const reasons=[];let current;
  try {current=readCurrent(order(id,root),id);}
  catch(error) {return {id,ready:false,reasons:[error.message]};}
  const {state,manifest,plan,folder}=current;
  try {
    const approval=readJson(inside(folder,'approval.json'));
    if(approval.version!==state.version||approval.manifestSha256!==state.manifestSha256||approval.inputFingerprint!==manifest.inputFingerprint)throw new Error('تأیید به نسخه و ورودی جاری متصل نیست.');
    nonempty(approval.reference,'مرجع تأیید');nonempty(approval.response,'پاسخ کاربر');nonempty(approval.presentedReference,'مرجع نمایش تصویر');
  } catch(error) {reasons.push('تأیید تصویری معتبر ثبت نشده: '+error.message);}
  const requiredMedia=(value,label)=>{
    if(!value) {reasons.push(label+' واقعی هنوز دریافت نشده است.');return;}
    try {const file=localFile(order(id,root),value);if(!fs.statSync(file.absolute).size)throw new Error('فایل خالی است.');}
    catch(error) {reasons.push(label+': '+error.message);}
  };
  if(['file','existing-speech'].includes(plan.narration.mode))requiredMedia(plan.narration.file,'فایل نریشن/گفتار');
  if(plan.music.mode!=='none')requiredMedia(plan.music.file,'فایل موسیقی زمینه');
  return {id,ready:reasons.length===0,reasons,version:state.version,manifestPath:state.manifestPath,contactSheets:manifest.contactSheets.map(sheet=>sheet.path)};
}

/** Real orders are gated, including continued legacy orders; examples are exempt. */
export function assertProductionReadyForPath(input,root=ROOT) {
  const base=path.resolve(root,'.local/projects'),absolute=path.resolve(root,input||'.');
  // A path outside projects may alias a real order through a junction; it is not an example exemption.
  const resolved=fs.existsSync(absolute)?fs.realpathSync(absolute):absolute;
  const lexical=path.relative(base,absolute),canonical=path.relative(base,resolved);
  const isInside=value=>value!== '..'&&!value.startsWith('..'+path.sep)&&!path.isAbsolute(value);
  const relative=isInside(lexical)?lexical:canonical;
  if(relative==='..'||relative.startsWith('..'+path.sep)||path.isAbsolute(relative))return {ready:true,exempt:true};
  if(!relative)throw new Error('مسیر یک سفارش مشخص را برای رندر بده.');
  const id=relative.split(path.sep)[0];
  inside(base,relative);
  const report=checkProduction(id,root);
  if(!report.ready)throw new Error('رندر نهایی مسدود است: '+report.reasons.join(' | '));
  return report;
}

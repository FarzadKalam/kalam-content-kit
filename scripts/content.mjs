#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {ROOT,inside,readJson,writeJson,browser,localEnv} from './lib/paths.mjs';
import {binary} from './lib/tools.mjs';
import {python} from './lib/studio-runtime.mjs';
import {createContentProject,projectPath,attachReference,buildBrief,saveRevision,kinds} from './content-projects.mjs';
import {defaultDataRequests,refreshData,importWebData,validateData} from './content-data.mjs';
import {contentGuidance} from './content-guidance.mjs';
const [command,...args]=process.argv.slice(2),opts={},pos=[];
for(let i=0;i<args.length;i++) {
  if(args[i].startsWith('--'))opts[args[i].slice(2)]=args[i+1]&&!args[i+1].startsWith('--')?args[++i]:true;
  else pos.push(args[i]);
}
const print=value=>console.log(JSON.stringify(value,null,2));
const required=value=>{if(typeof value!=='string'||!value)throw new Error('آرگومان لازم را وارد کن؛ content help را ببین.');return value;};
function merge(base,patch) {
  if(!patch||Array.isArray(patch)||typeof patch!=='object')return patch;
  const value=base&&typeof base==='object'&&!Array.isArray(base)?{...base}:{};
  for(const [key,item] of Object.entries(patch)) {
    if(['__proto__','constructor','prototype'].includes(key))throw new Error('کلید نامعتبر است.');
    value[key]=merge(value[key],item);
  }
  return value;
}
try {
  if(command==='help'||!command)print({commands:{
    doctor:'بررسی ابزار محلی؛ وجود تصویرساز و نریشن را خود عامل جدا بررسی کند',
    settings:'--template news_story | --profile post | --all',
    guide:'[job] [--kind motion] [--purpose motion] [--template morning_local] [--profile channel]؛ شناخت قابلیت‌ها و فرم مرتبط، بدون تولید',
    new:'--id job --kind image|text|slides|audio|video-prompts|motion --brand golbahar [--template news_story] [--purpose motion] [--spec file.json]',
    set:'job --patch changes.json (تنظیمات فعلی حفظ و نسخهٔ قبلی ذخیره می‌شود)',
    attach:'job input.png [--kind presenter --entityId kamran --scope studio]',
    brief:'job (دریافت دادهٔ عمومی لازم و ساخت دستور؛ مدل تولید محتوا فراخوانی نمی‌شود)',
    refresh:'job [--force] [--replace]؛ دریافت دادهٔ عمومی، ثبت منبع و حفظ مقادیر دستی',
    'data-plan':'job؛ فهرست درخواست‌های دادهٔ موردنیاز قالب',
    'data-import':'job --binding rates-request --file evidence.json؛ ورود مدرک بازبینی‌شدهٔ ابزار وب',
    resume:'job',capabilities:'job --file evidence.json',
    'image-export':'job input.png [--slide 1] (تطبیق ابعاد بدون برش؛ کنترل alpha استیکر)',
    'text-export':'job output.txt (اعتبارسنجی JSON اسلایدها در صورت نیاز)',
    pack:'job (بستهٔ کامل همان سفارش؛ خصوصی و خارج Git)'}});
  else if(command==='doctor') {
    let py;try{py=python(['-c','import sys; print(sys.version); assert sys.version_info >= (3,11)']).trim()}catch(e){py=null}
    const [major,minor]=process.versions.node.split('.').map(Number);
    const checks={node:{passed:major>22||major===22&&minor>=12,value:process.version},python:{passed:!!py,value:py},
      writableRoot:{passed:false,value:ROOT},browser:{passed:!!browser(),value:browser()||null}};
    try{fs.accessSync(ROOT,fs.constants.W_OK);checks.writableRoot.passed=true}catch{}
    for(const name of ['ffmpeg','ffprobe']){try{checks[name]={passed:fs.existsSync(binary(name))}}catch{checks[name]={passed:false}}}
    checks.hyperframes={passed:fs.existsSync(path.join(ROOT,'node_modules/hyperframes/package.json'))};
    print({local:checks,hostTools:{image:{status:'unknown',action:'عامل باید ابزار واقعی همین جلسه را بررسی کند'},speech:{status:'unknown',fallback:'فایل صوتی ادمین'},music:{status:'unknown',fallback:'فایل مجاز یا پرامپت برای تولید جداگانهٔ کاربر'}},
      ready:{text:checks.node.passed&&checks.python.passed&&checks.writableRoot.passed,
        media:Object.values(checks).every(v=>v.passed)},runtimeSnapshot:readJson(path.join(ROOT,'config/studio/status.json'))});
    if(!checks.node.passed||!checks.python.passed||!checks.writableRoot.passed)process.exitCode=1;
  } else if(command==='guide') {
    if(pos[0]) {
      const dest=projectPath(pos[0]);
      print(contentGuidance({spec:readJson(inside(dest,'spec.json')),state:readJson(inside(dest,'project.json')),settingsDir:inside(dest,'settings')}));
    } else {
      if(opts.kind&&!kinds.includes(opts.kind))throw new Error('نوع راهنما معتبر نیست.');
      print(contentGuidance({spec:{kind:opts.kind,profile:opts.profile,purpose:opts.purpose,
        ...(opts.template?{request:{format:{template:opts.template}}}:{})}}));
    }
  } else if(command==='settings') {
    const ui=readJson(path.join(ROOT,'catalog/studio-ui.json')),rules=readJson(path.join(ROOT,'catalog/studio.json'));
    if(opts.all)print({ui,rules});
    else if(opts.template) {
      const template=ui.templates.find(t=>t.id===opts.template);if(!template)throw new Error('قالب ناشناخته است.');
      print({template,prompt:rules.imageTemplates[opts.template],contentDefaults:ui.initialContent,
        controls:ui.controls.filter(c=>c.conditions.some(x=>x.includes(opts.template))),
        commonOptions:ui.stateDefaults.filter(s=>/^(news|studio|image|logo|advertising|citizen|videoFrame|videoOverlay|siteLink)/.test(s.name)),
        completeSettings:'catalog/studio-ui.json',sourceBuilders:ui.requestBuilders});
    } else if(opts.profile) {if(!rules.editorialProfiles[opts.profile])throw new Error('نوع متن ناشناخته است.');print(rules.editorialProfiles[opts.profile]);}
    else print({kinds,templates:ui.templates,editorialProfiles:Object.fromEntries(Object.entries(rules.editorialProfiles).map(([k,v])=>[k,v.label])),sourceModels:rules.imageModels,sourceVoices:rules.voiceEngines,limits:rules.limits,publicDataCatalog:'catalog/public-data.json',newsDiscovery:true,newsSettings:'config/news.json',newsGuide:'docs/studio/news-discovery.fa.md',sourceStatus:rules.runtimeSnapshot,assistantGuide:'content guide'});
  } else if(command==='new') {
    const options={...opts,id:required(opts.id)};if(opts.spec)options.spec=readJson(opts.spec);
    print({project:createContentProject(options)});
  } else if(command==='set') {
    const dest=projectPath(required(pos[0])),file=inside(dest,'spec.json');const before=readJson(file),patch=readJson(required(opts.patch));
    const next=merge(before,patch);
    if(next.kind!==before.kind||next.brand!==before.brand)throw new Error('نوع و برند سفارش را با تغییر تنظیمات عوض نکن؛ سفارش مستقل بساز.');
    if(patch.dataRequests===undefined&&(patch.request?.format?.template||patch.request?.content?.sportMode||patch.slides))next.dataRequests=defaultDataRequests(next).map(binding=>({...binding,...before.dataRequests?.find(old=>old.id===binding.id&&old.task===binding.task)}));
    saveRevision(dest,'settings-change');writeJson(file,next);
    const state=readJson(inside(dest,'project.json'));state.phase='brief';delete state.latestBrief;delete state.latestBriefSpecSha256;writeJson(path.join(dest,'project.json'),state);print({spec:file});
  } else if(command==='attach')print(attachReference(required(pos[0]),required(pos[1]),opts));
  else if(command==='refresh')print(refreshData(projectPath(required(pos[0])),{force:!!opts.force,replace:!!opts.replace,saveRevision}));
  else if(command==='data-plan') {const spec=readJson(inside(projectPath(required(pos[0])),'spec.json'));print({configured:spec.dataRequests||[],suggested:defaultDataRequests(spec),catalog:'catalog/public-data.json'});}
  else if(command==='data-import')print(importWebData(projectPath(required(pos[0])),required(opts.binding),required(opts.file),{replace:!!opts.replace,saveRevision}));
  else if(command==='brief') {const result=buildBrief(required(pos[0]));print({file:result.file,kind:result.result.kind});}
  else if(command==='resume') {
    const dest=projectPath(required(pos[0]));
    print({project:readJson(inside(dest,'project.json')),spec:readJson(inside(dest,'spec.json')),
      brief:fs.readFileSync(inside(dest,'BRIEF.md'),'utf8'),decisions:fs.readFileSync(inside(dest,'DECISIONS.md'),'utf8'),review:fs.readFileSync(inside(dest,'REVIEW.md'),'utf8')});
  } else if(command==='capabilities') {
    const dest=projectPath(required(pos[0])),state=readJson(inside(dest,'project.json')),evidence=readJson(required(opts.file));
    for(const [key,value] of Object.entries(evidence)) {
      if(!['image','speech','music','transcription','fileAccess'].includes(key)||!['available','unavailable','unknown'].includes(value.status)||typeof value.evidence!=='string'||!value.evidence.trim())throw new Error('وضعیت ابزار باید همراه مدرک واقعی ثبت شود.');
    }
    saveRevision(dest,'host-capabilities');state.capabilities={...state.capabilities,...evidence};writeJson(path.join(dest,'project.json'),state);print(state.capabilities);
  } else if(command==='image-export'||command==='text-export') {
    const dest=projectPath(required(pos[0])),state=readJson(inside(dest,'project.json'));
    validateData(dest);
    if(!state.latestBrief)throw new Error('ابتدا brief بساز.');
    const currentSpecHash=crypto.createHash('sha256').update(fs.readFileSync(inside(dest,'spec.json'))).digest('hex');
    if(state.latestBriefSpecSha256!==currentSpecHash)throw new Error('تنظیمات سفارش پس از ساخت brief تغییر کرده؛ brief تازه بساز.');
    const brief=readJson(inside(dest,state.latestBrief));
    const renders=inside(dest,'renders');fs.mkdirSync(renders,{recursive:true});
    const index=Number(opts.slide||1)-1;
    if(!Number.isInteger(index)||index<0)throw new Error('شمارهٔ اسلاید معتبر نیست.');
    if(command==='image-export') {
      const slide=brief.slides?.[index];if(!slide)throw new Error('اسلاید وجود ندارد.');
      const {default:sharp}=await import('sharp');const input=required(pos[1]),meta=await sharp(input).metadata();
      if(slide.transparent) {
        if(!meta.hasAlpha)throw new Error('استیکر کانال alpha واقعی ندارد.');
        const stats=await sharp(input).stats();if(stats.isOpaque)throw new Error('استیکر کاملاً مات است.');
      }
      const output=inside(renders,`slide-${String(index+1).padStart(2,'0')}-${crypto.randomUUID()}.png`);
      await sharp(input).rotate().resize(slide.width,slide.height,{fit:'contain',background:{r:0,g:0,b:0,alpha:0}}).png().toFile(output);
      state.artifacts.push({path:path.relative(dest,output).replaceAll('\\','/'),kind:'image',slide:index,brief:state.latestBrief,review:'pending'});
      state.phase='review';writeJson(path.join(dest,'project.json'),state);print({file:output,review:'pending',note:'در صورت تغییر نسبت، حاشیه اضافه شده است؛ برش انجام نشده.'});
    } else {
      if(brief.kind!=='text')throw new Error('سفارش متنی نیست.');
      const input=required(pos[1]);let output=inside(renders,`text-${crypto.randomUUID()}.txt`);
      if(brief.outputContract==='slide-json') {
        const deck=JSON.parse(python([path.join(ROOT,'scripts/studio.py'),'slides-validate',input]));
        output=output.replace(/\.txt$/,'.json');writeJson(output,deck);
      } else fs.copyFileSync(input,output,fs.constants.COPYFILE_EXCL);
      state.artifacts.push({path:path.relative(dest,output).replaceAll('\\','/'),kind:'text',brief:state.latestBrief,review:'pending'});state.phase='review';writeJson(path.join(dest,'project.json'),state);print({file:output});
    }
  } else if(command==='pack') {
    const dest=projectPath(required(pos[0])),{default:AdmZip}=await import('adm-zip');const zip=new AdmZip();
    function add(dir,relative='') {
      for(const entry of fs.readdirSync(dir,{withFileTypes:true})) {
        if(entry.isSymbolicLink())throw new Error('بستهٔ سفارش نباید symlink داشته باشد.');
        const rel=path.posix.join(relative,entry.name),file=inside(dest,rel);
        if(entry.isDirectory())add(file,rel);else if(!entry.name.endsWith('.zip'))zip.addFile(rel,fs.readFileSync(file));
      }
    }
    add(dest);const output=inside(dest,`renders/order-${Date.now()}.zip`);zip.writeZip(output);print({file:output,private:true});
  } else throw new Error('دستور ناشناخته است؛ content help را ببین.');
} catch(error) {console.error(error.message);process.exitCode=1;}

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {ROOT,inside,safeId,readJson,writeJson} from './lib/paths.mjs';

const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
const hash=file=>sha(fs.readFileSync(file));
const fields=['id','kind','brand','engine','mode','width','height','fps','duration','durationSeconds','durationInFrames','audio','music','motion','production','fonts'];
const text=(value,label,max=16000)=>{
  if(typeof value!=='string'||!value.trim()||value.length>max)throw new Error(label+' باید متن غیرخالی باشد.');
  return value.trim();
};
function order(id,root) {
  const dest=inside(path.join(root,'.local/projects'),safeId(id));
  const project=readJson(inside(dest,'project.json'));
  const specFile=inside(dest,'spec.json'),spec=fs.existsSync(specFile)?readJson(specFile):null;
  const kind=spec?.kind||project.kind||((project.engine&&project.mode)?'motion':null);
  if(!['image','slides','motion','video-prompts'].includes(kind))throw new Error('طرح تصویر برای سفارش تصویر، اسلاید، موشن یا مراجع ویدیوی مولد است.');
  if(spec?.kind&&project.kind&&spec.kind!==project.kind)throw new Error('نوع سفارش با تنظیمات تصویر یکسان نیست.');
  if(spec?.brand&&project.brand&&spec.brand!==project.brand)throw new Error('برند سفارش با تنظیمات تصویر یکسان نیست.');
  return {dest,project,spec,kind};
}
function reference(dest,value) {
  if(typeof value!=='string'||!value.trim()||path.isAbsolute(value)||value.includes('\\')||/^[a-z][a-z0-9+.-]*:/i.test(value))throw new Error('مرجع تصویر باید مسیر نسبی محلی با / در سفارش باشد.');
  const file=inside(dest,value),relative=path.relative(dest,file).replaceAll('\\','/');
  if(!relative||!fs.existsSync(file)||!fs.statSync(file).isFile()||!fs.statSync(file).size)throw new Error('فایل مرجع تصویر واقعی و غیرخالی لازم است: '+value);
  return {path:relative,sha256:hash(file)};
}
function validatePlan(dest,value) {
  if(!value||!['generate','edit'].includes(value.mode))throw new Error('حالت طرح تصویر باید generate یا edit باشد.');
  if(!Array.isArray(value.images)||!value.images.length||value.images.length>100)throw new Error('طرح باید یک تا صد تصویر توصیف‌شده داشته باشد.');
  const ids=new Set(),references=new Map();
  const images=value.images.map(image=>{
    const id=safeId(image?.id);
    if(ids.has(id))throw new Error('شناسهٔ تصویر در طرح تکراری است.');
    ids.add(id);
    if(typeof image.text!=='string'||image.text.length>20000)throw new Error('متن دقیق روی تصویر باید رشته باشد؛ برای تصویر بی‌نوشته رشتهٔ خالی بده.');
    if(!Array.isArray(image.referencePaths))throw new Error('referencePaths هر تصویر باید آرایه باشد.');
    const referencePaths=image.referencePaths.map(value=>{
      const record=reference(dest,value);references.set(record.path,record);return record.path;
    });
    if(new Set(referencePaths).size!==referencePaths.length)throw new Error('مرجع تصویر تکراری است.');
    if(value.mode==='edit'&&!referencePaths.length)throw new Error('ویرایش هر تصویر به فایل مرجع نیاز دارد.');
    return {id,description:text(image.description,'شرح دقیق تصویر'),style:text(image.style,'سبک تصویر'),text:image.text,referencePaths};
  });
  return {plan:{mode:value.mode,count:images.length,images},references:[...references.values()].sort((a,b)=>a.path.localeCompare(b.path,'en'))};
}
function snapshot(current) {
  const {dest,project,spec}=current;
  if(!spec&&current.kind!=='motion')throw new Error('فایل spec سفارش تصویر موجود نیست.');
  const specSha256=spec?hash(inside(dest,'spec.json')):sha(JSON.stringify(Object.fromEntries(fields.filter(key=>key in project).map(key=>[key,project[key]]))));
  const brandFile=inside(dest,'brand.json');
  const brandSha256=sha(JSON.stringify({brand:project.brand,profile:fs.existsSync(brandFile)?hash(brandFile):null}));
  return {specSha256,brandSha256,specSource:spec?'spec.json':'project-production-fields'};
}
function latestVersion(dest) {
  const folder=inside(dest,'analysis');
  if(!fs.existsSync(folder))return 0;
  return Math.max(0,...fs.readdirSync(folder).map(name=>/^image-plan-v([1-9]\d*)$/.exec(name)).filter(Boolean).map(match=>Number(match[1])));
}
const writeImmutable=(file,value)=>fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n',{encoding:'utf8',flag:'wx'});

/** Register the exact proposal before invoking any image generator, including edits. */
export function registerImagePlan(id,plan,root=ROOT) {
  const current=order(id,root),{dest}=current,validated=validatePlan(dest,plan),inputs=snapshot(current);
  const version=latestVersion(dest)+1,relative=`analysis/image-plan-v${version}`,folder=inside(dest,relative);
  fs.mkdirSync(inside(dest,'analysis'),{recursive:true});fs.mkdirSync(folder);
  writeImmutable(inside(folder,'plan.json'),validated.plan);
  const manifest={schemaVersion:1,id,version,createdAt:new Date().toISOString(),planSha256:hash(inside(folder,'plan.json')),
    ...inputs,references:validated.references};
  writeImmutable(inside(folder,'manifest.json'),manifest);
  const state={schemaVersion:1,id,version,manifestPath:relative+'/manifest.json',manifestSha256:hash(inside(folder,'manifest.json'))};
  writeJson(inside(dest,'analysis/image-approval.json'),state);
  return {...state,...inputs,status:'awaiting-user-approval',ready:false,count:validated.plan.count,
    next:'شرح دقیق همین تصویرها، سبک، متن و مراجع را به کاربر بده؛ سپس مرجع پیام و نقل پاسخ تأیید واقعی همین نسخه را ثبت کن.'};
}
function readCurrent(id,root) {
  const current=order(id,root),{dest}=current,state=readJson(inside(dest,'analysis/image-approval.json'));
  if(state.id!==id||!Number.isInteger(state.version)||state.version<1||state.version!==latestVersion(dest))throw new Error('نسخهٔ طرح تصویر جاری نیست.');
  if(state.manifestPath!==`analysis/image-plan-v${state.version}/manifest.json`)throw new Error('مسیر manifest طرح تصویر معتبر نیست.');
  const manifestFile=inside(dest,state.manifestPath);
  if(hash(manifestFile)!==state.manifestSha256)throw new Error('manifest طرح تصویر تغییر کرده است.');
  const manifest=readJson(manifestFile),folder=path.dirname(manifestFile),planFile=inside(folder,'plan.json');
  if(manifest.id!==id||manifest.version!==state.version||hash(planFile)!==manifest.planSha256)throw new Error('شرح یا نسخهٔ طرح تصویر تغییر کرده است.');
  const inputs=snapshot(current);
  if(inputs.specSha256!==manifest.specSha256||inputs.specSource!==manifest.specSource||inputs.brandSha256!==manifest.brandSha256)throw new Error('متن، تنظیمات یا برند تغییر کرده؛ طرح تصویر تازه لازم است.');
  const plan=readJson(planFile),validated=validatePlan(dest,plan);
  if(plan.count!==validated.plan.count||JSON.stringify(validated.references)!==JSON.stringify(manifest.references))throw new Error('فایل مرجع یا تعداد تصویرهای طرح تغییر کرده است.');
  return {current,state,manifest,plan,folder};
}

/** This records actual user evidence; it cannot authenticate a human or call a model tool. */
export function approveImagePlan(id,{version,reference:responseReference,response}={},root=ROOT) {
  const {state,manifest,folder}=readCurrent(id,root);
  if(Number(version)!==state.version)throw new Error('تأیید باید برای نسخهٔ جاری طرح تصویر باشد.');
  const approval={schemaVersion:1,version:state.version,manifestSha256:state.manifestSha256,specSha256:manifest.specSha256,
    brandSha256:manifest.brandSha256,planSha256:manifest.planSha256,references:manifest.references,
    reference:text(responseReference,'مرجع پیام تأیید کاربر',2000),response:text(response,'نقل پاسخ تأیید کاربر'),at:new Date().toISOString()};
  writeImmutable(inside(folder,'approval.json'),approval);
  return imageApprovalStatus(id,root);
}

export function imageApprovalStatus(id,root=ROOT) {
  let current;
  try {current=readCurrent(id,root);}
  catch(error) {return {id,status:'awaiting-user-approval',ready:false,reasons:[error.message]};}
  const {state,manifest,plan,folder}=current,reasons=[];
  try {
    const approval=readJson(inside(folder,'approval.json'));
    for(const field of ['version','manifestSha256'])if(approval[field]!==state[field])throw new Error('تأیید به نسخهٔ جاری طرح وصل نیست.');
    for(const field of ['specSha256','brandSha256','planSha256'])if(approval[field]!==manifest[field])throw new Error('تأیید به ورودی جاری تصویر وصل نیست.');
    if(JSON.stringify(approval.references)!==JSON.stringify(manifest.references))throw new Error('مراجع تأییدشده با طرح یکسان نیستند.');
    text(approval.reference,'مرجع تأیید');text(approval.response,'پاسخ تأیید کاربر');
  } catch(error) {reasons.push('تأیید واقعی طرح تصویر ثبت نشده یا معتبر نیست: '+error.message);}
  return {id,status:reasons.length?'awaiting-user-approval':'approved',ready:!reasons.length,reasons,
    version:state.version,manifestPath:state.manifestPath,manifestSha256:state.manifestSha256,specSha256:manifest.specSha256,plan};
}

export function assertImageApproved(id,root=ROOT) {
  const status=imageApprovalStatus(id,root);
  if(!status.ready)throw new Error('تولید/ویرایش یا تحویل تصویر نهایی نیازمند تأیید طرح است: '+status.reasons.join(' | '));
  return status;
}

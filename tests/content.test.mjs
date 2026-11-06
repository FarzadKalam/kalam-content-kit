import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {ROOT,readJson} from '../scripts/lib/paths.mjs';
import {createContentProject,attachReference,buildBrief} from '../scripts/content-projects.mjs';
import {python} from '../scripts/lib/studio-runtime.mjs';
import {refreshData,defaultDataRequests,validateData} from '../scripts/content-data.mjs';
import {registerImagePlan,approveImagePlan} from '../scripts/image-approval.mjs';
function fixture(t) {
  const base=path.join(ROOT,'.cache/tests');fs.mkdirSync(base,{recursive:true});
  const root=fs.mkdtempSync(path.join(base,'content-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  for(const name of ['catalog','brands','config/studio','vendor/studio'])fs.mkdirSync(path.join(root,name),{recursive:true});
  for(const rel of ['catalog/studio-ui.json','catalog/studio.json','brands/golbahar.json','config/studio/status.json','vendor/studio/sources.json'])fs.copyFileSync(path.join(ROOT,rel),path.join(root,rel));
  fs.mkdirSync(path.join(root,'config/studio/prompts'),{recursive:true});fs.writeFileSync(path.join(root,'config/studio/prompts/test.txt'),'نسخهٔ اول');return root;
}
test('new orders freeze settings and refuse replacing another order',t=>{
  const root=fixture(t),dest=createContentProject({id:'job',kind:'image',brand:'golbahar',template:'news_story'},root);
  fs.writeFileSync(path.join(root,'config/studio/prompts/test.txt'),'تغییر مشترک');
  assert.equal(fs.readFileSync(path.join(dest,'settings/prompts/test.txt'),'utf8'),'نسخهٔ اول');
  assert.equal(readJson(path.join(dest,'spec.json')).request.format.logoBehavior,'floating_profile');
  assert.throws(()=>createContentProject({id:'job',kind:'text',brand:'golbahar'},root));
});
test('attachments preserve originals and keep content outside the shared repository',t=>{
  const root=fixture(t),dest=createContentProject({id:'job',kind:'text',brand:'golbahar'},root);
  const input=path.join(root,'original.png');fs.writeFileSync(input,'immutable');
  const ref=attachReference('job',input,{},root);
  assert.equal(fs.readFileSync(input,'utf8'),'immutable');
  assert.equal(fs.readFileSync(path.join(dest,ref.path),'utf8'),'immutable');
  assert.ok(ref.sha256);assert.equal(fs.readdirSync(path.join(dest,'history')).length,1);
});
test('motion orders preserve explicitly selected landscape dimensions',t=>{
  const id='test-landscape-'+process.pid,dest=path.join(ROOT,'.local/projects',id);
  t.after(()=>fs.rmSync(dest,{recursive:true,force:true}));
  createContentProject({id,kind:'motion',brand:'golbahar',width:'1920',height:'1080'});
  const state=readJson(path.join(dest,'project.json')),spec=readJson(path.join(dest,'spec.json'));
  assert.equal(state.width,1920);assert.equal(state.height,1080);
  assert.equal(spec.motion.width,1920);assert.equal(spec.motion.engine,'hyperframes');
});
test('cloud media commands cannot be launched through the renderer wrapper',()=>{
  for(const command of ['tts','transcribe','cloud','publish']) {
    const r=spawnSync(process.execPath,['scripts/kit.mjs','hf',command],{cwd:ROOT,encoding:'utf8'});
    assert.equal(r.status,1);assert.match(r.stderr,/محلی/);
  }
});
test('offline Studio and live-export regression suite',()=>{
  const output=python(['-m','unittest','discover','-s','tests','-p','test_*.py']);
  assert.equal(typeof output,'string');
});
test('sticker export rejects opaque alpha and stale briefs while preserving real transparency',async t=>{
  const {default:sharp}=await import('sharp');
  const id='test-alpha-'+process.pid,dest=path.join(ROOT,'.local/projects',id);
  t.after(()=>fs.rmSync(dest,{recursive:true,force:true}));
  createContentProject({id,kind:'image',brand:'golbahar',template:'sticker'});
  const specPath=path.join(dest,'spec.json'),spec=readJson(specPath);spec.request.content.stickerText='آزمون شفافیت';fs.writeFileSync(specPath,JSON.stringify(spec));
  const proposal=registerImagePlan(id,{mode:'generate',images:[{id:'alpha-test',description:'آزمون فنی شفافیت، تصویر واقعی سفارش نیست',style:'fixture',text:'آزمون شفافیت',referencePaths:[]}]});
  approveImagePlan(id,{version:proposal.version,reference:'unit-test-user-message',response:'تأیید ساختگی فقط برای آزمون نرم‌افزار'});
  buildBrief(id);
  const opaque=path.join(dest,'opaque.png'),transparent=path.join(dest,'transparent.png');
  await sharp({create:{width:32,height:32,channels:4,background:{r:20,g:40,b:60,alpha:1}}}).png().toFile(opaque);
  await sharp({create:{width:32,height:32,channels:4,background:{r:20,g:40,b:60,alpha:0.5}}}).png().toFile(transparent);
  const run=input=>spawnSync(process.execPath,['scripts/content.mjs','image-export',id,input],{cwd:ROOT,encoding:'utf8'});
  const extra=spawnSync(process.execPath,['scripts/content.mjs','image-export',id,transparent,'--slide','2'],{cwd:ROOT,encoding:'utf8'});
  assert.equal(extra.status,1);assert.match(extra.stderr,/برنامهٔ تأییدشده نیست/);
  assert.equal(run(opaque).status,1);
  const good=run(transparent);assert.equal(good.status,0,good.stderr);
  const result=JSON.parse(good.stdout);assert.equal((await sharp(result.file).metadata()).width,1024);
  spec.request.content.stickerText='متن تازه';fs.writeFileSync(specPath,JSON.stringify(spec));
  const stale=run(transparent);assert.equal(stale.status,1);assert.match(stale.stderr,/تغییر/);
});
function weatherEvidence() {
  const date=python(['-c',"import sys;sys.path.insert(0,'scripts');import public_data as d;print(d.target_date('today',d.now_utc()))"]).trim();
  return {schemaVersion:1,task:'weather',status:'ready',fetchedAt:new Date().toISOString(),expiresAt:new Date(Date.now()+900000).toISOString(),
    meta:{city:'golbahar',date,timeZone:'Asia/Tehran',observedAt:new Date().toISOString()},sources:[{url:'https://api.open-meteo.com/',retrievedAt:new Date().toISOString(),sha256:'0'.repeat(64)}],warnings:[],
    values:{morningWeatherCondition:'ابری',morningMinTemperature:'۸',morningMaxTemperature:'۱۸',morningWindSpeed:'۵ km/h',morningHumidity:'۶۰٪',morningAttire:'ژاکت سبک'}};
}
test('morning orders declare real data needs and use the selected city',t=>{
  const root=fixture(t),dest=createContentProject({id:'morning',kind:'image',brand:'golbahar',template:'morning_local'},root),spec=readJson(path.join(dest,'spec.json'));
  assert.deepEqual(spec.dataRequests.map(b=>b.task),['date','weather','prayer','occasions']);
  assert.equal(spec.request.content.morningCity,'golbahar');
  spec.kind='slides';spec.slides=[spec.request,spec.request];
  assert.ok(defaultDataRequests(spec).some(b=>b.target===1&&b.task==='weather'));
  assert.deepEqual(defaultDataRequests({kind:'image',request:{format:{template:'sport'},content:{sportMode:'news'}}}),[]);
});
test('data refresh preserves manual values, updates owned fields and gates the brief on valid evidence',t=>{
  const root=fixture(t),dest=createContentProject({id:'weather',kind:'image',brand:'golbahar'},root),file=path.join(dest,'spec.json');
  const spec=readJson(file);spec.request.content.title='نمونهٔ آزمون';spec.request.content.morningMinTemperature='۹۹';spec.dataRequests=[{id:'weather-request',task:'weather',target:'request'}];fs.writeFileSync(file,JSON.stringify(spec));
  const evidence=weatherEvidence();const get=()=>[{id:'weather-request',result:evidence}];
  const first=refreshData(dest,{fetchResults:get});assert.equal(first.canRender,true);
  assert.equal(readJson(file).request.content.morningMinTemperature,'۹۹');assert.equal(readJson(file).request.content.morningMaxTemperature,'۱۸');
  evidence.values.morningMaxTemperature='۲۰';refreshData(dest,{fetchResults:get});
  assert.equal(readJson(file).request.content.morningMaxTemperature,'۲۰');assert.equal(readJson(file).request.content.morningMinTemperature,'۹۹');
  assert.equal(validateData(dest).valid,true);
  const result=buildBrief('weather',root);assert.ok(fs.existsSync(result.file));
});
test('failed public data leaves the project blocked and does not inject speculative values',t=>{
  const root=fixture(t),dest=createContentProject({id:'blocked-data',kind:'image',brand:'golbahar'},root),file=path.join(dest,'spec.json'),spec=readJson(file);
  spec.dataRequests=[{id:'weather-request',task:'weather',target:'request'}];fs.writeFileSync(file,JSON.stringify(spec));
  const report=refreshData(dest,{fetchResults:()=>[{id:'weather-request',result:{...weatherEvidence(),status:'blocked',values:{},error:'offline'}}]});
  assert.equal(report.canRender,false);assert.equal(readJson(path.join(dest,'project.json')).phase,'data-blocked');
  assert.equal(readJson(file).request.content.morningMinTemperature,'');assert.throws(()=>validateData(dest));
});

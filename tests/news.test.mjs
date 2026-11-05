import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {ROOT,readJson,writeJson} from '../scripts/lib/paths.mjs';
import {buildBrief} from '../scripts/content-projects.mjs';
import {newsSettings,publicNewsUrl,createNewsRun,buildNewsPlan,assessNewsItem,importNewsEvidence,newsDigest,markNewsItem,newsToContent} from '../scripts/news-projects.mjs';

const NOW=new Date().toISOString();
const hoursAgo=n=>new Date(Date.parse(NOW)-n*3600000).toISOString();
function fixture(t,category='national') {
  const base=path.join(ROOT,'.cache/tests');fs.mkdirSync(base,{recursive:true});
  const root=fs.mkdtempSync(path.join(base,'news-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  for(const rel of ['config/news.json','vendor/news-seeker/source-rules.json','config/studio/assistant-prompts/news-discovery.txt','catalog/studio-ui.json','catalog/studio.json','brands/golbahar.json','vendor/studio/sources.json']) {
    fs.mkdirSync(path.dirname(path.join(root,rel)),{recursive:true});fs.copyFileSync(path.join(ROOT,rel),path.join(root,rel));
  }
  fs.cpSync(path.join(ROOT,'config/studio'),path.join(root,'config/studio'),{recursive:true});
  const dest=createNewsRun({id:'scan',category},root);
  return {root,dest,settings:newsSettings(root),run:readJson(path.join(dest,'run.json'))};
}
function article(patch={}) {
  return {title:'گزارش تازه از افتتاح مرکز آموزشی گلبهار',summary:'این خبر نمونهٔ ساختگی آزمون است.',url:'https://www.irna.ir/news/123',sourceId:'irna',scope:'national',
    publishedAt:hoursAgo(1),publishedDateText:'زمان ساختگی آزمون',eventStatus:'current',eventReason:'فقط fixture آزمون',
    evidence:{url:'https://www.irna.ir/news/123',access:'full',excerpt:'شاهد ساختگی آزمون',retrievedAt:NOW,tool:'test-fixture'},facts:['واقعیت ساختگی آزمون'],...patch};
}
const atUrl=(url,patch={})=>{const item=article(patch);return {...item,url,evidence:{...item.evidence,url}};};
const batch=items=>({executedQueries:[{query:'جستجوی ساختگی آزمون',tool:'test-fixture',searchedAt:NOW}],items});

test('news plans freeze settings, retain seven categories and refuse replacing runs',t=>{
  const {root,dest}=fixture(t,'local'),plan=buildNewsPlan('scan',root);
  assert.equal(Object.keys(plan.sourceCatalog).length,17);
  assert.equal(Object.keys(newsSettings(root).categories).length,7);
  assert.ok(plan.queries.some(q=>q.query.includes('site:t.me')));
  assert.ok(plan.queries.some(q=>q.query.includes('چناران')));
  assert.equal(plan.importContract.items[0].eventStatus,'current|update|historical|unknown');
  const file=path.join(root,'config/news.json'),s=readJson(file);s.localTerms=['تهران'];writeJson(file,s);
  assert.ok(readJson(path.join(dest,'settings.json')).localTerms.includes('گلبهار'));
  assert.throws(()=>createNewsRun({id:'scan'},root));
  assert.throws(()=>createNewsRun({id:'../outside'},root));
  assert.throws(()=>createNewsRun({id:'wrong',lookback:0},root));
});

test('article assessment gates freshness, source identity, access and original event time',t=>{
  const {run,settings:s}=fixture(t),assess=patch=>assessNewsItem(article(patch),run,s,{now:NOW});
  assert.equal(assess({}).eligible,true);
  for(const patch of [{publishedAt:null},{publishedAt:'2026-11-06T12:00:00'},{publishedAt:hoursAgo(49)},{publishedAt:hoursAgo(-1)},
    {eventStatus:'historical'},{eventStatus:'current',eventDate:'2020-01-01'},
    {evidence:{...article().evidence,access:'partial'}},{sourceId:'isna'},{pageType:'index'}])assert.equal(assess(patch).eligible,false,JSON.stringify(patch));
  assert.equal(assess({eventStatus:'update',eventDate:'2020-01-01',eventReason:'خبر تازه دربارهٔ پروندهٔ قدیمی؛ نمونه آزمون'}).eligible,true);
  assert.throws(()=>assess({evidence:{...article().evidence,url:'https://isna.ir/a'}}));
  assert.throws(()=>assess({eventDate:'2026-02-30'}));
  assert.throws(()=>assess({potential:{score:101,reason:'invalid'}}));
  assert.throws(()=>assess({saturation:{assessment:'low-observed-coverage',basis:''}}));
});

test('local filters retain documented public-interest exceptions and flag homonyms',t=>{
  const {run,settings:s}=fixture(t,'local'),assess=patch=>assessNewsItem(article(patch),run,s,{now:NOW});
  const title='اعلام استخدام مرکز آموزشی گلبهار';
  assert.equal(assess({title}).eligible,false);
  assert.equal(assess({title,editorialJustification:'اطلاعیهٔ رسمی استخدام عمومی؛ نمونه آزمون'}).eligible,true);
  const homonym='گزارش گلبهار دربارهٔ فلارد';
  assert.equal(assess({title:homonym}).eligible,false);
  assert.equal(assess({title:homonym,localityVerified:true,localityReason:'ارجاع تاریخی به فلارد؛ محل اصلی گلبهار است'}).eligible,true);
  assert.equal(assess({title:'افتتاح مرکز آموزشی در تهران'}).eligible,false);
  const sensitive=assess({title:'گزارش زلزله در گلبهار و بررسی امدادرسانی'});
  assert.equal(sensitive.eligible,true);assert.equal(sensitive.needsReview,true);
});

test('news URLs discard tracking while preserving article identity and forbid local targets',()=>{
  assert.equal(publicNewsUrl('https://irna.ir/news?id=12&utm_source=x#part'),'https://irna.ir/news?id=12');
  assert.notEqual(publicNewsUrl('https://irna.ir/news?id=12'),publicNewsUrl('https://irna.ir/news?id=13'));
  for(const url of ['file:///a','http://localhost/a','http://127.0.0.1/a','https://a.local/a','https://user:password@irna.ir/a'])assert.throws(()=>publicNewsUrl(url));
});

test('digest rebuilds immutable evidence, preserves rejected items and reports unchecked sources',t=>{
  const {root,dest}=fixture(t);
  const payload=batch([article(),atUrl('https://www.irna.ir/news/124',{publishedAt:null,title:'گزارش بدون زمان انتشار مشخص'})]);
  payload.sourceChecks=[{sourceId:'isna',status:'failed',checkedAt:NOW,note:'خطای ساختگی آزمون'}];
  const imported=importNewsEvidence('scan',payload,root,{now:NOW});assert.equal(imported.eligible,1);
  writeJson(path.join(dest,'items.json'),[{id:'fake',eligible:true,title:'دستکاری نمای مشتق‌شده'}]);
  const digest=newsDigest('scan',root,{now:NOW});assert.equal(digest.items.length,2);assert.equal(digest.shortlist.length,1);
  assert.equal(digest.sourceHealth.find(s=>s.sourceId==='isna').lastCheck.status,'failed');
  assert.equal(digest.sourceHealth.find(s=>s.sourceId==='ilna').status,'not-checked');
  assert.equal(digest.publication,false);
  fs.appendFileSync(path.join(dest,imported.batch),' ');
  assert.throws(()=>newsDigest('scan',root,{now:NOW}),/تغییر/);
});

test('reprints share one origin and only documented independent sources earn coverage points',t=>{
  const {root}=fixture(t),origin='https://origin.org/report';
  const a=atUrl('https://www.irna.ir/news/123',{originalSourceUrl:origin,independenceVerified:true,independenceReason:'نمونه آزمون'});
  const b=atUrl('https://www.isna.ir/news/123',{sourceId:'isna',originalSourceUrl:origin,independenceVerified:true,independenceReason:'نمونه آزمون'});
  importNewsEvidence('scan',batch([a,b]),root,{now:NOW});
  const d=newsDigest('scan',root,{now:NOW});assert.equal(d.items.length,1);assert.equal(d.items[0].observedOriginDomains.length,1);
  const base=d.items[0].priorityScore;
  importNewsEvidence('scan',batch([{...b,originalSourceUrl:null,independenceReason:''}]),root,{now:NOW});
  assert.equal(newsDigest('scan',root,{now:NOW}).items[0].priorityScore,base);
  importNewsEvidence('scan',batch([{...b,originalSourceUrl:null}]),root,{now:NOW});
  assert.equal(newsDigest('scan',root,{now:NOW}).items[0].priorityScore,base+7);
  const changed=atUrl('https://www.irna.ir/news/125',{title:a.title+'؛ ظرفیت ۲۰۰ نفر'});
  importNewsEvidence('scan',batch([changed]),root,{now:NOW});assert.equal(newsDigest('scan',root,{now:NOW}).items.length,2);
});

test('used history suppresses local recommendations and old evidence expires on resume',t=>{
  const {root}=fixture(t);importNewsEvidence('scan',batch([article()]),root,{now:NOW});
  const item=newsDigest('scan',root,{now:NOW}).items[0];
  markNewsItem('scan',item.id,'used',{},root);
  assert.equal(newsDigest('scan',root,{now:NOW}).shortlist.length,0);
  assert.equal(newsDigest('scan',root,{now:hoursAgo(-50)}).items[0].eligible,false);
});

test('national suggestions exclude the Golbahar-only ministry source',t=>{
  const {root}=fixture(t,'all');
  importNewsEvidence('scan',batch([atUrl('https://mrud.ir/news/1',{sourceId:'roads_golbahar',scope:'national'})]),root,{now:NOW});
  const d=newsDigest('scan',root,{now:NOW});assert.equal(d.totalStored,1);assert.equal(d.items.length,0);
});

test('selecting news creates a separate content order with evidence and no implicit approvals',t=>{
  const {root}=fixture(t);importNewsEvidence('scan',batch([article()]),root,{now:NOW});
  const item=newsDigest('scan',root,{now:NOW}).items[0];
  const selected=newsToContent('scan',item.id,{project:'chosen',brand:'golbahar'},root);
  const spec=readJson(path.join(selected.project,'spec.json'));
  assert.ok(spec.text.includes(item.title));assert.equal(spec.discovery.sourceUrl,item.url);
  assert.deepEqual(readJson(path.join(selected.project,'project.json')).approvals,[]);
  const brief=buildBrief('chosen',root).result;assert.ok(brief.prompt.includes(item.title));
  assert.equal(newsDigest('scan',root,{now:NOW}).items[0].history[0].action,'selected');
  fs.appendFileSync(path.join(selected.project,spec.discovery.evidencePath),' ');
  assert.throws(()=>buildBrief('chosen',root),/مدرک خبر/);
});

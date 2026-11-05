import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {isIP} from 'node:net';
import {ROOT,inside,safeId,readJson,writeJson} from './lib/paths.mjs';
import {createContentProject,saveRevision} from './content-projects.mjs';

const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
const normalized=value=>String(value||'').normalize('NFKC').replace(/[يى]/g,'ی').replace(/ك/g,'ک').replace(/[\u064b-\u065f\u0670]/g,'').replace(/[\u200c\u200d]/g,' ').replace(/[^\p{L}\p{N}]+/gu,' ').trim().toLowerCase();
const domain=value=>new URL(value).hostname.toLowerCase().replace(/^www\./,'');
const matchesDomain=(host,base)=>host===base||host.endsWith('.'+base);
const stamp=value=>{
  if(typeof value!=='string'||!/(?:Z|[+-]\d\d:\d\d|GMT|[+-]\d{4})$/i.test(value.trim()))return null;
  const n=Date.parse(value);return Number.isFinite(n)?n:null;
};
const asNow=value=>{const n=value===undefined?Date.now():Date.parse(value);if(!Number.isFinite(n))throw new Error('زمان مرجع نامعتبر است.');return n;};

export function publicNewsUrl(value) {
  let url;try{url=new URL(value);}catch{throw new Error('پیوند خبر معتبر نیست.');}
  const host=url.hostname.toLowerCase();
  if(!['http:','https:'].includes(url.protocol)||url.username||url.password||isIP(host.replace(/^\[|\]$/g,''))||!host.includes('.')||/(?:^|\.)(?:localhost|local|internal|test|invalid|example)$/.test(host))throw new Error('خبر به پیوند عمومیِ بدون اطلاعات ورود نیاز دارد.');
  url.hash='';
  for(const key of [...url.searchParams.keys()])if(/^utm_/i.test(key)||['fbclid','gclid','yclid'].includes(key.toLowerCase()))url.searchParams.delete(key);
  url.searchParams.sort();return url.href;
}

export function newsSettings(root=ROOT) {
  const source=readJson(path.join(root,'vendor/news-seeker/source-rules.json'));
  const config=readJson(path.join(root,'config/news.json'));
  const sources=[...source.sources,...(config.additionalSources||[])].filter(s=>!(config.disabledSourceIds||[]).includes(s.id));
  if(new Set(sources.map(s=>s.id)).size!==sources.length)throw new Error('شناسهٔ منبع خبری تکراری است.');
  for(const s of sources) {if(!/^[a-z0-9][a-z0-9_-]{0,63}$/.test(s.id)||domain(publicNewsUrl('https://'+s.domain))!==s.domain||!Number.isFinite(s.credibility)||s.credibility<0||s.credibility>100)throw new Error('تنظیم منبع خبر معتبر نیست.');}
  return {...config,sources,sensitiveTerms:source.sensitiveTerms,shellTitleTerms:source.shellTitleTerms,legacyFilters:source.legacyFilters,provenance:source.provenance};
}

export const newsRunPath=(id,root=ROOT)=>inside(path.join(root,'.local/news'),safeId(id));

export function createNewsRun({id,category,query='',lookback,limit,social},root=ROOT) {
  const settings=newsSettings(root),dest=newsRunPath(id,root);
  category=category||settings.defaults.category;
  if(!Object.hasOwn(settings.categories,category))throw new Error('دستهٔ خبری ناشناخته است.');
  const lookbackHours=Number(lookback??settings.defaults.lookbackHours),count=Number(limit??settings.defaults.limit);
  if(!Number.isFinite(lookbackHours)||lookbackHours<0.25||lookbackHours>168||!Number.isInteger(count)||count<1||count>50)throw new Error('بازهٔ جستجو باید ۱۵ دقیقه تا ۷ روز و تعداد ۱ تا ۵۰ باشد.');
  if(typeof query!=='string'||query.length>1000)throw new Error('موضوع جستجو بیش از حد بلند است.');
  if(fs.existsSync(dest))throw new Error('این جستجو وجود دارد؛ resume را اجرا کن.');
  fs.mkdirSync(dest,{recursive:true});
  const prompt=path.join(root,settings.briefPrompt);
  fs.copyFileSync(prompt,path.join(dest,'instructions.txt'),fs.constants.COPYFILE_EXCL);
  writeJson(path.join(dest,'settings.json'),settings);
  writeJson(path.join(dest,'run.json'),{schemaVersion:1,id,category,query,lookbackHours,limit:count,includeSocial:social===undefined?settings.defaults.includeSocial:!['false',false].includes(social),createdAt:new Date().toISOString(),phase:'planned',batches:[]});
  writeJson(path.join(dest,'items.json'),[]);
  fs.writeFileSync(path.join(dest,'REVIEW.md'),'# بازبینی خبریابی\n\nوضعیت: pending\n\nجستجو، خواندن منبع، زمان انتشار/رویداد، استقلال منابع و پوشش/سابقه باید با مدرک ثبت شوند.\n','utf8');
  return dest;
}

export function buildNewsPlan(id,root=ROOT) {
  const dest=newsRunPath(id,root),run=readJson(inside(dest,'run.json')),s=readJson(inside(dest,'settings.json'));
  const terms=run.category==='local'?s.localTerms:run.category==='khorasan_razavi'?s.regionalTerms:[];
  const base=[run.query,...terms].filter(Boolean).join(' ')||s.categories[run.category];
  const queries=[{purpose:'کشف اولیه با محدودیت زمانی ابزار وب',query:base,lookbackHours:run.lookbackHours}];
  if(run.category==='local')for(const term of terms)queries.push({purpose:'پوشش جداگانهٔ محل و تشخیص هم‌نامی',query:[run.query,term,'خراسان رضوی'].filter(Boolean).join(' ')});
  const wanted=s.sources.filter(source=>run.category==='all'?source.scope!=='golbahar':run.category==='local'?source.scope==='golbahar':run.category==='khorasan_razavi'?source.scope==='khorasan_razavi':source.scope==='national');
  if(!['google_trends','google_sports','khabarfarsi'].includes(run.category))for(const source of wanted)queries.push({purpose:'جستجو در منبع مشخص',query:`site:${source.domain} ${run.query||terms.join(' ')}`,sourceId:source.id});
  if(run.includeSocial)for(const host of s.socialDomains)queries.push({purpose:'پست عمومی؛ دسترسی و تاریخ باید واقعاً بررسی شوند',query:`site:${host} ${base}`});
  return {run,queries:queries.slice(0,s.queryLimit),publicFeedHints:s.publicFeeds,sourceCatalog:s.sources,
    instructions:fs.readFileSync(inside(dest,'instructions.txt'),'utf8'),
    execution:'عامل باید با ابزار وب واقعی همین جلسه جستجو و صفحات را باز کند؛ این فرمان شبکه یا مدل را اجرا نمی‌کند.',
    importContract:{executedQueries:[{query:'متن جستجو',tool:'نام ابزار واقعی',searchedAt:'ISO timestamp with timezone'}],items:[{
      title:'تیتر عین منبع',summary:'خلاصهٔ مستقل فارسی',url:'https://publisher.example.org/article',category:run.category,scope:'golbahar',source:'نام منبع',sourceId:'اختیاری از کاتالوگ',
      publishedAt:'ISO timestamp with timezone',publishedDateText:'تاریخ عین صفحه',eventStatus:'current|update|historical|unknown',eventDate:'YYYY-MM-DD if evidenced',eventReason:'مدرک تازگی رویداد',
      evidence:{url:'همان صفحهٔ بازشده',access:'full|partial|unavailable',excerpt:'شاهد کوتاه حداکثر ۳۰۰ نویسه',retrievedAt:'ISO timestamp with timezone',tool:'نام ابزار واقعی'},
      facts:['فقط واقعیت مستند همین منبع'],originalSourceUrl:'اختیاری؛ اصل خبر برای تشخیص بازنشر',
      saturation:{assessment:'unknown|low-observed-coverage|widely-covered',basis:'محدوده و مدرک پوشش مشاهده‌شده؛ نه تضمین نسوختگی'},
      potential:{score:0,reason:'ارزیابی تحریریه‌ای؛ نه پیش‌بینی قطعی بازدید'}
    }]}};
}

export function assessNewsItem(raw,run,s,{now}={}) {
  if(!raw||typeof raw!=='object'||typeof raw.title!=='string'||!raw.title.trim()||raw.title.length>1000)throw new Error('تیتر منبع لازم است.');
  const url=publicNewsUrl(raw.url),e=raw.evidence||{},issues=[];
  if(typeof e.tool!=='string'||!e.tool.trim()||!['full','partial','unavailable'].includes(e.access)||typeof e.excerpt!=='string'||e.excerpt.length>300)throw new Error('مدرک ابزار وب و شاهد کوتاه معتبر لازم است.');
  if(publicNewsUrl(e.url)!==url)throw new Error('مدرک باید مربوط به همان پیوند خبر باشد.');
  const at=asNow(now),retrieved=stamp(e.retrievedAt),published=stamp(raw.publishedAt);
  if(retrieved===null||retrieved>at+600000)throw new Error('زمان دریافت مدرک وب معتبر نیست.');
  if(retrieved<at-7*86400000)issues.push('retrieval-stale');
  const title=raw.title.trim(),text=normalized(title+' '+(raw.summary||'')),host=domain(url);
  const source=s.sources.find(x=>x.id===raw.sourceId);
  if(raw.sourceId&&!source)issues.push('unknown-source-id');
  if(source&&!matchesDomain(host,source.domain))issues.push('source-domain-mismatch');
  if(e.access!=='full'||!e.excerpt.trim())issues.push('source-not-fully-read');
  if(published===null)issues.push('publication-date-unverified');
  else if(published>at+s.maxFutureMinutes*60000)issues.push('future-publication');
  else if(at-published>run.lookbackHours*3600000)issues.push('outside-time-window');
  if(!['current','update','historical','unknown'].includes(raw.eventStatus))issues.push('event-date-unverified');
  else if(['historical','unknown'].includes(raw.eventStatus)||!String(raw.eventReason||'').trim())issues.push('event-date-unverified');
  if(s.legacyFilters.blacklistedDomains.some(d=>matchesDomain(host,d)))issues.push('blocked-domain');
  if(s.shellTitleTerms.some(t=>normalized(title)===normalized(t))||title.length<8||normalized(title)===normalized(source?.label))issues.push('not-an-article');
  const local=run.category==='local'||raw.category==='local';
  if(local&&s.legacyFilters.excludedLocations.some(t=>text.includes(normalized(t)))&&!(raw.localityVerified===true&&String(raw.localityReason||'').trim()))issues.push('ambiguous-locality');
  if(local&&!s.localTerms.some(t=>text.includes(normalized(t))))issues.push('locality-unverified');
  const advertisingSignals=s.legacyFilters.blacklistedKeywords.filter(t=>normalized(title).includes(normalized(t)));
  if(advertisingSignals.length&&!String(raw.editorialJustification||'').trim())issues.push('possible-advertisement');
  const sensitive=s.sensitiveTerms.some(t=>text.includes(normalized(t)));
  const ageHours=published===null?null:Math.max(0,(at-published)/3600000),w=s.weights;
  let priority=Math.min(w.credibilityCap,Math.floor((source?.credibility||70)/w.credibilityDivisor));
  priority+=ageHours===null?0:ageHours<=2?w.fresh2h:ageHours<=12?w.fresh12h:w.older;
  if(raw.trendKeyword||raw.traffic)priority+=w.trend;
  if(['فوری','هم اکنون','دقایقی پیش','امشب'].some(t=>text.includes(t)))priority+=w.urgent;
  if(raw.scope==='khorasan_razavi'||source?.scope==='khorasan_razavi')priority+=w.regional;
  if(sensitive)priority+=w.sensitive;
  const facts=raw.facts||[];
  if(!Array.isArray(facts)||facts.length>30||facts.some(f=>typeof f!=='string'||f.length>1000))throw new Error('بستهٔ واقعیت‌های خبر معتبر نیست.');
  const saturation=['unknown','low-observed-coverage','widely-covered'].includes(raw.saturation?.assessment)?raw.saturation:{assessment:'unknown',basis:''};
  if(saturation.assessment!=='unknown'&&!String(saturation.basis||'').trim())throw new Error('ارزیابی پوشش خبر به دلیل و محدودهٔ بررسی نیاز دارد.');
  if(raw.potential&&(!Number.isFinite(raw.potential.score)||raw.potential.score<0||raw.potential.score>100||!String(raw.potential.reason||'').trim()))throw new Error('پتانسیل خبر به امتیاز ۰ تا ۱۰۰ و دلیل نیاز دارد.');
  if(raw.eventDate&&(!/^\d{4}-\d{2}-\d{2}$/.test(raw.eventDate)||!Number.isFinite(Date.parse(raw.eventDate))||new Date(raw.eventDate).toISOString().slice(0,10)!==raw.eventDate))throw new Error('تاریخ رویداد معتبر نیست.');
  if(raw.eventDate&&raw.eventStatus==='current'&&at-Date.parse(raw.eventDate)>(run.lookbackHours+24)*3600000)issues.push('event-outside-time-window');
  if(raw.pageType&&raw.pageType!=='article'&&raw.pageType!=='post')issues.push('not-an-article');
  return {...raw,id:sha(url).slice(0,20),title,url,evidence:{...e,url},facts,originalSourceUrl:raw.originalSourceUrl?publicNewsUrl(raw.originalSourceUrl):null,
    scope:source?.scope==='golbahar'?'golbahar':raw.scope||source?.scope||'',
    publishedAt:published===null?null:new Date(published).toISOString(),source:raw.source||source?.label||host,
    priorityScore:Math.min(100,priority),priorityReason:'اعتبار ثبت‌شدهٔ منبع، تازگی، فوریت و ارتباط موضوعی؛ امتیاز تحریریه‌ای',
    needsReview:sensitive||issues.length>0,issues:[...new Set(issues)],eligible:issues.length===0,
    ageHours,saturation,potential:raw.potential||null,assessedAt:new Date(at).toISOString()};
}

export function importNewsEvidence(id,payload,root=ROOT,{now}={}) {
  const dest=newsRunPath(id,root),run=readJson(inside(dest,'run.json')),s=readJson(inside(dest,'settings.json'));
  if(!payload||!Array.isArray(payload.items)||payload.items.length>200||!Array.isArray(payload.executedQueries))throw new Error('ورودی باید items و executedQueries داشته باشد؛ حداکثر ۲۰۰ خبر.');
  const at=asNow(now);
  for(const q of payload.executedQueries)if(!q.query?.trim()||!q.tool?.trim()||stamp(q.searchedAt)===null||stamp(q.searchedAt)>at+600000)throw new Error('جستجوهای اجراشده باید زمان و نام ابزار واقعی داشته باشند.');
  const items=payload.items.map(raw=>assessNewsItem(raw,run,s,{now:new Date(at).toISOString()}));
  for(const check of payload.sourceChecks||[])if(!s.sources.some(source=>source.id===check.sourceId)||!['read','empty','failed','partial'].includes(check.status)||stamp(check.checkedAt)===null||stamp(check.checkedAt)>at+600000)throw new Error('وضعیت منبع و زمان بررسی معتبر نیست.');
  const batchId=crypto.randomUUID(),batch=`batches/${batchId}.json`;
  writeJson(inside(dest,batch),{...payload,importedAt:new Date(at).toISOString()});
  const old=readJson(inside(dest,'items.json')),map=new Map(old.map(i=>[i.id,i]));
  for(const item of items)map.set(item.id,{...item,batch});
  writeJson(inside(dest,'items.json'),[...map.values()]);
  run.batches.push({file:batch,sha256:sha(fs.readFileSync(inside(dest,batch))),itemCount:items.length});
  run.phase='review';writeJson(inside(dest,'run.json'),run);
  return {items:items.length,eligible:items.filter(i=>i.eligible).length,needsReview:items.filter(i=>!i.eligible).length,batch};
}

function ledger(root) {
  const file=inside(path.join(root,'.local/news'),'history.json');return fs.existsSync(file)?readJson(file):[];
}

export function newsDigest(id,root=ROOT,{now}={}) {
  const dest=newsRunPath(id,root),run=readJson(inside(dest,'run.json')),s=readJson(inside(dest,'settings.json')),history=ledger(root);
  const batches=run.batches.map(batch=>{
    const file=inside(dest,batch.file);
    if(sha(fs.readFileSync(file))!==batch.sha256)throw new Error('مدرک خبریابی پس از ثبت تغییر کرده است.');
    return readJson(file);
  });
  const originals=new Map();
  for(let n=0;n<batches.length;n++)for(const raw of batches[n].items)originals.set(sha(publicNewsUrl(raw.url)).slice(0,20),{raw,batch:run.batches[n].file});
  const items=[...originals.values()].map(({raw,batch})=>({...assessNewsItem(raw,run,s,{now}),batch}));
  const groups=new Map();
  for(const item of items) {
    const date=item.eventDate||item.publishedAt?.slice(0,10)||'undated';
    const key=normalized(item.title)+'|'+date+'|'+(item.scope||'');
    const previous=groups.get(key);
    if(previous) {
      if((item.eligible&&!previous.eligible)||item.eligible===previous.eligible&&item.priorityScore>previous.priorityScore)groups.set(key,{...item,related:[{...previous,related:undefined},...previous.related]});
      else previous.related.push(item);
    } else groups.set(key,{...item,related:[]});
  }
  const clustered=[...groups.values()].map(item=>{
    // Reprints of one original are one origin, even across many publisher domains.
    const origins=new Set([item,...item.related].map(i=>domain(i.originalSourceUrl||i.url)));
    const independent=new Set([item,...item.related].filter(i=>i.eligible&&i.independenceVerified===true&&String(i.independenceReason||'').trim()).map(i=>domain(i.originalSourceUrl||i.url)));
    const coverageScore=Math.min(s.weights.independentCoverageCap,Math.max(0,independent.size-1)*s.weights.independentCoverageEach);
    const prior=history.filter(h=>[item,...item.related].some(i=>i.url===h.url||normalized(i.title)===normalized(h.title)&&(i.eventDate||i.publishedAt?.slice(0,10))===h.eventDate));
    return {...item,priorityScore:Math.min(100,item.priorityScore+coverageScore),observedOriginDomains:[...origins],
      coverageMeaning:'پوشش مشاهده‌شده؛ استقلال و صحت محتوا باید جدا بررسی شوند',history:prior,
      previouslyUsed:prior.some(h=>h.action==='used'),noveltyGuarantee:false};
  }).sort((a,b)=>Number(b.eligible)-Number(a.eligible)||b.priorityScore-a.priorityScore||(b.potential?.score||0)-(a.potential?.score||0));
  const national=run.category==='all'?clustered.filter(i=>i.scope!=='golbahar'):clustered;
  return {runId:id,category:run.category,asOf:new Date(asNow(now)).toISOString(),phase:run.phase,
    items:national,shortlist:national.filter(i=>i.eligible&&!i.previouslyUsed).slice(0,run.limit),
    totalStored:items.length,executedQueries:batches.flatMap(b=>b.executedQueries),sourceHealth:s.sources.map(source=>({sourceId:source.id,domain:source.domain,
      evidenceCount:items.filter(i=>i.sourceId===source.id).length,
      lastCheck:batches.flatMap(b=>b.sourceChecks||[]).filter(c=>c.sourceId===source.id).sort((a,b)=>Date.parse(b.checkedAt)-Date.parse(a.checkedAt))[0]||null,
      status:items.some(i=>i.sourceId===source.id)?'evidence-imported':batches.some(b=>b.sourceChecks?.some(c=>c.sourceId===source.id))?'checked-see-lastCheck':'not-checked'})),
    historyScope:'این محیط محلی؛ سابقهٔ سایر ادمین‌ها بدون انتقال صریح در دسترس نیست',
    publication:false};
}

export function markNewsItem(id,itemId,action,{note=''}={},root=ROOT) {
  if(!['selected','used','dismissed','archived'].includes(action))throw new Error('وضعیت خبر نامعتبر است.');
  const digest=newsDigest(id,root);
  const item=digest.items.flatMap(i=>[i,...i.related]).find(i=>i.id===itemId);
  if(!item)throw new Error('خبر پیدا نشد.');
  const entries=ledger(root);entries.push({runId:id,itemId,url:item.url,title:item.title,eventDate:item.eventDate||item.publishedAt?.slice(0,10),action,note,at:new Date().toISOString()});
  writeJson(inside(path.join(root,'.local/news'),'history.json'),entries);return entries.at(-1);
}

export function newsToContent(id,itemId,{project,kind='text',brand='kalametaze',profile='channel',template='news_story'},root=ROOT) {
  if(!['text','image','slides','motion'].includes(kind))throw new Error('مقصد خبر متن، تصویر، اسلاید یا موشن است.');
  const digest=newsDigest(id,root),item=digest.items.find(i=>i.id===itemId||i.related.some(r=>r.id===itemId));
  const selected=item?.id===itemId?item:item?.related.find(r=>r.id===itemId);
  if(!selected||!selected.eligible)throw new Error('خبر به خواندن منبع و رفع ابهام زمان/مکان نیاز دارد؛ از نتیجهٔ ناقص سفارش قطعی نساز.');
  const evidence={runId:id,itemId,selectedAt:new Date().toISOString(),article:selected};
  const dest=createContentProject({id:safeId(project),kind,brand,profile,template},root);
  const spec=readJson(inside(dest,'spec.json'));
  const sourceText=[selected.title,selected.summary||'',...selected.facts,`منبع: ${selected.source}\n${selected.url}`].filter(Boolean).join('\n\n');
  if(kind==='text')spec.text=sourceText;
  else if(spec.request)Object.assign(spec.request.content,{title:selected.title,caption:selected.summary||'',source:selected.source});
  else if(spec.slides)Object.assign(spec.slides[0].content,{title:selected.title,caption:selected.summary||'',source:selected.source});
  writeJson(inside(dest,'analysis/news-source.json'),evidence);
  spec.discovery={runId:id,itemId,sourceUrl:selected.url,evidencePath:'analysis/news-source.json',evidenceSha256:sha(fs.readFileSync(inside(dest,'analysis/news-source.json')))};
  saveRevision(dest,'news-selection');writeJson(inside(dest,'spec.json'),spec);
  fs.appendFileSync(inside(dest,'BRIEF.md'),'\n\n## ورودی خبریابی\n\n'+sourceText+'\n\nاین متن بستهٔ منبع است؛ متن نریشن/طرح تأییدشده محسوب نمی‌شود.\n','utf8');
  markNewsItem(id,itemId,'selected',{note:`content-project:${project}`},root);
  return {project:dest,sourceUrl:selected.url,needsReview:selected.needsReview,publication:false};
}

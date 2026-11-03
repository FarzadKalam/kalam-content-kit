import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {ROOT,inside,safeId,readJson,writeJson} from './lib/paths.mjs';
import {createProject} from './projects.mjs';
import {compile} from './lib/studio-runtime.mjs';
import {defaultDataRequests,refreshData,dataIsFresh} from './content-data.mjs';

export const kinds=['text','image','slides','audio','video-prompts','motion'];
export const projectPath=(id,root=ROOT)=>inside(path.join(root,'.local/projects'),safeId(id));
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

export function imageRequest({id,brand,template='news_story',canvas,root=ROOT}) {
  const ui=readJson(path.join(root,'catalog/studio-ui.json'));
  const definition=ui.templates.find(t=>t.id===template);
  if(!definition)throw new Error('قالب ناشناخته است؛ content settings را ببین.');
  if(!['kalametaze','golbahar','chenaran'].includes(brand))throw new Error('قالب‌های Studio برای سه رسانهٔ خبری تعریف شده‌اند.');
  canvas=canvas||(template==='sticker'?'sticker_1024x1024':template==='news_post'||template==='poll_post'?'post_1080x1350':'story_1080x1920');
  const req={requestId:id,platform:'codex',brand,format:{family:definition.group==='non_news'?'fixed':definition.group,template,canvas,logoBehavior:'floating_profile',slideMode:'single',slideCount:1},
    content:{...ui.initialContent},image:{mode:'generate',engine:'',quality:'medium',aiWritesText:true,useAllUploadedImages:true},assets:{adminImageIds:[]},production:{kind:'image'}};
  if(template==='morning_local')req.content.morningCity=brand==='chenaran'?'chenaran':'golbahar';
  if(definition.group==='news'&&template!=='citizen_message')req.format.news={outputKind:'title_photo',layout:'top',photoFrame:'full',videoOverlay:false,videoFrame:'landscape',videoBackgroundBlur:false,siteLinkPlaceholder:false};
  if(template==='citizen_message')req.format.citizen={messageType:'text'};
  if(template==='morning_kalam')req.format.morningKalam={todayIndex:1,holidayIndexes:[]};
  if(template==='sticker'){req.format.logoBehavior='none';req.image.quality='auto';}
  if(definition.group==='studio') {
    req.image.mode='studio';
    req.format.studio={presenterIds:['kamran'],locationId:'newsroom',location:{mode:'catalog',id:'newsroom',assetIds:[],prompt:'',referenceInstructions:''},textMode:'monitor',text:'',
      monitor:{enabled:true,mode:'text',text:'',imageMode:'generate',imageCount:1,brief:''},titleSpace:{enabled:false,placement:'auto',textHint:''},
      headerEnabled:false,copySpacePlacement:'auto',expressions:{kamran:'آرام و مطمئن'},characterInstructions:{},speechBubbles:{},referenceSelection:{presenters:{kamran:{mode:'auto',assetIds:[]}},location:{mode:'auto',assetIds:[]}}};
  }
  return req;
}

export function createContentProject({id,brand='kalametaze',kind='image',template,profile='post',canvas,engine='hyperframes',mode='motion',width=1080,height=1920,spec:provided},root=ROOT) {
  if(!kinds.includes(kind))throw new Error('نوع سفارش معتبر نیست.');
  const dest=projectPath(id,root);
  const brandProfile=readJson(inside(path.join(root,'brands'),safeId(brand)+'.json'));
  if(fs.existsSync(dest))throw new Error('این سفارش وجود دارد؛ resume را اجرا کن.');
  let spec=provided?structuredClone(provided):{schemaVersion:1,kind,brand,references:[]};
  if(spec.kind!==kind||spec.brand!==brand)throw new Error('نوع و برند فایل تنظیمات با سفارش یکسان نیست.');
  if(!provided) {
    if(kind==='text')Object.assign(spec,{profile,text:'',additionalInstructions:'',channelJoinUrl:''});
    if(kind==='image')spec.request=imageRequest({id,brand,template,canvas,root});
    if(kind==='slides') {
      spec.slides=[imageRequest({id:id+'-01',brand,template:template||'news_post',canvas,root})];
    }
    if(kind==='audio')spec.audio={text:'',instructions:'روان، طبیعی، با تلفظ فارسی روشن و مکث‌های طبیعی بخوان.'};
    if(kind==='video-prompts')spec.video={projectId:crypto.randomUUID(),brand,canvas:'portrait',qualityMode:'precise',generationModel:'veo_3_1',directionMode:'news_bulletin',durationSeconds:8,resolution:'1080p',speechEnabled:true,presenterIds:['kamran'],
      location:{mode:'catalog',id:'newsroom'},monitor:{enabled:true,mode:'blank'},characterInstructions:{},referenceSelection:{presenters:{kamran:{mode:'auto',assetIds:[]}},location:{mode:'auto',assetIds:[]}},
      lines:[{presenterId:'kamran',text:'',shot:'medium',durationSeconds:8,description:'',dialogueStartSecond:0,dialogueEndSecond:8}],timeline:[],music:{mood:'neutral'},additionalInstructions:''};
    spec.dataRequests=defaultDataRequests(spec);
  }
  if(kind==='motion') {
    width=Number(width);height=Number(height);
    if(!provided)spec.motion={engine,mode,width,height,fps:30};
    createProject({id,brand,engine,mode,width,height},root);
  }
  else {
    for(const dir of ['assets/originals','analysis','renders','source','history'])fs.mkdirSync(path.join(dest,dir),{recursive:true});
    writeJson(path.join(dest,'brand.json'),brandProfile);
    fs.writeFileSync(path.join(dest,'BRIEF.md'),`# سفارش ${id}\n\nنوع: ${kind}\nبرند: ${brandProfile.name}\nهدف، ورودی، متن قطعی و محدودیت‌ها:\n`,'utf8');
    fs.writeFileSync(path.join(dest,'DECISIONS.md'),'# تصمیم‌ها و تأییدها\n\nتأیید واقعی متن و تغییرات با مرجع پیام ثبت شود.\n','utf8');
    fs.writeFileSync(path.join(dest,'REVIEW.md'),'# بازبینی\n\nوضعیت: pending\n\nمحتوا، هویت، فارسی، فایل خروجی و محدودیت ابزارها هنوز بررسی نشده‌اند.\n','utf8');
  }
  fs.mkdirSync(path.join(dest,'history'),{recursive:true});
  fs.cpSync(path.join(root,'config/studio'),path.join(dest,'settings'),{recursive:true});
  const state=kind==='motion'?readJson(path.join(dest,'project.json')):{};
  writeJson(path.join(dest,'project.json'),{...state,schemaVersion:2,id,kind,brand,phase:'brief',createdAt:new Date().toISOString(),
    source:readJson(path.join(root,'vendor/studio/sources.json')).commit,settingsStatus:readJson(path.join(dest,'settings/status.json')),
    capabilities:{image:{status:'unknown'},speech:{status:'unknown'}},approvals:[],artifacts:[]});
  // Stage approved shared references into each job; jobs never depend on a remote URL.
  const registry=path.join(root,'assets/studio/references/registry.json');
  if(fs.existsSync(registry))for(const ref of readJson(registry).assets) {
    const input=inside(path.dirname(registry),ref.path);
    const relative=path.join('assets/originals',safeId(ref.assetId)+path.extname(ref.path));
    const target=inside(dest,relative);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(input,target,fs.constants.COPYFILE_EXCL);
    spec.references??=[];spec.references.push({...ref,path:relative.replaceAll('\\','/'),sha256:hash(target)});
  }
  writeJson(path.join(dest,'spec.json'),spec);
  return dest;
}

export function saveRevision(dest,reason) {
  const history=inside(dest,'history');fs.mkdirSync(history,{recursive:true});
  const revision=fs.mkdtempSync(path.join(history,new Date().toISOString().replaceAll(':','-')+'-'));
  for(const name of ['spec.json','project.json'])if(fs.existsSync(path.join(dest,name)))fs.copyFileSync(path.join(dest,name),path.join(revision,name));
  writeJson(path.join(revision,'revision.json'),{reason,at:new Date().toISOString()});
  return revision;
}

export function attachReference(id,input,{kind='image',entityId='input',assetId=crypto.randomUUID(),scope='project'}={},root=ROOT) {
  const dest=projectPath(id,root),spec=readJson(inside(dest,'spec.json'));
  safeId(assetId);safeId(entityId);
  if(!['image','presenter','location','monitor','audio','footage'].includes(kind))throw new Error('نوع فایل مرجع معتبر نیست.');
  if(!['project','studio'].includes(scope))throw new Error('دامنهٔ فایل معتبر نیست.');
  const extension=path.extname(input).toLowerCase();
  if(!['.png','.jpg','.jpeg','.webp','.wav','.mp3','.m4a','.mp4','.mov','.ogg'].includes(extension))throw new Error('پسوند فایل پشتیبانی نمی‌شود.');
  const relative=path.join('assets/originals',assetId+extension),target=inside(dest,relative);
  fs.mkdirSync(path.dirname(target),{recursive:true});
  saveRevision(dest,'attach-reference');
  fs.copyFileSync(input,target,fs.constants.COPYFILE_EXCL);
  const ref={assetId,kind,entityId,scope,path:relative.replaceAll('\\','/'),sha256:hash(target),filename:path.basename(input)};
  spec.references??=[];spec.references.push(ref);
  writeJson(path.join(dest,'spec.json'),spec);
  return ref;
}

export function buildBrief(id,root=ROOT) {
  const dest=projectPath(id,root);
  const specPath=inside(dest,'spec.json');
  if(!dataIsFresh(dest)) {
    const data=refreshData(dest,{saveRevision});
    if(!data.canRender)throw new Error('داده‌های روز آماده نیستند؛ گزارش publicData را بخوان، منبع وب معتبر وارد کن یا دادهٔ دستیِ تأییدشده را انتخاب کن.');
  }
  const result=compile(specPath,inside(dest,'settings'));
  saveRevision(dest,'compile-brief');
  const outputs=inside(dest,'analysis');fs.mkdirSync(outputs,{recursive:true});
  const existing=fs.readdirSync(outputs).filter(n=>/^brief-\d+\.json$/.test(n));
  const version=existing.reduce((n,s)=>Math.max(n,Number(s.match(/\d+/)[0])),0)+1;
  const file=inside(outputs,`brief-${version}.json`);writeJson(file,result);
  if(result.kind==='video-prompts') {
    const bundle=inside(dest,`renders/video-prompts-${version}`);fs.mkdirSync(bundle,{recursive:true});
    for(const ref of result.references)fs.copyFileSync(inside(dest,ref.path),inside(bundle,ref.downloadName),fs.constants.COPYFILE_EXCL);
    writeJson(path.join(bundle,'package.json'),result);
    fs.writeFileSync(path.join(bundle,'prompts.txt'),result.segments.map(s=>`SEGMENT ${s.index+1}\n${s.prompt}\n\nNEGATIVE PROMPT:\n${s.negativePrompt}`).join('\n\n'),'utf8');
  }
  const state=readJson(path.join(dest,'project.json'));state.phase='brief-ready';state.latestBrief=path.relative(dest,file).replaceAll('\\','/');state.latestBriefSpecSha256=hash(specPath);writeJson(path.join(dest,'project.json'),state);
  return {file,result};
}

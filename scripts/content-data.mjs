import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {ROOT,inside,readJson,writeJson,safeId} from './lib/paths.mjs';
import {python} from './lib/studio-runtime.mjs';
const tool=path.join(ROOT,'scripts/public_data.py');
export function defaultDataRequests(spec) {
  const requests=spec.kind==='image'?[spec.request]:spec.kind==='slides'?spec.slides:[];
  return requests.flatMap((request,index)=>{
    const target=spec.kind==='slides'?index:'request',template=request.format?.template;
    if(template==='sport'&&request.content?.sportMode==='news')return [];
    const tasks={morning_local:['date','weather','prayer','occasions'],morning_kalam:['kalam-calendar','kalam-occasions'],market:['market-date','rates'],sport:['sports']}[template]||[];
    return tasks.map(task=>({id:`${task}-${target}`,task,target,date:'today',enabled:true,required:true}));
  });
}
function target(spec,binding) {
  if(binding.target==='context')return {content:spec.dataContext??={},format:{}};
  if(binding.target==='request'||binding.target===undefined) {
    if(spec.kind!=='image'||!spec.request)throw new Error('مقصد داده سفارش تصویری وجود ندارد.');
    return spec.request;
  }
  if(!Number.isInteger(binding.target)||!spec.slides?.[binding.target])throw new Error('مقصد دادهٔ اسلاید معتبر نیست.');
  return spec.slides[binding.target];
}
function applyResult(spec,binding,result,dest,{replace=false}={}) {
  safeId(binding.id);
  const relative=`analysis/data/${binding.id}-${crypto.randomUUID()}.json`;
  const file=inside(dest,relative);writeJson(file,result);
  const original=spec.dataEvidence?.[binding.id],applied={},preserved=[];
  if(result.status!=='ready'&&original?.applied) {
    const request=target(spec,binding);
    for(const [field,value] of Object.entries(original.applied))if(request.content?.[field]===value)request.content[field]='';
  }
  if(result.status==='ready') {
    const request=target(spec,binding);request.content??={};
    for(const [field,value] of Object.entries(result.values)) {
      const current=request.content[field];
      if(replace||current===undefined||current===null||current===''||current===original?.applied?.[field]||['sportEventIds','sportVisualAssets'].includes(field)&&current==='[]') {
        request.content[field]=value;applied[field]=value;
      } else preserved.push(field);
    }
    if(binding.task==='kalam-calendar'&&binding.target!=='context') {
      request.format??={};request.format.morningKalam??={};
      for(const field of ['todayIndex','holidayIndexes']) {
        const current=request.format.morningKalam[field],previous=original?.formatApplied?.[field];
        const initial=!original&&(field==='todayIndex'?current===1:!current?.length);
        if(replace||current===undefined||initial||JSON.stringify(current)===JSON.stringify(previous))request.format.morningKalam[field]=result.meta[field];
      }
    }
  }
  spec.dataEvidence??={};
  spec.dataEvidence[binding.id]={path:relative,sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),status:result.status,
    applied,preserved,formatApplied:binding.task==='kalam-calendar'&&result.status==='ready'?{todayIndex:result.meta.todayIndex,holidayIndexes:result.meta.holidayIndexes}:undefined};
  return {id:binding.id,task:binding.task,status:result.status,evidence:relative,applied:Object.keys(applied),preserved,error:result.error,warnings:result.warnings};
}
export function refreshData(dest,{force=false,replace=false,saveRevision,fetchResults}={}) {
  const specPath=inside(dest,'spec.json'),spec=readJson(specPath);
  if(!(spec.dataRequests||[]).some(b=>b.enabled!==false))return {results:[],canRender:true};
  const results=fetchResults?fetchResults(spec):JSON.parse(python([tool,'batch',specPath,...(force?['--force']:[])]));
  saveRevision?.(dest,'public-data-refresh');
  const report=results.map(item=>applyResult(spec,spec.dataRequests.find(b=>b.id===item.id),item.result,dest,{replace}));
  writeJson(specPath,spec);
  const failed=report.filter(r=>r.status!=='ready'&&spec.dataRequests.find(b=>b.id===r.id)?.required!==false);
  const state=readJson(inside(dest,'project.json'));state.phase=failed.length?'data-blocked':'brief';state.publicData={updatedAt:new Date().toISOString(),results:report};
  delete state.latestBrief;delete state.latestBriefSpecSha256;writeJson(path.join(dest,'project.json'),state);
  return {results:report,canRender:failed.length===0};
}
export function importWebData(dest,bindingId,evidenceFile,{replace=false,saveRevision}={}) {
  const specPath=inside(dest,'spec.json'),spec=readJson(specPath),binding=spec.dataRequests?.find(b=>b.id===bindingId);
  if(!binding||binding.enabled===false)throw new Error('درخواست دادهٔ فعال پیدا نشد.');
  const result=JSON.parse(python([tool,'review-web',specPath,'--binding',bindingId,'--evidence',evidenceFile]));
  saveRevision?.(dest,'public-data-web-evidence');const report=applyResult(spec,binding,result,dest,{replace});writeJson(specPath,spec);
  const state=readJson(path.join(dest,'project.json'));state.phase='brief';delete state.latestBrief;delete state.latestBriefSpecSha256;writeJson(path.join(dest,'project.json'),state);
  return report;
}
export function validateData(dest) {return JSON.parse(python([tool,'validate',inside(dest,'spec.json')]));}
export function dataIsFresh(dest) {
  try{validateData(dest);return true}catch{return false}
}

import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {ROOT,readJson,writeJson} from '../scripts/lib/paths.mjs';
import {registerImagePlan,approveImagePlan,imageApprovalStatus,assertImageApproved} from '../scripts/image-approval.mjs';

function fixture(t,kind='image',{legacy=false}={}) {
  const base=path.join(ROOT,'.cache/tests');fs.mkdirSync(base,{recursive:true});
  const root=fs.mkdtempSync(path.join(base,'image-approval-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const dest=path.join(root,'.local/projects/sample');fs.mkdirSync(path.join(dest,'assets'),{recursive:true});
  writeJson(path.join(dest,'project.json'),{id:'sample',...(legacy?{}:{kind}),brand:'kalametaze',engine:'hyperframes',mode:'motion',width:1080,height:1920,phase:'brief'});
  if(!legacy)writeJson(path.join(dest,'spec.json'),{kind,brand:'kalametaze',text:'متن تأییدشده'});
  writeJson(path.join(dest,'brand.json'),{name:'کلام تازه',color:'#fff'});
  // Real different image bytes; no generation or model/tool invocation is implied.
  fs.writeFileSync(path.join(dest,'assets/reference.svg'),'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="red"/></svg>');
  return {root,dest};
}
const proposal=(patch={})=>({mode:'generate',images:[{id:'cover',description:'کارت خبر با نمای شهر و تیتر تأییدشده',style:'روشن با تایپوگرافی برند',text:'متن تأییدشده',referencePaths:['assets/reference.svg']}],...patch});
const approve=(root,version=1)=>approveImagePlan('sample',{version,reference:'user-message:42',response:'شرح تصویر نسخهٔ '+version+' را تأیید می‌کنم.'},root);

test('image proposal needs separate real approval even when a prior request or storyboard was approved',t=>{
  const {root,dest}=fixture(t);
  writeJson(path.join(dest,'analysis/storyboard.json'),{approved:true});
  const project=readJson(path.join(dest,'project.json'));project.approvals=[{type:'image-request',approved:true}];writeJson(path.join(dest,'project.json'),project);
  assert.equal(imageApprovalStatus('sample',root).ready,false);
  const registered=registerImagePlan('sample',proposal(),root);
  assert.equal(registered.version,1);assert.equal(registered.count,1);
  assert.equal(registered.status,'awaiting-user-approval');
  assert.throws(()=>assertImageApproved('sample',root));
  for(const evidence of [{reference:'',response:'تأیید'},{reference:'user:1',response:' '}])assert.throws(()=>approveImagePlan('sample',{version:1,...evidence},root));
  assert.equal(approve(root).status,'approved');
  assert.equal(assertImageApproved('sample',root).plan.images[0].text,'متن تأییدشده');
  assert.throws(()=>approve(root)); // Immutable approval evidence.
});

test('each changed proposal gets a new immutable version and cannot reuse an older approval',t=>{
  const {root,dest}=fixture(t,'slides');
  registerImagePlan('sample',proposal(),root);approve(root);
  const second=proposal();second.images.push({...second.images[0],id:'second',description:'تصویر دوم با قاب دایره‌ای'});
  assert.equal(registerImagePlan('sample',second,root).version,2);
  assert.equal(imageApprovalStatus('sample',root).ready,false);
  assert.throws(()=>approve(root,1));assert.equal(approve(root,2).ready,true);
  const previous=readJson(path.join(dest,'analysis/image-plan-v1/plan.json'));assert.equal(previous.count,1);
  const changed=path.join(dest,'analysis/image-plan-v2/plan.json'),plan=readJson(changed);plan.images[0].description='چیدمان دیگر';writeJson(changed,plan);
  assert.equal(imageApprovalStatus('sample',root).ready,false);
});

test('changed spec, brand or actual reference bytes invalidate image approval',t=>{
  for(const target of ['spec.json','brand.json','assets/reference.svg']) {
    const {root,dest}=fixture(t);registerImagePlan('sample',proposal(),root);approve(root);
    if(target.endsWith('.svg')) {
      const file=path.join(dest,target);fs.writeFileSync(file,fs.readFileSync(file,'utf8').replace('fill="red"','fill="blue"'));
    } else fs.appendFileSync(path.join(dest,target),'\n');
    assert.equal(imageApprovalStatus('sample',root).ready,false,target);
    assert.throws(()=>assertImageApproved('sample',root));
  }
});

test('edit proposals require source references, precise description/style/text and local files',t=>{
  const {root}=fixture(t);
  const edit=proposal({mode:'edit'});assert.equal(registerImagePlan('sample',edit,root).count,1);
  for(const imagePatch of [{description:''},{style:''},{text:null},{referencePaths:[]},{referencePaths:['../../outside.png']},{referencePaths:['https://example.com/ref.png']},{referencePaths:['assets/missing.png']}]) {
    assert.throws(()=>registerImagePlan('sample',{mode:'edit',images:[{...edit.images[0],...imagePatch}]},root));
  }
  assert.throws(()=>registerImagePlan('sample',{mode:'generate',images:[]},root));
  assert.throws(()=>registerImagePlan('sample',{mode:'generate',images:[edit.images[0],edit.images[0]]},root));
});

test('legacy motion production fields are frozen while review metadata can progress',t=>{
  const {root,dest}=fixture(t,'motion',{legacy:true});
  assert.equal(registerImagePlan('sample',proposal(),root).specSource,'project-production-fields');approve(root);
  const file=path.join(dest,'project.json'),project=readJson(file);project.phase='assets';project.approvals=[{type:'storyboard'}];writeJson(file,project);
  assert.equal(assertImageApproved('sample',root).ready,true);
  project.width=1920;writeJson(file,project);assert.equal(imageApprovalStatus('sample',root).ready,false);
});

test('wrong order kinds, corrupt manifests, replaced approvals and stale indexes fail closed',t=>{
  const textOrder=fixture(t,'text');assert.throws(()=>registerImagePlan('sample',proposal(),textOrder.root));
  for(const target of ['manifest','approval','index']) {
    const {root,dest}=fixture(t);registerImagePlan('sample',proposal(),root);approve(root);
    if(target==='manifest')fs.appendFileSync(path.join(dest,'analysis/image-plan-v1/manifest.json'),'\n');
    if(target==='approval') {const file=path.join(dest,'analysis/image-plan-v1/approval.json'),value=readJson(file);value.specSha256='wrong';writeJson(file,value);}
    if(target==='index') {registerImagePlan('sample',proposal(),root);const file=path.join(dest,'analysis/image-approval.json'),value=readJson(file);value.version=1;writeJson(file,value);}
    assert.equal(imageApprovalStatus('sample',root).ready,false,target);
  }
});

import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import sharp from 'sharp';
import {ROOT,readJson,writeJson} from '../scripts/lib/paths.mjs';
import {registerStoryboard,approveStoryboard,checkProduction,assertProductionReadyForPath} from '../scripts/storyboard.mjs';

async function fixture(t) {
  const base=path.join(ROOT,'.cache/tests');fs.mkdirSync(base,{recursive:true});
  const root=fs.mkdtempSync(path.join(base,'storyboard-')),dest=path.join(root,'.local/projects/job');
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  for(const dir of ['analysis','assets','source','renders'])fs.mkdirSync(path.join(dest,dir),{recursive:true});
  writeJson(path.join(dest,'project.json'),{id:'job',kind:'motion',mode:'motion',width:1080,height:1920,fps:30,phase:'brief'});
  writeJson(path.join(dest,'spec.json'),{kind:'motion',brand:'test'});
  writeJson(path.join(dest,'brand.json'),{name:'برند ساختگی آزمون'});
  writeJson(path.join(dest,'sound-plan.json'),{events:[]});
  fs.writeFileSync(path.join(dest,'script.md'),'متن تأییدشدهٔ ساختگی آزمون','utf8');
  fs.writeFileSync(path.join(dest,'source/index.html'),'<p>متن تأییدشدهٔ ساختگی آزمون</p>','utf8');
  fs.writeFileSync(path.join(dest,'assets/photo.dat'),'test-media');
  await sharp({create:{width:240,height:426,channels:3,background:'#f4f2ee'}}).png().toFile(path.join(dest,'analysis/frame.png'));
  const plan={scenes:[{id:'intro',time:{start:0,end:3},image:'analysis/frame.png',onScreenText:'متن آزمون',narrationPhrase:''}],
    copy:{file:'script.md',approvalReference:'user:test-script'},media:[{file:'assets/photo.dat',usage:'fixture'}],narration:{mode:'none'},music:{mode:'none'}};
  return {root,dest,plan};
}
const approval={version:1,reference:'user:test-storyboard',response:'همین استوری‌بورد تأیید است',presentedReference:'tool:test-images-shown'};

test('real video orders cannot render without visual approval; examples remain exempt',async t=>{
  const {root,dest,plan}=await fixture(t);
  assert.equal(checkProduction('job',root).ready,false);
  assert.throws(()=>assertProductionReadyForPath(path.join(dest,'source/index.html'),root),/مسدود/);
  assert.equal(assertProductionReadyForPath('.local/examples/demo/index.html',root).exempt,true);
  assert.throws(()=>assertProductionReadyForPath('.local/projects/no-such/source.html',root));
  const result=await registerStoryboard('job',plan,root);
  assert.equal(result.version,1);assert.equal(result.contactSheets.length,1);
  assert.equal((await sharp(path.join(dest,result.contactSheets[0])).metadata()).format,'png');
  assert.equal(checkProduction('job',root).ready,false);
  assert.equal((await approveStoryboard('job',approval,root)).ready,true);
  assert.equal(assertProductionReadyForPath(path.join(dest,'source/index.html'),root).ready,true);
});

test('approval binds exact script, source, assets, spec, brand and sound timing',async t=>{
  const {root,dest,plan}=await fixture(t);
  for(const relative of ['script.md','source/index.html','assets/photo.dat','spec.json','brand.json','sound-plan.json']) {
    const version=(await registerStoryboard('job',plan,root)).version;
    await approveStoryboard('job',{...approval,version},root);
    const target=path.join(dest,relative),original=fs.readFileSync(target);
    fs.appendFileSync(target,' ');
    assert.equal(checkProduction('job',root).ready,false,relative);
    fs.writeFileSync(target,original);
    assert.equal(checkProduction('job',root).ready,true,relative+' restored');
  }
});

test('frame, contact sheet, manifest and plan tampering are detected even inside analysis',async t=>{
  const {root,dest,plan}=await fixture(t),registered=await registerStoryboard('job',plan,root);
  await approveStoryboard('job',approval,root);
  for(const relative of ['analysis/frame.png',registered.contactSheets[0],registered.manifestPath,'analysis/storyboard-v1/plan.json']) {
    const file=path.join(dest,relative),original=fs.readFileSync(file);
    fs.appendFileSync(file,'tamper');assert.equal(checkProduction('job',root).ready,false,relative);
    fs.writeFileSync(file,original);assert.equal(checkProduction('job',root).ready,true);
  }
});

test('new storyboard versions invalidate old approval and cannot be replaced',async t=>{
  const {root,dest,plan}=await fixture(t);
  const first=await registerStoryboard('job',plan,root);await approveStoryboard('job',approval,root);
  const original=fs.readFileSync(path.join(dest,first.manifestPath));
  const second=await registerStoryboard('job',plan,root);
  assert.equal(second.version,2);assert.equal(checkProduction('job',root).ready,false);
  await assert.rejects(()=>approveStoryboard('job',approval,root),/نسخه/);
  assert.equal((await approveStoryboard('job',{...approval,version:2},root)).ready,true);
  assert.deepEqual(fs.readFileSync(path.join(dest,first.manifestPath)),original);
  await assert.rejects(()=>approveStoryboard('job',{...approval,version:2},root),/EEXIST/);
});

test('phase and review bookkeeping do not invalidate approval; production dimensions do',async t=>{
  const {root,dest,plan}=await fixture(t);await registerStoryboard('job',plan,root);await approveStoryboard('job',approval,root);
  const file=path.join(dest,'project.json'),state=readJson(file);state.phase='rendering';state.updatedAt=new Date().toISOString();writeJson(file,state);
  fs.writeFileSync(path.join(dest,'REVIEW.md'),'بازبینی ثبت شد');fs.writeFileSync(path.join(dest,'DECISIONS.md'),'تأیید تصویری ثبت شد');
  fs.writeFileSync(path.join(dest,'renders/preview.mp4'),'preview');
  assert.equal(checkProduction('job',root).ready,true);
  state.width=720;writeJson(file,state);assert.equal(checkProduction('job',root).ready,false);
});

test('narration and external music prompt cannot masquerade as available final audio',async t=>{
  const {root,dest,plan}=await fixture(t);
  plan.narration={mode:'file',file:'assets/narration.wav'};
  fs.writeFileSync(path.join(dest,'renders/music-prompt.txt'),'Instrumental background score only.');
  plan.music={mode:'external-prompt',promptFile:'renders/music-prompt.txt'};
  await registerStoryboard('job',plan,root);
  const report=await approveStoryboard('job',approval,root);
  assert.equal(report.ready,false);assert.ok(report.reasons.some(reason=>reason.includes('نریشن')));assert.ok(report.reasons.some(reason=>reason.includes('موسیقی')));
  assert.throws(()=>assertProductionReadyForPath(dest,root));
  // A newly supplied file changes the production inputs; visual approval cannot silently carry over.
  fs.writeFileSync(path.join(dest,'assets/narration.wav'),'received fixture audio');
  assert.equal(checkProduction('job',root).ready,false);
  plan.music={mode:'none'};
  const next=await registerStoryboard('job',plan,root);
  assert.equal((await approveStoryboard('job',{...approval,version:next.version},root)).ready,true);
});

test('approval requires nonblank response, user reference and presentation evidence',async t=>{
  const {root,plan}=await fixture(t);await registerStoryboard('job',plan,root);
  for(const field of ['reference','response','presentedReference'])await assert.rejects(()=>approveStoryboard('job',{...approval,[field]:'   '},root));
  assert.equal(checkProduction('job',root).ready,false);
  assert.equal((await approveStoryboard('job',approval,root)).ready,true);
});

test('storyboards reject outside paths, symlinks, fake frames and impossible times',async t=>{
  const {root,dest,plan}=await fixture(t);
  for(const image of ['../outside.png','https://example.com/frame.png',path.join(dest,'analysis/frame.png')]) {
    const bad=structuredClone(plan);bad.scenes[0].image=image;await assert.rejects(()=>registerStoryboard('job',bad,root));
  }
  const badTime=structuredClone(plan);badTime.scenes[0].time={start:3,end:1};await assert.rejects(()=>registerStoryboard('job',badTime,root));
  fs.writeFileSync(path.join(dest,'analysis/fake.png'),'not a real image');
  const fake=structuredClone(plan);fake.scenes[0].image='analysis/fake.png';await assert.rejects(()=>registerStoryboard('job',fake,root));
  const linked=path.join(dest,'assets/linked');
  try {fs.symlinkSync(path.join(dest,'source'),linked,process.platform==='win32'?'junction':'dir');}
  catch(error) {if(error.code==='EPERM'){t.diagnostic('Symlink creation unavailable; path cases still checked.');return;}throw error;}
  await assert.rejects(()=>registerStoryboard('job',plan,root),/لینک/);
  const alias=path.join(root,'alias-to-real-order');
  fs.symlinkSync(dest,alias,process.platform==='win32'?'junction':'dir');
  assert.throws(()=>assertProductionReadyForPath(path.join(alias,'source/index.html'),root),/مسدود/);
});

test('contact sheets split after twelve scenes and explicit silent plan is supported',async t=>{
  const {root,dest,plan}=await fixture(t);
  plan.scenes=Array.from({length:13},(_,i)=>({...plan.scenes[0],id:'scene-'+i,time:i}));
  plan.narration={mode:'silent'};
  const registered=await registerStoryboard('job',plan,root);assert.equal(registered.contactSheets.length,2);
  const first=await sharp(path.join(dest,registered.contactSheets[0])).metadata();assert.equal(first.height,1344);
  assert.equal((await approveStoryboard('job',approval,root)).ready,true);
  plan.music={mode:'file',file:'assets/music.wav'};await assert.rejects(()=>registerStoryboard('job',plan,root),/بی‌صدا/);
});

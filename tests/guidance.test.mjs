import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {ROOT,readJson,writeJson} from '../scripts/lib/paths.mjs';
import {contentGuidance} from '../scripts/content-guidance.mjs';
import {createContentProject,buildBrief} from '../scripts/content-projects.mjs';

function order(t,kind,options={}) {
  const id=`test-guide-${kind}-${process.pid}-${Math.random().toString(16).slice(2)}`;
  const dest=createContentProject({id,kind,brand:'golbahar',...options});
  t.after(()=>fs.rmSync(dest,{recursive:true,force:true}));
  return {id,dest};
}

test('guidance exposes every source capability while focusing on the active forms',()=>{
  const rules=readJson(path.join(ROOT,'catalog/studio.json'));
  const spec={kind:'slides',slides:[{format:{template:'morning_local'}},{format:{template:'news_story'}}]};
  const before=structuredClone(spec),guide=contentGuidance({spec});
  assert.deepEqual(guide.routes.image.templates.map(t=>t.id).sort(),Object.keys(rules.imageTemplates).sort());
  assert.deepEqual(guide.routes.text.profiles.map(p=>p.id).sort(),Object.keys(rules.editorialProfiles).sort());
  assert.deepEqual(guide.activeForms.templates.map(t=>t.id),['morning_local','news_story']);
  assert.deepEqual(spec,before);
  assert.equal(guide.routes.videoPrompts.videoGeneration,false);
  assert.equal(guide.routes.publicData.newsDiscovery,false);
  assert.equal(guide.routes.newsDiscovery.skill,'.agents/skills/kalam-news/SKILL.md');
  assert.throws(()=>contentGuidance({spec:{profile:'invented-profile'}}));
});

test('motion narration travels with the order and brief without authorizing audio',t=>{
  const {id,dest}=order(t,'text',{purpose:'motion',profile:'scenario'});
  const file=path.join(dest,'spec.json'),spec=readJson(file);
  spec.text='متن خبر آموزشی؛ عدد تأییدشده ۱۲۳ است.';writeJson(file,spec);
  spec.music={mode:'external-prompt',intent:'زمینهٔ آرام برای همان خبر'};writeJson(file,spec);
  const policyFile=path.join(dest,'settings/assistant-guidance.json'),policy=readJson(policyFile);
  policy.snapshotEvidence='order-specific';writeJson(policyFile,policy);
  const state=readJson(path.join(dest,'project.json'));
  state.capabilities.speech={status:'unavailable',evidence:'test session has no speech tool'};
  writeJson(path.join(dest,'project.json'),state);
  const brief=buildBrief(id).result;
  assert.ok(brief.prompt.includes('۱۲۳'));
  assert.equal(brief.assistantGuidance.context.motionNarration,true);
  assert.equal(brief.assistantGuidance.policy.snapshotEvidence,'order-specific');
  assert.equal(brief.assistantGuidance.context.capabilities.speech.status,'unavailable');
  assert.deepEqual(brief.assistantGuidance.context.music,spec.music);
  assert.equal(brief.assistantGuidance.routes.music.instructionsSource,'order-settings');
  assert.ok(fs.existsSync(brief.assistantGuidance.routes.music.promptInstructions));
  assert.equal(brief.assistantGuidance.brandTypography.roles.handwrittenAccent.family,'Parsa');
  assert.equal(brief.assistantGuidance.pairedDeliverables.outputs.length,2);
  assert.deepEqual(readJson(path.join(dest,'project.json')).approvals,[]);
  assert.deepEqual(readJson(file),spec);
});

test('a motion order alone does not imply a request for new narration',()=>{
  const guide=contentGuidance({spec:{kind:'motion'}});
  assert.equal(guide.context.motionNarration,false);
  assert.equal(guide.pairedDeliverables,null);
});

test('guide works before copy is written and does not change project files',t=>{
  const {id,dest}=order(t,'audio',{purpose:'motion'});
  const before=Object.fromEntries(['spec.json','project.json','DECISIONS.md'].map(name=>[name,fs.readFileSync(path.join(dest,name),'utf8')]));
  const run=spawnSync(process.execPath,['scripts/content.mjs','guide',id],{cwd:ROOT,encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);
  const guide=JSON.parse(run.stdout);
  assert.equal(guide.context.purpose,'motion');
  assert.ok(guide.pairedDeliverables);
  for(const [name,bytes] of Object.entries(before))assert.equal(fs.readFileSync(path.join(dest,name),'utf8'),bytes);
  assert.deepEqual(fs.readdirSync(path.join(dest,'history')),[]);
});

test('bundled references actually compile a Studio image and continuous video package',t=>{
  const image=order(t,'image',{template:'studio'});
  const shot=buildBrief(image.id).result.slides[0];
  assert.ok(shot.references.some(r=>r.kind==='presenter'&&r.entityId==='kamran'));
  assert.ok(shot.references.some(r=>r.kind==='location'&&r.entityId==='newsroom'));
  assert.ok(shot.references.every(r=>fs.existsSync(path.join(image.dest,r.path))));
  const video=order(t,'video-prompts');
  const file=path.join(video.dest,'spec.json'),spec=readJson(file);
  spec.video.lines[0].text='متن قطعی سکانس نخست';
  spec.video.lines.push({...spec.video.lines[0],text:'متن قطعی سکانس دوم'});
  writeJson(file,spec);
  const result=buildBrief(video.id).result;
  const bundle=path.join(video.dest,'renders/video-prompts-1');
  assert.equal(result.segments.length,2);
  assert.equal(result.execution.videoGeneration,false);
  assert.equal(result.segments[1].continuityAssetRequired,true);
  for(const segment of result.segments)for(const filename of segment.referenceFiles) {
    assert.ok(segment.prompt.includes(filename));
    assert.ok(fs.existsSync(path.join(bundle,filename)));
  }
});

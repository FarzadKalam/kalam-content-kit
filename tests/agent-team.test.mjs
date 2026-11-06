import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {ROOT,readJson,writeJson} from '../scripts/lib/paths.mjs';
import {freezeTeam,teamGuide,createHandoff} from '../scripts/agent-team.mjs';

function fixture(t) {
  const base=path.join(ROOT,'.cache/tests');fs.mkdirSync(base,{recursive:true});
  const root=fs.mkdtempSync(path.join(base,'team-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const team=readJson(path.join(ROOT,'config/agents.json'));
  for(const rel of ['config/agents.json',...Object.values(team.roles).flatMap(role=>[role.config,role.skill])]) {
    fs.mkdirSync(path.dirname(path.join(root,rel)),{recursive:true});fs.copyFileSync(path.join(ROOT,rel),path.join(root,rel));
  }
  const dest=path.join(root,'.local/projects/job');fs.mkdirSync(dest,{recursive:true});
  writeJson(path.join(dest,'project.json'),{id:'job',kind:'motion',brand:'golbahar'});
  writeJson(path.join(dest,'spec.json'),{kind:'motion',brand:'golbahar',purpose:'motion'});
  fs.writeFileSync(path.join(dest,'DECISIONS.md'),'کاربر قبلاً روایت آرام و برند گلبهار را انتخاب کرده است.','utf8');
  return {root,dest};
}

test('team routes only relevant specialists and preserves frozen role instructions',t=>{
  const {root,dest}=fixture(t);freezeTeam(dest,root);
  assert.deepEqual(teamGuide({id:'job',root}).primaryRoles,['kalam_motion_editor']);
  assert.deepEqual(teamGuide({kind:'news',root}).primaryRoles,['kalam_news_researcher']);
  const before=readJson(path.join(dest,'team.json'));
  const shared=readJson(path.join(root,'config/agents.json'));shared.roles.kalam_writer.label='نسخهٔ تازه';writeJson(path.join(root,'config/agents.json'),shared);
  fs.appendFileSync(path.join(root,shared.roles.kalam_writer.config),'\n# changed shared file');
  freezeTeam(dest,root);assert.deepEqual(readJson(path.join(dest,'team.json')),before);
  assert.notEqual(teamGuide({id:'job',root}).roles.kalam_writer.label,'نسخهٔ تازه');
});

test('handoffs isolate output paths and carry real choices without claiming agent execution',t=>{
  const {root,dest}=fixture(t);
  const first=createHandoff('job',{role:'kalam_writer',task:'نریشن و سناریو را با انتخاب قبلی آماده کن'},root);
  const second=createHandoff('job',{role:'kalam_writer',task:'بازبینی نهایی همان متن'},root);
  assert.notEqual(first.outputDirectory,second.outputDirectory);
  const packet=readJson(first.file);
  assert.ok(packet.memory['DECISIONS.md'].includes('روایت آرام'));
  assert.equal(packet.spec.brand,'golbahar');assert.match(packet.execution,/not-started/);
  assert.match(packet.definition.instructions,/kalam-writer/);
  assert.ok(fs.existsSync(first.outputDirectory));
  assert.deepEqual(readJson(path.join(dest,'project.json')),{id:'job',kind:'motion',brand:'golbahar'});
  assert.throws(()=>createHandoff('job',{role:'../../outside',task:'invalid'},root));
  assert.throws(()=>createHandoff('job',{role:'kalam_writer',task:''},root));
});

test('both renderer wrappers stop actual orders before launching a render without storyboard approval',t=>{
  const id='test-render-approval-'+process.pid,dest=path.join(ROOT,'.local/projects',id);
  fs.mkdirSync(dest,{recursive:true});writeJson(path.join(dest,'project.json'),{id,engine:'hyperframes',mode:'motion'});
  t.after(()=>fs.rmSync(dest,{recursive:true,force:true}));
  for(const argv of [['scripts/kit.mjs','hf','render',dest],['scripts/remotion.mjs','render',path.join(dest,'src/index.jsx'),'Main',path.join(dest,'renders/final.mp4')]]) {
    const result=spawnSync(process.execPath,argv,{cwd:ROOT,encoding:'utf8'});
    assert.equal(result.status,1);assert.match(result.stderr,/رندر نهایی مسدود/);
  }
});

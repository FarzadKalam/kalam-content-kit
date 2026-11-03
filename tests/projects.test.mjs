import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {ROOT,safeId,inside} from '../scripts/lib/paths.mjs';
import {createProject} from '../scripts/projects.mjs';
function fixture(){
  const base=path.join(ROOT,'.cache/tests');fs.mkdirSync(base,{recursive:true});
  const p=fs.mkdtempSync(path.join(base,'project-'));
  for(const d of ['brands','assets/fonts','assets/sfx','node_modules/gsap/dist'])fs.mkdirSync(path.join(p,d),{recursive:true});
  fs.writeFileSync(path.join(p,'brands/test.json'),JSON.stringify({id:'test',name:'آزمایش',status:'ready'}));
  fs.writeFileSync(path.join(p,'assets/fonts/font.txt'),'font');fs.writeFileSync(path.join(p,'node_modules/gsap/dist/gsap.min.js'),'// fixture');return p;
}
test('project IDs cannot escape the local workspace',()=>{
  for(const id of ['../escape','a/b','a\\b','C:bad','a..b',''])assert.throws(()=>safeId(id));
  assert.throws(()=>inside(ROOT,'../outside'));assert.equal(safeId('news-01'),'news-01');
});
test('new job preserves original files, Unicode and refuses overwriting an existing job',()=>{
  const root=fixture(), original=path.join(root,'original.mp4');fs.writeFileSync(original,'unchanged');
  const p=createProject({id:'job',brand:'test',mode:'presenter'},root);
  assert.equal(fs.readFileSync(original,'utf8'),'unchanged');
  assert.ok(fs.readFileSync(path.join(p,'BRIEF.md'),'utf8').includes('آزمایش'));
  const state=JSON.parse(fs.readFileSync(path.join(p,'project.json'),'utf8'));
  assert.equal(state.audio.scriptApproval,null);assert.equal(state.audio.mode,'undecided');
  assert.equal(state.width,1080);assert.equal(state.height,1920);
  const sound=JSON.parse(fs.readFileSync(path.join(p,'sound-plan.json'),'utf8'));
  assert.equal(sound.fps,state.fps);assert.equal(sound.review.listened,false);assert.deepEqual(sound.events,[]);
  const visual=JSON.parse(fs.readFileSync(path.join(p,'visual-plan.json'),'utf8'));
  assert.deepEqual(visual.assets,[]);assert.equal(visual.review.status,'pending');
  assert.throws(()=>createProject({id:'job',brand:'test'},root));
  assert.throws(()=>createProject({id:'bad',brand:'test',mode:'invalid'},root));
});
test('Remotion job stages public assets separately and never inherits another customer identity',()=>{
  const root=fixture(),p=createProject({id:'ad',brand:'test',engine:'remotion'},root);
  assert.ok(fs.existsSync(path.join(p,'public/assets/fonts/font.txt')));
  assert.ok(!fs.existsSync(path.join(p,'assets/brand')));
});
test('a junction cannot redirect a project write outside its workspace',()=>{
  const root=fixture(), outside=fixture();fs.mkdirSync(path.join(root,'.local'),{recursive:true});
  fs.symlinkSync(outside,path.join(root,'.local/projects'),process.platform==='win32'?'junction':'dir');
  assert.throws(()=>createProject({id:'job',brand:'test'},root));
  assert.ok(!fs.existsSync(path.join(outside,'job')));
});
test('CLI home caches stay on the workspace drive without changing the user profile',()=>{
  const home=path.join(ROOT,'.cache/runtime-home-test');
  const value=execFileSync(process.execPath,['--require',path.join(ROOT,'scripts/runtime-home.cjs'),'--input-type=module','-e',"import {homedir} from 'node:os'; console.log(homedir());"],{env:{...process.env,KALAM_RUNTIME_HOME:home},encoding:'utf8'}).trim();
  assert.equal(value,path.resolve(home));
});

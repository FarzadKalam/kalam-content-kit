import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {ROOT,inside,safeId,readJson,writeJson} from './lib/paths.mjs';

export function freezeTeam(dest,root=ROOT) {
  const source=path.join(root,'config/agents.json'),target=inside(dest,'team.json');
  if(fs.existsSync(target))return readJson(target);
  if(!fs.existsSync(source))return null;
  const team=readJson(source);
  for(const role of Object.values(team.roles)) {
    role.instructions=fs.readFileSync(inside(root,role.config),'utf8');
    role.skillInstructions=fs.readFileSync(inside(root,role.skill),'utf8');
  }
  writeJson(target,team);return team;
}

export function teamGuide({id,kind,root=ROOT}={}) {
  let dest,source,spec;
  if(id) {
    dest=inside(path.join(root,'.local/projects'),safeId(id));
    const file=inside(dest,'spec.json');spec=fs.existsSync(file)?readJson(file):readJson(inside(dest,'project.json'));
    source=inside(dest,'team.json');
  }
  source=source&&fs.existsSync(source)?source:path.join(root,'config/agents.json');
  if(!fs.existsSync(source))return {status:'not-configured',roles:{},execution:'no-agent-started'};
  const team=readJson(source),requested=kind||spec?.kind||'all';
  if(requested!=='all'&&!team.routes[requested])throw new Error('مسیر تیم ناشناخته است.');
  return {...team,source,primaryRoles:team.routes[requested]||[],requested,
    execution:'guidance-only; coordinator-must-use-real-subagent-tools',
    handoff:id?`content handoff ${id} --role ROLE --task TASK`:null};
}

export function createHandoff(id,{role,task}={},root=ROOT) {
  const dest=inside(path.join(root,'.local/projects'),safeId(id));
  if(!fs.existsSync(inside(dest,'project.json')))throw new Error('سفارش برای واگذاری پیدا نشد.');
  if(typeof task!=='string'||!task.trim()||task.length>12000)throw new Error('وظیفهٔ روشن و مشخص لازم است.');
  const team=freezeTeam(dest,root);
  if(!team||!Object.hasOwn(team.roles,role))throw new Error('نقش ناشناخته است.');
  const definition=team.roles[role],assignmentId=crypto.randomUUID();
  const relative=`analysis/agents/${role}/${assignmentId}`,folder=inside(dest,relative);
  fs.mkdirSync(inside(folder,'outputs'),{recursive:true});
  const optional=name=>fs.existsSync(inside(dest,name))?fs.readFileSync(inside(dest,name),'utf8'):null;
  const packet={schemaVersion:1,id,assignmentId,role,task,createdAt:new Date().toISOString(),definition,
    spec:fs.existsSync(inside(dest,'spec.json'))?readJson(inside(dest,'spec.json')):null,
    project:readJson(inside(dest,'project.json')),
    memory:Object.fromEntries(['BRIEF.md','DECISIONS.md','REVIEW.md'].map(file=>[file,optional(file)])),
    settingsDirectory:fs.existsSync(inside(dest,'settings'))?'settings':null,
    ownedOutputDirectory:relative+'/outputs',
    sharedWrites:'coordinator-only: spec.json, project.json, DECISIONS.md, approvals',
    returnContract:{status:'done|needs-user-input|blocked',required:['files','evidence','preservedChoices','uncertainties','nextStep']},
    execution:'not-started; use-native-subagent-tool-with-this-role-and-packet'};
  const file=inside(folder,'handoff.json');writeJson(file,packet);
  return {file,outputDirectory:inside(folder,'outputs'),role,execution:packet.execution};
}

import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {ROOT,readJson,localEnv,browser} from './lib/paths.mjs';
const [command,entry,...rest]=process.argv.slice(2);
try {
  if(!['studio','render','still','compositions'].includes(command)||!entry)throw new Error('remotion.mjs studio|render|still|compositions entry [composition] [output]');
  const chrome=browser();if(!chrome)throw new Error('KALAM_BROWSER_PATH را به مرورگر موجود تنظیم کن.');
  const engine=path.join(ROOT,'engines/remotion'); const manifest=readJson(path.join(engine,'node_modules/@remotion/cli/package.json'));
  const bin=typeof manifest.bin==='string'?manifest.bin:Object.values(manifest.bin)[0];
  const input=path.resolve(entry);
  const adjusted=rest.map((v,i)=>i===1&&['render','still'].includes(command)&&!v.startsWith('--')?path.resolve(v):v);
  const project=path.dirname(path.dirname(input)); // project/src/index.jsx
  const outIndex=['render','still'].includes(command)?1:-1;
  if(outIndex>=0&&rest[outIndex]&&!rest[outIndex].startsWith('--')&&fs.existsSync(path.resolve(rest[outIndex])))throw new Error('خروجی از قبل وجود دارد؛ نام نسخهٔ تازه بده.');
  if(!fs.existsSync(path.join(project,'node_modules')))fs.symlinkSync(path.join(engine,'node_modules'),path.join(project,'node_modules'),process.platform==='win32'?'junction':'dir');
  const argv=['--require',path.join(ROOT,'scripts/runtime-home.cjs'),path.join(engine,'node_modules/@remotion/cli',bin),command,input,...adjusted,'--browser-executable',chrome,'--public-dir',path.join(project,'public')];
  if(command==='render')argv.push('--concurrency','1');
  const env=localEnv(); env.NODE_PATH=path.join(engine,'node_modules');
  const result=spawnSync(process.execPath,argv,{cwd:engine,env,stdio:'inherit'});
  if(result.error)throw result.error;process.exitCode=result.status??1;
} catch(e) {console.error(e.message);process.exitCode=1;}

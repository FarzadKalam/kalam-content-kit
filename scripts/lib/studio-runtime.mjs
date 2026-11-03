import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {ROOT} from './paths.mjs';
export function python(args,{input,root=ROOT}={}) {
  for(const exe of [process.env.KALAM_PYTHON,'python3','python'].filter(Boolean)) {
    const r=spawnSync(exe,args,{cwd:root,input,encoding:'utf8',maxBuffer:20*1024*1024});
    if(r.error?.code==='ENOENT')continue;
    if(r.error)throw r.error;
    if(r.status!==0)throw new Error(r.stderr.trim()||'Python command failed');
    return r.stdout;
  }
  throw new Error('Python 3.11+ لازم است؛ KALAM_PYTHON را در صورت نیاز تنظیم کن.');
}
export const compile=(spec,settings)=>JSON.parse(python([path.join(ROOT,'scripts/studio.py'),'compile',spec,'--settings',settings]));

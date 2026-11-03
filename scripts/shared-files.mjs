import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {ROOT} from './lib/paths.mjs';
export function sharedFiles(root=ROOT) {
  // Git is optional for ZIP users. The same directory exclusions apply in both modes.
  const excluded=p=>p.split('/').some(s=>['.git','.local','.cache','node_modules','__pycache__','.hyperframes','dist'].includes(s))||p.startsWith('engines/remotion/public/assets/');
  const git=fs.existsSync(path.join(root,'.git'))?spawnSync('git',['ls-files','--cached','--others','--exclude-standard','-z'],{cwd:root,encoding:'utf8'}):null;
  const result=[];
  if(git?.status===0)result.push(...git.stdout.split('\0').filter(Boolean));
  else {
    function walk(dir,relative='') {
      for(const item of fs.readdirSync(dir,{withFileTypes:true})) {
        const rel=path.posix.join(relative,item.name);
        if(excluded(rel))continue;
        if(item.isSymbolicLink())throw new Error('Symlinks are not included in shared packages: '+rel);
        if(item.isDirectory())walk(path.join(dir,item.name),rel);else result.push(rel);
      }
    }
    walk(root);
  }
  return [...new Set(result)].filter(p=>!excluded(p)&&fs.existsSync(path.join(root,p))).sort();
}

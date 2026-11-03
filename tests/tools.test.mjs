import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {binary} from '../scripts/lib/tools.mjs';
import {browser,ROOT} from '../scripts/lib/paths.mjs';
import {python} from '../scripts/lib/studio-runtime.mjs';

test('platform-specific media binaries execute on the current OS',()=>{
  for(const name of ['ffmpeg','ffprobe']){
    const tool=binary(name);assert.ok(fs.existsSync(tool));
    assert.match(execFileSync(tool,['-version'],{encoding:'utf8'}),new RegExp(name+' version'));
  }
});
test('explicit browser path is preserved on both supported OS paths',()=>{
  for(const os of ['linux','win32'])assert.equal(browser({KALAM_BROWSER_PATH:process.execPath},os),process.execPath);
});
test('Python reads and returns Persian UTF-8 even when the parent requests a legacy code page',t=>{
  const directory=path.join(ROOT,'.cache/tests');fs.mkdirSync(directory,{recursive:true});
  const file=path.join(directory,'persian-encoding-'+process.pid+'.txt'),content='کلام تازه؛ فارسی و نیم‌فاصله';
  fs.writeFileSync(file,content,'utf8');
  const saved={PYTHONUTF8:process.env.PYTHONUTF8,PYTHONIOENCODING:process.env.PYTHONIOENCODING};
  t.after(()=>{fs.rmSync(file,{force:true});for(const [key,value] of Object.entries(saved)){if(value===undefined)delete process.env[key];else process.env[key]=value;}});
  process.env.PYTHONUTF8='0';process.env.PYTHONIOENCODING='cp1252';
  const result=python(['-c','import sys;from pathlib import Path;print(Path(sys.argv[1]).read_text(),end="")',file]);
  assert.equal(result,content);
});

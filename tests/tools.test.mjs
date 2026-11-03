import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {binary} from '../scripts/lib/tools.mjs';
import {browser} from '../scripts/lib/paths.mjs';

test('platform-specific media binaries execute on the current OS',()=>{
  for(const name of ['ffmpeg','ffprobe']){
    const tool=binary(name);assert.ok(fs.existsSync(tool));
    assert.match(execFileSync(tool,['-version'],{encoding:'utf8'}),new RegExp(name+' version'));
  }
});
test('explicit browser path is preserved on both supported OS paths',()=>{
  for(const os of ['linux','win32'])assert.equal(browser({KALAM_BROWSER_PATH:process.execPath},os),process.execPath);
});

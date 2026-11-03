import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const readJson = p => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\uFEFF/, ''));
export function writeJson(p, value) { fs.mkdirSync(path.dirname(p), {recursive:true}); fs.writeFileSync(p, JSON.stringify(value,null,2)+'\n','utf8'); }
export function safeId(id) {
  if (!/^[a-z0-9][a-z0-9-]{0,63}$/.test(id||'')) throw new Error('شناسه فقط حروف کوچک انگلیسی، عدد و خط تیره، حداکثر ۶۴ نویسه باشد.');
  return id;
}
export function inside(base, candidate) {
  const target=path.resolve(base,candidate), rel=path.relative(path.resolve(base),target);
  if (rel==='..'||rel.startsWith('..'+path.sep)||path.isAbsolute(rel)) throw new Error('مسیر باید داخل پوشهٔ مجاز باشد.');
  // Reject symlinks/junctions at existing ancestors, including the base itself.
  for (let p=target;;p=path.dirname(p)) {
    if(fs.existsSync(p)&&fs.lstatSync(p).isSymbolicLink()) throw new Error('مسیر لینک‌شده برای سفارش مجاز نیست.');
    if(p===path.parse(p).root) break;
  }
  return target;
}
export function localEnv(root=ROOT) {
  const cache=path.join(root,'.cache'), temp=path.join(cache,'temp'); fs.mkdirSync(temp,{recursive:true});
  return {...process.env,TEMP:temp,TMP:temp,TMPDIR:temp,npm_config_cache:path.join(cache,'npm'),
    KALAM_RUNTIME_HOME:path.join(cache,'tool-home'),
    LOCALAPPDATA:path.join(cache,'appdata/local'),APPDATA:path.join(cache,'appdata/roaming'),
    HF_HOME:path.join(cache,'huggingface'),XDG_CACHE_HOME:cache,
    HYPERFRAMES_SKIP_SKILLS:'1',HYPERFRAMES_NO_UPDATE_CHECK:'1',HYPERFRAMES_NO_TELEMETRY:'1',DO_NOT_TRACK:'1',
    PLAYWRIGHT_BROWSERS_PATH:path.join(cache,'browsers'),PUPPETEER_CACHE_DIR:path.join(cache,'browsers')};
}
export function browser(env=process.env,platform=process.platform) {
  const system=platform==='linux'?[
    '/usr/bin/google-chrome','/usr/bin/google-chrome-stable','/usr/bin/chromium','/usr/bin/chromium-browser',
    '/opt/google/chrome/chrome']:platform==='darwin'?[
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Chromium.app/Contents/MacOS/Chromium']:[
    'C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe', env.LOCALAPPDATA&&path.join(env.LOCALAPPDATA,'Google/Chrome/Application/chrome.exe')];
  const candidates=[env.KALAM_BROWSER_PATH, env.HYPERFRAMES_BROWSER_PATH,...system];
  return candidates.find(p=>p&&fs.existsSync(p));
}

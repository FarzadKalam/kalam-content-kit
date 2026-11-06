import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {ROOT,readJson,localEnv,browser} from './lib/paths.mjs';
import {createProject} from './projects.mjs';
import {binary} from './lib/tools.mjs';
import {assertProductionReadyForPath} from './storyboard.mjs';
const [command,...args]=process.argv.slice(2);
const opts={}; for(let i=0;i<args.length;i++) if(args[i].startsWith('--')) opts[args[i].slice(2)]=args[i+1]&&!args[i+1].startsWith('--')?args[++i]:true;
const env=localEnv(); const chrome=browser(); if(chrome) env.HYPERFRAMES_BROWSER_PATH=chrome;
function run(exe,argv) {const r=spawnSync(exe,argv,{cwd:ROOT,env,stdio:'inherit'});if(r.error)throw r.error;process.exitCode=r.status??1;}
try {
  if(command==='doctor') {
    const [major,minor]=process.versions.node.split('.').map(Number);
    const checks={node:{passed:major>22||(major===22&&minor>=12),value:process.version},
      writableRoot:{passed:fs.existsSync(ROOT),value:ROOT},browser:{passed:!!chrome,value:chrome||'KALAM_BROWSER_PATH را تنظیم کن'},
      skills:{passed:fs.existsSync(path.join(ROOT,'.agents/skills/hyperframes/SKILL.md'))}};
    for(const n of ['ffmpeg','ffprobe']) {try {const p=binary(n);checks[n]={passed:fs.existsSync(p),value:p}}catch{checks[n]={passed:false}}}
    checks.hyperframes={passed:fs.existsSync(path.join(ROOT,'node_modules/hyperframes/package.json'))};
    checks.remotionOptional={installed:fs.existsSync(path.join(ROOT,'engines/remotion/node_modules/remotion'))};
    console.log(JSON.stringify(checks,null,2)); if(Object.values(checks).some(c=>c.passed===false))process.exitCode=1;
  } else if(command==='new') console.log(createProject({...opts,width:Number(opts.width||1080),height:Number(opts.height||1920)}));
  else if(command==='catalog') {
    const q=String(opts.query||'').toLowerCase(), items=readJson(path.join(ROOT,'library/catalog.json'));
    console.log(JSON.stringify(items.filter(x=>[x.name,x.description,...x.tags].join(' ').toLowerCase().includes(q)&&(!opts.engine||x.engine===opts.engine)),null,2));
  } else if(command==='hf') {
    if(args[0]==='render'&&!args.includes('--help')&&!args.includes('-h')) {
      if(!args[1]||args[1].startsWith('-'))throw new Error('برای رندر، ابتدا مسیر سفارش و سپس گزینه‌ها را بده.');
      assertProductionReadyForPath(args[1]);
    }
    const localCommands=new Set(['check','lint','snapshot','preview','render','info','compositions','timeline','docs','catalog','add','history','init','audio','keyframes','compare','present','play']);
    if(!localCommands.has(args[0])||args.some(a=>['--cloud','--upload','--publish'].includes(a))||args.includes('--describe')&&args[args.indexOf('--describe')+1]!=='false')throw new Error('این کیت فقط فرمان‌های محلی HyperFrames را اجرا می‌کند؛ تولید رسانه با ابزار داخلی محیط است.');
    if(args[0]==='snapshot'&&!args.includes('--describe'))args.push('--describe','false');
    if(!chrome&&['render','snapshot','check','preview'].includes(args[0]))throw new Error('مرورگر موجود پیدا نشد؛ KALAM_BROWSER_PATH را تنظیم کن.');
    const pkg=readJson(path.join(ROOT,'node_modules/hyperframes/package.json'));
    const entry=typeof pkg.bin==='string'?pkg.bin:pkg.bin.hyperframes;
    env.PATH=[path.dirname(binary('ffmpeg')),path.dirname(binary('ffprobe')),env.PATH].join(path.delimiter);
    run(process.execPath,['--require',path.join(ROOT,'scripts/runtime-home.cjs'),path.join(ROOT,'node_modules/hyperframes',entry),...args]);
  } else if(command==='media') {
    const [action,input,output]=args; if(!input||!fs.existsSync(input))throw new Error('فایل ورودی پیدا نشد.');
    if(action==='probe')run(binary('ffprobe'),['-v','error','-show_format','-show_streams','-of','json',path.resolve(input)]);
    else if(action==='extract') {
      if(!output||path.resolve(input)===path.resolve(output)||fs.existsSync(output))throw new Error('خروجی باید فایل تازه و جدا از ورودی باشد.');
      fs.mkdirSync(path.dirname(path.resolve(output)),{recursive:true});
      run(binary('ffmpeg'),['-n','-i',path.resolve(input),'-vn','-ac','1','-ar','16000',path.resolve(output)]);
    } else throw new Error('media probe یا media extract');
  } else throw new Error('دستورها: doctor | new | catalog | hf | media');
} catch(error) {console.error(error.message);process.exitCode=1;}

#!/usr/bin/env node
import fs from 'node:fs';
import {readJson,inside} from './lib/paths.mjs';
import {newsSettings,newsRunPath,createNewsRun,buildNewsPlan,importNewsEvidence,newsDigest,markNewsItem,newsToContent} from './news-projects.mjs';
const [command,...args]=process.argv.slice(2),opts={},pos=[];
for(let i=0;i<args.length;i++)if(args[i].startsWith('--'))opts[args[i].slice(2)]=args[i+1]&&!args[i+1].startsWith('--')?args[++i]:true;else pos.push(args[i]);
const print=value=>console.log(JSON.stringify(value,null,2));
const required=value=>{if(typeof value!=='string'||!value)throw new Error('آرگومان لازم است؛ news help را ببین.');return value;};
try {
  if(!command||command==='help')print({commands:{settings:'منابع، دسته‌ها، فیلترها و وزن‌ها',new:'--id scan --category local|national|khorasan_razavi|khabarfarsi|google_trends|google_sports|all [--query موضوع] [--lookback 48] [--limit 10] [--social false]',plan:'scan؛ دستور جستجو با وب واقعی، بدون اجرای شبکه یا مدل',import:'scan --file evidence.json؛ ورود مدرک واقعی، نه نتیجهٔ حدسی',digest:'scan؛ رتبه‌بندی، منابع مرتبط، تازگی و سابقهٔ استفاده',select:'scan itemId --project job [--kind text|image|slides|motion] [--brand golbahar] [--profile channel] [--template news_story]',mark:'scan itemId --action selected|used|dismissed|archived [--note توضیح]',resume:'scan؛ ادامهٔ جستجو با snapshot همان تنظیمات'},automaticPublication:false});
  else if(command==='settings')print(newsSettings());
  else if(command==='new')print({run:createNewsRun({...opts,id:required(opts.id)})});
  else if(command==='plan')print(buildNewsPlan(required(pos[0])));
  else if(command==='import')print(importNewsEvidence(required(pos[0]),readJson(required(opts.file))));
  else if(command==='digest')print(newsDigest(required(pos[0])));
  else if(command==='select')print(newsToContent(required(pos[0]),required(pos[1]),{...opts,project:required(opts.project)}));
  else if(command==='mark')print(markNewsItem(required(pos[0]),required(pos[1]),required(opts.action),{note:opts.note||''}));
  else if(command==='resume') {
    const dest=newsRunPath(required(pos[0]));print({run:readJson(inside(dest,'run.json')),settings:readJson(inside(dest,'settings.json')),review:fs.readFileSync(inside(dest,'REVIEW.md'),'utf8'),digest:newsDigest(pos[0])});
  } else throw new Error('دستور خبریابی ناشناخته است.');
}catch(error){console.error(error.message);process.exitCode=1;}

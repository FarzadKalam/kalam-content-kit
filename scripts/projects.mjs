import fs from 'node:fs';
import path from 'node:path';
import {ROOT,inside,safeId,readJson,writeJson} from './lib/paths.mjs';

export function createProject({id,brand,mode='motion',engine='hyperframes',width=1080,height=1920}, root=ROOT) {
  safeId(id);safeId(brand);
  if(!['motion','photos','presenter'].includes(mode)) throw new Error('نوع سفارش نامعتبر است.');
  if(!['hyperframes','remotion'].includes(engine)) throw new Error('موتور نامعتبر است.');
  if(![width,height].every(n=>Number.isInteger(n)&&n>=240&&n<=7680&&n%2===0)) throw new Error('ابعاد باید عدد صحیح زوج بین ۲۴۰ و ۷۶۸۰ باشد.');
  const profile=readJson(inside(path.join(root,'brands'),brand+'.json'));
  const project=inside(path.join(root,'.local/projects'),id);
  if(fs.existsSync(project)) throw new Error('این سفارش وجود دارد؛ برای ادامه همان پوشه را باز کن.');
  const assets=engine==='remotion'?'public/assets':'assets';
  for(const d of [assets,'analysis','renders','compositions']) fs.mkdirSync(path.join(project,d),{recursive:true});
  for(const dir of ['fonts','sfx']) fs.cpSync(path.join(root,'assets',dir),path.join(project,assets,dir),{recursive:true});
  if(fs.existsSync(path.join(root,'assets/brands',brand))) fs.cpSync(path.join(root,'assets/brands',brand),path.join(project,assets,'brand'),{recursive:true});
  writeJson(path.join(project,'project.json'),{schemaVersion:1,id,brand,mode,engine,width,height,fps:30,phase:'brief',
    audio:{mode:'undecided',scriptApproval:null,narrationFile:null},fonts:profile.fontPolicy||{primary:profile.font||'Peyda',selection:'project-brief'},brandReady:profile.status==='ready',createdAt:new Date().toISOString()});
  writeJson(path.join(project,'brand.json'),profile);
  writeJson(path.join(project,'sound-plan.json'),{schemaVersion:1,fps:30,events:[],tracks:[],review:{status:'pending',listened:false,notes:''}});
  writeJson(path.join(project,'visual-plan.json'),{schemaVersion:1,assets:[],review:{status:'pending'}});
  fs.writeFileSync(path.join(project,'BRIEF.md'),`# سفارش ${id}\n\nبرند: ${profile.name}\nنوع: ${mode}\nهدف و مخاطب:\nمنبع خبر/محصول:\nفایل‌های اصلی:\nمتن قطعی و CTA:\nوضعیت سناریو/تأیید متن:\nنریشن کاربر / گفتار موجود / بی‌نریشن / کاملاً بی‌صدا:\nمدت تقریبی:\nموارد الزامی یا ممنوع:\n\nهویتِ ناقص باید پیش از ساخت گرافیک برند تکمیل شود.\n`,'utf8');
  for(const [name,text] of Object.entries({'DECISIONS.md':'# تصمیم‌های سفارش\n\nتأیید واقعی متن، تغییرات کاربر و دلیل انتخاب موتور با تاریخ و مرجع پیام ثبت شود.\n','REVIEW.md':'# بازبینی\n\nوضعیت: pending\n\n| بررسی | نتیجه | مدرک |\n| --- | --- | --- |\n| محتوا و برند | pending | |\n| زمان و صدا | pending | |\n| فریم‌ها | pending | |\n| رندر و ffprobe | pending | |\n'})) fs.writeFileSync(path.join(project,name),text,'utf8');
  if(engine==='hyperframes') {
    fs.copyFileSync(path.join(root,'node_modules/gsap/dist/gsap.min.js'),path.join(project,assets,'gsap.min.js'));
    writeJson(path.join(project,'hyperframes.json'),{paths:{blocks:'compositions',components:'compositions/components',assets:'assets'},media:{autoProxy:false}});
  } else {
    fs.writeFileSync(path.join(project,'README.md'),`# Remotion\n\nاز engines/remotion/src الگوی Composition بگیر و صحنهٔ واقعی سفارش را بنویس.\nبرای preview: node scripts/remotion.mjs studio .local/projects/${id}/src/index.jsx\nبرای رندر: node scripts/remotion.mjs render .local/projects/${id}/src/index.jsx Main .local/projects/${id}/renders/final.mp4\nدستورها از ریشهٔ کیت اجرا شوند؛ public همین سفارش خودکار انتخاب می‌شود.\n`,'utf8');
    fs.mkdirSync(path.join(project,'src')); // Source is intentionally not a copied generic film.
  }
  return project;
}

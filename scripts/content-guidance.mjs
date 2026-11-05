import fs from 'node:fs';
import path from 'node:path';
import {ROOT,readJson} from './lib/paths.mjs';

// Discover abilities from the real catalogs; do not encode a fixed recommendation menu.
export function contentGuidance({spec={},state={},settingsDir,root=ROOT}={}) {
  const settings=settingsDir||path.join(root,'config/studio');
  const ui=readJson(path.join(root,'catalog/studio-ui.json'));
  const rules=readJson(path.join(root,'catalog/studio.json'));
  const policyFile=path.join(settings,'assistant-guidance.json');
  const policy=fs.existsSync(policyFile)?readJson(policyFile):{
    guide:'docs/studio/assistant.fa.md',legacyOrder:true,
    instructions:['قواعد و انتخاب‌های سفارش قبلی حفظ شوند؛ راهنمای فعلی صرفاً برای شناخت قابلیت‌هاست.']};
  const registryFile=path.join(root,'assets/studio/references/registry.json');
  const references=spec.references??(fs.existsSync(registryFile)?readJson(registryFile).assets:[]);
  const templates=ui.templates.map(t=>({...t,prompt:`prompts/templates/${t.id}.txt`}));
  const profiles=Object.entries(rules.editorialProfiles).map(([id,p])=>({id,label:p.label,description:p.description,prompt:`prompts/editorial/${id}.txt`}));
  const requests=spec.kind==='slides'?spec.slides||[]:spec.request?[spec.request]:[];
  const activeTemplates=[...new Set(requests.map(r=>r.format?.template).filter(Boolean))];
  for(const id of activeTemplates)if(!templates.some(t=>t.id===id))throw new Error('قالب راهنما ناشناخته است: '+id);
  if(spec.profile&&!profiles.some(p=>p.id===spec.profile))throw new Error('پروفایل راهنما ناشناخته است: '+spec.profile);
  const referenceGroups=Object.entries(rules.assetEntities).flatMap(([kind,entities])=>
    Object.entries(entities).map(([entityId,label])=>({kind,entityId,label,
      assets:references.filter(r=>r.kind===kind&&r.entityId===entityId).map(r=>({assetId:r.assetId,path:r.path,profile:r.profile,isDefault:r.isDefault})),
      status:references.some(r=>r.kind===kind&&r.entityId===entityId)?'references-present':'needs-reference'})));
  const statusFile=path.join(settings,'status.json');
  const brandFile=settingsDir?path.join(path.dirname(settingsDir),'brand.json'):spec.brand?path.join(root,'brands',spec.brand+'.json'):null;
  const brandTypography=state.fonts||(brandFile&&fs.existsSync(brandFile)?readJson(brandFile).fontPolicy:null);
  const musicInstructions=path.join(settings,'assistant-prompts/music-score.txt');
  const musicInstructionsPresent=fs.existsSync(musicInstructions);
  return {
    policy,
    brandTypography,
    context:{kind:spec.kind||null,brand:spec.brand||null,purpose:spec.purpose||null,templates:activeTemplates,profile:spec.profile||null,
      motionNarration:spec.purpose==='motion',music:spec.music||null,
      currentSettings:settings,capabilities:state.capabilities||{image:{status:'unknown'},speech:{status:'unknown'},music:{status:'unknown'}},
      memoryFiles:['BRIEF.md','DECISIONS.md','REVIEW.md'],
      execution:'read-only-guidance; no generation, new order, approval or spec change'},
    routes:{
      text:{guide:'docs/studio/text.fa.md',profiles,basePrompt:'prompts/editorial/master.txt'},
      image:{guide:'docs/studio/image.fa.md',templates,modes:['generate','preserve','reference','edit_existing','studio'],
        basePrompts:['prompts/image-base.txt','prompts/image-non-news-base.txt','prompts/image-style.txt']},
      slides:{guide:'docs/studio/slides.fa.md',perSlideSettings:true,limit:rules.limits.slides},
      audio:{guide:'docs/studio/audio.fa.md',execution:'native-if-available-after-script-approval; otherwise admin audio file'},
      music:{guide:'docs/studio/music.fa.md',execution:'approved-local-file-or-external-prompt; native-generation-only-if-real-tool-is-available',
        modes:['none','file','external-prompt','native-if-available'],mixing:'local; narration-first; real-duration-and-ducking',
        promptInstructions:musicInstructionsPresent?musicInstructions:path.join(root,'config/studio/assistant-prompts/music-score.txt'),
        instructionsSource:musicInstructionsPresent?'order-settings':'current-kit-fallback; preserve legacy choices',
        deliverables:['renders/music-prompt.txt','renders/MUSIC-SCORE.md'],
        alignment:'cue-sheet-linked-to-narration-phrases-and-visual-events; seconds-for-builds-drops-hits-and-ending; estimates-until-final-audio'},
      videoPrompts:{guide:'docs/studio/video-prompts.fa.md',execution:'prompt-package-for-manual-Gemini-or-Google-Flow',
        models:Object.keys(rules.limits.videoReferences),compiler:'vendor/studio/video_rules.py',videoGeneration:false},
      motion:{guide:'docs/studio/motion.fa.md',skill:'.agents/skills/kalam-edit/SKILL.md',taste:policy.motionTaste||'docs/editing-contract.fa.md',
        craftSkills:['.agents/skills/gsap-kalam/SKILL.md','.agents/skills/illustration-kalam/SKILL.md'],
        reframing:'docs/workflows/reframing.md',durationBasis:'actual-narration-audio-when-present',
        mediaChoices:['existing-media','generated-images','studio-characters','svg-html','documented-charts','external-generated-video'],
        engines:['hyperframes','remotion-optional'],scenarioGuidance:'دو ایدهٔ متفاوت برای سناریوی باز؛ رسانه و تعداد نماها تابع محتوا و انتخاب کاربر است.'},
      newsDiscovery:{guide:'docs/studio/news-discovery.fa.md',skill:'.agents/skills/kalam-news/SKILL.md',settings:'config/news.json',
        execution:'native-web-search-and-source-reading; local-evidence-and-ranking',command:'npm run news -- help',
        sources:['news-sites','public-channels','public-social-posts'],automaticPublication:false},
      publicData:{guide:'docs/studio/public-data.fa.md',catalog:'catalog/public-data.json',newsDiscovery:false}
    },
    references:referenceGroups,
    activeForms:{templates:activeTemplates.map(id=>templates.find(t=>t.id===id)),
      profile:profiles.find(p=>p.id===spec.profile)||null,
      completeControls:'catalog/studio-ui.json',requestBuilders:ui.requestBuilders.map(b=>({name:b.name,file:b.file,line:b.line})),
      instructions:'فیلد، شرط، پیش‌فرض و payload کامل فرم فعال را بخوان؛ فهرست مختصر guide جای فرم کامل نیست.'},
    pairedDeliverables:spec.purpose==='motion'?{
      guide:'docs/studio/assistant.fa.md',script:'script.md',
      outputs:['continuous-spoken-narration','visual-scenario-linked-to-exact-narration-phrases'],
      beatFields:['id','narrationPhrase','onScreenText','visualAction','mediaSourceOrNeed','soundCue'],
      timing:'estimated-before-audio; align-to-real-speech-afterwards',
      audioGeneration:'requires-actual-script-approval; preparing-the-draft-does-not'
    }:null,
    sourceStatus:fs.existsSync(statusFile)?readJson(statusFile):null,
    promptDirectory:path.join(settings,'prompts')
  };
}

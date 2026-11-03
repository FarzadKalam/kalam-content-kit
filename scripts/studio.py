#!/usr/bin/env python3
"""Offline adapter for Studio rules. All model execution belongs to the host agent."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'vendor/studio'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

gateway = load('gateway_rules')
image = load('image_rules')
video = load('video_rules')

def read(path, fallback=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else copy.deepcopy(fallback)

def load_settings(directory=None):
    base = Path(directory) if directory else ROOT/'config/studio'
    defaults = {
        'image-model': {'defaultModel': gateway.DEFAULT_IMAGE_MODEL},
        'text-models': {'editorialModel':gateway.DEFAULT_EDITORIAL_TEXT_MODEL,
            'replyModel':gateway.DEFAULT_REPLY_TEXT_MODEL,'analysisModel':gateway.DEFAULT_ANALYSIS_TEXT_MODEL,
            'videoPromptModel':'gpt-6-luna'},
        'voice-models': {'defaultVoiceEngine':gateway.DEFAULT_VOICE_ENGINE,
            'defaultVoice':gateway.DEFAULT_VOICE_BY_ENGINE[gateway.DEFAULT_VOICE_ENGINE]},
        'transcription-model': {'defaultModel':gateway.DEFAULT_TRANSCRIPTION_MODEL},
    }
    settings={}
    for name,value in defaults.items():
        loaded=read(base/'settings'/f'{name}.json',{})
        settings[name]={**value,**(loaded if isinstance(loaded,dict) else {})}
    selected=str(settings['image-model'].get('defaultModel',''))
    if selected=='gpt-image-2':selected='gpt-image-2.5-flare'  # Same legacy migration as Studio.
    settings['image-model']['defaultModel']=selected if selected in gateway.IMAGE_MODELS else gateway.DEFAULT_IMAGE_MODEL
    for key in ['editorialModel','replyModel','analysisModel','videoPromptModel']:
        if settings['text-models'][key] not in gateway.TEXT_MODELS:settings['text-models'][key]=defaults['text-models'][key]
    if settings['text-models']['videoPromptModel'] not in {'gpt-6-luna','gpt-6.1-terra','gpt-6-astra'}:settings['text-models']['videoPromptModel']='gpt-6-luna'
    engine=settings['voice-models']['defaultVoiceEngine']
    if engine not in gateway.VOICE_ENGINES:engine=gateway.DEFAULT_VOICE_ENGINE
    settings['voice-models']['defaultVoiceEngine']=engine
    voices={v['id'] for v in gateway.VOICE_ENGINES[engine]['voices']} if gateway.VOICE_ENGINES[engine]['provider']=='openai' else {v[0] for v in gateway._GEMINI_PREBUILT_VOICES}
    if settings['voice-models']['defaultVoice'] not in voices:settings['voice-models']['defaultVoice']=gateway.DEFAULT_VOICE_BY_ENGINE[engine]
    if settings['voice-models'].get('defaultTranscriptionModel'):
        settings['transcription-model']['defaultModel']=settings['voice-models']['defaultTranscriptionModel']
    prompts = {
        'image-base':gateway.DEFAULT_IMAGE_BASE_PROMPT,
        'image-non-news-base':gateway.DEFAULT_IMAGE_NON_NEWS_PROMPT,
        'image-style':gateway.DEFAULT_IMAGE_STYLE_PROMPT,
        **{f'templates/{k}':v for k,v in gateway.DEFAULT_TEMPLATE_PROMPTS.items()},
        **{f'editorial/{k}':v[2] for k,v in gateway.TEXT_PROMPT_META.items()},
    }
    for name in prompts:
        path=base/'prompts'/f'{name}.txt'
        if path.is_file() and path.read_text(encoding='utf-8').strip():
            prompts[name]=path.read_text(encoding='utf-8').strip()
    return settings,prompts

def configure(directory=None, references=None):
    settings,prompts=load_settings(directory)
    registry=references if references is not None else read(ROOT/'assets/studio/references/registry.json',{'assets':[]})['assets']
    gateway.image_model_settings=lambda: settings['image-model']
    gateway.image_base_prompt=lambda:prompts['image-base']
    gateway.image_non_news_prompt=lambda:prompts['image-non-news-base']
    gateway.image_style_prompt=lambda:prompts['image-style']
    gateway.image_template_prompt=lambda name:prompts[f'templates/{name}']
    gateway.studio_text_prompt=lambda name:prompts[f'editorial/{name}']
    gateway.video_asset_registry=lambda:{'assets':registry}
    gateway.video_scene_project=video.scene_project
    image.app=gateway
    return settings,prompts

def catalog():
    settings,prompts=configure()
    voices=copy.deepcopy(gateway.VOICE_ENGINES)
    for engine in voices.values():
        if engine['provider']=='gemini':
            engine['voices']=[{'id':i,'label':f'{i} — {label}'} for i,label in gateway._GEMINI_PREBUILT_VOICES]
        engine['execution']='host-native-only; source catalog does not establish availability'
    return {'schemaVersion':1,'editorialProfiles':{
        k:{'label':v[0],'description':v[1],'prompt':prompts[f'editorial/{k}']}
        for k,v in gateway.TEXT_PROMPT_META.items()},
        'imageTemplates':{k:{'prompt':prompts[f'templates/{k}']} for k in gateway.DEFAULT_TEMPLATE_PROMPTS},
        'imageModels':gateway.IMAGE_MODELS,'textModels':gateway.TEXT_MODELS,'voiceEngines':voices,
        'transcriptionModels':gateway.TRANSCRIPTION_MODELS,'assetEntities':gateway.VIDEO_ASSET_ENTITIES,
        'assetProfileOptions':gateway.VIDEO_ASSET_PROFILE_OPTIONS,'settings':settings,
        'runtimeSnapshot':read(ROOT/'config/studio/status.json',{'status':'pending-live-export'}),
        'limits':{'studioReferences':gateway.STUDIO_IMAGE_REFERENCE_LIMIT,
                  'videoReferences':gateway.VIDEO_MODEL_REFERENCE_LIMITS,'slides':gateway.MAX_SLIDES_PER_SERIES}}

def checked_reference(item, base):
    relative=Path(str(item.get('path','')))
    if relative.is_absolute() or '..' in relative.parts or not str(item.get('path','')):
        raise ValueError('مسیر مرجع باید نسبی و داخل پوشهٔ سفارش باشد.')
    path=(base/relative).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise ValueError(f'فایل مرجع موجود نیست: {relative}')
    if item.get('sha256') and hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
        raise ValueError(f'فایل مرجع تغییر کرده است: {relative}')
    return path

def compile_spec(spec, base, settings_dir=None):
    if spec.get('dataRequests'):
        from public_data import validate_evidence
        validate_evidence(spec,base)
    references=spec.get('references',[])
    for item in references: checked_reference(item,base)
    settings,prompts=configure(settings_dir,references)
    kind=spec['kind']
    if kind=='text':
        profile=spec.get('profile','post')
        if not str(spec.get('text','')).strip(): raise ValueError('متن ورودی خالی است.')
        if profile=='channel_teaser' and not spec.get('channelJoinUrl'): raise ValueError('لینک عضویت لازم است.')
        return {'kind':kind,'prompt':gateway.reporter_prompt(profile,spec['text'],spec['brand'],
                spec.get('additionalInstructions',''),spec.get('channelJoinUrl',''),spec.get('webResearch')),
                'outputContract':'slide-json' if profile in gateway.SLIDE_REPORTER_PROFILES else 'text',
                'execution':{'provider':'host-native','requestedModel':settings['text-models'].get('editorialModel'),
                             'availability':'agent-must-check'}}
    if kind in {'image','slides'}:
        requests=spec.get('slides',[]) if kind=='slides' else [spec['request']]
        if not 1<=len(requests)<=10: raise ValueError('تعداد اسلاید باید بین یک تا ده باشد.')
        results=[]
        for index,raw in enumerate(requests):
            request=gateway.validate_request(copy.deepcopy(raw))
            if request['format'].get('template') not in gateway.DEFAULT_TEMPLATE_PROMPTS:
                raise ValueError('قالب تصویر ناشناخته است.')
            if request['brand']!=spec['brand']: raise ValueError('رسانهٔ سفارش و اسلاید یکسان نیست.')
            content_ready(request)
            selected=gateway.selected_studio_image_reference_assets(request) if gateway.is_studio_image_request(request) else gateway.selected_design_presenter_reference_assets(request)
            # Never silently compile a real person's identity without their actual reference.
            studio=request.get('format',{}).get('studio',{})
            people=studio.get('presenterIds',[]) if gateway.is_studio_image_request(request) else request.get('image',{}).get('presenterIds',[])
            for person in people:
                if not any(r.get('kind')=='presenter' and r.get('entityId')==person for r in selected):
                    raise ValueError(f'مرجع واقعی کاراکتر موجود نیست: {person}')
            if gateway.is_studio_image_request(request) and studio.get('location',{}).get('mode','catalog')=='catalog':
                if not any(r.get('kind')=='location' for r in selected): raise ValueError('مرجع واقعی لوکیشن موجود نیست.')
            input_ids=request.get('assets',{}).get('adminImageIds',[])
            by_id={r.get('assetId'):r for r in references}
            if any(i not in by_id for i in input_ids): raise ValueError('یکی از تصاویر سفارش موجود نیست.')
            attachments=list({r['assetId']:r for r in [*selected,*[by_id[i] for i in input_ids]]}.values())
            if request['image']['mode'] in {'preserve','reference','edit_existing'} and not attachments:
                raise ValueError('این حالت به فایل اصلی یا تصویر مرجع نیاز دارد.')
            if len(attachments)>gateway.STUDIO_IMAGE_REFERENCE_LIMIT: raise ValueError('تعداد مرجع‌های تصویر بیش از حد مجاز است.')
            record={'request':request,'requestId':request['requestId']}
            results.append({'index':index,'request':request,'prompt':image.render_prompt(record),
                'width':image.canvas_size(record)[0],'height':image.canvas_size(record)[1],
                'transparent':request['format'].get('template')=='sticker',
                'references':attachments,'requestedModel':request['image']['engine']})
        return {'kind':kind,'slides':results,'execution':{'provider':'host-native-image','availability':'agent-must-check'}}
    if kind=='video-prompts':
        project=gateway.validate_video_project(copy.deepcopy(spec['video']))
        if project['brand']!=spec['brand']: raise ValueError('رسانهٔ سفارش و ویدیو یکسان نیست.')
        segments=[]
        manifest=[]
        for index,ref in enumerate(references):
            extension=Path(ref['path']).suffix.lower()
            if extension not in {'.png','.jpg','.jpeg','.webp'}: raise ValueError('پسوند مرجع تصویری معتبر نیست.')
            name=f"{ref.get('kind','reference').upper()}_{ref.get('entityId','asset')}_{index+1:02d}{extension}"
            if Path(name).name!=name: raise ValueError('شناسهٔ مرجع معتبر نیست.')
            manifest.append({**ref,'downloadName':name})
        by_id={r['assetId']:r for r in manifest}
        for index,line in enumerate(project['lines']):
            wanted=[]
            for pid in project['presenterIds']:
                choice=project['referenceSelection']['presenters'][pid]
                chosen=[by_id[i] for i in choice['assetIds'] if i in by_id] if choice['mode']=='manual' else [r for r in manifest if r.get('kind')=='presenter' and r.get('entityId')==pid][:1]
                if not chosen or (choice['mode']=='manual' and len(chosen)!=len(choice['assetIds'])): raise ValueError(f'مرجع مجری موجود نیست: {pid}')
                if any(r.get('kind')!='presenter' or r.get('entityId')!=pid for r in chosen): raise ValueError('مرجع کاراکتر نادرست است.')
                wanted.extend(chosen)
            location=project['location']
            if location['mode']!='generated_prompt':
                choice=project['referenceSelection']['location']
                ids=location.get('assetIds',[]) if location['mode']!='catalog' else choice['assetIds']
                chosen=[by_id[i] for i in ids if i in by_id] if ids else [r for r in manifest if r.get('kind')=='location' and r.get('entityId')==location['id']][:1]
                if not chosen or (ids and len(chosen)!=len(ids)): raise ValueError('مرجع لوکیشن موجود نیست.')
                if any(r.get('kind')!='location' or r.get('entityId')!=location['id'] for r in chosen): raise ValueError('مرجع لوکیشن نادرست است.')
                wanted.extend(chosen)
            if project['monitor']['enabled'] and project['monitor']['mode']=='images' and project['monitor']['imageMode']!='generate':
                for aid in project['monitor'].get('assetIds',[]):
                    if aid not in by_id or by_id[aid].get('kind')!='monitor' or by_id[aid].get('entityId')!=project['location']['id']: raise ValueError('مرجع مانیتور موجود نیست یا متعلق به لوکیشن دیگری است.')
                    wanted.append(by_id[aid])
            wanted=list({r['assetId']:r for r in wanted}.values())
            # Prioritize the speaking presenter, then monitor, environment, co-hosts.
            # Match Studio's reserved continuity slot instead of silently exceeding Veo's limit.
            wanted.sort(key=lambda r:0 if r.get('kind')=='presenter' and r.get('entityId')==line['presenterId'] else 1 if r.get('kind')=='monitor' else 2 if r.get('kind')=='location' else 3)
            limit=gateway.VIDEO_MODEL_REFERENCE_LIMITS[project['generationModel']]
            if project['generationModel']=='veo_3_1' and (index>0 or project.get('continuation')):limit=min(limit,2)
            deferred=[r['assetId'] for r in wanted[limit:]]
            wanted=wanted[:limit]
            filenames=[r['downloadName'] for r in wanted]
            segments.append({'index':index,'durationSeconds':line['durationSeconds'],'referenceFiles':filenames,
                'prompt':gateway.video_generation_contract(project,line,index,filenames)+'\n\n'+video.compile_segment(project,line,index),
                'negativePrompt':'identity drift, invented dialogue, fake logos, unreadable Persian, warped hands, discontinuity',
                'continuityAssetRequired':index>0 or bool(project.get('continuation')),
                'deferredReferenceIds':deferred})
        return {'kind':kind,'targetModel':project['generationModel'],'project':project,'references':manifest,
                'segments':segments,'execution':{'provider':'host-native-text','videoGeneration':False}}
    if kind=='audio':
        audio=spec.get('audio',{})
        if not str(audio.get('text','')).strip(): raise ValueError('متن نریشن را کامل کنید.')
        if len(audio['text'])>4096 or len(audio.get('instructions',''))>800: raise ValueError('متن یا راهنمای لحن بیش از حد مجاز است.')
        return {'kind':kind,'text':audio['text'],'instructions':audio.get('instructions',''),
                'sourceEngine':audio.get('engineId',settings['voice-models']['defaultVoiceEngine']),
                'sourceVoice':audio.get('voice',settings['voice-models']['defaultVoice']),
                'execution':{'provider':'host-native-speech','availability':'agent-must-check',
                             'fallback':'await-admin-audio-file','requiresApprovedScript':True}}
    raise ValueError('برای موشن از مسیر تدوین و ابزارهای محلی استفاده کنید.')

def content_ready(request):
    """Preserve Studio's client-side required-content gates before a model call."""
    template=request['format']['template'];content=request.get('content',{})
    if gateway.is_studio_image_request(request): return  # Gateway and actual reference checks cover Studio scenes.
    all_fields={
        'morning_local':'morningWeekday morningPersianDate morningGregorianDate morningHijriDate morningFajr morningSunrise morningNoon morningSunset morningMaghrib morningMidnight morningRiddleQuestion'.split(),
        'morning_kalam':['morningKalamWeekLabel',*[f'morningKalamDay{i}' for i in range(1,8)]],
        'market':'marketWeekday marketPersianDate marketGregorianDate marketHijriDate marketTime marketSource marketUsdPrice marketEurPrice marketCoinPrice marketGold18Price marketBitcoinPrice'.split(),
        'poster':['posterHeadline'],'sticker':['stickerText'],'citizen_message':['citizenMessageText'],
    }
    any_fields={'sport':['title','sportResults'],'occasion_greeting':['occasionName','occasionHeadline','occasionMessage'],
                'editorial_note':['title','caption']}
    if template=='club_showcase':return  # Upstream validator handles its nested contract.
    if template=='classifieds':
        ads=json.loads(content.get('classifiedsJson','[]'))
        if not isinstance(ads,list) or not 1<=len(ads)<=4 or any(not isinstance(a,dict) or not str(a.get('title','')).strip() or not str(a.get('body','')).strip() for a in ads):raise ValueError('آگهی‌ها کامل نیستند؛ بین یک تا چهار عنوان و متن لازم است.')
        return
    fields=all_fields.get(template,['title'])
    if template in any_fields:
        if not any(str(content.get(k,'')).strip() for k in any_fields[template]):raise ValueError('متن ضروری قالب را کامل کنید.')
    else:
        missing=[k for k in fields if not str(content.get(k,'')).strip()]
        if missing:raise ValueError('فیلدهای ضروری قالب خالی‌اند: '+', '.join(missing))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['catalog','compile','slides-validate'])
    parser.add_argument('file',nargs='?',type=Path)
    parser.add_argument('--settings',type=Path)
    args=parser.parse_args()
    if args.command=='catalog': result=catalog()
    elif args.command=='slides-validate':
        configure(args.settings)
        result=gateway.parse_reporter_slide_deck(args.file.read_text(encoding='utf-8'))
    else:
        spec=read(args.file)
        result=compile_spec(spec,args.file.resolve().parent,args.settings)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try: main()
    except (ValueError,KeyError,TypeError,OSError,gateway.ClientError) as error:
        print(str(error),file=sys.stderr)
        sys.exit(1)

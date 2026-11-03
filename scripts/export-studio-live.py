#!/usr/bin/env python3
"""Run on the Studio server. Read-only, allowlisted export; never imports the gateway.

python3 export-studio-live.py --data-dir /var/lib/kalam-design --output /tmp/studio-live.zip
Only the new output archive is written. No service restart, default creation or network call.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

TEMPLATES='club_news club_content club_studio club_showcase club_promotion news_story news_post photo_report video_placeholder citizen_message infographic poster sticker classifieds morning_local morning_kalam market occasion_greeting editorial_note night home_tip visual_riddle nature poll_story poll_post sport studio'.split()
EDITORIAL='master extract site_publish newsroom_rewrite site post channel story multi_story citizen_multi_story admin_multi_story carousel reel scenario titles analysis infographic_data channel_teaser citizen_clean citizen_short citizen_report'.split()
SETTING_KEYS={'image-model':['defaultModel'],'text-models':['editorialModel','replyModel','analysisModel','videoPromptModel'],
              'voice-models':['defaultVoiceEngine','defaultVoice','defaultTranscriptionModel']}
ENTITIES={'presenter':{'kamran','tara','mojtaba_jafari','hamidreza_jafari'},
          'location':{'newsroom','studio_main','studio_2','terrace','living_room'},
          'monitor':{'newsroom','studio_main','studio_2','terrace','living_room'}}
PROFILE_KEYS={'role','aspectRatio','framing','presenterCapacity','copySpace','placement','subjectPosition','foregroundOccluder','cameraAngle','label'}

def allowed_config_paths():
    return {'prompts/image-base.txt','prompts/image-non-news-base.txt','prompts/image-style.txt',
            *[f'prompts/templates/{name}.txt' for name in TEMPLATES],
            *[f'prompts/editorial/{name}.txt' for name in EDITORIAL],
            *[f'settings/{name}.json' for name in SETTING_KEYS]}

def json_bytes(value): return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def safe_file(root,relative):
    rel=Path(relative)
    if rel.is_absolute() or '..' in rel.parts:raise ValueError('Unsafe relative path')
    candidate=root/rel
    for part in [candidate,*candidate.parents]:
        if part==root.parent:break
        if part.is_symlink():raise ValueError('Symlink not allowed in export')
    if not candidate.resolve().is_relative_to(root.resolve()):raise ValueError('Path outside data directory')
    return candidate

def export(data_dir,output):
    root=data_dir.resolve();files={};absent=[]
    for relative in sorted(allowed_config_paths()):
        path=safe_file(root,relative)
        if not path.is_file():absent.append(relative);continue
        if relative.startswith('settings/'):
            value=json.loads(path.read_text(encoding='utf-8'))
            files[relative]=json_bytes({k:value[k] for k in SETTING_KEYS[path.stem] if k in value})
        else:files[relative]=path.read_text(encoding='utf-8').encode('utf-8')
    registry=safe_file(root,'video-assets/registry.json');assets=[];missing_assets=[]
    if registry.is_file():
        for item in json.loads(registry.read_text(encoding='utf-8')).get('assets',[]):
            if item.get('scope')=='project':continue
            kind,entity=item.get('kind'),item.get('entityId')
            if kind not in ENTITIES or entity not in ENTITIES[kind]:raise ValueError('Unknown shared asset entity')
            filename=str(item.get('storedFilename',''));asset_id=str(item.get('assetId',''))
            if not re.fullmatch(r'[a-f0-9-]{36}',asset_id) or Path(filename).name!=filename:raise ValueError('Invalid shared asset ID/path')
            suffix=Path(filename).suffix.lower()
            if suffix not in {'.png','.jpg','.jpeg','.webp'}:raise ValueError('Unsupported shared image format')
            path=safe_file(root,f'video-assets/{kind}/{entity}/{filename}')
            if not path.is_file():missing_assets.append(asset_id);continue
            relative=f'assets/{asset_id}{suffix}';files[relative]=path.read_bytes()
            profile=item.get('profile',{})
            assets.append({'assetId':asset_id,'kind':kind,'entityId':entity,'scope':'studio','isDefault':bool(item.get('isDefault')),
                'profile':{k:v for k,v in profile.items() if k in PROFILE_KEYS},'path':relative,
                'sha256':hashlib.sha256(files[relative]).hexdigest()})
    files['registry.json']=json_bytes({'version':1,'assets':assets})
    # A token pasted into a prompt must not accidentally enter a public repository.
    secret=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{25,}|sk-(?:proj-|ant-)?[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)')
    if any(secret.search(data) for name,data in files.items() if name.endswith(('.txt','.json'))):raise ValueError('Possible credential in export; archive was not written')
    manifest={'schemaVersion':1,'source':'studio-live-filesystem','exportedAt':datetime.now(timezone.utc).isoformat(),
        'absentOverrides':absent,'missingSharedAssets':missing_assets,'registryFound':registry.is_file(),
        'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(name,data)
        archive.writestr('manifest.json',json_bytes(manifest))
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    result=export(args.data_dir,args.output)
    print(json.dumps({'output':str(args.output),'files':len(result['files']),
        'missingSharedAssets':result['missingSharedAssets'],'registryFound':result['registryFound']}))

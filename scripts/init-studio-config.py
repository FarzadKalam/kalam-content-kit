"""Materialize Git defaults and deployed production prompts; never claim a live export."""
from pathlib import Path
import json
import studio

root=studio.ROOT/'config/studio'
settings,prompts=studio.load_settings()
production=studio.ROOT/'vendor/studio/source/deploy/prompts'
for key,name in {'image-base':'image-base.production.fa.txt','templates/news_story':'news_story.master.fa.txt',
                 'templates/news_post':'news_post.master.fa.txt','templates/poster':'poster.production.fa.txt'}.items():
    prompts[key]=(production/name).read_text(encoding='utf-8').strip()
for name,value in prompts.items():
    path=root/'prompts'/f'{name}.txt';path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():path.write_text(value.rstrip()+'\n',encoding='utf-8')
for name,value in settings.items():
    path=root/'settings'/f'{name}.json';path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
status=root/'status.json'
if not status.exists():
    status.write_text(json.dumps({'schemaVersion':1,'status':'local-source-ready',
        'source':'Git defaults plus tracked deployment production prompts',
        'liveSyncRequired':False,'liveVerified':False,'missing':[]},indent=2)+'\n',encoding='utf-8')

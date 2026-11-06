from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import studio

def module(filename):
    spec=importlib.util.spec_from_file_location(filename,ROOT/'scripts'/f'{filename}.py')
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

class StudioRulesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
    def image(self,template='news_story'):
        return {'schemaVersion':1,'kind':'image','brand':'golbahar','references':[],
            'request':{'requestId':'test-news','platform':'codex','brand':'golbahar',
            'format':{'family':'news','template':template,'canvas':'story_1080x1920','logoBehavior':'none',
                      'news':{'layout':'top','outputKind':'title_photo'}},
            'content':{'title':'تیتر آزمون فارسی','caption':'متن قطعی ۱۲۳','additionalInstructions':''},
            'image':{'mode':'generate','engine':'gpt-image-2.5-flare'},'production':{'kind':'image'}}}
    def reference(self,kind,entity):
        aid={'presenter':'11111111-1111-1111-1111-111111111111','location':'22222222-2222-2222-2222-222222222222','monitor':'33333333-3333-3333-3333-333333333333'}[kind]
        path=Path(aid+'.png');(self.base/path).write_bytes(b'fixture')
        return {'assetId':aid,'kind':kind,'entityId':entity,'scope':'studio','path':str(path),'sha256':hashlib.sha256(b'fixture').hexdigest()}
    def video(self):
        return {'kind':'video-prompts','brand':'golbahar','references':[self.reference('presenter','kamran'),self.reference('location','newsroom')],
            'video':{'projectId':'12345678-1234-1234-1234-123456789012','brand':'golbahar','canvas':'portrait',
            'qualityMode':'precise','generationModel':'veo_3_1','directionMode':'news_bulletin','durationSeconds':8,
            'resolution':'1080p','presenterIds':['kamran'],'location':{'mode':'catalog','id':'newsroom'},
            'lines':[{'presenterId':'kamran','text':'متن قطعی اول','shot':'medium'}]}}
    def test_all_studio_templates_and_editorial_profiles_are_retained(self):
        ui=json.loads((ROOT/'catalog/studio-ui.json').read_text(encoding='utf-8'))
        catalog=studio.catalog()
        self.assertEqual({t['id'] for t in ui['templates']},set(catalog['imageTemplates']))
        self.assertEqual(set(catalog['editorialProfiles']),set(studio.gateway.TEXT_PROMPT_META))
        self.assertTrue(ui['requestBuilders'])
        self.assertIn('studioSpeechBubbles',{s['name'] for s in ui['stateDefaults']})
        self.assertTrue(any(c['options'] and c['conditions'] for c in ui['controls']))
    def test_selected_news_layout_changes_prompt_and_keeps_copy(self):
        spec=self.image();before=copy.deepcopy(spec)
        top=studio.compile_spec(spec,self.base)['slides'][0]['prompt']
        spec['request']['format']['news']['layout']='right_column'
        column=studio.compile_spec(spec,self.base)['slides'][0]['prompt']
        self.assertNotEqual(top,column);self.assertIn('ستون',column)
        self.assertIn('تیتر آزمون فارسی',top)
        self.assertEqual(before['request']['image'],{'mode':'generate','engine':'gpt-image-2.5-flare'})
    def test_all_27_templates_compile_with_their_own_fields(self):
        ui=json.loads((ROOT/'catalog/studio-ui.json').read_text(encoding='utf-8'))
        for definition in ui['templates']:
            with self.subTest(template=definition['id']):
                spec=self.image(definition['id']);req=spec['request']
                req['format']['family']={'non_news':'fixed'}.get(definition['group'],definition['group'])
                req['content']={k:(v if v else 'دادهٔ آموزشی') for k,v in ui['initialContent'].items()}
                req['content'].update({'classifiedsJson':json.dumps([{'category':'services','title':'نمونه','body':'متن آموزشی','contact':''}]),
                    'sportEventIds':'[]','sportVisualAssets':'[]','clubShowcase':{'title':'نمونهٔ جایزه','store':'نمونهٔ فروشگاه'}})
                if definition['id']=='sticker':req['format']['canvas']='sticker_1024x1024'
                if definition['group']=='studio':
                    req['image']['mode']='studio'
                    req['format']['studio']={'presenterIds':['kamran'],'locationId':'newsroom','location':{'mode':'catalog','id':'newsroom'},'textMode':'monitor','text':'متن آموزشی','monitor':{'enabled':True,'mode':'text','text':'متن آموزشی'}}
                    spec['references']=[self.reference('presenter','kamran'),self.reference('location','newsroom')]
                result=studio.compile_spec(spec,self.base)
                self.assertTrue(result['slides'][0]['prompt'])
                self.assertEqual(result['slides'][0]['request']['format']['template'],definition['id'])
    def test_each_slide_uses_its_own_copy_and_reference_mode(self):
        first=self.image()['request'];second=copy.deepcopy(first)
        first['requestId']='slide-01';second['requestId']='slide-02'
        second['content']['title']='تیتر مستقل اسلاید دوم'
        for req in [first,second]:req['format'].update({'slideMode':'carousel','slideCount':2,'canvas':'post_1080x1350'})
        result=studio.compile_spec({'kind':'slides','brand':'golbahar','slides':[first,second]},self.base)
        self.assertNotIn('تیتر مستقل اسلاید دوم',result['slides'][0]['prompt'])
        self.assertIn('تیتر مستقل اسلاید دوم',result['slides'][1]['prompt'])
    def test_empty_required_copy_blocks_before_generation(self):
        spec=self.image();spec['request']['content']['title']=''
        with self.assertRaisesRegex(ValueError,'ضروری'):studio.compile_spec(spec,self.base)
    def test_native_alpha_and_reference_requirements(self):
        spec=self.image('sticker');spec['request']['format']['canvas']='sticker_1024x1024'
        spec['request']['content']['stickerText']='متن شفاف'
        output=studio.compile_spec(spec,self.base)['slides'][0]
        self.assertTrue(output['transparent']);self.assertEqual((output['width'],output['height']),(1024,1024))
        spec=self.image();spec['request']['image']['mode']='edit_existing'
        with self.assertRaisesRegex(ValueError,'فایل اصلی'):studio.compile_spec(spec,self.base)
    def test_missing_real_presenter_is_blocked(self):
        spec=self.video();spec['references']=[]
        with self.assertRaisesRegex(ValueError,'مجری'):studio.compile_spec(spec,self.base)
    def test_reference_checksum_and_path_are_checked(self):
        spec=self.image();ref=self.reference('presenter','kamran');spec['references']=[ref]
        (self.base/ref['path']).write_bytes(b'modified')
        with self.assertRaisesRegex(ValueError,'تغییر'):studio.compile_spec(spec,self.base)
        ref['path']='../outside.png'
        with self.assertRaisesRegex(ValueError,'داخل'):studio.compile_spec(spec,self.base)
    def test_video_dialogue_time_window_and_exact_reference_filenames(self):
        spec=self.video();spec['video']['lines'][0].update({'dialogueStartSecond':1,'dialogueEndSecond':4})
        output=studio.compile_spec(spec,self.base);first=output['segments'][0]
        self.assertIn('متن قطعی اول',first['prompt']);self.assertIn('1-4s',first['prompt'])
        self.assertTrue(all(name in first['prompt'] for name in first['referenceFiles']))
        self.assertFalse(output['execution']['videoGeneration'])
        spec['video']['lines'][0]['dialogueEndSecond']=10
        with self.assertRaises(studio.gateway.ClientError):studio.compile_spec(spec,self.base)
    def test_omni_scene_durations_silence_and_timeline_stay_independent(self):
        spec=self.video();p=spec['video'];p.update({'generationModel':'gemini_omni_flash','speechEnabled':False,'durationSeconds':10})
        p['lines']=[{'presenterId':'kamran','text':'','shot':'selfie','durationSeconds':10},
                    {'presenterId':'kamran','text':'','shot':'medium','durationSeconds':5}]
        p['timeline']=[{'sceneIndex':1,'startSecond':1,'endSecond':4,'motionText':'فقط دوم','description':'حرکت دوم'}]
        output=studio.compile_spec(spec,self.base)
        self.assertEqual([s['durationSeconds'] for s in output['segments']],[10,5])
        self.assertNotIn('فقط دوم',output['segments'][0]['prompt'])
        self.assertIn('فقط دوم',output['segments'][1]['prompt'])
        self.assertIn('No character may speak',output['segments'][1]['prompt'])
    def test_disabled_monitor_does_not_require_hidden_reference_assets(self):
        spec=self.video();spec['video']['monitor']={'enabled':False,'mode':'disabled','imageMode':'generate','assetIds':['33333333-3333-3333-3333-333333333333']}
        out=studio.compile_spec(spec,self.base)
        self.assertFalse(any(name.startswith('MONITOR') for name in out['segments'][0]['referenceFiles']))
    def test_video_prompt_model_and_dimensions_match_in_all_compiler_sections(self):
        for model, resolutions in [('veo_3_1', ['720p', '1080p']), ('gemini_omni_flash', ['360p', '720p', '1080p', '4k'])]:
            for resolution in resolutions:
                for canvas in ['portrait', 'landscape']:
                    with self.subTest(model=model, resolution=resolution, canvas=canvas):
                        spec=self.video();spec['video'].update({'generationModel':model,'resolution':resolution,'canvas':canvas})
                        result=studio.compile_spec(spec,self.base)
                        prompt=result['segments'][0]['prompt']
                        width,height={'360p':(640,360),'720p':(1280,720),'1080p':(1920,1080),'4k':(3840,2160)}[resolution]
                        dimensions=f'{height}x{width}' if canvas=='portrait' else f'{width}x{height}'
                        target='Gemini Omni Flash' if model=='gemini_omni_flash' else 'Veo 3.1'
                        self.assertIn(f'{target}: a 8-second',prompt)
                        self.assertIn(f'24fps {target} scene',prompt)
                        self.assertEqual(prompt.count(dimensions),2)
                        self.assertIn('متن قطعی اول',prompt)
                        if model=='gemini_omni_flash':self.assertNotIn('Veo 3.1',prompt)
                        original=studio.video.compile_segment(result['project'],result['project']['lines'][0],0)
                        adapted=studio.video_creative_prompt(result['project'],result['project']['lines'][0],0)
                        self.assertEqual(original.split('. Cinematic professional',1)[1],adapted.split('. Cinematic professional',1)[1])
    def test_audio_missing_native_tool_has_explicit_file_fallback(self):
        out=studio.compile_spec({'kind':'audio','brand':'golbahar','audio':{'text':'متن نریشن تأییدشده'}},self.base)
        self.assertEqual(out['execution']['fallback'],'await-admin-audio-file')
        self.assertEqual(out['execution']['availability'],'agent-must-check')
    def test_partial_live_voice_settings_keep_effective_studio_defaults(self):
        base=self.base/'config';(base/'settings').mkdir(parents=True)
        (base/'settings/voice-models.json').write_text(json.dumps({'defaultTranscriptionModel':'gpt-4o-transcribe'}))
        settings,_=studio.load_settings(base)
        self.assertEqual(settings['voice-models']['defaultVoice'],'marin')
        self.assertEqual(settings['transcription-model']['defaultModel'],'gpt-4o-transcribe')
    def test_slide_parser_rejects_unstructured_text_and_preserves_persian(self):
        studio.configure()
        with self.assertRaises(studio.gateway.ClientError):studio.gateway.parse_reporter_slide_deck('متن ساده')
        deck={'slides':[{'title':'تیتر فارسی','subtitle':'','body':'بدنه','footer':'','imageMode':'generate'}]}
        out=studio.gateway.parse_reporter_slide_deck(json.dumps(deck,ensure_ascii=False))
        self.assertEqual(out[0]['title'],'تیتر فارسی')

class LiveExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.exporter=module('export-studio-live');self.importer=module('import-studio-live')
    def test_export_is_read_only_and_excludes_credentials_and_private_jobs(self):
        data=self.root/'data';(data/'settings').mkdir(parents=True);(data/'video-assets').mkdir()
        (data/'settings/image-model.json').write_text(json.dumps({'defaultModel':'gpt-image-2','apiKey':'must-not-export'}))
        (data/'video-assets/registry.json').write_text(json.dumps({'assets':[{'scope':'project','ownerId':'secret'}]}))
        before={str(p.relative_to(data)):p.read_bytes() for p in data.rglob('*') if p.is_file()}
        archive=self.root/'export.zip';self.exporter.export(data,archive)
        manifest,files=self.importer.inspect(archive)
        self.assertEqual(json.loads(files['settings/image-model.json']),{'defaultModel':'gpt-image-2'})
        self.assertEqual(json.loads(files['registry.json'])['assets'],[])
        self.assertEqual(before,{str(p.relative_to(data)):p.read_bytes() for p in data.rglob('*') if p.is_file()})
        self.assertNotIn(b'must-not-export',b''.join(files.values()))
    def test_archive_path_traversal_is_rejected(self):
        data=b'bad';archive=self.root/'bad.zip';name='../escaped.txt'
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr(name,data);z.writestr('manifest.json',json.dumps({'schemaVersion':1,'source':'studio-live-filesystem','files':{name:hashlib.sha256(data).hexdigest()}}))
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.importer.inspect(archive)
    def test_possible_token_in_prompt_prevents_export(self):
        data=self.root/'data';(data/'prompts').mkdir(parents=True)
        (data/'prompts/image-base.txt').write_text('sk-'+('x'*40))
        archive=self.root/'export.zip'
        with self.assertRaisesRegex(ValueError,'credential'):self.exporter.export(data,archive)
        self.assertFalse(archive.exists())
    def test_live_import_replaces_previous_overrides_and_leaves_a_backup(self):
        root=self.root/'kit';config=root/'config/studio';config.mkdir(parents=True)
        (config/'status.json').write_text('{}');(config/'obsolete.txt').write_text('old')
        defaults=root/'vendor/studio/git-defaults';(defaults/'prompts').mkdir(parents=True)
        (defaults/'prompts/image-base.txt').write_text('Git baseline')
        data=self.root/'live';(data/'prompts').mkdir(parents=True)
        (data/'prompts/image-base.txt').write_text('Live prompt')
        archive=self.root/'live.zip';self.exporter.export(data,archive)
        check=self.importer.install(archive,root=root,check=True)
        self.assertIn('prompts/image-base.txt',check['changed'])
        self.assertTrue((config/'obsolete.txt').is_file())
        self.importer.install(archive,root=root)
        self.assertEqual((config/'prompts/image-base.txt').read_text(),'Live prompt')
        self.assertFalse((config/'obsolete.txt').exists())
        self.assertFalse(json.loads((config/'status.json').read_text())['liveVerified'])
        self.assertTrue(any((root/'.local/live-imports').iterdir()))

if __name__=='__main__':unittest.main()

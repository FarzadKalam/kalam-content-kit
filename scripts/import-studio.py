#!/usr/bin/env python3
"""Extract reviewed offline rules from an explicit, pinned Studio checkout.

Never imports the application, reads deployment secrets or contacts a provider.
Re-run only as a reviewed source update, not during an administrator's order.
"""
from __future__ import annotations
import argparse
import ast
import builtins
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import symtable

ROOT = Path(__file__).resolve().parents[1]

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def globals_used(source):
    table = symtable.symtable(source, '<extracted>', 'exec')
    names = set()
    def visit(t):
        names.update(s.get_name() for s in t.get_symbols() if s.is_referenced() and s.is_global() and not s.is_assigned())
        for child in t.get_children():
            visit(child)
    visit(table)
    return names

def extract(path, roots, overrides, header):
    source = path.read_text(encoding='utf-8-sig')
    tree = ast.parse(source)
    definitions = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            definitions[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name): definitions[target.id] = node
    selected, missing = {}, set()
    def require(name):
        if name in selected or name in overrides: return
        if name not in definitions:
            if name not in dir(builtins): missing.add(name)
            return
        node = definitions[name]
        selected[name] = node
        snippet = ast.get_source_segment(source, node)
        for dep in globals_used(snippet):
            if dep != name: require(dep)
    for name in roots: require(name)
    nodes = sorted({n.lineno: n for n in selected.values()}.values(), key=lambda n:n.lineno)
    body = '\n\n'.join(ast.get_source_segment(source, n) for n in nodes)
    # Reject accidentally expanding the slice to a service or external runner.
    forbidden = {'urllib', 'requests', 'subprocess', 'os', 'cgi', 'environ', 'socket', 'importlib'}
    if missing & forbidden: raise ValueError(f'Unsafe dependency expansion: {missing & forbidden}')
    allowed = {'re','json','hashlib','copy','HTTPStatus','Path','app','_VIDEO_PROMPT_RULES'}
    if missing - allowed: raise ValueError(f'Unresolved dependencies: {missing - allowed}')
    return header + '\n\n' + body + '\n', [
        {'name': name, 'sourceLine': n.lineno, 'sha256': hashlib.sha256(ast.get_source_segment(source,n).encode()).hexdigest()}
        for name,n in sorted(selected.items())]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('checkout', type=Path)
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()
    dest = ROOT/'vendor/studio'
    dest.mkdir(parents=True, exist_ok=True)
    overrides = {'image_model_settings','studio_text_prompt','image_base_prompt','image_non_news_prompt',
                 'image_style_prompt','image_template_prompt','video_asset_registry','video_scene_project'}
    gateway_roots = ['validate_request','validate_video_project','studio_image_prompt_sections',
        'studio_image_reference_contract','selected_studio_image_reference_assets',
        'selected_design_presenter_reference_assets','validate_studio_image_reference_budget',
        'reporter_prompt','parse_reporter_slide_deck','video_generation_contract',
        'TEXT_PROMPT_META','DEFAULT_TEMPLATE_PROMPTS','DEFAULT_IMAGE_BASE_PROMPT',
        'DEFAULT_IMAGE_NON_NEWS_PROMPT','DEFAULT_IMAGE_STYLE_PROMPT','IMAGE_MODELS','TEXT_MODELS',
        'VOICE_ENGINES','_GEMINI_PREBUILT_VOICES','DEFAULT_VOICE_BY_ENGINE','DEFAULT_VOICE_ENGINE',
        'DEFAULT_IMAGE_MODEL','DEFAULT_EDITORIAL_TEXT_MODEL','DEFAULT_REPLY_TEXT_MODEL',
        'DEFAULT_ANALYSIS_TEXT_MODEL','TRANSCRIPTION_MODELS','DEFAULT_TRANSCRIPTION_MODEL',
        'VIDEO_ASSET_ENTITIES','VIDEO_ASSET_PROFILE_OPTIONS']
    header = '"""Generated offline Studio rules. See sources.json. No service imports."""\nfrom __future__ import annotations\nimport re, json, hashlib, copy\nfrom http import HTTPStatus\nfrom pathlib import Path'
    gateway, records = extract(checkout/'deploy/kalam-design-gateway.app.py', gateway_roots, overrides, header)
    (dest/'gateway_rules.py').write_text(gateway, encoding='utf-8')
    worker, worker_records = extract(checkout/'deploy/kalam-design-worker.py',
        ['render_prompt','render_size','canvas_size'], {'app'}, header)
    (dest/'image_rules.py').write_text(worker, encoding='utf-8')
    shutil.copyfile(checkout/'deploy/kalam-video-prompt.py',dest/'video_rules.py')
    source_files = [str(p.relative_to(checkout)) for p in sorted(
        (checkout/'kalam-design-studio/apps/admin-miniapp/src').iterdir()) if p.suffix in {'.ts','.tsx'}]
    source_files += ['kalam-design-studio/contracts/design-request.schema.json',
                     'kalam-design-studio/contracts/video-project.schema.json']
    source_files += [str(p.relative_to(checkout)) for p in (checkout/'deploy/prompts').glob('*.txt')]
    snapshots = dest/'source'
    if snapshots.exists():shutil.rmtree(snapshots)
    for rel in source_files:
        target = snapshots/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(checkout/rel,target)
    # Include real Studio variants without replacing the newer motion identities.
    assets = checkout/'kalam-design-studio/apps/admin-miniapp/public'
    shutil.copytree(assets/'brand', ROOT/'assets/studio/brand',dirs_exist_ok=True)
    shutil.copytree(assets/'fonts', ROOT/'assets/studio/fonts',dirs_exist_ok=True)
    shutil.copyfile(checkout/'kalam-design-studio/apps/club-portal/public/brand/club-logo.png',ROOT/'assets/studio/club-logo.png')
    studio_assets=ROOT/'assets/studio'
    write_json(studio_assets/'provenance.json',{'source':'https://github.com/FarzadKalam/KalamStudio',
        'commit':commit,'files':{str(p.relative_to(studio_assets)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(studio_assets.rglob('*')) if p.is_file() and p.name!='provenance.json' and 'references' not in p.relative_to(studio_assets).parts}})
    write_json(dest/'sources.json', {'repository':'https://github.com/FarzadKalam/KalamStudio',
        'commit':commit,'extraction':'AST dependency slice; application is never imported',
        'gateway':records,'image':worker_records,
        'snapshots':[{'path':p,'sha256':hashlib.sha256((checkout/p).read_bytes()).hexdigest()} for p in source_files]})
    write_json(dest/'checksums.json',{name:hashlib.sha256((dest/name).read_bytes()).hexdigest()
               for name in ['gateway_rules.py','image_rules.py','video_rules.py']})
    print(json.dumps({'commit':commit,'gatewaySymbols':len(records),'imageSymbols':len(worker_records)}))

if __name__ == '__main__': main()

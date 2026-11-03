#!/usr/bin/env python3
"""Inspect or install an allowlisted live export, without contacting Studio."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('exporter',Path(__file__).with_name('export-studio-live.py'))
exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)

def inspect(archive_path):
    with zipfile.ZipFile(archive_path) as archive:
        infos=archive.infolist();names=[i.filename for i in infos]
        if len(names)!=len(set(names)) or sum(i.file_size for i in infos)>128*1024*1024:raise ValueError('Invalid or oversized archive')
        manifest=json.loads(archive.read('manifest.json'))
        if manifest.get('schemaVersion')!=1 or manifest.get('source')!='studio-live-filesystem':raise ValueError('Unknown live-export format')
        if set(names)!={'manifest.json',*manifest['files']}:raise ValueError('Unexpected archive entries')
        files={}
        for name,expected in manifest['files'].items():
            path=Path(name)
            if '\\' in name or path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe archive path')
            if name not in exporter.allowed_config_paths()|{'registry.json'} and not (name.startswith('assets/') and len(path.parts)==2 and path.suffix.lower() in {'.png','.jpg','.jpeg','.webp'}):raise ValueError('Entry outside allowlist')
            data=archive.read(name)
            if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Checksum mismatch')
            if name.endswith(('.txt','.json')) and re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{25,}|sk-(?:proj-|ant-)?[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)',data):raise ValueError('Possible credential in imported data')
            if name.startswith('settings/'):
                value=json.loads(data)
                if set(value)-set(exporter.SETTING_KEYS[path.stem]):raise ValueError('Unexpected setting/credential field')
            files[name]=data
        registry=json.loads(files['registry.json'])
        for asset in registry['assets']:
            if asset.get('scope')!='studio' or asset['kind'] not in exporter.ENTITIES or asset['entityId'] not in exporter.ENTITIES[asset['kind']]:raise ValueError('Private or invalid asset')
            if asset['path'] not in files or hashlib.sha256(files[asset['path']]).hexdigest()!=asset['sha256']:raise ValueError('Shared asset mismatch')
        return manifest,files

def install(archive_path,root=ROOT,check=False):
    manifest,files=inspect(archive_path);config=root/'config/studio'
    changed=[]
    for name,data in files.items():
        if name not in exporter.allowed_config_paths():continue
        target=config/name
        if not target.is_file() or target.read_bytes()!=data:changed.append(name)
    report={'changed':changed,'sharedAssets':len(json.loads(files['registry.json'])['assets']),
            'missingSharedAssets':manifest['missingSharedAssets'],'registryFound':manifest['registryFound']}
    if check:return report
    # The live release is a snapshot; deleting a live override restores the Git default.
    backup=root/'.local/live-imports'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True,exist_ok=False)
    if config.exists():shutil.copytree(config,backup/'config')
    references=root/'assets/studio/references'
    for destination in [config,references]:
        for ancestor in [destination,*destination.parents]:
            if ancestor==root.parent:break
            if ancestor.is_symlink():raise ValueError('Symlink in destination')
    if references.exists():shutil.copytree(references,backup/'references')
    defaults=root/'vendor/studio/git-defaults'
    if not defaults.exists():raise ValueError('Git default snapshot is missing')
    for path in config.rglob('*'):
        if path.is_symlink():raise ValueError('Symlink in destination')
    shutil.rmtree(config);shutil.copytree(defaults,config)
    for name,data in files.items():
        if name in exporter.allowed_config_paths():
            target=config/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    if references.exists():shutil.rmtree(references)
    references.mkdir(parents=True)
    for name,data in files.items():
        if name.startswith('assets/'):
            target=references/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    (references/'registry.json').write_bytes(files['registry.json'])
    status={'schemaVersion':1,'status':'live-imported','liveVerified':False,
        'importedAt':datetime.now(timezone.utc).isoformat(),'exportedAt':manifest['exportedAt'],
        'archiveSha256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        'missingSharedAssets':manifest['missingSharedAssets'],'registryFound':manifest['registryFound'],
        'parityReview':'pending; import alone is not an end-to-end comparison'}
    (config/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();print(json.dumps(install(args.archive,check=args.check),ensure_ascii=False,indent=2))

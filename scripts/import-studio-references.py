#!/usr/bin/env python3
"""Copy the approved local Studio reference packs, without running deployment code."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]


def literal(checkout, relative, name):
    source = checkout / relative
    for node in ast.parse(source.read_text(encoding='utf-8-sig')).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f'Missing approved metadata: {relative}:{name}')


def approved_files(checkout):
    packs = literal(checkout, 'deploy/register-approved-reference-assets-20260831.py', 'PACKS')
    for pack in packs:
        for name, profile in pack['files'].items():
            yield (f"output/reference-assets/{pack['source']}/{name}", pack['kind'], pack['entity'],
                   profile, name == pack['default'], 'deploy/register-approved-reference-assets-20260831.py')
    definitions = [
        ('deploy/register-tara-reference-assets.py', 'PROFILES', 'reference-assets/tara-20260831', 'presenter', 'tara'),
        ('deploy/register-studio-main-reference-assets.py', 'PROFILES', 'reference-assets/studio-main-20260830', 'location', 'studio_main'),
        ('deploy/register-newsroom-reference-assets.py', 'SOURCE_PROFILES', 'location-concepts/kalametaze-newsroom-v1', 'location', 'newsroom'),
        ('deploy/register-studio-2-reference-assets.py', 'SOURCE_PROFILES', 'location-concepts/kalametaze-studio-2-v1', 'location', 'studio_2'),
        ('deploy/promote-studio-2-final-assets.py', 'FINAL_PROFILES', 'location-concepts/kalametaze-studio-2-v2', 'location', 'studio_2'),
    ]
    for metadata, variable, directory, kind, entity in definitions:
        for index, (name, profile) in enumerate(literal(checkout, metadata, variable).items()):
            default = index == 0 and (entity != 'studio_2' or directory.endswith('-v2'))
            yield (f'output/{directory}/{name}', kind, entity, profile, default, metadata)


def transfer(checkout, root=ROOT):
    checkout = checkout.resolve()
    destination = root / 'assets/studio/references'
    records = []
    seen = set()
    sources = {}
    # Read and validate everything before writing; never import a registration script.
    for relative, kind, entity, profile, default, metadata in approved_files(checkout):
        source = (checkout / relative).resolve()
        if not source.is_relative_to(checkout) or not source.is_file():
            raise ValueError(f'Missing local reference: {relative}')
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        key = (kind, entity, digest)
        if key in seen:
            raise ValueError(f'Duplicate approved reference: {relative}')
        seen.add(key)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f'kalam-studio/{kind}/{entity}/{digest}'))
        target = f'{kind}/{entity}/{source.name}'
        records.append((data, {'assetId': asset_id, 'kind': kind, 'entityId': entity, 'scope': 'studio',
                              'isDefault': bool(default), 'profile': profile, 'path': target,
                              'filename': source.name, 'sha256': digest, 'sourcePath': relative,
                              'metadataSource': metadata}))
        sources[metadata] = hashlib.sha256((checkout / metadata).read_bytes()).hexdigest()
    expected = {str(p.relative_to(checkout)).replace('\\', '/')
                for directory in ['output/reference-assets', 'output/location-concepts']
                for p in (checkout / directory).rglob('*') if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}}
    actual = {r['sourcePath'] for _, r in records}
    if expected != actual:
        raise ValueError(f'Unmapped local reference files: {sorted(expected - actual)}')
    for data, item in records:
        target = destination / item['path']
        if target.exists() and target.read_bytes() != data:
            raise ValueError(f'Reference already exists with different bytes: {target}')
    for data, item in records:
        target = destination / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
    registry = {'version': 1, 'source': 'approved-local-studio-packs', 'metadataChecksums': sources,
                'assets': [r for _, r in records]}
    (destination / 'registry.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'assets': len(records), 'bytes': sum(len(data) for data, _ in records),
            'entities': sorted({r['entityId'] for _, r in records}), 'unmappedFiles': []}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    args = parser.parse_args()
    print(json.dumps(transfer(args.checkout), ensure_ascii=False, indent=2))

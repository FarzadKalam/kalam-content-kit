#!/usr/bin/env python3
"""Extract public News Seeker rules only; never import or copy its service/workflows."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def extract(checkout, output):
    gateway = checkout / 'deploy/kalam-design-gateway.app.py'
    source = gateway.read_text(encoding='utf-8-sig')
    definitions = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef):
            definitions[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name): definitions[target.id] = node
    names = ['NEWSROOM_SOURCES', 'NEWSROOM_SENSITIVE_TERMS', 'NEWSROOM_SHELL_TITLE_TERMS',
             'NEWSROOM_MAX_ARTICLE_AGE_SECONDS']
    def constant(node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            return constant(node.left) * constant(node.right)
        return ast.literal_eval(node)
    values = {name: constant(definitions[name].value) for name in names}
    rules = ['newsroom_clean_title', 'newsroom_published_timestamp', 'newsroom_valid_source_item',
             'newsroom_priority', 'newsroom_deduplicate_items']
    workflow_file = checkout / 'News Seeker.json'
    workflow = json.loads(workflow_file.read_text(encoding='utf-8-sig'))
    nodes = workflow['nodes']
    filter_code = next(n['parameters']['jsCode'] for n in nodes
                       if n.get('type', '').endswith('.code') and 'blacklistedDomains' in n['parameters'].get('jsCode', ''))
    def js_array(name):
        body = re.search(r'const\s+' + re.escape(name) + r'\s*=\s*\[(.*?)\]', filter_code, re.S).group(1)
        body = re.sub(r'//[^\n]*', '', body)
        return re.findall(r"'([^']+)'", body)
    prompt = next(n['parameters']['responses']['values'][0]['content'] for n in nodes
                  if n.get('type', '').endswith('.openAi'))
    result = {'schemaVersion': 1,
              'sources': [{'id': sid, 'label': label, 'domain': domain, 'scope': scope, 'credibility': credibility}
                          for sid, label, domain, scope, credibility in values['NEWSROOM_SOURCES']],
              'sensitiveTerms': values['NEWSROOM_SENSITIVE_TERMS'],
              'shellTitleTerms': values['NEWSROOM_SHELL_TITLE_TERMS'],
              'maxArticleAgeHours': values['NEWSROOM_MAX_ARTICLE_AGE_SECONDS'] // 3600,
              'legacyFilters': {name: js_array(name) for name in
                                ['blacklistedDomains', 'blacklistedKeywords', 'excludedLocations']},
              'legacyEditorialPrompt': prompt,
              'originalRuleText': {name: ast.get_source_segment(source, definitions[name]) for name in rules},
              'provenance': {'source': 'KalamN8N local News Seeker and newsroom pilot',
                             'gatewaySha256': hashlib.sha256(gateway.read_bytes()).hexdigest(),
                             'workflowSha256': hashlib.sha256(workflow_file.read_bytes()).hexdigest(),
                             'definitionHashes': {name: hashlib.sha256(ast.get_source_segment(source, definitions[name]).encode()).hexdigest()
                                                  for name in [*names, *rules]},
                             'excluded': ['credentials', 'personal Google Alerts feed', 'webhooks', 'Telegram recipients',
                                          'n8n runtime', 'automatic sends', 'server accounts']}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return {'file': str(output), 'sources': len(result['sources']), 'rules': len(rules)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'vendor/news-seeker/source-rules.json')
    args = parser.parse_args()
    print(json.dumps(extract(args.checkout, args.output), ensure_ascii=False))

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {ROOT,readJson} from './lib/paths.mjs';
import {python} from './lib/studio-runtime.mjs';
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const ui=readJson(path.join(ROOT,'catalog/studio-ui.json')),rules=readJson(path.join(ROOT,'catalog/studio.json'));
assert.deepEqual(ui.templates.map(t=>t.id).sort(),Object.keys(rules.imageTemplates).sort(),'Studio template mismatch');
assert.ok(ui.requestBuilders.length,'Missing original request builder');
const current=JSON.parse(python([path.join(ROOT,'scripts/studio.py'),'catalog']));
assert.deepEqual(current,rules,'Studio catalog is stale; run npm run catalog:studio');
assert.deepEqual(JSON.parse(python([path.join(ROOT,'scripts/public_data.py'),'catalog'])),readJson(path.join(ROOT,'catalog/public-data.json')),'Public data catalog is stale');
const source=readJson(path.join(ROOT,'vendor/studio/sources.json'));
for(const item of source.snapshots)assert.equal(sha(path.join(ROOT,'vendor/studio/source',item.path)),item.sha256,'Source snapshot changed: '+item.path);
const lock=readJson(path.join(ROOT,'vendor/studio/checksums.json'));
for(const [name,expected] of Object.entries(lock))assert.equal(sha(path.join(ROOT,'vendor/studio',name)),expected,'Extracted rule snapshot changed: '+name);
for(const [name,expected] of Object.entries(readJson(path.join(ROOT,'assets/studio/provenance.json')).files))assert.equal(sha(path.join(ROOT,'assets/studio',name)),expected,'Studio asset changed: '+name);
const references=path.join(ROOT,'assets/studio/references/registry.json');
if(fs.existsSync(references))for(const item of readJson(references).assets) {
  const relative=path.relative(path.dirname(references),path.resolve(path.dirname(references),item.path));
  assert.ok(relative&&!relative.startsWith('..')&&!path.isAbsolute(relative),'Unsafe shared reference path');
  assert.equal(sha(path.join(path.dirname(references),relative)),item.sha256,'Shared reference changed');
}
console.log('passed: Studio catalog, source snapshots, offline compiler and shared references');

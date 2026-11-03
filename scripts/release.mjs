import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import AdmZip from 'adm-zip';
import {ROOT,readJson} from './lib/paths.mjs';
import {sharedFiles} from './shared-files.mjs';
await import('./validate.mjs');
if(process.exitCode)throw new Error('Release validation failed');
const args=process.argv.slice(2),index=args.indexOf('--output');
const output=index>=0?path.resolve(args[index+1]):path.join(ROOT,'dist',`kalam-content-kit-${readJson(path.join(ROOT,'package.json')).version}.zip`);
if(fs.existsSync(output))throw new Error('Release output already exists; choose a new filename.');
const zip=new AdmZip(),files={};
for(const file of sharedFiles().filter(f=>f!=='RELEASE-MANIFEST.json')) {
  const full=path.join(ROOT,file);if(fs.lstatSync(full).isSymbolicLink())throw new Error('Symlink in release: '+file);
  const data=fs.readFileSync(full);files[file]=crypto.createHash('sha256').update(data).digest('hex');
  zip.addFile('kalam-content-kit/'+file,data);
}
const manifest={schemaVersion:1,version:readJson(path.join(ROOT,'package.json')).version,
  sources:readJson(path.join(ROOT,'config/sources.json')),studio:readJson(path.join(ROOT,'config/studio/status.json')),files};
zip.addFile('kalam-content-kit/RELEASE-MANIFEST.json',Buffer.from(JSON.stringify(manifest,null,2)+'\n'));
fs.mkdirSync(path.dirname(output),{recursive:true});zip.writeZip(output);
console.log(JSON.stringify({output,files:Object.keys(files).length,bytes:fs.statSync(output).size,sha256:crypto.createHash('sha256').update(fs.readFileSync(output)).digest('hex')},null,2));

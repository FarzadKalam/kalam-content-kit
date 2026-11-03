import fs from 'node:fs';
import path from 'node:path';
import {ROOT,readJson} from './lib/paths.mjs';
const entries=readJson(path.join(ROOT,'library/catalog.json'));
fs.writeFileSync(path.join(ROOT,'library/catalog-data.js'),'window.KALAM_CATALOG = '+JSON.stringify(entries,null,2)+';\n','utf8');
console.log(`Built searchable offline catalog: ${entries.length} entries`);

import path from 'node:path';
import {ROOT} from './lib/paths.mjs';
import {python} from './lib/studio-runtime.mjs';
try {process.stdout.write(python([path.join(ROOT,'scripts/public_data.py'),...process.argv.slice(2)]));}
catch(error){console.error(error.message);process.exitCode=1;}

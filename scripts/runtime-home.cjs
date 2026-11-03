// The CLI hard-codes some caches via os.homedir(). Scope those writes to this
// process only; do not change the user's HOME, USERPROFILE or global settings.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {syncBuiltinESMExports} = require('node:module');
if (process.env.KALAM_RUNTIME_HOME) {
  const runtimeHome = path.resolve(process.env.KALAM_RUNTIME_HOME);
  fs.mkdirSync(runtimeHome, {recursive:true});
  os.homedir = () => runtimeHome;
  syncBuiltinESMExports();
}

#!/usr/bin/env bash
set -euo pipefail
kit_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$kit_root"
case "${1:-}" in ''|--with-remotion) ;; *) echo 'Usage: bash scripts/setup.sh [--with-remotion]' >&2; exit 2 ;; esac
export TMPDIR="$kit_root/.cache/temp" TEMP="$kit_root/.cache/temp" TMP="$kit_root/.cache/temp"
export npm_config_cache="$kit_root/.cache/npm"
export HYPERFRAMES_SKIP_SKILLS=1 HYPERFRAMES_NO_UPDATE_CHECK=1 HYPERFRAMES_NO_TELEMETRY=1 DO_NOT_TRACK=1
export PUPPETEER_CACHE_DIR="$kit_root/.cache/browsers" PLAYWRIGHT_BROWSERS_PATH="$kit_root/.cache/browsers"
mkdir -p "$TMPDIR"
command -v node >/dev/null || { echo 'Node.js 22.12+ is required.' >&2; exit 1; }
node -e 'const [a,b]=process.versions.node.split(".").map(Number);if(a<22||(a===22&&b<12))process.exit(1)' || { echo 'Node.js 22.12+ is required.' >&2; exit 1; }
npm ci --no-audit --no-fund
if [[ "${1:-}" == --with-remotion ]]; then npm ci --prefix engines/remotion --no-audit --no-fund; fi
node scripts/kit.mjs doctor

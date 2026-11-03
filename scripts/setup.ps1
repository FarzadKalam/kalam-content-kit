param([switch]$WithRemotion)
$ErrorActionPreference = 'Stop'
$kitRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($kitRoot -match '^[Cc]:\\') { throw 'Clone this kit onto D: or another non-C drive first.' }
$cacheRoot = Join-Path $kitRoot '.cache'
$env:TEMP = Join-Path $cacheRoot 'temp'
$env:TMP = $env:TEMP
$env:npm_config_cache = Join-Path $cacheRoot 'npm'
$env:HYPERFRAMES_SKIP_SKILLS = '1'
$env:HYPERFRAMES_NO_UPDATE_CHECK = '1'
$env:HYPERFRAMES_NO_TELEMETRY = '1'
$env:DO_NOT_TRACK = '1'
$env:PUPPETEER_CACHE_DIR = Join-Path $cacheRoot 'browsers'
$env:PLAYWRIGHT_BROWSERS_PATH = $env:PUPPETEER_CACHE_DIR
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js 22.12+ is required. Install it on the tools drive, then retry.' }
$busyTools = Get-CimInstance Win32_Process -Filter "Name='esbuild.exe' OR Name='ffmpeg.exe'" | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith(($kitRoot + [IO.Path]::DirectorySeparatorChar), [StringComparison]::OrdinalIgnoreCase) }
if ($busyTools) { throw 'Close this kit''s active previews or renders before setup. A running tool would lock files during npm ci; no dependency files have been changed.' }
Push-Location $kitRoot
try {
  & npm.cmd ci --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw 'npm ci failed; see its error above.' }
  if ($WithRemotion) {
    & npm.cmd ci --prefix engines/remotion --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Optional Remotion installation failed.' }
  }
  & node scripts/kit.mjs doctor
  if ($LASTEXITCODE -ne 0) { throw 'Doctor found an incomplete prerequisite. No browser was downloaded automatically.' }
} finally { Pop-Location }

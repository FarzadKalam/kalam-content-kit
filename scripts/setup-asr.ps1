param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$kitRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($kitRoot -match '^[Cc]:\\') { throw 'Use a non-C drive.' }
$env:TEMP = Join-Path $kitRoot '.cache/temp'; $env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $kitRoot '.cache/pip'
$env:HF_HOME = Join-Path $kitRoot '.cache/huggingface'
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
$venvPath = Join-Path $kitRoot '.local/asr-venv'
& $Python -m venv $venvPath
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ with venv is required; no system Python was installed.' }
$venvPython = Join-Path $venvPath 'Scripts/python.exe'
& $venvPython -m pip install -r (Join-Path $PSScriptRoot 'requirements-asr.txt')
if ($LASTEXITCODE -ne 0) { throw 'Local ASR dependency installation failed.' }

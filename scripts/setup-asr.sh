#!/usr/bin/env bash
set -euo pipefail
kit_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export TMPDIR="$kit_root/.cache/temp" TEMP="$kit_root/.cache/temp" TMP="$kit_root/.cache/temp"
export PIP_CACHE_DIR="$kit_root/.cache/pip" HF_HOME="$kit_root/.cache/huggingface"
mkdir -p "$TMPDIR"
python_bin="${KALAM_PYTHON:-python3}"
"$python_bin" -m venv "$kit_root/.local/asr-venv"
"$kit_root/.local/asr-venv/bin/python" -m pip install -r "$kit_root/scripts/requirements-asr.txt"

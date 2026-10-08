#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
venv_dir="$project_dir/.venv-laya"

if [[ ! -x "$venv_dir/bin/laya-serve" ]]; then
  echo "Laya is not installed. Run ./setup-laya.sh first."
  exit 1
fi

device="${LAYA_DEVICE:-}"
if [[ -z "$device" ]]; then
  if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    device="mps"
  else
    device="cpu"
  fi
fi

export LAYA_HOST="${LAYA_HOST:-127.0.0.1}"
export LAYA_PORT="${LAYA_PORT:-8002}"
export LAYA_DEVICE="$device"
export LAYA_MODELS="${LAYA_MODELS:-typed-decisions}"
export LAYA_PRELOAD="${LAYA_PRELOAD:-1}"
export LAYA_MAX_LOADED="${LAYA_MAX_LOADED:-1}"

echo "Starting Laya typed-decisions on http://$LAYA_HOST:$LAYA_PORT using $LAYA_DEVICE"
echo "The first run downloads the selected model checkpoint."
exec "$venv_dir/bin/laya-serve"

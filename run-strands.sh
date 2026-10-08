#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
venv_dir="$project_dir/.venv-strands"
checkpoint="${STRANDS_DECIDER_MODEL:-StrandsAgents/strands-decider-2B-hobson-v19}"
device="${STRANDS_DECIDER_DEVICE:-mlx}"
port="${STRANDS_DECIDER_PORT:-8001}"

if [[ ! -x "$venv_dir/bin/strands-decider" ]]; then
  echo "Strands Decider is not installed. Run ./setup-strands.sh first."
  exit 1
fi

echo "Starting $checkpoint on http://127.0.0.1:$port using $device"
echo "The first run downloads the checkpoint and Qwen base weights."
exec "$venv_dir/bin/strands-decider" serve "$checkpoint" \
  --device "$device" \
  --port "$port"

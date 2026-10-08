#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
python_bin="${STRANDS_PYTHON:-python3.12}"
venv_dir="$project_dir/.venv-strands"
revision="${STRANDS_DECIDER_REVISION:-6d5dec6bd9c36fb63317803363a92ebcfcdfd207}"

if ! command -v "$python_bin" >/dev/null 2>&1; then
  echo "Strands Decider requires Python 3.10 or newer."
  echo "Set STRANDS_PYTHON to a compatible interpreter, for example:"
  echo "  STRANDS_PYTHON=/opt/homebrew/bin/python3.12 ./setup-strands.sh"
  exit 1
fi

"$python_bin" -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --upgrade pip
"$venv_dir/bin/python" -m pip install \
  "strands-decider[mlx] @ git+https://github.com/strands-labs/strands-decider.git@$revision"

echo
echo "Strands Decider is installed in $venv_dir"
echo "Start it with: ./run-strands.sh"

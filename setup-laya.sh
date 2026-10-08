#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
python_bin="${LAYA_PYTHON:-python3.12}"
venv_dir="$project_dir/.venv-laya"
laya_version="${LAYA_VERSION:-0.3.26}"

if ! command -v "$python_bin" >/dev/null 2>&1; then
  echo "Laya requires Python 3.10 or newer."
  echo "Set LAYA_PYTHON to a compatible interpreter, for example:"
  echo "  LAYA_PYTHON=/opt/homebrew/bin/python3.12 ./setup-laya.sh"
  exit 1
fi

"$python_bin" -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --upgrade pip
"$venv_dir/bin/python" -m pip install "laya[serve]==$laya_version"

echo
echo "Laya is installed in $venv_dir"
echo "Start it with: ./run-laya.sh"

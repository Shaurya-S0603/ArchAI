#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"
ARCHAI_PYTHON="${ARCHAI_PYTHON:-python3}"

if [ ! -x ".venv/bin/python" ]; then
  "$ARCHAI_PYTHON" -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi

exec .venv/bin/python app.py

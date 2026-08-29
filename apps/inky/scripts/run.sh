#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="$APP_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Inky is not set up. Run $APP_DIR/scripts/setup.sh first." >&2
  exit 1
fi

export PYTHONUNBUFFERED=1
exec "$PYTHON" "$APP_DIR/main.py"

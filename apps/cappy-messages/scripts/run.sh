#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cleanup() {
  kill "$SQUEEKBOARD_PID" "$HARDWARE_PID" "$WEB_PID" 2> /dev/null || true
  wait "$SQUEEKBOARD_PID" "$HARDWARE_PID" "$WEB_PID" 2> /dev/null || true
}
trap cleanup EXIT INT TERM

SQUEEKBOARD_LAYER=overlay squeekboard &
SQUEEKBOARD_PID=$!

python3 "$APP_DIR/hardware/main.py" &
HARDWARE_PID=$!

pnpm --filter cappy-messages start &
WEB_PID=$!

wait -n "$SQUEEKBOARD_PID" "$HARDWARE_PID" "$WEB_PID"

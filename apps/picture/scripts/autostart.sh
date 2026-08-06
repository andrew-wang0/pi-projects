#!/bin/bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$APP_DIR/media/logs"
LOG_FILE="$LOG_DIR/autostart.log"

mkdir -p "$LOG_DIR"
if [[ -f "$LOG_FILE" ]] && (($(stat -c %s "$LOG_FILE") > 1048576)); then
  mv -f "$LOG_FILE" "$LOG_FILE.previous"
fi

exec >> "$LOG_FILE" 2>&1

echo
echo "[$(date --iso-8601=seconds)] Picture autostart launcher started."

export HOME="${HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

display_ready=false
for ((attempt = 1; attempt <= 180; attempt++)); do
  if [[ -n "${WAYLAND_DISPLAY:-}" ]] \
    && [[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]]; then
    display_ready=true
    echo "Using Wayland display $WAYLAND_DISPLAY."
    break
  fi

  for socket in "$XDG_RUNTIME_DIR"/wayland-*; do
    if [[ -S "$socket" ]]; then
      export WAYLAND_DISPLAY="$(basename "$socket")"
      display_ready=true
      echo "Discovered Wayland display $WAYLAND_DISPLAY."
      break 2
    fi
  done

  if [[ -n "${DISPLAY:-}" ]]; then
    display_ready=true
    echo "Using X display $DISPLAY."
    break
  fi

  if [[ -S /tmp/.X11-unix/X0 ]]; then
    export DISPLAY=:0
    if [[ -f "$HOME/.Xauthority" ]]; then
      export XAUTHORITY="$HOME/.Xauthority"
    fi
    display_ready=true
    echo "Discovered X display $DISPLAY."
    break
  fi

  if ((attempt == 1)); then
    echo "Waiting up to 180 seconds for the graphical desktop..."
  fi
  sleep 1
done

if [[ "$display_ready" != true ]]; then
  echo "No graphical display was found. Enable desktop autologin and reboot."
  exit 1
fi

echo "Launching $APP_DIR/main.py"
exec "$APP_DIR/scripts/run.sh"

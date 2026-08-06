#!/bin/bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="picture.service"
LOG_FILE="$APP_DIR/media/logs/autostart.log"

section() {
  echo
  echo "===== $1 ====="
}

section "Service state"
systemctl is-enabled "$SERVICE_NAME" 2>&1 || true
systemctl is-active "$SERVICE_NAME" 2>&1 || true
systemctl status "$SERVICE_NAME" --no-pager --full 2>&1 || true

section "Current-boot service journal"
journalctl -u "$SERVICE_NAME" -b --no-pager -n 80 2>&1 || true

section "Picture launcher log"
if [[ -f "$LOG_FILE" ]]; then
  tail -n 120 "$LOG_FILE"
else
  echo "No launcher log exists at $LOG_FILE"
fi

section "Graphical display sockets"
echo "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-<unset>}"
echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<unset>}"
echo "DISPLAY=${DISPLAY:-<unset>}"
ls -l "/run/user/$(id -u)"/wayland-* /tmp/.X11-unix/X0 2>&1 || true

section "Python dependencies"
if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
  "$APP_DIR/.venv/bin/python" -c \
    "import av, gpiozero, lgpio, pygame, picamera2, PIL; print('All imports succeeded.')"
else
  echo "Missing $APP_DIR/.venv/bin/python; run scripts/setup.sh."
fi

section "Camera detection"
if command -v rpicam-hello > /dev/null 2>&1; then
  rpicam-hello --list-cameras 2>&1 || true
else
  echo "rpicam-hello is not installed."
fi

section "Power state"
if command -v vcgencmd > /dev/null 2>&1; then
  vcgencmd get_throttled 2>&1 || true
else
  echo "vcgencmd is not installed."
fi

section "User and groups"
id

echo
echo "To restart after fixing an issue:"
echo "  sudo systemctl restart $SERVICE_NAME"

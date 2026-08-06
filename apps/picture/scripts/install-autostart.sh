#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="picture.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"

if ((EUID == 0)); then
  echo "Run this script as the desktop user, without sudo." >&2
  echo "The script will request sudo only when installing the service." >&2
  exit 1
fi

if [[ "$APP_DIR" =~ [[:space:]] ]]; then
  echo "The project path cannot contain spaces for this systemd service:" >&2
  echo "  $APP_DIR" >&2
  exit 1
fi

USER_NAME="$(id -un)"
USER_ID="$(id -u)"
UNIT_FILE="$(mktemp)"

cleanup() {
  rm -f "$UNIT_FILE"
}
trap cleanup EXIT

if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  echo "Picture is not set up. Run $APP_DIR/scripts/setup.sh first." >&2
  exit 1
fi

chmod +x \
  "$APP_DIR/scripts/run.sh" \
  "$APP_DIR/scripts/autostart.sh" \
  "$APP_DIR/scripts/troubleshoot.sh"

cat > "$UNIT_FILE" << EOF
[Unit]
Description=Picture interactive camera display
Wants=display-manager.service
After=display-manager.service
StartLimitIntervalSec=0

[Service]
Type=simple
User=$USER_NAME
Environment="HOME=$HOME"
Environment="XDG_RUNTIME_DIR=/run/user/$USER_ID"
Environment="PYTHONUNBUFFERED=1"
WorkingDirectory=$APP_DIR
ExecStart=/bin/bash $APP_DIR/scripts/autostart.sh
Restart=on-failure
RestartSec=5
TimeoutStopSec=15

[Install]
WantedBy=graphical.target
EOF

sudo install -m 0644 "$UNIT_FILE" "$SERVICE_FILE"
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/picture.desktop"

sudo systemctl daemon-reload
if ! sudo systemd-analyze verify "$SERVICE_FILE"; then
  echo "The generated service failed validation:" >&2
  sudo systemctl cat "$SERVICE_NAME" >&2 || true
  exit 1
fi
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl reset-failed "$SERVICE_NAME" 2> /dev/null || true
sudo systemctl restart "$SERVICE_NAME"

echo "Installed and started $SERVICE_FILE"
echo "Status: sudo systemctl status $SERVICE_NAME"
echo "Log:    $APP_DIR/media/logs/autostart.log"
echo
echo "Desktop autologin must be enabled for the full-screen display."

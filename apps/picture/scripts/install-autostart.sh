#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="picture.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
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
WorkingDirectory="$APP_DIR"
ExecStart="$APP_DIR/scripts/autostart.sh"
Restart=on-failure
RestartSec=5
TimeoutStopSec=15

[Install]
WantedBy=graphical.target
EOF

sudo install -m 0644 "$UNIT_FILE" "$SERVICE_FILE"
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/picture.desktop"

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Installed and started $SERVICE_FILE"
echo "Status: sudo systemctl status $SERVICE_NAME"
echo "Log:    $APP_DIR/media/logs/autostart.log"
echo
echo "Desktop autologin must be enabled for the full-screen display."

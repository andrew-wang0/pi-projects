#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="inky.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"

if ((EUID == 0)); then
  echo "Run this script without sudo; it requests sudo when needed." >&2
  exit 1
fi

if [[ "$APP_DIR" =~ [[:space:]] ]]; then
  echo "The project path cannot contain spaces: $APP_DIR" >&2
  exit 1
fi

if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  echo "Inky is not set up. Run $APP_DIR/scripts/setup.sh first." >&2
  exit 1
fi

chmod +x "$APP_DIR/scripts/run.sh"

UNIT_FILE="$(mktemp)"
trap 'rm -f "$UNIT_FILE"' EXIT

cat > "$UNIT_FILE" << EOF
[Unit]
Description=Inky still camera
After=local-fs.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$(id -un)
Environment="HOME=$HOME"
Environment="PYTHONUNBUFFERED=1"
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/scripts/run.sh
Restart=on-failure
RestartSec=5
TimeoutStopSec=45

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl disable --now picture.service 2> /dev/null || true
sudo rm -f /etc/systemd/system/picture.service
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/picture.desktop"
sudo install -m 0644 "$UNIT_FILE" "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemd-analyze verify "$SERVICE_FILE"
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Installed and started $SERVICE_FILE"
echo "Status: sudo systemctl status $SERVICE_NAME --no-pager --full"
echo "Logs:   sudo journalctl -u $SERVICE_NAME -b --no-pager -n 100"

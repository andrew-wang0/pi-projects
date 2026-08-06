#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/picture.desktop"

mkdir -p "$AUTOSTART_DIR"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Picture
Comment=Interactive camera picture display
Exec="$APP_DIR/scripts/run.sh"
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Installed $DESKTOP_FILE"
echo "Picture will start after the next desktop login."

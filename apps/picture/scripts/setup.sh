#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

sudo apt-get update
sudo apt-get install -y \
  python3-av \
  python3-gpiozero \
  python3-lgpio \
  python3-picamera2 \
  python3-pil \
  python3-pygame \
  python3-venv

python3 -m venv --system-site-packages "$APP_DIR/.venv"

"$APP_DIR/.venv/bin/python" -c \
  "import av, gpiozero, lgpio, pygame, picamera2, PIL; print('Picture dependencies are ready.')"

echo "Setup complete. Start the app with: $APP_DIR/scripts/run.sh"

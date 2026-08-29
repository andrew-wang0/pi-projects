#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if ((EUID == 0)); then
  echo "Run this script without sudo; it requests sudo when needed." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y \
  python3-gpiod \
  python3-gpiozero \
  python3-lgpio \
  python3-numpy \
  python3-picamera2 \
  python3-pil \
  python3-smbus2 \
  python3-spidev \
  python3-venv

sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0
sudo usermod -aG gpio,i2c,spi "$USER"

BOOT_CONFIG=/boot/firmware/config.txt
if [[ ! -f "$BOOT_CONFIG" ]]; then
  BOOT_CONFIG=/boot/config.txt
fi

for setting in dtoverlay=i2c1 dtoverlay=i2c1-pi5 dtoverlay=spi0-0cs; do
  if ! grep -qxF "$setting" "$BOOT_CONFIG"; then
    echo "$setting" | sudo tee -a "$BOOT_CONFIG" > /dev/null
  fi
done

python3 -m venv --system-site-packages "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade inky
"$APP_DIR/.venv/bin/python" -c \
  "import gpiozero, inky, lgpio, picamera2, PIL; print('Inky dependencies are ready.')"

echo "Setup complete. Reboot before starting the app."

#!/bin/bash
set -euo pipefail

# URLs — update these before running
SQUEEKBOARD_REPO="https://github.com/YOUR_USERNAME/squeekboard-force-overlay"
CAPPY_MESSAGES_REPO="https://github.com/YOUR_USERNAME/pi-projects"
APP_PORT=3000
APP_DIR="$HOME/pi-projects"

echo "==> Installing system dependencies"
sudo apt-get update
sudo apt-get install -y \
  git curl \
  build-essential meson ninja-build \
  libgtk-3-dev libglib2.0-dev \
  libwayland-dev wayland-protocols \
  libpulse-dev \
  gettext

echo "==> Installing Node.js (via NodeSource)"
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt-get install -y nodejs

echo "==> Installing pnpm"
npm install -g pnpm

echo "==> Building and installing squeekboard-force-overlay"
git clone "$SQUEEKBOARD_REPO" /tmp/squeekboard-force-overlay
cd /tmp/squeekboard-force-overlay
# Install any remaining build deps declared in debian/control
sudo apt-get build-dep -y . 2> /dev/null || true
meson _build
cd _build
ninja
sudo ninja install
cd "$HOME"
rm -rf /tmp/squeekboard-force-overlay

echo "==> Enabling on-screen keyboard"
gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled true

echo "==> Cloning and building cappy-messages"
git clone "$CAPPY_MESSAGES_REPO" "$APP_DIR"
cd "$APP_DIR"
pnpm install
pnpm --filter cappy-messages build

echo "==> Creating systemd service for cappy-messages"
sudo tee /etc/systemd/system/cappy-messages.service > /dev/null << EOF
[Unit]
Description=cappy-messages Next.js server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$(which pnpm) --filter cappy-messages start -- --port $APP_PORT
Restart=on-failure
RestartSec=5
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cappy-messages
sudo systemctl start cappy-messages

echo "==> Setting up Chromium kiosk autostart"
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/chromium-kiosk.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Chromium Kiosk
Exec=chromium-browser \
    --kiosk \
    --ozone-platform=wayland \
    --disable-infobars \
    --noerrdialogs \
    --no-first-run \
    --disable-session-crashed-bubble \
    --app=http://localhost:$APP_PORT
EOF

echo ""
echo "Setup complete. Reboot to start the kiosk."
echo "  sudo reboot"

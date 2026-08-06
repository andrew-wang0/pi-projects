# Picture

`picture` is a full-screen interactive camera display for a Raspberry Pi 3A+,
the 7-inch DSI display, and a Camera Module 3 Wide. It continuously displays
the newest capture—showing a photo or looping a video—temporarily replaces it
with a live camera preview during capture, and records videos up to 30 seconds.

The app uses Pygame for the display, Picamera2 with the hardware H.264 encoder
and PyAV MP4 output for the camera, and gpiozero with the `lgpio` backend for
the controls. The default 720p, 24 FPS preview/recording stream is intentionally
conservative for the Pi 3A+'s memory.

## Default wiring

See [WIRING.md](WIRING.md) for the complete circuit, parts list, MOSFET pinout,
power-budget guidance, assembly procedure, and electrical safety checks.

All pin names below are BCM GPIO numbers, not physical header numbers.

- Mode switch: GPIO26, physical pin 37.
  - Connect the center/common leg to GPIO26.
  - Connect one outside leg to ground (physical pin 39).
  - Leave the other outside leg disconnected.
  - Grounded selects video; the open/pulled-up position selects photo.
- Capture button (BTN1): GPIO16, physical pin 36, to ground on physical pin 34.
- LED MOSFET gate: GPIO21, physical pin 40.
- Small pattern LED: GPIO12, physical pin 32, through a 330 ohm resistor to
  the LED anode; LED cathode to ground on physical pin 30.
- LED-strip on/off button (BTN2): GPIO17, physical pin 11, to ground
  (physical pin 9 is convenient).

A four-leg tactile button has two permanently connected legs on each side.
Use one leg from each opposite side, not two legs from the same side. The app
enables the Pi's internal pull-up resistors, so neither button needs an
external pull-up.

For a direct IRLB8721 low-side circuit:

1. Connect GPIO21 to the MOSFET gate through a 330 ohm resistor.
2. Add a 10 kohm resistor from gate to source so the strip stays off while the
   Pi boots.
3. Connect the MOSFET source to the boost converter's OUT- and Pi ground.
4. Connect the MOSFET drain to the LED strip's negative lead.
5. Connect the 12 V strip's positive lead to the boost converter's OUT+.
6. Connect Pi USB 5 V and ground to the converter's IN+ and IN-.

GPIO21 only drives the MOSFET gate; never power an LED strip from a GPIO pin.
The 5 V input current is higher than the strip's 12 V current because of the
step-up conversion. Confirm the Pi supply, USB path, and converter can handle
the calculated full-brightness load without undervoltage. This no-fuse build
requires a converter with documented current limiting, short-circuit
protection, and thermal shutdown.

## Capture behavior

Photo mode:

- BTN1 immediately replaces the saved picture with the live preview.
- The small pattern LED runs three slow flashes (0.5 seconds off, 0.5 seconds
  on), followed by three fast flashes during the fourth second.
- The final fast flash stays on while the photo is captured.
- Additional BTN1 presses during the sequence or capture are discarded.
- The new photo replaces the previous photo on screen.

Video mode:

- BTN1 immediately displays the live preview and flashes the small pattern LED
  three times over one second.
- Recording then starts with the small pattern LED on.
- A blinking red dot appears in the preview's top-right corner.
- BTN1 stops an active recording. Recording also stops automatically at
  30 seconds.
- At the 30-second limit, recording ends before the small pattern LED flashes
  three times over one second to confirm the automatic stop.
- Presses during the one-second pre-recording flash sequence are discarded.
- Every completed video is saved and then looped full-screen continuously. A
  manually stopped video starts looping immediately; an automatically stopped
  video starts after the ending small-LED flashes.
- Pressing BTN1 during a video loop ends playback and starts a new photo or
  video capture according to the current mode-switch position.

BTN2 directly toggles the LED strip on or off. The selected strip state remains
steady during photo countdowns, video countdowns, recording, ending flashes,
and playback. Only the small pattern LED performs the slow and fast capture
animations. It always follows the requested pattern and is unaffected by BTN2.
The strip starts on when the app starts.

The mode switch is read when BTN1 requests a new capture. Moving it during an
active photo or video capture does not interrupt that capture.

## Install

Use 64-bit Raspberry Pi OS with Desktop. Picamera2 should be installed from
Raspberry Pi OS packages, not from PyPI, because it depends on the system
libcamera installation.

```bash
cd /path/to/pi-projects/apps/picture
./scripts/setup.sh
./scripts/run.sh
```

The setup script installs Picamera2, PyAV, Pygame, gpiozero, `lgpio`, and a
virtual environment that can see those system packages.

Press Escape or `q` on an attached keyboard to exit during setup. Normal
appliance use only requires the physical controls.

### Start automatically

The full-screen app needs a graphical desktop. Enable desktop autologin:

```bash
sudo raspi-config
```

Choose **System Options → Boot / Auto Login → Desktop Autologin**. Then install
the boot service. These commands can be run over SSH:

```bash
cd /path/to/pi-projects/apps/picture
./scripts/install-autostart.sh
sudo reboot
```

The installer creates and enables `/etc/systemd/system/picture.service`. Its
launcher waits for either the Wayland or X11 desktop before starting Pygame,
restarts the app after failures, and writes a persistent startup log. It also
removes the older desktop-entry launcher so two copies cannot start.

Re-run the installer after moving the project to a different path.

### Troubleshoot autostart

Run the diagnostic script over SSH:

```bash
cd /path/to/pi-projects/apps/picture
./scripts/troubleshoot.sh
```

The most useful individual commands are:

```bash
sudo systemctl status picture.service --no-pager --full
sudo journalctl -u picture.service -b --no-pager -n 100
tail -n 120 media/logs/autostart.log
sudo systemctl restart picture.service
```

Common results:

- `No graphical display was found`: enable desktop autologin and confirm the
  Pi boots to the desktop, not the console.
- Missing `.venv/bin/python` or import errors: rerun `./scripts/setup.sh`.
- `pygame.error` involving the video device: verify a desktop session exists
  for the same user that ran `install-autostart.sh`.
- GPIO permission errors: run `id` and confirm the user belongs to `gpio`.
- Camera busy or unavailable: stop other camera programs and run
  `rpicam-hello --list-cameras`.
- Reboots, display flicker, or camera errors when the strip turns on: inspect
  `vcgencmd get_throttled` and correct the power budget.

## Saved media

By default the app creates:

- `media/photos/picture_YYYYMMDD_HHMMSS_microseconds.jpg`
- `media/videos/video_YYYYMMDD_HHMMSS_microseconds.mp4`

The `media` directory is ignored by Git. On every boot, the app compares photo
and video filename timestamps. It displays the newest photo or continuously
loops the newest video, whichever capture is newer. Captures are never
intentionally overwritten: every photo and video filename contains its capture
timestamp down to microseconds. Set `PICTURE_MEDIA_DIR` to keep files on a
different disk or mounted directory.

The combined size of `media/photos` and `media/videos` is limited to 48 GB by
default. Once usage is at or above the configured limit, BTN1 cannot start
another photo or video. The display briefly shows **Storage full**, then
returns to the current photo or resumes the current video loop. Existing media
is never automatically deleted. After files are manually removed, the next
BTN1 press recalculates usage and capture becomes available again.

## Configuration

The defaults can be changed through environment variables before running the
app:

- `MODE_SWITCH_PIN=26`
- `CAPTURE_BUTTON_PIN=16`
- `LED_OUTPUT_PIN=21`
- `PATTERN_LED_PIN=12`
- `LED_TOGGLE_BUTTON_PIN=17`
- `VIDEO_MODE_WHEN_GROUNDED=true`
- `LED_ACTIVE_HIGH=true`
- `PATTERN_LED_ACTIVE_HIGH=true`
- `BUTTON_BOUNCE_SECONDS=0.08`
- `CAMERA_PREVIEW_WIDTH=1280`
- `CAMERA_PREVIEW_HEIGHT=720`
- `CAMERA_STILL_WIDTH=2304`
- `CAMERA_STILL_HEIGHT=1296`
- `CAMERA_FRAME_RATE=24`
- `CAMERA_HFLIP=false`
- `CAMERA_VFLIP=false`
- `VIDEO_BITRATE=8000000`
- `VIDEO_MAX_SECONDS=30` (values above 30 are clamped to 30)
- `DISPLAY_FRAME_RATE=30`
- `PICTURE_MEDIA_DIR=/path/to/media`
- `MEDIA_MAX_GB=48`
- `STORAGE_FULL_MESSAGE_SECONDS=2`

All GPIO settings use BCM numbering. Preview and still dimensions must be
positive even numbers.

## Hardware checks

Before starting the app, these commands should complete without camera or
undervoltage errors:

```bash
rpicam-hello -t 5000
vcgencmd get_throttled
```

If GPIO access fails, verify that the desktop user belongs to the `gpio` group.
If the display is blank only when autostarted, confirm desktop autologin is
enabled; this app is graphical and must start inside the desktop session.

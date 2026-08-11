# Picture

`picture` is a full-screen interactive camera display for a Raspberry Pi 3A+,
the 7-inch DSI display, and a Camera Module 3 Wide. It continuously displays
the newest capture—showing a photo or looping a video—temporarily replaces it
with a live camera preview during capture, and records videos up to 20 seconds.

The app uses Pygame for the display, Picamera2 with the hardware H.264 encoder
and PyAV MP4 output for the camera, and gpiozero with the `lgpio` backend for
the controls. The default 720p, 24 FPS preview/recording stream is intentionally
conservative for the Pi 3A+'s memory.

## Default wiring

See [WIRING.md](WIRING.md) for the complete circuit, parts list, MOSFET
controller wiring, power-budget guidance, assembly procedure, and electrical
safety checks.

All pin names below are BCM GPIO numbers, not physical header numbers.

- Capture button: GPIO17, physical pin 11, to ground on physical pin 9.
- LED-strip PWM: GPIO18, physical pin 12, to the MOSFET controller's
  3.3 V-compatible PWM/input terminal.
- Small pattern LED: GPIO12, physical pin 32, through a 330 ohm resistor to
  the LED anode; LED cathode to ground on physical pin 30.

A four-leg tactile button has two permanently connected legs on each side.
Use one leg from each opposite side, not two legs from the same side. The app
enables the Pi's internal pull-up resistor, so the button needs no external
pull-up.

For a MOSFET controller with a PWM/input terminal:

1. Confirm that the controller accepts 3.3 V PWM logic and can switch the
   strip's full current.
2. Connect GPIO18 (physical pin 12) to the controller PWM/input terminal.
3. Connect Pi ground to the controller signal ground so PWM has a common
   reference.
4. Connect the converter and strip to the controller's power/load terminals
   exactly as specified by the controller manufacturer.

GPIO18 supplies only a PWM control signal; never power an LED strip from GPIO.
The 5 V input current is higher than the strip's 12 V current because of the
step-up conversion. Confirm the Pi supply, USB path, and converter can handle
the calculated full-brightness load without undervoltage. This no-fuse build
requires a converter with documented current limiting, short-circuit
protection, and thermal shutdown.

## Capture behavior

Photo capture:

- Press and release BTN1 in under one second. Nothing starts on the press edge;
  releasing the button immediately turns on the small pattern LED, starts the
  camera, and begins the photo process. The live preview replaces the saved
  media as soon as the first camera frame is available.
- The small pattern LED turns on first, then runs three slow flashes (0.5
  seconds on, 0.5 seconds off), followed by three fast flashes during the
  fourth second.
- At the end of the flashes, the small pattern LED turns on. The app lets
  illuminated camera frames flow for 0.2 seconds before capturing, so it does
  not save the buffered frame from just before the LED turned on.
- The exact final frame already shown in the live preview is frozen, saved as
  the JPEG, and left on screen. The camera does not switch modes between
  preview and capture, eliminating the pause and framing/time mismatch.
- The small pattern LED turns off immediately after the photo is saved.
- Additional BTN1 presses during the sequence or capture are discarded.
- The new photo replaces the previous photo on screen.

Video capture:

- Press and hold BTN1. As soon as the hold reaches one second, the small pattern
  LED turns on, the camera starts, and the recording process begins; BTN1 does
  not need to be released first. The preview appears as soon as the first frame
  is available.
- The small pattern LED turns on first and flashes three times over one second.
- Recording then starts with the small pattern LED on.
- A solid red dot in the preview's top-right corner flashes for half a second
  on and half a second off.
- Releasing the initial long hold does not stop recording. After that release,
  press and release BTN1 again to stop; stopping occurs on the release edge.
  Recording also stops automatically at 20 seconds.
- At the 20-second limit, recording ends before the small pattern LED flashes
  three times over one second to confirm the automatic stop.
- If the initial hold is released during the one-second pre-recording flashes,
  that release is ignored as intended. A subsequent press and release requests
  a stop, including during the remaining pre-recording flashes.
- Every completed video is saved and then looped full-screen continuously. A
  manually stopped video starts looping immediately; an automatically stopped
  video starts after the ending small-LED flashes.
- Looping keeps the MP4 container and decoder open and seeks back to the first
  keyframe, avoiding repeated file and codec initialization.
- The small pattern LED turns off after recording and remains off during video
  playback.
- During a video loop, a short press and release starts a photo process; a
  one-second hold starts a video process.

The LED strip has no physical on/off button. Software drives it at the
configured peak PWM brightness. For visual testing, it currently fades from
bright to off and back to bright every five seconds; only the small pattern
LED performs the capture animations. The strip turns off when the app exits.

The camera is stopped while a saved photo is displayed or a saved video loops,
then restarted only when a capture process begins. This avoids leaving an
unconsumed camera stream running long enough for the Pi camera frontend to time
out.

## Install

Use 64-bit Raspberry Pi OS with Desktop. Picamera2 should be installed from
Raspberry Pi OS packages, not from PyPI, because it depends on the system
libcamera installation.

```bash
cd /path/to/pi-projects/apps/picture
./scripts/setup.sh
./scripts/run.sh
```

The setup script installs Picamera2, PyAV, Pillow, Pygame, gpiozero, `lgpio`,
and a virtual environment that can see those system packages.

Press Escape or `q` on an attached keyboard to exit during setup. Normal
appliance use only requires the capture button.

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

- `media/picture_YYYYMMDD_HHMMSS_microseconds.jpg`
- `media/video_YYYYMMDD_HHMMSS_microseconds.mp4`

The `media` directory is ignored by Git. On every boot, the app compares photo
and video filename timestamps. It displays the newest photo or continuously
loops the newest video, whichever capture is newer. Captures are never
intentionally overwritten: every photo and video filename contains its capture
timestamp down to microseconds. Set `PICTURE_MEDIA_DIR` to keep files on a
different disk or mounted directory.

The combined size of timestamped photos and videos in `media` is limited to
48 GB by default. Once usage is at or above the configured limit, BTN1 cannot
start another photo or video. The display briefly shows **Storage full**, then
returns to the current photo or resumes the current video loop. Existing media
is never automatically deleted. After files are manually removed, the next
short-release or long-hold capture attempt recalculates usage and becomes
available again.

Older captures inside legacy `media/photos` or `media/videos` folders are still
discovered, displayed, and included in the storage limit.

## Configuration

The defaults can be changed through environment variables before running the
app:

- `CAPTURE_BUTTON_PIN=17`
- `LED_PWM_PIN=18`
- `LED_PWM_ACTIVE_HIGH=true`
- `LED_PWM_FREQUENCY=20000`
- `LED_STRIP_BRIGHTNESS=1.0` (from `0.0` off to `1.0` full brightness)
- `PATTERN_LED_PIN=12`
- `PATTERN_LED_ACTIVE_HIGH=true`
- `BUTTON_BOUNCE_SECONDS=0.08`
- `CAPTURE_HOLD_SECONDS=1.0`
- `CAMERA_PREVIEW_WIDTH=1280`
- `CAMERA_PREVIEW_HEIGHT=720`
- `CAMERA_SENSOR_WIDTH=2304`
- `CAMERA_SENSOR_HEIGHT=1296`
- `CAMERA_FRAME_RATE=24`
- `PHOTO_LIGHT_SETTLE_SECONDS=0.2`
- `CAMERA_HFLIP=true`
- `CAMERA_VFLIP=false`
- `VIDEO_BITRATE=8000000`
- `VIDEO_MAX_SECONDS=20` (values above 20 are clamped to 20)
- `DISPLAY_FRAME_RATE=30`
- `PICTURE_MEDIA_DIR=/path/to/media`
- `MEDIA_MAX_GB=48`
- `STORAGE_FULL_MESSAGE_SECONDS=2`

All GPIO settings use BCM numbering. Preview and sensor dimensions must be
positive even numbers. Photos use the preview dimensions because they are
saved from the exact frame shown on screen.

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

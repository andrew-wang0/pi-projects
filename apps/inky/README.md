# Inky

`inky` takes still photos with a Raspberry Pi Camera Module and displays them
on an Inky Impression 7.3 Spectra (800×480).

## Behavior

1. Pressing the capture button turns on the small signal LED.
2. Releasing the same accepted press captures one photo.
3. The signal LED turns off as soon as capture completes.
4. The photo is cropped to 800×480, stored as a PNG, and shown on the display.

Button activity is ignored from the start of capture through the end of the
display refresh. A press that begins during this time remains invalid even if
the button is released after the refresh finishes.

The big show light is independent of capture state. It starts at
`LIGHT_BRIGHTNESS`, does not react to the button, and can be switched or dimmed
through Home Assistant.

The app has no video, preview, countdown, or graphical-desktop dependency.

## Wiring

All GPIO values are BCM numbers.

- Capture button: GPIO24 (physical pin 18) to ground (physical pin 20).
- Signal LED: GPIO13 (physical pin 33), through a series resistor and LED, to
  ground (physical pin 34).
- Show-light PWM: GPIO18 (physical pin 12) to the MOSFET controller input.
- MOSFET controller signal ground: physical pin 14.

GPIO24 is also connected to the Inky Impression's onboard D button, so either
that button or the external button will trigger capture. Do not use GPIO16 on
physical pin 36 as an output; Inky's onboard C button can short it to ground.

The MOSFET controller must accept 3.3 V PWM logic. Never connect LED power or
the LED load directly to a GPIO pin.

## Install

```bash
cd /path/to/pi-projects/apps/inky
./scripts/setup.sh
cp .env.example .env
# Edit .env with the Home Assistant MQTT broker credentials.
chmod 600 .env
sudo reboot
./scripts/install-autostart.sh
```

The installer creates and starts `inky.service`. It also disables and removes
the obsolete `picture.service`.

Useful service commands:

```bash
sudo systemctl restart inky.service
sudo systemctl status inky.service --no-pager --full
sudo journalctl -u inky.service -b --no-pager -n 100
```

## Home Assistant

Install the Mosquitto broker add-on and MQTT integration in Home Assistant,
then create a broker user for Inky. Put its address and credentials in `.env`;
this file is ignored by Git. If `MQTT_HOST` is unset, MQTT is disabled and
local capture continues normally.

Inky publishes retained MQTT Discovery configurations. Home Assistant creates:

- `light.inky_show_light` for independent on/off and brightness control.
- `image.inky_latest_photo` for the latest captured 800×480 PNG.
- `sensor.inky_last_photo` for the latest photo's filename.

The device publishes online/offline availability and its actual light state.
MQTT light commands remain active while the e-paper display refreshes.

Home Assistant does not retain previous MQTT image payloads automatically. To
copy each received capture into its local media directory, create `/media/inky`
on the Home Assistant host and add this automation:

```yaml
alias: Archive Inky photos
triggers:
  - trigger: state
    entity_id: sensor.inky_last_photo
    not_from:
      - unknown
      - unavailable
    not_to:
      - unknown
      - unavailable
actions:
  - delay: "00:00:01"
  - action: image.snapshot
    target:
      entity_id: image.inky_latest_photo
    data:
      filename: "/media/inky/{{ trigger.to_state.state }}"
mode: queued
```

This archives photos received while MQTT is connected; the complete originals
always remain in Inky's local `images/` directory. The Home Assistant copies
appear under **Media → Local Media → inky**. For a gallery directly on a
dashboard, install Media Explorer Card through HACS and use:

```yaml
type: custom:media-explorer-card
startPath: media-source://media_source/local/inky
```

## Image conversion

The camera produces a 2304×1296 RGB image. Picamera2 exposes its `RGB888`
NumPy buffer in BGR byte order, so `camera.py` swaps the red and blue channels
when constructing the Pillow RGB image.

`display.py` then uses `ImageOps.fit` with Lanczos resampling. This
center-crops the camera's 16:9 image to the display's 5:3 aspect ratio and
resizes it to exactly 800×480 without stretching it.

Every fitted image is stored losslessly in `images/` as
`inky_YYYYMMDD_HHMMSS_microseconds.png`. Set `INKY_IMAGE_DIR` to use another
directory. The saved PNG is the full-color 800×480 source supplied to Inky,
before panel palette conversion.

The fitted RGB image is passed to the official Inky library's
`set_image(..., saturation=0.5)`. Its Spectra driver quantizes and
Floyd–Steinberg dithers the image into the panel's six native colors: black,
white, yellow, red, blue, and green. `show()` sends that buffer to the display
and blocks until the refresh is complete.

## Configuration

- `INKY_IMAGE_DIR=/path/to/images`
- `CAPTURE_BUTTON_PIN=24`
- `SIGNAL_LED_PIN=13`
- `SIGNAL_LED_ACTIVE_HIGH=true`
- `LIGHT_PWM_PIN=18`
- `LIGHT_ACTIVE_HIGH=true`
- `LIGHT_BRIGHTNESS=1.0`
- `LIGHT_PWM_FREQUENCY=5000`
- `BUTTON_BOUNCE_SECONDS=0.08`
- `CAMERA_WIDTH=2304`
- `CAMERA_HEIGHT=1296`
- `CAMERA_HFLIP=true`
- `CAMERA_VFLIP=false`
- `INKY_SATURATION=0.5`
- `MQTT_HOST=homeassistant.local` (unset disables MQTT)
- `MQTT_PORT=1883`
- `MQTT_USERNAME=inky`
- `MQTT_PASSWORD=...`
- `MQTT_DEVICE_ID=inky`
- `MQTT_TOPIC_PREFIX=inky`
- `MQTT_DISCOVERY_PREFIX=homeassistant`

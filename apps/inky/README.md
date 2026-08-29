# Inky

`inky` takes still photos with a Raspberry Pi Camera Module and displays them
on an Inky Impression 7.3 Spectra (800×480).

## Behavior

1. Pressing the capture button turns on both signal LEDs: the separately wired
   LED and the Pimoroni board's shine-through LED.
2. Releasing the same accepted press captures one photo.
3. Both signal LEDs turn off as soon as capture completes.
4. The big light breathes from minimum to maximum and back every two seconds
   while the photo is processed, stored, published, and shown on the display.
5. The big light returns to its latest Home Assistant setting.

Button activity is ignored from the start of capture through the end of the
display refresh. A press that begins during this time remains invalid even if
the button is released after the refresh finishes.

The big show light starts at `LIGHT_BRIGHTNESS` and can be switched or dimmed
through Home Assistant. Its temporary breathing pattern reports processing
activity after capture without changing its Home Assistant state.

The app has no video, preview, countdown, or graphical-desktop dependency.

## Wiring

All GPIO values are BCM numbers.

- Capture button: GPIO24 (physical pin 18) to ground (physical pin 20).
- External signal LED: GPIO12 (physical pin 32), through a series resistor and
  LED, to ground (physical pin 34).
- The Pimoroni board's built-in shine-through LED uses GPIO13 and mirrors the
  external signal LED automatically.
- Show-light PWM: GPIO18 (physical pin 12) to the MOSFET controller input.
- MOSFET controller signal ground: physical pin 14.

GPIO24 is also connected to the Inky Impression's onboard D button, so either
that button or the external button will trigger capture. Do not use GPIO16 on
physical pin 36 as an output; Inky's onboard C button can short it to ground.

GPIO12 also reaches the Inky board's EEPROM write-protect input. The app drives
it explicitly and only reads the EEPROM. The external LED still requires a
series resistor; never connect an LED directly between GPIO and ground.

The MOSFET controller must accept 3.3 V PWM logic. Never connect the show-light
power or load directly to a GPIO pin.

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
local capture continues normally. Capture and display also continue if the
broker is unreachable, credentials are wrong, or the MQTT package is missing.

Inky publishes retained MQTT Discovery configurations. Home Assistant creates:

- `light.inky_show_light`, named **Light**, for independent on/off and
  brightness control.
- `image.inky_latest_photo` for the latest captured 800×480 PNG.
- `image.inky_archive_queue`, a diagnostic entity used for reliable historical
  photo transfer.

The device publishes online/offline availability and its actual light state.
MQTT light commands remain active while the e-paper display refreshes.

Light commands fade over one second by default, including ordinary dashboard
toggle and brightness changes. Home Assistant can override that duration per
command. For example, this action fades the big LED to 70% over two seconds:

```yaml
action: light.turn_on
target:
  entity_id: light.inky_show_light
data:
  brightness_pct: 70
  transition: 2
```

Use `light.turn_off` with the same `transition` field for a smooth fade out.

PWM stays at a fixed frequency. To avoid unstable ultra-short pulses, nonzero
brightness is remapped: Home Assistant 1% uses 25% physical duty, then scales
linearly to 100% duty at 100% brightness. Off remains 0%. Change
`LIGHT_MINIMUM_DUTY` if the hardware needs a different lower bound.

Home Assistant does not retain previous MQTT image payloads automatically. To
copy each received capture into its local media directory, create `/media/inky`
on the Home Assistant host and add this automation:

```yaml
alias: Archive Inky photos
triggers:
  - trigger: mqtt
    topic: inky/photo/transfer
conditions:
  - condition: template
    value_template: "{{ trigger.payload | length == 64 }}"
variables:
  filename: "{{ as_timestamp(now()) | int }}.png"
actions:
  - delay: "00:00:01"
  - action: image.snapshot
    target:
      entity_id: image.inky_archive_queue
    data:
      filename: "/media/inky/{{ filename }}"
  - action: mqtt.publish
    data:
      topic: inky/photo/ack
      payload: "{{ trigger.payload }}"
mode: queued
```

Every PNG remains on Inky until it is deleted manually. Inky appends capture
order to `images/.mqtt-photo-queue` and records acknowledged files atomically in
`images/.mqtt-synced.json`. After MQTT reconnects, it publishes every
unacknowledged PNG in capture order. It waits for the automation to save and
acknowledge each image before sending the next. The first run of this backup
logic publishes all existing PNGs.

To replay the complete local archive again, stop the service, remove the
cursor, and restart:

```bash
sudo systemctl stop inky.service
rm images/.mqtt-synced.json
sudo systemctl start inky.service
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
`UNIX_TIMESTAMP.png`, with no prefix. Set `INKY_IMAGE_DIR` to use another
directory. The saved PNG is the full-color 800×480 source supplied to Inky
before panel palette conversion.

The fitted RGB image is passed to the official Inky library's
`set_image(..., saturation=0.5)`. Its Spectra driver quantizes and
Floyd–Steinberg dithers the image into the panel's six native colors: black,
white, yellow, red, blue, and green. `show()` sends that buffer to the display
and blocks until the refresh is complete.

## Configuration

- `INKY_IMAGE_DIR=/path/to/images`
- `CAPTURE_BUTTON_PIN=24`
- `SIGNAL_LED_PIN=12`
- `SIGNAL_LED_ACTIVE_HIGH=true`
- `LIGHT_PWM_PIN=18`
- `LIGHT_ACTIVE_HIGH=true`
- `LIGHT_BRIGHTNESS=1.0`
- `LIGHT_PWM_FREQUENCY=1000`
- `LIGHT_MINIMUM_DUTY=0.25`
- `LIGHT_TRANSITION_SECONDS=1.0`
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

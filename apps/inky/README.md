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

The big show light is independent of capture state. It remains at
`LIGHT_BRIGHTNESS` while the app runs and does not react to the button.

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

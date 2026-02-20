#!/usr/bin/env python3
from pathlib import Path
from signal import pause
import colorsys
import threading
import time

from gpiozero import MotionSensor, Device
from gpiozero.pins.lgpio import LGPIOFactory
from rpi_ws281x import Color, PixelStrip

Device.pin_factory = LGPIOFactory()

# PIR pin
PIR_PIN = 14

# Backlight sysfs path
BL_DIR = Path("/sys/class/backlight/10-0045")
BRIGHTNESS = BL_DIR / "brightness"
MAX_BRIGHTNESS = int((BL_DIR / "max_brightness").read_text().strip())

# Turn backlight off 15 seconds after motion stops
OFF_DELAY_SECONDS = 15.0

# NeoPixel strip config
NEOPIXEL_PIN = 5
NEOPIXEL_COUNT = 10
NEOPIXEL_FREQ_HZ = 800000
NEOPIXEL_DMA = 10
NEOPIXEL_BRIGHTNESS = 128
NEOPIXEL_INVERT = False
NEOPIXEL_CHANNEL = 0
RAINBOW_STEP_DELAY_SECONDS = 0.03

pir = MotionSensor(PIR_PIN)
strip = PixelStrip(
    NEOPIXEL_COUNT,
    NEOPIXEL_PIN,
    NEOPIXEL_FREQ_HZ,
    NEOPIXEL_DMA,
    NEOPIXEL_INVERT,
    NEOPIXEL_BRIGHTNESS,
    NEOPIXEL_CHANNEL,
)

_off_timer = None
_timer_lock = threading.Lock()
_display_active = threading.Event()
_shutdown = threading.Event()
_anim_lock = threading.Lock()


def _clear_pixels() -> None:
    with _anim_lock:
        for i in range(NEOPIXEL_COUNT):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()


def _show_rainbow_frame(offset: int) -> None:
    with _anim_lock:
        for i in range(NEOPIXEL_COUNT):
            hue = ((i * 256 // NEOPIXEL_COUNT) + offset) % 256
            r, g, b = colorsys.hsv_to_rgb(hue / 255.0, 1.0, 1.0)
            strip.setPixelColor(i, Color(int(r * 255), int(g * 255), int(b * 255)))
        strip.show()


def _neopixel_loop() -> None:
    offset = 0
    pixels_off = False
    while not _shutdown.is_set():
        if _display_active.is_set():
            _show_rainbow_frame(offset)
            offset = (offset + 1) % 256
            pixels_off = False
            time.sleep(RAINBOW_STEP_DELAY_SECONDS)
            continue
        if not pixels_off:
            _clear_pixels()
            pixels_off = True
        time.sleep(0.05)


def set_brightness(x: int) -> None:
    x = max(0, min(MAX_BRIGHTNESS, int(x)))
    BRIGHTNESS.write_text(f"{x}\n")


def _cancel_off_timer() -> None:
    global _off_timer
    with _timer_lock:
        if _off_timer and _off_timer.is_alive():
            _off_timer.cancel()
        _off_timer = None


def _schedule_backlight_off() -> None:
    global _off_timer
    with _timer_lock:
        if _off_timer and _off_timer.is_alive():
            _off_timer.cancel()
        _off_timer = threading.Timer(OFF_DELAY_SECONDS, _timeout_display_off)
        _off_timer.daemon = True
        _off_timer.start()


def _timeout_display_off() -> None:
    set_brightness(0)
    _display_active.clear()


def on_motion() -> None:
    _cancel_off_timer()
    set_brightness(MAX_BRIGHTNESS)
    _display_active.set()


def on_no_motion() -> None:
    _schedule_backlight_off()


def main() -> None:
    strip.begin()
    _clear_pixels()
    set_brightness(0)
    _display_active.clear()

    anim_thread = threading.Thread(target=_neopixel_loop, daemon=True)
    anim_thread.start()

    pir.when_motion = on_motion
    pir.when_no_motion = on_no_motion

    try:
        pause()
    finally:
        _shutdown.set()
        _display_active.clear()
        _cancel_off_timer()
        _clear_pixels()
        set_brightness(0)


if __name__ == "__main__":
    main()

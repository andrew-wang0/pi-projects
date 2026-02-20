#!/usr/bin/env python3
from pathlib import Path
from signal import pause
import threading

from gpiozero import MotionSensor, Device
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()

# PIR pin
PIR_PIN = 14

# Backlight sysfs path
BL_DIR = Path("/sys/class/backlight/10-0045")
BRIGHTNESS = BL_DIR / "brightness"
MAX_BRIGHTNESS = int((BL_DIR / "max_brightness").read_text().strip())

# Turn backlight off 15 seconds after motion stops
OFF_DELAY_SECONDS = 15.0

pir = MotionSensor(PIR_PIN)
_off_timer = None
_timer_lock = threading.Lock()


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
        _off_timer = threading.Timer(OFF_DELAY_SECONDS, set_brightness, args=(0,))
        _off_timer.daemon = True
        _off_timer.start()


def on_motion() -> None:
    _cancel_off_timer()
    set_brightness(MAX_BRIGHTNESS)


def on_no_motion() -> None:
    _schedule_backlight_off()


def main() -> None:
    set_brightness(0)

    pir.when_motion = on_motion
    pir.when_no_motion = on_no_motion

    pause()


if __name__ == "__main__":
    main()

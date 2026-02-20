#!/usr/bin/env python3
from signal import pause
import threading
import time

from gpiozero import Device, MotionSensor
from gpiozero.pins.lgpio import LGPIOFactory

from background_sync import BackgroundSyncClient
from backgrounds import DEFAULT_BACKGROUND_ID, pattern_for_background
from backlight import BacklightController
from config import (
    ANIMATION_FRAME_DELAY_SECONDS,
    BACKLIGHT,
    NEOPIXEL,
    OFF_DELAY_SECONDS,
    PIR_FLASH_PULSES,
    PIR_FLASH_SECONDS,
    PIR_PIN,
    read_backlight_max_brightness,
)
from neopixel_driver import build_pixel_driver
from patterns import PatternRenderer
from state import RuntimeState

Device.pin_factory = LGPIOFactory()


def main() -> None:
    pir = MotionSensor(PIR_PIN)
    state = RuntimeState(initial_background_id=DEFAULT_BACKGROUND_ID)

    backlight = BacklightController(
        brightness_file=BACKLIGHT.brightness_file,
        max_brightness=read_backlight_max_brightness(),
    )
    pixels = build_pixel_driver()
    patterns = PatternRenderer(pixel_count=NEOPIXEL.count)

    background_sync = BackgroundSyncClient(
        on_background_id=state.set_background_id,
        shutdown_event=state.shutdown,
    )

    off_timer: threading.Timer | None = None
    off_timer_lock = threading.Lock()

    def cancel_off_timer() -> None:
        nonlocal off_timer
        with off_timer_lock:
            if off_timer and off_timer.is_alive():
                off_timer.cancel()
            off_timer = None

    def timeout_display_off() -> None:
        backlight.turn_off()
        state.display_active.clear()

    def schedule_backlight_off() -> None:
        nonlocal off_timer
        with off_timer_lock:
            if off_timer and off_timer.is_alive():
                off_timer.cancel()
            off_timer = threading.Timer(OFF_DELAY_SECONDS, timeout_display_off)
            off_timer.daemon = True
            off_timer.start()

    def animation_loop() -> None:
        frame = 0
        pixels_off = False

        while not state.shutdown.is_set():
            if state.display_active.is_set():
                pattern = pattern_for_background(state.get_background_id())
                flash_remaining = state.pir_flash_remaining(time.monotonic())
                colors = patterns.render(
                    pattern,
                    frame,
                    flash_remaining,
                    PIR_FLASH_SECONDS,
                    PIR_FLASH_PULSES,
                )

                pixels.show(colors)
                frame += 1
                pixels_off = False
                time.sleep(ANIMATION_FRAME_DELAY_SECONDS)
                continue

            if not pixels_off:
                pixels.clear()
                pixels_off = True

            time.sleep(0.05)

    def on_motion() -> None:
        cancel_off_timer()
        backlight.turn_on()
        state.display_active.set()
        state.trigger_pir_flash(PIR_FLASH_SECONDS)

    def on_no_motion() -> None:
        schedule_backlight_off()

    pixels.begin()
    pixels.clear()
    backlight.turn_off()
    state.display_active.clear()

    animation_thread = threading.Thread(target=animation_loop, daemon=True)
    background_thread = threading.Thread(target=background_sync.run_forever, daemon=True)

    animation_thread.start()
    background_thread.start()

    pir.when_motion = on_motion
    pir.when_no_motion = on_no_motion

    try:
        pause()
    finally:
        state.shutdown.set()
        state.display_active.clear()
        cancel_off_timer()

        animation_thread.join(timeout=1.0)
        background_thread.join(timeout=1.0)

        pixels.clear()
        backlight.turn_off()


if __name__ == "__main__":
    main()

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto
import threading
import time

from gpiozero import Button, Device, DigitalOutputDevice, PWMOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

from config import PinConfig


class ControlEvent(Enum):
    CAPTURE_PRESSED = auto()
    CAPTURE_HELD = auto()
    CAPTURE_RELEASED = auto()


class LedStripController:
    """Drives the software-controlled strip PWM and pattern indicator."""

    def __init__(self, pins: PinConfig) -> None:
        self._strip_peak_brightness = pins.led_strip_brightness
        self._strip_output = PWMOutputDevice(
            pins.led_pwm_output,
            active_high=pins.led_pwm_active_high,
            initial_value=self._strip_peak_brightness,
            frequency=pins.led_pwm_frequency,
        )
        self._pattern_output = DigitalOutputDevice(
            pins.pattern_led_output,
            active_high=pins.pattern_led_active_high,
            initial_value=False,
        )
        self._cycle_stop = threading.Event()
        self._cycle_thread = threading.Thread(
            target=self._run_visual_test_cycle,
            name="led-strip-visual-test",
            daemon=True,
        )
        self._cycle_thread.start()

    def _run_visual_test_cycle(self) -> None:
        """Temporarily fade bright -> off -> bright every five seconds."""
        cycle_seconds = 5.0
        half_cycle = cycle_seconds / 2
        started_at = time.monotonic()

        while not self._cycle_stop.is_set():
            phase = (time.monotonic() - started_at) % cycle_seconds
            if phase < half_cycle:
                level = 1.0 - (phase / half_cycle)
            else:
                level = (phase - half_cycle) / half_cycle
            self._strip_output.value = level * self._strip_peak_brightness
            self._cycle_stop.wait(0.02)

    def set_strip_brightness(self, brightness: float) -> None:
        if not 0.0 <= brightness <= 1.0:
            raise ValueError("Strip brightness must be between 0.0 and 1.0")
        self._strip_output.value = brightness

    def request(self, on: bool) -> None:
        self._pattern_output.value = on

    def close(self) -> None:
        self._cycle_stop.set()
        self._cycle_thread.join()
        self._strip_output.off()
        self._pattern_output.off()
        self._strip_output.close()
        self._pattern_output.close()


class PhysicalControls:
    def __init__(
        self,
        pins: PinConfig,
        on_event: Callable[[ControlEvent], None],
    ) -> None:
        self._capture_button = Button(
            pins.capture_button,
            pull_up=True,
            bounce_time=pins.button_bounce_seconds,
            hold_time=pins.capture_hold_seconds,
            hold_repeat=False,
        )
        self._capture_button.when_pressed = lambda: on_event(ControlEvent.CAPTURE_PRESSED)
        self._capture_button.when_held = lambda: on_event(ControlEvent.CAPTURE_HELD)
        self._capture_button.when_released = lambda: on_event(
            ControlEvent.CAPTURE_RELEASED
        )

    def close(self) -> None:
        self._capture_button.close()


def use_lgpio() -> None:
    Device.pin_factory = LGPIOFactory()

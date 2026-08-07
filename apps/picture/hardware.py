from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto
import threading

from gpiozero import Button, Device, DigitalOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

from config import PinConfig


class ControlEvent(Enum):
    CAPTURE_PRESSED = auto()
    CAPTURE_HELD = auto()
    CAPTURE_RELEASED = auto()
    LED_TOGGLE_PRESSED = auto()


class LedStripController:
    """Toggles the strip and independently drives the pattern indicator."""

    def __init__(self, pins: PinConfig) -> None:
        self._strip_output = DigitalOutputDevice(
            pins.led_output,
            active_high=pins.led_active_high,
            initial_value=False,
        )
        self._pattern_output = DigitalOutputDevice(
            pins.pattern_led_output,
            active_high=pins.pattern_led_active_high,
            initial_value=False,
        )
        self._strip_on = True
        self._requested_on = False
        self._lock = threading.Lock()

    @property
    def strip_on(self) -> bool:
        with self._lock:
            return self._strip_on

    def toggle_strip(self) -> None:
        with self._lock:
            self._strip_on = not self._strip_on
            self._apply()

    def request(self, on: bool) -> None:
        with self._lock:
            self._requested_on = on
            self._apply()

    def _apply(self) -> None:
        self._strip_output.value = self._strip_on
        self._pattern_output.value = self._requested_on

    def close(self) -> None:
        with self._lock:
            self._strip_on = False
            self._requested_on = False
            self._apply()
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
        self._led_toggle_button = Button(
            pins.led_toggle_button,
            pull_up=True,
            bounce_time=pins.button_bounce_seconds,
        )
        self._capture_button.when_pressed = lambda: on_event(ControlEvent.CAPTURE_PRESSED)
        self._capture_button.when_held = lambda: on_event(ControlEvent.CAPTURE_HELD)
        self._capture_button.when_released = lambda: on_event(
            ControlEvent.CAPTURE_RELEASED
        )
        self._led_toggle_button.when_pressed = lambda: on_event(
            ControlEvent.LED_TOGGLE_PRESSED
        )

    def close(self) -> None:
        self._capture_button.close()
        self._led_toggle_button.close()


def use_lgpio() -> None:
    Device.pin_factory = LGPIOFactory()

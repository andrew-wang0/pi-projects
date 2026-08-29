from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto
import threading

from gpiozero import Button, Device, DigitalOutputDevice, PWMOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

from config import Config


class ButtonEvent(Enum):
    PRESSED = auto()
    RELEASED = auto()


class CaptureButton:
    def __init__(
        self,
        config: Config,
        on_event: Callable[[ButtonEvent], None],
    ) -> None:
        self._on_event = on_event
        self._enabled = True
        self._accepted_press = False
        self._blocked_until_release = False
        self._lock = threading.Lock()
        self._button = Button(
            config.capture_button_pin,
            pull_up=True,
            bounce_time=config.button_bounce_seconds,
        )
        self._button.when_pressed = self._pressed
        self._button.when_released = self._released

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = enabled
            self._accepted_press = False
            self._blocked_until_release = enabled and self._button.is_pressed

    def _pressed(self) -> None:
        with self._lock:
            self._accepted_press = (
                self._enabled
                and not self._blocked_until_release
                and self._button.is_pressed
            )
            if self._accepted_press:
                self._on_event(ButtonEvent.PRESSED)

    def _released(self) -> None:
        with self._lock:
            accepted = (
                self._enabled
                and not self._blocked_until_release
                and self._accepted_press
            )
            self._accepted_press = False
            self._blocked_until_release = False
            if accepted:
                self._on_event(ButtonEvent.RELEASED)

    def close(self) -> None:
        self.set_enabled(False)
        self._button.close()


class CaptureLights:
    def __init__(self, config: Config) -> None:
        self._brightness = config.light_brightness
        self._show_light = PWMOutputDevice(
            config.light_pwm_pin,
            active_high=config.light_active_high,
            initial_value=0.0,
            frequency=config.light_pwm_frequency,
        )
        self._signal_led = DigitalOutputDevice(
            config.signal_led_pin,
            active_high=config.signal_led_active_high,
            initial_value=False,
        )

    def on(self) -> None:
        self._show_light.value = self._brightness
        self._signal_led.on()

    def off(self) -> None:
        self._show_light.off()
        self._signal_led.off()

    def close(self) -> None:
        self.off()
        self._show_light.close()
        self._signal_led.close()


def use_lgpio() -> None:
    Device.pin_factory = LGPIOFactory()

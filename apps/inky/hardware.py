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


class SignalLed:
    def __init__(self, config: Config) -> None:
        self._output = DigitalOutputDevice(
            config.signal_led_pin,
            active_high=config.signal_led_active_high,
            initial_value=False,
        )

    def on(self) -> None:
        self._output.on()

    def off(self) -> None:
        self._output.off()

    def close(self) -> None:
        self.off()
        self._output.close()


class ShowLight:
    def __init__(self, config: Config) -> None:
        self._brightness = config.light_brightness
        self._on = self._brightness > 0
        self._lock = threading.Lock()
        self._output = PWMOutputDevice(
            config.light_pwm_pin,
            active_high=config.light_active_high,
            initial_value=self._brightness,
            frequency=config.light_pwm_frequency,
        )

    def set(self, *, on: bool | None = None, brightness: float | None = None) -> None:
        with self._lock:
            if brightness is not None:
                if not 0.0 <= brightness <= 1.0:
                    raise ValueError("Brightness must be between 0.0 and 1.0")
                self._brightness = brightness
                if on is None:
                    self._on = brightness > 0
            if on is not None:
                self._on = on
            self._output.value = self._brightness if self._on else 0.0

    def state(self) -> tuple[bool, float]:
        with self._lock:
            return self._on, self._brightness

    def close(self) -> None:
        self.set(on=False)
        self._output.close()


def use_lgpio() -> None:
    Device.pin_factory = LGPIOFactory()

from __future__ import annotations

from collections.abc import Callable
from enum import Enum, auto
import threading
import time

from gpiozero import Button, Device, DigitalOutputDevice, PWMOutputDevice
from gpiozero.pins.lgpio import LGPIOFactory

from config import Config, INKY_LED_PIN


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
        external = DigitalOutputDevice(
            config.signal_led_pin,
            active_high=config.signal_led_active_high,
            initial_value=False,
        )
        try:
            onboard = DigitalOutputDevice(
                INKY_LED_PIN,
                active_high=True,
                initial_value=False,
            )
        except Exception:
            external.close()
            raise
        self._outputs = (external, onboard)

    def on(self) -> None:
        for output in self._outputs:
            output.on()

    def off(self) -> None:
        for output in self._outputs:
            output.off()

    def close(self) -> None:
        self.off()
        for output in self._outputs:
            output.close()


class ShowLight:
    def __init__(self, config: Config) -> None:
        self._brightness = config.light_brightness
        self._on = self._brightness > 0
        self._minimum_duty = config.light_minimum_duty
        self._lock = threading.Lock()
        self._output = PWMOutputDevice(
            config.light_pwm_pin,
            active_high=config.light_active_high,
            initial_value=self._physical_level(),
            frequency=config.light_pwm_frequency,
        )

        self._transition_id = 0

    def set(
        self,
        *,
        on: bool | None = None,
        brightness: float | None = None,
        transition: float = 0,
    ) -> None:
        if transition < 0:
            raise ValueError("Transition cannot be negative")

        with self._lock:
            self._transition_id += 1
            transition_id = self._transition_id
            start = self._output.value
            if brightness is not None:
                if not 0.0 <= brightness <= 1.0:
                    raise ValueError("Brightness must be between 0.0 and 1.0")
                self._brightness = brightness
                if on is None:
                    self._on = brightness > 0
            if on is not None:
                self._on = on
            target = self._physical_level()
            if transition == 0:
                self._output.value = target
                return

        threading.Thread(
            target=self._fade,
            args=(transition_id, start, target, transition),
            daemon=True,
        ).start()

    def _fade(
        self,
        transition_id: int,
        start: float,
        target: float,
        duration: float,
    ) -> None:
        steps = max(1, int(duration * 50))
        started = time.monotonic()
        for step in range(1, steps + 1):
            deadline = started + duration * step / steps
            time.sleep(max(0, deadline - time.monotonic()))
            with self._lock:
                if transition_id != self._transition_id:
                    return
                self._output.value = start + (target - start) * step / steps

    def _physical_level(self) -> float:
        if not self._on or self._brightness <= 0:
            return 0.0
        scaled = max(0.0, (self._brightness - 0.01) / 0.99)
        return self._minimum_duty + scaled * (1.0 - self._minimum_duty)

    def state(self) -> tuple[bool, float]:
        with self._lock:
            return self._on, self._brightness

    def close(self) -> None:
        self.set(on=False)
        self._output.close()


def use_lgpio() -> None:
    Device.pin_factory = LGPIOFactory()

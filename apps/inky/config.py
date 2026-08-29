from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


INKY_DISPLAY_PINS = {2, 3, 8, 9, 10, 11, 12, 17, 22, 27}
INKY_BUTTON_PINS = {5, 6, 16, 24}


def _integer(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _number(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def _boolean(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


@dataclass(frozen=True)
class Config:
    image_dir: Path
    capture_button_pin: int
    signal_led_pin: int
    signal_led_active_high: bool
    light_pwm_pin: int
    light_active_high: bool
    light_brightness: float
    light_pwm_frequency: float
    button_bounce_seconds: float
    camera_size: tuple[int, int]
    camera_hflip: bool
    camera_vflip: bool
    inky_saturation: float


def load_config() -> Config:
    app_dir = Path(__file__).resolve().parent
    config = Config(
        image_dir=Path(os.getenv("INKY_IMAGE_DIR", app_dir / "images")).expanduser(),
        capture_button_pin=_integer("CAPTURE_BUTTON_PIN", 24),
        signal_led_pin=_integer("SIGNAL_LED_PIN", 13),
        signal_led_active_high=_boolean("SIGNAL_LED_ACTIVE_HIGH", True),
        light_pwm_pin=_integer("LIGHT_PWM_PIN", 18),
        light_active_high=_boolean("LIGHT_ACTIVE_HIGH", True),
        light_brightness=_number("LIGHT_BRIGHTNESS", 1.0),
        light_pwm_frequency=_number("LIGHT_PWM_FREQUENCY", 5_000.0),
        button_bounce_seconds=_number("BUTTON_BOUNCE_SECONDS", 0.08),
        camera_size=(
            _integer("CAMERA_WIDTH", 2304),
            _integer("CAMERA_HEIGHT", 1296),
        ),
        camera_hflip=_boolean("CAMERA_HFLIP", True),
        camera_vflip=_boolean("CAMERA_VFLIP", False),
        inky_saturation=_number("INKY_SATURATION", 0.5),
    )

    pins = {
        config.capture_button_pin,
        config.signal_led_pin,
        config.light_pwm_pin,
    }
    if len(pins) != 3:
        raise ValueError("The button, signal LED, and show light need different pins")
    if any(pin < 0 or pin > 27 for pin in pins):
        raise ValueError("GPIO pins must be BCM numbers from 0 through 27")
    if pins & INKY_DISPLAY_PINS:
        raise ValueError("Configured GPIO conflicts with the Inky Impression")
    if {config.signal_led_pin, config.light_pwm_pin} & INKY_BUTTON_PINS:
        raise ValueError("An output cannot use an Inky Impression button pin")
    if not 0.0 <= config.light_brightness <= 1.0:
        raise ValueError("LIGHT_BRIGHTNESS must be between 0.0 and 1.0")
    if not 0.1 <= config.light_pwm_frequency <= 10_000:
        raise ValueError("LIGHT_PWM_FREQUENCY must be between 0.1 and 10000")
    if config.button_bounce_seconds < 0:
        raise ValueError("BUTTON_BOUNCE_SECONDS cannot be negative")
    if any(value <= 0 or value % 2 for value in config.camera_size):
        raise ValueError("Camera dimensions must be positive even numbers")
    if not 0.0 <= config.inky_saturation <= 1.0:
        raise ValueError("INKY_SATURATION must be between 0.0 and 1.0")

    return config

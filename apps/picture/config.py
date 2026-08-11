from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value, got {value!r}")


@dataclass(frozen=True)
class PinConfig:
    capture_button: int
    led_pwm_output: int
    pattern_led_output: int
    led_pwm_active_high: bool
    led_pwm_frequency: float
    led_strip_brightness: float
    pattern_led_active_high: bool
    button_bounce_seconds: float
    capture_hold_seconds: float


@dataclass(frozen=True)
class CameraConfig:
    preview_size: tuple[int, int]
    sensor_size: tuple[int, int]
    frame_rate: int
    photo_light_settle_seconds: float
    video_bitrate: int
    video_max_seconds: float
    horizontal_flip: bool
    vertical_flip: bool


@dataclass(frozen=True)
class StorageConfig:
    media_dir: Path
    max_bytes: int
    full_message_seconds: float


@dataclass(frozen=True)
class AppConfig:
    pins: PinConfig
    camera: CameraConfig
    storage: StorageConfig
    display_frame_rate: int


def load_config() -> AppConfig:
    app_dir = Path(__file__).resolve().parent
    media_dir = Path(os.getenv("PICTURE_MEDIA_DIR", app_dir / "media")).expanduser()

    pins = PinConfig(
        capture_button=_int_env("CAPTURE_BUTTON_PIN", 17),
        led_pwm_output=_int_env("LED_PWM_PIN", 18),
        pattern_led_output=_int_env("PATTERN_LED_PIN", 12),
        led_pwm_active_high=_bool_env("LED_PWM_ACTIVE_HIGH", True),
        led_pwm_frequency=_float_env("LED_PWM_FREQUENCY", 2_000.0),
        led_strip_brightness=_float_env("LED_STRIP_BRIGHTNESS", 1.0),
        pattern_led_active_high=_bool_env("PATTERN_LED_ACTIVE_HIGH", True),
        button_bounce_seconds=_float_env("BUTTON_BOUNCE_SECONDS", 0.08),
        capture_hold_seconds=_float_env("CAPTURE_HOLD_SECONDS", 1.0),
    )
    camera = CameraConfig(
        preview_size=(
            _int_env("CAMERA_PREVIEW_WIDTH", 1280),
            _int_env("CAMERA_PREVIEW_HEIGHT", 720),
        ),
        sensor_size=(
            _int_env(
                "CAMERA_SENSOR_WIDTH",
                _int_env("CAMERA_STILL_WIDTH", 2304),
            ),
            _int_env(
                "CAMERA_SENSOR_HEIGHT",
                _int_env("CAMERA_STILL_HEIGHT", 1296),
            ),
        ),
        frame_rate=_int_env("CAMERA_FRAME_RATE", 24),
        photo_light_settle_seconds=_float_env(
            "PHOTO_LIGHT_SETTLE_SECONDS",
            0.2,
        ),
        video_bitrate=_int_env("VIDEO_BITRATE", 8_000_000),
        video_max_seconds=min(_float_env("VIDEO_MAX_SECONDS", 20.0), 20.0),
        horizontal_flip=_bool_env("CAMERA_HFLIP", True),
        vertical_flip=_bool_env("CAMERA_VFLIP", False),
    )
    storage = StorageConfig(
        media_dir=media_dir,
        max_bytes=int(_float_env("MEDIA_MAX_GB", 48.0) * 1_000_000_000),
        full_message_seconds=_float_env("STORAGE_FULL_MESSAGE_SECONDS", 2.0),
    )
    config = AppConfig(
        pins=pins,
        camera=camera,
        storage=storage,
        display_frame_rate=_int_env("DISPLAY_FRAME_RATE", 30),
    )
    _validate(config)
    return config


def _validate(config: AppConfig) -> None:
    pin_values = (
        config.pins.capture_button,
        config.pins.led_pwm_output,
        config.pins.pattern_led_output,
    )
    if len(set(pin_values)) != len(pin_values):
        raise ValueError("All GPIO assignments must use different BCM pins")
    if any(pin < 0 or pin > 27 for pin in pin_values):
        raise ValueError("GPIO assignments must be BCM pin numbers from 0 through 27")
    if config.pins.button_bounce_seconds < 0:
        raise ValueError("BUTTON_BOUNCE_SECONDS cannot be negative")
    if config.pins.capture_hold_seconds <= 0:
        raise ValueError("CAPTURE_HOLD_SECONDS must be positive")
    if config.pins.led_pwm_frequency <= 0:
        raise ValueError("LED_PWM_FREQUENCY must be positive")
    if config.pins.led_pwm_frequency > 10_000:
        raise ValueError("LED_PWM_FREQUENCY cannot exceed lgpio's 10000 Hz limit")
    if not 0.0 <= config.pins.led_strip_brightness <= 1.0:
        raise ValueError("LED_STRIP_BRIGHTNESS must be between 0.0 and 1.0")

    for name, size in (
        ("preview", config.camera.preview_size),
        ("sensor", config.camera.sensor_size),
    ):
        if any(dimension <= 0 or dimension % 2 for dimension in size):
            raise ValueError(f"The camera {name} dimensions must be positive even numbers")

    if config.camera.frame_rate <= 0:
        raise ValueError("CAMERA_FRAME_RATE must be positive")
    if config.camera.photo_light_settle_seconds <= 0:
        raise ValueError("PHOTO_LIGHT_SETTLE_SECONDS must be positive")
    if config.camera.video_bitrate <= 0:
        raise ValueError("VIDEO_BITRATE must be positive")
    if config.camera.video_max_seconds <= 0:
        raise ValueError("VIDEO_MAX_SECONDS must be positive")
    if config.display_frame_rate <= 0:
        raise ValueError("DISPLAY_FRAME_RATE must be positive")
    if config.storage.max_bytes <= 0:
        raise ValueError("MEDIA_MAX_GB must be positive")
    if config.storage.full_message_seconds <= 0:
        raise ValueError("STORAGE_FULL_MESSAGE_SECONDS must be positive")

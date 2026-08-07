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
    mode_switch: int
    capture_button: int
    led_output: int
    pattern_led_output: int
    led_toggle_button: int
    led_active_high: bool
    pattern_led_active_high: bool
    video_mode_when_grounded: bool
    button_bounce_seconds: float


@dataclass(frozen=True)
class CameraConfig:
    preview_size: tuple[int, int]
    sensor_size: tuple[int, int]
    frame_rate: int
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
        mode_switch=_int_env("MODE_SWITCH_PIN", 26),
        capture_button=_int_env("CAPTURE_BUTTON_PIN", 16),
        led_output=_int_env("LED_OUTPUT_PIN", 21),
        pattern_led_output=_int_env("PATTERN_LED_PIN", 12),
        led_toggle_button=_int_env("LED_TOGGLE_BUTTON_PIN", 17),
        led_active_high=_bool_env("LED_ACTIVE_HIGH", True),
        pattern_led_active_high=_bool_env("PATTERN_LED_ACTIVE_HIGH", True),
        video_mode_when_grounded=_bool_env("VIDEO_MODE_WHEN_GROUNDED", True),
        button_bounce_seconds=_float_env("BUTTON_BOUNCE_SECONDS", 0.08),
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
        config.pins.mode_switch,
        config.pins.capture_button,
        config.pins.led_output,
        config.pins.pattern_led_output,
        config.pins.led_toggle_button,
    )
    if len(set(pin_values)) != len(pin_values):
        raise ValueError("All GPIO assignments must use different BCM pins")
    if any(pin < 0 or pin > 27 for pin in pin_values):
        raise ValueError("GPIO assignments must be BCM pin numbers from 0 through 27")
    if config.pins.button_bounce_seconds < 0:
        raise ValueError("BUTTON_BOUNCE_SECONDS cannot be negative")

    for name, size in (
        ("preview", config.camera.preview_size),
        ("sensor", config.camera.sensor_size),
    ):
        if any(dimension <= 0 or dimension % 2 for dimension in size):
            raise ValueError(f"The camera {name} dimensions must be positive even numbers")

    if config.camera.frame_rate <= 0:
        raise ValueError("CAMERA_FRAME_RATE must be positive")
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

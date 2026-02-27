from dataclasses import dataclass
from pathlib import Path
import os


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_backlight_dir() -> Path:
    configured = os.getenv("BACKLIGHT_DIR")
    if configured:
        return Path(configured)

    backlight_root = Path("/sys/class/backlight")
    if not backlight_root.exists():
        return Path("/sys/class/backlight/10-0045")

    candidates = sorted(path for path in backlight_root.iterdir() if path.is_dir())
    if not candidates:
        return Path("/sys/class/backlight/10-0045")

    # Prefer the common DSI backlight controller names first.
    for preferred_name in ("11-0045", "10-0045"):
        preferred = backlight_root / preferred_name
        if preferred in candidates:
            return preferred

    for candidate in candidates:
        if (candidate / "brightness").exists() and (candidate / "max_brightness").exists():
            return candidate

    return candidates[0]


@dataclass(frozen=True)
class BacklightConfig:
    dir: Path
    brightness_file: Path
    max_brightness_file: Path


@dataclass(frozen=True)
class NeoPixelConfig:
    count: int
    backend: str
    pin: int
    freq_hz: int
    dma: int
    brightness: int
    invert: bool
    channel: int
    spi_device: str
    spi_khz: int


@dataclass(frozen=True)
class MessageApiConfig:
    base_url: str
    state_url: str
    stream_url: str
    connect_timeout_seconds: float
    read_timeout_seconds: float
    reconnect_delay_seconds: float
    state_refresh_seconds: float


@dataclass(frozen=True)
class TouchConfig:
    enabled: bool
    device_name_hint: str
    debounce_seconds: float
    rescan_seconds: float


PIR_PIN = _int_env("PIR_PIN", 14)
OFF_DELAY_SECONDS = _float_env("OFF_DELAY_SECONDS", 15.0)
ANIMATION_FRAME_DELAY_SECONDS = _float_env("ANIMATION_FRAME_DELAY_SECONDS", 0.02)

_backlight_dir = _resolve_backlight_dir()
_backlight_brightness = _backlight_dir / "brightness"
_backlight_max = _backlight_dir / "max_brightness"

BACKLIGHT = BacklightConfig(
    dir=_backlight_dir,
    brightness_file=_backlight_brightness,
    max_brightness_file=_backlight_max,
)

NEOPIXEL = NeoPixelConfig(
    count=_int_env("NEOPIXEL_COUNT", 10),
    backend=os.getenv("NEOPIXEL_BACKEND", "auto").strip().lower(),
    pin=_int_env("NEOPIXEL_PIN", 10),
    freq_hz=_int_env("NEOPIXEL_FREQ_HZ", 800000),
    dma=_int_env("NEOPIXEL_DMA", 10),
    brightness=_int_env("NEOPIXEL_BRIGHTNESS", 160),
    invert=os.getenv("NEOPIXEL_INVERT", "0").strip() in {"1", "true", "True", "yes"},
    channel=_int_env("NEOPIXEL_CHANNEL", 0),
    spi_device=os.getenv("NEOPIXEL_SPI_DEVICE", "/dev/spidev0.0"),
    spi_khz=_int_env("NEOPIXEL_SPI_KHZ", 800),
)

_message_api_base = os.getenv("MESSAGE_API_BASE_URL", "http://127.0.0.1:3000").rstrip("/")

MESSAGE_API = MessageApiConfig(
    base_url=_message_api_base,
    state_url=f"{_message_api_base}/api/message",
    stream_url=f"{_message_api_base}/api/message/stream",
    connect_timeout_seconds=_float_env("HTTP_CONNECT_TIMEOUT_SECONDS", 4.0),
    read_timeout_seconds=_float_env("HTTP_READ_TIMEOUT_SECONDS", 45.0),
    reconnect_delay_seconds=_float_env("HTTP_RECONNECT_DELAY_SECONDS", 1.5),
    state_refresh_seconds=_float_env("HTTP_STATE_REFRESH_SECONDS", 1.0),
)

TOUCH = TouchConfig(
    enabled=_bool_env("TOUCH_ENABLED", True),
    device_name_hint=os.getenv("TOUCH_DEVICE_NAME_HINT", "").strip(),
    debounce_seconds=_float_env("TOUCH_DEBOUNCE_SECONDS", 0.15),
    rescan_seconds=_float_env("TOUCH_RESCAN_SECONDS", 2.0),
)


def read_backlight_max_brightness() -> int:
    override = os.getenv("BACKLIGHT_MAX_BRIGHTNESS")
    if override is not None:
        return int(override)
    return int(BACKLIGHT.max_brightness_file.read_text().strip())

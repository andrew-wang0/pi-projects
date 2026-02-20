#!/usr/bin/env python3
from pathlib import Path
from signal import pause
import colorsys
import json
import math
import os
import random
import threading
import time
from typing import Sequence

import requests
from gpiozero import Device, MotionSensor
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()

# PIR pin
PIR_PIN = 14

# Backlight sysfs path
BL_DIR = Path("/sys/class/backlight/10-0045")
BRIGHTNESS = BL_DIR / "brightness"
MAX_BRIGHTNESS = int((BL_DIR / "max_brightness").read_text().strip())

# Turn backlight off 15 seconds after motion stops
OFF_DELAY_SECONDS = 15.0

# NeoPixel strip config
NEOPIXEL_COUNT = int(os.getenv("NEOPIXEL_COUNT", "10"))
NEOPIXEL_BACKEND = os.getenv("NEOPIXEL_BACKEND", "auto").strip().lower()
NEOPIXEL_PIN = int(os.getenv("NEOPIXEL_PIN", "10"))
NEOPIXEL_FREQ_HZ = 800000
NEOPIXEL_DMA = 10
NEOPIXEL_BRIGHTNESS = 160
NEOPIXEL_INVERT = False
NEOPIXEL_CHANNEL = 0
NEOPIXEL_PI5_SPI_DEVICE = os.getenv("NEOPIXEL_SPI_DEVICE", "/dev/spidev0.0")
NEOPIXEL_PI5_SPI_KHZ = int(os.getenv("NEOPIXEL_SPI_KHZ", "800"))

ANIMATION_FRAME_DELAY_SECONDS = 0.03
PIR_FLASH_SECONDS = 0.22

# Message API / stream config
MESSAGE_API_BASE_URL = os.getenv("MESSAGE_API_BASE_URL", "http://127.0.0.1:3000").rstrip("/")
MESSAGE_API_STATE_URL = f"{MESSAGE_API_BASE_URL}/api/message"
MESSAGE_API_STREAM_URL = f"{MESSAGE_API_BASE_URL}/api/message/stream"
HTTP_CONNECT_TIMEOUT_SECONDS = 4.0
HTTP_READ_TIMEOUT_SECONDS = 45.0
HTTP_RECONNECT_DELAY_SECONDS = 1.5

# Explicit background -> pattern mapping
BACKGROUND_PATTERN_MAP = {
    "default": "rainbow",
    "beach": "rainbow",
    "fire": "fire_embers",
    "fruits": "rainbow",
    "frances": "rainbow",
    "sleep": "rainbow",
}
DEFAULT_PATTERN = "rainbow"

pir = MotionSensor(PIR_PIN)

_off_timer = None
_timer_lock = threading.Lock()
_anim_lock = threading.Lock()
_state_lock = threading.Lock()

_display_active = threading.Event()
_shutdown = threading.Event()

_current_background_id = "default"
_pir_flash_until = 0.0

_random = random.Random()


def _read_pi_model() -> str:
    model_path = Path("/proc/device-tree/model")
    if not model_path.exists():
        return ""
    return model_path.read_text(encoding="utf-8", errors="ignore").strip("\x00\r\n")


def _is_pi5() -> bool:
    return "Raspberry Pi 5" in _read_pi_model()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _blend_rgb(base: tuple[int, int, int], overlay: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    alpha = _clamp(alpha, 0.0, 1.0)
    inv = 1.0 - alpha
    return (
        int(base[0] * inv + overlay[0] * alpha),
        int(base[1] * inv + overlay[1] * alpha),
        int(base[2] * inv + overlay[2] * alpha),
    )


class _NoopPixels:
    def begin(self) -> None:
        return

    def clear(self) -> None:
        return

    def show(self, colors: Sequence[tuple[int, int, int]]) -> None:
        return


class _RpiWs281xPixels:
    def __init__(self) -> None:
        from rpi_ws281x import Color, PixelStrip

        supported_pins = {10, 12, 13, 18, 19, 21}
        if NEOPIXEL_PIN not in supported_pins:
            pins = ", ".join(str(pin) for pin in sorted(supported_pins))
            raise ValueError(
                f"NEOPIXEL_PIN={NEOPIXEL_PIN} is not supported by rpi_ws281x. "
                f"Supported GPIO pins: {pins}."
            )

        self._color = Color
        self._strip = PixelStrip(
            NEOPIXEL_COUNT,
            NEOPIXEL_PIN,
            NEOPIXEL_FREQ_HZ,
            NEOPIXEL_DMA,
            NEOPIXEL_INVERT,
            NEOPIXEL_BRIGHTNESS,
            NEOPIXEL_CHANNEL,
        )

    def begin(self) -> None:
        self._strip.begin()

    def clear(self) -> None:
        for i in range(NEOPIXEL_COUNT):
            self._strip.setPixelColor(i, self._color(0, 0, 0))
        self._strip.show()

    def show(self, colors: Sequence[tuple[int, int, int]]) -> None:
        for i in range(NEOPIXEL_COUNT):
            r, g, b = colors[i]
            self._strip.setPixelColor(i, self._color(r, g, b))
        self._strip.show()


class _Pi5NeoPixels:
    def __init__(self) -> None:
        from pi5neo import Pi5Neo

        if NEOPIXEL_PIN != 10:
            print(
                "NeoPixel pi5neo backend uses SPI MOSI (GPIO10). "
                f"Current NEOPIXEL_PIN={NEOPIXEL_PIN} is ignored."
            )
        configured_spi_device = Path(NEOPIXEL_PI5_SPI_DEVICE)
        if configured_spi_device.exists():
            spi_device = str(configured_spi_device)
        else:
            spi_candidates = sorted(Path("/dev").glob("spidev*"))
            if not spi_candidates:
                raise RuntimeError(
                    f"SPI device not found at {NEOPIXEL_PI5_SPI_DEVICE}. "
                    "Enable SPI and verify /dev/spidev* is present."
                )
            spi_device = str(spi_candidates[0])
            print(
                f"Configured SPI device {NEOPIXEL_PI5_SPI_DEVICE} not found; "
                f"using {spi_device}."
            )

        self._strip = Pi5Neo(
            spi_device,
            NEOPIXEL_COUNT,
            NEOPIXEL_PI5_SPI_KHZ,
        )
        self._enabled = True

    def _disable(self, exc: Exception) -> None:
        if self._enabled:
            print(
                "NeoPixel pi5neo disabled after SPI error: "
                f"{exc}. Check SPI interface and wiring."
            )
        self._enabled = False

    def begin(self) -> None:
        if not self._enabled:
            return
        # Probe SPI early so startup can fail fast into fallback behavior.
        self.clear()
        return

    def clear(self) -> None:
        if not self._enabled:
            return
        try:
            self._strip.clear_strip()
            self._strip.update_strip()
        except Exception as exc:
            self._disable(exc)

    def show(self, colors: Sequence[tuple[int, int, int]]) -> None:
        if not self._enabled:
            return
        for i in range(NEOPIXEL_COUNT):
            r, g, b = colors[i]
            self._strip.set_led_color(i, r, g, b)
        try:
            self._strip.update_strip()
        except Exception as exc:
            self._disable(exc)


def _build_pixels() -> _NoopPixels | _RpiWs281xPixels | _Pi5NeoPixels:
    if NEOPIXEL_BACKEND not in {"auto", "pi5neo", "rpi_ws281x", "off"}:
        print(f"Unknown NEOPIXEL_BACKEND='{NEOPIXEL_BACKEND}', disabling NeoPixels.")
        return _NoopPixels()

    if NEOPIXEL_BACKEND == "off":
        return _NoopPixels()

    if NEOPIXEL_BACKEND in {"auto", "pi5neo"} and _is_pi5():
        try:
            return _Pi5NeoPixels()
        except Exception as exc:
            print(f"NeoPixel pi5neo init failed: {exc}")
            if NEOPIXEL_BACKEND == "pi5neo":
                return _NoopPixels()

    if NEOPIXEL_BACKEND == "auto" and _is_pi5():
        print(
            "Pi 5 detected: skipping rpi_ws281x auto fallback to avoid "
            "ws2811_init hardware-revision crashes."
        )
        return _NoopPixels()

    try:
        return _RpiWs281xPixels()
    except Exception as exc:
        print(f"NeoPixel rpi_ws281x init failed: {exc}")
        return _NoopPixels()


_pixels: _NoopPixels | _RpiWs281xPixels | _Pi5NeoPixels = _NoopPixels()


def _clear_pixels() -> None:
    with _anim_lock:
        _pixels.clear()


def _show_pixels(colors: Sequence[tuple[int, int, int]]) -> None:
    with _anim_lock:
        _pixels.show(colors)


def set_brightness(x: int) -> None:
    x = max(0, min(MAX_BRIGHTNESS, int(x)))
    BRIGHTNESS.write_text(f"{x}\n")


def _cancel_off_timer() -> None:
    global _off_timer
    with _timer_lock:
        if _off_timer and _off_timer.is_alive():
            _off_timer.cancel()
        _off_timer = None


def _schedule_backlight_off() -> None:
    global _off_timer
    with _timer_lock:
        if _off_timer and _off_timer.is_alive():
            _off_timer.cancel()
        _off_timer = threading.Timer(OFF_DELAY_SECONDS, _timeout_display_off)
        _off_timer.daemon = True
        _off_timer.start()


def _timeout_display_off() -> None:
    set_brightness(0)
    _display_active.clear()


def _set_background_id(background_id: str) -> None:
    global _current_background_id
    with _state_lock:
        _current_background_id = background_id


def _get_background_id() -> str:
    with _state_lock:
        return _current_background_id


def _trigger_pir_flash() -> None:
    global _pir_flash_until
    with _state_lock:
        _pir_flash_until = time.monotonic() + PIR_FLASH_SECONDS


def _get_pir_flash_remaining(now: float) -> float:
    with _state_lock:
        return _pir_flash_until - now


def _extract_background_id(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    background_id = payload.get("activeBackgroundId")
    if isinstance(background_id, str) and background_id:
        return background_id
    return None


def _fetch_background_state(session: requests.Session) -> None:
    response = session.get(
        MESSAGE_API_STATE_URL,
        timeout=(HTTP_CONNECT_TIMEOUT_SECONDS, HTTP_READ_TIMEOUT_SECONDS),
        headers={"Cache-Control": "no-store"},
    )
    response.raise_for_status()
    payload = response.json()
    background_id = _extract_background_id(payload)
    if background_id:
        _set_background_id(background_id)


def _iter_sse_data(response: requests.Response):
    data_lines: list[str] = []
    for raw_line in response.iter_lines(decode_unicode=True):
        if _shutdown.is_set():
            return
        if raw_line is None:
            continue

        line = raw_line.strip("\r")

        if line == "":
            if data_lines:
                yield "\n".join(data_lines)
                data_lines.clear()
            continue

        if line.startswith(":"):
            continue

        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    if data_lines:
        yield "\n".join(data_lines)


def _sleep_until_retry(seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if _shutdown.is_set():
            return
        time.sleep(0.05)


def _background_sync_loop() -> None:
    session = requests.Session()

    while not _shutdown.is_set():
        try:
            _fetch_background_state(session)
        except Exception as exc:
            print(f"Background state fetch failed: {exc}")

        if _shutdown.is_set():
            break

        try:
            with session.get(
                MESSAGE_API_STREAM_URL,
                stream=True,
                timeout=(HTTP_CONNECT_TIMEOUT_SECONDS, HTTP_READ_TIMEOUT_SECONDS),
                headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
            ) as response:
                response.raise_for_status()

                for raw_event in _iter_sse_data(response):
                    try:
                        payload = json.loads(raw_event)
                    except json.JSONDecodeError:
                        continue

                    background_id = _extract_background_id(payload)
                    if background_id:
                        _set_background_id(background_id)

                    if _shutdown.is_set():
                        break

        except Exception as exc:
            if not _shutdown.is_set():
                print(f"Background stream disconnected, reconnecting: {exc}")
                _sleep_until_retry(HTTP_RECONNECT_DELAY_SECONDS)


def _pattern_for_background(background_id: str) -> str:
    return BACKGROUND_PATTERN_MAP.get(background_id, DEFAULT_PATTERN)


def _render_rainbow_frame(frame: int) -> list[tuple[int, int, int]]:
    colors: list[tuple[int, int, int]] = []
    for i in range(NEOPIXEL_COUNT):
        hue = (frame * 3 + i * 24 + int(18 * math.sin(frame * 0.11 + i * 0.7))) % 256
        brightness = 0.45 + 0.45 * (0.5 + 0.5 * math.sin(frame * 0.09 + i * 0.55))
        r, g, b = colorsys.hsv_to_rgb(hue / 255.0, 1.0, _clamp(brightness, 0.0, 1.0))
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors


def _heat_to_fire_rgb(heat: float) -> tuple[int, int, int]:
    heat = _clamp(heat, 0.0, 1.0)

    if heat < 0.33:
        t = heat / 0.33
        return (int(180 * t), int(14 * t), int(0 * t))

    if heat < 0.66:
        t = (heat - 0.33) / 0.33
        return (int(180 + 70 * t), int(14 + 90 * t), int(8 * t))

    t = (heat - 0.66) / 0.34
    return (255, int(104 + 151 * t), int(12 + 80 * t))


class _FireState:
    def __init__(self, count: int) -> None:
        self.heat = [_random.uniform(0.02, 0.15) for _ in range(count)]

    def reset(self) -> None:
        for i in range(len(self.heat)):
            self.heat[i] = _random.uniform(0.02, 0.15)


def _render_fire_frame(state: _FireState, frame: int) -> list[tuple[int, int, int]]:
    n = len(state.heat)

    for i in range(n):
        state.heat[i] = max(0.0, state.heat[i] - _random.uniform(0.025, 0.13))

    for i in range(n - 1, 0, -1):
        near = state.heat[i - 1]
        near2 = state.heat[i - 2] if i > 1 else near
        state.heat[i] = _clamp(state.heat[i] * 0.2 + near * 0.55 + near2 * 0.25, 0.0, 1.0)

    if n > 0 and _random.random() < 0.9:
        spark_idx = _random.randrange(min(3, n))
        state.heat[spark_idx] = _clamp(state.heat[spark_idx] + _random.uniform(0.5, 1.0), 0.0, 1.0)

    for i in range(n):
        turbulence = 0.06 * math.sin(frame * 0.25 + i * 1.23) + 0.04 * math.sin(
            frame * 0.16 - i * 0.77
        )
        ember_flicker = _random.uniform(-0.04, 0.07)
        falloff = 1.0 - (i / max(1, n - 1)) * 0.45
        state.heat[i] = _clamp((state.heat[i] + turbulence + ember_flicker) * falloff, 0.0, 1.0)

    colors: list[tuple[int, int, int]] = []
    for i in range(n):
        colors.append(_heat_to_fire_rgb(state.heat[i]))

    return colors


def _apply_pir_flash(colors: list[tuple[int, int, int]], now: float) -> None:
    remaining = _get_pir_flash_remaining(now)
    if remaining <= 0 or not colors:
        return

    alpha = _clamp(remaining / PIR_FLASH_SECONDS, 0.0, 1.0)
    colors[0] = _blend_rgb(colors[0], (255, 0, 0), 0.85 * alpha + 0.15)

    if len(colors) > 1:
        colors[1] = _blend_rgb(colors[1], (255, 38, 0), 0.35 * alpha)


def _neopixel_loop() -> None:
    frame = 0
    pixels_off = False
    fire_state = _FireState(NEOPIXEL_COUNT)
    last_pattern = ""

    while not _shutdown.is_set():
        if _display_active.is_set():
            background_id = _get_background_id()
            pattern = _pattern_for_background(background_id)

            if pattern != last_pattern:
                if pattern == "fire_embers":
                    fire_state.reset()
                last_pattern = pattern

            if pattern == "fire_embers":
                colors = _render_fire_frame(fire_state, frame)
            else:
                colors = _render_rainbow_frame(frame)

            _apply_pir_flash(colors, time.monotonic())
            _show_pixels(colors)

            frame += 1
            pixels_off = False
            time.sleep(ANIMATION_FRAME_DELAY_SECONDS)
            continue

        if not pixels_off:
            _clear_pixels()
            pixels_off = True

        time.sleep(0.05)


def on_motion() -> None:
    _cancel_off_timer()
    set_brightness(MAX_BRIGHTNESS)
    _display_active.set()
    _trigger_pir_flash()


def on_no_motion() -> None:
    _schedule_backlight_off()


def main() -> None:
    global _pixels

    _pixels = _build_pixels()
    _pixels.begin()
    _clear_pixels()

    set_brightness(0)
    _display_active.clear()

    anim_thread = threading.Thread(target=_neopixel_loop, daemon=True)
    background_thread = threading.Thread(target=_background_sync_loop, daemon=True)

    anim_thread.start()
    background_thread.start()

    pir.when_motion = on_motion
    pir.when_no_motion = on_no_motion

    try:
        pause()
    finally:
        _shutdown.set()
        _display_active.clear()
        _cancel_off_timer()

        anim_thread.join(timeout=1.0)
        background_thread.join(timeout=1.0)

        _clear_pixels()
        set_brightness(0)


if __name__ == "__main__":
    main()

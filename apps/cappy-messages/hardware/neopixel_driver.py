from pathlib import Path
from typing import Protocol, Sequence

from config import NEOPIXEL


RGB = tuple[int, int, int]


class PixelDriver(Protocol):
    def begin(self) -> None:
        ...

    def clear(self) -> None:
        ...

    def show(self, colors: Sequence[RGB]) -> None:
        ...


class NoopPixels:
    def begin(self) -> None:
        return

    def clear(self) -> None:
        return

    def show(self, colors: Sequence[RGB]) -> None:
        return


class RpiWs281xPixels:
    def __init__(self) -> None:
        from rpi_ws281x import Color, PixelStrip

        supported_pins = {10, 12, 13, 18, 19, 21}
        if NEOPIXEL.pin not in supported_pins:
            pins = ", ".join(str(pin) for pin in sorted(supported_pins))
            raise ValueError(
                f"NEOPIXEL_PIN={NEOPIXEL.pin} is not supported by rpi_ws281x. "
                f"Supported GPIO pins: {pins}."
            )

        self._color = Color
        self._strip = PixelStrip(
            NEOPIXEL.count,
            NEOPIXEL.pin,
            NEOPIXEL.freq_hz,
            NEOPIXEL.dma,
            NEOPIXEL.invert,
            NEOPIXEL.brightness,
            NEOPIXEL.channel,
        )

    def begin(self) -> None:
        self._strip.begin()

    def clear(self) -> None:
        for i in range(NEOPIXEL.count):
            self._strip.setPixelColor(i, self._color(0, 0, 0))
        self._strip.show()

    def show(self, colors: Sequence[RGB]) -> None:
        for i in range(NEOPIXEL.count):
            r, g, b = colors[i]
            self._strip.setPixelColor(i, self._color(r, g, b))
        self._strip.show()


class Pi5NeoPixels:
    def __init__(self) -> None:
        from pi5neo import Pi5Neo

        if NEOPIXEL.pin != 10:
            print(
                "NeoPixel pi5neo backend uses SPI MOSI (GPIO10). "
                f"Current NEOPIXEL_PIN={NEOPIXEL.pin} is ignored."
            )

        configured_spi_device = Path(NEOPIXEL.spi_device)
        if configured_spi_device.exists():
            spi_device = str(configured_spi_device)
        else:
            spi_candidates = sorted(Path("/dev").glob("spidev*"))
            if not spi_candidates:
                raise RuntimeError(
                    f"SPI device not found at {NEOPIXEL.spi_device}. "
                    "Enable SPI and verify /dev/spidev* is present."
                )
            spi_device = str(spi_candidates[0])
            print(
                f"Configured SPI device {NEOPIXEL.spi_device} not found; "
                f"using {spi_device}."
            )

        self._strip = Pi5Neo(
            spi_device,
            NEOPIXEL.count,
            NEOPIXEL.spi_khz,
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
        self.clear()

    def clear(self) -> None:
        if not self._enabled:
            return
        try:
            self._strip.clear_strip()
            self._strip.update_strip()
        except Exception as exc:
            self._disable(exc)

    def show(self, colors: Sequence[RGB]) -> None:
        if not self._enabled:
            return
        for i in range(NEOPIXEL.count):
            r, g, b = colors[i]
            self._strip.set_led_color(i, r, g, b)
        try:
            self._strip.update_strip()
        except Exception as exc:
            self._disable(exc)


def _read_pi_model() -> str:
    model_path = Path("/proc/device-tree/model")
    if not model_path.exists():
        return ""
    return model_path.read_text(encoding="utf-8", errors="ignore").strip("\x00\r\n")


def _is_pi5() -> bool:
    return "Raspberry Pi 5" in _read_pi_model()


def build_pixel_driver() -> PixelDriver:
    if NEOPIXEL.backend not in {"auto", "pi5neo", "rpi_ws281x", "off"}:
        print(f"Unknown NEOPIXEL_BACKEND='{NEOPIXEL.backend}', disabling NeoPixels.")
        return NoopPixels()

    if NEOPIXEL.backend == "off":
        return NoopPixels()

    if NEOPIXEL.backend in {"auto", "pi5neo"} and _is_pi5():
        try:
            return Pi5NeoPixels()
        except Exception as exc:
            print(f"NeoPixel pi5neo init failed: {exc}")
            if NEOPIXEL.backend == "pi5neo":
                return NoopPixels()

    if NEOPIXEL.backend == "auto" and _is_pi5():
        print(
            "Pi 5 detected: skipping rpi_ws281x auto fallback to avoid "
            "ws2811_init hardware-revision crashes."
        )
        return NoopPixels()

    try:
        return RpiWs281xPixels()
    except Exception as exc:
        print(f"NeoPixel rpi_ws281x init failed: {exc}")
        return NoopPixels()

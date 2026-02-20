from pathlib import Path


class BacklightController:
    def __init__(self, brightness_file: Path, max_brightness: int) -> None:
        self._brightness_file = brightness_file
        self._max_brightness = max_brightness

    @property
    def max_brightness(self) -> int:
        return self._max_brightness

    def set_brightness(self, value: int) -> None:
        clamped = max(0, min(self._max_brightness, int(value)))
        self._brightness_file.write_text(f"{clamped}\n")

    def turn_on(self) -> None:
        self.set_brightness(self._max_brightness)

    def turn_off(self) -> None:
        self.set_brightness(0)

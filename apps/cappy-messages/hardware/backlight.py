from pathlib import Path


class BacklightController:
    def __init__(self, brightness_file: Path, max_brightness: int) -> None:
        self._brightness_file = brightness_file
        self._max_brightness = max_brightness
        self._disabled = False

    @property
    def max_brightness(self) -> int:
        return self._max_brightness

    def set_brightness(self, value: int) -> None:
        if self._disabled:
            return

        clamped = max(0, min(self._max_brightness, int(value)))
        try:
            self._brightness_file.write_text(f"{clamped}\n")
        except OSError as exc:
            # Some displays intermittently return EREMOTEIO (errno 121) via sysfs.
            # Disable further writes so the process stays alive.
            print(
                f"Backlight write failed ({self._brightness_file}): {exc}. "
                "Disabling backlight control for this process."
            )
            self._disabled = True

    def turn_on(self) -> None:
        self.set_brightness(self._max_brightness)

    def turn_off(self) -> None:
        self.set_brightness(0)

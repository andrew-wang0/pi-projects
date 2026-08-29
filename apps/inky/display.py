from __future__ import annotations

from PIL import Image, ImageOps
from inky.auto import auto

from config import Config


class InkyDisplay:
    RESOLUTION = (800, 480)

    def __init__(self, config: Config) -> None:
        self._display = auto()
        self._saturation = config.inky_saturation
        if tuple(self._display.resolution) != self.RESOLUTION:
            raise RuntimeError("Expected an Inky Impression 7.3 at 800x480")

    def prepare(self, image: Image.Image) -> Image.Image:
        return ImageOps.fit(
            image.convert("RGB"),
            self.RESOLUTION,
            method=Image.Resampling.LANCZOS,
        )

    def show(self, image: Image.Image) -> None:
        if image.size != self.RESOLUTION:
            raise ValueError("Inky image must be 800x480")
        self._display.set_image(image, saturation=self._saturation)
        self._display.show()

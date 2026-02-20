import math
import random

from .common import RGB, clamp


def _heat_to_fire_rgb(heat: float) -> RGB:
    heat = clamp(heat, 0.0, 1.0)

    if heat < 0.33:
        t = heat / 0.33
        return (int(180 * t), int(14 * t), int(0 * t))

    if heat < 0.66:
        t = (heat - 0.33) / 0.33
        return (int(180 + 70 * t), int(14 + 90 * t), int(8 * t))

    t = (heat - 0.66) / 0.34
    return (255, int(120 + 105 * t), int(35 + 95 * t))


class FirePattern:
    def __init__(self, pixel_count: int, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()
        self._heat = [self._rng.uniform(0.02, 0.15) for _ in range(pixel_count)]

    def reset(self) -> None:
        for i in range(len(self._heat)):
            self._heat[i] = self._rng.uniform(0.02, 0.15)

    def render(self, frame: int) -> list[RGB]:
        n = len(self._heat)
        if n == 0:
            return []

        # Random cooling keeps each pixel flickering independently.
        for i in range(n):
            self._heat[i] = max(0.0, self._heat[i] - self._rng.uniform(0.015, 0.10))

        # Circular diffusion avoids left/right bias, so any pixel can burn hot.
        previous = self._heat.copy()
        for i in range(n):
            left = previous[(i - 1) % n]
            center = previous[i]
            right = previous[(i + 1) % n]
            self._heat[i] = clamp(center * 0.50 + left * 0.25 + right * 0.25, 0.0, 1.0)

        # Sparks can appear anywhere on the strip.
        spark_count = 1 + (1 if self._rng.random() < 0.55 else 0)
        for _ in range(spark_count):
            spark_idx = self._rng.randrange(n)
            self._heat[spark_idx] = clamp(
                self._heat[spark_idx] + self._rng.uniform(0.25, 0.75),
                0.0,
                1.0,
            )
            # Nearby embers also warm up slightly.
            for neighbor in ((spark_idx - 1) % n, (spark_idx + 1) % n):
                self._heat[neighbor] = clamp(
                    self._heat[neighbor] + self._rng.uniform(0.03, 0.16),
                    0.0,
                    1.0,
                )

        for i in range(n):
            turbulence = 0.06 * math.sin(frame * 0.25 + i * 1.23) + 0.04 * math.sin(
                frame * 0.16 - i * 0.77
            )
            ember_flicker = self._rng.uniform(-0.04, 0.07)
            self._heat[i] = clamp(self._heat[i] + turbulence + ember_flicker, 0.0, 1.0)

        return [_heat_to_fire_rgb(heat) for heat in self._heat]

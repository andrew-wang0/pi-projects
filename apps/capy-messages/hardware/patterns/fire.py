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
    return (255, int(104 + 151 * t), int(12 + 80 * t))


class FirePattern:
    def __init__(self, pixel_count: int, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()
        self._heat = [self._rng.uniform(0.02, 0.15) for _ in range(pixel_count)]

    def reset(self) -> None:
        for i in range(len(self._heat)):
            self._heat[i] = self._rng.uniform(0.02, 0.15)

    def render(self, frame: int) -> list[RGB]:
        n = len(self._heat)

        for i in range(n):
            self._heat[i] = max(0.0, self._heat[i] - self._rng.uniform(0.025, 0.13))

        for i in range(n - 1, 0, -1):
            near = self._heat[i - 1]
            near2 = self._heat[i - 2] if i > 1 else near
            self._heat[i] = clamp(self._heat[i] * 0.2 + near * 0.55 + near2 * 0.25, 0.0, 1.0)

        if n > 0 and self._rng.random() < 0.9:
            spark_idx = self._rng.randrange(min(3, n))
            self._heat[spark_idx] = clamp(
                self._heat[spark_idx] + self._rng.uniform(0.5, 1.0),
                0.0,
                1.0,
            )

        for i in range(n):
            turbulence = 0.06 * math.sin(frame * 0.25 + i * 1.23) + 0.04 * math.sin(
                frame * 0.16 - i * 0.77
            )
            ember_flicker = self._rng.uniform(-0.04, 0.07)
            falloff = 1.0 - (i / max(1, n - 1)) * 0.45
            self._heat[i] = clamp((self._heat[i] + turbulence + ember_flicker) * falloff, 0.0, 1.0)

        return [_heat_to_fire_rgb(heat) for heat in self._heat]

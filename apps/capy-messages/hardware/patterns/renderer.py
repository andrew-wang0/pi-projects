import random

from backgrounds import BEACH_PATTERN, FIRE_PATTERN, FRANCES_PATTERN, SLEEP_PATTERN

from .beach import render_beach_frame
from .common import RGB, blend_rgb
from .fire import FirePattern
from .frances import render_frances_frame
from .rainbow import render_rainbow_frame
from .sleep import render_sleep_frame


class PatternRenderer:
    def __init__(self, pixel_count: int) -> None:
        self._pixel_count = pixel_count
        self._rng = random.Random()
        self._fire_pattern = FirePattern(pixel_count, self._rng)
        self._last_pattern = ""
        self._smoothed_colors: list[RGB] = [(0, 0, 0)] * pixel_count
        self._color_smoothing_alpha = 0.42

    def render(
        self,
        pattern: str,
        frame: int,
    ) -> list[RGB]:
        if pattern != self._last_pattern:
            if pattern == FIRE_PATTERN:
                self._fire_pattern.reset()
            self._last_pattern = pattern

        if pattern == FIRE_PATTERN:
            target_colors = self._fire_pattern.render(frame)
        elif pattern == BEACH_PATTERN:
            target_colors = render_beach_frame(self._pixel_count, frame)
        elif pattern == FRANCES_PATTERN:
            target_colors = render_frances_frame(self._pixel_count, frame)
        elif pattern == SLEEP_PATTERN:
            target_colors = render_sleep_frame(self._pixel_count, frame)
        else:
            target_colors = render_rainbow_frame(self._pixel_count, frame)

        return self._smooth_colors(target_colors)

    def _smooth_colors(self, target_colors: list[RGB]) -> list[RGB]:
        if len(self._smoothed_colors) != len(target_colors):
            self._smoothed_colors = target_colors.copy()
            return self._smoothed_colors.copy()

        smoothed: list[RGB] = []
        for i, target in enumerate(target_colors):
            previous = self._smoothed_colors[i]
            smoothed_color = blend_rgb(previous, target, self._color_smoothing_alpha)
            smoothed.append(smoothed_color)

        self._smoothed_colors = smoothed
        return smoothed.copy()

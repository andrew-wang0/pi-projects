import random

from backgrounds import BEACH_PATTERN, FIRE_PATTERN, FRANCES_PATTERN

from .beach import render_beach_frame
from .common import RGB, blend_rgb, clamp
from .fire import FirePattern
from .frances import render_frances_frame
from .rainbow import render_rainbow_frame


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
        pir_flash_remaining: float,
        pir_flash_seconds: float,
        pir_flash_pulses: int,
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
        else:
            target_colors = render_rainbow_frame(self._pixel_count, frame)

        colors = self._smooth_colors(target_colors)
        self._apply_pir_flash(colors, pir_flash_remaining, pir_flash_seconds, pir_flash_pulses)
        return colors

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

    def _apply_pir_flash(
        self,
        colors: list[RGB],
        pir_flash_remaining: float,
        pir_flash_seconds: float,
        pir_flash_pulses: int,
    ) -> None:
        if (
            pir_flash_remaining <= 0
            or not colors
            or pir_flash_seconds <= 0
            or pir_flash_pulses <= 0
        ):
            return

        elapsed = clamp(pir_flash_seconds - pir_flash_remaining, 0.0, pir_flash_seconds)
        phase_count = pir_flash_pulses * 2
        phase_progress = elapsed / pir_flash_seconds
        phase_index = int(phase_progress * phase_count)
        is_red_phase = phase_index % 2 == 0

        colors[0] = (255, 0, 0) if is_red_phase else (255, 255, 255)

import colorsys
import math

from .common import RGB, clamp


def render_frances_frame(pixel_count: int, frame: int) -> list[RGB]:
    colors: list[RGB] = []
    for i in range(pixel_count):
        phase = frame * 0.16 + i * 0.72
        hue = 0.30 + 0.045 * math.sin(phase) + 0.02 * math.sin(frame * 0.05 + i * 1.1)
        sat = 0.72 + 0.18 * (0.5 + 0.5 * math.sin(phase * 0.8 + 1.7))
        val = 0.34 + 0.58 * (0.5 + 0.5 * math.sin(frame * 0.10 + i * 0.95))
        r, g, b = colorsys.hsv_to_rgb(
            clamp(hue, 0.24, 0.40),
            clamp(sat, 0.58, 0.96),
            clamp(val, 0.20, 1.0),
        )
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors

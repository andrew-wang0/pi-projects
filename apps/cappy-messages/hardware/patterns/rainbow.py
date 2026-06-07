import colorsys
import math

from .common import RGB, clamp


def render_rainbow_frame(pixel_count: int, frame: int) -> list[RGB]:
    colors: list[RGB] = []
    for i in range(pixel_count):
        hue = (frame * 4 + i * 24 + int(16 * math.sin(frame * 0.10 + i * 0.65))) % 256
        brightness = 0.5 + 0.4 * (0.5 + 0.5 * math.sin(frame * 0.08 + i * 0.50))
        r, g, b = colorsys.hsv_to_rgb(hue / 255.0, 1.0, clamp(brightness, 0.0, 1.0))
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors

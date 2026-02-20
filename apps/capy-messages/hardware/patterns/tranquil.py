import colorsys
import math

from .common import RGB, blend_rgb, clamp


def render_tranquil_frame(pixel_count: int, frame: int) -> list[RGB]:
    if pixel_count <= 0:
        return []

    colors: list[RGB] = []

    for i in range(pixel_count):
        flow = 0.5 + 0.5 * math.sin(frame * 0.075 + i * 0.65)
        breathe = 0.5 + 0.5 * math.sin(frame * 0.03 - i * 0.4)

        pink_h = 0.90 + 0.02 * flow
        pink_s = 0.45 + 0.25 * breathe
        pink_v = 0.68 + 0.20 * flow
        base = _hsv_to_rgb(
            clamp(pink_h, 0.88, 0.94),
            clamp(pink_s, 0.35, 0.82),
            clamp(pink_v, 0.60, 0.93),
        )

        flicker_wave = 0.5 + 0.5 * math.sin(frame * 0.34 + i * 1.27)
        flicker_micro = 0.5 + 0.5 * math.sin(frame * 0.52 - i * 2.11)
        flicker = clamp(flicker_wave * flicker_micro, 0.0, 1.0) ** 3.6
        white_alpha = clamp(0.02 + 0.14 * flicker, 0.0, 0.16)

        colors.append(blend_rgb(base, (255, 238, 246), white_alpha))

    return colors


def _hsv_to_rgb(h: float, s: float, v: float) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))

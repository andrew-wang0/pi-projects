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

        pink_h = 0.91 + 0.015 * flow
        pink_s = 0.78 + 0.18 * breathe
        pink_v = 0.45 + 0.28 * flow
        base = _hsv_to_rgb(
            clamp(pink_h, 0.89, 0.95),
            clamp(pink_s, 0.72, 1.0),
            clamp(pink_v, 0.38, 0.82),
        )

        flicker_wave = 0.5 + 0.5 * math.sin(frame * 0.34 + i * 1.27)
        flicker_micro = 0.5 + 0.5 * math.sin(frame * 0.52 - i * 2.11)
        flicker = clamp(flicker_wave * flicker_micro, 0.0, 1.0) ** 3.6
        pink_glow_alpha = clamp(0.06 + 0.20 * flicker, 0.0, 0.24)
        white_alpha = clamp(0.01 + 0.05 * (flicker * flicker), 0.0, 0.06)

        pink_glow = blend_rgb(base, (255, 98, 198), pink_glow_alpha)
        colors.append(blend_rgb(pink_glow, (255, 238, 246), white_alpha))

    return colors


def _hsv_to_rgb(h: float, s: float, v: float) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))

import colorsys
import math

from .common import RGB, blend_rgb, clamp


def render_night_frame(pixel_count: int, frame: int) -> list[RGB]:
    if pixel_count <= 0:
        return []

    colors: list[RGB] = []

    # Keep the sparkle hotspot centered around LEDs 2..4 with slight drift.
    twinkle_center = 2.0 + 0.35 * math.sin(frame * 0.028)
    twinkle_sigma = max(1.1, pixel_count * 0.16)
    glow_center = 2.35 + 0.18 * math.sin(frame * 0.018)
    glow_sigma = max(1.0, pixel_count * 0.14)

    for i in range(pixel_count):
        breathe = 0.5 + 0.5 * math.sin(frame * 0.024 + i * 0.23)
        base_h = 0.625 + 0.01 * math.sin(frame * 0.02 + i * 0.13)
        base_s = 0.80 + 0.08 * breathe
        base_v = 0.055 + 0.06 * breathe
        base = _hsv_to_rgb(
            clamp(base_h, 0.58, 0.67),
            clamp(base_s, 0.74, 0.92),
            clamp(base_v, 0.04, 0.13),
        )

        glow_dist = i - glow_center
        glow_strength = math.exp(-(glow_dist * glow_dist) / (2.0 * glow_sigma * glow_sigma))
        glow_pulse = 0.5 + 0.5 * math.sin(frame * 0.05 + i * 0.2)

        ember_orange = _hsv_to_rgb(0.073, 0.86, 0.42)
        glow_alpha = clamp(glow_strength * (0.12 + 0.16 * glow_pulse), 0.0, 0.30)
        ember_base = blend_rgb(base, ember_orange, glow_alpha)

        dist = i - twinkle_center
        hotspot_strength = math.exp(-(dist * dist) / (2.0 * twinkle_sigma * twinkle_sigma))

        shimmer = 0.5 + 0.5 * math.sin(frame * 0.29 + i * 1.21)
        micro = 0.5 + 0.5 * math.sin(frame * 0.41 - i * 1.77)
        sparkle = clamp(shimmer * micro, 0.0, 1.0) ** 3.2

        orange_h = 0.070 + 0.010 * math.sin(frame * 0.12 + i * 0.7)
        orange_s = 0.82 + 0.14 * shimmer
        orange_v = 0.35 + 0.62 * sparkle
        sunset_orange = _hsv_to_rgb(
            clamp(orange_h, 0.05, 0.10),
            clamp(orange_s, 0.74, 1.0),
            clamp(orange_v, 0.26, 1.0),
        )

        orange_alpha = clamp(hotspot_strength * (0.08 + 0.72 * sparkle), 0.0, 0.86)
        colors.append(blend_rgb(ember_base, sunset_orange, orange_alpha))

    return colors


def _hsv_to_rgb(h: float, s: float, v: float) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))

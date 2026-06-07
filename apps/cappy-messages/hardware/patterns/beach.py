import colorsys
import math

from .common import RGB, blend_rgb, clamp


def render_beach_frame(pixel_count: int, frame: int) -> list[RGB]:
    colors: list[RGB] = []
    if pixel_count <= 0:
        return colors

    sand_start_base = int(pixel_count * 2 / 3)
    wave_motion = int(round((pixel_count * 0.10) * math.sin(frame * 0.12)))
    wave_center = sand_start_base + wave_motion
    transition_half_width = max(1, int(pixel_count * 0.14))

    for i in range(pixel_count):
        sea_hue = 0.56 + 0.035 * math.sin(frame * 0.06 + i * 0.6)
        sea_sat = 0.76 + 0.12 * (0.5 + 0.5 * math.sin(frame * 0.08 - i * 0.7))
        sea_val = 0.34 + 0.58 * (0.5 + 0.5 * math.sin(frame * 0.11 + i * 0.9))
        sea = colorsys.hsv_to_rgb(
            clamp(sea_hue, 0.49, 0.64),
            clamp(sea_sat, 0.55, 0.95),
            clamp(sea_val, 0.22, 1.0),
        )

        sand_hue = 0.15 + 0.012 * math.sin(frame * 0.03 + i * 0.4)
        sand_sat = 0.70 + 0.12 * (0.5 + 0.5 * math.sin(frame * 0.05 + i * 0.35))
        sand_val = 0.70 + 0.22 * (0.5 + 0.5 * math.sin(frame * 0.04 - i * 0.22))
        sand = colorsys.hsv_to_rgb(
            clamp(sand_hue, 0.13, 0.18),
            clamp(sand_sat, 0.55, 0.90),
            clamp(sand_val, 0.55, 1.0),
        )

        dist = (i - wave_center) / transition_half_width
        sand_mix = clamp((dist + 1.0) / 2.0, 0.0, 1.0)
        base = blend_rgb(
            (int(sea[0] * 255), int(sea[1] * 255), int(sea[2] * 255)),
            (int(sand[0] * 255), int(sand[1] * 255), int(sand[2] * 255)),
            sand_mix,
        )

        whitewash_shape = math.exp(-((i - wave_center) ** 2) / max(1.0, transition_half_width * 1.5))
        whitewash_pulse = 0.5 + 0.5 * math.sin(frame * 0.38 + i * 0.8)
        whitewash_alpha = clamp(whitewash_shape * (0.20 + 0.45 * whitewash_pulse), 0.0, 0.70)
        foam = blend_rgb(base, (250, 250, 242), whitewash_alpha)

        colors.append(foam)

    return colors

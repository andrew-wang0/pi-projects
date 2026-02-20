import math

from .common import RGB, blend_rgb, clamp


def render_sleep_frame(pixel_count: int, frame: int) -> list[RGB]:
    if pixel_count <= 0:
        return []

    colors: list[RGB] = []

    # Purple bob glides back and forth along the strip.
    bob_center = (pixel_count - 1) * (0.5 + 0.5 * math.sin(frame * 0.065))
    bob_width = max(1.0, pixel_count * 0.18)

    for i in range(pixel_count):
        # Calm blue base with subtle breathing.
        breathe = 0.5 + 0.5 * math.sin(frame * 0.035 + i * 0.45)
        base_h = 0.59 + 0.01 * math.sin(frame * 0.02 + i * 0.2)
        base_s = 0.68 + 0.10 * breathe
        base_v = 0.22 + 0.26 * breathe

        # Keep base in blue range.
        r, g, b = _hsv_to_rgb(
            clamp(base_h, 0.56, 0.63),
            clamp(base_s, 0.55, 0.85),
            clamp(base_v, 0.12, 0.60),
        )
        base = (r, g, b)

        # Moving purple bob with gaussian-like falloff.
        dist = i - bob_center
        bob_strength = math.exp(-(dist * dist) / (2.0 * bob_width * bob_width))
        bob_pulse = 0.55 + 0.45 * math.sin(frame * 0.11 + i * 0.3)
        bob_alpha = clamp(0.85 * bob_strength * bob_pulse, 0.0, 0.90)

        purple = (180, 60, 255)
        colors.append(blend_rgb(base, purple, bob_alpha))

    return colors


def _hsv_to_rgb(h: float, s: float, v: float) -> RGB:
    import colorsys

    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))

import math

from .common import RGB, blend_rgb, clamp


def render_sleep_frame(pixel_count: int, frame: int) -> list[RGB]:
    if pixel_count <= 0:
        return []

    colors: list[RGB] = []

    # Purple blob glides back and forth along the strip.
    blob_center = (pixel_count - 1) * (0.5 + 0.5 * math.sin(frame * 0.065))
    blob_width = max(1.0, pixel_count * 0.18)

    for i in range(pixel_count):
        # Deep blue base with subtle breathing.
        breathe = 0.5 + 0.5 * math.sin(frame * 0.035 + i * 0.45)
        base_h = 0.61 + 0.008 * math.sin(frame * 0.02 + i * 0.2)
        base_s = 0.78 + 0.10 * breathe
        base_v = 0.07 + 0.12 * breathe

        # Keep base in blue range.
        r, g, b = _hsv_to_rgb(
            clamp(base_h, 0.58, 0.64),
            clamp(base_s, 0.70, 0.92),
            clamp(base_v, 0.04, 0.24),
        )
        base = (r, g, b)

        # Moving deep purple blob with gaussian-like falloff.
        dist = i - blob_center
        blob_strength = math.exp(-(dist * dist) / (2.0 * blob_width * blob_width))
        blob_pulse = 0.50 + 0.50 * math.sin(frame * 0.11 + i * 0.3)
        blob_alpha = clamp(0.80 * blob_strength * blob_pulse, 0.0, 0.82)

        purple = (82, 24, 138)
        colors.append(blend_rgb(base, purple, blob_alpha))

    return colors


def _hsv_to_rgb(h: float, s: float, v: float) -> RGB:
    import colorsys

    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))

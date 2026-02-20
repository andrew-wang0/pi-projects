RGB = tuple[int, int, int]


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def blend_rgb(base: RGB, overlay: RGB, alpha: float) -> RGB:
    alpha = clamp(alpha, 0.0, 1.0)
    inv = 1.0 - alpha
    return (
        int(base[0] * inv + overlay[0] * alpha),
        int(base[1] * inv + overlay[1] * alpha),
        int(base[2] * inv + overlay[2] * alpha),
    )

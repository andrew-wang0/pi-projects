import random

from .common import RGB


def render_adel_frame(pixel_count: int, rng: random.Random) -> list[RGB]:
    colors: list[RGB] = []
    for _ in range(pixel_count):
        colors.append((rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)))
    return colors

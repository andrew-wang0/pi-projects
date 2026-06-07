from .common import RGB


def render_tan_brown_frame(pixel_count: int, frame: int) -> list[RGB]:
    if pixel_count <= 0:
        return []

    tan: RGB = (194, 152, 107)
    dark_brown: RGB = (69, 42, 24)

    return [tan if i % 2 == 0 else dark_brown for i in range(pixel_count)]

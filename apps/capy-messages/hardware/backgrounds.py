from dataclasses import dataclass

RAINBOW_PATTERN = "rainbow"
FIRE_PATTERN = "fire"
BEACH_PATTERN = "beach"
FRANCES_PATTERN = "frances"


@dataclass(frozen=True)
class BackgroundLighting:
    background_id: str
    label: str
    pattern: str


# Central source of truth for known backgrounds and their light behavior.
BACKGROUND_LIGHTING: tuple[BackgroundLighting, ...] = (
    BackgroundLighting(background_id="default", label="Default", pattern=RAINBOW_PATTERN),
    BackgroundLighting(background_id="beach", label="Beach", pattern=BEACH_PATTERN),
    BackgroundLighting(background_id="fire", label="Fire", pattern=FIRE_PATTERN),
    BackgroundLighting(background_id="fruits", label="Fruits", pattern=RAINBOW_PATTERN),
    BackgroundLighting(background_id="frances", label="Frances", pattern=FRANCES_PATTERN),
    BackgroundLighting(background_id="sleep", label="Sleep", pattern=RAINBOW_PATTERN),
)

DEFAULT_BACKGROUND_ID = "default"
DEFAULT_PATTERN = RAINBOW_PATTERN

BACKGROUND_PATTERN_MAP: dict[str, str] = {
    item.background_id: item.pattern for item in BACKGROUND_LIGHTING
}


def pattern_for_background(background_id: str) -> str:
    return BACKGROUND_PATTERN_MAP.get(background_id, DEFAULT_PATTERN)

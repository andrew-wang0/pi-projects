from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LedCue:
    duration: float
    on: bool


def photo_capture_cues() -> tuple[LedCue, ...]:
    """Three slow flashes followed by three fast flashes in four seconds."""
    slow_flash = (LedCue(0.5, False), LedCue(0.5, True))
    fast_flash = (LedCue(1 / 6, False), LedCue(1 / 6, True))
    return slow_flash * 3 + fast_flash * 3


def video_start_cues() -> tuple[LedCue, ...]:
    """Three flashes over one second before recording begins."""
    flash = (LedCue(1 / 6, False), LedCue(1 / 6, True))
    return flash * 3


def video_end_cues() -> tuple[LedCue, ...]:
    """Three flashes over one second after an automatic recording stop."""
    flash = (LedCue(1 / 6, False), LedCue(1 / 6, True))
    return flash * 3


class CuePlayer:
    def __init__(self, cues: tuple[LedCue, ...]) -> None:
        if not cues:
            raise ValueError("A cue sequence cannot be empty")
        if any(cue.duration <= 0 for cue in cues):
            raise ValueError("Every cue duration must be positive")

        self._cues = cues
        self._index = -1
        self._deadline = 0.0
        self._started = False
        self._finished = False

    @property
    def total_duration(self) -> float:
        return sum(cue.duration for cue in self._cues)

    @property
    def finished(self) -> bool:
        return self._finished

    def start(self, now: float) -> bool:
        if self._started:
            raise RuntimeError("A cue sequence can only be started once")

        self._started = True
        self._index = 0
        self._deadline = now + self._cues[0].duration
        return self._cues[0].on

    def update(self, now: float) -> tuple[bool | None, bool]:
        """Return a changed LED state, if any, and whether the sequence ended."""
        if not self._started:
            raise RuntimeError("Start the cue sequence before updating it")
        if self._finished:
            return None, True

        changed_state: bool | None = None
        while now >= self._deadline:
            self._index += 1
            if self._index >= len(self._cues):
                self._finished = True
                return changed_state, True

            cue = self._cues[self._index]
            self._deadline += cue.duration
            changed_state = cue.on

        return changed_state, False

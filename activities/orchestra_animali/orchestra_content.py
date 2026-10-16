"""Orchestra Animali — the Animal Band roster and musical constants.

Pure data, no pygame. The band is six canonical cast musicians, each with
one shared-library instrument (``prop.instrument.*``), plus the rainbow
xylophone at the front of the stage. Loud/soft (dynamics) and fast/slow
(tempo) are properties of the whole band, chosen by the child.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
# Unchanged key: the saved payload is migrated forward in place
# (legacy ``{"stars": n}`` keeps its stars and gains a level).
STORAGE_KEY: Final = "orchestra_animali.state.v3"


@dataclass(frozen=True, slots=True)
class Musician:
    """One band member: a canonical cast friend and the instrument they play."""

    instrument: str
    character: str

    @property
    def prop_id(self) -> str:
        return f"prop.instrument.{self.instrument}"

    @property
    def character_id(self) -> str:
        return f"character.{self.character}"


# Left to right on the stage. Number keys 1-6 play them in this order.
BAND: Final[tuple[Musician, ...]] = (
    Musician("drum", "leo"),
    Musician("maracas", "momo"),
    Musician("bells", "lilli"),
    Musician("trumpet", "tito"),
    Musician("tambourine", "flash"),
    Musician("keyboard", "dani"),
)
# Momo loves music: Momo hosts the end-of-concert scene.
BAND_LEADER: Final = "momo"

# Rainbow xylophone, C major octave (low -> high, long -> short bars).
XYLOPHONE_COLORS: Final[tuple[tuple[int, int, int], ...]] = (
    (240, 92, 86),
    (247, 148, 62),
    (255, 205, 64),
    (118, 196, 96),
    (68, 184, 174),
    (78, 146, 222),
    (140, 112, 214),
    (226, 108, 176),
)
NOTE_FREQS: Final[tuple[float, ...]] = (261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25)


class Dynamics(StrEnum):
    """How loudly the band (and the child's taps) play."""

    SOFT = "soft"
    LOUD = "loud"

    @property
    def volume(self) -> float:
        return 0.3 if self is Dynamics.SOFT else 1.0


class Tempo(StrEnum):
    """How fast the band sways and plays its echo patterns."""

    SLOW = "slow"
    FAST = "fast"

    @property
    def beat_seconds(self) -> float:
        return 0.66 if self is Tempo.SLOW else 0.4


SESSION_ECHOES: Final = 5
LEVEL_MIN: Final = 1
LEVEL_MAX: Final = 5


__all__ = [
    "BAND",
    "BAND_LEADER",
    "Dynamics",
    "LEVEL_MAX",
    "LEVEL_MIN",
    "Musician",
    "NOTE_FREQS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SESSION_ECHOES",
    "STORAGE_KEY",
    "Tempo",
    "XYLOPHONE_COLORS",
]

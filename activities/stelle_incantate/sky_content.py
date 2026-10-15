"""Stelle Incantate — figure catalogue and scene geometry (no pygame).

The reference canvas is 1024x600 logical pixels. The night sky play area is
``SKY_ORIGIN`` + ``SKY_SIZE``; every figure's stars are authored in that
sky-local pixel space, which is also the viewBox of the figure's picture
(``assets/source/figures/<id>.svg`` -> ``assets/runtime/figures/<id>.png``),
so the revealed illustration lines up with the stars exactly.

``stars`` are listed in counting order (path order). The numbers a child sees
are assigned by the stage (start at 1, count on from a given star, count back
to 1, or teens 10 -> 20), never stored here. ``edges`` are index pairs; an edge
is drawn once both of its stars are lit, so branching figures (the swan's
wings, the hunter's belt) stay one unambiguous counting path.

Five figures are simplified stick figures of real constellations (their
voiced curiosity facts stay truthful); the others are friendly Greia sky
pictures for the bigger number ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

# Kept from the first release so existing child saves load (schema migrates).
STORAGE_KEY: Final[str] = "stelle_incantate.progress.v1"

# -- scene geometry (reference logical pixels) --------------------------------

SKY_ORIGIN: Final[tuple[int, int]] = (150, 92)
SKY_SIZE: Final[tuple[int, int]] = (820, 372)

STAR_SIZE: Final[int] = 78  # drawn star sprite
STAR_POP_SIZE: Final[int] = 92  # pop / hint size
STAR_TARGET: Final[int] = 92  # square hit + focus box
MIN_STAR_SPACING: Final[int] = 94  # targets of one figure never overlap

LEO_MIDBOTTOM: Final[tuple[int, int]] = (96, 596)
LEO_HEIGHT: Final[int] = 178

CARD_SIZE: Final[tuple[int, int]] = (104, 118)
CARD_CENTER: Final[tuple[int, int]] = (560, 533)
CARD_GAP: Final[int] = 30

NEXT_CENTER: Final[tuple[int, int]] = (940, 526)
NEXT_SIZE: Final[int] = 104
FACT_CENTER: Final[tuple[int, int]] = (240, 540)
FACT_SIZE: Final[int] = 80
BAND_CENTER: Final[tuple[int, int]] = (575, 538)  # name plate / fact bubble


def sky_point(local: tuple[int, int]) -> tuple[int, int]:
    """Sky-local pixel -> reference canvas pixel."""

    return (SKY_ORIGIN[0] + local[0], SKY_ORIGIN[1] + local[1])


@dataclass(frozen=True, slots=True)
class Figure:
    """One connect-the-stars figure and the picture it reveals."""

    figure_id: str
    stars: tuple[tuple[int, int], ...]
    edges: tuple[tuple[int, int], ...]
    real: bool = False  # a real constellation with a voiced curiosity fact

    @property
    def star_count(self) -> int:
        return len(self.stars)

    @property
    def name_key(self) -> str:
        return f"constellation.{self.figure_id}.name"

    @property
    def fact_key(self) -> str | None:
        return f"curiosity.{self.figure_id}.fact" if self.real else None

    @property
    def picture(self) -> str:
        return f"{self.figure_id}.png"

    def centre(self) -> tuple[int, int]:
        """Reference-canvas centre of the star figure (for celebration FX)."""

        xs = [x for x, _ in self.stars]
        ys = [y for _, y in self.stars]
        return sky_point(((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2))


def _figure(figure_id: str, stars, edges, *, real: bool = False) -> Figure:
    return Figure(figure_id, tuple(stars), tuple(edges), real)


# -- small figures: five stars (numbers 1-5) ---------------------------------

KITE = _figure(
    "aquilone",
    ((380, 36), (476, 138), (380, 262), (284, 138), (536, 334)),
    ((0, 1), (1, 2), (2, 3), (3, 0), (2, 4)),
)
HOUSE = _figure(
    "casetta",
    ((300, 330), (300, 184), (410, 62), (520, 184), (520, 330)),
    ((0, 1), (1, 2), (2, 3), (3, 4), (4, 0), (1, 3)),
)
CROWN = _figure(  # Cassiopeia's W is the top of a queen's crown
    "cassiopea",
    ((220, 112), (318, 214), (410, 92), (504, 214), (600, 112)),
    ((0, 1), (1, 2), (2, 3), (3, 4)),
    real=True,
)
SWAN = _figure(  # Cygnus: tail, heart, head, then the two wing tips
    "cigno",
    ((190, 170), (396, 188), (620, 236), (432, 48), (360, 326)),
    ((0, 1), (1, 2), (1, 3), (1, 4)),
    real=True,
)
FISH = _figure(  # the crossed-tail "alpha" fish
    "pesce",
    ((210, 96), (420, 290), (610, 190), (420, 92), (210, 286)),
    ((0, 1), (1, 2), (2, 3), (3, 4), (4, 0)),
)

# -- medium figures: seven to ten stars (numbers up to 10) -------------------

BEAR = _figure(  # the Big Dipper is the Great Bear's tail and back
    "carro",
    ((110, 110), (220, 146), (318, 186), (412, 180), (570, 150), (586, 262), (432, 282)),
    ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 3)),
    real=True,
)
LION = _figure(  # Leo: tail, back, neck, mane, face, jaw, chest, hip
    "leone",
    ((100, 196), (276, 140), (470, 152), (530, 50), (650, 92), (664, 206), (520, 276), (300, 270)),
    ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 1)),
    real=True,
)
HUNTER = _figure(  # Orion: club, shoulder, head, shoulder, shield, belt, feet
    "orione",
    (
        (196, 44), (296, 124), (418, 40), (540, 132), (650, 176),
        (520, 230), (420, 214), (320, 222), (262, 338), (566, 338),
    ),
    ((0, 1), (1, 2), (2, 3), (3, 4), (3, 5), (5, 6), (6, 7), (7, 1), (7, 8), (5, 9)),
    real=True,
)
ROCKET = _figure(
    "razzo",
    ((410, 30), (484, 132), (566, 330), (472, 262), (348, 262), (254, 330), (336, 132)),
    ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 0)),
)
BOAT = _figure(  # keel, bow, mast foot, mast top, sail corner, stern, keel
    "barca",
    ((290, 322), (196, 236), (400, 240), (400, 40), (570, 176), (636, 248), (540, 322)),
    ((0, 1), (1, 2), (2, 3), (3, 4), (4, 2), (2, 5), (5, 6), (6, 0)),
)

# -- teen figures: eleven stars (anchor 10, then 11-20) ----------------------

BUTTERFLY = _figure(
    "farfalla",
    (
        (410, 112), (340, 36), (480, 36), (620, 62), (526, 196), (600, 322),
        (410, 304), (220, 322), (294, 196), (200, 62), (410, 208),
    ),
    (
        (0, 1), (0, 2), (0, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8),
        (8, 9), (9, 0), (10, 0), (10, 6),
    ),
)
WHALE = _figure(
    "balena",
    (
        (110, 214), (226, 124), (246, 30), (400, 96), (556, 138), (656, 204),
        (742, 116), (748, 292), (548, 290), (380, 316), (218, 292),
    ),
    (
        (0, 1), (1, 2), (1, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 5),
        (5, 8), (8, 9), (9, 10), (10, 0),
    ),
)

ALL_FIGURES: Final[tuple[Figure, ...]] = (
    KITE, HOUSE, CROWN, SWAN, FISH,
    BEAR, LION, HUNTER, ROCKET, BOAT,
    BUTTERFLY, WHALE,
)
FIGURES_BY_ID: Final[dict[str, Figure]] = {figure.figure_id: figure for figure in ALL_FIGURES}

SMALL: Final[tuple[str, ...]] = ("aquilone", "casetta", "cassiopea", "cigno", "pesce")
MEDIUM: Final[tuple[str, ...]] = ("carro", "leone", "orione", "razzo", "barca")
TEEN: Final[tuple[str, ...]] = ("farfalla", "balena")


__all__ = [
    "ALL_FIGURES",
    "BAND_CENTER",
    "CARD_CENTER",
    "CARD_GAP",
    "CARD_SIZE",
    "FACT_CENTER",
    "FACT_SIZE",
    "FIGURES_BY_ID",
    "Figure",
    "LEO_HEIGHT",
    "LEO_MIDBOTTOM",
    "MEDIUM",
    "MIN_STAR_SPACING",
    "NEXT_CENTER",
    "NEXT_SIZE",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SKY_ORIGIN",
    "SKY_SIZE",
    "SMALL",
    "STAR_POP_SIZE",
    "STAR_SIZE",
    "STAR_TARGET",
    "STORAGE_KEY",
    "TEEN",
    "sky_point",
]

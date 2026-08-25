"""Constellation catalogue for Stelle Incantate.

Coordinates are normalized inside the sky play area (0..1 on both axes,
y grows downward). ``stars`` are listed in child connection order: star 1 is
the first big number the child taps. ``edges`` are index pairs into ``stars``;
an edge is drawn when both of its stars are connected, so branch shapes such
as Cygnus stay one unambiguous connect-the-dots path.

All shapes are simplified stick figures of real IAU constellations so the
curiosity facts remain truthful about what the child just drew.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SkyStar:
    """One connectable star of a constellation figure."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Constellation:
    """One real constellation presented as a connect-the-dots figure."""

    constellation_id: str
    name_key: str
    fact_key: str
    stars: tuple[SkyStar, ...]
    edges: tuple[tuple[int, int], ...]

    @property
    def star_count(self) -> int:
        return len(self.stars)


def _constellation(
    constellation_id: str,
    stars: tuple[tuple[float, float], ...],
    edges: tuple[tuple[int, int], ...],
) -> Constellation:
    return Constellation(
        constellation_id=constellation_id,
        name_key=f"constellation.{constellation_id}.name",
        fact_key=f"curiosity.{constellation_id}.fact",
        stars=tuple(SkyStar(x=x, y=y) for x, y in stars),
        edges=edges,
    )


TRIANGOLO = _constellation(
    "triangolo",
    ((0.50, 0.16), (0.28, 0.78), (0.74, 0.70)),
    ((0, 1), (1, 2), (2, 0)),
)

CASSIOPEA = _constellation(
    "cassiopea",
    ((0.12, 0.48), (0.31, 0.70), (0.50, 0.38), (0.69, 0.70), (0.88, 0.46)),
    ((0, 1), (1, 2), (2, 3), (3, 4)),
)

CIGNO = _constellation(
    "cigno",
    ((0.48, 0.10), (0.50, 0.44), (0.52, 0.86), (0.20, 0.52), (0.80, 0.50)),
    ((0, 1), (1, 2), (1, 3), (1, 4)),
)

GRANDE_CARRO = _constellation(
    "carro",
    (
        (0.14, 0.62),
        (0.27, 0.44),
        (0.44, 0.42),
        (0.56, 0.58),
        (0.70, 0.48),
        (0.80, 0.26),
        (0.92, 0.38),
    ),
    ((0, 1), (1, 2), (2, 3), (3, 0), (3, 4), (4, 5), (5, 6)),
)

LEONE = _constellation(
    "leone",
    (
        (0.26, 0.66),
        (0.36, 0.50),
        (0.34, 0.32),
        (0.46, 0.18),
        (0.60, 0.22),
        (0.72, 0.36),
        (0.88, 0.56),
    ),
    ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6)),
)

ORIONE = _constellation(
    "orione",
    (
        (0.28, 0.18),
        (0.40, 0.48),
        (0.50, 0.50),
        (0.60, 0.52),
        (0.72, 0.20),
        (0.64, 0.84),
        (0.34, 0.86),
    ),
    ((0, 1), (4, 3), (1, 2), (2, 3), (1, 6), (3, 5)),
)

#: Child progression order: fewest points and simplest silhouettes first.
CONSTELLATION_ORDER: tuple[str, ...] = (
    "triangolo",
    "cassiopea",
    "cigno",
    "carro",
    "leone",
    "orione",
)

CONSTELLATIONS_BY_ID: dict[str, Constellation] = {
    item.constellation_id: item
    for item in (TRIANGOLO, CASSIOPEA, CIGNO, GRANDE_CARRO, LEONE, ORIONE)
}


def ordered_constellations() -> tuple[Constellation, ...]:
    """Return the catalogue in child progression order."""

    return tuple(CONSTELLATIONS_BY_ID[constellation_id] for constellation_id in CONSTELLATION_ORDER)

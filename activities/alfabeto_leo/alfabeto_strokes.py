"""Stroke-order letter shapes for L'Alfabeto di Leo (capital print letters).

Every letter is a short list of strokes in the order a child is taught to
write them (top-down, left-to-right; round letters start at the top right or
the top). A stroke is a polyline in *letter units*: the cap height runs from
``y = 0`` (top) to ``y = 100`` (baseline) and ``x`` grows to the right. Curves
are sampled once at import from arcs and cubic Béziers, so drawing and
tracing only ever walk point lists.

The same strokes render the letters on the choice tiles, the hollow tracing
guide and the child's ink, so the letter a child traces is exactly the letter
they find. Pure data: no Pygame import.
"""

from __future__ import annotations

import math
from typing import Final, Sequence

Point = tuple[float, float]
Stroke = tuple[Point, ...]

CAP_HEIGHT: Final = 100.0
# Band width of a printed letter, in letter units (≈ a fat child's marker).
STROKE_WIDTH: Final = 15.0
_ARC_STEPS: Final = 28
_BEZIER_STEPS: Final = 18


def _arc(cx: float, cy: float, rx: float, ry: float, start: float, end: float) -> list[Point]:
    """Sample an elliptical arc from ``start`` to ``end`` degrees (y grows down)."""

    span = end - start
    steps = max(4, int(abs(span) / 360.0 * _ARC_STEPS * 2))
    points = []
    for index in range(steps + 1):
        angle = math.radians(start + span * index / steps)
        points.append((round(cx + rx * math.cos(angle), 2), round(cy + ry * math.sin(angle), 2)))
    return points


def _bezier(p0: Point, p1: Point, p2: Point, p3: Point) -> list[Point]:
    points = []
    for index in range(_BEZIER_STEPS + 1):
        t = index / _BEZIER_STEPS
        u = 1.0 - t
        x = u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0]
        y = u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]
        points.append((round(x, 2), round(y, 2)))
    return points


def _join(*parts: Sequence[Point]) -> Stroke:
    """Concatenate stroke parts, dropping duplicated joint points."""

    joined: list[Point] = []
    for part in parts:
        for point in part:
            if not joined or math.dist(joined[-1], point) > 0.01:
                joined.append(point)
    return tuple(joined)


def _line(*points: Point) -> Stroke:
    return tuple(points)


_O_RING = _arc(46, 50, 42, 50, -90, -450)
_P_BOWL = _join([(10, 0), (38, 0)], _arc(38, 27, 30, 27, -90, 90), [(10, 54)])
_N_BODY = _line((10, 100), (10, 0), (70, 100), (70, 0))

LETTER_STROKES: Final[dict[str, tuple[Stroke, ...]]] = {
    "A": (_line((40, 0), (6, 100)), _line((40, 0), (74, 100)), _line((19, 64), (61, 64))),
    "B": (
        _line((10, 0), (10, 100)),
        _join([(10, 0), (40, 0)], _arc(40, 24, 26, 24, -90, 90), [(10, 48)]),
        _join([(10, 48), (44, 48)], _arc(44, 74, 28, 26, -90, 90), [(10, 100)]),
    ),
    "C": (_join(_arc(46, 50, 42, 50, -42, -318)),),
    "D": (
        _line((10, 0), (10, 100)),
        _join([(10, 0), (30, 0)], _arc(30, 50, 44, 50, -90, 90), [(10, 100)]),
    ),
    "E": (
        _line((12, 0), (12, 100)),
        _line((12, 0), (66, 0)),
        _line((12, 50), (58, 50)),
        _line((12, 100), (66, 100)),
    ),
    "F": (_line((12, 0), (12, 100)), _line((12, 0), (66, 0)), _line((12, 50), (58, 50))),
    "G": (_join(_arc(46, 50, 42, 50, -42, -360), [(56, 50)]),),
    "H": (_line((10, 0), (10, 100)), _line((70, 0), (70, 100)), _line((10, 50), (70, 50))),
    "I": (_line((30, 0), (30, 100)), _line((8, 0), (52, 0)), _line((8, 100), (52, 100))),
    "J": (_join([(58, 0), (58, 70)], _arc(32, 70, 26, 30, 0, 180)),),
    "K": (_line((10, 0), (10, 100)), _line((66, 0), (14, 54), (70, 100))),
    "L": (_line((12, 0), (12, 100), (64, 100)),),
    "M": (_line((8, 100), (8, 0), (44, 64), (80, 0), (80, 100)),),
    "N": (_N_BODY,),
    "O": (_join(_O_RING),),
    "P": (_line((10, 0), (10, 100)), _P_BOWL),
    "Q": (_join(_O_RING), _line((54, 70), (88, 104))),
    "R": (_line((10, 0), (10, 100)), _P_BOWL, _line((36, 54), (72, 100))),
    "S": (
        _join(
            _bezier((70, 16), (64, 1), (24, -6), (17, 22)),
            _bezier((17, 22), (12, 42), (38, 47), (46, 51)),
            _bezier((46, 51), (64, 59), (80, 70), (72, 88)),
            _bezier((72, 88), (63, 106), (22, 105), (9, 84)),
        ),
    ),
    "T": (_line((6, 0), (74, 0)), _line((40, 0), (40, 100))),
    "U": (_join([(10, 0), (10, 64)], _arc(40, 64, 30, 36, 180, 0), [(70, 0)]),),
    "V": (_line((6, 0), (40, 100), (74, 0)),),
    "W": (_line((4, 0), (24, 100), (48, 32), (72, 100), (92, 0)),),
    "X": (_line((8, 0), (72, 100)), _line((72, 0), (8, 100))),
    "Y": (_line((6, 0), (40, 50)), _line((74, 0), (40, 50), (40, 100))),
    "Z": (_line((8, 0), (70, 0), (8, 100), (72, 100)),),
    # Spanish Ñ: the N, then the tilde above it (a separate final stroke).
    "Ñ": (_N_BODY, _join(_bezier((12, -26), (26, -44), (54, -6), (68, -28)))),
}


def strokes_for(char: str) -> tuple[Stroke, ...]:
    """Return the taught strokes of one capital letter (KeyError if unknown)."""

    return LETTER_STROKES[char.upper()]


def letter_bounds(char: str) -> tuple[float, float, float, float]:
    """Bounding box ``(left, top, right, bottom)`` of the stroke centre lines."""

    points = [point for stroke in strokes_for(char) for point in stroke]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def resample(points: Sequence[Point], spacing: float) -> list[Point]:
    """Return points spaced ``spacing`` apart along the polyline (ends kept)."""

    if len(points) < 2:
        return list(points)
    spacing = max(0.5, float(spacing))
    result = [points[0]]
    carry = 0.0
    for start, end in zip(points, points[1:]):
        segment = math.dist(start, end)
        if segment <= 0:
            continue
        position = spacing - carry
        while position <= segment:
            t = position / segment
            result.append((start[0] + (end[0] - start[0]) * t, start[1] + (end[1] - start[1]) * t))
            position += spacing
        carry = segment - (position - spacing)
    if math.dist(result[-1], points[-1]) > 0.01:
        result.append(points[-1])
    return result


__all__ = [
    "CAP_HEIGHT",
    "LETTER_STROKES",
    "STROKE_WIDTH",
    "Point",
    "Stroke",
    "letter_bounds",
    "resample",
    "strokes_for",
]

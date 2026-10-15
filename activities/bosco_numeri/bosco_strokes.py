"""Stroke-order numeral shapes 0–10 for Tito's Number Forest.

Every numeral is a short list of strokes in the order children are taught to
write them (start at the top; ``0`` and ``6`` curl left first; ``5`` is
"down, round the belly, then the hat"; ``4`` is "down-across, then the long
line"). A stroke is a polyline in *numeral units*: the height runs from
``y = 0`` (top) to ``y = 100`` (baseline) and ``x`` grows to the right.
Curves are sampled once at import from arcs and cubic Béziers, so drawing and
tracing only ever walk point lists. ``10`` is written as a ``1`` followed by
a ``0``.

The same strokes render the numerals on the choice tiles, the hollow tracing
guide and the child's ink, so the numeral a child traces is exactly the one
they find. Pure data: no Pygame import.
"""

from __future__ import annotations

import math
from typing import Final, Sequence

Point = tuple[float, float]
Stroke = tuple[Point, ...]

NUMERAL_HEIGHT: Final = 100.0
# Band width of a printed numeral, in numeral units (≈ a fat child's marker).
STROKE_WIDTH: Final = 15.0
# Horizontal offset of the second digit of 10.
TEN_ADVANCE: Final = 62.0
_ARC_STEPS: Final = 28
_BEZIER_STEPS: Final = 18


def _arc(cx: float, cy: float, rx: float, ry: float, start: float, end: float) -> list[Point]:
    """Sample an elliptical arc from ``start`` to ``end`` degrees (y grows down).

    Increasing angles run clockwise on screen, decreasing ones anticlockwise.
    """

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


def _shift(strokes: tuple[Stroke, ...], dx: float) -> tuple[Stroke, ...]:
    return tuple(tuple((round(x + dx, 2), y) for x, y in stroke) for stroke in strokes)


_TWO_TOP: Final = _arc(37, 29, 28, 29, 198, 378)
_FIVE_BELLY: Final = _arc(37, 68, 31, 31, 226, 500)

# Start at the top and curl left (anticlockwise), all the way round.
_ZERO: Final = (_join(_arc(34, 50, 30, 50, -90, -450)),)
# The little flag, then straight down.
_ONE: Final = (_line((12, 26), (38, 0), (38, 100)),)

NUMERAL_STROKES: Final[dict[int, tuple[Stroke, ...]]] = {
    0: _ZERO,
    1: _ONE,
    # Round the top, slide down to the left, then along the bottom.
    2: (
        _join(
            _TWO_TOP,
            _bezier(_TWO_TOP[-1], (58, 58), (28, 78), (8, 100)),
            [(70, 100)],
        ),
    ),
    # Two bumps: round to the middle, round again to the bottom.
    3: (_join(_arc(34, 25, 27, 25, 205, 450), _arc(34, 75, 31, 25, 270, 520)),),
    # Down and across, then the long line down.
    4: (_line((50, 0), (6, 64), (78, 64)), _line((56, 0), (56, 100))),
    # Down, round the belly, then the hat.
    5: (_join([(16, 0), _FIVE_BELLY[0]], _FIVE_BELLY), _line((16, 0), (66, 0))),
    # From the top right, down the left side and round into the loop.
    6: (_join(_bezier((60, 4), (34, -6), (8, 26), (8, 70)), _arc(37, 70, 29, 29, 180, -176)),),
    # Along the top, then the long slide down.
    7: (_line((6, 0), (70, 0), (26, 100)),),
    # An S down to the bottom, then back up to the top.
    8: (
        _join(
            _bezier((60, 14), (54, -3), (12, -4), (12, 22)),
            _bezier((12, 22), (12, 42), (62, 50), (62, 74)),
            _bezier((62, 74), (62, 104), (8, 104), (8, 74)),
            _bezier((8, 74), (8, 50), (58, 42), (58, 18)),
        ),
    ),
    # Round the little loop (anticlockwise), then the line down.
    9: (_join(_arc(34, 29, 29, 29, -8, -360), [(62, 100)]),),
    10: _ONE + _shift(_ZERO, TEN_ADVANCE),
}


def strokes_for(value: int) -> tuple[Stroke, ...]:
    """Return the taught strokes of one numeral 0–10 (KeyError if unknown)."""

    return NUMERAL_STROKES[int(value)]


def numeral_bounds(value: int) -> tuple[float, float, float, float]:
    """Bounding box ``(left, top, right, bottom)`` of the stroke centre lines."""

    points = [point for stroke in strokes_for(value) for point in stroke]
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
    "NUMERAL_HEIGHT",
    "NUMERAL_STROKES",
    "STROKE_WIDTH",
    "Point",
    "Stroke",
    "numeral_bounds",
    "resample",
    "strokes_for",
]

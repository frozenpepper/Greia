"""Forgiving stroke-order tracing for L'Alfabeto di Leo.

``TraceGuide`` places one letter's strokes inside a logical rectangle and
samples them evenly. ``TraceTracker`` follows a finger (or pointer) along the
*current* stroke only, in its taught direction:

* a touch counts when it lands near the stroke's traced end (or a little
  ahead of it), so a child can lift the finger and carry on;
* each move advances to the furthest stroke sample within ``tolerance`` of
  the finger, but never more than ``lookahead`` along the stroke at once, so a
  shortcut across a loop (the end of an ``O`` is next to its start) never
  completes it and starting from the wrong end does nothing;
* nothing ever goes backwards or is "wrong": straying simply pauses the ink.

Keyboard/controller children press the action button and the stroke traces
itself ("follow the dot", ``auto_advance``), so tracing is never pointer-only.
Pure geometry: no Pygame import.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Final, Sequence

if __package__:
    from .alfabeto_strokes import CAP_HEIGHT, STROKE_WIDTH, Point, letter_bounds, resample, strokes_for
else:
    from alfabeto_strokes import CAP_HEIGHT, STROKE_WIDTH, Point, letter_bounds, resample, strokes_for

SAMPLE_SPACING: Final = 4.0
# Fraction of the band width a finger may stray and still trace (generous).
TOLERANCE_BANDS: Final = 1.55
LOOKAHEAD_BANDS: Final = 2.2
# A stroke completes this close (in band widths) to its end.
FINISH_BANDS: Final = 0.45


class TraceEvent(StrEnum):
    NONE = "none"
    ADVANCED = "advanced"
    STROKE_DONE = "stroke_done"
    LETTER_DONE = "letter_done"


@dataclass(frozen=True, slots=True)
class StrokePath:
    """One stroke in logical pixels, evenly sampled, with cumulative lengths."""

    points: tuple[Point, ...]
    distances: tuple[float, ...]

    @classmethod
    def from_points(cls, points: Sequence[Point]) -> "StrokePath":
        sampled = resample(points, SAMPLE_SPACING)
        distances = [0.0]
        for start, end in zip(sampled, sampled[1:]):
            distances.append(distances[-1] + math.dist(start, end))
        return cls(tuple(sampled), tuple(distances))

    @property
    def length(self) -> float:
        return self.distances[-1]

    @property
    def start(self) -> Point:
        return self.points[0]

    def index_at(self, distance: float) -> int:
        return min(len(self.points) - 1, bisect_left(self.distances, max(0.0, distance)))

    def point_at(self, distance: float) -> Point:
        distance = max(0.0, min(self.length, distance))
        index = self.index_at(distance)
        if index == 0:
            return self.points[0]
        before, after = self.distances[index - 1], self.distances[index]
        t = 0.0 if after <= before else (distance - before) / (after - before)
        (x0, y0), (x1, y1) = self.points[index - 1], self.points[index]
        return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)

    def direction_at(self, distance: float) -> Point:
        """Unit direction of travel at ``distance`` (for the start arrow)."""

        ahead = self.point_at(distance + 10.0)
        here = self.point_at(distance)
        dx, dy = ahead[0] - here[0], ahead[1] - here[1]
        norm = math.hypot(dx, dy) or 1.0
        return (dx / norm, dy / norm)


@dataclass(frozen=True, slots=True)
class TraceGuide:
    """A letter's strokes fitted (centred, uniform scale) into a logical box."""

    char: str
    strokes: tuple[StrokePath, ...]
    band: float
    scale: float
    origin: Point

    @classmethod
    def fit(cls, char: str, box: tuple[int, int, int, int]) -> "TraceGuide":
        x, y, width, height = box
        left, top, right, bottom = letter_bounds(char)
        pad = STROKE_WIDTH  # half a band each side plus breathing room
        span_w = right - left + pad
        span_h = max(CAP_HEIGHT, bottom - top) + pad
        scale = min(width / span_w, height / span_h)
        ox = x + width / 2 - (left + right) / 2 * scale
        oy = y + height / 2 - (top + bottom) / 2 * scale
        strokes = tuple(
            StrokePath.from_points([(ox + px * scale, oy + py * scale) for px, py in stroke])
            for stroke in strokes_for(char)
        )
        return cls(char, strokes, STROKE_WIDTH * scale, scale, (ox, oy))


class TraceTracker:
    """Follow one child along a ``TraceGuide`` stroke by stroke."""

    def __init__(self, guide: TraceGuide) -> None:
        self.guide = guide
        self.tolerance = guide.band * TOLERANCE_BANDS
        self.lookahead = guide.band * LOOKAHEAD_BANDS
        self._finish = guide.band * FINISH_BANDS
        self.stroke_index = 0
        self.progress = 0.0
        self.dragging = False

    # -- queries -----------------------------------------------------------------
    @property
    def complete(self) -> bool:
        return self.stroke_index >= len(self.guide.strokes)

    @property
    def stroke(self) -> StrokePath | None:
        return None if self.complete else self.guide.strokes[self.stroke_index]

    @property
    def head(self) -> Point | None:
        """Where the ink currently ends on the active stroke."""

        stroke = self.stroke
        return None if stroke is None else stroke.point_at(self.progress)

    @property
    def fraction(self) -> float:
        total = sum(stroke.length for stroke in self.guide.strokes) or 1.0
        done = sum(stroke.length for stroke in self.guide.strokes[: self.stroke_index])
        return min(1.0, (done + (0.0 if self.complete else self.progress)) / total)

    # -- pointer -----------------------------------------------------------------
    def begin(self, position: Point) -> bool:
        """Start a drag; True when the touch is on the active part of the stroke."""

        if self.complete:
            return False
        if self._nearest_ahead(position, allow_behind=True) is None:
            self.dragging = False
            return False
        self.dragging = True
        return True

    def move(self, position: Point) -> TraceEvent:
        if not self.dragging or self.complete:
            return TraceEvent.NONE
        found = self._nearest_ahead(position, allow_behind=False)
        if found is None or found <= self.progress:
            return TraceEvent.NONE
        self.progress = found
        return self._check_finished()

    def end(self) -> None:
        self.dragging = False

    # -- keyboard / controller / demonstration -------------------------------------
    def auto_advance(self, distance: float) -> TraceEvent:
        """Advance the active stroke by ``distance`` px ("follow the dot")."""

        if self.complete or distance <= 0:
            return TraceEvent.NONE
        self.progress = min(self.stroke.length, self.progress + distance)  # type: ignore[union-attr]
        return self._check_finished()

    # -- internals -----------------------------------------------------------------
    def _check_finished(self) -> TraceEvent:
        stroke = self.stroke
        assert stroke is not None
        if self.progress < stroke.length - self._finish:
            return TraceEvent.ADVANCED
        self.stroke_index += 1
        self.progress = 0.0
        if self.complete:
            self.dragging = False
            return TraceEvent.LETTER_DONE
        return TraceEvent.STROKE_DONE

    def _nearest_ahead(self, position: Point, *, allow_behind: bool) -> float | None:
        """Furthest-along sample within reach of ``position`` (None if none)."""

        stroke = self.stroke
        if stroke is None:
            return None
        low = self.progress - (self.tolerance if allow_behind else 0.0)
        high = self.progress + self.lookahead
        start = stroke.index_at(low)
        stop = stroke.index_at(high)
        limit = self.tolerance * self.tolerance
        best: float | None = None
        px, py = position
        for index in range(start, stop + 1):
            x, y = stroke.points[index]
            if (x - px) ** 2 + (y - py) ** 2 <= limit:
                best = stroke.distances[index]
        return best


__all__ = ["StrokePath", "TraceEvent", "TraceGuide", "TraceTracker"]

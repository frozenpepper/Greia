"""Timing model for the post-Activity badge celebration (ADR 0025).

The celebration is one short, bounded *character moment* on the child's Home
after an Activity returns control to the Shell::

    INTRO    card scales in, badge overshoots and settles, sparkles appear;
             the greeter reacts and (first badge only) says one cheer clip
    WAITING  completely static until the child taps / presses a key —
             the Shell loop presents zero frames here
    FLIGHT   the badge shrinks and flies into the Home star, then the star
             bounces once and its count goes up

This module is pure timing: it knows *what* each frame shows (card scale,
badge size and flight progress, sparkle frame, star scale) and *when* the next
visible change is due. It owns no surfaces and no pygame state, so the
pacing/keyframe contract is unit-testable without a display. The launcher
mixin (``achievement_presentation``) paints the frames with pre-scaled cached
sprites and dirty rectangles.

Frames are discrete keyframes at most ``FRAME_FPS`` apart, and badge sizes
snap to a handful of fixed values so the bounded badge renderer prepares a
few small surfaces once per badge instead of scaling every frame.
"""

from __future__ import annotations

import bisect
import enum
from dataclasses import dataclass

FRAME_FPS = 24
_STEP = 1.0 / FRAME_FPS

# Badge sizes (px) the celebration can show. Intro: grow, overshoot, settle.
# Flight: shrink towards the star. Kept tiny so every size is one cached
# badge surface.
BADGE_REST_SIZE = 126
INTRO_BADGE_SIZES = (84, 112, 146, 136, BADGE_REST_SIZE)
FLIGHT_BADGE_SIZES = (96, 72, 56, 44)
# Star bounce scales; each is one cached star icon size.
STAR_SCALES = (1.0, 1.12, 1.25)

FIRST_INTRO_SECONDS = 0.55
LATER_INTRO_SECONDS = 0.25
FLIGHT_SECONDS = 8 / FRAME_FPS  # 0.333 s: whole frames, no short last step
BOUNCE_SECONDS = 0.24
SPARKLE_FRAME_SECONDS = 0.12
# The longest uninterrupted animated stretch must stay within this budget.
MAX_ANIMATED_SECONDS = 0.9


class CelebrationPhase(enum.Enum):
    INTRO = "intro"
    WAITING = "waiting"
    FLIGHT = "flight"
    DONE = "done"


@dataclass(frozen=True, slots=True)
class CelebrationFrame:
    """Everything the painter needs for one visible celebration frame.

    ``card_scale`` is ``None`` once the card has gone (flight). ``flight`` is
    the 0..1 progress of the badge from the card centre to the star; ``None``
    while the badge sits on the card or after it has landed.
    """

    card_scale: float | None
    badge_size: int | None
    flight: float | None
    sparkle_frame: int | None
    show_text: bool
    star_scale: float
    landed: bool


def _ease_out(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return 1.0 - (1.0 - t) * (1.0 - t)


def _ease_in(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t


class CelebrationTimeline:
    """Deterministic keyframes for one badge's celebration.

    ``first`` selects the full intro (voice, ~0.55 s). Later badges queued from
    the same Activity return get a quicker 0.25 s intro and no voice, so a
    multi-badge return never becomes a barrage.
    """

    def __init__(self, *, first: bool, sparkle_frames: int = 2) -> None:
        self.first = first
        self.intro_seconds = FIRST_INTRO_SECONDS if first else LATER_INTRO_SECONDS
        self.sparkle_frames = max(1, int(sparkle_frames))
        # The card is fully open (and the voice/cheer moment happens) here.
        self.reveal_at = 0.25 if first else 0.125
        self._intro = self._build_intro()
        self._flight = self._build_flight()

    # ------------------------------------------------------------- building
    def _build_intro(self) -> tuple[tuple[float, CelebrationFrame], ...]:
        frames: list[tuple[float, CelebrationFrame]] = []
        start_scale = 0.6 if self.first else 0.8
        reveal = self.reveal_at
        settle = self.intro_seconds
        for step in range(int(round(settle * FRAME_FPS)) + 1):
            t = step / FRAME_FPS
            if t >= settle - 1e-6:
                break
            if t < reveal - 1e-6:
                progress = _ease_out(t / reveal)
                card = start_scale + (1.0 - start_scale) * progress
                size = INTRO_BADGE_SIZES[min(2, int(progress * 3.0))] if self.first else (
                    112 if progress < 0.5 else 146
                )
                sparkle = None
                text = False
            else:
                card = 1.0
                after = (t - reveal) / max(1e-6, settle - reveal)
                size = 146 if after < 0.34 else (136 if after < 0.67 else BADGE_REST_SIZE)
                sparkle = int((t - reveal + 1e-6) / SPARKLE_FRAME_SECONDS) % self.sparkle_frames
                text = True
            frames.append(
                (
                    round(t, 4),
                    CelebrationFrame(
                        card_scale=round(card, 3),
                        badge_size=size,
                        flight=None,
                        sparkle_frame=sparkle,
                        show_text=text,
                        star_scale=1.0,
                        landed=False,
                    ),
                )
            )
        return _dedupe(frames)

    def _build_flight(self) -> tuple[tuple[float, CelebrationFrame], ...]:
        frames: list[tuple[float, CelebrationFrame]] = []
        for step in range(int(FLIGHT_SECONDS * FRAME_FPS) + 1):
            t = step / FRAME_FPS
            if t >= FLIGHT_SECONDS - 1e-6:
                break
            progress = _ease_in((t + _STEP) / FLIGHT_SECONDS)
            size = FLIGHT_BADGE_SIZES[min(3, int((t / FLIGHT_SECONDS) * 4.0))]
            frames.append(
                (
                    round(t, 4),
                    CelebrationFrame(None, size, round(progress, 3), None, False, 1.0, False),
                )
            )
        # Star bounce: 1.0 -> 1.25 -> 1.0, count already incremented.
        bounce = (STAR_SCALES[1], STAR_SCALES[2], STAR_SCALES[2], STAR_SCALES[1], STAR_SCALES[1])
        for index, scale in enumerate(bounce):
            frames.append(
                (
                    round(FLIGHT_SECONDS + index * (BOUNCE_SECONDS / len(bounce)), 4),
                    CelebrationFrame(None, None, None, None, False, scale, True),
                )
            )
        return _dedupe(frames)

    # ------------------------------------------------------------ querying
    @property
    def flight_seconds(self) -> float:
        return FLIGHT_SECONDS + BOUNCE_SECONDS

    @property
    def resting_frame(self) -> CelebrationFrame:
        """The static WAITING frame (card open, badge settled, sparkles on)."""

        return CelebrationFrame(1.0, BADGE_REST_SIZE, None, 0, True, 1.0, False)

    @property
    def landed_frame(self) -> CelebrationFrame:
        return CelebrationFrame(None, None, None, None, False, 1.0, True)

    def intro_frame(self, elapsed: float) -> CelebrationFrame:
        if elapsed >= self.intro_seconds:
            return self.resting_frame
        return _frame_at(self._intro, elapsed)

    def flight_frame(self, elapsed: float) -> CelebrationFrame:
        if elapsed >= self.flight_seconds:
            return self.landed_frame
        return _frame_at(self._flight, elapsed)

    def next_intro_change(self, elapsed: float) -> float | None:
        """Seconds until the intro shows something new (``None`` = static)."""

        return _next_change(self._intro, elapsed, self.intro_seconds)

    def next_flight_change(self, elapsed: float) -> float | None:
        return _next_change(self._flight, elapsed, self.flight_seconds)

    @property
    def intro_keyframes(self) -> tuple[tuple[float, CelebrationFrame], ...]:
        return self._intro

    @property
    def flight_keyframes(self) -> tuple[tuple[float, CelebrationFrame], ...]:
        return self._flight


def _dedupe(
    frames: list[tuple[float, CelebrationFrame]],
) -> tuple[tuple[float, CelebrationFrame], ...]:
    """Drop keyframes that look identical to their predecessor."""

    result: list[tuple[float, CelebrationFrame]] = []
    for item in frames:
        if result and result[-1][1] == item[1]:
            continue
        result.append(item)
    return tuple(result)


def _frame_at(
    frames: tuple[tuple[float, CelebrationFrame], ...], elapsed: float
) -> CelebrationFrame:
    times = [time for time, _frame in frames]
    index = max(0, bisect.bisect_right(times, max(0.0, elapsed)) - 1)
    return frames[index][1]


def _next_change(
    frames: tuple[tuple[float, CelebrationFrame], ...], elapsed: float, end: float
) -> float | None:
    if elapsed >= end:
        return None
    for time, _frame in frames:
        if time > elapsed + 1e-6:
            return time - elapsed
    return max(0.0, end - elapsed)


@dataclass(frozen=True, slots=True)
class LibraryHop:
    """The 0.8 s ``happy_hop`` of a tapped Badge Library badge.

    Pure offset curve (dy −18 / −28 / −12 / 0 px at the reference size,
    scaled by ``amplitude``) sampled at most ``FRAME_FPS`` times a second. The
    sprite itself is reused; only its position changes.
    """

    index: int
    started: float
    amplitude: float = 1.0

    DURATION = 0.8
    _KEYS = ((0.0, 0.0), (0.2, -18.0), (0.4, -28.0), (0.6, -12.0), (0.8, 0.0))

    def offset(self, now: float) -> int:
        t = now - self.started
        if t <= 0.0 or t >= self.DURATION:
            return 0
        for (t0, y0), (t1, y1) in zip(self._KEYS, self._KEYS[1:]):
            if t <= t1:
                share = (t - t0) / (t1 - t0)
                return int(round((y0 + (y1 - y0) * share) * self.amplitude))
        return 0

    def finished(self, now: float) -> bool:
        return now - self.started >= self.DURATION

    def next_change(self, now: float) -> float | None:
        if self.finished(now):
            return None
        return _STEP


__all__ = [
    "BADGE_REST_SIZE",
    "CelebrationFrame",
    "CelebrationPhase",
    "CelebrationTimeline",
    "FLIGHT_BADGE_SIZES",
    "FRAME_FPS",
    "INTRO_BADGE_SIZES",
    "LibraryHop",
    "MAX_ANIMATED_SECONDS",
    "STAR_SCALES",
]

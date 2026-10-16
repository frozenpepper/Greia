"""Orchestra Animali — presentation of the band stage.

``BandMotion`` holds the transient, bounded presentation state (strikes,
borrowed poses, lit bars, FX bursts, beat rings, the inviting musician's
speech bubble). ``OrchestraRenderer`` blits the prepared ``OrchestraArt`` in
one pass: stage → spotlight → musicians + instruments → lit bars → bubble →
FX. Motion is offsets only; nothing is decoded, scaled or rendered as text
per frame.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
import math
from typing import Final

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .orchestra_art import OrchestraArt
    from .orchestra_content import BAND, Dynamics, Tempo
    from .orchestra_layout import (
        BAR_RECTS,
        BUBBLE_HEIGHT,
        BUBBLE_ICON,
        BUBBLE_MAX_X,
        BUBBLE_MIN_X,
        BUBBLE_TOKEN,
        BUBBLE_TOP,
        CAST_HEIGHT,
        instrument_anchor,
        musician_anchor,
    )
    from .orchestra_model import XYLOPHONE_VOICE
else:  # pragma: no cover - runtime/script fallback
    from orchestra_art import OrchestraArt
    from orchestra_content import BAND, Dynamics, Tempo
    from orchestra_layout import (
        BAR_RECTS,
        BUBBLE_HEIGHT,
        BUBBLE_ICON,
        BUBBLE_MAX_X,
        BUBBLE_MIN_X,
        BUBBLE_TOKEN,
        BUBBLE_TOP,
        CAST_HEIGHT,
        instrument_anchor,
        musician_anchor,
    )
    from orchestra_model import XYLOPHONE_VOICE

STRIKE_SECONDS: Final = 0.32
BAR_LIT_SECONDS: Final = 0.35
RING_SECONDS: Final = 0.7
MAX_FX: Final = 24
MAX_RINGS: Final = 8
BEAT_UNIT: Final = 62  # bubble pixels per beat (rhythm is drawn to scale)
BUBBLE_PAD: Final = 16
BUBBLE_KEEP: Final = 8


@dataclass(slots=True)
class FxBurst:
    name: str
    center: tuple[int, int]
    start: float
    duration: float = 0.6
    rise: float = 0.0


@dataclass(slots=True)
class Bubble:
    """The inviting musician's bubble: ear (listen) or go (your turn) + tokens.

    ``tokens`` are ``(voice, position_in_beats)``; the bubble spans
    ``span_beats`` so a long gap looks long and a short gap looks short.
    """

    lead: int
    mode: str
    span_beats: float
    tokens: list[tuple[int, float]] = field(default_factory=list)


class BandMotion:
    """Bounded transient presentation state for one stage."""

    def __init__(self) -> None:
        count = len(BAND)
        self.strikes: list[float] = [-10.0] * count
        self.borrowed: dict[int, tuple[str, float]] = {}
        self.bars_lit: list[float] = [-10.0] * len(BAR_RECTS)
        self.fx: deque[FxBurst] = deque(maxlen=MAX_FX)
        self.rings: deque[tuple[tuple[int, int], float]] = deque(maxlen=MAX_RINGS)
        self.spotlight: int | None = None
        self.bubble: Bubble | None = None

    def strike(self, index: int, now: float) -> None:
        self.strikes[index] = now
        self.borrow(index, "pose_play", now + STRIKE_SECONDS + 0.1)

    def borrow(self, index: int, pose: str, until: float) -> None:
        self.borrowed[index] = (pose, until)

    def light_bar(self, index: int, now: float) -> None:
        self.bars_lit[index] = now

    def burst(self, name: str, center: tuple[int, int], now: float, *, duration: float = 0.6, rise: float = 0.0) -> None:
        self.fx.append(FxBurst(name, center, now, duration, rise))

    def ring(self, center: tuple[int, int], now: float) -> None:
        self.rings.append((center, now))

    def prune(self, now: float) -> None:
        for index, (_, until) in list(self.borrowed.items()):
            if until <= now:
                del self.borrowed[index]
        while self.fx and self.fx[0].start + self.fx[0].duration < now:
            self.fx.popleft()
        while self.rings and self.rings[0][1] + RING_SECONDS < now:
            self.rings.popleft()

    def active(self, now: float) -> bool:
        return (
            bool(self.borrowed)
            or bool(self.fx)
            or bool(self.rings)
            or any(now - at < STRIKE_SECONDS for at in self.strikes)
            or any(now - at < BAR_LIT_SECONDS for at in self.bars_lit)
        )

    def clear(self) -> None:
        self.__init__()


def sway(now: float, tempo: Tempo) -> int:
    """Band sway in px (quantised so an idle stage redraws only on change)."""

    period = tempo.beat_seconds * 2.0
    return int(round(math.sin(2.0 * math.pi * now / period) * 3.0))


class OrchestraRenderer:
    """Draw the band stage from prepared art (blits only)."""

    def __init__(self, art: OrchestraArt, feedback: Sequence[CastFeedback], *, clock: Callable[[], float]) -> None:
        self.art = art
        self.feedback = tuple(feedback)
        self._clock = clock
        self._bubbles: dict[tuple, pygame.Surface] = {}

    def draw(self, surface: pygame.Surface, motion: BandMotion, *, tempo: Tempo, dynamics: Dynamics) -> None:
        now = self._clock()
        surface.blit(self.art.background, (0, 0))
        if motion.spotlight is not None:
            x, y = musician_anchor(motion.spotlight)
            spot = self.art.spotlight
            surface.blit(spot, spot.get_rect(center=(x, y - 4)))
        bob = sway(now, tempo)
        hop = CAST_HEIGHT * (0.1 if dynamics is Dynamics.LOUD else 0.045)
        for index in range(len(BAND)):
            self._draw_musician(surface, motion, index, now, bob if index % 2 == 0 else -bob, hop)
        for index, rect in enumerate(BAR_RECTS):
            if now - motion.bars_lit[index] < BAR_LIT_SECONDS:
                surface.blit(self.art.bar_lit[index], rect.move(0, 3))
        if motion.bubble is not None:
            self._draw_bubble(surface, motion.bubble)
        for center, start in motion.rings:
            frames = self.art.fx_frames("beat_ring")
            if frames:
                frame = frames[int((now - start) / 0.18) % len(frames)]
                surface.blit(frame, frame.get_rect(center=center))
        for burst in motion.fx:
            self._draw_burst(surface, burst, now)

    # -- pieces ----------------------------------------------------------------------

    def _draw_musician(
        self, surface: pygame.Surface, motion: BandMotion, index: int, now: float, bob: int, hop: float
    ) -> None:
        x, y = musician_anchor(index)
        since = now - motion.strikes[index]
        lift = int(math.sin(math.pi * since / STRIKE_SECONDS) * hop) if 0 <= since < STRIKE_SECONDS else 0
        feedback = self.feedback[index]
        if feedback.pose is not CastPose.IDLE:
            feedback.draw(surface, (x, y))
        else:
            pose = "happy"
            borrowed = motion.borrowed.get(index)
            if borrowed is not None and borrowed[1] > now:
                pose = borrowed[0]
            image = self.art.pose(index, pose)
            if image is not None:
                surface.blit(image, image.get_rect(midbottom=(x, y + bob - lift)))
        instrument = self.art.instruments[index]
        if instrument is not None:
            ix, iy = instrument_anchor(index)
            shake = int(math.sin(math.pi * since / STRIKE_SECONDS) * 9) if 0 <= since < STRIKE_SECONDS else 0
            surface.blit(instrument, instrument.get_rect(midbottom=(ix, iy - shake)))

    def _draw_burst(self, surface: pygame.Surface, burst: FxBurst, now: float) -> None:
        elapsed = now - burst.start
        if elapsed < 0:
            return
        frames = self.art.fx_frames(burst.name)
        if not frames:
            return
        progress = min(1.0, elapsed / burst.duration)
        frame = frames[min(len(frames) - 1, int(progress * len(frames)))]
        x, y = burst.center
        rect = frame.get_rect(center=(x, int(y - burst.rise * progress)))
        alpha = 255 if progress < 0.6 else int(255 * (1.0 - progress) / 0.4)
        frame.set_alpha(alpha)
        surface.blit(frame, rect)
        frame.set_alpha(255)

    def _draw_bubble(self, surface: pygame.Surface, bubble: Bubble) -> None:
        key = (bubble.mode, bubble.span_beats, tuple(bubble.tokens))
        image = self._bubbles.get(key)
        if image is None:
            image = self._compose_bubble(bubble)
            if len(self._bubbles) >= BUBBLE_KEEP:
                self._bubbles.pop(next(iter(self._bubbles)))
            self._bubbles[key] = image
        x, _ = musician_anchor(bubble.lead)
        half = image.get_width() // 2
        cx = max(BUBBLE_MIN_X + half, min(BUBBLE_MAX_X - half, x))
        rect = image.get_rect(midtop=(cx, BUBBLE_TOP))
        surface.blit(image, rect)
        tail = self.art.bubble_tail
        tail_x = max(rect.left + 34, min(rect.right - 34, x))
        surface.blit(tail, tail.get_rect(midtop=(tail_x, rect.bottom - 6)))

    def _compose_bubble(self, bubble: Bubble) -> pygame.Surface:
        lane = int(bubble.span_beats * BEAT_UNIT) + BUBBLE_TOKEN
        width = BUBBLE_PAD * 3 + BUBBLE_ICON + lane
        image = self.art.bubble(width).copy()
        icon = self.art.listen_icon if bubble.mode == "listen" else self.art.go_icon
        mid = BUBBLE_HEIGHT // 2
        if icon is not None:
            image.blit(icon, icon.get_rect(midleft=(BUBBLE_PAD, mid)))
        left = BUBBLE_PAD * 2 + BUBBLE_ICON
        for voice, at in bubble.tokens:
            token = self.art.bar_token if voice == XYLOPHONE_VOICE else self.art.tokens[voice]
            if token is None:
                continue
            offset = int(max(0.0, min(bubble.span_beats, at)) * BEAT_UNIT)
            image.blit(token, token.get_rect(midleft=(left + offset, mid)))
        return image


__all__ = ["BandMotion", "Bubble", "FxBurst", "OrchestraRenderer", "sway"]

"""Storybook night-sky presentation for Stelle Incantate.

The renderer owns the sky (backdrop, the figure's revealed picture, glowing
lines, numbered stars), Leo, the bottom "speech band" (name plate or fact
bubble) and FX. Kit controls (goal strip, progress dots, number cards, next
and fact buttons) and their focus ring are drawn afterwards by the shared
``ControlLayer``. Nothing here marks the next star: hint pulses and the
demonstration trail appear only when the app asks for them (after hesitation
or a mistake). Per-frame work is blits plus a handful of short lines; every
surface comes prepared from ``SkyArt`` and animation is expressed as offsets
and prepared sizes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math
import random
import time

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .sky_art import INK, LINE_GLOW, SkyArt
    from .sky_content import BAND_CENTER, LEO_MIDBOTTOM, STAR_POP_SIZE, STAR_SIZE, sky_point
    from .sky_model import SkyRound
else:
    from sky_art import INK, LINE_GLOW, SkyArt
    from sky_content import BAND_CENTER, LEO_MIDBOTTOM, STAR_POP_SIZE, STAR_SIZE, sky_point
    from sky_model import SkyRound

APPEAR_STEP = 0.07
APPEAR_SECONDS = 0.3
LINE_SECONDS = 0.32
POP_SECONDS = 0.32
PULSE_SECONDS = 1.3
WOBBLE_SECONDS = 0.7
TRAIL_SECONDS = 0.7
REVEAL_FADE_SECONDS = 0.9
REVEAL_BREATH_SECONDS = 4.0
PICTURE_ALPHA = 235
RUMBLE = {"razzo": 3.0}  # the rocket rumbles as it "lifts off" (shooting star + whoosh)
RUMBLE_SECONDS = 0.9
MAX_FX = 10
FX_SECONDS = {"sparkle": 0.45, "star_burst": 0.8, "firework": 1.1, "shooting_star": 0.9}
FX_DEFAULT_SECONDS = 0.6
FX_DRIFT = {"shooting_star": (120.0, -60.0)}


class SkyCast:
    """Leo with the shared feedback grammar plus a pointing hint pose.

    ``CastFeedback`` owns cheer (correct) and think (try again); this wrapper
    adds ``point`` for figure starts and graduated hints, drawn only while the
    feedback friend is idle so the grammar stays unambiguous.
    """

    def __init__(self, feedback: CastFeedback, point: pygame.Surface | None, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._point = point
        self._clock = clock
        self._point_until = 0.0

    @property
    def animating(self) -> bool:
        return self.feedback.animating or self.pointing

    @property
    def pointing(self) -> bool:
        return self._clock() < self._point_until and self._point is not None

    def point(self, seconds: float = 1.8) -> None:
        self._point_until = self._clock() + seconds

    def correct(self) -> None:
        self._point_until = 0.0
        self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = 0.0
        self.feedback.try_again()

    def reset(self) -> None:
        self._point_until = 0.0
        self.feedback.reset()

    def update(self) -> bool:
        was_pointing = self._point_until > 0.0
        changed = self.feedback.update()
        if was_pointing and not self.pointing:
            self._point_until = 0.0
            changed = True
        return changed

    def draw(self, target: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self.pointing and self.feedback.pose is CastPose.IDLE:
            target.blit(self._point, self._point.get_rect(midbottom=midbottom))  # type: ignore[union-attr]
            return
        self.feedback.draw(target, midbottom)


@dataclass(slots=True)
class SceneMotion:
    """Bounded, time-stamped animation state owned by the app."""

    figure_started: float = -10.0
    appear_order: tuple[int, ...] = ()
    line_started: float = -10.0
    line_from: dict[tuple[int, int], int] = field(default_factory=dict)  # edge -> star it grows from
    pops: dict[int, float] = field(default_factory=dict)
    pulses: dict[int, float] = field(default_factory=dict)
    wobble: tuple[int, float] | None = None
    trail: tuple[int, int, float] | None = None  # (from star, to star, start)
    reveal_started: float | None = None
    fx: list[tuple[str, tuple[int, int], float]] = field(default_factory=list)

    def start_figure(self, now: float, count: int, seed: str) -> None:
        self.figure_started = now
        order = list(range(count))
        # Stars twinkle in a scrambled order so their appearance never hints
        # at the counting order.
        random.Random(seed).shuffle(order)
        self.appear_order = tuple(order)
        self.line_from.clear()
        self.line_started = -10.0
        self.pops.clear()
        self.pulses.clear()
        self.wobble = None
        self.trail = None
        self.reveal_started = None
        self.fx.clear()

    def appear_seconds(self) -> float:
        return APPEAR_STEP * len(self.appear_order) + APPEAR_SECONDS

    def add_fx(self, name: str, position: tuple[int, int], now: float) -> None:
        self.fx.append((name, position, now))
        del self.fx[:-MAX_FX]

    def active(self, now: float) -> bool:
        if now - self.figure_started < self.appear_seconds() or now - self.line_started < LINE_SECONDS:
            return True
        if any(now - start < POP_SECONDS for start in self.pops.values()):
            return True
        if any(now - start < PULSE_SECONDS for start in self.pulses.values()):
            return True
        if self.wobble is not None and now - self.wobble[1] < WOBBLE_SECONDS:
            return True
        if self.trail is not None and now - self.trail[2] < TRAIL_SECONDS + PULSE_SECONDS:
            return True
        if self.reveal_started is not None and now - self.reveal_started < REVEAL_BREATH_SECONDS:
            return True  # the revealed picture breathes, then rests (no idle redraw)
        return any(now - start < _fx_seconds(name) for name, _, start in self.fx)

    def prune(self, now: float) -> None:
        self.fx = [entry for entry in self.fx if now - entry[2] < _fx_seconds(entry[0])]
        for store, limit in ((self.pops, POP_SECONDS), (self.pulses, PULSE_SECONDS)):
            for key in [key for key, start in store.items() if now - start >= limit]:
                del store[key]
        if self.wobble is not None and now - self.wobble[1] >= WOBBLE_SECONDS:
            self.wobble = None
        if self.trail is not None and now - self.trail[2] >= TRAIL_SECONDS + PULSE_SECONDS:
            self.trail = None


def _fx_seconds(name: str) -> float:
    return FX_SECONDS.get(name, FX_DEFAULT_SECONDS)


def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


@dataclass(slots=True)
class Band:
    """What the bottom speech band shows (resolved, already-cased text)."""

    name: str | None = None
    fact: str | None = None


class SkyRenderer:
    """Compose one frame of the night sky from prepared surfaces."""

    def __init__(
        self, art: SkyArt, cast: SkyCast | None = None, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.art = art
        self.cast = cast
        self._clock = clock

    def figure_offset(self, round_: SkyRound, motion: SceneMotion, now: float) -> tuple[int, int]:
        """Revealed figures breathe gently, then rest (the rocket rumbles first).

        Offsets stay small so a figure never reaches the goal strip or the
        speech band.
        """

        if motion.reveal_started is None:
            return (0, 0)
        age = now - motion.reveal_started
        shake = RUMBLE.get(round_.figure.figure_id, 0.0) if age < RUMBLE_SECONDS else 0.0
        settle = max(0.0, min(1.0, age, REVEAL_BREATH_SECONDS - age))
        bob = math.sin(age * 2.2) * 4.0 * settle
        return (int(round(math.sin(age * 70.0) * shake)), int(round(bob)))

    def draw(self, target: pygame.Surface, round_: SkyRound, motion: SceneMotion, band: Band) -> None:
        now = self._clock()
        target.blit(self.art.background, (0, 0))
        offset = self.figure_offset(round_, motion, now)
        self._draw_picture(target, round_, motion, now, offset)
        self._draw_lines(target, round_, motion, now, offset)
        self._draw_trail(target, round_, motion, now)
        self._draw_stars(target, round_, motion, now, offset)
        if self.cast is not None:
            self.cast.draw(target, LEO_MIDBOTTOM)
        self._draw_band(target, band)
        self._draw_fx(target, motion, now)

    def star_centre(self, round_: SkyRound, index: int, offset: tuple[int, int] = (0, 0)) -> tuple[int, int]:
        x, y = sky_point(round_.figure.stars[index])
        return (x + offset[0], y + offset[1])

    # -- layers ---------------------------------------------------------------

    def _draw_picture(
        self, target: pygame.Surface, round_: SkyRound, motion: SceneMotion, now: float, offset: tuple[int, int]
    ) -> None:
        if motion.reveal_started is None:
            return
        picture = self.art.picture(round_.figure.figure_id)
        if picture is None:
            return
        age = now - motion.reveal_started
        alpha = int(PICTURE_ALPHA * _ease_out(age / REVEAL_FADE_SECONDS))
        if picture.get_alpha() != alpha:
            picture.set_alpha(alpha)
        origin = sky_point((0, 0))
        target.blit(picture, (origin[0] + offset[0], origin[1] + offset[1]))

    def _draw_lines(
        self, target: pygame.Surface, round_: SkyRound, motion: SceneMotion, now: float, offset: tuple[int, int]
    ) -> None:
        growing = now - motion.line_started < LINE_SECONDS
        progress = _ease_out((now - motion.line_started) / LINE_SECONDS)
        for edge in round_.lit_edges():
            a = self.star_centre(round_, edge[0], offset)
            b = self.star_centre(round_, edge[1], offset)
            source = motion.line_from.get(edge) if growing else None
            if source is not None:
                start, end = (a, b) if source == edge[0] else (b, a)
                b = (int(start[0] + (end[0] - start[0]) * progress), int(start[1] + (end[1] - start[1]) * progress))
                a = start
            pygame.draw.line(target, INK, a, b, 11)
            pygame.draw.line(target, LINE_GLOW, a, b, 5)

    def _draw_trail(self, target: pygame.Surface, round_: SkyRound, motion: SceneMotion, now: float) -> None:
        """Demonstration after mistakes: dots travel from the last lit star."""

        if motion.trail is None:
            return
        start_index, end_index, started = motion.trail
        age = now - started
        a = self.star_centre(round_, start_index)
        b = self.star_centre(round_, end_index)
        distance = math.dist(a, b)
        dots = max(2, int(distance // 26))
        shown = int(dots * min(1.0, age / TRAIL_SECONDS))
        for step in range(1, shown):
            t = step / dots
            centre = (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t))
            pygame.draw.circle(target, INK, centre, 7)
            pygame.draw.circle(target, LINE_GLOW, centre, 5)

    def _draw_stars(
        self, target: pygame.Surface, round_: SkyRound, motion: SceneMotion, now: float, offset: tuple[int, int]
    ) -> None:
        appear_rank = {index: rank for rank, index in enumerate(motion.appear_order)}
        for index in range(round_.star_count):
            rank = appear_rank.get(index, 0)
            appear = (now - motion.figure_started - APPEAR_STEP * rank) / APPEAR_SECONDS
            if appear <= 0.0:
                continue
            lit = round_.is_lit(index)
            big = (
                appear < 1.0
                or now - motion.pops.get(index, -10.0) < POP_SECONDS
                or self._pulsing(motion, index, now)
            )
            x, y = self.star_centre(round_, index, offset)
            missed = False
            if motion.wobble is not None and motion.wobble[0] == index:
                elapsed = now - motion.wobble[1]
                if elapsed < WOBBLE_SECONDS:
                    missed = True
                    x += int(9 * (1 - elapsed / WOBBLE_SECONDS) * math.sin(elapsed * 38))
            if lit and motion.reveal_started is None:
                target.blit(self.art.glow, self.art.glow.get_rect(center=(x, y)))
            if missed:
                target.blit(self.art.miss_ring, self.art.miss_ring.get_rect(center=(x, y)))
            face = self.art.star_face(round_.label(index), lit=lit, size=STAR_POP_SIZE if big else STAR_SIZE)
            target.blit(face, face.get_rect(center=(x, y)))

    @staticmethod
    def _pulsing(motion: SceneMotion, index: int, now: float) -> bool:
        start = motion.pulses.get(index)
        if start is None and motion.trail is not None and motion.trail[1] == index:
            start = motion.trail[2] + TRAIL_SECONDS
        if start is None:
            return False
        age = now - start
        return 0.0 <= age < PULSE_SECONDS and int(age / 0.22) % 2 == 0

    def _draw_band(self, target: pygame.Surface, band: Band) -> None:
        if band.fact:
            bubble = self.art.fact_bubble(band.fact)
            target.blit(bubble, bubble.get_rect(center=BAND_CENTER))
        elif band.name:
            plate = self.art.name_plate(band.name)
            target.blit(plate, plate.get_rect(center=BAND_CENTER))

    def _draw_fx(self, target: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self.art.fx_frames(name)
            duration = _fx_seconds(name)
            age = now - start
            if not frames or age >= duration:
                continue
            frame = frames[min(len(frames) - 1, int(age / duration * len(frames)))]
            dx, dy = FX_DRIFT.get(name, (0.0, 0.0))
            k = age / duration
            target.blit(frame, frame.get_rect(center=(int(position[0] + dx * k), int(position[1] + dy * k))))


__all__ = ["Band", "SceneMotion", "SkyCast", "SkyRenderer"]

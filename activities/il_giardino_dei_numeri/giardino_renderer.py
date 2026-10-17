"""Storybook scene presentation for Il Giardino dei Numeri.

The renderer owns the meadow, Dani, the crate, garden objects, number badges,
FX and the cardinality close card. Kit controls (answer cards, replay voice,
progress dots) and their focus ring are drawn afterwards by the shared
``ControlLayer``. Per-frame work is blits only: every surface comes prepared
from ``GardenArt``; animation is expressed as offsets and prepared sizes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math
import time

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose
from greia_platform.pygame_blit import PreparedSurfaces

if __package__:
    from .giardino_art import WELL_ITEM_SIZE, GardenArt
    from .giardino_model import (
        DANI_MIDBOTTOM,
        ITEM_SIZE,
        POP_ITEM_SIZE,
        GardenItem,
        GardenRound,
        crate_origin,
        crate_rows,
        well_position,
    )
else:
    from giardino_art import WELL_ITEM_SIZE, GardenArt
    from giardino_model import (
        DANI_MIDBOTTOM,
        ITEM_SIZE,
        POP_ITEM_SIZE,
        GardenItem,
        GardenRound,
        crate_origin,
        crate_rows,
        well_position,
    )

HOP_SECONDS = 0.5
POP_SECONDS = 0.34
BADGE_SECONDS = 0.95
DROP_SECONDS = 0.32
DROP_STAGGER = 0.07
CLOSE_CARD_CENTER = (470, 300)
MAX_FX = 10
# Seconds each shared FX animation stays on screen (frames spread across it).
FX_SECONDS = {"sparkle": 0.42, "ripple": 0.45, "star_burst": 0.75, "confetti": 1.5}
FX_DEFAULT_SECONDS = 0.5
FX_DRIFT = {"confetti": 70.0}


class GardenCast:
    """Dani with the shared feedback grammar plus a pointing hint pose.

    ``CastFeedback`` owns cheer (correct) and think (try again); this wrapper
    adds ``point`` for graduated hints and round starts, drawn only while the
    feedback friend is idle so the grammar stays unambiguous.
    """

    def __init__(self, feedback: CastFeedback, point: pygame.Surface | None, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._point = point
        self._fast = PreparedSurfaces(max_entries=2)  # RLE copy of the pose (opaque targets only)
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
            target.blit(self._fast.for_target(self._point, target), self._point.get_rect(midbottom=midbottom))  # type: ignore[union-attr]
            return
        self.feedback.draw(target, midbottom)


@dataclass(slots=True)
class SceneMotion:
    """Bounded, time-stamped animation state owned by the app."""

    round_started: float = 0.0
    hops: dict[int, float] = field(default_factory=dict)  # item_id -> start
    pops: dict[int, float] = field(default_factory=dict)  # item_id -> start
    badges: dict[int, tuple[float, int]] = field(default_factory=dict)  # item_id -> (start, number)
    fx: list[tuple[str, tuple[int, int], float]] = field(default_factory=list)
    close_number: int | None = None
    close_started: float = 0.0
    wobble_started: float | None = None

    def clear(self, now: float) -> None:
        self.round_started = now
        self.hops.clear()
        self.pops.clear()
        self.badges.clear()
        self.fx.clear()
        self.close_number = None
        self.wobble_started = None

    def add_fx(self, name: str, position: tuple[int, int], now: float) -> None:
        self.fx.append((name, position, now))
        del self.fx[:-MAX_FX]

    def active(self, now: float) -> bool:
        if now - self.round_started < DROP_SECONDS + DROP_STAGGER * 10:
            return True
        if any(now - start < HOP_SECONDS for start in self.hops.values()):
            return True
        if any(now - start < POP_SECONDS for start in self.pops.values()):
            return True
        if any(now - start < BADGE_SECONDS for start, _ in self.badges.values()):
            return True
        if self.close_number is not None and now - self.close_started < 0.5:
            return True
        return any(now - start < _fx_seconds(name) for name, _, start in self.fx)

    def prune(self, now: float) -> None:
        self.fx = [entry for entry in self.fx if now - entry[2] < _fx_seconds(entry[0])]
        for item_id in [key for key, start in self.pops.items() if now - start >= POP_SECONDS]:
            del self.pops[item_id]
        for item_id in [key for key, (start, _) in self.badges.items() if now - start >= BADGE_SECONDS]:
            del self.badges[item_id]


def _fx_seconds(name: str) -> float:
    return FX_SECONDS.get(name, FX_DEFAULT_SECONDS)


def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


class GardenRenderer:
    """Compose one frame of the garden from prepared surfaces."""

    def __init__(self, art: GardenArt, cast: GardenCast | None = None, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.art = art
        self.cast = cast
        self._clock = clock

    def draw(self, target: pygame.Surface, round_: GardenRound, motion: SceneMotion) -> None:
        now = self._clock()
        target.blit(self.art.background, (0, 0))
        if self.cast is not None:
            self.cast.draw(target, DANI_MIDBOTTOM)
        self._draw_crate(target, round_, motion, now)
        flying: list[GardenItem] = []
        for item in round_.items:
            if not item.counted:
                self._draw_field_item(target, round_, item, motion, now)
            elif now - motion.hops.get(item.item_id, -10.0) < HOP_SECONDS:
                flying.append(item)
        for item in flying:
            self._draw_flying(target, round_, item, motion, now)
        self._draw_badges(target, round_, motion, now)
        if motion.close_number is not None:
            self._draw_close(target, motion, now)
        self._draw_fx(target, motion, now)

    # -- crate ----------------------------------------------------------------

    def _draw_crate(self, target: pygame.Surface, round_: GardenRound, motion: SceneMotion, now: float) -> None:
        wells = round_.spec.wells
        landed = {
            item.order - 1: item
            for item in round_.items
            if item.counted and now - motion.hops.get(item.item_id, -10.0) >= HOP_SECONDS
        }
        small = self.art.item(round_.kind, WELL_ITEM_SIZE)
        big = self.art.item(round_.kind, 82)
        for row in range(crate_rows(wells)):
            origin = crate_origin(row, wells)
            if self.art.crate_back is not None:
                target.blit(self.art.crate_back, origin)
            for column in range(5):
                index = row * 5 + column
                item = landed.get(index)
                if item is None or small is None:
                    continue
                popping = now - motion.pops.get(item.item_id, -10.0) < POP_SECONDS
                image = big if popping and big is not None else small
                target.blit(image, image.get_rect(midbottom=well_position(index, wells)))
            if self.art.crate_front is not None:
                target.blit(self.art.crate_front, origin)

    # -- field objects ----------------------------------------------------------

    def _draw_field_item(
        self, target: pygame.Surface, round_: GardenRound, item: GardenItem, motion: SceneMotion, now: float
    ) -> None:
        popping = now - motion.pops.get(item.item_id, -10.0) < POP_SECONDS
        image = self.art.item(round_.kind, POP_ITEM_SIZE if popping else ITEM_SIZE)
        if image is None:
            return
        appear = (now - motion.round_started - DROP_STAGGER * item.item_id) / DROP_SECONDS
        if appear <= 0.0:
            return
        dy = -46.0 * (1.0 - _ease_out(appear))
        target.blit(image, image.get_rect(center=(int(item.x), int(item.y + dy))))

    def _draw_flying(
        self, target: pygame.Surface, round_: GardenRound, item: GardenItem, motion: SceneMotion, now: float
    ) -> None:
        t = (now - motion.hops[item.item_id]) / HOP_SECONDS
        t = max(0.0, min(1.0, t))
        end_x, end_y = well_position(item.order - 1, round_.spec.wells)
        end_y -= WELL_ITEM_SIZE / 2
        x = item.x + (end_x - item.x) * t
        y = item.y + (end_y - item.y) * t - 120.0 * math.sin(math.pi * t)
        size = ITEM_SIZE if t < 0.25 else 96 if t < 0.5 else 82 if t < 0.75 else WELL_ITEM_SIZE
        image = self.art.item(round_.kind, size)
        if image is not None:
            target.blit(image, image.get_rect(center=(int(x), int(y))))

    def _draw_badges(self, target: pygame.Surface, round_: GardenRound, motion: SceneMotion, now: float) -> None:
        for item_id, (start, number) in motion.badges.items():
            age = now - start
            if age >= BADGE_SECONDS or not 0 <= item_id < len(round_.items):
                continue
            item = round_.items[item_id]
            if item.counted:
                x, y = well_position(item.order - 1, round_.spec.wells)
                y -= WELL_ITEM_SIZE + 18
            else:
                x, y = int(item.x), int(item.y - ITEM_SIZE // 2 - 14)
            rise = int(10 * _ease_out(age / 0.3))
            badge = self.art.badge(number)
            target.blit(badge, badge.get_rect(center=(x, y - rise)))

    def _draw_fx(self, target: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self.art.fx_frames(name)
            duration = _fx_seconds(name)
            age = now - start
            if not frames or age >= duration:
                continue
            frame = frames[min(len(frames) - 1, int(age / duration * len(frames)))]
            drift = int(FX_DRIFT.get(name, 0.0) * age / duration)
            target.blit(frame, frame.get_rect(center=(position[0], position[1] + drift)))

    def _draw_close(self, target: pygame.Surface, motion: SceneMotion, now: float) -> None:
        card = self.art.close_card(motion.close_number or 1)
        age = now - motion.close_started
        rise = int(36 * (1.0 - _ease_out(age / 0.35)))
        target.blit(card, card.get_rect(center=(CLOSE_CARD_CENTER[0], CLOSE_CARD_CENTER[1] + rise)))


__all__ = ["GardenCast", "GardenRenderer", "SceneMotion"]

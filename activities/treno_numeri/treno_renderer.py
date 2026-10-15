"""Storybook scene presentation for Treno Numeri.

The renderer owns the station (backdrop, order board, Dani), the train
(wheels, wagons, cargo, locomotive, smoke), cargo on the platform, cargo
hopping between platform and wagon, number badges, the try-again
demonstration marks and FX. Kit controls (GO, progress dots) and their focus
ring are drawn afterwards by the shared ``ControlLayer``. Per-frame work is
blits plus a few short demonstration lines: every surface comes prepared from
``TrainArt``; animation is expressed as offsets, prepared sizes and
pre-rotated wheel frames.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math
import time

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .treno_art import WAGON_POP_SIZE, TrainArt
    from .treno_content import (
        CHIMNEY_TOP,
        DANI_MIDBOTTOM,
        ITEM_SIZE,
        LOCO_TOP,
        LOCO_WHEELS,
        LOCO_X,
        POP_ITEM_SIZE,
        RAIL_Y,
        SIGN_FACE,
        SIGN_POS,
        WAGON_ITEM_SIZE,
        WAGON_TOP,
        WAGON_WELLS,
        WAGON_WHEEL_SIZE,
        WAGON_WHEELS_X,
        WAGON_X,
        slot_position,
    )
    from .treno_model import Cargo, Station, TaskKind
else:
    from treno_art import WAGON_POP_SIZE, TrainArt
    from treno_content import (
        CHIMNEY_TOP,
        DANI_MIDBOTTOM,
        ITEM_SIZE,
        LOCO_TOP,
        LOCO_WHEELS,
        LOCO_X,
        POP_ITEM_SIZE,
        RAIL_Y,
        SIGN_FACE,
        SIGN_POS,
        WAGON_ITEM_SIZE,
        WAGON_TOP,
        WAGON_WELLS,
        WAGON_WHEEL_SIZE,
        WAGON_WHEELS_X,
        WAGON_X,
        slot_position,
    )
    from treno_model import Cargo, Station, TaskKind

HOP_SECONDS = 0.45
POP_SECONDS = 0.3
BADGE_SECONDS = 0.95
DROP_SECONDS = 0.32
DROP_STAGGER = 0.06
SIGN_HOP_SECONDS = 0.3
WOBBLE_SECONDS = 0.45
DEMO_MARK_SECONDS = 2.6
MAX_FX = 10
MAX_PUFFS = 8
PUFF_SECONDS = 1.1
FX_SECONDS = {"sparkle": 0.42, "star_burst": 0.75, "confetti": 1.5, "check_pop": 0.6}
FX_DEFAULT_SECONDS = 0.5
FX_DRIFT = {"confetti": 70.0}
INK = (75, 55, 47)
SUNSHINE = (255, 194, 52)


class TrainCast:
    """Dani with the shared feedback grammar plus a pointing hint pose.

    ``CastFeedback`` owns cheer (correct) and think (try again); this wrapper
    adds ``point`` for graduated hints and station starts, drawn only while the
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
class Hop:
    """One cargo item travelling between the platform and a wagon slot."""

    start: float
    origin: tuple[float, float]
    slot: int
    into_wagon: bool


@dataclass(slots=True)
class SceneMotion:
    """Bounded, time-stamped animation state owned by the app."""

    station_started: float = 0.0
    train_offset: float = 0.0
    wheel_frame: int = 0
    hops: dict[int, Hop] = field(default_factory=dict)  # item_id -> hop
    pops: dict[int, float] = field(default_factory=dict)  # item_id -> start
    badges: dict[int, tuple[float, int]] = field(default_factory=dict)  # slot -> (start, number)
    fx: list[tuple[str, tuple[int, int], float]] = field(default_factory=list)
    puffs: list[tuple[float, float, float]] = field(default_factory=list)  # (start, x, y)
    sign_hop: float = -10.0
    wobble: tuple[int, float] | None = None  # (wagon, start)
    extra_slots: tuple[int, ...] = ()
    missing_slots: tuple[int, ...] = ()
    pairs: int = 0  # SAME demonstration: number of one-to-one links
    marks_started: float = -10.0

    def clear(self, now: float) -> None:
        self.station_started = now
        self.hops.clear()
        self.pops.clear()
        self.badges.clear()
        self.fx.clear()
        self.wobble = None
        self.clear_marks()

    def clear_marks(self) -> None:
        self.extra_slots = ()
        self.missing_slots = ()
        self.pairs = 0
        self.marks_started = -10.0

    def add_fx(self, name: str, position: tuple[int, int], now: float) -> None:
        self.fx.append((name, position, now))
        del self.fx[:-MAX_FX]

    def add_puff(self, now: float, x: float, y: float) -> None:
        self.puffs.append((now, x, y))
        del self.puffs[:-MAX_PUFFS]

    def marks_visible(self, now: float) -> bool:
        return now - self.marks_started < DEMO_MARK_SECONDS

    def active(self, now: float) -> bool:
        if now - self.station_started < DROP_SECONDS + DROP_STAGGER * 10:
            return True
        if any(now - hop.start < HOP_SECONDS for hop in self.hops.values()):
            return True
        if any(now - start < POP_SECONDS for start in self.pops.values()):
            return True
        if any(now - start < BADGE_SECONDS for start, _ in self.badges.values()):
            return True
        if now - self.sign_hop < SIGN_HOP_SECONDS or self.marks_visible(now):
            return True
        if self.wobble is not None and now - self.wobble[1] < WOBBLE_SECONDS:
            return True
        if any(now - start < PUFF_SECONDS for start, _, _ in self.puffs):
            return True
        return any(now - start < _fx_seconds(name) for name, _, start in self.fx)

    def prune(self, now: float) -> None:
        self.fx = [entry for entry in self.fx if now - entry[2] < _fx_seconds(entry[0])]
        self.puffs = [entry for entry in self.puffs if now - entry[0] < PUFF_SECONDS]
        for key in [key for key, hop in self.hops.items() if now - hop.start >= HOP_SECONDS]:
            del self.hops[key]
        for key in [key for key, start in self.pops.items() if now - start >= POP_SECONDS]:
            del self.pops[key]
        for key in [key for key, (start, _) in self.badges.items() if now - start >= BADGE_SECONDS]:
            del self.badges[key]
        if self.wobble is not None and now - self.wobble[1] >= WOBBLE_SECONDS:
            self.wobble = None
        if (self.extra_slots or self.missing_slots or self.pairs) and not self.marks_visible(now):
            self.clear_marks()


def _fx_seconds(name: str) -> float:
    return FX_SECONDS.get(name, FX_DEFAULT_SECONDS)


def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


class TrainRenderer:
    """Compose one frame of the station from prepared surfaces."""

    def __init__(self, art: TrainArt, cast: TrainCast | None = None, *, clock: Callable[[], float] = time.monotonic) -> None:
        self.art = art
        self.cast = cast
        self._clock = clock

    def draw(self, target: pygame.Surface, station: Station, motion: SceneMotion) -> None:
        now = self._clock()
        target.blit(self.art.background, (0, 0))
        self._draw_train(target, station, motion, now)
        # The board and Dani stand on the platform, in front of the track.
        self._draw_sign(target, station, motion, now)
        if self.cast is not None:
            self.cast.draw(target, DANI_MIDBOTTOM)
        self._draw_pairs(target, station, motion, now)
        for item in station.items:
            if item.on_platform and item.item_id not in motion.hops:
                self._draw_platform_item(target, station, item, motion, now)
        for item_id, hop in motion.hops.items():
            self._draw_hop(target, station, hop, motion, now)
        self._draw_badges(target, motion, now)
        self._draw_puffs(target, motion, now)
        self._draw_fx(target, motion, now)

    # -- order board -------------------------------------------------------------

    def _draw_sign(self, target: pygame.Surface, station: Station, motion: SceneMotion, now: float) -> None:
        age = now - motion.sign_hop
        lift = int(10 * math.sin(math.pi * age / SIGN_HOP_SECONDS)) if 0 <= age < SIGN_HOP_SECONDS else 0
        x, y = SIGN_POS[0], SIGN_POS[1] - lift
        if self.art.sign is not None:
            target.blit(self.art.sign, (x, y))
        if station.task is TaskKind.COUNT_OUT:
            face = self.art.order_face(station.order, dots=station.spec.sign_dots)
        else:
            face = self.art.same_face()
        fx, fy, fw, fh = SIGN_FACE
        target.blit(face, face.get_rect(center=(x + fx + fw // 2, y + fy + fh // 2)))

    # -- train -----------------------------------------------------------------------

    def _draw_train(self, target: pygame.Surface, station: Station, motion: SceneMotion, now: float) -> None:
        offset = motion.train_offset
        frame = motion.wheel_frame
        hopping_in = {hop.slot for hop in motion.hops.values() if hop.into_wagon}
        marks = motion.marks_visible(now)
        for wagon in range(2):
            shake = 0
            if motion.wobble is not None and motion.wobble[0] == wagon:
                elapsed = now - motion.wobble[1]
                if elapsed < WOBBLE_SECONDS:
                    shake = int(7 * (1 - elapsed / WOBBLE_SECONDS) * (1 if int(elapsed * 36) % 2 else -1))
            left = int(WAGON_X[wagon] + offset) + shake
            wheel = self.art.wheel(WAGON_WHEEL_SIZE, frame)
            if wheel is not None:
                for wx in WAGON_WHEELS_X:
                    target.blit(wheel, wheel.get_rect(center=(left + wx, RAIL_Y - WAGON_WHEEL_SIZE // 2)))
            back = self.art.wagon_back[wagon]
            if back is not None:
                target.blit(back, (left, WAGON_TOP))
            for bay in range(WAGON_WELLS):
                slot = wagon * WAGON_WELLS + bay
                item = station.item_in_slot(slot)
                if item is None or slot in hopping_in:
                    continue
                popping = now - motion.pops.get(item.item_id, -10.0) < POP_SECONDS
                image = self.art.item(station.kind, WAGON_POP_SIZE if popping else WAGON_ITEM_SIZE)
                if image is not None:
                    target.blit(image, image.get_rect(midbottom=slot_position(slot, offset + shake)))
            front = self.art.wagon_front[wagon]
            if front is not None:
                target.blit(front, (left, WAGON_TOP))
            if marks:
                for slot in motion.missing_slots:
                    if slot // WAGON_WELLS == wagon:
                        x, y = slot_position(slot, offset + shake)
                        ghost = self.art.missing_ghost
                        target.blit(ghost, ghost.get_rect(center=(x, y - WAGON_ITEM_SIZE // 2)))
                for slot in motion.extra_slots:
                    if slot // WAGON_WELLS == wagon:
                        x, y = slot_position(slot, offset + shake)
                        ring = self.art.extra_ring
                        target.blit(ring, ring.get_rect(center=(x, y - WAGON_ITEM_SIZE // 2)))
        loco_left = int(LOCO_X + offset)
        for wx, size in LOCO_WHEELS:
            wheel = self.art.wheel(size, frame)
            if wheel is not None:
                target.blit(wheel, wheel.get_rect(center=(loco_left + wx, RAIL_Y - size // 2)))
        if self.art.locomotive is not None:
            target.blit(self.art.locomotive, (loco_left, LOCO_TOP))

    def _draw_pairs(self, target: pygame.Surface, station: Station, motion: SceneMotion, now: float) -> None:
        """SAME demonstration: one-to-one links from the order wagon to the child's."""

        if not motion.pairs or not motion.marks_visible(now):
            return
        for index in range(motion.pairs):
            ax, ay = slot_position(index, motion.train_offset)
            bx, by = slot_position(WAGON_WELLS + index, motion.train_offset)
            top = ay - WAGON_ITEM_SIZE - 6
            peak = top - 44 - 6 * index
            points = []
            for step in range(13):
                t = step / 12
                x = ax + (bx - ax) * t
                y = (1 - t) ** 2 * top + 2 * (1 - t) * t * peak + t**2 * top
                points.append((int(x), int(y)))
            pygame.draw.lines(target, INK, False, points, 7)
            pygame.draw.lines(target, SUNSHINE, False, points, 3)

    # -- cargo ----------------------------------------------------------------------

    def _draw_platform_item(
        self, target: pygame.Surface, station: Station, item: Cargo, motion: SceneMotion, now: float
    ) -> None:
        popping = now - motion.pops.get(item.item_id, -10.0) < POP_SECONDS
        image = self.art.item(station.kind, POP_ITEM_SIZE if popping else ITEM_SIZE)
        if image is None:
            return
        appear = (now - motion.station_started - DROP_STAGGER * item.item_id) / DROP_SECONDS
        if appear <= 0.0:
            return
        dy = -40.0 * (1.0 - _ease_out(appear))
        target.blit(image, image.get_rect(center=(int(item.x), int(item.y + dy))))

    def _draw_hop(self, target: pygame.Surface, station: Station, hop: Hop, motion: SceneMotion, now: float) -> None:
        t = max(0.0, min(1.0, (now - hop.start) / HOP_SECONDS))
        wx, wy = slot_position(hop.slot, motion.train_offset)
        wagon_centre = (float(wx), float(wy - WAGON_ITEM_SIZE / 2))
        start, end = (hop.origin, wagon_centre) if hop.into_wagon else (wagon_centre, hop.origin)
        x = start[0] + (end[0] - start[0]) * t
        y = start[1] + (end[1] - start[1]) * t - 110.0 * math.sin(math.pi * t)
        k = t if hop.into_wagon else 1.0 - t  # 0 = platform size, 1 = wagon size
        size = ITEM_SIZE if k < 0.25 else 82 if k < 0.5 else WAGON_POP_SIZE if k < 0.75 else WAGON_ITEM_SIZE
        image = self.art.item(station.kind, size)
        if image is not None:
            target.blit(image, image.get_rect(center=(int(x), int(y))))

    def _draw_badges(self, target: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for slot, (start, number) in motion.badges.items():
            age = now - start
            if age >= BADGE_SECONDS:
                continue
            x, y = slot_position(slot, motion.train_offset)
            y -= WAGON_ITEM_SIZE + 16
            rise = int(10 * _ease_out(age / 0.3))
            badge = self.art.badge(number)
            target.blit(badge, badge.get_rect(center=(x, y - rise)))

    # -- smoke and FX -------------------------------------------------------------

    def _draw_puffs(self, target: pygame.Surface, motion: SceneMotion, now: float) -> None:
        frames = self.art.fx_frames("dust_puff")
        if not frames:
            return
        for start, x, y in motion.puffs:
            age = now - start
            if age >= PUFF_SECONDS:
                continue
            frame = frames[min(len(frames) - 1, int(age / PUFF_SECONDS * len(frames)))]
            target.blit(frame, frame.get_rect(center=(int(x - 30 * age), int(y - 70 * age))))

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


def chimney_position(offset: float) -> tuple[float, float]:
    return (LOCO_X + CHIMNEY_TOP[0] + offset, LOCO_TOP + CHIMNEY_TOP[1])


__all__ = ["Hop", "SceneMotion", "TrainCast", "TrainRenderer", "chimney_position"]

"""Frame composition for Woodland Hide & Seek (blits only).

``SceneMotion`` holds the short-lived presentation state of a round: how
visible each peeking friend is (steady peeks, the duck-and-peek rhythm of
higher rungs, the "everybody hide again" shuffle), rustles, hint glows, "not
me" reveals, FX and the found friend hopping over to Lilli. ``LilliCast``
wraps the shared ``CastFeedback`` (cheer / think) with Lilli's point pose.
``WoodlandRenderer`` draws one frame from the model plus that motion state;
every surface comes prepared from ``WoodlandArt``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .woodland_art import WoodlandArt
    from .woodland_content import Level, Season
    from .woodland_layout import FRIEND_SLOT_SIZE, FRIEND_SLOTS, LILLI_HEIGHT, LILLI_MIDBOTTOM, SpotGeometry
else:
    from woodland_art import WoodlandArt
    from woodland_content import Level, Season
    from woodland_layout import FRIEND_SLOT_SIZE, FRIEND_SLOTS, LILLI_HEIGHT, LILLI_MIDBOTTOM, SpotGeometry

DUCK_SECONDS = 0.3
HIDDEN_SECONDS = 0.18
RISE_SECONDS = 0.38
HIDE_TOTAL = DUCK_SECONDS + HIDDEN_SECONDS + RISE_SECONDS
SHUFFLE_AT = DUCK_SECONDS + HIDDEN_SECONDS * 0.5
PEEK_RAMP = 0.25
SHAKE_SECONDS = 0.6
WOBBLE_SECONDS = 0.7
FX_SECONDS = 0.6
HOP_SECONDS = 0.34
FLIGHT_SECONDS = 0.72
REVEAL_RISE = 1.25
HINT_RISE = 0.8
MAX_FX = 16


@dataclass(slots=True)
class SpotMotion:
    shake_start: float = -10.0
    reveal_until: float = -10.0
    reveal_start: float = -10.0
    reveal_rise: float = 0.0
    wobble_start: float = -10.0
    glow_until: float = -10.0


@dataclass(slots=True)
class Hop:
    """A found friend: pops out of its place, then hops over to Lilli."""

    friend_id: str
    start: float
    origin: tuple[int, int]
    origin_size: int
    target: tuple[int, int]

    @property
    def end(self) -> float:
        return self.start + HOP_SECONDS + FLIGHT_SECONDS


@dataclass(slots=True)
class SceneMotion:
    """Presentation-only timers for the current round (bounded, cleared per round)."""

    spots: list[SpotMotion] = field(default_factory=list)
    hide_start: float = -10.0
    hops: list[Hop] = field(default_factory=list)
    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    phase_seed: float = 0.0

    def reset(self, spot_count: int, seed: float = 0.0) -> None:
        self.spots = [SpotMotion() for _ in range(spot_count)]
        self.hide_start = -10.0
        self.hops.clear()
        self.fx.clear()
        self.phase_seed = seed

    # -- events --
    def hide_everyone(self, now: float) -> None:
        self.hide_start = now

    def shake(self, index: int, now: float) -> None:
        self.spots[index].shake_start = now

    def reveal(self, index: int, now: float, seconds: float, rise: float, *, wobble: bool = False) -> None:
        spot = self.spots[index]
        spot.reveal_start = now
        spot.reveal_until = now + seconds
        spot.reveal_rise = rise
        if wobble:
            spot.wobble_start = now

    def glow(self, index: int, now: float, seconds: float) -> None:
        self.spots[index].glow_until = now + seconds

    def add_fx(self, name: str, position: tuple[int, int], start: float) -> None:
        self.fx.append((name, position, start))

    def add_hop(self, hop: Hop) -> None:
        self.hops.append(hop)

    def prune(self, now: float) -> None:
        self.hops = [hop for hop in self.hops if now < hop.end]
        while self.fx and now - self.fx[0][2] >= FX_SECONDS:
            self.fx.popleft()

    # -- queries --
    def hiding_transition(self, now: float) -> bool:
        return self.hide_start <= now < self.hide_start + HIDE_TOTAL

    def visibility(self, index: int, now: float, level: Level) -> tuple[float, float]:
        """(visibility 0..1, rise) of the friend at place ``index``."""

        rise = level.rise
        value = 1.0
        if level.down > 0.0:
            period = level.up + level.down
            phase = (now + self.phase_seed + index * 0.61 * period) % period
            if phase < level.up:
                value = min(1.0, phase / PEEK_RAMP)
            else:
                value = max(0.0, 1.0 - (phase - level.up) / PEEK_RAMP)
        t = now - self.hide_start
        if 0.0 <= t < DUCK_SECONDS:
            value = min(value, 1.0 - t / DUCK_SECONDS)
        elif DUCK_SECONDS <= t < DUCK_SECONDS + HIDDEN_SECONDS:
            value = 0.0
        elif DUCK_SECONDS + HIDDEN_SECONDS <= t < HIDE_TOTAL:
            value = min(value, (t - DUCK_SECONDS - HIDDEN_SECONDS) / RISE_SECONDS)
        if index < len(self.spots):
            spot = self.spots[index]
            if spot.reveal_start <= now < spot.reveal_until:
                ramp = min(1.0, (now - spot.reveal_start) / PEEK_RAMP, (spot.reveal_until - now) / PEEK_RAMP)
                value = max(value, ramp)
                rise = max(rise, spot.reveal_rise)
        return value, rise

    def shake_offset(self, index: int, now: float) -> int:
        t = now - self.spots[index].shake_start
        if 0.0 <= t < SHAKE_SECONDS:
            return int(round(math.sin(t * 38.0) * 5.0 * (1.0 - t / SHAKE_SECONDS)))
        return 0

    def wobble_offset(self, index: int, now: float) -> int:
        t = now - self.spots[index].wobble_start
        if 0.0 <= t < WOBBLE_SECONDS:
            return int(round(math.sin(t * 26.0) * 7.0 * (1.0 - t / WOBBLE_SECONDS)))
        return 0

    def glowing(self, index: int, now: float) -> bool:
        return now < self.spots[index].glow_until

    def in_flight(self, friend_id: str) -> bool:
        return any(hop.friend_id == friend_id for hop in self.hops)

    def active(self, now: float, level: Level) -> bool:
        if level.down > 0.0 or self.hiding_transition(now) or self.hops:
            return True
        if any(now - start < FX_SECONDS for _, _, start in self.fx):
            return True
        for spot in self.spots:
            if (
                now - spot.shake_start < SHAKE_SECONDS
                or spot.reveal_start <= now < spot.reveal_until + 0.05
                or now - spot.wobble_start < WOBBLE_SECONDS
                or now < spot.glow_until
            ):
                return True
        return False


class LilliCast:
    """Lilli: shared cheer/think feedback plus a point pose (requests, hints)."""

    def __init__(self, feedback: CastFeedback, art: WoodlandArt, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._clock = clock
        self._point = art.cast_pose("pose_point", LILLI_HEIGHT)
        self._point_until = 0.0

    @property
    def pose(self) -> CastPose:
        return self.feedback.pose

    @property
    def pointing(self) -> bool:
        return self._clock() < self._point_until and self.feedback.pose is CastPose.IDLE

    @property
    def animating(self) -> bool:
        return self.feedback.animating or self.pointing

    def correct(self) -> None:
        self._point_until = 0.0
        self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = 0.0
        self.feedback.try_again()

    def point(self, seconds: float) -> None:
        self.feedback.reset()
        self._point_until = self._clock() + seconds

    def reset(self) -> None:
        self._point_until = 0.0
        self.feedback.reset()

    def update(self) -> bool:
        changed = self.feedback.update()
        if self._point_until and self._clock() >= self._point_until:
            self._point_until = 0.0
            changed = True
        return changed

    def draw(self, surface: pygame.Surface) -> None:
        if self.pointing and self._point is not None:
            bob = int(math.sin((self._point_until - self._clock()) * 7.0) * 3)
            surface.blit(self._point, self._point.get_rect(midbottom=(LILLI_MIDBOTTOM[0], LILLI_MIDBOTTOM[1] + bob)))
            return
        self.feedback.draw(surface, LILLI_MIDBOTTOM)


class WoodlandRenderer:
    """Compose a round frame from prepared art (no scaling, no text)."""

    def __init__(self, art: WoodlandArt, cast: LilliCast) -> None:
        self._art = art
        self._cast = cast

    def draw(
        self,
        surface: pygame.Surface,
        season: Season,
        level: Level,
        geometry: Sequence[SpotGeometry],
        hiding: Sequence[str | None],
        found: Sequence[str],
        motion: SceneMotion,
        now: float,
    ) -> None:
        surface.blit(self._art.backdrop(season), (0, 0))
        width = surface.get_width()
        for index, geom in enumerate(geometry):
            if motion.glowing(index, now):
                self._draw_glow(surface, geom)
            friend = hiding[index] if index < len(hiding) else None
            if friend is not None:
                self._draw_peek(surface, geom, friend, motion, index, now, level, width)
            self._draw_place(surface, geom, motion.shake_offset(index, now))
        self._draw_fx(surface, motion, now)
        self._draw_friends(surface, found, motion)
        self._cast.draw(surface)
        self._draw_hops(surface, motion, now)

    # -- pieces -------------------------------------------------------------

    def _draw_glow(self, surface: pygame.Surface, geom: SpotGeometry) -> None:
        width = int(geom.hit_rect.width * 1.08)
        height = max(40, int(width * 0.32))
        glow = self._art.glow((width, height))
        surface.blit(glow, glow.get_rect(center=(geom.center_x, geom.anchor.y - height // 6)))

    def _draw_peek(self, surface, geom, friend, motion, index, now, level, width) -> None:
        visibility, rise = motion.visibility(index, now, level)
        if visibility <= 0.01:
            return
        image = self._art.full(friend, geom.friend_size)
        if image is None:
            return
        rect = geom.peek_rect(self._art.peek_top(friend), rise, visibility)
        rect.x += motion.wobble_offset(index, now)
        previous = surface.get_clip()
        surface.set_clip(geom.clip_rect(width).clip(previous))
        surface.blit(image, rect)
        surface.set_clip(previous)

    def _draw_place(self, surface: pygame.Surface, geom: SpotGeometry, shake: int) -> None:
        kind = geom.anchor.kind
        if geom.prop_rect is None:
            ripple = self._art.ripple(int(kind.width * geom.anchor.depth * 0.8))
            if ripple is not None:
                surface.blit(ripple, ripple.get_rect(center=(geom.center_x + shake, geom.cut_y)))
            return
        image = self._art.prop(kind, geom.prop_rect.size)
        if image is not None:
            surface.blit(image, geom.prop_rect.move(shake, 0))

    def _draw_fx(self, surface: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self._art.fx_frames(name)
            t = now - start
            if not frames or not 0.0 <= t < FX_SECONDS:
                continue
            frame = frames[min(len(frames) - 1, int(t / FX_SECONDS * len(frames)))]
            surface.blit(frame, frame.get_rect(center=position))

    def _draw_friends(self, surface: pygame.Surface, found: Sequence[str], motion: SceneMotion) -> None:
        # Back slots first so the front pair overlaps them.
        order = sorted(range(min(len(found), len(FRIEND_SLOTS))), key=lambda i: FRIEND_SLOTS[i][1])
        for index in order:
            friend = found[index]
            if motion.in_flight(friend):
                continue
            image = self._art.full(friend, FRIEND_SLOT_SIZE)
            if image is not None:
                surface.blit(image, image.get_rect(midbottom=FRIEND_SLOTS[index]))

    def _draw_hops(self, surface: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for hop in motion.hops:
            t = now - hop.start
            if t < 0:
                continue
            if t < HOP_SECONDS:
                image = self._art.full(hop.friend_id, hop.origin_size)
                lift = math.sin(math.pi * 0.5 * t / HOP_SECONDS) * hop.origin_size * 0.4
                position = (hop.origin[0], int(hop.origin[1] - lift + hop.origin_size * 0.12))
            else:
                k = min(1.0, (t - HOP_SECONDS) / FLIGHT_SECONDS)
                ease = 1 - (1 - k) ** 3
                start = (hop.origin[0], int(hop.origin[1] - hop.origin_size * 0.28))
                x = start[0] + (hop.target[0] - start[0]) * ease
                y = start[1] + (hop.target[1] - start[1]) * ease - math.sin(math.pi * k) * 90
                image = self._art.full(hop.friend_id, FRIEND_SLOT_SIZE)
                position = (int(x), int(y))
            if image is not None:
                surface.blit(image, image.get_rect(midbottom=position))


__all__ = [
    "FLIGHT_SECONDS",
    "HIDE_TOTAL",
    "HINT_RISE",
    "HOP_SECONDS",
    "Hop",
    "LilliCast",
    "REVEAL_RISE",
    "SHUFFLE_AT",
    "SceneMotion",
    "SpotMotion",
    "WoodlandRenderer",
]

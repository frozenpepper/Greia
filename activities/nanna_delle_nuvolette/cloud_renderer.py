"""Frame composition for Cloud Bedtime (blits only).

* ``SceneMotion`` holds short-lived presentation state: quilts flying to a
  cloud (and back when the cloud dreamed of another one), gentle FX, hint
  glows, quilt hops, a declining cloud's slow head-shake, the shooting star.
* ``MomoCast`` is the shared ``CastFeedback`` (cheer / think) idling in Momo's
  canonical ``sleepy`` pose, plus Momo's point pose for hints.
* ``CloudRenderer`` draws the night: sky (darker for every sleeping cloud),
  dream bubbles, clouds with their quilts, the quilt tray, Momo, FX.

Every surface comes prepared from ``CloudArt``; motion is a blit offset.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .cloud_art import CloudArt
    from .cloud_content import Quilt
    from .cloud_layout import (
        MOMO_HEIGHT,
        MOMO_MIDBOTTOM,
        MOON_CENTER,
        bubble_box,
        cloud_box,
    )
    from .cloud_model import CloudState, SleepyCloud
else:
    from cloud_art import CloudArt
    from cloud_content import Quilt
    from cloud_layout import (
        MOMO_HEIGHT,
        MOMO_MIDBOTTOM,
        MOON_CENTER,
        bubble_box,
        cloud_box,
    )
    from cloud_model import CloudState, SleepyCloud

FX_SECONDS = 0.9          # slow, soft sparkles (calm)
FLY_SECONDS = 0.42
TRY_HOLD_SECONDS = 0.7    # a declined quilt rests on the cloud for a moment
SHAKE_SECONDS = 0.9
HOP_SECONDS = 0.6
POKE_SECONDS = 0.6
SHOOTING_SECONDS = 1.8
FADE_SECONDS = 1.2        # the sky darkening one step
MAX_FX = 12
SHOOTING_FROM = (250, 70)
SHOOTING_TO = (720, 210)


def _ease(k: float) -> float:
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3


@dataclass(slots=True)
class Flight:
    """A quilt flying from the tray (or the finger) to a cloud, maybe back again."""

    quilt: Quilt
    image: pygame.Surface
    origin: tuple[int, int]
    target: tuple[int, int]
    start: float
    returning: bool
    cloud: int
    tray_index: int

    @property
    def end(self) -> float:
        return self.start + (2 * FLY_SECONDS + TRY_HOLD_SECONDS if self.returning else FLY_SECONDS)

    def holding(self, now: float) -> bool:
        """True while a declined quilt is being tried on the cloud."""

        t = now - self.start
        return self.returning and FLY_SECONDS <= t < FLY_SECONDS + TRY_HOLD_SECONDS

    def position(self, now: float) -> tuple[int, int] | None:
        t = now - self.start
        if t < 0 or now >= self.end or self.holding(now):
            return None
        if t < FLY_SECONDS:
            k = _ease(t / FLY_SECONDS)
            a, b, lift = self.origin, self.target, 50
        else:
            k = _ease((t - FLY_SECONDS - TRY_HOLD_SECONDS) / FLY_SECONDS)
            a, b, lift = self.target, self.origin, 34
        x = a[0] + (b[0] - a[0]) * k
        y = a[1] + (b[1] - a[1]) * k - math.sin(math.pi * k) * lift
        return (int(x), int(y))


@dataclass(slots=True)
class SceneMotion:
    """Presentation-only timers of the current night (bounded, cleared per night)."""

    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    flights: list[Flight] = field(default_factory=list)
    bubble_glow: tuple[int, float] | None = None
    tile_glow: tuple[int, float] | None = None
    tile_hops: dict[int, float] = field(default_factory=dict)
    shakes: dict[int, float] = field(default_factory=dict)
    pokes: dict[int, float] = field(default_factory=dict)
    shooting: float | None = None
    fade_from: int | None = None
    fade_start: float = 0.0

    def reset(self) -> None:
        self.fx.clear()
        self.flights.clear()
        self.bubble_glow = None
        self.tile_glow = None
        self.tile_hops.clear()
        self.shakes.clear()
        self.pokes.clear()
        self.shooting = None
        self.fade_from = None

    def add_fx(self, name: str, position: tuple[int, int], start: float) -> None:
        self.fx.append((name, position, start))

    def fly(self, flight: Flight) -> None:
        self.flights.append(flight)

    def glow_bubble(self, cloud: int, until: float) -> None:
        self.bubble_glow = (cloud, until)

    def glow_tile(self, index: int, until: float) -> None:
        self.tile_glow = (index, until)

    def hop_tile(self, index: int, now: float) -> None:
        self.tile_hops[index] = now

    def shake(self, cloud: int, now: float) -> None:
        self.shakes[cloud] = now

    def poke(self, cloud: int, now: float) -> None:
        self.pokes[cloud] = now

    def fade(self, previous_step: int, now: float) -> None:
        self.fade_from = previous_step
        self.fade_start = now

    def flying_tiles(self, now: float) -> set[int]:
        return {flight.tray_index for flight in self.flights if now < flight.end}

    def trying_on(self, cloud: int, now: float) -> Quilt | None:
        for flight in self.flights:
            if flight.cloud == cloud and flight.holding(now):
                return flight.quilt
        return None

    def prune(self, now: float) -> None:
        self.flights = [flight for flight in self.flights if now < flight.end]
        while self.fx and now - self.fx[0][2] >= FX_SECONDS:
            self.fx.popleft()
        self.tile_hops = {i: s for i, s in self.tile_hops.items() if now - s < HOP_SECONDS}
        self.shakes = {i: s for i, s in self.shakes.items() if now - s < SHAKE_SECONDS}
        self.pokes = {i: s for i, s in self.pokes.items() if now - s < POKE_SECONDS}
        if self.bubble_glow is not None and now >= self.bubble_glow[1]:
            self.bubble_glow = None
        if self.tile_glow is not None and now >= self.tile_glow[1]:
            self.tile_glow = None
        if self.shooting is not None and now - self.shooting >= SHOOTING_SECONDS:
            self.shooting = None
        if self.fade_from is not None and now - self.fade_start >= FADE_SECONDS:
            self.fade_from = None

    def active(self, now: float) -> bool:
        return bool(
            self.flights
            or self.fx
            or self.tile_hops
            or self.shakes
            or self.pokes
            or self.bubble_glow
            or self.tile_glow
            or self.shooting is not None
            or self.fade_from is not None
        )

    def tile_offset(self, index: int, now: float) -> int:
        start = self.tile_hops.get(index)
        if start is None or not 0.0 <= now - start < HOP_SECONDS:
            return 0
        k = (now - start) / HOP_SECONDS
        return -int(round(abs(math.sin(2 * math.pi * k)) * 14 * (1.0 - k)))

    def cloud_offset(self, cloud: int, now: float) -> tuple[int, int]:
        """Slow "no, thank you" head-shake or a little bounce when poked."""

        dx = dy = 0
        start = self.shakes.get(cloud)
        if start is not None and 0.0 <= now - start < SHAKE_SECONDS:
            t = (now - start) / SHAKE_SECONDS
            dx = int(round(math.sin(t * 2 * math.pi * 2) * 7 * (1.0 - t)))
        start = self.pokes.get(cloud)
        if start is not None and 0.0 <= now - start < POKE_SECONDS:
            t = (now - start) / POKE_SECONDS
            dy = -int(round(math.sin(math.pi * t) * 10))
        return dx, dy


class MomoCast:
    """Momo: shared cheer/think feedback idling in the canonical sleepy pose."""

    def __init__(self, feedback: CastFeedback, art: CloudArt, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._clock = clock
        # Momo stands at the right edge; the mirrored point pose points at the clouds.
        self._point = art.momo("pose_point", MOMO_HEIGHT, mirrored=True)
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
            bob = int(math.sin((self._point_until - self._clock()) * 6.0) * 3)
            surface.blit(self._point, self._point.get_rect(midbottom=(MOMO_MIDBOTTOM[0], MOMO_MIDBOTTOM[1] + bob)))
            return
        self.feedback.draw(surface, MOMO_MIDBOTTOM)


@dataclass(frozen=True, slots=True)
class TrayTile:
    """One tray place: its quilt (``None`` once given away) and its rect."""

    quilt: Quilt | None
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class SceneView:
    """Everything one frame needs from the app (read-only)."""

    clouds: Sequence[SleepyCloud]
    tiles: Sequence[TrayTile]
    dim_step: int
    held: int | None = None
    dragging: tuple[int, int] | None = None
    hovered_tile: int | None = None
    hovered_cloud: int | None = None
    moon_glow: float = 0.0
    show_dreams: bool = True
    intro: float = 1.0  # 0..1 while the clouds drift in


class CloudRenderer:
    """Compose a frame: night sky, dreams, clouds, tray, Momo, FX, flights."""

    def __init__(self, art: CloudArt, cast: MomoCast) -> None:
        self._art = art
        self._cast = cast

    @staticmethod
    def bob(cloud: SleepyCloud, now: float) -> int:
        """Gentle float; sleeping clouds breathe slower."""

        speed = 0.9 if cloud.asleep else 1.4
        return int(round(math.sin(now * speed + cloud.index * 2.1) * (2.5 if cloud.asleep else 3.5)))

    def draw(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        self._sky(surface, view, motion, now)
        if view.moon_glow > 0.0:
            glow = self._art.moon_glow(120)
            glow.set_alpha(int(255 * max(0.0, min(1.0, view.moon_glow))))
            surface.blit(glow, glow.get_rect(center=MOON_CENTER))
            glow.set_alpha(None)
        drift = int(round((1.0 - _ease(view.intro)) * 60))
        for cloud in view.clouds:
            self._cloud(surface, cloud, view, motion, now, drift)
        self._tray(surface, view, motion, now)
        self._cast.draw(surface)
        self._fx(surface, motion, now)
        for flight in motion.flights:
            position = flight.position(now)
            if position is not None:
                surface.blit(flight.image, flight.image.get_rect(center=position))
        if view.dragging is not None and view.held is not None and view.held < len(view.tiles):
            quilt = view.tiles[view.held].quilt
            if quilt is not None:
                image = self._art.tile_quilt(quilt)
                surface.blit(image, image.get_rect(center=view.dragging))
        self._shooting_star(surface, motion, now)

    # -- pieces -------------------------------------------------------------------

    def _sky(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        surface.blit(self._art.backdrop(view.dim_step), (0, 0))
        if motion.fade_from is not None and motion.fade_from != view.dim_step:
            # Cross-fade from the previous (lighter) night for a moment, then settle.
            k = max(0.0, min(1.0, (now - motion.fade_start) / FADE_SECONDS))
            previous = self._art.backdrop(motion.fade_from)
            previous.set_alpha(int(255 * (1.0 - k)))
            surface.blit(previous, (0, 0))
            previous.set_alpha(None)

    def _cloud(
        self,
        surface: pygame.Surface,
        cloud: SleepyCloud,
        view: SceneView,
        motion: SceneMotion,
        now: float,
        drift: int,
    ) -> None:
        dx, dy = motion.cloud_offset(cloud.index, now)
        direction = -1 if cloud.index == 0 else 1 if cloud.index == 2 else 0
        offset = (dx + direction * drift, dy + self.bob(cloud, now) - (drift if direction == 0 else 0))
        box = cloud_box(cloud.index).move(offset)
        if view.show_dreams and cloud.awake and view.intro >= 1.0:
            bubble = bubble_box(cloud.index).move(offset)
            if motion.bubble_glow is not None and motion.bubble_glow[0] == cloud.index:
                glow = self._art.glow((bubble.width + 36, bubble.height - 16))
                pulse = int(round(math.sin(now * 4.0) * 3))
                surface.blit(glow, glow.get_rect(center=(bubble.centerx, bubble.centery - 18 + pulse)))
            surface.blit(self._art.bubble(cloud.dream), bubble)
        if view.hovered_cloud == cloud.index and cloud.awake:
            glow = self._art.glow((box.width - 10, box.height - 70))
            surface.blit(glow, glow.get_rect(center=(box.centerx, box.centery + 18)))
        face = "asleep" if cloud.state is CloudState.ASLEEP else "yawn" if cloud.state is CloudState.YAWNING else "awake"
        surface.blit(self._art.cloud(cloud.dream.colour.cloud, face), box)
        quilt = cloud.quilt or motion.trying_on(cloud.index, now)
        if quilt is not None:
            surface.blit(self._art.tucked_quilt(quilt), box)

    def _tray(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        flying = motion.flying_tiles(now)
        for index, tile in enumerate(view.tiles):
            if tile.quilt is None or index in flying:
                continue
            dragged = view.dragging is not None and view.held == index
            image = self._art.tile_quilt(tile.quilt)
            lift = motion.tile_offset(index, now)
            if view.held == index:
                lift -= 10
            elif view.hovered_tile == index:
                lift -= 4
            rect = image.get_rect(center=(tile.rect.centerx, tile.rect.centery + lift))
            if (view.held == index and not dragged) or (motion.tile_glow is not None and motion.tile_glow[0] == index):
                glow = self._art.glow((rect.width + 40, rect.height + 44))
                surface.blit(glow, glow.get_rect(center=rect.center))
            if dragged:
                ghost = image.copy()
                ghost.set_alpha(90)
                surface.blit(ghost, rect)
            else:
                surface.blit(image, rect)

    def _fx(self, surface: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self._art.fx_frames(name)
            t = now - start
            if not frames or not 0.0 <= t < FX_SECONDS:
                continue
            frame = frames[min(len(frames) - 1, int(t / FX_SECONDS * len(frames)))]
            surface.blit(frame, frame.get_rect(center=position))

    def _shooting_star(self, surface: pygame.Surface, motion: SceneMotion, now: float) -> None:
        if motion.shooting is None:
            return
        frames = self._art.fx_frames("shooting_star")
        t = (now - motion.shooting) / SHOOTING_SECONDS
        if not frames or not 0.0 <= t < 1.0:
            return
        k = _ease(t)
        x = SHOOTING_FROM[0] + (SHOOTING_TO[0] - SHOOTING_FROM[0]) * k
        y = SHOOTING_FROM[1] + (SHOOTING_TO[1] - SHOOTING_FROM[1]) * k
        frame = frames[0]
        frame.set_alpha(int(255 * min(1.0, 4 * (1.0 - t))))
        surface.blit(frame, frame.get_rect(center=(int(x), int(y))))
        frame.set_alpha(None)


__all__ = [
    "CloudRenderer",
    "FADE_SECONDS",
    "FLY_SECONDS",
    "Flight",
    "MomoCast",
    "SceneMotion",
    "SceneView",
    "TRY_HOLD_SECONDS",
    "TrayTile",
]

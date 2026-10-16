"""Frame drawing for La Corsa delle Bacche (blits of prepared surfaces only).

``MomoCast`` is Momo himself walking the garden: ``CastFeedback`` owns the
shared grammar (``pose_cheer`` for a berry / a full basket, ``pose_think``
after a bump) and this wrapper adds the ``pose_point`` hint and a
``pose_wave`` hello when a garden starts. ``CorsaMotion`` holds the
short-lived presentation state (FX, pulses, the hint trail, the "wait"
bubble), all hard-bounded.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose
from greia_platform.pygame_blit import PreparedSurfaces

if __package__:
    from .corsa_art import MOMO_SHARE, CorsaArt, fruit_for
    from .corsa_layout import GardenGeometry
    from .corsa_model import Cell, Direction, Garden
else:
    from corsa_art import MOMO_SHARE, CorsaArt, fruit_for
    from corsa_layout import GardenGeometry
    from corsa_model import Cell, Direction, Garden

FX_SECONDS = 0.5
PULSE_SECONDS = 1.4
WALL_SECONDS = 0.26
BUBBLE_SECONDS = 1.6
TRAIL_SPEED = 5.0  # cells per second the hint trail grows
TRAIL_SECONDS = 2.6
MAX_FX = 12
MAX_PULSES = 8
FEET = 0.4  # sprites stand this far (in cells) below a cell centre
INTRO_HOP_STEP = 0.09


class MomoCast:
    """Momo in the garden: shared cheer/think grammar + point and wave poses."""

    def __init__(
        self,
        feedback: CastFeedback,
        point: pygame.Surface | None,
        wave: pygame.Surface | None,
        clock: Callable[[], float],
    ) -> None:
        self._fast = PreparedSurfaces(max_entries=96)  # RLE copies of per-frame sprites (pygame_blit)
        self.feedback = feedback
        self._point = point
        self._wave = wave
        self._clock = clock
        self._point_until = 0.0
        self._wave_until = 0.0

    @property
    def pointing(self) -> bool:
        return self._point is not None and self._clock() < self._point_until

    @property
    def waving(self) -> bool:
        return self._wave is not None and self._clock() < self._wave_until

    @property
    def animating(self) -> bool:
        return self.feedback.animating or self.pointing or self.waving

    def point(self, seconds: float = 1.8) -> None:
        self._wave_until = 0.0
        self._point_until = self._clock() + seconds

    def wave(self, seconds: float = 1.3) -> None:
        self._wave_until = self._clock() + seconds

    def correct(self) -> None:
        self._point_until = self._wave_until = 0.0
        self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = self._wave_until = 0.0
        self.feedback.try_again()

    def reset(self) -> None:
        self._point_until = self._wave_until = 0.0
        self.feedback.reset()

    def update(self) -> bool:
        return self.feedback.update() or self.pointing or self.waving

    def draw(self, target: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self.feedback.pose is CastPose.IDLE:
            extra = self._point if self.pointing else self._wave if self.waving else None
            if extra is not None:
                target.blit(self._fast(extra), extra.get_rect(midbottom=midbottom))
                return
        self.feedback.draw(target, midbottom)


@dataclass(slots=True)
class HintTrail:
    """Glowing dots along the way to a berry, growing from Momo."""

    route: tuple[Cell, ...]
    start: float

    def shown(self, now: float) -> int:
        return min(len(self.route), int((now - self.start) * TRAIL_SPEED) + 1)

    def done(self, now: float) -> bool:
        return now - self.start > len(self.route) / TRAIL_SPEED + TRAIL_SECONDS


@dataclass(slots=True)
class CorsaMotion:
    """Bounded transient presentation state for one garden."""

    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    pulses: dict[Cell, float] = field(default_factory=dict)
    critter_pulses: dict[int, float] = field(default_factory=dict)
    trail: HintTrail | None = None
    bubble: float = -10.0
    wall: tuple[float, Direction] | None = None
    intro: float = -10.0
    ambient: bool = True

    def clear(self) -> None:
        self.fx.clear()
        self.pulses.clear()
        self.critter_pulses.clear()
        self.trail = None
        self.bubble = -10.0
        self.wall = None
        self.intro = -10.0

    def add_fx(self, name: str, position: tuple[float, float], now: float) -> None:
        self.fx.append((name, (int(position[0]), int(position[1])), now))

    def pulse(self, cells, now: float) -> None:
        for cell in cells:
            self.pulses[cell] = now
        while len(self.pulses) > MAX_PULSES:
            self.pulses.pop(next(iter(self.pulses)))

    def pulse_critter(self, index: int, now: float) -> None:
        self.critter_pulses[index] = now
        while len(self.critter_pulses) > MAX_PULSES:
            self.critter_pulses.pop(next(iter(self.critter_pulses)))

    def prune(self, now: float) -> None:
        while self.fx and now - self.fx[0][2] > FX_SECONDS:
            self.fx.popleft()
        for cell in [cell for cell, start in self.pulses.items() if now - start > PULSE_SECONDS]:
            del self.pulses[cell]
        for index in [i for i, start in self.critter_pulses.items() if now - start > PULSE_SECONDS]:
            del self.critter_pulses[index]
        if self.trail is not None and self.trail.done(now):
            self.trail = None
        if self.wall is not None and now - self.wall[0] > WALL_SECONDS:
            self.wall = None

    def active(self, now: float) -> bool:
        return bool(
            self.fx
            or self.pulses
            or self.critter_pulses
            or self.trail is not None
            or self.wall is not None
            or now - self.bubble < BUBBLE_SECONDS
            or now - self.intro < 2.0
        )


def _hop(elapsed: float, duration: float, height: float) -> int:
    if elapsed < 0 or elapsed > duration:
        return 0
    return -int(round(abs(math.sin(math.pi * elapsed / (duration / 2))) * height))


class CorsaRenderer:
    """Draw one garden frame from the prepared scene and sprites."""

    def __init__(self, art: CorsaArt, cast: MomoCast) -> None:
        self._fast = PreparedSurfaces(max_entries=96)  # RLE copies of per-frame sprites (pygame_blit)
        self.art = art
        self.cast = cast

    def draw(
        self,
        surface: pygame.Surface,
        scene: pygame.Surface,
        garden: Garden,
        geometry: GardenGeometry,
        motion: CorsaMotion,
        now: float,
    ) -> None:
        surface.blit(scene, (0, 0))
        cell = geometry.cell
        sprites = self.art.sprites(cell)
        feet = int(cell * FEET)

        def anchor(row: float, col: float) -> tuple[int, int]:
            x, y = geometry.center(row, col)
            return int(x), int(y)

        # Hint trail: dots along the way (drawn on the path, under everything).
        trail = motion.trail
        if trail is not None:
            shown = trail.route[: trail.shown(now)]
            goal = trail.route[-1]
            for a, b in zip(shown, shown[1:]):
                middle = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
                surface.blit(self._fast(sprites.trail), sprites.trail.get_rect(center=anchor(*middle)))
                if b != goal:
                    surface.blit(self._fast(sprites.trail), sprites.trail.get_rect(center=anchor(*b)))

        # Berries: a gentle sway; a pulsed berry glows and hops.
        for index, berry in enumerate(garden.layout.berries):
            if berry not in garden.remaining:
                continue
            bx, by = anchor(*berry)
            if berry in motion.pulses:
                surface.blit(self._fast(sprites.halo), sprites.halo.get_rect(center=(bx, by)))
            image = sprites.berries.get(fruit_for(berry))
            if image is None:
                continue
            lift = _hop(now - motion.pulses.get(berry, -10.0), PULSE_SECONDS, cell * 0.18)
            lift = min(lift, _hop(now - motion.intro - index * INTRO_HOP_STEP, 0.5, cell * 0.16))
            sway = math.sin(now * 2.4 + index * 1.3) * cell * 0.03 if motion.ambient else 0.0
            surface.blit(self._fast(image), image.get_rect(center=(bx, int(by + sway) + lift)))

        # FX bursts behind the characters so Momo's cheer stays visible.
        for name, position, start in motion.fx:
            frames = self.art.fx_frames(name, cell)
            if not frames:
                continue
            frame = frames[min(len(frames) - 1, int((now - start) / FX_SECONDS * len(frames)))]
            surface.blit(self._fast(frame), frame.get_rect(center=position))

        # Critters and Momo, back to front.
        drawables: list[tuple[float, int]] = [(garden.momo.position()[0], -1)]
        drawables += [(critter.position()[0], index) for index, critter in enumerate(garden.critters)]
        drawables.sort()
        for _, index in drawables:
            if index < 0:
                self._draw_momo(surface, garden, geometry, motion, now, feet)
            else:
                self._draw_critter(surface, garden, index, geometry, motion, now, feet, sprites)

        # "Wait" bubble over Momo (a tapped path stopped before a critter).
        if now - motion.bubble < BUBBLE_SECONDS:
            mx, my = anchor(*garden.momo.position())
            bubble = sprites.bubble
            bob = int(math.sin(now * 5.0) * cell * 0.03)
            surface.blit(self._fast(bubble), bubble.get_rect(midbottom=(mx + int(cell * 0.42), my - int(cell * 0.62) + bob)))

    def sprite_regions(
        self,
        garden: Garden,
        geometry: GardenGeometry,
        motion: CorsaMotion,
        now: float,
    ) -> list[pygame.Rect] | None:
        """Logical rectangles ``draw`` may change between two frames.

        Covers Momo, every critter (with hop and halo) and every remaining
        berry (sway, pulse hop and halo).  Returns None when something else
        animates (hint trail, FX, wall shove, wait bubble, intro hops): the
        caller then renders a full frame.  Callers union these with the
        previous frame's rectangles so vacated pixels are repaired too.
        """

        if (
            motion.trail is not None
            or motion.fx
            or motion.wall is not None
            or now - motion.bubble < BUBBLE_SECONDS + 0.1
            or now - motion.intro < 2.5
        ):
            return None
        cell = geometry.cell

        def box(row: float, col: float, width: float, height: float, bottom: float) -> pygame.Rect:
            x, y = geometry.center(row, col)
            rect = pygame.Rect(0, 0, int(cell * width) + 4, int(cell * height) + 4)
            rect.midbottom = (int(x), int(y + cell * bottom) + 2)
            return rect

        # Momo (incl. point/wave poses and cheer hop), then critters, berries.
        regions = [box(*garden.momo.position(), 3.0, MOMO_SHARE + 0.9, FEET + 0.15)]
        for critter in garden.critters:
            regions.append(box(*critter.position(), 1.8, 2.1, FEET + 0.2))
        for berry in garden.remaining:
            regions.append(box(*berry, 1.5, 1.9, 0.75))
        return regions

    def _draw_momo(
        self,
        surface: pygame.Surface,
        garden: Garden,
        geometry: GardenGeometry,
        motion: CorsaMotion,
        now: float,
        feet: int,
    ) -> None:
        cell = geometry.cell
        row, col = garden.momo.position()
        x, y = geometry.center(row, col)
        lift = 0
        if garden.momo.moving and not garden.bouncing:
            lift = -int(abs(math.sin(now * 11.0)) * cell * 0.07)
        shove_x = shove_y = 0
        if motion.wall is not None:
            elapsed = now - motion.wall[0]
            push = math.sin(math.pi * min(1.0, elapsed / WALL_SECONDS)) * cell * 0.12
            shove_x = int(motion.wall[1][1] * push)
            shove_y = int(motion.wall[1][0] * push)
        self.cast.draw(surface, (int(x) + shove_x, int(y) + feet + lift + shove_y))

    def _draw_critter(
        self,
        surface: pygame.Surface,
        garden: Garden,
        index: int,
        geometry: GardenGeometry,
        motion: CorsaMotion,
        now: float,
        feet: int,
        sprites,
    ) -> None:
        critter = garden.critters[index]
        cell = geometry.cell
        row, col = critter.position()
        x, y = geometry.center(row, col)
        center = (int(x), int(y))
        if index in motion.critter_pulses:
            surface.blit(self._fast(sprites.halo), sprites.halo.get_rect(center=center))
        image = sprites.critters.get((critter.kind, critter.asleep))
        if image is None:
            return
        lift = 0
        if critter.walker.moving:
            lift = -int(abs(math.sin(now * 8.0 + index)) * cell * 0.05)
        lift = min(lift, _hop(now - motion.critter_pulses.get(index, -10.0), PULSE_SECONDS * 0.5, cell * 0.12))
        surface.blit(self._fast(image), image.get_rect(midbottom=(center[0], center[1] + feet + lift)))


__all__ = ["CorsaMotion", "CorsaRenderer", "FEET", "HintTrail", "MomoCast"]

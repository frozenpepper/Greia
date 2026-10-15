"""Frame drawing for Il Labirinto Magico (blits of prepared surfaces only).

``MazeCast`` is Tito himself walking the maze: ``CastFeedback`` owns the
shared grammar (``pose_cheer`` for a star / the tent, ``pose_think`` for a
dead end or a closed door) and this wrapper adds the ``pose_point`` hint and a
``pose_wave`` hello when a maze starts. ``MazeMotion`` holds the short-lived
presentation state (FX, pulses, the firefly guide), all hard-bounded.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .maze_art import MazeArt
    from .maze_layout import MazeGeometry
    from .maze_model import Cell, Maze, Walker, is_cell
else:
    from maze_art import MazeArt
    from maze_layout import MazeGeometry
    from maze_model import Cell, Maze, Walker, is_cell

FX_SECONDS = 0.5
PULSE_SECONDS = 1.4
BUMP_SECONDS = 0.28
DOOR_RATTLE_SECONDS = 0.5
FIREFLY_SPEED = 4.0  # squares per second
TRAIL_SECONDS = 2.2
MAX_FX = 12
MAX_PULSES = 8
TITO_SCALE = 1.4
FEET = 0.42  # Tito's feet sit this far (in cells) below a cell centre


class MazeCast:
    """Tito in the maze: shared cheer/think grammar + point and wave poses."""

    def __init__(
        self,
        feedback: CastFeedback,
        point: pygame.Surface | None,
        wave: pygame.Surface | None,
        clock: Callable[[], float],
    ) -> None:
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
                target.blit(extra, extra.get_rect(midbottom=midbottom))
                return
        self.feedback.draw(target, midbottom)


@dataclass(slots=True)
class FireflyFlight:
    route: tuple[Cell, ...]
    start: float

    def position(self, now: float) -> tuple[float, float] | None:
        steps = (now - self.start) * FIREFLY_SPEED
        last = len(self.route) - 1
        if steps < 0 or last < 0:
            return None
        if steps >= last + TRAIL_SECONDS * FIREFLY_SPEED * 0.4:
            return None
        index = min(last, int(steps))
        t = 0.0 if index >= last else steps - index
        a = self.route[index]
        b = self.route[min(last, index + 1)]
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    def reached(self, now: float) -> int:
        return min(len(self.route), int((now - self.start) * FIREFLY_SPEED) + 1)

    def done(self, now: float) -> bool:
        return now - self.start > len(self.route) / FIREFLY_SPEED + TRAIL_SECONDS


@dataclass(slots=True)
class MazeMotion:
    """Bounded transient presentation state for one maze."""

    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    pulses: dict[Cell, float] = field(default_factory=dict)
    firefly: FireflyFlight | None = None
    bump: tuple[float, Cell] | None = None
    door_rattle: float = -10.0
    tent_hop: float = -10.0
    ambient: bool = True

    def clear(self) -> None:
        self.fx.clear()
        self.pulses.clear()
        self.firefly = None
        self.bump = None
        self.door_rattle = -10.0
        self.tent_hop = -10.0

    def add_fx(self, name: str, position: tuple[float, float], now: float) -> None:
        self.fx.append((name, (int(position[0]), int(position[1])), now))

    def pulse(self, cells: Sequence[Cell], now: float) -> None:
        for cell in cells:
            self.pulses[cell] = now
        while len(self.pulses) > MAX_PULSES:
            self.pulses.pop(next(iter(self.pulses)))

    def prune(self, now: float) -> None:
        while self.fx and now - self.fx[0][2] > FX_SECONDS:
            self.fx.popleft()
        for cell in [cell for cell, start in self.pulses.items() if now - start > PULSE_SECONDS]:
            del self.pulses[cell]
        if self.firefly is not None and self.firefly.done(now):
            self.firefly = None
        if self.bump is not None and now - self.bump[0] > BUMP_SECONDS:
            self.bump = None

    def active(self, now: float) -> bool:
        return bool(
            self.fx
            or self.pulses
            or self.firefly is not None
            or self.bump is not None
            or now - self.door_rattle < DOOR_RATTLE_SECONDS
            or now - self.tent_hop < PULSE_SECONDS
        )


def _hop(elapsed: float, duration: float, height: float) -> int:
    if elapsed < 0 or elapsed > duration:
        return 0
    return -int(round(abs(math.sin(math.pi * elapsed / (duration / 2))) * height))


class MazeRenderer:
    """Draw one maze frame from the prepared scene and sprites."""

    def __init__(self, art: MazeArt, cast: MazeCast) -> None:
        self.art = art
        self.cast = cast

    def draw(
        self,
        surface: pygame.Surface,
        scene: pygame.Surface,
        maze: Maze,
        walker: Walker,
        geometry: MazeGeometry,
        motion: MazeMotion,
        now: float,
        *,
        show_arrows: bool,
    ) -> None:
        surface.blit(scene, (0, 0))
        cell = geometry.cell
        sprites = self.art.sprites(cell)
        layout = maze.layout

        def anchor(square: Cell) -> tuple[int, int]:
            x, y = geometry.center(*square)
            return int(x), int(y)

        def halo(square: Cell) -> None:
            surface.blit(sprites.halo, sprites.halo.get_rect(center=anchor(square)))

        # Tent (the goal): glows when open, wears a bubble of missing stars.
        gx, gy = anchor(layout.goal)
        missing = len(maze.missing_stars)
        tent_lift = _hop(now - motion.tent_hop, PULSE_SECONDS, cell * 0.12)
        if layout.goal in motion.pulses:
            tent_lift = min(tent_lift, _hop(now - motion.pulses[layout.goal], PULSE_SECONDS, cell * 0.12))
        if not missing or layout.goal in motion.pulses:
            halo(layout.goal)
        if sprites.tent is not None:
            rect = sprites.tent.get_rect(midbottom=(gx, gy + int(cell * FEET) + tent_lift))
            surface.blit(sprites.tent, rect)
            if missing:
                badge = self.art.badge(missing, cell)
                surface.blit(badge, badge.get_rect(midbottom=(gx, rect.top + cell // 6)))

        # Garden door (locked until Tito carries the key).
        if layout.door is not None and not maze.door_open and sprites.door is not None:
            dx, dy = anchor(layout.door)
            shake = 0
            elapsed = now - motion.door_rattle
            if elapsed < DOOR_RATTLE_SECONDS:
                shake = int(round(math.sin(elapsed * 40.0) * cell * 0.05))
            if layout.door in motion.pulses:
                halo(layout.door)
            surface.blit(sprites.door, sprites.door.get_rect(midbottom=(dx + shake, dy + int(cell * FEET))))

        bob = math.sin(now * 3.0) * cell * 0.05 if motion.ambient else 0.0
        if layout.key is not None and not maze.has_key and sprites.key is not None:
            if layout.key in motion.pulses:
                halo(layout.key)
            kx, ky = anchor(layout.key)
            lift = _hop(now - motion.pulses.get(layout.key, -10.0), PULSE_SECONDS, cell * 0.18)
            surface.blit(sprites.key, sprites.key.get_rect(center=(kx, int(ky + bob) + lift)))

        for index, star in enumerate(layout.stars):
            if star in maze.collected:
                continue
            if star in motion.pulses:
                halo(star)
            sx, sy = anchor(star)
            lift = _hop(now - motion.pulses.get(star, -10.0), PULSE_SECONDS, cell * 0.18)
            wobble = math.sin(now * 3.0 + index * 1.7) * cell * 0.05 if motion.ambient else 0.0
            surface.blit(sprites.star, sprites.star.get_rect(center=(sx, int(sy + wobble) + lift)))

        # Firefly guide: flies a few squares of the way and leaves glowing dots.
        flight = motion.firefly
        if flight is not None:
            for square in flight.route[1 : flight.reached(now)]:
                if is_cell(square) or square == flight.route[-1]:
                    surface.blit(sprites.trail, sprites.trail.get_rect(center=anchor(square)))
            spot = flight.position(now)
            if spot is not None and sprites.firefly is not None:
                fx, fy = geometry.center(*spot)
                flutter = math.sin(now * 14.0) * cell * 0.06
                center = (int(fx), int(fy - cell * 0.25 + flutter))
                surface.blit(sprites.glow, sprites.glow.get_rect(center=center))
                surface.blit(sprites.firefly, sprites.firefly.get_rect(center=center))

        # Pre-reader guide: which ways are open right now (never which is right).
        row, col = walker.position()
        tx, ty = geometry.center(row, col)
        if show_arrows:
            nudge = (math.sin(now * 4.0) + 1.0) * cell * 0.04
            for direction in maze.open_directions():
                arrow = sprites.arrows.get(direction)
                if arrow is None:
                    continue
                distance = cell * 0.62 + geometry.gap * 0.5 + nudge
                ax = tx + direction[1] * distance
                ay = ty + direction[0] * distance
                surface.blit(arrow, arrow.get_rect(center=(int(ax), int(ay))))

        # FX burst behind Tito so his cheer stays visible.
        for name, position, start in motion.fx:
            frames = self.art.fx_frames(name, cell)
            if not frames:
                continue
            index = min(len(frames) - 1, int((now - start) / FX_SECONDS * len(frames)))
            frame = frames[index]
            surface.blit(frame, frame.get_rect(center=position))

        # Tito (hops while walking; squashes into a hedge on a bump).
        lift = 0
        if walker.moving:
            lift = -int(abs(math.sin(now * 12.0)) * cell * 0.08)
        shove_x = shove_y = 0
        if motion.bump is not None:
            elapsed = now - motion.bump[0]
            push = math.sin(math.pi * min(1.0, elapsed / BUMP_SECONDS)) * cell * 0.14
            shove_x = int(motion.bump[1][1] * push)
            shove_y = int(motion.bump[1][0] * push)
        self.cast.draw(surface, (int(tx) + shove_x, int(ty + cell * FEET) + lift + shove_y))



__all__ = ["FireflyFlight", "MazeCast", "MazeMotion", "MazeRenderer", "TITO_SCALE", "FEET"]

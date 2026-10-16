"""Frame composition for Specchi Magici (blits only).

``SceneView`` is the read-only state one frame needs, ``SceneMotion`` the
small bounded set of running animations (tile drops, a declined tile's
wobble, hint glows, tray hops, sparkles, the celebration wave) and
``LilliCast`` wraps the shared ``CastFeedback`` with the hint ``pose_point``.
Nothing here decodes, scales or renders text per frame: every surface comes
prepared from ``MirrorArt``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .mirror_art import MirrorArt
    from .mirror_layout import (
        CELL,
        LILLI_HEIGHT,
        LILLI_MIDBOTTOM,
        MIRROR_X,
        MIRROR_Y,
        GRID_RECT,
        TILE_SIZE,
        TRAY_TILE,
        cell_rect,
    )
    from .mirror_model import HALF_COLS, HALF_ROWS, MirrorAxis, Piece
else:
    from mirror_art import MirrorArt
    from mirror_layout import (
        CELL,
        LILLI_HEIGHT,
        LILLI_MIDBOTTOM,
        MIRROR_X,
        MIRROR_Y,
        GRID_RECT,
        TILE_SIZE,
        TRAY_TILE,
        cell_rect,
    )
    from mirror_model import HALF_COLS, HALF_ROWS, MirrorAxis, Piece

DROP_SECONDS = 0.32
WOBBLE_SECONDS = 0.9
HOP_SECONDS = 0.55
POKE_SECONDS = 0.4
FX_FRAME_SECONDS = 0.12
CELEBRATE_SECONDS = 2.2
MAX_FX = 12
MAX_GLOWS = 8


class LilliCast:
    """Lilli: shared cheer/think feedback plus the hint ``pose_point``.

    She stands left of the mirror; the canonical point pose already points
    right, at the board.
    """

    def __init__(self, feedback: CastFeedback, art: MirrorArt, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._clock = clock
        self._point = art.lilli("pose_point", LILLI_HEIGHT)
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
            surface.blit(self._point, self._point.get_rect(midbottom=(LILLI_MIDBOTTOM[0] + bob, LILLI_MIDBOTTOM[1])))
            return
        self.feedback.draw(surface, LILLI_MIDBOTTOM)


@dataclass(slots=True)
class SceneMotion:
    """Running animations, each bounded and pruned by time."""

    drops: dict[tuple[int, int], float] = field(default_factory=dict)
    wobble: tuple[tuple[int, int], Piece, float] | None = None
    source_glow: dict[tuple[int, int], float] = field(default_factory=dict)
    target_ring: dict[tuple[int, int], float] = field(default_factory=dict)
    ghost: tuple[tuple[int, int], Piece, float] | None = None
    tray_hops: dict[int, float] = field(default_factory=dict)
    pokes: dict[tuple[int, int], float] = field(default_factory=dict)
    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    celebrate: float | None = None

    def reset(self) -> None:
        self.drops.clear()
        self.wobble = None
        self.source_glow.clear()
        self.target_ring.clear()
        self.ghost = None
        self.tray_hops.clear()
        self.pokes.clear()
        self.fx.clear()
        self.celebrate = None

    def clear_hints(self) -> None:
        self.source_glow.clear()
        self.target_ring.clear()
        self.ghost = None

    def glow_source(self, cell: tuple[int, int], until: float) -> None:
        if len(self.source_glow) >= MAX_GLOWS:
            self.source_glow.clear()
        self.source_glow[cell] = until

    def ring_target(self, cell: tuple[int, int], until: float) -> None:
        if len(self.target_ring) >= MAX_GLOWS:
            self.target_ring.clear()
        self.target_ring[cell] = until

    def add_fx(self, name: str, center: tuple[int, int], start: float) -> None:
        self.fx.append((name, center, start))

    def prune(self, now: float) -> None:
        self.drops = {k: v for k, v in self.drops.items() if now - v < DROP_SECONDS}
        if self.wobble is not None and now - self.wobble[2] >= WOBBLE_SECONDS:
            self.wobble = None
        self.source_glow = {k: v for k, v in self.source_glow.items() if v > now}
        self.target_ring = {k: v for k, v in self.target_ring.items() if v > now}
        if self.ghost is not None and self.ghost[2] <= now:
            self.ghost = None
        self.tray_hops = {k: v for k, v in self.tray_hops.items() if now - v < HOP_SECONDS}
        self.pokes = {k: v for k, v in self.pokes.items() if now - v < POKE_SECONDS}
        while self.fx and now - self.fx[0][2] > 3 * FX_FRAME_SECONDS + 1.0:
            self.fx.popleft()

    def active(self, now: float) -> bool:
        return bool(
            self.drops or self.wobble or self.source_glow or self.target_ring or self.ghost
            or self.tray_hops or self.pokes or self.fx
            or (self.celebrate is not None and now - self.celebrate < CELEBRATE_SECONDS)
        )


@dataclass(frozen=True, slots=True)
class SceneView:
    """Everything one frame needs from the app (read-only)."""

    axis: MirrorAxis
    picture_cells: frozenset[tuple[int, int]]
    tiles: Mapping[tuple[int, int], Piece]
    tray: tuple[Piece, ...]
    tray_rects: tuple[pygame.Rect, ...]
    held: int | None = None
    dragging: tuple[int, int] | None = None
    hovered_tile: int | None = None
    hovered_cell: tuple[int, int] | None = None
    intro: float = 1.0


class MirrorRenderer:
    """Draw one frame of the mirror stage from a ``SceneView``."""

    def __init__(self, art: MirrorArt, cast: LilliCast) -> None:
        self._art = art
        self._cast = cast

    def draw(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        surface.blit(self._art.scene(view.picture_cells, view.axis, len(view.tray)), (0, 0))
        self._board_tiles(surface, view, motion, now)
        self._hints(surface, view, motion, now)
        self._tray(surface, view, motion, now)
        self._cast.draw(surface)
        self._fx(surface, motion, now)
        if view.dragging is not None and view.held is not None and 0 <= view.held < len(view.tray):
            image = self._art.tile(view.tray[view.held], TILE_SIZE + 6)
            surface.blit(image, image.get_rect(center=view.dragging))

    # -- board ------------------------------------------------------------------

    def _board_tiles(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        celebrate = motion.celebrate
        for cell, piece in view.tiles.items():
            rect = cell_rect(*cell)
            dx = dy = 0
            started = motion.drops.get(cell)
            if started is not None:
                t = min(1.0, (now - started) / DROP_SECONDS)
                dy = -int(round(18 * (1 - t) * (1 - t)))
            poke = motion.pokes.get(cell)
            if poke is not None:
                dx = int(round(math.sin((now - poke) * 40) * 4 * (1 - (now - poke) / POKE_SECONDS)))
            if celebrate is not None:
                # A happy wave that starts at the mirror line and runs outwards.
                delay = 0.09 * _distance_from_mirror(cell, view.axis)
                t = now - celebrate - delay
                if 0 <= t < 0.5:
                    dy -= int(round(math.sin(math.pi * t / 0.5) * 14))
            if view.intro < 1.0:
                dy += int(round((1.0 - view.intro) * 20))
            image = self._art.tile(piece, TILE_SIZE)
            surface.blit(image, image.get_rect(center=(rect.centerx + dx, rect.centery + dy)))
        if motion.wobble is not None:
            cell, piece, started = motion.wobble
            t = (now - started) / WOBBLE_SECONDS
            rect = cell_rect(*cell)
            dx = int(round(math.sin(t * math.pi * 6) * 7 * (1 - t)))
            image = self._art.ghost(piece, TILE_SIZE) if t > 0.6 else self._art.tile(piece, TILE_SIZE)
            surface.blit(image, image.get_rect(center=(rect.centerx + dx, rect.centery)))
        if celebrate is not None and now - celebrate < CELEBRATE_SECONDS:
            flash = self._art.line_flash(view.axis)
            alpha = int(255 * max(0.0, math.sin(math.pi * min(1.0, (now - celebrate) / 1.2))))
            flash.set_alpha(alpha)
            surface.blit(flash, GRID_RECT.inflate(40, 40).topleft)

    def _hints(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        pulse = 0.55 + 0.45 * math.sin(now * 5.5)
        ring = self._art.glow_ring(CELL - 4)
        ring.set_alpha(int(255 * pulse))
        for cell in motion.source_glow:
            surface.blit(ring, ring.get_rect(center=cell_rect(*cell).center))
        for cell in motion.target_ring:
            surface.blit(ring, ring.get_rect(center=cell_rect(*cell).center))
        if motion.ghost is not None:
            cell, piece, _ = motion.ghost
            ghost = self._art.ghost(piece, TILE_SIZE)
            ghost.set_alpha(int(150 + 105 * pulse))
            surface.blit(ghost, ghost.get_rect(center=cell_rect(*cell).center))
            ghost.set_alpha(None)
        # Preview of the tile in hand over the cell under the pointer.
        if (
            view.held is not None
            and view.hovered_cell is not None
            and view.hovered_cell not in view.tiles
            and view.hovered_cell not in view.picture_cells
            and 0 <= view.held < len(view.tray)
        ):
            ghost = self._art.ghost(view.tray[view.held], TILE_SIZE)
            surface.blit(ghost, ghost.get_rect(center=cell_rect(*view.hovered_cell).center))

    # -- tray -------------------------------------------------------------------

    def _tray(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        for index, (piece, rect) in enumerate(zip(view.tray, view.tray_rects)):
            dy = 0
            hop = motion.tray_hops.get(index)
            if hop is not None:
                dy = -int(round(math.sin(math.pi * min(1.0, (now - hop) / HOP_SECONDS)) * 16))
            held = index == view.held
            if held:
                ring = self._art.hand_ring(rect.width - 2)
                surface.blit(ring, ring.get_rect(center=(rect.centerx, rect.centery - 6)))
                dy -= 6
            elif index == view.hovered_tile:
                dy -= 3
            if held and view.dragging is not None:
                ghost = self._art.ghost(piece, TRAY_TILE)
                surface.blit(ghost, ghost.get_rect(center=(rect.centerx, rect.centery + dy)))
                continue
            image = self._art.tile(piece, TRAY_TILE)
            surface.blit(image, image.get_rect(center=(rect.centerx, rect.centery + dy)))

    def _fx(self, surface: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for name, center, start in motion.fx:
            if now < start:
                continue
            frames = self._art.fx_frames(name)
            if not frames:
                continue
            index = int((now - start) / FX_FRAME_SECONDS)
            if index >= len(frames) + 2:
                continue
            frame = frames[min(index, len(frames) - 1)]
            surface.blit(frame, frame.get_rect(center=center))


def _distance_from_mirror(cell: tuple[int, int], axis: MirrorAxis) -> int:
    row, col = cell
    dc = min(abs(col - (HALF_COLS - 1)), abs(col - HALF_COLS))
    dr = min(abs(row - (HALF_ROWS - 1)), abs(row - HALF_ROWS))
    if axis is MirrorAxis.VERTICAL:
        return dc
    if axis is MirrorAxis.HORIZONTAL:
        return dr
    return dc + dr


def mirror_points(axis: MirrorAxis) -> tuple[tuple[int, int], ...]:
    """Where the sparkles run along the mirror line(s) at a celebration."""

    points: list[tuple[int, int]] = []
    if axis in (MirrorAxis.VERTICAL, MirrorAxis.BOTH):
        points += [(MIRROR_X, GRID_RECT.top + GRID_RECT.height * k // 4) for k in (0, 1, 2, 3, 4)]
    if axis in (MirrorAxis.HORIZONTAL, MirrorAxis.BOTH):
        points += [(GRID_RECT.left + GRID_RECT.width * k // 6, MIRROR_Y) for k in (0, 1, 2, 4, 5, 6)]
    return tuple(points)


__all__ = [
    "CELEBRATE_SECONDS",
    "DROP_SECONDS",
    "LilliCast",
    "MirrorRenderer",
    "SceneMotion",
    "SceneView",
    "WOBBLE_SECONDS",
    "mirror_points",
]

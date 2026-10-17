"""Frame composition for La Torre delle Forme (blits only).

``SceneView`` is the read-only state one frame needs, ``SceneMotion`` the
small bounded set of running animations (blocks dropping in, a block that
does not fit wobbling and fading, hint glows, Dani's demonstration glide,
kit hops and "turn it" pulses, sparkles, the finished-build wave) and
``DaniCast`` wraps the shared ``CastFeedback`` with the hint ``pose_point``.
Nothing here decodes, scales or renders text per frame: every surface comes
prepared from ``TorreArt``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .torre_art import OUTLINE_PAD, TorreArt
    from .torre_layout import CARD_RECT, CELL, DANI_HEIGHT, DANI_MIDBOTTOM, BoardFrame, turn_rect
    from .torre_model import Block, BuildPlan, OutlineStyle, Placement
else:
    from torre_art import OUTLINE_PAD, TorreArt
    from torre_layout import CARD_RECT, CELL, DANI_HEIGHT, DANI_MIDBOTTOM, BoardFrame, turn_rect
    from torre_model import Block, BuildPlan, OutlineStyle, Placement

DROP_SECONDS = 0.3
WOBBLE_SECONDS = 0.9
HOP_SECONDS = 0.55
SHAKE_SECONDS = 0.5
GLIDE_SECONDS = 1.3
FX_FRAME_SECONDS = 0.12
CELEBRATE_SECONDS = 2.4
MAX_FX = 16


class DaniCast:
    """Dani: shared cheer/think feedback plus the hint ``pose_point``.

    He stands left of the workbench; the canonical point pose points right,
    at the build.
    """

    def __init__(self, feedback: CastFeedback, art: TorreArt, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._clock = clock
        self._point = art.dani("pose_point", DANI_HEIGHT)
        self._loader = art.loader
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
            surface.blit(self._loader.presentable(self._point, surface), self._point.get_rect(midbottom=(DANI_MIDBOTTOM[0] + bob, DANI_MIDBOTTOM[1])))
            return
        self.feedback.draw(surface, DANI_MIDBOTTOM)


@dataclass(frozen=True, slots=True)
class Glide:
    """Dani's demonstration: a see-through block glides from the kit to its place."""

    block: Block
    start: tuple[int, int]
    target: Placement
    began: float


@dataclass(slots=True)
class SceneMotion:
    """Running animations, each bounded and pruned by time."""

    drops: dict[Placement, float] = field(default_factory=dict)
    wobble: tuple[Block, tuple[int, int], float] | None = None
    target_glow: tuple[Placement, float] | None = None
    glide: Glide | None = None
    tray_hops: dict[int, float] = field(default_factory=dict)
    tray_shakes: dict[int, float] = field(default_factory=dict)
    turn_hints: dict[int, float] = field(default_factory=dict)
    outline_pulse: float | None = None
    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    celebrate: float | None = None

    def reset(self) -> None:
        self.drops.clear()
        self.wobble = None
        self.clear_hints()
        self.tray_hops.clear()
        self.tray_shakes.clear()
        self.fx.clear()
        self.celebrate = None

    def clear_hints(self) -> None:
        self.target_glow = None
        self.glide = None
        self.turn_hints.clear()
        self.outline_pulse = None

    def add_fx(self, name: str, center: tuple[int, int], start: float) -> None:
        self.fx.append((name, center, start))

    def prune(self, now: float) -> None:
        self.drops = {k: v for k, v in self.drops.items() if now - v < DROP_SECONDS}
        if self.wobble is not None and now - self.wobble[2] >= WOBBLE_SECONDS:
            self.wobble = None
        if self.target_glow is not None and self.target_glow[1] <= now:
            self.target_glow = None
        if self.glide is not None and now - self.glide.began >= GLIDE_SECONDS + 0.8:
            self.glide = None
        self.tray_hops = {k: v for k, v in self.tray_hops.items() if now - v < HOP_SECONDS}
        self.tray_shakes = {k: v for k, v in self.tray_shakes.items() if now - v < SHAKE_SECONDS}
        self.turn_hints = {k: v for k, v in self.turn_hints.items() if v > now}
        if self.outline_pulse is not None and now - self.outline_pulse > 1.2:
            self.outline_pulse = None
        while self.fx and now - self.fx[0][2] > 3 * FX_FRAME_SECONDS + 1.0:
            self.fx.popleft()

    def active(self, now: float) -> bool:
        return bool(
            self.drops or self.wobble or self.target_glow or self.glide or self.tray_hops
            or self.tray_shakes or self.turn_hints or self.outline_pulse is not None or self.fx
            or (self.celebrate is not None and now - self.celebrate < CELEBRATE_SECONDS)
        )


@dataclass(frozen=True, slots=True)
class SceneView:
    """Everything one frame needs from the app (read-only)."""

    plan: BuildPlan
    style: OutlineStyle
    frame: BoardFrame
    placed: tuple[Placement, ...]
    kit: tuple[Block, ...]
    tray_rects: tuple[pygame.Rect, ...]
    held: int | None = None
    dragging: tuple[int, int] | None = None
    hovered_tile: int | None = None
    preview: Placement | None = None
    intro: float = 1.0


class TorreRenderer:
    """Draw one frame of the playroom from a ``SceneView``."""

    def __init__(self, art: TorreArt, cast: DaniCast) -> None:
        self._art = art
        self._cast = cast

    def draw(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        surface.blit(self._art.scene(len(view.kit)), (0, 0))
        card = self._art.card(view.plan.picture)
        if card is not None:
            surface.blit(card, CARD_RECT.move(-8, -8).topleft)
        self._outline(surface, view, motion, now)
        self._hints(surface, view, motion, now)
        self._blocks(surface, view, motion, now)
        self._miss(surface, motion, now)
        self._tray(surface, view, motion, now)
        self._cast.draw(surface)
        self._glide(surface, view, motion, now)
        self._fx(surface, motion, now)
        if view.dragging is not None and view.held is not None and 0 <= view.held < len(view.kit):
            image = self._art.block(view.kit[view.held], CELL)
            surface.blit(image, image.get_rect(center=view.dragging))

    # -- board ------------------------------------------------------------------------

    def _outline(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        outline = self._art.outline(view.plan, view.style)
        alpha = 255
        if view.intro < 1.0:
            alpha = int(255 * view.intro)
        if motion.outline_pulse is not None:
            t = (now - motion.outline_pulse) / 1.2
            alpha = int(255 * (0.75 + 0.25 * math.cos(t * math.tau * 2)))
        outline.set_alpha(alpha)
        surface.blit(outline, (view.frame.left - OUTLINE_PAD, view.frame.top - OUTLINE_PAD))
        outline.set_alpha(255)

    def _blocks(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        celebrate = motion.celebrate
        for placement in view.placed:
            rect = view.frame.placement_rect(placement)
            dy = 0
            started = motion.drops.get(placement)
            if started is not None:
                t = min(1.0, (now - started) / DROP_SECONDS)
                dy = -int(round(22 * (1 - t) * (1 - t)))
            if celebrate is not None:
                # A happy wave that runs from the bench up to the top block.
                delay = 0.1 * (view.frame.rows - placement.row - placement.block.size[1])
                t = now - celebrate - delay
                if 0 <= t < 0.5:
                    dy -= int(round(math.sin(math.pi * t / 0.5) * 16))
            image = self._art.block(placement.block, CELL)
            surface.blit(image, rect.move(0, dy))

    def _hints(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        pulse = 0.55 + 0.45 * math.sin(now * 5.5)
        if motion.target_glow is not None:
            placement = motion.target_glow[0]
            glow = self._art.glow(placement.block, CELL)
            glow.set_alpha(int(255 * pulse))
            surface.blit(glow, view.frame.placement_rect(placement).move(-7, -7).topleft)
            glow.set_alpha(255)
        if view.preview is not None:
            # "It fits here!": the outline glows where the block in hand would go.
            glow = self._art.glow(view.preview.block, CELL)
            surface.blit(glow, view.frame.placement_rect(view.preview).move(-7, -7).topleft)
            if view.dragging is None:
                ghost = self._art.ghost(view.preview.block, CELL)
                surface.blit(ghost, view.frame.placement_rect(view.preview))

    def _miss(self, surface: pygame.Surface, motion: SceneMotion, now: float) -> None:
        if motion.wobble is None:
            return
        block, center, started = motion.wobble
        t = (now - started) / WOBBLE_SECONDS
        dx = int(round(math.sin(t * math.pi * 6) * 8 * (1 - t)))
        image = self._art.ghost(block, CELL) if t > 0.55 else self._art.block(block, CELL)
        surface.blit(image, image.get_rect(center=(center[0] + dx, center[1])))

    def _glide(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        glide = motion.glide
        if glide is None or now < glide.began:
            return
        t = min(1.0, (now - glide.began) / GLIDE_SECONDS)
        ease = t * t * (3 - 2 * t)
        end = view.frame.placement_rect(glide.target).center
        x = glide.start[0] + (end[0] - glide.start[0]) * ease
        y = glide.start[1] + (end[1] - glide.start[1]) * ease - math.sin(math.pi * ease) * 70
        ghost = self._art.ghost(glide.target.block, CELL)
        if t >= 1.0:
            ghost.set_alpha(int(255 * (0.45 + 0.4 * math.sin(now * 6.0))))
        surface.blit(ghost, ghost.get_rect(center=(int(x), int(y))))
        ghost.set_alpha(255)

    # -- tray -----------------------------------------------------------------------

    def _tray(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        pulse = 0.55 + 0.45 * math.sin(now * 5.5)
        for index, (block, rect) in enumerate(zip(view.kit, view.tray_rects)):
            dx = dy = 0
            hop = motion.tray_hops.get(index)
            if hop is not None:
                dy = -int(round(math.sin(math.pi * min(1.0, (now - hop) / HOP_SECONDS)) * 16))
                glow = self._art.slot_glow()
                surface.blit(glow, glow.get_rect(center=rect.center))
            shake = motion.tray_shakes.get(index)
            if shake is not None:
                t = (now - shake) / SHAKE_SECONDS
                dx = int(round(math.sin(t * math.pi * 6) * 7 * (1 - t)))
            held = index == view.held
            if held:
                ring = self._art.hand_ring()
                surface.blit(ring, ring.get_rect(center=(rect.centerx, rect.centery - 6)))
                dy -= 6
            elif index == view.hovered_tile:
                dy -= 3
            if held and view.dragging is not None:
                continue
            image = self._art.tray_block(block)
            surface.blit(image, image.get_rect(center=(rect.centerx + dx, rect.centery + dy)))
            if index in motion.turn_hints:
                # "Turn it": the turn arrow bobs above the block and the turn
                # button glows (the button itself is drawn by the kit on top).
                badge = self._art.turn_badge(56)
                bob = int(math.sin(now * 6.0) * 4)
                surface.blit(badge, badge.get_rect(midbottom=(rect.centerx, rect.top + 10 + bob)))
        if motion.turn_hints:
            button = turn_rect(len(view.kit))
            glow = self._art.slot_glow(button.width + 22)
            glow.set_alpha(int(255 * pulse))
            surface.blit(glow, glow.get_rect(center=button.center))
            glow.set_alpha(255)

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


__all__ = [
    "CELEBRATE_SECONDS",
    "DaniCast",
    "GLIDE_SECONDS",
    "Glide",
    "SceneMotion",
    "SceneView",
    "TorreRenderer",
    "WOBBLE_SECONDS",
]

"""Frame drawing for Tito's Marble Run (blits of prepared surfaces only).

``RunCast`` is Tito beside the board: ``CastFeedback`` owns the shared grammar
(``pose_cheer`` when the marble lands in the basket, ``pose_think`` when it
stops or rolls away) and this wrapper adds the ``pose_point`` hint and the
``pose_wave`` hello when a board starts. ``RunMotion`` holds the short-lived,
hard-bounded presentation state: FX bursts, slot pulses, the demonstration
ghost, the basket wiggle and the bumper squash.
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
    from .ramp_art import MARBLE_FRAMES, RunArt
    from .ramp_content import MARBLE_RADIUS, PieceKind
    from .ramp_engine import MarbleRun
    from .ramp_layout import BoardView
    from .ramp_model import BoardState, HintAction, HintStep
else:
    from ramp_art import MARBLE_FRAMES, RunArt
    from ramp_content import MARBLE_RADIUS, PieceKind
    from ramp_engine import MarbleRun
    from ramp_layout import BoardView
    from ramp_model import BoardState, HintAction, HintStep

FX_SECONDS = 0.55
PULSE_SECONDS = 1.6
DEMO_SECONDS = 2.6
DEMO_TRAVEL_SECONDS = 0.9
WIGGLE_SECONDS = 0.7
SQUASH_SECONDS = 0.25
POP_SECONDS = 0.22
MAX_FX = 12
MAX_PULSES = 6


class RunCast:
    """Tito: shared cheer/think grammar + point and wave poses."""

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

    def wave(self, seconds: float = 1.4) -> None:
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
class Drag:
    """A piece following the pointer (from the tray or from a slot)."""

    piece: int
    position: tuple[int, int]
    from_slot: int | None
    hover_slot: int | None = None


@dataclass(slots=True)
class RunMotion:
    """Bounded transient presentation state for one board."""

    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    pulses: dict[int, float] = field(default_factory=dict)  # slot -> start
    demo: tuple[HintStep, float, tuple[int, int] | None] | None = None  # step, start, travel origin
    go_pulse: float = -10.0
    wiggle: float = -10.0
    squash: dict[int, float] = field(default_factory=dict)  # slot -> start
    pops: dict[int, float] = field(default_factory=dict)  # slot -> start

    def clear(self) -> None:
        self.fx.clear()
        self.pulses.clear()
        self.demo = None
        self.go_pulse = -10.0
        self.wiggle = -10.0
        self.squash.clear()
        self.pops.clear()

    def add_fx(self, name: str, position: tuple[int, int], size: int, now: float) -> None:
        self.fx.append((name, position, size, now))

    def pulse(self, slot: int, now: float) -> None:
        self.pulses[slot] = now
        while len(self.pulses) > MAX_PULSES:
            self.pulses.pop(next(iter(self.pulses)))

    def prune(self, now: float) -> None:
        while self.fx and now - self.fx[0][3] > FX_SECONDS:
            self.fx.popleft()
        for table, seconds in ((self.pulses, PULSE_SECONDS), (self.squash, SQUASH_SECONDS), (self.pops, POP_SECONDS)):
            for key in [key for key, start in table.items() if now - start > seconds]:
                del table[key]
        if self.demo is not None and now - self.demo[1] > DEMO_SECONDS:
            self.demo = None

    def active(self, now: float) -> bool:
        return bool(
            self.fx
            or self.pulses
            or self.demo is not None
            or self.squash
            or self.pops
            or now - self.wiggle < WIGGLE_SECONDS
            or now - self.go_pulse < PULSE_SECONDS
        )


def _hop(elapsed: float, duration: float, height: float) -> int:
    if elapsed < 0 or elapsed > duration:
        return 0
    return -int(round(abs(math.sin(math.pi * elapsed / (duration / 2))) * height))


class RunRenderer:
    """Draw one board frame from the prepared scene and sprites."""

    def __init__(self, art: RunArt, cast: RunCast) -> None:
        self._fast = PreparedSurfaces(max_entries=96)  # RLE copies of per-frame sprites (pygame_blit)
        self.art = art
        self.cast = cast

    def draw(
        self,
        surface: pygame.Surface,
        scene: pygame.Surface,
        state: BoardState,
        run: MarbleRun | None,
        view: BoardView,
        motion: RunMotion,
        now: float,
        *,
        trail: tuple[tuple[float, float], ...] = (),
        marble_home: bool = True,
        in_basket: bool = False,
        drag: Drag | None = None,
        go_rect: pygame.Rect | None = None,
        cast_midbottom: tuple[int, int] = (87, 596),
    ) -> None:
        surface.blit(scene, (0, 0))
        board = state.board
        sprites = self.art.sprites(view)

        # Last run's path, so the child can see where the marble went.
        for point in trail[::2]:
            dot = sprites.trail
            surface.blit(self._fast(dot), dot.get_rect(center=view.point(*point)))

        # Shining slots (empty) + hint pulses / drag hover.
        hover = drag.hover_slot if drag is not None else None
        for index, centre in enumerate(board.slots):
            rect = view.slot_rect(centre)
            if index in motion.pulses or index == hover:
                surface.blit(self._fast(sprites.slot_glow), sprites.slot_glow.get_rect(center=rect.center))
            if state.occupant(index) is None:
                surface.blit(self._fast(sprites.slot_shine), sprites.slot_shine.get_rect(center=rect.center))
                if sprites.slot is not None:
                    surface.blit(self._fast(sprites.slot), rect)

        # Pieces.
        for placement in state.placements():
            if drag is not None and drag.piece == placement.piece:
                continue
            kind = state.kind(placement.piece)
            sprite = sprites.piece(kind, placement.facing)
            if sprite is None:
                continue
            x, y = view.point(*board.slots[placement.slot])
            shadow = sprites.shadow(kind, placement.facing)
            if shadow is not None:
                shadow.blit(surface, (x + sprites.shadow_offset[0], y + sprites.shadow_offset[1]))
            y += _hop(now - motion.pops.get(placement.slot, -10.0), POP_SECONDS, view.length(10))
            if kind is PieceKind.BUMPER and placement.slot in motion.squash:
                y += int(round(math.sin(math.pi * (now - motion.squash[placement.slot]) / SQUASH_SECONDS) * view.length(4)))
            sprite.blit(surface, (x, y))

        # Demonstration ghost (what to do next).
        if motion.demo is not None:
            self._draw_demo(surface, state, view, motion, now)

        # Basket back, marble, basket front.
        bx, by = view.point(board.basket.x, board.basket.floor)
        wiggle = now - motion.wiggle
        if 0 <= wiggle < WIGGLE_SECONDS:
            bx += int(round(math.sin(wiggle * 36.0) * (1 - wiggle / WIGGLE_SECONDS) * view.length(6)))
        sprites.basket_back.blit(surface, (bx, by))
        if marble_home or in_basket or run is not None:
            if in_basket:
                position = (board.basket.x, board.basket.rim - MARBLE_RADIUS * 0.1)
                spin = 0.0
            elif run is not None and not marble_home:
                position = run.drawn_position()
                spin = run.marble.spin
            else:
                position = (board.start.x, board.start.y)
                spin = 0.0
            frame = sprites.marble[int(round(spin / (2 * math.pi) * MARBLE_FRAMES)) % MARBLE_FRAMES]
            mx, my = view.point(*position)
            surface.blit(self._fast(frame), frame.get_rect(center=(mx, my)))
        sprites.basket_front.blit(surface, (bx, by))

        # FX bursts.
        for name, position, size, start in motion.fx:
            frames = self.art.fx_frames(name, size)
            if not frames:
                continue
            index = min(len(frames) - 1, int((now - start) / FX_SECONDS * len(frames)))
            frame = frames[index]
            surface.blit(self._fast(frame), frame.get_rect(center=position))

        # GO pulse (hint: "now press GO").
        if go_rect is not None and now - motion.go_pulse < PULSE_SECONDS:
            glow = self.art.glow((go_rect.width + 30, go_rect.height + 30))
            surface.blit(self._fast(glow), glow.get_rect(center=go_rect.center))

        self.cast.draw(surface, cast_midbottom)

        if drag is not None:
            sprite = sprites.piece(state.kind(drag.piece), state.facings[drag.piece])
            if sprite is not None:
                shadow = sprites.marble_shadow
                surface.blit(self._fast(shadow), shadow.get_rect(center=(drag.position[0], drag.position[1] + view.length(30))))
                sprite.blit(surface, drag.position)

    def _draw_demo(self, surface: pygame.Surface, state: BoardState, view: BoardView, motion: RunMotion, now: float) -> None:
        assert motion.demo is not None
        step, start, origin = motion.demo
        if step.slot is None:
            return
        sprites = self.art.sprites(view)
        x, y = view.point(*state.board.slots[step.slot])
        lift = _hop(now - start, 0.9, view.length(12))
        if step.action is HintAction.PLACE and step.kind is not None:
            ghost = sprites.piece(step.kind, step.facing, ghost=True)
            if origin is not None:
                # The ghost piece travels from its tray tile to the slot, carried by
                # the shared drag hand: the demonstration of "put it here".
                t = min(1.0, max(0.0, (now - start) / DEMO_TRAVEL_SECONDS))
                t = 1.0 - (1.0 - t) ** 3
                x = int(round(origin[0] + (x - origin[0]) * t))
                y = int(round(origin[1] + (y - origin[1]) * t))
                lift = 0
            if ghost is not None:
                ghost.blit(surface, (x, y + lift))
            hand = self.art.art.image("icon.hud.drag_hint", view.length(70))
            if hand is not None and origin is not None:
                surface.blit(self._fast(hand), hand.get_rect(topleft=(x - view.length(6), y + view.length(4))))
            return
        glyph = self.art.art.image(
            "icon.hud.rotate" if step.action is HintAction.TURN else "icon.hud.undo", view.length(64)
        )
        if glyph is not None:
            surface.blit(self._fast(glyph), glyph.get_rect(midbottom=(x, y - view.length(34) + lift)))


__all__ = ["Drag", "RunCast", "RunMotion", "RunRenderer"]

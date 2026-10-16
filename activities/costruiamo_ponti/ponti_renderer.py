"""Frame drawing for Bridge Builders (blits of prepared surfaces only).

``TravelerCast`` is the friend who has to cross: ``CastFeedback`` owns the
shared grammar (``pose_cheer`` at the picnic, ``pose_think`` when the walk
stops) and this wrapper adds the ``pose_point`` hint, the ``pose_wave`` hello
and, for a heavy friend, the pumpkin held overhead. ``BridgeMotion`` holds the
short-lived, hard-bounded presentation state: FX bursts, target pulses, the
demonstration ghost, plank pops and the "missing length" marks after a short
plank.
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
    from .ponti_art import ANGLE_STEP, BridgeArt, rotate_point, rotated_center
    from .ponti_layout import BANK_TOP, UNIT, CrossingView, thickness
    from .ponti_model import BridgeState, HintAction, HintStep, spot_seat
    from .ponti_run import BridgeRun
else:
    from ponti_art import ANGLE_STEP, BridgeArt, rotate_point, rotated_center
    from ponti_layout import BANK_TOP, UNIT, CrossingView, thickness
    from ponti_model import BridgeState, HintAction, HintStep, spot_seat
    from ponti_run import BridgeRun

FX_SECONDS = 0.55
PULSE_SECONDS = 1.6
DEMO_SECONDS = 2.6
DEMO_TRAVEL_SECONDS = 0.9
POP_SECONDS = 0.22
MAX_FX = 12
MAX_PULSES = 6
ROPE = (92, 70, 58)
LOAD_SHARE = 0.46  # pumpkin height relative to the friend


class TravelerCast:
    """The crossing friend: shared cheer/think grammar + point, wave and a heavy load."""

    def __init__(
        self,
        feedback: CastFeedback,
        point: pygame.Surface | None,
        wave: pygame.Surface | None,
        load: pygame.Surface | None,
        clock: Callable[[], float],
    ) -> None:
        self._fast = PreparedSurfaces(max_entries=96)  # RLE copies of per-frame sprites (pygame_blit)
        self.feedback = feedback
        self._point = point
        self._wave = wave
        self.load = load
        self._clock = clock
        self._point_until = 0.0
        self._wave_until = 0.0

    @property
    def character(self) -> str:
        return self.feedback.character

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

    def draw(self, target: pygame.Surface, midbottom: tuple[int, int], height: int) -> None:
        drawn = False
        if self.feedback.pose is CastPose.IDLE:
            extra = self._point if self.pointing else self._wave if self.waving else None
            if extra is not None:
                target.blit(self._fast(extra), extra.get_rect(midbottom=midbottom))
                drawn = True
        if not drawn:
            self.feedback.draw(target, midbottom)
        if self.load is not None:
            # Held overhead: the heavy load is the visible "weight" cue.
            target.blit(self._fast(self.load), self.load.get_rect(midbottom=(midbottom[0], midbottom[1] - int(height * 0.8))))


@dataclass(slots=True)
class Drag:
    """A piece following the pointer (from the tray or from the bridge)."""

    piece: int
    position: tuple[int, int]
    from_bridge: bool
    hover: str | None = None  # target id under the pointer


@dataclass(slots=True)
class BridgeMotion:
    """Bounded transient presentation state for one crossing."""

    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    pulses: dict[str, float] = field(default_factory=dict)  # target id -> start
    demo: tuple[HintStep, float, tuple[int, int] | None] | None = None
    go_pulse: float = -10.0
    pops: dict[int, float] = field(default_factory=dict)  # piece -> start
    missing: tuple[float, float] | None = None  # units of a span still uncovered

    def clear(self) -> None:
        self.fx.clear()
        self.pulses.clear()
        self.demo = None
        self.go_pulse = -10.0
        self.pops.clear()
        self.missing = None

    def add_fx(self, name: str, position: tuple[int, int], size: int, now: float) -> None:
        self.fx.append((name, position, size, now))

    def pulse(self, target: str, now: float) -> None:
        self.pulses[target] = now
        while len(self.pulses) > MAX_PULSES:
            self.pulses.pop(next(iter(self.pulses)))

    def prune(self, now: float) -> None:
        while self.fx and now - self.fx[0][3] > FX_SECONDS:
            self.fx.popleft()
        for table, seconds in ((self.pulses, PULSE_SECONDS), (self.pops, POP_SECONDS)):
            for key in [key for key, start in table.items() if now - start > seconds]:
                del table[key]
        if self.demo is not None and now - self.demo[1] > DEMO_SECONDS:
            self.demo = None

    def active(self, now: float) -> bool:
        return bool(self.fx or self.pulses or self.demo is not None or self.pops or now - self.go_pulse < PULSE_SECONDS)


def _hop(elapsed: float, duration: float, height: float) -> int:
    if elapsed < 0 or elapsed > duration:
        return 0
    return -int(round(abs(math.sin(math.pi * elapsed / (duration / 2))) * height))


class BridgeRenderer:
    """Draw one crossing frame from the prepared scene and sprites."""

    def __init__(self, art: BridgeArt, cast: TravelerCast, cast_height: int) -> None:
        self._fast = PreparedSurfaces(max_entries=96)  # RLE copies of per-frame sprites (pygame_blit)
        self.art = art
        self.cast = cast
        self.cast_height = cast_height

    def draw(
        self,
        surface: pygame.Surface,
        scene: pygame.Surface,
        state: BridgeState,
        view: CrossingView,
        motion: BridgeMotion,
        now: float,
        *,
        run: BridgeRun | None = None,
        drag: Drag | None = None,
        targets: dict[str, pygame.Rect] | None = None,
        go_rect: pygame.Rect | None = None,
    ) -> None:
        surface.blit(scene, (0, 0))
        targets = targets or {}
        art = self.art
        dragged = drag.piece if drag is not None else None

        # Glow under hint pulses / the drag hover target.
        hover = drag.hover if drag is not None else None
        for target_id, rect in targets.items():
            if target_id in motion.pulses or target_id == hover:
                glow = art.glow((rect.width + 36, rect.height + 36))
                surface.blit(self._fast(glow), glow.get_rect(center=rect.center))

        # Pillars on their rocks (with their own rope post).
        for spot in state.pillar_spots():
            index = state.pillar_at(spot)
            if index is None or index == dragged:
                continue
            rect = view.pillar_rect(spot)
            lift = _hop(now - motion.pops.get(index, -10.0), POP_SECONDS, 10)
            surface.blit(art.pillar(), rect.move(0, lift))
            art.paint_post(surface, view.seat_x(spot_seat(spot)), BANK_TOP + lift)

        # Measuring marks: one dash per unit of open water.
        missing = motion.missing
        for span in state.spans():
            for unit in range(int(span.start), int(math.ceil(span.end))):
                gold = missing is not None and missing[0] <= unit < missing[1]
                dash = art.dash_missing if gold else art.dash
                surface.blit(self._fast(dash), dash.get_rect(center=(view.x(unit + 0.5), BANK_TOP - 6)))

        # Planks: standing (build), swinging down / lying across (test).
        angle = run.angle() if run is not None else 90.0
        for index, where in enumerate(state.seat_of):
            if where is None or state.is_pillar(index) or index == dragged:
                continue
            self._draw_plank(surface, state, view, index, where, angle, run, motion, now)

        if motion.demo is not None:
            self._draw_demo(surface, state, view, motion, now)

        if run is not None:
            midbottom = run.traveler_midbottom()
        else:
            midbottom = (view.home_x, BANK_TOP + 4)
        self.cast.draw(surface, midbottom, self.cast_height)

        for name, position, size, start in motion.fx:
            frames = art.fx_frames(name, size)
            if not frames:
                continue
            frame = frames[min(len(frames) - 1, int((now - start) / FX_SECONDS * len(frames)))]
            surface.blit(self._fast(frame), frame.get_rect(center=position))

        if go_rect is not None and now - motion.go_pulse < PULSE_SECONDS:
            glow = art.glow((go_rect.width + 30, go_rect.height + 30))
            surface.blit(self._fast(glow), glow.get_rect(center=go_rect.center))

        if drag is not None:
            piece = state.piece(drag.piece)
            sprite = art.pillar() if state.is_pillar(drag.piece) else art.plank(piece).flat
            surface.blit(self._fast(sprite), sprite.get_rect(center=drag.position))

    def _draw_plank(
        self,
        surface: pygame.Surface,
        state: BridgeState,
        view: CrossingView,
        index: int,
        seat: str,
        angle: float,
        run: BridgeRun | None,
        motion: BridgeMotion,
        now: float,
    ) -> None:
        piece = state.piece(index)
        frames = self.art.plank(piece)
        seat_x = view.seat_x(seat)
        length = piece.length * UNIT
        thick = thickness(piece.strong)
        lift = _hop(now - motion.pops.get(index, -10.0), POP_SECONDS, 10)
        laid = run.plank_for(index) if run is not None else None
        if run is not None and laid is not None and run.sag > 0 and laid is run.bending and angle < 1:
            for x, strip in frames.strips:
                dy = run.sag_at(laid, seat_x + x + strip.get_width() / 2)
                surface.blit(self._fast(strip), (seat_x + x, BANK_TOP - thick + int(round(dy))))
            tip = (seat_x + length, BANK_TOP - thick // 2)
        else:
            step = int(round(angle / ANGLE_STEP))
            snapped = step * ANGLE_STEP
            image = frames.rotations[step]
            cx, cy = rotated_center(length, thick, snapped)
            surface.blit(self._fast(image), image.get_rect(center=(int(seat_x + cx), int(BANK_TOP + cy + lift))))
            tx, ty = rotate_point(length, -thick / 2, snapped)
            tip = (int(seat_x + tx), int(BANK_TOP + ty + lift))
        post = self.art.post_top(seat_x)
        pygame.draw.line(surface, ROPE, post, tip, 2)

    def _draw_demo(
        self,
        surface: pygame.Surface,
        state: BridgeState,
        view: CrossingView,
        motion: BridgeMotion,
        now: float,
    ) -> None:
        assert motion.demo is not None
        step, start, origin = motion.demo
        art = self.art
        t = min(1.0, max(0.0, (now - start) / DEMO_TRAVEL_SECONDS))
        t = 1.0 - (1.0 - t) ** 3
        hand = art.art.image("icon.hud.drag_hint", 64)
        if step.action is HintAction.PLACE_PLANK and step.seat is not None and step.signature is not None:
            length = step.signature[1] * UNIT
            thick = thickness(step.signature[2])
            ghost = next(
                (art.plank(state.piece(i)).upright_ghost for i in range(len(state.seat_of)) if state.piece(i).signature == step.signature),
                None,
            )
            if ghost is None or step.seat not in state.seats():
                return
            seat_x = view.seat_x(step.seat)
            cx, cy = rotated_center(length, thick, 90)
            end = (int(seat_x + cx), int(BANK_TOP + cy))
        elif step.action is HintAction.PLACE_PILLAR and step.spot is not None:
            ghost = art.pillar_ghost()
            end = view.pillar_rect(step.spot).center
        elif step.action is HintAction.REMOVE_PILLAR and step.spot is not None:
            glyph = art.art.image("icon.hud.undo", 60)
            if glyph is not None:
                lift = _hop(now - start, 0.9, 12)
                surface.blit(self._fast(glyph), glyph.get_rect(midbottom=(view.pillar_rect(step.spot).centerx, BANK_TOP - 12 + lift)))
            return
        else:
            return
        if origin is not None:
            position = (int(origin[0] + (end[0] - origin[0]) * t), int(origin[1] + (end[1] - origin[1]) * t))
        else:
            position = end
        surface.blit(self._fast(ghost), ghost.get_rect(center=position))
        if hand is not None and origin is not None:
            surface.blit(self._fast(hand), hand.get_rect(topleft=(position[0] - 6, position[1] + 4)))


__all__ = ["BridgeMotion", "BridgeRenderer", "Drag", "TravelerCast"]

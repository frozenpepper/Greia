"""Forest-walk scene presentation for Tito's Number Forest.

Draw order: cached woodland + paper card (static layer) → signposts on the
path with the numerals written this walk → the step on the card (meet: big
numeral + its forest friends counted into a frame; find: the frame sign;
trace: hollow numeral, the child's ink, the start dot, arrow and the
demonstrating hand; show: the numeral above the frames; bloom: the coloured
numeral with its friends popping in) → Tito → speaking/hint glows → kit
controls → counting rings → FX.

All images come pre-scaled from ``BoscoArt``; per frame there are only blits,
a few integer offsets and tiny vector marks (start dot ring, direction arrow,
counting ring). No text is rendered: numerals are stroke-font art, prompts
are spoken.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Final, Sequence

import pygame

from greia_platform.activity_controls import BodyShape, ControlKit, mix

if __package__:
    from .bosco_art import CREAM, GLOW, INK, BoscoArt, FrameGeometry, TraceInk, frame_cells_for
    from .bosco_controls import TITO_HEIGHT, TITO_MIDBOTTOM, ForestLayout
    from .bosco_model import ForestStep, NumeralItem, StepKind
    from .bosco_trace import TraceGuide
else:
    from bosco_art import CREAM, GLOW, INK, BoscoArt, FrameGeometry, TraceInk, frame_cells_for
    from bosco_controls import TITO_HEIGHT, TITO_MIDBOTTOM, ForestLayout
    from bosco_model import ForestStep, NumeralItem, StepKind
    from bosco_trace import TraceGuide


CARD_FILL: Final = (255, 248, 228)
LEAF: Final = (89, 184, 106)
PATH_GLYPH: Final = 66
PATH_FRIEND: Final = 62
FLIGHT_GLYPH: Final = 84
SPEAKING_LIFT: Final = 8
BLOOM_SECONDS: Final = 0.9
HAND_SIZE: Final = 92
# Fingertip of icon.hud.drag_hint (96-unit master), as a fraction of its size.
HAND_TIP: Final = (0.60, 0.12)


@dataclass(frozen=True, slots=True)
class TraceView:
    """Tracing state the renderer needs (geometry is local to the trace box)."""

    guide: TraceGuide
    ink: TraceInk
    stroke_index: int
    head: tuple[float, float] | None
    progress: float = 0.0
    demo_point: tuple[float, float] | None = None
    start_pulse: bool = False
    complete: bool = False


@dataclass(frozen=True, slots=True)
class SceneState:
    """Everything the renderer needs for one frame (built by the app)."""

    step: ForestStep | None
    season: str = "woodland_pond"
    written: Sequence[NumeralItem] = ()
    path_count: int = 2
    speaking: str | None = None
    hint_target: str | None = None
    pulse_phase: int = 0
    shake: tuple[str, int] | None = None
    tito_pointing: bool = False
    meet_revealed: int = 0
    trace: TraceView | None = None
    bloom: float | None = None
    flight: tuple[NumeralItem, tuple[int, int], tuple[int, int], float] | None = None
    sparkle_at: tuple[tuple[int, int], float] | None = None
    finale: float | None = None
    celebrating_choice: int | None = None
    # (option index, 1-based item) currently being counted aloud on a SHOW frame.
    counting: tuple[int, int] | None = None


class BoscoRenderer:
    """Render the forest walk; geometry comes from ``ForestLayout``."""

    def __init__(self, art: BoscoArt) -> None:
        self._art = art
        self.cast = None  # CastFeedback, injected by the app (shares the kit art cache)
        self.kit: ControlKit | None = None
        self.controls = None  # ForestControls, injected by the app (option frames)
        self._static: pygame.Surface | None = None
        self._static_key: tuple | None = None
        self._point = art.cast_pose("tito", "pose_point", TITO_HEIGHT)
        self._start_dot: dict[int, pygame.Surface] = {}
        self._rings: dict[int, pygame.Surface] = {}
        self._guides: dict[tuple[int, int, int], TraceGuide] = {}

    @property
    def art(self) -> BoscoArt:
        return self._art

    # -- caches -------------------------------------------------------------------
    def _static_layer(self, geometry: ForestLayout, season: str) -> pygame.Surface:
        """Woodland backdrop + paper card, rebuilt only on relayout or a new season."""

        key = (tuple(geometry.card), season)
        if self._static is not None and self._static_key == key:
            return self._static
        surface = self._art.background(season).copy()
        card = geometry.card
        if self.kit is not None:
            body = self.kit.painter.body(BodyShape.PANEL, (card.width, card.height + 10), CARD_FILL, lip=10, contour_width=5, highlight=False)
            surface.blit(body, card.topleft)
        else:
            pygame.draw.rect(surface, CARD_FILL, card, border_radius=28)
            pygame.draw.rect(surface, INK, card, width=4, border_radius=28)
        self._static = surface
        self._static_key = key
        return surface

    def guide(self, value: int, size: tuple[int, int]) -> TraceGuide:
        """Numeral geometry fitted to a local box (computed once per numeral/size)."""

        key = (value, int(size[0]), int(size[1]))
        guide = self._guides.get(key)
        if guide is None:
            if len(self._guides) >= 16:
                self._guides.clear()
            guide = TraceGuide.fit(value, (0, 0, key[1], key[2]))
            self._guides[key] = guide
        return guide

    def start_dot(self, diameter: int) -> pygame.Surface:
        """Green "start here" dot with a cream ring (built once per size)."""

        diameter = max(12, int(diameter))
        cached = self._start_dot.get(diameter)
        if cached is not None:
            return cached
        if len(self._start_dot) > 6:
            self._start_dot.clear()
        s = 2
        big = pygame.Surface((diameter * s, diameter * s), pygame.SRCALPHA)
        r = diameter * s // 2
        pygame.draw.circle(big, INK, (r, r), r)
        pygame.draw.circle(big, CREAM, (r, r), int(r * 0.86))
        pygame.draw.circle(big, INK, (r, r), int(r * 0.66))
        pygame.draw.circle(big, LEAF, (r, r), int(r * 0.56))
        pygame.draw.circle(big, mix(LEAF, (255, 255, 255), 0.45), (int(r * 0.8), int(r * 0.8)), int(r * 0.16))
        surface = pygame.transform.smoothscale(big, (diameter, diameter))
        self._start_dot[diameter] = surface
        return surface

    def ring(self, diameter: int) -> pygame.Surface:
        """Sunshine counting ring drawn around the item being counted."""

        diameter = max(12, int(diameter))
        cached = self._rings.get(diameter)
        if cached is not None:
            return cached
        if len(self._rings) > 6:
            self._rings.clear()
        s = 2
        big = pygame.Surface((diameter * s, diameter * s), pygame.SRCALPHA)
        r = diameter * s // 2
        width = max(3 * s, diameter * s // 12)
        pygame.draw.circle(big, INK, (r, r), r, width + 2 * s)
        pygame.draw.circle(big, GLOW, (r, r), r - s, width)
        surface = pygame.transform.smoothscale(big, (diameter, diameter))
        self._rings[diameter] = surface
        return surface

    # -- frame --------------------------------------------------------------------
    def draw_scene(self, target: pygame.Surface, geometry: ForestLayout, state: SceneState, *, draw_controls) -> None:
        target.blit(self._static_layer(geometry, state.season), (0, 0))
        self._draw_path(target, geometry, state)
        step = state.step
        if step is not None:
            if step.kind is StepKind.MEET:
                self._draw_meet(target, geometry, state)
            elif step.is_find:
                self._draw_find(target, geometry, state)
            elif step.kind is StepKind.TRACE:
                self._draw_trace(target, geometry, state)
            elif step.kind is StepKind.SHOW:
                self._draw_show(target, geometry, state)
        elif state.finale is not None:
            self._draw_parade(target, geometry, state)
        self._draw_tito(target, state)
        self._draw_choice_glows(target, state)
        draw_controls(target, _control_offsets(state))
        self._draw_counting(target, state)
        self._draw_fx(target, geometry, state)

    def _draw_path(self, target: pygame.Surface, geometry: ForestLayout, state: SceneState) -> None:
        for index, item in enumerate(state.written):
            if state.flight is not None and index == len(state.written) - 1:
                continue  # still flying to its signpost
            slot = geometry.path_slot(state.path_count, index)
            glyph = self._art.glyphs.tile(item.value, (PATH_GLYPH + (30 if item.value >= 10 else 0), PATH_GLYPH), item.color)
            base_y = slot.bottom - 4
            friend = self._art.picture(item.creature, PATH_FRIEND) if item.value else None
            wide = 14 if item.value >= 10 else 0
            if friend is not None:
                target.blit(friend, friend.get_rect(midbottom=(slot.centerx + 38 + wide, base_y)))
            target.blit(glyph, glyph.get_rect(midbottom=(slot.centerx - 20 - wide, base_y)))

    def _frame_in(self, box: pygame.Rect, value: int, *, max_cell: int) -> FrameGeometry:
        return FrameGeometry.fit(frame_cells_for(value), box.size, max_cell=max_cell)

    def _blit_frame(self, target, box: pygame.Rect, item: NumeralItem, count: int, *, max_cell: int, lift: int = 0) -> tuple[pygame.Rect, FrameGeometry]:
        frame = self._frame_in(box, item.value, max_cell=max_cell)
        surface = self._art.quantity(item.creature, count, frame)
        rect = surface.get_rect(center=(box.centerx, box.centery + lift))
        target.blit(surface, rect)
        return rect, frame

    def _draw_meet(self, target: pygame.Surface, geometry: ForestLayout, state: SceneState) -> None:
        step = state.step
        assert step is not None
        item = step.numeral
        box = geometry.meet_numeral
        guide = self.guide(item.value, box.size)
        if state.speaking == "numeral" or state.hint_target == "numeral":
            glow = self._art.glow(int(min(box.width, box.height) * 1.15))
            target.blit(glow, glow.get_rect(center=box.center))
        target.blit(self._art.glyphs.solid(guide, box.size, item.color), box.topleft)
        revealed = min(item.value, state.meet_revealed)
        rect, frame = self._blit_frame(target, geometry.meet_frame, item, revealed, max_cell=74)
        if state.speaking is not None and state.speaking.startswith("item.") and revealed:
            center = frame.cell_center(revealed - 1)
            ring = self.ring(int(frame.cell * 1.02))
            target.blit(ring, ring.get_rect(center=(rect.left + center[0], rect.top + center[1])))

    def _draw_find(self, target: pygame.Surface, geometry: ForestLayout, state: SceneState) -> None:
        step = state.step
        assert step is not None
        sign = geometry.find_sign
        if state.speaking == "sign" or state.hint_target == "sign":
            glow = self._art.glow(int(min(sign.width, sign.height) * 1.5))
            target.blit(glow, glow.get_rect(center=sign.center))
        self._blit_frame(target, sign, step.numeral, step.numeral.value, max_cell=66)

    def _draw_show(self, target: pygame.Surface, geometry: ForestLayout, state: SceneState) -> None:
        step = state.step
        assert step is not None
        box = geometry.show_numeral
        height = min(box.height, int(box.width * (0.8 if step.numeral.value >= 10 else 1.5)))
        if state.speaking == "numeral" or state.hint_target == "numeral":
            glow = self._art.glow(int(height * 1.15))
            target.blit(glow, glow.get_rect(center=box.center))
        glyph = self._art.glyphs.tile(step.numeral.value, (box.width, height), step.numeral.color)
        target.blit(glyph, glyph.get_rect(center=box.center))

    def _draw_trace(self, target: pygame.Surface, geometry: ForestLayout, state: SceneState) -> None:
        view = state.trace
        step = state.step
        if view is None or step is None:
            return
        box = geometry.trace_box
        if state.bloom is not None or view.complete:
            self._draw_bloom(target, geometry, state, view)
            return
        # The goal: the friends who come out when the numeral is written.
        self._blit_frame(target, geometry.trace_frame, step.numeral, step.numeral.value, max_cell=50)
        target.blit(self._art.glyphs.hollow(view.guide, box.size), box.topleft)
        target.blit(view.ink.surface, box.topleft)
        stroke = view.guide.strokes[view.stroke_index] if view.stroke_index < len(view.guide.strokes) else None
        if stroke is not None:
            self._draw_stroke_cue(target, box, view, stroke, state.pulse_phase)
        if view.demo_point is not None:
            hand = self._art.hud("drag_hint", HAND_SIZE)
            if hand is not None:
                x = box.left + view.demo_point[0] - HAND_SIZE * HAND_TIP[0]
                y = box.top + view.demo_point[1] - HAND_SIZE * HAND_TIP[1]
                target.blit(hand, (int(x), int(y)))

    def _draw_stroke_cue(self, target, box: pygame.Rect, view: TraceView, stroke, pulse_phase: int) -> None:
        """Green dot where the ink ends plus an arrow just ahead, along the stroke."""

        band = view.guide.band
        head = view.head if view.head is not None else stroke.start
        ahead = view.progress + band * 1.45
        if ahead < stroke.length - band * 0.4:
            ax, ay = stroke.point_at(ahead)
            dx, dy = stroke.direction_at(ahead - band * 0.3)
            nx, ny = -dy, dx
            length, wing = band * 0.42, band * 0.3
            cx, cy = box.left + ax, box.top + ay
            points = [
                (cx + dx * length, cy + dy * length),
                (cx - dx * length * 0.6 + nx * wing, cy - dy * length * 0.6 + ny * wing),
                (cx - dx * length * 0.6 - nx * wing, cy - dy * length * 0.6 - ny * wing),
            ]
            polygon = [(int(round(x)), int(round(y))) for x, y in points]
            pygame.draw.polygon(target, LEAF, polygon)
            pygame.draw.polygon(target, INK, polygon, max(2, int(band * 0.07)))
        big = view.start_pulse and pulse_phase % 2 == 0
        dot = self.start_dot(int(band * (1.05 if big else 0.86)))
        target.blit(dot, dot.get_rect(center=(int(box.left + head[0]), int(box.top + head[1]))))

    def _draw_bloom(self, target, geometry: ForestLayout, state: SceneState, view: TraceView) -> None:
        step = state.step
        assert step is not None
        box = geometry.trace_box
        t = 1.0 if state.bloom is None else max(0.0, min(1.0, state.bloom / BLOOM_SECONDS))
        if state.flight is None:
            glow = self._art.glow(int(min(box.width, box.height) * (0.9 + 0.3 * t)))
            target.blit(glow, glow.get_rect(center=box.center))
            target.blit(self._art.glyphs.solid(view.guide, box.size, step.numeral.color), box.topleft)
        # The frame pops (three cached lifts, never a per-frame scale).
        lift = -14 if 0.35 <= t < 0.7 else 0
        self._blit_frame(target, geometry.trace_frame, step.numeral, step.numeral.value, max_cell=50, lift=lift)

    def _draw_parade(self, target: pygame.Surface, geometry: ForestLayout, state: SceneState) -> None:
        """Finale: the walk's numerals side by side, each above its friends."""

        card = geometry.card.inflate(-40, -36)
        count = len(state.written)
        if not count:
            return
        width = card.width // count
        glyph_h = min(170, int(card.height * 0.5))
        for index, item in enumerate(state.written):
            cx = card.left + width * index + width // 2
            glyph_w = int(glyph_h * (1.3 if item.value >= 10 else 0.8))
            glyph = self._art.glyphs.tile(item.value, (glyph_w, glyph_h), item.color)
            target.blit(glyph, glyph.get_rect(midtop=(cx, card.top)))
            box = pygame.Rect(0, 0, width - 30, card.height - glyph_h - 12)
            box.midbottom = (cx, card.bottom)
            self._blit_frame(target, box, item, item.value, max_cell=56)

    def _draw_tito(self, target: pygame.Surface, state: SceneState) -> None:
        cast = self.cast
        if state.tito_pointing and self._point is not None and (cast is None or not cast.animating):
            target.blit(self._art.art.presentable(self._point, target), self._point.get_rect(midbottom=TITO_MIDBOTTOM))
            return
        if cast is not None:
            cast.draw(target, TITO_MIDBOTTOM)

    def _option_rect(self, state: SceneState, index: int) -> pygame.Rect | None:
        step = state.step
        if step is None or not step.is_choice or self.controls is None or index >= len(step.choices):
            return None
        return self.controls.option_rect(step, index)

    def _draw_choice_glows(self, target: pygame.Surface, state: SceneState) -> None:
        step = state.step
        if step is None or not step.is_choice:
            return
        for index in range(len(step.choices)):
            tag = f"choice.{index}"
            speaking = state.speaking == tag
            hinted = state.hint_target == tag
            celebrating = state.celebrating_choice == index
            if not (speaking or hinted or celebrating):
                continue
            rect = self._option_rect(state, index)
            if rect is None:
                continue
            big = speaking or celebrating or state.pulse_phase % 2 == 0
            rect = rect.move(0, -SPEAKING_LIFT if speaking else 0)
            glow = self._art.glow(int(max(rect.width, rect.height) * (1.5 if big else 1.3)))
            target.blit(glow, glow.get_rect(center=rect.center))

    def _draw_counting(self, target: pygame.Surface, state: SceneState) -> None:
        """Ring the friend being counted aloud on a SHOW frame."""

        step = state.step
        if state.counting is None or step is None or step.kind is not StepKind.SHOW or self.controls is None:
            return
        index, item = state.counting
        rect = self._option_rect(state, index)
        if rect is None or item < 1:
            return
        frame = self.controls.show_frame(step, index)
        face = self.controls.choices[index]
        width, height = frame.size
        # Kit tiles centre their icon on the face (above the lip).
        face_rect = face.rect
        left = face_rect.centerx - width // 2
        top = face_rect.top + (face_rect.height - face.lip) // 2 - height // 2
        center = frame.cell_center(item - 1)
        ring = self.ring(int(frame.cell * 1.05))
        target.blit(ring, ring.get_rect(center=(left + center[0], top + center[1])))

    def _draw_fx(self, target: pygame.Surface, geometry: ForestLayout, state: SceneState) -> None:
        if state.sparkle_at is not None:
            (x, y), t = state.sparkle_at
            sparkle = self._art.fx("fx.sparkle", _bucket(int(120 * (0.9 + 0.6 * min(1.0, t)))))
            if sparkle is not None:
                target.blit(sparkle, sparkle.get_rect(center=(x, y - int(16 * t))))
        if state.bloom is not None and state.flight is None:
            t = max(0.0, min(1.0, state.bloom / BLOOM_SECONDS))
            if t < 0.95:
                spot = geometry.trace_frame
                burst = self._art.fx("fx.star_burst", _bucket(int(min(spot.width, spot.height) * (0.6 + 0.6 * t))))
                if burst is not None:
                    target.blit(burst, burst.get_rect(center=spot.center))
                sparkle = self._art.fx("fx.sparkle", _bucket(int(geometry.trace_box.height * (0.5 + 0.4 * t))))
                if sparkle is not None:
                    target.blit(sparkle, sparkle.get_rect(center=geometry.trace_box.center))
        if state.flight is not None:
            item, start, end, t = state.flight
            t = max(0.0, min(1.0, t))
            ease = 1 - (1 - t) ** 2
            control = ((start[0] + end[0]) / 2, min(start[1], end[1]) - 90)
            x = (1 - ease) ** 2 * start[0] + 2 * (1 - ease) * ease * control[0] + ease ** 2 * end[0]
            y = (1 - ease) ** 2 * start[1] + 2 * (1 - ease) * ease * control[1] + ease ** 2 * end[1]
            glyph = self._art.glyphs.tile(item.value, (FLIGHT_GLYPH + (36 if item.value >= 10 else 0), FLIGHT_GLYPH), item.color)
            target.blit(glyph, glyph.get_rect(center=(int(x), int(y))))
        if state.finale is not None:
            self._draw_finale(target, state.finale)

    def _draw_finale(self, target: pygame.Surface, elapsed: float) -> None:
        spots = ((420, 170, 0.0), (820, 140, 0.3), (620, 110, 0.6), (900, 300, 0.9), (380, 320, 1.15))
        for x, y, delay in spots:
            local = elapsed - delay
            if 0 <= local < 0.9:
                image = self._art.fx("fx.confetti" if int(delay * 10) % 2 == 0 else "fx.leaf_drift", 168)
                if image is not None:
                    target.blit(image, image.get_rect(center=(x, y - int(30 * local))))


def _control_offsets(state: SceneState) -> dict[str, tuple[int, int]]:
    """Per-control draw offsets: the spoken option lifts, a wrong pick shakes."""

    offsets: dict[str, tuple[int, int]] = {}
    if state.speaking is not None and state.speaking.startswith("choice."):
        offsets[state.speaking] = (0, -SPEAKING_LIFT)
    if state.shake is not None:
        control_id, dx = state.shake
        offsets[control_id] = (dx, 0)
    return offsets


def _bucket(size: int) -> int:
    """Quantise animated FX sizes so only a few scaled copies are ever cached."""

    return max(16, int(math.ceil(size / 24.0) * 24))


__all__ = ["BoscoRenderer", "SceneState", "TraceView"]

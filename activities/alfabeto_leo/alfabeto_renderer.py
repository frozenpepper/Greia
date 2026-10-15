"""Letter-garden scene presentation for L'Alfabeto di Leo.

Draw order: cached meadow + paper card (static layer) → garden beds with the
letters planted this round → the step on the card (meet: big letter + its
picture; find: the picture sign; trace: hollow letter, the child's ink, the
start dot and the demonstrating hand; bloom: the coloured letter and its
picture popping out) → Leo → speaking/hint glows → kit controls → FX.

All images come pre-scaled from ``AlfabetoArt``; per frame there are only
blits, a few integer offsets and two tiny vector marks (start dot ring and
direction arrow) on the tracing guide. No text is rendered: letters are
stroke-font art, prompts are spoken.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Final, Sequence

import pygame

from greia_platform.activity_controls import BodyShape, ControlKit, mix

if __package__:
    from .alfabeto_art import CREAM, INK, AlfabetoArt, TraceInk
    from .alfabeto_controls import LEO_HEIGHT, LEO_MIDBOTTOM, GardenLayout
    from .alfabeto_model import GardenStep, LetterItem, StepKind
    from .alfabeto_trace import TraceGuide
else:
    from alfabeto_art import CREAM, INK, AlfabetoArt, TraceInk
    from alfabeto_controls import LEO_HEIGHT, LEO_MIDBOTTOM, GardenLayout
    from alfabeto_model import GardenStep, LetterItem, StepKind
    from alfabeto_trace import TraceGuide


CARD_FILL: Final = (255, 248, 228)
LEAF: Final = (89, 184, 106)
GARDEN_FLOWER: Final = 74
GARDEN_GLYPH: Final = 70
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

    step: GardenStep | None
    picture: str
    planted: Sequence[LetterItem] = ()
    garden_count: int = 3
    speaking: str | None = None
    hint_target: str | None = None
    pulse_phase: int = 0
    shake: tuple[str, int] | None = None
    leo_pointing: bool = False
    trace: TraceView | None = None
    bloom: float | None = None
    flight: tuple[LetterItem, tuple[int, int], tuple[int, int], float] | None = None
    sparkle_at: tuple[tuple[int, int], float] | None = None
    finale: float | None = None
    celebrating_choice: int | None = None
    # Finale recap: each planted letter with its example picture.
    bouquet: Sequence[tuple[LetterItem, str]] = ()


class AlfabetoRenderer:
    """Render the letter garden; geometry comes from ``GardenLayout``."""

    def __init__(self, art: AlfabetoArt) -> None:
        self._art = art
        self.cast = None  # CastFeedback, injected by the app (shares the kit art cache)
        self.kit: ControlKit | None = None
        self._static: pygame.Surface | None = None
        self._static_key: tuple | None = None
        self._point = art.cast_pose("leo", "pose_point", LEO_HEIGHT)
        self._start_dot: dict[int, pygame.Surface] = {}
        self._guides: dict[tuple[str, int, int], TraceGuide] = {}

    @property
    def art(self) -> AlfabetoArt:
        return self._art

    # -- caches -------------------------------------------------------------------
    def _static_layer(self, geometry: GardenLayout) -> pygame.Surface:
        """Meadow backdrop + paper card, rebuilt only on relayout."""

        key = (tuple(geometry.card),)
        if self._static is not None and self._static_key == key:
            return self._static
        surface = self._art.background.copy()
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

    def guide(self, char: str, size: tuple[int, int]) -> TraceGuide:
        """Letter geometry fitted to a local box (computed once per letter/size)."""

        key = (char, int(size[0]), int(size[1]))
        guide = self._guides.get(key)
        if guide is None:
            if len(self._guides) >= 12:
                self._guides.clear()
            guide = TraceGuide.fit(char, (0, 0, key[1], key[2]))
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

    # -- frame --------------------------------------------------------------------
    def draw_scene(self, target: pygame.Surface, geometry: GardenLayout, state: SceneState, *, draw_controls) -> None:
        target.blit(self._static_layer(geometry), (0, 0))
        self._draw_garden(target, geometry, state)
        step = state.step
        if step is not None:
            if step.kind is StepKind.MEET:
                self._draw_meet(target, geometry, state)
            elif step.is_find:
                self._draw_find(target, geometry, state)
            elif step.kind is StepKind.TRACE:
                self._draw_trace(target, geometry, state)
        elif state.bouquet:
            self._draw_bouquet(target, geometry, state)
        self._draw_leo(target, state)
        self._draw_choice_glows(target, geometry, state)
        draw_controls(target, _control_offsets(state))
        self._draw_fx(target, geometry, state)

    def _draw_garden(self, target: pygame.Surface, geometry: GardenLayout, state: SceneState) -> None:
        flower = self._art.picture("prop.nature.flower", GARDEN_FLOWER)
        for index, item in enumerate(state.planted):
            if state.flight is not None and index == len(state.planted) - 1:
                continue  # still flying into its bed
            slot = geometry.garden_slot(state.garden_count, index)
            glyph = self._art.glyphs.tile(item.char, GARDEN_GLYPH, item.color)
            base_y = slot.bottom - 4
            if flower is not None:
                target.blit(flower, flower.get_rect(midbottom=(slot.centerx + 34, base_y)))
            target.blit(glyph, glyph.get_rect(midbottom=(slot.centerx - 22, base_y)))

    def _draw_meet(self, target: pygame.Surface, geometry: GardenLayout, state: SceneState) -> None:
        step = state.step
        assert step is not None
        box = geometry.meet_letter
        picture = self._art.picture(state.picture, geometry.meet_picture.width)
        if picture is None:  # staged words without art: the letter alone, centred
            box = geometry.card.inflate(-60, -50)
        guide = self.guide(step.letter.char, box.size)
        if state.speaking == "letter" or state.hint_target == "letter":
            glow = self._art.glow(int(min(box.width, box.height) * 1.1))
            target.blit(glow, glow.get_rect(center=box.center))
        letter = self._art.glyphs.solid(guide, box.size, step.letter.color)
        target.blit(letter, box.topleft)
        if picture is not None:
            lift = -6 if state.speaking == "letter" else 0
            target.blit(picture, picture.get_rect(center=geometry.meet_picture.move(0, lift).center))

    def _draw_find(self, target: pygame.Surface, geometry: GardenLayout, state: SceneState) -> None:
        picture = self._art.picture(state.picture, geometry.find_picture.width)
        if picture is not None:
            target.blit(picture, geometry.find_picture.topleft)

    def _draw_trace(self, target: pygame.Surface, geometry: GardenLayout, state: SceneState) -> None:
        view = state.trace
        step = state.step
        if view is None or step is None:
            return
        box = geometry.trace_box
        if state.bloom is not None or view.complete:
            self._draw_bloom(target, geometry, state, view)
            return
        picture = self._art.picture(state.picture, geometry.trace_picture.width)
        if picture is not None:
            faded = picture  # the goal: the picture that blooms when the letter is done
            target.blit(faded, faded.get_rect(center=geometry.trace_picture.center))
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

    def _draw_bloom(self, target, geometry: GardenLayout, state: SceneState, view: TraceView) -> None:
        step = state.step
        assert step is not None
        box = geometry.trace_box
        t = 1.0 if state.bloom is None else max(0.0, min(1.0, state.bloom / BLOOM_SECONDS))
        if state.flight is None:
            glow = self._art.glow(int(min(box.width, box.height) * (0.9 + 0.3 * t)))
            target.blit(glow, glow.get_rect(center=box.center))
            target.blit(self._art.glyphs.solid(view.guide, box.size, step.letter.color), box.topleft)
        picture_rect = geometry.trace_picture
        # Pop: three cached sizes (small → over-size → settle), never a per-frame scale.
        if t < 0.35:
            scale = 0.7
        elif t < 0.7:
            scale = 1.15
        else:
            scale = 1.0
        size = int(picture_rect.width * scale)
        picture = self._art.picture(state.picture, size)
        if picture is not None:
            target.blit(picture, picture.get_rect(center=picture_rect.center))

    def _draw_bouquet(self, target: pygame.Surface, geometry: GardenLayout, state: SceneState) -> None:
        """Finale: the round's letters side by side, each above its picture."""

        card = geometry.card.inflate(-40, -36)
        count = len(state.bouquet)
        width = card.width // max(1, count)
        letter_size = min(176, width - 24, int(card.height * 0.52))
        picture_size = min(128, int(card.height * 0.36))
        for index, (item, picture_id) in enumerate(state.bouquet):
            cx = card.left + width * index + width // 2
            glyph = self._art.glyphs.tile(item.char, letter_size, item.color)
            target.blit(glyph, glyph.get_rect(midtop=(cx, card.top)))
            picture = self._art.picture(picture_id, picture_size)
            if picture is not None:
                target.blit(picture, picture.get_rect(midbottom=(cx, card.bottom)))

    def _draw_leo(self, target: pygame.Surface, state: SceneState) -> None:
        cast = self.cast
        if state.leo_pointing and self._point is not None and (cast is None or not cast.animating):
            target.blit(self._point, self._point.get_rect(midbottom=LEO_MIDBOTTOM))
            return
        if cast is not None:
            cast.draw(target, LEO_MIDBOTTOM)

    def _draw_choice_glows(self, target: pygame.Surface, geometry: GardenLayout, state: SceneState) -> None:
        step = state.step
        if step is None or not step.is_find:
            return
        count = len(step.choices)
        for index in range(count):
            tag = f"choice.{index}"
            speaking = state.speaking == tag
            hinted = state.hint_target == tag
            celebrating = state.celebrating_choice == index
            if not (speaking or hinted or celebrating):
                continue
            big = speaking or celebrating or state.pulse_phase % 2 == 0
            rect = geometry.choice_rect(count, index).move(0, -SPEAKING_LIFT if speaking else 0)
            glow = self._art.glow(int(rect.width * (1.6 if big else 1.38)))
            target.blit(glow, glow.get_rect(center=rect.center))

    def _draw_fx(self, target: pygame.Surface, geometry: GardenLayout, state: SceneState) -> None:
        if state.sparkle_at is not None:
            (x, y), t = state.sparkle_at
            sparkle = self._art.fx("fx.sparkle", _bucket(int(120 * (0.9 + 0.6 * min(1.0, t)))))
            if sparkle is not None:
                target.blit(sparkle, sparkle.get_rect(center=(x, y - int(16 * t))))
        if state.bloom is not None and state.flight is None:
            # The letter "blooms into" its picture: a bloom burst on the picture,
            # sparkles over the finished letter.
            t = max(0.0, min(1.0, state.bloom / BLOOM_SECONDS))
            if t < 0.95:
                spot = geometry.trace_picture
                bloom = self._art.fx("fx.bloom", _bucket(int(spot.width * (0.7 + 0.8 * t))))
                if bloom is not None:
                    target.blit(bloom, bloom.get_rect(center=spot.center))
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
            glyph = self._art.glyphs.tile(item.char, FLIGHT_GLYPH, item.color)
            target.blit(glyph, glyph.get_rect(center=(int(x), int(y))))
        if state.finale is not None:
            self._draw_finale(target, geometry, state.finale)

    def _draw_finale(self, target: pygame.Surface, geometry: GardenLayout, elapsed: float) -> None:
        spots = ((420, 170, 0.0), (820, 140, 0.3), (620, 110, 0.6), (900, 300, 0.9), (380, 320, 1.15))
        for x, y, delay in spots:
            local = elapsed - delay
            if 0 <= local < 0.9:
                image = self._art.fx("fx.confetti" if int(delay * 10) % 2 == 0 else "fx.star_burst", 168)
                if image is not None:
                    target.blit(image, image.get_rect(center=(x, y - int(30 * local))))


def _control_offsets(state: SceneState) -> dict[str, tuple[int, int]]:
    """Per-control draw offsets: the spoken tile lifts, a wrong pick shakes."""

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


__all__ = ["AlfabetoRenderer", "SceneState", "TraceView"]

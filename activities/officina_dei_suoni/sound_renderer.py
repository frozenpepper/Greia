"""Workshop scene presentation for Officina dei Suoni.

Draw order: cached workshop room → gears (pre-rotated frames) → Sound Machine
→ machine screen (listening ear, or the word's picture) → letter slots →
horn notes while a sound plays → Dani → speaking/hint glows → kit controls →
FX (sparkle, flight into the hopper or a slot, check pop, finale confetti).

All surfaces are pre-scaled through ``SoundWorkshopArt``; per-frame work is
blits and a few integer offsets. Nothing here renders UI text: the game is
pictorial and spoken, and the only letters drawn are the taught capitals.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Final, Sequence

import pygame

if __package__:
    from .sound_art import INK, SoundWorkshopArt
    from .sound_content import WordItem, WorkshopMode
    from .sound_controls import DANI_HEIGHT, DANI_MIDBOTTOM, PICTURE_SIZE, WorkshopLayout
    from .sound_workshop_model import WorkshopChallenge
else:
    from sound_art import INK, SoundWorkshopArt
    from sound_content import WordItem, WorkshopMode
    from sound_controls import DANI_HEIGHT, DANI_MIDBOTTOM, PICTURE_SIZE, WorkshopLayout
    from sound_workshop_model import WorkshopChallenge


SCREEN_PICTURE: Final = 112
SCREEN_EAR: Final = 96
SPEAKING_LIFT: Final = 10
CREAM: Final = (255, 251, 235)
SAND: Final = (238, 221, 186)
SUNSHINE: Final = (255, 194, 52)
SLOT_EMPTY: Final = (248, 236, 214)


@dataclass(frozen=True, slots=True)
class Flight:
    """A picture or letter travelling from a tile into the machine."""

    item: WordItem | str
    start: tuple[int, int]
    end: tuple[int, int]
    t: float
    start_size: int
    end_size: int


@dataclass(frozen=True, slots=True)
class SceneState:
    """Everything the renderer needs for one frame (built by the app)."""

    challenge: WorkshopChallenge | None
    filled_slots: Sequence[int] = ()
    active_slot: int | None = None
    show_answer_picture: bool = False
    reveal_letter: bool = False
    speaking: str | None = None
    hint_target: str | None = None
    pulse_phase: int = 0
    shake: tuple[str, int] | None = None
    sparkle_at: tuple[tuple[int, int], float] | None = None
    flight: Flight | None = None
    pop_at: tuple[tuple[int, int], float] | None = None
    gear_frame: int = 0
    confetti: float | None = None
    dani_pointing: bool = False


class SoundWorkshopRenderer:
    """Render the workshop; geometry comes from ``WorkshopLayout``."""

    def __init__(self, art: SoundWorkshopArt) -> None:
        self._art = art
        self.cast = None  # CastFeedback, injected by the app (shares the kit art cache)
        self._point = art.cast_pose("dani", "pose_point", DANI_HEIGHT)
        self._boxes: dict[tuple[int, str], pygame.Surface] = {}

    @property
    def art(self) -> SoundWorkshopArt:
        return self._art

    # -- frame ----------------------------------------------------------------------
    def draw_scene(
        self,
        target: pygame.Surface,
        geometry: WorkshopLayout,
        state: SceneState,
        *,
        draw_controls,
    ) -> None:
        target.blit(self._art.room, (0, 0))
        self._draw_machine(target, geometry, state)
        self._draw_screen(target, geometry, state)
        self._draw_slots(target, geometry, state)
        self._draw_horn(target, geometry, state)
        self._draw_dani(target, state)
        self._draw_choice_glows(target, state)
        draw_controls(target, _control_offsets(state))
        self._draw_fx(target, geometry, state)

    # -- machine -----------------------------------------------------------------------
    def _draw_machine(self, target: pygame.Surface, geometry: WorkshopLayout, state: SceneState) -> None:
        for index, (x, y, size) in enumerate(geometry.gears):
            frames = self._art.gear_frames(size)
            if frames:
                # The small gear turns the other way, as meshed gears do.
                frame = frames[(state.gear_frame if index == 0 else -state.gear_frame) % len(frames)]
                target.blit(frame, frame.get_rect(center=(x, y)))
        machine = self._art.machine(geometry.machine.size)
        if machine is not None:
            target.blit(machine, geometry.machine.topleft)

    def _draw_screen(self, target: pygame.Surface, geometry: WorkshopLayout, state: SceneState) -> None:
        challenge = state.challenge
        if challenge is None:
            return
        center = geometry.screen.center
        speaking = state.speaking in {"screen", "word"} or (
            state.hint_target == "machine" and state.pulse_phase % 2 == 0
        )
        if speaking:
            glow = self._art.glow(int(SCREEN_PICTURE * 1.45))
            target.blit(glow, glow.get_rect(center=center))
        if challenge.mode is WorkshopMode.FIND_SOUND and not state.show_answer_picture:
            ear = self._art.hud("ear", SCREEN_EAR)
            if ear is not None:
                lift = -4 if state.speaking == "horn" else 0
                target.blit(ear, ear.get_rect(center=(center[0], center[1] + lift)))
            return
        picture = self._art.picture(challenge.answer_word, SCREEN_PICTURE)
        if picture is not None:
            lift = -4 if speaking else 0
            target.blit(picture, picture.get_rect(center=(center[0], center[1] + lift)))

    def _draw_slots(self, target: pygame.Surface, geometry: WorkshopLayout, state: SceneState) -> None:
        challenge = state.challenge
        if challenge is None:
            return
        if state.pop_at is not None:
            # A star burst behind the box the letter just landed in.
            center, t = state.pop_at
            burst = self._art.fx("fx.star_burst", _bucket(int(72 + 64 * min(1.0, t))))
            if burst is not None:
                target.blit(burst, burst.get_rect(center=center))
        if challenge.mode is WorkshopMode.BUILD_WORD:
            assert challenge.target_word is not None
            label = challenge.target_word.label
            rects = geometry.slot_rects(len(label))
            slot_positions = set(challenge.slots)
            for position, rect in enumerate(rects):
                if position not in slot_positions:
                    self._blit_box(target, rect, "given")
                    glyph = self._art.plain_letter(label[position], _letter_size(rect))
                    target.blit(glyph, glyph.get_rect(center=rect.center))
                else:
                    self._draw_slot(target, rect, label[position], position, state)
            if state.speaking == "word":
                span = rects[0].unionall(rects[1:]) if len(rects) > 1 else rects[0]
                pygame.draw.rect(target, SUNSHINE, span.inflate(10, 10), width=4, border_radius=12)
            return
        rect = geometry.slot_rects(1)[0]
        letter = challenge.target_unit.grapheme_upper
        if challenge.mode is WorkshopMode.FIND_SOUND:
            if state.reveal_letter:
                self._blit_box(target, rect, "filled")
                glyph = self._art.letter(letter, _letter_size(rect), done=True)
                target.blit(glyph, glyph.get_rect(center=rect.center))
            else:
                self._blit_box(target, rect, "sleep")
            return
        self._draw_slot(target, rect, letter, 0, state)

    def _draw_slot(self, target: pygame.Surface, rect: pygame.Rect, letter: str, position: int, state: SceneState) -> None:
        if position in state.filled_slots:
            self._blit_box(target, rect, "filled")
            glyph = self._art.letter(letter, _letter_size(rect), done=True)
            target.blit(glyph, glyph.get_rect(center=rect.center))
            if state.speaking == f"slot.{position}":
                pygame.draw.rect(target, SUNSHINE, rect.inflate(8, 8), width=4, border_radius=12)
            return
        if position == state.active_slot:
            if state.pulse_phase % 2 == 0:
                glow = self._art.glow(int(rect.width * 1.9))
                target.blit(glow, glow.get_rect(center=rect.center))
            self._blit_box(target, rect, "active")
        else:
            self._blit_box(target, rect, "empty")

    def _blit_box(self, target: pygame.Surface, rect: pygame.Rect, kind: str) -> None:
        key = (rect.width, kind)
        surface = self._boxes.get(key)
        if surface is None:
            if len(self._boxes) >= 16:
                self._boxes.clear()
            surface = _box_surface(rect.width, kind)
            self._boxes[key] = surface
        target.blit(surface, rect.topleft)

    def _draw_horn(self, target: pygame.Surface, geometry: WorkshopLayout, state: SceneState) -> None:
        if state.speaking != "horn" and not (state.hint_target == "horn" and state.pulse_phase % 2 == 0):
            return
        hx, hy = geometry.horn
        glow = self._art.glow(120)
        target.blit(glow, glow.get_rect(center=(hx + 6, hy - 4)))
        notes = self._art.fx("fx.note_burst", 96)
        if notes is not None:
            lift = 6 if state.pulse_phase % 2 else 0
            target.blit(notes, notes.get_rect(center=(hx + 36, hy - 28 - lift)))

    # -- cast / glows -----------------------------------------------------------------------
    def _draw_dani(self, target: pygame.Surface, state: SceneState) -> None:
        cast = self.cast
        if state.dani_pointing and self._point is not None and (cast is None or not cast.animating):
            target.blit(self._point, self._point.get_rect(midbottom=DANI_MIDBOTTOM))
            return
        if cast is not None:
            cast.draw(target, DANI_MIDBOTTOM)

    def _draw_choice_glows(self, target: pygame.Surface, state: SceneState) -> None:
        for index in range(3):
            tag = f"choice.{index}"
            speaking = state.speaking == tag
            hinted = state.hint_target == tag
            if not speaking and not hinted:
                continue
            big = speaking or state.pulse_phase % 2 == 0
            rect = WorkshopLayout.choice_rect(3, index).move(0, -SPEAKING_LIFT if speaking else 0)
            glow = self._art.glow(int(rect.width * (1.6 if big else 1.38)))
            target.blit(glow, glow.get_rect(center=rect.center))

    # -- fx ---------------------------------------------------------------------------------
    def _draw_fx(self, target: pygame.Surface, geometry: WorkshopLayout, state: SceneState) -> None:
        if state.sparkle_at is not None:
            (x, y), t = state.sparkle_at
            size = int(PICTURE_SIZE * (0.9 + 0.5 * min(1.0, t)))
            sparkle = self._art.fx("fx.sparkle", _bucket(size))
            if sparkle is not None:
                target.blit(sparkle, sparkle.get_rect(center=(x, y - int(18 * t))))
        if state.flight is not None:
            self._draw_flight(target, state.flight)
        if state.confetti is not None:
            self._draw_confetti(target, state.confetti)

    def _draw_flight(self, target: pygame.Surface, flight: Flight) -> None:
        t = max(0.0, min(1.0, flight.t))
        ease = 1 - (1 - t) ** 2
        (sx, sy), (ex, ey) = flight.start, flight.end
        control = ((sx + ex) / 2, min(sy, ey) - 110)
        x = (1 - ease) ** 2 * sx + 2 * (1 - ease) * ease * control[0] + ease ** 2 * ex
        y = (1 - ease) ** 2 * sy + 2 * (1 - ease) * ease * control[1] + ease ** 2 * ey
        size = _bucket(int(flight.start_size + (flight.end_size - flight.start_size) * ease))
        if isinstance(flight.item, WordItem):
            image = self._art.picture(flight.item, size)
        else:
            image = self._art.letter(flight.item, size, done=True)
        if image is not None:
            target.blit(image, image.get_rect(center=(int(x), int(y))))

    def _draw_confetti(self, target: pygame.Surface, elapsed: float) -> None:
        spots = ((300, 150, 0.0), (820, 130, 0.3), (566, 90, 0.6), (900, 300, 0.9), (240, 300, 1.2))
        for x, y, delay in spots:
            local = elapsed - delay
            if local < 0 or local >= 1.1:
                continue
            image = self._art.fx("fx.confetti", 168)
            if image is not None:
                target.blit(image, image.get_rect(center=(x, y + int(30 * local))))


def _box_surface(size: int, kind: str) -> pygame.Surface:
    """One letter box (given / empty / active / filled / sleep), built once per size."""

    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    rect = surface.get_rect()
    radius = max(6, size // 4)
    fill = {"given": SAND, "empty": SLOT_EMPTY, "active": CREAM, "filled": CREAM, "sleep": SLOT_EMPTY}[kind]
    border = SUNSHINE if kind == "active" else INK
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    width = 4 if kind in {"active", "filled"} else 3
    pygame.draw.rect(surface, border, rect, width=width, border_radius=radius)
    if kind == "active":
        pygame.draw.rect(surface, INK, rect.inflate(-2 * width, -2 * width), width=2, border_radius=max(4, radius - width))
    return surface


def _letter_size(rect: pygame.Rect) -> int:
    return max(12, int(rect.height * 0.74))


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
    """Quantise animated sizes so only a few scaled copies are ever cached."""

    return max(16, int(math.ceil(size / 24.0) * 24))


__all__ = ["SoundWorkshopRenderer", "SceneState", "Flight"]

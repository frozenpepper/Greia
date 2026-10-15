"""Scene presentation for Leo's Syllable Train.

Draw order: cached meadow + track → station board (word picture, or the
listening ear on the beats train) → train (wagons with their beats/syllables,
locomotive, pre-rotated wheels) → Leo → speaking/hint glows → kit controls →
FX (sparkle, tile flight, landing burst, beat rings, finale confetti).

All surfaces are pre-scaled through ``SillabeArt``; per-frame work is blits and
a few integer offsets. Nothing here renders UI text: the game is pictorial and
spoken, and the only letters drawn are the taught syllables.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Final

import pygame

if __package__:
    from .sillabe_art import INK, SillabeArt
    from .sillabe_content import ReadingMethod, TrainWord
    from .sillabe_controls import (
        LEO_HEIGHT,
        LEO_MIDBOTTOM,
        LOCO_WHEEL_X,
        PICTURE_SIZE,
        WAGON_FACE,
        WAGON_WHEEL_X,
        WHEEL_CENTER_Y,
        WHEEL_SIZE,
        TrainLayout,
    )
    from .sillabe_model import ChoiceStep, StepKind, TrainChallenge
else:
    from sillabe_art import INK, SillabeArt
    from sillabe_content import ReadingMethod, TrainWord
    from sillabe_controls import (
        LEO_HEIGHT,
        LEO_MIDBOTTOM,
        LOCO_WHEEL_X,
        PICTURE_SIZE,
        WAGON_FACE,
        WAGON_WHEEL_X,
        WHEEL_CENTER_Y,
        WHEEL_SIZE,
        TrainLayout,
    )
    from sillabe_model import ChoiceStep, StepKind, TrainChallenge


SIGN_PICTURE: Final = 100
SIGN_EAR: Final = 78
WAGON_TEXT: Final = 54
SPEAKING_LIFT: Final = 10
CREAM: Final = (255, 251, 235)
SUNSHINE: Final = (255, 194, 52)
SLOT_EMPTY: Final = (248, 236, 214)


@dataclass(frozen=True, slots=True)
class Flight:
    """A tile (syllable/vowel) or picture travelling to a wagon or the board."""

    item: TrainWord | str
    start: tuple[int, int]
    end: tuple[int, int]
    t: float
    start_size: int
    end_size: int


@dataclass(frozen=True, slots=True)
class SceneState:
    """Everything the renderer needs for one frame (built by the app)."""

    challenge: TrainChallenge | None
    step: ChoiceStep | None = None
    built: tuple[int, ...] = ()
    claps: int = 0
    active_wagon: int | None = None
    train_offset: int = 0
    wheel_frame: int = 0
    sign_picture: bool = True
    speaking: str | None = None
    hint_target: str | None = None
    pulse_phase: int = 0
    shake: tuple[str, int] | None = None
    sparkle_at: tuple[tuple[int, int], float] | None = None
    flight: Flight | None = None
    pop_at: tuple[tuple[int, int], float] | None = None
    beat_ring: tuple[int, float] | None = None
    confetti: float | None = None
    leo_pointing: bool = False


class SillabeRenderer:
    """Render the meadow station; geometry comes from ``TrainLayout``."""

    def __init__(self, art: SillabeArt) -> None:
        self._art = art
        self.cast = None  # CastFeedback, injected by the app (shares the kit art cache)
        self._point = art.cast_pose("leo", "pose_point", LEO_HEIGHT)
        self._vowel_boxes: dict[tuple[int, int, bool], pygame.Surface] = {}

    @property
    def art(self) -> SillabeArt:
        return self._art

    # -- frame ----------------------------------------------------------------------
    def draw_scene(self, target: pygame.Surface, geometry: TrainLayout, state: SceneState, *, draw_controls) -> None:
        target.blit(self._art.background, (0, 0))
        self._draw_sign(target, geometry, state)
        self._draw_train(target, state)
        self._draw_leo(target, state)
        self._draw_glows(target, geometry, state)
        draw_controls(target, _control_offsets(state))
        self._draw_fx(target, state)

    # -- station board --------------------------------------------------------------
    def _draw_sign(self, target: pygame.Surface, geometry: TrainLayout, state: SceneState) -> None:
        board = self._art.sign(geometry.sign.size)
        if board is not None:
            target.blit(board, geometry.sign.topleft)
        challenge = state.challenge
        if challenge is None:
            return
        center = geometry.sign_face.center
        speaking = state.speaking in {"sign", "train"} or (state.hint_target == "sign" and state.pulse_phase % 2 == 0)
        if speaking:
            glow = self._art.glow(int(SIGN_PICTURE * 1.5))
            target.blit(glow, glow.get_rect(center=center))
        lift = -4 if speaking else 0
        if state.sign_picture:
            picture = self._art.picture(challenge.word, SIGN_PICTURE)
            if picture is not None:
                target.blit(picture, picture.get_rect(center=(center[0], center[1] + lift)))
            return
        ear = self._art.hud("ear", SIGN_EAR)
        if ear is not None:
            target.blit(ear, ear.get_rect(center=(center[0], center[1] + lift)))

    # -- train ------------------------------------------------------------------------
    def _draw_train(self, target: pygame.Surface, state: SceneState) -> None:
        challenge = state.challenge
        if challenge is None:
            return
        wagons, loco = TrainLayout.train_rects(challenge.wagons, state.train_offset)
        frames = self._art.wheel_frames(WHEEL_SIZE)
        frame = frames[state.wheel_frame % len(frames)] if frames else None
        for index, rect in enumerate(wagons):
            if frame is not None:
                for wx in WAGON_WHEEL_X:
                    target.blit(frame, frame.get_rect(center=(rect.left + wx, WHEEL_CENTER_Y)))
            body = self._art.wagon(index, rect.size)
            if body is not None:
                target.blit(body, rect.topleft)
            self._draw_wagon_face(target, rect, index, challenge, state)
        if frame is not None:
            for wx in LOCO_WHEEL_X:
                target.blit(frame, frame.get_rect(center=(loco.left + wx, WHEEL_CENTER_Y)))
        body = self._art.locomotive(loco.size)
        if body is not None:
            target.blit(body, loco.topleft)
        speaking = state.speaking or ""
        if speaking.startswith("beat.") and int(speaking.split(".", 1)[1]) >= len(wagons):
            # A demonstrated beat with no wagon left for it: a puff behind the train.
            puff = self._art.fx("fx.dust_puff", 96)
            if puff is not None:
                target.blit(puff, puff.get_rect(midright=(wagons[0].left - 4, wagons[0].centery + 10)))

    def _draw_wagon_face(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        index: int,
        challenge: TrainChallenge,
        state: SceneState,
    ) -> None:
        face = WAGON_FACE.move(rect.topleft)
        tag = f"wagon.{index}"
        lit = state.speaking in {tag, f"beat.{index}", "train"}
        if lit:
            pygame.draw.rect(target, SUNSHINE, face.inflate(10, 10), width=5, border_radius=16)
        if challenge.method is ReadingMethod.BEATS:
            if index < state.claps:
                star = self._art.fx("fx.star_burst", 72 if lit else 60)
                if star is not None:
                    target.blit(star, star.get_rect(center=face.center))
            else:
                # One quiet beat ring per wagon: "this train wants N beats".
                ring = self._quiet_ring(56 if lit else 48)
                if ring is not None:
                    target.blit(ring, ring.get_rect(center=face.center))
            return
        if index in state.built:
            syllable = challenge.word.syllables[index]
            size = WAGON_TEXT if len(syllable) <= 2 else max(36, WAGON_TEXT - 8 * (len(syllable) - 2))
            glyph = self._art.wagon_text(syllable, size, index)
            target.blit(glyph, glyph.get_rect(center=(face.centerx, face.centery + (-3 if lit else 0))))
            return
        if index == state.active_wagon and state.step is not None:
            pulse = state.pulse_phase % 2 == 0
            if state.step.kind is StepKind.VOWEL:
                given = self._art.given_text(state.step.given, WAGON_TEXT)
                box = self._vowel_box(40, 50, pulse)
                total = given.get_width() + 6 + box.get_width()
                left = face.centerx - total // 2
                target.blit(given, given.get_rect(midleft=(left, face.centery)))
                target.blit(box, box.get_rect(midleft=(left + given.get_width() + 6, face.centery)))
                return
            box = self._vowel_box(face.width - 26, face.height - 16, pulse)
            target.blit(box, box.get_rect(center=face.center))
            return
        if index < state.claps:
            # A clapped (heard) beat waiting to be built.
            ring = self._art.fx("fx.beat_ring", 44)
            if ring is not None:
                target.blit(ring, ring.get_rect(center=face.center))

    def _quiet_ring(self, size: int) -> pygame.Surface | None:
        key = (size, -1, False)
        surface = self._vowel_boxes.get(key)
        if surface is None:
            ring = self._art.fx("fx.beat_ring", size)
            if ring is None:
                return None
            surface = ring.copy()
            surface.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
            self._vowel_boxes[key] = surface
        return surface

    def _vowel_box(self, width: int, height: int, pulse: bool) -> pygame.Surface:
        key = (int(width), int(height), pulse)
        surface = self._vowel_boxes.get(key)
        if surface is None:
            if len(self._vowel_boxes) >= 12:
                self._vowel_boxes.clear()
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            rect = surface.get_rect()
            pygame.draw.rect(surface, CREAM if pulse else SLOT_EMPTY, rect, border_radius=10)
            pygame.draw.rect(surface, SUNSHINE if pulse else INK, rect, width=4 if pulse else 3, border_radius=10)
            self._vowel_boxes[key] = surface
        return surface

    # -- cast / glows -----------------------------------------------------------------
    def _draw_leo(self, target: pygame.Surface, state: SceneState) -> None:
        cast = self.cast
        if state.leo_pointing and self._point is not None and (cast is None or not cast.animating):
            target.blit(self._point, self._point.get_rect(midbottom=LEO_MIDBOTTOM))
            return
        if cast is not None:
            cast.draw(target, LEO_MIDBOTTOM)

    def _draw_glows(self, target: pygame.Surface, geometry: TrainLayout, state: SceneState) -> None:
        targets: list[tuple[pygame.Rect, bool]] = []
        if state.speaking is not None and state.speaking.startswith("choice.") and state.step is not None:
            index = int(state.speaking.split(".", 1)[1])
            targets.append((TrainLayout.choice_rect(len(state.step.choices), index).move(0, -SPEAKING_LIFT), True))
        hint = state.hint_target
        if hint is not None and state.pulse_phase % 2 == 0:
            if hint.startswith("choice.") and state.step is not None:
                index = int(hint.split(".", 1)[1])
                targets.append((TrainLayout.choice_rect(len(state.step.choices), index), False))
            elif hint == "drum":
                targets.append((geometry.drum, False))
        if state.speaking == "drum":
            targets.append((geometry.drum, True))
        for rect, big in targets:
            glow = self._art.glow(int(rect.width * (1.6 if big else 1.42)))
            target.blit(glow, glow.get_rect(center=rect.center))

    # -- fx ------------------------------------------------------------------------------
    def _draw_fx(self, target: pygame.Surface, state: SceneState) -> None:
        if state.beat_ring is not None and state.challenge is not None:
            index, t = state.beat_ring
            wagons, _ = TrainLayout.train_rects(state.challenge.wagons, state.train_offset)
            if 0 <= index < len(wagons):
                ring = self._art.fx("fx.beat_ring", _bucket(int(70 + 90 * min(1.0, t))))
                if ring is not None:
                    target.blit(ring, ring.get_rect(center=WAGON_FACE.move(wagons[index].topleft).center))
        if state.pop_at is not None:
            center, t = state.pop_at
            burst = self._art.fx("fx.star_burst", _bucket(int(80 + 70 * min(1.0, t))))
            if burst is not None:
                target.blit(burst, burst.get_rect(center=center))
        if state.sparkle_at is not None:
            (x, y), t = state.sparkle_at
            sparkle = self._art.fx("fx.sparkle", _bucket(int(PICTURE_SIZE * (0.9 + 0.5 * min(1.0, t)))))
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
        control = ((sx + ex) / 2, min(sy, ey) - 90)
        x = (1 - ease) ** 2 * sx + 2 * (1 - ease) * ease * control[0] + ease ** 2 * ex
        y = (1 - ease) ** 2 * sy + 2 * (1 - ease) * ease * control[1] + ease ** 2 * ey
        size = _bucket(int(flight.start_size + (flight.end_size - flight.start_size) * ease))
        if isinstance(flight.item, TrainWord):
            image = self._art.picture(flight.item, size)
        else:
            image = self._art.tile_text(flight.item, size)
        if image is not None:
            target.blit(image, image.get_rect(center=(int(x), int(y))))

    def _draw_confetti(self, target: pygame.Surface, elapsed: float) -> None:
        spots = ((330, 150, 0.0), (840, 130, 0.3), (604, 96, 0.6), (900, 300, 0.9), (360, 300, 1.2))
        for x, y, delay in spots:
            local = elapsed - delay
            if local < 0 or local >= 1.1:
                continue
            image = self._art.fx("fx.confetti", 168)
            if image is not None:
                target.blit(image, image.get_rect(center=(x, y + int(30 * local))))


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


__all__ = ["Flight", "SceneState", "SillabeRenderer"]

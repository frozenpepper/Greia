"""Shared control-kit wiring and stage layout for Leo's Syllable Train (ADR 0037).

* the listen button is a round kit ``IconButton`` with ``icon.hud.listen``;
* round progress is kit ``ProgressDots``;
* the choices (vowels, syllable tiles or pictures, 2–4 of them) are kit
  ``IconButton`` tiles in one row under the train;
* the clap drum is a kit ``IconButton`` showing the library drum; it replaces
  the choice row during the clap phase;
* the station board is an Activity-drawn ``ExternalTarget``: tapping or
  activating it replays the word (or, on the beats train, the train's beats).

Keyboard, D-pad/stick and the south face button move between them through the
kit's spatial focus; pointer/touch taps activate them directly. Nothing is
placed in the protected Home/Back region: the top row starts after
``ControlLayout.protected`` and the stage sits to the right of Leo.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
)

if __package__:
    from .sillabe_art import TRACK_Y, SillabeArt
    from .sillabe_content import TrainWord
    from .sillabe_model import CHALLENGE_COUNT, MAX_CHOICES, Phase, StepKind, TrainSession
else:
    from sillabe_art import TRACK_Y, SillabeArt
    from sillabe_content import TrainWord
    from sillabe_model import CHALLENGE_COUNT, MAX_CHOICES, Phase, StepKind, TrainSession

STAGE_CENTER_X = 604
CHOICE_SIZE = 124
CHOICE_GAP = 26
CHOICE_CENTER_Y = 512
DRUM_SIZE = 136
PICTURE_SIZE = 96
TILE_TEXT_SIZE = 54
LEO_HEIGHT = 214
LEO_MIDBOTTOM = (138, 594)

# Train geometry (master art scaled by TRAIN_SCALE; see assets/source).
TRAIN_SCALE = 0.8
WAGON_SIZE = (176, 120)          # wagon_*.svg 220×150
WAGON_FACE = pygame.Rect(19, 22, 138, 63)   # cream panel inside the wagon
WAGON_WHEEL_X = (44, 132)        # wheel centres inside a wagon
WAGON_WHEEL_Y = 102
LOCO_SIZE = (192, 166)           # locomotive.svg 240×208
LOCO_WHEEL_X = (46, 104, 150)
LOCO_WHEEL_Y = 136
TRAIN_GAP = 6
WHEEL_SIZE = 40
WHEEL_CENTER_Y = TRACK_Y - 16
SIGN_SIZE = (150, 216)           # station_sign.svg 208×300
SIGN_TOP = 82
SIGN_FACE = pygame.Rect(16, 33, 118, 110)   # cream face inside the board


def choice_id(index: int) -> str:
    return f"choice.{index}"


@dataclass(frozen=True, slots=True)
class TrainLayout:
    """Logical (1024×600) geometry, recomputed only when the display changes."""

    listen: pygame.Rect
    dots_bar: pygame.Rect
    sign: pygame.Rect
    sign_face: pygame.Rect
    drum: pygame.Rect

    @classmethod
    def build(cls, layout: ControlLayout) -> "TrainLayout":
        size = layout.control_height(72, maximum=104)
        bar = layout.top_bar(size)
        listen = pygame.Rect(bar.left, bar.top, size, size)
        dots_bar = pygame.Rect(listen.right + 24, bar.top, max(0, bar.right - listen.right - 24), size)
        sign = pygame.Rect(0, 0, *SIGN_SIZE)
        sign.midtop = (STAGE_CENTER_X, max(SIGN_TOP, bar.bottom - 4))
        face = SIGN_FACE.move(sign.topleft)
        drum = pygame.Rect(0, 0, DRUM_SIZE, DRUM_SIZE)
        drum.center = (STAGE_CENTER_X, CHOICE_CENTER_Y)
        return cls(listen, dots_bar, sign, face, drum)

    @staticmethod
    def choice_rect(count: int, index: int) -> pygame.Rect:
        span = count * CHOICE_SIZE + (count - 1) * CHOICE_GAP
        left = STAGE_CENTER_X - span // 2 + index * (CHOICE_SIZE + CHOICE_GAP)
        return pygame.Rect(left, CHOICE_CENTER_Y - CHOICE_SIZE // 2, CHOICE_SIZE, CHOICE_SIZE)

    @staticmethod
    def train_rects(wagons: int, offset_x: int = 0) -> tuple[tuple[pygame.Rect, ...], pygame.Rect]:
        """Wagon rects (reading order, left to right) and the locomotive on the right."""

        width = wagons * WAGON_SIZE[0] + wagons * TRAIN_GAP + LOCO_SIZE[0]
        left = STAGE_CENTER_X - width // 2 + offset_x
        wagon_top = WHEEL_CENTER_Y - WAGON_WHEEL_Y
        rects = tuple(
            pygame.Rect(left + i * (WAGON_SIZE[0] + TRAIN_GAP), wagon_top, *WAGON_SIZE)
            for i in range(wagons)
        )
        loco = pygame.Rect(left + wagons * (WAGON_SIZE[0] + TRAIN_GAP), WHEEL_CENTER_Y - LOCO_WHEEL_Y, *LOCO_SIZE)
        return rects, loco


class TrainControls:
    """Own the kit controls and the ``ControlLayer`` for the train screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: SillabeArt,
        layout: ControlLayout,
        *,
        on_choice: Callable[[int], object],
        on_listen: Callable[[], object],
        on_sign: Callable[[], object],
        on_drum: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self._on_sign = on_sign
        self.geometry = TrainLayout.build(layout)
        self.listen: IconButton = kit.icon_button(
            "listen",
            self.geometry.listen,
            icon=kit.glyph("listen", int(self.geometry.listen.height * 0.56)),
            on_activate=on_listen,
        )
        self.dots: ProgressDots = kit.progress_dots("progress", self._dots_rect(), total=CHALLENGE_COUNT)
        self.sign = ExternalTarget("sign", self.geometry.sign_face, on_sign, focus_radius=18)
        self.drum: IconButton = kit.icon_button(
            "drum",
            self.geometry.drum,
            icon=art.art.image("prop.instrument.drum", int(DRUM_SIZE * 0.72)),
            shape=BodyShape.ROUND,
            on_activate=on_drum,
        )
        self.choices = tuple(
            kit.icon_button(
                choice_id(index),
                TrainLayout.choice_rect(MAX_CHOICES, index),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_choice(i)),
            )
            for index in range(MAX_CHOICES)
        )
        self.layer: ControlLayer = kit.layer(self._all_targets(), layer_id="sillabe.controls")
        self._focus_key: tuple | None = None
        self.choice_count = 0

    def _all_targets(self) -> tuple:
        return (self.listen, self.dots, self.sign, self.drum, *self.choices)

    def _dots_rect(self) -> pygame.Rect:
        bar = self.geometry.dots_bar
        height = max(28, min(46, int(bar.height * 0.62)))
        width = min(bar.width, ProgressDots.preferred_width(CHALLENGE_COUNT, height))
        rect = pygame.Rect(0, 0, width, height)
        rect.midright = (bar.right, bar.centery)
        return rect

    def relayout(self, layout: ControlLayout) -> None:
        self.geometry = TrainLayout.build(layout)
        self.listen.rect = self.geometry.listen
        self.listen.icon = self._kit.glyph("listen", int(self.geometry.listen.height * 0.56))
        self.dots.rect = self._dots_rect()
        self.drum.rect = self.geometry.drum
        focused = self.layer.focused_id
        self.sign = ExternalTarget("sign", self.geometry.sign_face, self._on_sign, focus_radius=18)
        self.layer.set_targets(self._all_targets())
        if focused is not None:
            self.layer.focus(focused)
        self._focus_key = None
        self.layer.invalidation.invalidate()

    def sync(self, session: TrainSession, *, interactive: bool = True) -> None:
        """Mirror the session phase into the drum / tiles (icons pre-scaled here)."""

        self.dots.set_progress(session.challenge_index)
        challenge = session.current_challenge
        phase = session.phase
        step = session.current_step
        clapping = interactive and phase is Phase.CLAP
        self.drum.visible = clapping
        self.drum.enabled = clapping
        self.sign.enabled = challenge is not None
        if step is None or not interactive:
            for button in self.choices:
                button.visible = False
                button.enabled = False
            self.choice_count = 0
        else:
            count = len(step.choices)
            self.choice_count = count
            eliminated = session.eliminated
            for index, button in enumerate(self.choices):
                if index >= count:
                    button.visible = False
                    button.enabled = False
                    continue
                button.rect = TrainLayout.choice_rect(count, index)
                button.icon = self.icon_for(step.kind, step.choices[index])
                # A pool tile already placed on an earlier wagon leaves the row.
                button.visible = index not in step.used
                button.enabled = index not in eliminated
        key = (challenge.challenge_id if challenge else None, phase, session.step_index, interactive)
        if key != self._focus_key:
            self._focus_key = key
            if clapping:
                self.layer.focus("drum")
            elif step is not None and interactive:
                first = next((i for i in range(self.choice_count) if i not in session.eliminated), None)
                if first is not None:
                    self.layer.focus(choice_id(first))
        focused = self.layer.focused_id
        if focused is not None and not self.layer.target(focused).focusable:
            fallback = next(
                (choice_id(i) for i in range(self.choice_count) if self.choices[i].enabled),
                "drum" if self.drum.enabled else "listen",
            )
            self.layer.focus(fallback)
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def icon_for(self, kind: StepKind, choice) -> pygame.Surface | None:
        if kind is StepKind.PICTURE:
            assert isinstance(choice, TrainWord)
            return self._art.picture(choice, PICTURE_SIZE)
        assert isinstance(choice, str)
        size = TILE_TEXT_SIZE if len(choice) <= 2 else max(34, TILE_TEXT_SIZE - 9 * (len(choice) - 2))
        return self._art.tile_text(choice, size)

    def choice_center(self, index: int) -> tuple[int, int]:
        return self.choices[index].rect.center


__all__ = [
    "LEO_HEIGHT",
    "LEO_MIDBOTTOM",
    "LOCO_WHEEL_X",
    "PICTURE_SIZE",
    "TrainControls",
    "TrainLayout",
    "WAGON_FACE",
    "WAGON_WHEEL_X",
    "WHEEL_CENTER_Y",
    "WHEEL_SIZE",
    "choice_id",
]

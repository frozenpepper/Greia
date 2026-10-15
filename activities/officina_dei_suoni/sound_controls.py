"""Shared control-kit wiring and workshop layout for Officina dei Suoni (ADR 0037).

* the listen button is a round kit ``IconButton`` with ``icon.hud.listen``;
* round progress is kit ``ProgressDots``;
* the three choices are kit ``IconButton`` tiles showing a library picture
  (first-sound stage) or a capital letter (letter stages);
* the Sound Machine's screen is an Activity-drawn ``ExternalTarget``: tapping
  or activating it replays the machine's sound or word.

Keyboard, D-pad/stick and the south face button move between them through
the kit's spatial focus; pointer/touch taps activate them directly. Nothing is
placed in the protected Home/Back region: the top row starts after
``ControlLayout.protected`` and the machine and tiles sit to the right of Dani.
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
    from .sound_art import SoundWorkshopArt
    from .sound_content import WordItem
    from .sound_workshop_model import CHALLENGE_COUNT, CHOICE_COUNT, SoundSession
else:
    from sound_art import SoundWorkshopArt
    from sound_content import WordItem
    from sound_workshop_model import CHALLENGE_COUNT, CHOICE_COUNT, SoundSession

STAGE_CENTER_X = 566
CHOICE_SIZE = 156
CHOICE_GAP = 34
CHOICE_CENTER_Y = 512
PICTURE_SIZE = 118
LETTER_SIZE = 112
DANI_HEIGHT = 236
DANI_MIDBOTTOM = (150, 592)

# Sound Machine master geometry (assets/source/machine.svg, 440×360 units).
MACHINE_SIZE = (440, 360)
MACHINE_TOP = 68
SCREEN_IN_MACHINE = pygame.Rect(110, 102, 220, 140)
SLOT_PANEL_IN_MACHINE = pygame.Rect(74, 258, 292, 60)
HOPPER_IN_MACHINE = (220, 22)
HORN_IN_MACHINE = (410, 58)
GEARS_IN_MACHINE = ((36, 174, 112), (60, 110, 72))  # centre x, centre y, size
SLOT_BOX = 50          # letter boxes of a whole word
SLOT_BOX_SINGLE = 56   # the one first-sound box
SLOT_GAP = 6


def choice_id(index: int) -> str:
    return f"choice.{index}"


@dataclass(frozen=True, slots=True)
class WorkshopLayout:
    """Logical (1024×600) geometry, recomputed only when the display changes."""

    listen: pygame.Rect
    dots_bar: pygame.Rect
    machine: pygame.Rect
    screen: pygame.Rect
    slot_panel: pygame.Rect
    hopper: tuple[int, int]
    horn: tuple[int, int]
    gears: tuple[tuple[int, int, int], ...]

    @classmethod
    def build(cls, layout: ControlLayout) -> "WorkshopLayout":
        size = layout.control_height(72, maximum=104)
        bar = layout.top_bar(size)
        listen = pygame.Rect(bar.left, bar.top, size, size)
        dots_bar = pygame.Rect(listen.right + 24, bar.top, max(0, bar.right - listen.right - 24), size)
        machine = pygame.Rect(0, 0, *MACHINE_SIZE)
        machine.midtop = (STAGE_CENTER_X, MACHINE_TOP)
        ox, oy = machine.topleft
        screen = SCREEN_IN_MACHINE.move(ox, oy)
        panel = SLOT_PANEL_IN_MACHINE.move(ox, oy)
        hopper = (ox + HOPPER_IN_MACHINE[0], oy + HOPPER_IN_MACHINE[1])
        horn = (ox + HORN_IN_MACHINE[0], oy + HORN_IN_MACHINE[1])
        gears = tuple((ox + x, oy + y, s) for x, y, s in GEARS_IN_MACHINE)
        return cls(listen, dots_bar, machine, screen, panel, hopper, horn, gears)

    @staticmethod
    def choice_rect(count: int, index: int) -> pygame.Rect:
        span = count * CHOICE_SIZE + (count - 1) * CHOICE_GAP
        left = STAGE_CENTER_X - span // 2 + index * (CHOICE_SIZE + CHOICE_GAP)
        return pygame.Rect(left, CHOICE_CENTER_Y - CHOICE_SIZE // 2, CHOICE_SIZE, CHOICE_SIZE)

    def slot_rects(self, count: int) -> tuple[pygame.Rect, ...]:
        """Letter boxes centred in the machine's slot panel (one per letter)."""

        count = max(1, count)
        widest = SLOT_BOX_SINGLE if count == 1 else SLOT_BOX
        box = min(widest, (self.slot_panel.width - 16 - (count - 1) * SLOT_GAP) // count)
        span = count * box + (count - 1) * SLOT_GAP
        left = self.slot_panel.centerx - span // 2
        top = self.slot_panel.centery - box // 2
        return tuple(pygame.Rect(left + i * (box + SLOT_GAP), top, box, box) for i in range(count))


class WorkshopControls:
    """Own the kit controls and the ``ControlLayer`` for the workshop screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: SoundWorkshopArt,
        layout: ControlLayout,
        *,
        on_choice: Callable[[int], object],
        on_listen: Callable[[], object],
        on_machine: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self._on_machine = on_machine
        self.geometry = WorkshopLayout.build(layout)
        self.listen: IconButton = kit.icon_button(
            "listen",
            self.geometry.listen,
            icon=kit.glyph("listen", int(self.geometry.listen.height * 0.56)),
            on_activate=on_listen,
        )
        self.dots: ProgressDots = kit.progress_dots("progress", self._dots_rect(), total=CHALLENGE_COUNT)
        self.machine = ExternalTarget("machine", self.geometry.screen, on_machine, focus_radius=26)
        self.choices = tuple(
            kit.icon_button(
                choice_id(index),
                WorkshopLayout.choice_rect(CHOICE_COUNT, index),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_choice(i)),
            )
            for index in range(CHOICE_COUNT)
        )
        self.layer: ControlLayer = kit.layer(self._all_targets(), layer_id="officina.controls")
        self._step_key: tuple | None = None

    def _all_targets(self) -> tuple:
        return (self.listen, self.dots, self.machine, *self.choices)

    def _dots_rect(self) -> pygame.Rect:
        bar = self.geometry.dots_bar
        height = max(28, min(46, int(bar.height * 0.62)))
        width = min(bar.width, ProgressDots.preferred_width(CHALLENGE_COUNT, height))
        rect = pygame.Rect(0, 0, width, height)
        rect.midright = (bar.right, bar.centery)
        return rect

    def relayout(self, layout: ControlLayout) -> None:
        self.geometry = WorkshopLayout.build(layout)
        self.listen.rect = self.geometry.listen
        self.listen.icon = self._kit.glyph("listen", int(self.geometry.listen.height * 0.56))
        self.dots.rect = self._dots_rect()
        focused = self.layer.focused_id
        self.machine = ExternalTarget("machine", self.geometry.screen, self._on_machine, focus_radius=26)
        self.layer.set_targets(self._all_targets())
        if focused is not None:
            self.layer.focus(focused)
        self._step_key = None
        self.layer.invalidation.invalidate()

    def sync(self, session: SoundSession) -> None:
        """Mirror the current step into the tiles (pictures/letters pre-scaled here)."""

        self.dots.set_progress(session.challenge_index)
        challenge = session.current_challenge
        step = session.current_step
        if challenge is None or step is None:
            for button in self.choices:
                button.visible = False
                button.enabled = False
            self.machine.enabled = False
            self.layer.invalidation.invalidate()
            return
        self.machine.enabled = True
        eliminated = session.eliminated
        for index, button in enumerate(self.choices):
            item = step.choices[index]
            button.rect = WorkshopLayout.choice_rect(CHOICE_COUNT, index)
            if isinstance(item, WordItem):
                button.icon = self._art.picture(item, PICTURE_SIZE)
            else:
                button.icon = self._art.letter(item, LETTER_SIZE)
            button.visible = True
            button.enabled = index not in eliminated
        key = (challenge.challenge_id, session.step_index)
        if key != self._step_key:
            self._step_key = key
            self.layer.focus(choice_id(0))
        focused = self.layer.focused_id
        if focused is not None and not self.layer.target(focused).focusable:
            first = next((choice_id(i) for i in range(CHOICE_COUNT) if i not in eliminated), "listen")
            self.layer.focus(first)
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def choice_center(self, index: int) -> tuple[int, int]:
        return self.choices[index].rect.center


__all__ = [
    "WorkshopControls",
    "WorkshopLayout",
    "choice_id",
    "DANI_HEIGHT",
    "DANI_MIDBOTTOM",
    "PICTURE_SIZE",
]

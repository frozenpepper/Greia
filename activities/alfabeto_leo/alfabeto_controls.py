"""Shared control-kit wiring and garden layout for L'Alfabeto di Leo (ADR 0037).

* the listen button is a round kit ``IconButton`` with ``icon.hud.listen``;
* round progress is kit ``ProgressDots``;
* the letter choices are kit ``IconButton`` tiles showing stroke-font letters;
* the big letter (meet) and the tracing box are Activity-drawn
  ``ExternalTarget``s so keyboard, D-pad/stick and the south face button reach
  them through the kit's spatial focus. The tracing box is keyboard-only: a
  finger on it traces (handled by the app), the action button makes the
  current stroke trace itself.

Nothing is placed in the protected Home/Back region: the top row starts after
``ControlLayout.protected`` and the stage sits right of Leo, clear of it.
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
    from .alfabeto_art import AlfabetoArt
    from .alfabeto_model import REFERENCE_HEIGHT, GardenStep, StepKind
else:
    from alfabeto_art import AlfabetoArt
    from alfabeto_model import REFERENCE_HEIGHT, GardenStep, StepKind

MAX_CHOICES = 3
CHOICE_SIZE = 192
CHOICE_GAP = 40
TILE_GLYPH = 136
LEO_HEIGHT = 236
LEO_MIDBOTTOM = (150, 594)
CARD_RECT = pygame.Rect(292, 100, 712, 392)
GARDEN_TOP = 500


def choice_id(index: int) -> str:
    return f"choice.{index}"


class KeyboardTarget(ExternalTarget):
    """Focusable by keyboard/controller only; pointer touches go to gameplay."""

    def contains(self, point: tuple[int, int]) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class GardenLayout:
    """Logical (1024×600) geometry, recomputed only when the display changes."""

    listen: pygame.Rect
    dots_bar: pygame.Rect
    card: pygame.Rect
    meet_letter: pygame.Rect
    meet_picture: pygame.Rect
    find_picture: pygame.Rect
    choice_row_y: int
    trace_box: pygame.Rect
    trace_picture: pygame.Rect
    garden: pygame.Rect

    @classmethod
    def build(cls, layout: ControlLayout) -> "GardenLayout":
        size = layout.control_height(72, maximum=104)
        bar = layout.top_bar(size)
        listen = pygame.Rect(bar.left, bar.top, size, size)
        dots_bar = pygame.Rect(listen.right + 24, bar.top, max(0, bar.right - listen.right - 24), size)
        card = layout.clear_of_chrome(CARD_RECT.copy())
        card.top = max(card.top, bar.bottom + 12)
        card.height = min(CARD_RECT.height, GARDEN_TOP - 8 - card.top)
        inner = card.inflate(-44, -40)
        meet_letter = pygame.Rect(inner.left + 10, inner.top, int(inner.width * 0.5), inner.height)
        side = min(inner.height - 30, int(inner.width * 0.42))
        meet_picture = pygame.Rect(0, 0, side, side)
        meet_picture.center = (inner.left + int(inner.width * 0.76), inner.centery)
        find_side = min(146, inner.height - CHOICE_SIZE - 12)
        find_picture = pygame.Rect(0, 0, find_side, find_side)
        find_picture.midtop = (inner.centerx, inner.top - 6)
        choice_row_y = inner.bottom - CHOICE_SIZE // 2 - 6
        trace_box = pygame.Rect(inner.left + 30, inner.top - 4, int(inner.width * 0.56), inner.height + 8)
        tp = min(176, inner.height // 2)
        trace_picture = pygame.Rect(0, 0, tp, tp)
        trace_picture.center = (inner.left + int(inner.width * 0.83), inner.centery)
        garden = pygame.Rect(card.left + 40, GARDEN_TOP, card.width - 80, REFERENCE_HEIGHT - GARDEN_TOP - 6)
        return cls(listen, dots_bar, card, meet_letter, meet_picture, find_picture, choice_row_y, trace_box, trace_picture, garden)

    def choice_rect(self, count: int, index: int) -> pygame.Rect:
        span = count * CHOICE_SIZE + (count - 1) * CHOICE_GAP
        left = self.card.centerx - span // 2 + index * (CHOICE_SIZE + CHOICE_GAP)
        return pygame.Rect(left, self.choice_row_y - CHOICE_SIZE // 2, CHOICE_SIZE, CHOICE_SIZE)

    def garden_slot(self, count: int, index: int) -> pygame.Rect:
        """Bed ``index`` of ``count`` along the garden strip under the card."""

        count = max(1, count)
        width = min(200, self.garden.width // count)
        left = self.garden.centerx - width * count // 2 + index * width
        return pygame.Rect(left, self.garden.top, width, self.garden.height)


class GardenControls:
    """Own the kit controls and the ``ControlLayer`` for the garden screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: AlfabetoArt,
        layout: ControlLayout,
        *,
        task_total: int,
        on_choice: Callable[[int], object],
        on_listen: Callable[[], object],
        on_letter: Callable[[], object],
        on_trace_key: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self.geometry = GardenLayout.build(layout)
        self.listen: IconButton = kit.icon_button(
            "listen",
            self.geometry.listen,
            icon=kit.glyph("listen", int(self.geometry.listen.height * 0.56)),
            on_activate=on_listen,
        )
        self.dots: ProgressDots = kit.progress_dots("progress", self._dots_rect(task_total), total=task_total)
        self._on_letter = on_letter
        self._on_trace_key = on_trace_key
        self.letter, self.trace = self._stage_targets()
        self.choices = tuple(
            kit.icon_button(
                choice_id(index),
                self.geometry.choice_rect(MAX_CHOICES, index),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_choice(i)),
            )
            for index in range(MAX_CHOICES)
        )
        self.layer: ControlLayer = kit.layer(self._all_targets(), layer_id="alfabeto.controls")
        self._step_key: tuple | None = None

    def _stage_targets(self) -> tuple[ExternalTarget, KeyboardTarget]:
        letter = ExternalTarget("letter", self.geometry.meet_letter, self._on_letter, focus_radius=36)
        trace = KeyboardTarget("trace", self.geometry.trace_box, self._on_trace_key, focus_radius=36)
        return letter, trace

    def _all_targets(self) -> tuple:
        return (self.listen, self.dots, self.letter, self.trace, *self.choices)

    def _dots_rect(self, total: int) -> pygame.Rect:
        bar = self.geometry.dots_bar
        height = max(28, min(46, int(bar.height * 0.62)))
        width = min(bar.width, ProgressDots.preferred_width(total, height))
        rect = pygame.Rect(0, 0, width, height)
        rect.midright = (bar.right, bar.centery)
        return rect

    def relayout(self, layout: ControlLayout) -> None:
        self.geometry = GardenLayout.build(layout)
        self.listen.rect = self.geometry.listen
        self.listen.icon = self._kit.glyph("listen", int(self.geometry.listen.height * 0.56))
        self.dots.rect = self._dots_rect(self.dots.total)
        focused = self.layer.focused_id
        self.letter, self.trace = self._stage_targets()
        self.layer.set_targets(self._all_targets())
        if focused is not None:
            self.layer.focus(focused)
        self._step_key = None
        self.layer.invalidation.invalidate()

    def reset_round(self, task_total: int) -> None:
        self.dots.total = int(task_total)
        self.dots.rect = self._dots_rect(task_total)
        self._step_key = None

    def sync(self, step: GardenStep | None, *, eliminated: frozenset[int], tasks_done: int, step_key: object) -> None:
        """Mirror the shown step into the controls (letter tiles pre-rendered)."""

        self.dots.set_progress(tasks_done)
        kind = step.kind if step is not None else None
        self.letter.enabled = kind is StepKind.MEET
        self.letter.focusable = kind is StepKind.MEET
        self.trace.enabled = kind is StepKind.TRACE
        self.trace.focusable = kind is StepKind.TRACE
        count = len(step.choices) if step is not None and step.is_find else 0
        for index, button in enumerate(self.choices):
            if index < count:
                assert step is not None
                item = step.choices[index]
                button.rect = self.geometry.choice_rect(count, index)
                button.icon = self._art.glyphs.tile(item.char, TILE_GLYPH, item.color)
                button.visible = True
                button.enabled = index not in eliminated
            else:
                button.visible = False
                button.enabled = False
        if step_key != self._step_key:
            self._step_key = step_key
            if kind is StepKind.TRACE:
                self.layer.focus("trace")
            elif kind is StepKind.MEET:
                self.layer.focus("letter")
            elif count:
                self.layer.focus(choice_id(0))
        focused = self.layer.focused_id
        if focused is not None and not self.layer.target(focused).focusable:
            first = next((choice_id(i) for i in range(count) if i not in eliminated), None)
            self.layer.focus(first or "listen")
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def choice_center(self, index: int) -> tuple[int, int]:
        return self.choices[index].rect.center


__all__ = ["GardenControls", "GardenLayout", "KeyboardTarget", "LEO_HEIGHT", "LEO_MIDBOTTOM", "choice_id"]

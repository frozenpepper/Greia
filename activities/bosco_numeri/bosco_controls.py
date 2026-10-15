"""Shared control-kit wiring and forest layout for Tito's Number Forest (ADR 0037).

* the listen button is a round kit ``IconButton`` with ``icon.hud.listen``;
* walk progress is kit ``ProgressDots``;
* the options are kit ``IconButton`` tiles: stroke-font numerals on FIND
  steps, quantity frames of forest friends on SHOW steps;
* the big numeral (meet) and the tracing box are Activity-drawn
  ``ExternalTarget``s so keyboard, D-pad/stick and the south face button reach
  them through the kit's spatial focus. The tracing box is keyboard-only: a
  finger on it traces (handled by the app), the action button makes the
  current stroke trace itself.

Nothing is placed in the protected Home/Back region: the top row starts after
``ControlLayout.protected`` and the stage sits right of Tito, clear of it.
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
    from .bosco_art import BoscoArt, FrameGeometry, frame_cells_for
    from .bosco_model import REFERENCE_HEIGHT, ForestStep, StepKind
else:
    from bosco_art import BoscoArt, FrameGeometry, frame_cells_for
    from bosco_model import REFERENCE_HEIGHT, ForestStep, StepKind

MAX_CHOICES = 3
CHOICE_SIZE = 192
CHOICE_GAP = 40
TILE_GLYPH = 132
SHOW_GAP = 24
SHOW_NUMERAL_WIDTH = 150
SHOW_PAD = 32
LIP_SHARE = 0.93
TITO_HEIGHT = 232
TITO_MIDBOTTOM = (150, 596)
CARD_RECT = pygame.Rect(292, 100, 712, 392)
PATH_TOP = 500


def choice_id(index: int) -> str:
    return f"choice.{index}"


class KeyboardTarget(ExternalTarget):
    """Focusable by keyboard/controller only; pointer touches go to gameplay."""

    def contains(self, point: tuple[int, int]) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class ForestLayout:
    """Logical (1024×600) geometry, recomputed only when the display changes."""

    listen: pygame.Rect
    dots_bar: pygame.Rect
    card: pygame.Rect
    meet_numeral: pygame.Rect
    meet_frame: pygame.Rect
    find_sign: pygame.Rect
    choice_row_y: int
    trace_box: pygame.Rect
    trace_frame: pygame.Rect
    show_numeral: pygame.Rect
    show_area: pygame.Rect
    path: pygame.Rect

    @classmethod
    def build(cls, layout: ControlLayout) -> "ForestLayout":
        size = layout.control_height(72, maximum=104)
        bar = layout.top_bar(size)
        listen = pygame.Rect(bar.left, bar.top, size, size)
        dots_bar = pygame.Rect(listen.right + 24, bar.top, max(0, bar.right - listen.right - 24), size)
        card = layout.clear_of_chrome(CARD_RECT.copy())
        card.top = max(card.top, bar.bottom + 12)
        card.height = min(CARD_RECT.height, PATH_TOP - 8 - card.top)
        inner = card.inflate(-44, -40)
        meet_numeral = pygame.Rect(inner.left + 6, inner.top, int(inner.width * 0.34), inner.height)
        meet_frame = pygame.Rect(meet_numeral.right + 16, inner.top, inner.right - meet_numeral.right - 16, inner.height)
        choice_row_y = inner.bottom - CHOICE_SIZE // 2 - 6
        sign_h = max(40, choice_row_y - CHOICE_SIZE // 2 - inner.top - 6)
        find_sign = pygame.Rect(inner.left, inner.top - 6, inner.width, sign_h)
        trace_box = pygame.Rect(inner.left + 24, inner.top - 4, int(inner.width * 0.52), inner.height + 8)
        trace_frame = pygame.Rect(trace_box.right + 20, inner.top, inner.right - trace_box.right - 20, inner.height)
        show_numeral = pygame.Rect(inner.left, inner.top, SHOW_NUMERAL_WIDTH, inner.height)
        show_area = pygame.Rect(show_numeral.right + 20, inner.top - 6, inner.right - show_numeral.right - 20, inner.height + 12)
        path = pygame.Rect(card.left + 40, PATH_TOP, card.width - 80, REFERENCE_HEIGHT - PATH_TOP - 6)
        return cls(listen, dots_bar, card, meet_numeral, meet_frame, find_sign, choice_row_y, trace_box, trace_frame, show_numeral, show_area, path)

    def choice_rect(self, count: int, index: int) -> pygame.Rect:
        span = count * CHOICE_SIZE + (count - 1) * CHOICE_GAP
        left = self.card.centerx - span // 2 + index * (CHOICE_SIZE + CHOICE_GAP)
        return pygame.Rect(left, self.choice_row_y - CHOICE_SIZE // 2, CHOICE_SIZE, CHOICE_SIZE)

    def show_width(self, count: int) -> int:
        return min(300, (self.show_area.width - (count - 1) * SHOW_GAP) // max(1, count))

    def show_row_height(self, count: int) -> int:
        return (self.show_area.height - (count - 1) * SHOW_GAP) // max(1, count)

    def show_rect(self, count: int, index: int, size: tuple[int, int], *, stacked: bool) -> pygame.Rect:
        """Quantity-frame option ``index`` of ``count`` right of the numeral.

        Five-frames are wide, so their options stack in rows; ten-frames stand
        upright, so their options sit side by side in columns.
        """

        width, height = min(int(size[0]), self.show_area.width), min(int(size[1]), self.show_area.height)
        if stacked:
            span = count * height + (count - 1) * SHOW_GAP
            top = self.show_area.centery - span // 2 + index * (height + SHOW_GAP)
            return pygame.Rect(self.show_area.centerx - width // 2, top, width, height)
        span = count * width + (count - 1) * SHOW_GAP
        left = self.show_area.centerx - span // 2 + index * (width + SHOW_GAP)
        return pygame.Rect(left, self.show_area.centery - height // 2, width, height)

    def path_slot(self, count: int, index: int) -> pygame.Rect:
        """Signpost ``index`` of ``count`` along the forest path under the card."""

        count = max(1, count)
        width = min(220, self.path.width // count)
        left = self.path.centerx - width * count // 2 + index * width
        return pygame.Rect(left, self.path.top, width, self.path.height)


class ForestControls:
    """Own the kit controls and the ``ControlLayer`` for the forest screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: BoscoArt,
        layout: ControlLayout,
        *,
        task_total: int,
        on_choice: Callable[[int], object],
        on_listen: Callable[[], object],
        on_numeral: Callable[[], object],
        on_trace_key: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self.geometry = ForestLayout.build(layout)
        self.listen: IconButton = kit.icon_button(
            "listen",
            self.geometry.listen,
            icon=kit.glyph("listen", int(self.geometry.listen.height * 0.56)),
            on_activate=on_listen,
        )
        self.dots: ProgressDots = kit.progress_dots("progress", self._dots_rect(task_total), total=task_total)
        self._on_numeral = on_numeral
        self._on_trace_key = on_trace_key
        self.numeral, self.trace = self._stage_targets()
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
        self.layer: ControlLayer = kit.layer(self._all_targets(), layer_id="bosco.controls")
        self._step_key: tuple | None = None

    def _stage_targets(self) -> tuple[ExternalTarget, KeyboardTarget]:
        numeral = ExternalTarget("numeral", self.geometry.meet_numeral, self._on_numeral, focus_radius=36)
        trace = KeyboardTarget("trace", self.geometry.trace_box, self._on_trace_key, focus_radius=36)
        return numeral, trace

    def _all_targets(self) -> tuple:
        return (self.listen, self.dots, self.numeral, self.trace, *self.choices)

    def _dots_rect(self, total: int) -> pygame.Rect:
        bar = self.geometry.dots_bar
        height = max(28, min(46, int(bar.height * 0.62)))
        width = min(bar.width, ProgressDots.preferred_width(total, height))
        rect = pygame.Rect(0, 0, width, height)
        rect.midright = (bar.right, bar.centery)
        return rect

    def relayout(self, layout: ControlLayout) -> None:
        self.geometry = ForestLayout.build(layout)
        self.listen.rect = self.geometry.listen
        self.listen.icon = self._kit.glyph("listen", int(self.geometry.listen.height * 0.56))
        self.dots.rect = self._dots_rect(self.dots.total)
        focused = self.layer.focused_id
        self.numeral, self.trace = self._stage_targets()
        self.layer.set_targets(self._all_targets())
        if focused is not None:
            self.layer.focus(focused)
        self._step_key = None
        self.layer.invalidation.invalidate()

    def reset_round(self, task_total: int) -> None:
        self.dots.total = int(task_total)
        self.dots.rect = self._dots_rect(task_total)
        self._step_key = None

    def option_rect(self, step: ForestStep, index: int) -> pygame.Rect:
        count = len(step.choices)
        if step.kind is StepKind.SHOW:
            frame = self.show_frame(step)
            width, height = frame.size
            # Tile padding around the frame plus the kit's tactile lip (~7 %).
            size = (width + SHOW_PAD, int((height + SHOW_PAD) / LIP_SHARE))
            return self.geometry.show_rect(count, index, size, stacked=not frame.vertical)
        return self.geometry.choice_rect(count, index)

    def show_frame(self, step: ForestStep, index: int = 0) -> FrameGeometry:
        """Frame geometry inside every SHOW option (the same for all options)."""

        geometry = self.geometry
        count = len(step.choices)
        cells = frame_cells_for(*step.choices)
        if cells == 10:
            box = (geometry.show_width(count) - SHOW_PAD, int(geometry.show_area.height * LIP_SHARE) - SHOW_PAD)
            return FrameGeometry.fit(cells, box, max_cell=72, allow_vertical=True)
        box = (geometry.show_area.width - SHOW_PAD, int(geometry.show_row_height(count) * LIP_SHARE) - SHOW_PAD)
        return FrameGeometry.fit(cells, box, max_cell=80)

    def sync(self, step: ForestStep | None, *, eliminated: frozenset[int], tasks_done: int, step_key: object) -> None:
        """Mirror the shown step into the controls (tile faces pre-rendered)."""

        self.dots.set_progress(tasks_done)
        kind = step.kind if step is not None else None
        self.numeral.enabled = kind is StepKind.MEET
        self.numeral.focusable = kind is StepKind.MEET
        self.trace.enabled = kind is StepKind.TRACE
        self.trace.focusable = kind is StepKind.TRACE
        count = len(step.choices) if step is not None and step.is_choice else 0
        for index, button in enumerate(self.choices):
            if index < count:
                assert step is not None
                button.rect = self.option_rect(step, index)
                button.icon = self._option_face(step, index)
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
                self.layer.focus("numeral")
            elif count:
                self.layer.focus(choice_id(0))
        focused = self.layer.focused_id
        if focused is not None and not self.layer.target(focused).focusable:
            first = next((choice_id(i) for i in range(count) if i not in eliminated), None)
            self.layer.focus(first or "listen")
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def _option_face(self, step: ForestStep, index: int) -> pygame.Surface:
        value = step.choices[index]
        if step.kind is StepKind.SHOW:
            return self._art.quantity(step.numeral.creature, value, self.show_frame(step, index))
        # Every numeral tile wears the same ink so colour never gives the answer away.
        return self._art.glyphs.tile(value, (TILE_GLYPH + (36 if value >= 10 else 0), TILE_GLYPH), "ocean")

    def choice_center(self, index: int) -> tuple[int, int]:
        return self.choices[index].rect.center


__all__ = [
    "ForestControls",
    "ForestLayout",
    "KeyboardTarget",
    "TITO_HEIGHT",
    "TITO_MIDBOTTOM",
    "choice_id",
]

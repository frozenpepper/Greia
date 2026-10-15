"""Shared control-kit wiring for Il Giardino dei Numeri (ADR 0037).

Garden objects are Activity-drawn ``ExternalTarget``s (the kit adds pointer
activation, keyboard/D-pad/stick focus and the focus ring); the "how many?"
answers are kit ``IconButton`` tiles showing a numeral + dot card; the replay
voice is a round ``IconButton`` with the shared ``listen`` glyph and progress
is ``ProgressDots``. Rules stay in ``GardenRound``; this class only maps
controls to the app callbacks.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.activity_controls import (
    Align,
    BodyShape,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
)

if __package__:
    from .giardino_art import CARD_SIZE, GardenArt
    from .giardino_model import ITEM_SIZE, GardenRound, Phase
else:
    from giardino_art import CARD_SIZE, GardenArt
    from giardino_model import ITEM_SIZE, GardenRound, Phase

MAX_CHOICES = 3
CARD_CENTER_Y = 262
CARD_CENTER_X = 610
CARD_GAP = 44
ITEM_TARGET = 116  # < cell pitch, so neighbouring targets never overlap much


def item_id(index: int) -> str:
    return f"item.{index}"


def choice_id(index: int) -> str:
    return f"choice.{index}"


def card_rects(count: int) -> list[pygame.Rect]:
    width, height = CARD_SIZE
    total = count * width + (count - 1) * CARD_GAP
    left = CARD_CENTER_X - total // 2
    return [
        pygame.Rect(left + index * (width + CARD_GAP), CARD_CENTER_Y - height // 2, width, height)
        for index in range(count)
    ]


class GardenControls:
    """Own the kit controls and the ``ControlLayer`` for the garden screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: GardenArt,
        layout: ControlLayout,
        rounds: int,
        *,
        on_item: Callable[[int], object],
        on_choice: Callable[[int], object],
        on_listen: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self._on_item = on_item
        self._on_choice = on_choice
        self.items: list[ExternalTarget] = []
        self.choices: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                choice_id(index),
                pygame.Rect(0, 0, *CARD_SIZE),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_choice(i)),
                enabled=False,
            )
            for index in range(MAX_CHOICES)
        )
        for button in self.choices:
            button.visible = False
        self.listen: IconButton = kit.icon_button(
            "listen",
            pygame.Rect(0, 0, 64, 64),
            icon=kit.glyph("listen", 40),
            on_activate=on_listen,
        )
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=rounds)
        self.layer: ControlLayer = kit.layer((), layer_id="giardino.controls")
        self._round: GardenRound | None = None
        self._choice_values: tuple[int, ...] = ()
        self.relayout(layout)

    # -- geometry -----------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Top bar beside protected chrome: replay voice, then progress dots."""

        height = layout.control_height(56, maximum=72)
        bar = layout.top_bar(height)
        dots_height = max(34, int(height * 0.66))
        dots_width = ProgressDots.preferred_width(self.progress.total, dots_height)
        listen_rect, dots_rect = layout.row(bar, [height, dots_width], align=Align.END, height=height)
        self.listen.rect = listen_rect
        self.progress.rect = pygame.Rect(dots_rect.x, dots_rect.centery - dots_height // 2, dots_width, dots_height)
        self.layer.invalidation.invalidate()

    # -- round binding --------------------------------------------------------

    def bind_round(self, round_: GardenRound) -> None:
        """Create one focus target per garden object for a new basket."""

        self._round = round_
        half = ITEM_TARGET // 2
        self.items = [
            ExternalTarget(
                item_id(item.item_id),
                pygame.Rect(int(item.x) - half, int(item.y) - half, ITEM_TARGET, ITEM_TARGET),
                (lambda i=item.item_id: self._on_item(i)),
                focus_radius=ITEM_SIZE // 2,
            )
            for item in round_.items
        ]
        self._choice_values = ()
        for rect, button in zip(card_rects(len(round_.choices) or 1), self.choices):
            button.rect = rect
        self.layer.set_targets((*self.items, *self.choices, self.listen, self.progress))
        self.sync(round_, refocus=True)

    def choice_value(self, index: int) -> int | None:
        if 0 <= index < len(self._choice_values):
            return self._choice_values[index]
        return None

    def sync(self, round_: GardenRound, *, refocus: bool = False) -> None:
        """Mirror round state into control enablement/visibility (cheap)."""

        counting = round_.phase is Phase.COUNTING
        for target, item in zip(self.items, round_.items):
            target.enabled = counting and not item.counted
        show_cards = round_.phase in {Phase.ASKING, Phase.DEMONSTRATING}
        if show_cards and self._choice_values != round_.choices:
            self._choice_values = round_.choices
            for rect, button, value in zip(card_rects(len(round_.choices)), self.choices, round_.choices):
                button.rect = rect
                button.icon = self._art.card_face(value)
        for index, button in enumerate(self.choices):
            value = self.choice_value(index)
            button.visible = show_cards and value is not None
            # Cards stay lit during the recount demonstration (the model ignores
            # choices then); only a rejected answer greys out.
            button.enabled = button.visible and value not in round_.rejected
        self.listen.visible = counting
        self.listen.enabled = counting
        if refocus or not self._focused_is_live():
            self.focus_default(round_)
        self.layer.invalidation.invalidate()

    def focus_default(self, round_: GardenRound) -> None:
        if round_.phase is Phase.COUNTING:
            waiting = round_.next_uncounted()
            if waiting is not None:
                self.layer.focus(item_id(waiting.item_id))
                return
        if round_.phase is Phase.ASKING:
            for button in self.choices:
                if button.enabled:
                    self.layer.focus(button.control_id)
                    return
        self.layer.ensure_focus()

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        target = self.layer.target(focused)
        return target.focusable and target.enabled

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()


__all__ = ["GardenControls", "card_rects", "choice_id", "item_id"]

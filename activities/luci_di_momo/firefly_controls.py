"""Shared control-kit wiring for Luci di Momo (ADR 0037).

The three "how many?" answers are kit ``IconButton`` tiles showing a numeral
(with a dot frame at the early stages), "look again" is a round
``IconButton`` with the shared replay glyph, the voice prompt replays from a
round listen button and progress is ``ProgressDots``. The play screen has no
text. Every control is reachable by pointer, touch, keyboard (arrows + Space /
Enter) and controller (D-pad / stick + south button) through the kit's focus
layer. Rules stay in ``FireflySession``; this class mirrors session state into
the controls.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.activity_controls import (
    Align,
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    IconButton,
    ProgressDots,
)

if __package__:
    from .firefly_art import FireflyArt
    from .firefly_layout import CHOICE_RECTS, REPLAY_RECT
    from .firefly_model import ROUND_COUNT, FireflySession, stage_rule
else:
    from firefly_art import FireflyArt
    from firefly_layout import CHOICE_RECTS, REPLAY_RECT
    from firefly_model import ROUND_COUNT, FireflySession, stage_rule


def choice_id(index: int) -> str:
    return f"choice.{index}"


class FireflyControls:
    """Own the kit controls and the ``ControlLayer`` for the night meadow."""

    def __init__(
        self,
        kit: ControlKit,
        art: FireflyArt,
        layout: ControlLayout,
        *,
        on_choice: Callable[[int], object],
        on_replay: Callable[[], object],
        on_listen: Callable[[], object],
    ) -> None:
        self._art = art
        self.choices: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                choice_id(index),
                rect,
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_choice(i)),
                enabled=False,
            )
            for index, rect in enumerate(CHOICE_RECTS)
        )
        self.replay: IconButton = kit.icon_button(
            "replay",
            REPLAY_RECT,
            icon=kit.glyph("replay", 56),
            role=ButtonRole.PRIMARY,
            on_activate=on_replay,
            enabled=False,
        )
        self.listen: IconButton = kit.icon_button(
            "listen",
            pygame.Rect(0, 0, 64, 64),
            icon=kit.glyph("listen", 40),
            on_activate=on_listen,
        )
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=ROUND_COUNT)
        self.layer: ControlLayer = kit.layer(
            (*self.choices, self.replay, self.listen, self.progress),
            layer_id="luci_di_momo.controls",
        )
        self._round_id: str | None = None
        self._values: tuple[int, ...] = ()
        for button in (*self.choices, self.replay):
            button.visible = False
        self.relayout(layout)

    # -- geometry --------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Top bar beside protected chrome: replay voice, then progress dots."""

        height = layout.control_height(56, maximum=72)
        bar = layout.top_bar(height)
        dots_height = max(34, int(height * 0.66))
        dots_width = ProgressDots.preferred_width(ROUND_COUNT, dots_height)
        listen_rect, dots_rect = layout.row(bar, [height, dots_width], align=Align.END, height=height)
        self.listen.rect = listen_rect
        self.progress.rect = pygame.Rect(dots_rect.x, dots_rect.centery - dots_height // 2, dots_width, dots_height)
        self.layer.invalidation.invalidate()

    # -- state sync ---------------------------------------------------------------

    def choice_value(self, index: int) -> int | None:
        if 0 <= index < len(self._values):
            return self._values[index]
        return None

    def index_of(self, value: int) -> int | None:
        return self._values.index(value) if value in self._values else None

    def sync(
        self,
        session: FireflySession,
        *,
        asking: bool,
        busy: bool,
        refocus: bool = False,
    ) -> None:
        """Mirror the session into control visibility/enablement (cheap).

        ``asking``: the cards are on the grass. ``busy``: a scripted moment
        (glimpse, demonstration) plays; the cards stay lit (the app ignores
        them meanwhile) and "look again" greys out.
        """

        self.progress.set_progress(session.round_index)
        current = session.current_round
        if current is not None and current.round_id != self._round_id:
            self._round_id = current.round_id
            self._values = current.choice_values
            dots = stage_rule(session.level).card_dots
            for button, value in zip(self.choices, self._values):
                button.icon = self._art.card_face(value, dots=dots)
        rejected = session.rejected
        for index, button in enumerate(self.choices):
            value = self.choice_value(index)
            shown = asking and value is not None
            button.visible = shown
            # A tried answer stays visible but greyed (kind, no red crosses).
            button.enabled = shown and value not in rejected
        replay_ready = current is not None and not session.missed and not session.replay_used
        self.replay.visible = asking and current is not None and not session.missed
        self.replay.enabled = self.replay.visible and replay_ready and not busy
        if refocus or not self._focused_is_live():
            self.focus_default()
        self.layer.invalidation.invalidate()

    def show_solo(self, index: int) -> None:
        """Keep only the chosen (correct) card on the grass for the close."""

        for position, button in enumerate(self.choices):
            button.visible = position == index
        self.replay.visible = False
        self.layer.invalidation.invalidate()

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()

    def focus_default(self) -> None:
        enabled = [button for button in self.choices if button.enabled and button.visible]
        if enabled:
            self.layer.focus(enabled[len(enabled) // 2].control_id)
            return
        self.layer.ensure_focus()

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        target = self.layer.target(focused)
        return target.focusable and target.enabled

    def wobble_target(self, control_id: str | None) -> IconButton | None:
        """Return the answer control that shakes on a try-again."""

        return next((button for button in self.choices if button.control_id == control_id), None)


__all__ = ["FireflyControls", "choice_id"]

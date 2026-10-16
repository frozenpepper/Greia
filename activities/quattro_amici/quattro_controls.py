"""Shared control-kit wiring for Quattro Amici in Fila (ADR 0037).

The Activity draws its own board; every interactive element goes through
``greia_platform.activity_controls``:

* each board column is an ``ExternalTarget`` (pointer/touch tap drops a disc;
  arrows / D-pad / stick move focus between columns; Space / Enter / south
  button drops), with the shared focus ring after keyboard/controller use;
* "who plays Leo" is a two-slot ``ToolStrip`` (Leo himself, or two friends);
* the turn banner is a display-only ``PromptBanner`` (the goal pictogram —
  N discs on a golden band — plus a short turn line for readers);
* games of the match are ``ProgressDots``;
* "next game" is a primary round ``IconButton`` with the shared go glyph;
* a ``KeyboardHint`` (left / down / right + Space keycaps) beside the board
  teaches that the arrows choose a column and Space or arrow-down drops; the
  drawn key lights while the real key is pressed (ADR 0037 §4b).

Game rules stay in the model; this class only maps controls to the app's
callbacks and mirrors state into control enablement/visibility.
"""

from __future__ import annotations

from collections.abc import Callable
import time

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
    PromptBanner,
)
from greia_platform.activity_keyboard_hint import KeyboardHint, KeyCap
from greia_platform.localization import LocalizedResources

if __package__:
    from .quattro_art import QuattroArt
    from .quattro_content import GAMES_PER_MATCH, GameMode
    from .quattro_layout import BoardGeometry, next_button_rect
else:
    from quattro_art import QuattroArt
    from quattro_content import GAMES_PER_MATCH, GameMode
    from quattro_layout import BoardGeometry, next_button_rect

MAX_COLUMNS = 7

# Keyboard hint: arrows pick the column, arrow-down or Space drops the disc.
KEY_HINT_KEYS = frozenset({KeyCap.LEFT, KeyCap.RIGHT, KeyCap.DOWN, KeyCap.SPACE})
KEY_HINT_KEY = 36
# Right of the board near its top row (where discs drop), above Leo (head ~ y 330).
KEY_HINT_CENTER = (900, 244)


def key_hint_rect() -> pygame.Rect:
    width, height = KeyboardHint.preferred_size(KEY_HINT_KEYS, key=KEY_HINT_KEY)
    rect = pygame.Rect(0, 0, width, height)
    rect.center = KEY_HINT_CENTER
    return rect


def column_id(col: int) -> str:
    return f"column.{col}"


def column_of(control_id: str | None) -> int | None:
    if control_id is None or not control_id.startswith("column."):
        return None
    try:
        return int(control_id.split(".", 1)[1])
    except ValueError:
        return None


class QuattroControls:
    """Own the kit controls and the ``ControlLayer`` for the match screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: QuattroArt,
        resources: LocalizedResources,
        layout: ControlLayout,
        geometry: BoardGeometry,
        mode: GameMode,
        *,
        on_column: Callable[[int], object],
        on_mode: Callable[[str], object],
        on_next: Callable[[], object],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kit = kit
        self._art = art
        self._on_column = on_column
        self.columns: tuple[ExternalTarget, ...] = ()
        self.mode = kit.tool_strip(
            "mode",
            [
                (GameMode.VS_CPU.value, resources.text("ui.mode_vs_leo"), art.mode_icon(False, 44)),
                (GameMode.TWO_PLAYERS.value, resources.text("ui.mode_two_players"), art.mode_icon(True, 44)),
            ],
            selected=mode.value,
            on_select=on_mode,
        )
        self.banner: PromptBanner = kit.prompt_banner("turn", pygame.Rect(0, 0, 300, 60), text="")
        self.progress: ProgressDots = kit.progress_dots("games", pygame.Rect(0, 0, 10, 10), total=GAMES_PER_MATCH)
        self.next_game: IconButton = kit.icon_button(
            "next_game",
            pygame.Rect(0, 0, 10, 10),
            icon=kit.glyph("go", 76),
            shape=BodyShape.ROUND,
            role=ButtonRole.PRIMARY,
            on_activate=on_next,
        )
        self.next_game.visible = False
        self.keys: KeyboardHint = kit.keyboard_hint("keys", key_hint_rect(), active=KEY_HINT_KEYS, clock=clock)
        self.layer: ControlLayer = kit.layer(layer_id="quattro.controls")
        self._layout = layout
        self.set_geometry(geometry)
        self.relayout(layout)

    # -- geometry -------------------------------------------------------------------

    def set_geometry(self, geometry: BoardGeometry) -> None:
        """Rebuild the column targets for a stage board (once per stage)."""

        self.geometry = geometry
        self.columns = tuple(
            ExternalTarget(column_id(col), geometry.column_rect(col), (lambda c=col: self._on_column(c)), focus_radius=18)
            for col in range(geometry.cols)
        )
        self.next_game.rect = next_button_rect(geometry)
        self.layer.set_targets((*self.columns, *self.mode.controls, self.banner, self.progress, self.next_game, self.keys))

    def relayout(self, layout: ControlLayout) -> None:
        """Top bar beside protected chrome: who-plays strip, turn banner, games."""

        self._layout = layout
        height = layout.control_height(60, maximum=72)
        bar = layout.top_bar(height)
        dots_h = max(34, int(height * 0.66))
        dots_w = ProgressDots.preferred_width(GAMES_PER_MATCH, dots_h)
        slots = self.mode.controls
        for slot in slots:
            # A two-picture toggle (Leo / two hands): icons are the language here,
            # so the strip stays compact and the turn banner gets the room.
            slot.rect = pygame.Rect(0, 0, 10, height)
            slot.compact = True
        widths = [max(slot.compact_width(), int(height * 1.35)) for slot in slots]
        strip_w = sum(widths) + layout.gap * (len(widths) - 1)
        banner_w = bar.width - strip_w - dots_w - 2 * layout.gap
        rects = layout.row(bar, [*widths, banner_w, dots_w], height=height)
        for slot, rect in zip(slots, rects):
            slot.rect = rect
        self.banner.rect = rects[len(slots)]
        dots = rects[-1]
        self.progress.rect = pygame.Rect(dots.x, dots.centery - dots_h // 2, dots_w, dots_h)
        self.layer.invalidation.invalidate()

    # -- state sync -------------------------------------------------------------------

    def sync(
        self,
        *,
        columns_live: bool,
        mode_live: bool,
        between_games: bool,
        games_played: int,
        banner_text: str,
        banner_icon: pygame.Surface | None,
    ) -> None:
        for target in self.columns:
            target.enabled = columns_live
        for slot in self.mode.controls:
            slot.enabled = mode_live
        self.next_game.visible = between_games
        self.next_game.enabled = between_games
        self.progress.set_progress(games_played)
        if banner_text != self.banner.text or banner_icon is not self.banner.icon:
            self.banner.text = banner_text
            self.banner.icon = banner_icon
        if not self._focused_is_live():
            self.focus_default(None)
        self.layer.invalidation.invalidate()

    def select_mode(self, mode: GameMode) -> None:
        self.mode.select(mode.value)

    def focus_column(self, col: int) -> None:
        if 0 <= col < len(self.columns) and self.columns[col].enabled:
            self.layer.focus(column_id(col))

    def focus_default(self, col: int | None) -> None:
        if self.next_game.visible and self.next_game.enabled:
            self.layer.focus(self.next_game.control_id)
        elif col is not None:
            self.focus_column(col)
        self.layer.ensure_focus()

    def focused_column(self) -> int | None:
        return column_of(self.layer.focused_id)

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        target = self.layer.target(focused)
        return target.focusable and target.enabled


__all__ = ["QuattroControls", "column_id", "column_of"]

"""Shared control-kit wiring for The Big Seasons Tree (ADR 0037).

The scene is the Activity's own drawing; every interactive element is a kit
control, so pointer, touch, keyboard, D-pad/stick and the south button all
work the same way and share one focus ring:

* the season picker is four ``IconButton`` tiles (emblem + season name);
* each mission's picture cards are ``IconButton`` tiles (pictures only);
* the mission prompt is a ``PromptBanner`` (what is being dressed + the
  season, with a listen button that replays Tito's season clip);
* round progress is ``ProgressDots``.

Focus never jumps to the right card: a new mission focuses the first card.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ControlKit,
    ControlLayer,
    ControlLayout,
    IconButton,
    ProgressDots,
    PromptBanner,
)

if __package__:
    from .tree_content import SEASONS, Season
    from .tree_layout import BANNER_HEIGHT, BANNER_WIDTH, CARD_SIZE, TILE_SIZE, row_rects
else:
    from tree_content import SEASONS, Season
    from tree_layout import BANNER_HEIGHT, BANNER_WIDTH, CARD_SIZE, TILE_SIZE, row_rects

MAX_CARDS = 4


def card_id(index: int) -> str:
    return f"card.{index}"


def tile_id(season: Season) -> str:
    return f"season.{season.value}"


class TreeControls:
    """Own the kit controls and the single ``ControlLayer`` of the Activity."""

    def __init__(
        self,
        kit: ControlKit,
        *,
        on_card: Callable[[int], object],
        on_season: Callable[[Season], object],
        on_listen: Callable[[], object],
    ) -> None:
        self._kit = kit
        self.cards: tuple[IconButton, ...] = tuple(
            kit.icon_button(card_id(index), pygame.Rect((0, 0), CARD_SIZE), icon=None, shape=BodyShape.TILE,
                            on_activate=(lambda i=index: on_card(i)))
            for index in range(MAX_CARDS)
        )
        self.tiles: dict[Season, IconButton] = {
            season: kit.icon_button(tile_id(season), rect, icon=None, shape=BodyShape.TILE,
                                    on_activate=(lambda s=season: on_season(s)))
            for season, rect in zip(SEASONS, row_rects(len(SEASONS), TILE_SIZE))
        }
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 120, 44), total=3)
        self.banner: PromptBanner = kit.prompt_banner(
            "prompt",
            pygame.Rect(0, 0, BANNER_WIDTH, BANNER_HEIGHT),
            replay_icon=kit.glyph("listen", 34),
            on_replay=on_listen,
        )
        self.layer: ControlLayer = kit.layer((), layer_id="seasons.controls")
        self._layout: ControlLayout | None = None
        self._card_count = 0
        self._card_rects: tuple[pygame.Rect, ...] = ()

    # -- layout -----------------------------------------------------------------

    def place_bar(self, layout: ControlLayout) -> None:
        """Remember the layout (outside protected chrome) and lay the top bar."""

        self._layout = layout
        self._layout_bar()

    def _layout_bar(self) -> None:
        """Progress dots beside the protected chrome, the prompt banner centred."""

        layout = self._layout
        if layout is None:
            return
        height = layout.control_height(BANNER_HEIGHT, maximum=84)
        bar = layout.top_bar(height)
        dots_h = max(36, int(height * 0.6))
        dots_w = ProgressDots.preferred_width(self.progress.total, dots_h)
        self.progress.rect = pygame.Rect(bar.left, bar.centery - dots_h // 2, dots_w, dots_h)
        free_left = self.progress.rect.right + layout.gap * 2 if self.progress.visible else bar.left
        width = max(120, min(BANNER_WIDTH, bar.right - free_left))
        centre = max(free_left + width // 2, layout.width // 2)
        centre = min(centre, bar.right - width // 2)
        rect = pygame.Rect(0, 0, width, height)
        rect.center = (centre, bar.centery)
        self.banner.rect = rect

    # -- modes --------------------------------------------------------------------

    def show_picker(self, emblems: dict[Season, pygame.Surface], names: dict[Season, str], focus: Season, prompt: str) -> None:
        for season, tile in self.tiles.items():
            tile.icon = emblems[season]
            tile.caption = names[season]
            tile.visible = True
            tile.enabled = True
        for card in self.cards:
            card.visible = False
        self.banner.set_text(prompt, icon=None)
        self.banner.icon = None
        if self.banner.replay is not None:
            self.banner.replay.visible = False
        self.progress.visible = False
        self._layout_bar()
        self.layer.set_targets((*self.tiles.values(), *self.banner.controls))
        self.layer.focus(tile_id(focus), visible=self.layer.focus_visible)
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def start_round(self, total: int) -> None:
        self.progress.total = max(1, int(total))
        self.progress.set_progress(0)
        self.progress.visible = True
        self._layout_bar()
        for tile in self.tiles.values():
            tile.visible = False

    def show_cards(self, icons: Sequence[pygame.Surface], prompt: str, prompt_icon: pygame.Surface | None, *, voiced: bool) -> None:
        """A new mission: ``icons`` in card order; focus the first card."""

        visible = self.layer.focus_visible
        self._card_count = min(MAX_CARDS, len(icons))
        rects = row_rects(self._card_count, CARD_SIZE)
        self._card_rects = rects
        for index, card in enumerate(self.cards):
            if index < self._card_count:
                card.icon = icons[index]
                card.rect = rects[index]
                card.visible = True
                card.enabled = True
            else:
                card.visible = False
        self.banner.set_text(prompt, icon=prompt_icon)
        if self.banner.replay is not None:
            self.banner.replay.visible = voiced
        self.layer.set_targets((*self.cards[: self._card_count], self.progress, *self.banner.controls))
        self.layer.focus(card_id(0), visible=visible)
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def hide_cards(self) -> None:
        for card in self.cards:
            card.visible = False
        self.layer.set_targets((self.progress, *self.banner.controls))
        self.layer.invalidation.invalidate()

    def disable_card(self, index: int) -> None:
        if 0 <= index < self._card_count:
            self.cards[index].enabled = False
            if self.layer.focused_id == card_id(index):
                self.layer.focused_id = None
                for other in range(self._card_count):
                    if self.cards[other].enabled:
                        self.layer.focus(card_id(other))
                        break
            self.layer.invalidation.invalidate()

    def tell(self, text: str, icon: pygame.Surface | None) -> None:
        """Show what was placed (picture + name) in the banner."""

        self.banner.set_text(text, icon=icon)
        if icon is None:
            self.banner.icon = None
        self.layer.invalidation.invalidate()

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()

    @property
    def card_count(self) -> int:
        return self._card_count

    def card_rect(self, index: int) -> pygame.Rect:
        """The card's resting rect (hops never move its hit area for long)."""

        return self._card_rects[index].copy() if index < len(self._card_rects) else self.cards[index].rect

    def nudge_card(self, index: int, dy: int) -> None:
        """Lift a card by ``dy`` for a hint hop (position only; no re-render)."""

        if index < len(self._card_rects):
            self.cards[index].rect = self._card_rects[index].move(0, dy)


__all__ = ["MAX_CARDS", "TreeControls", "card_id", "tile_id"]

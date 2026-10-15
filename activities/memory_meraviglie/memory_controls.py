"""Shared control-kit wiring for Wonder Match (ADR 0037).

The Activity draws its own cards, but every interactive element goes through
``greia_platform.activity_controls``: cards are ``ExternalTarget``s (pointer
activation plus keyboard / D-pad / stick focus and the shared focus ring), the
album covers on the picker are kit ``IconButton`` tiles showing pictures (no
words), the round album button on the board shows the album's picture, and
board progress is ``ProgressDots`` (one dot per pair). Rules stay in
``MemoryBoard``; this class maps controls to app callbacks and mirrors state.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ControlKit,
    ControlLayer,
    ExternalTarget,
    IconButton,
    ProgressDots,
)

if __package__:
    from .memory_art import MemoryArt
    from .memory_content import ALBUMS, Album
    from .memory_layout import BoardLayout, PickerLayout
    from .memory_model import CardState, MemoryBoard, StickerBook
else:
    from memory_art import MemoryArt
    from memory_content import ALBUMS, Album
    from memory_layout import BoardLayout, PickerLayout
    from memory_model import CardState, MemoryBoard, StickerBook


def card_id(index: int) -> str:
    return f"card.{index}"


def album_id_of(control_id: str) -> str:
    return control_id.split(".", 1)[1]


class MemoryControls:
    """Own the kit controls and the single ``ControlLayer`` of both screens."""

    def __init__(
        self,
        kit: ControlKit,
        art: MemoryArt,
        *,
        on_card: Callable[[int], object],
        on_album: Callable[[str], object],
        on_albums: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self._on_card = on_card
        self._on_album = on_album
        self.cards: tuple[ExternalTarget, ...] = ()
        self.albums: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                f"album.{album.album_id}",
                pygame.Rect(0, 0, 200, 200),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda chosen=album.album_id: on_album(chosen)),
            )
            for album in ALBUMS
        )
        self.album_button: IconButton = kit.icon_button(
            "albums",
            pygame.Rect(0, 0, 68, 68),
            icon=None,
            on_activate=on_albums,
        )
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 40, 40), total=2)
        self.layer: ControlLayer = kit.layer((), layer_id="memory.controls")
        self._album_shown: str | None = None

    # -- picker ---------------------------------------------------------------

    def show_picker(self, layout: PickerLayout, book: StickerBook, focus_album: str) -> None:
        for button, album, rect in zip(self.albums, ALBUMS, layout.tiles):
            button.rect = rect
            count = book.count(album.album_id)
            button.icon = self._art.album_cover(album, rect.width, count, self._kit.star)
        self.cards = ()
        self.layer.set_targets(self.albums)
        self.layer.focus(f"album.{focus_album}")
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    # -- board ------------------------------------------------------------------

    def show_board(self, layout: BoardLayout, album: Album, board: MemoryBoard) -> None:
        self.cards = tuple(
            ExternalTarget(card_id(index), rect, (lambda i=index: self._on_card(i)), focus_radius=16)
            for index, rect in enumerate(layout.cards[: len(board.cards)])
        )
        self.album_button.rect = layout.album_button
        if self._album_shown != album.album_id:
            self.album_button.icon = self._art.album_badge(album, int(layout.album_button.width * 0.78))
            self._album_shown = album.album_id
        self.progress.total = board.pairs
        dots_width = ProgressDots.preferred_width(board.pairs, layout.dots.height)
        self.progress.rect = pygame.Rect(layout.dots.x, layout.dots.y, dots_width, layout.dots.height)
        self.layer.set_targets((*self.cards, self.album_button, self.progress))
        self.layer.focus(card_id(0))
        self.sync(board)

    def relayout_board(self, layout: BoardLayout, album: Album, board: MemoryBoard) -> None:
        """Rebuild card targets for a new geometry, keeping the focused card."""

        focused, visible = self.layer.focused_id, self.layer.focus_visible
        self.show_board(layout, album, board)
        if focused is not None:
            self.layer.focus(focused, visible=visible)
        self.layer.ensure_focus()

    def sync(self, board: MemoryBoard) -> None:
        """Mirror the board into card enablement (cheap; called on changes)."""

        for target, card in zip(self.cards, board.cards):
            target.enabled = card.state is not CardState.MATCHED
        self.progress.set_progress(board.matched)
        if not self._focused_is_live():
            self.focus_next_card(board)
        self.layer.invalidation.invalidate()

    def focus_next_card(self, board: MemoryBoard, after: int = -1) -> None:
        count = len(self.cards)
        for step in range(1, count + 1):
            index = (after + step) % count
            if board.cards[index].state is not CardState.MATCHED:
                self.layer.focus(card_id(index))
                return
        self.layer.ensure_focus()

    def focused_card(self) -> int | None:
        focused = self.layer.focused_id
        if focused is None or not focused.startswith("card."):
            return None
        return int(focused.split(".", 1)[1])

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        try:
            target = self.layer.target(focused)
        except KeyError:
            return False
        return target.focusable and target.enabled

    def card_rects(self) -> Sequence[pygame.Rect]:
        return tuple(target.rect for target in self.cards)


__all__ = ["MemoryControls", "album_id_of", "card_id"]

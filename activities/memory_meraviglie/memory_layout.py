"""Geometry for Wonder Match in 1024x600 logical pixels.

The board screen has three zones: Lilli on the lawn at the bottom left, the
card grid in the middle and Lilli's sticker page (eight wells, one per album
picture) on the right, under the round album button. The album picker shows
five big album covers beside Lilli. Every zone is computed from the platform
protected Home/Back rectangle (mapped into logical space by
``ControlLayout.for_canvas``), so nothing enters it at any resolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

if __package__:
    from .memory_content import ALBUM_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH, GridSpec
else:
    from memory_content import ALBUM_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH, GridSpec

CARD_ASPECT: Final = 232 / 256  # card art canvas (incl. its lip shadow)
CARD_MAX_WIDTH: Final = 176
MARGIN: Final = 12
LILLI_HEIGHT: Final = 210
LILLI_MIDBOTTOM: Final[tuple[int, int]] = (106, REFERENCE_HEIGHT - 6)
GRID_LEFT: Final = 214
PANEL_WIDTH: Final = 184
PANEL_LEFT: Final = REFERENCE_WIDTH - MARGIN - PANEL_WIDTH
GRID_RIGHT: Final = PANEL_LEFT - 14
DOTS_HEIGHT: Final = 40
ALBUM_BUTTON: Final = 68
# The face picture sits on the card's inner mat (card_face.svg 20..212 x 20..232).
PICTURE_SCALE: Final = 0.74
PICTURE_CENTER: Final[tuple[float, float]] = (116 / 232, 128 / 256)


@dataclass(frozen=True, slots=True)
class BoardLayout:
    cards: tuple[pygame.Rect, ...]
    card_size: tuple[int, int]
    grid: pygame.Rect
    panel: pygame.Rect
    wells: tuple[pygame.Rect, ...]
    sticker_size: int
    album_button: pygame.Rect
    dots: pygame.Rect

    @classmethod
    def build(cls, spec: GridSpec, protected: pygame.Rect, *, album_button_size: int = ALBUM_BUTTON) -> "BoardLayout":
        button = pygame.Rect(
            REFERENCE_WIDTH - MARGIN - album_button_size - (PANEL_WIDTH - album_button_size) // 2,
            MARGIN,
            album_button_size,
            album_button_size,
        )
        top = max(88, protected.bottom + 10) if protected.right > GRID_LEFT else 88
        grid_area = pygame.Rect(GRID_LEFT, top, GRID_RIGHT - GRID_LEFT, REFERENCE_HEIGHT - 10 - top)
        gap = 12 if spec.rows >= 4 else 14
        width_limit = (grid_area.width - (spec.cols - 1) * gap) / spec.cols
        height_limit = (grid_area.height - (spec.rows - 1) * gap) / spec.rows
        card_w = int(min(CARD_MAX_WIDTH, width_limit, height_limit * CARD_ASPECT))
        card_h = int(card_w / CARD_ASPECT)
        grid_w = spec.cols * card_w + (spec.cols - 1) * gap
        grid_h = spec.rows * card_h + (spec.rows - 1) * gap
        left = grid_area.centerx - grid_w // 2
        top_y = grid_area.centery - grid_h // 2
        cards = tuple(
            pygame.Rect(left + column * (card_w + gap), top_y + row * (card_h + gap), card_w, card_h)
            for row in range(spec.rows)
            for column in range(spec.cols)
        )
        panel_top = max(button.bottom + 10, protected.bottom + 10 if protected.right > PANEL_LEFT else 0)
        panel = pygame.Rect(PANEL_LEFT, panel_top, PANEL_WIDTH, REFERENCE_HEIGHT - 10 - panel_top)
        wells, sticker = _wells(panel)
        dots_left = protected.right + 14
        dots = pygame.Rect(dots_left, MARGIN + (album_button_size - DOTS_HEIGHT) // 2, 10, DOTS_HEIGHT)
        return cls(cards, (card_w, card_h), pygame.Rect(left, top_y, grid_w, grid_h), panel, wells, sticker, button, dots)


def _wells(panel: pygame.Rect) -> tuple[tuple[pygame.Rect, ...], int]:
    pad = 12
    columns, rows = 2, ALBUM_SIZE // 2
    gap = 8
    cell_w = (panel.width - 2 * pad - gap) // columns
    cell_h = (panel.height - 2 * pad - (rows - 1) * gap) // rows
    size = min(cell_w, cell_h)
    total_h = rows * size + (rows - 1) * gap
    top = panel.top + (panel.height - total_h) // 2
    left = panel.centerx - (columns * size + gap) // 2
    wells = tuple(
        pygame.Rect(left + column * (size + gap), top + row * (size + gap), size, size)
        for row in range(rows)
        for column in range(columns)
    )
    return wells, int(size * 0.86)


@dataclass(frozen=True, slots=True)
class PickerLayout:
    tiles: tuple[pygame.Rect, ...]
    tile_size: int

    @classmethod
    def build(cls, count: int, protected: pygame.Rect) -> "PickerLayout":
        left_edge = 238
        top = max(92, protected.bottom + 12)
        area = pygame.Rect(left_edge, top, REFERENCE_WIDTH - MARGIN - left_edge, REFERENCE_HEIGHT - 12 - top)
        gap = 22
        per_row = (count + 1) // 2
        size = int(min(214, (area.width - (per_row - 1) * gap) / per_row, (area.height - gap) / 2))
        tiles: list[pygame.Rect] = []
        total_h = 2 * size + gap
        y0 = area.top + (area.height - total_h) // 2
        for row, in_row in enumerate((per_row, count - per_row)):
            row_w = in_row * size + (in_row - 1) * gap
            x0 = area.centerx - row_w // 2
            for column in range(in_row):
                tiles.append(pygame.Rect(x0 + column * (size + gap), y0 + row * (size + gap), size, size))
        return cls(tuple(tiles), size)


def picture_rect(card: pygame.Rect) -> pygame.Rect:
    """Where the subject picture sits on a card of ``card`` size."""

    size = int(min(card.width, card.height * CARD_ASPECT) * PICTURE_SCALE)
    center = (card.x + int(card.width * PICTURE_CENTER[0]), card.y + int(card.height * PICTURE_CENTER[1]))
    return pygame.Rect(center[0] - size // 2, center[1] - size // 2, size, size)


__all__ = [
    "BoardLayout",
    "CARD_ASPECT",
    "LILLI_HEIGHT",
    "LILLI_MIDBOTTOM",
    "PickerLayout",
    "picture_rect",
]

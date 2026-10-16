"""Screen geometry for Fluffy Monsters in 1024x600 logical pixels.

``protected`` is the platform Home/Back chrome mapped into this logical space
by ``ControlLayout.for_canvas`` (largest at 480x320, where it reaches x 239 /
y 87). Top-bar controls start right of it and every other row starts below
y 100, so nothing ever sits under the protected region. Rects are computed once
per viewport, never per frame. Drawer and option tiles stay >= 88 logical px
(>= 40 physical px at 480x320).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pygame

if __package__:
    from .monster_content import CATEGORY_ORDER, GALLERY_PAGE_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH
else:
    from monster_content import CATEGORY_ORDER, GALLERY_PAGE_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH

MARGIN: Final = 12
CONTENT_TOP: Final = 100
DRAWER_TILE: Final = 88
GAP: Final = 8


@dataclass(frozen=True, slots=True)
class TopBar:
    """One row of square buttons beside the protected chrome."""

    bar: pygame.Rect

    @classmethod
    def build(cls, protected: pygame.Rect, height: int) -> "TopBar":
        left = protected.right + 14
        top = max(6, (CONTENT_TOP - height) // 2 - 2)
        return cls(pygame.Rect(left, top, REFERENCE_WIDTH - MARGIN - left, height))

    def left(self, index: int, size: int, gap: int = 12) -> pygame.Rect:
        return pygame.Rect(self.bar.left + index * (size + gap), self.bar.top, size, size)

    def right(self, index: int, size: int, gap: int = 12) -> pygame.Rect:
        """``index`` 0 is the right-most slot."""

        return pygame.Rect(self.bar.right - (index + 1) * size - index * gap, self.bar.top, size, size)


def grid(area: pygame.Rect, count: int, columns: int, *, max_tile: int, gap: int = 10) -> tuple[pygame.Rect, ...]:
    """``count`` square tiles in ``columns`` columns, as large as fit ``area``."""

    rows = max(1, (count + columns - 1) // columns)
    tile = min(
        max_tile,
        (area.width - gap * (columns - 1)) // columns,
        (area.height - gap * (rows - 1)) // rows,
    )
    width = columns * tile + (columns - 1) * gap
    height = rows * tile + (rows - 1) * gap
    left = area.centerx - width // 2
    top = area.top + max(0, (area.height - height) // 2)
    return tuple(
        pygame.Rect(left + (index % columns) * (tile + gap), top + (index // columns) * (tile + gap), tile, tile)
        for index in range(count)
    )


def plate_between(left: pygame.Rect, right: pygame.Rect, *, width: int = 320, height: int = 60) -> pygame.Rect:
    """The name plate, centred in the top bar between two button groups."""

    room = right.left - left.right - 24
    plate = pygame.Rect(0, 0, max(120, min(width, room)), height)
    plate.center = ((left.right + right.left) // 2, left.centery)
    return plate


@dataclass(frozen=True, slots=True)
class StudioLayout:
    """Drawers left, the monster's stage centre, option tiles right."""

    top: TopBar
    undo: pygame.Rect
    surprise: pygame.Rect
    save: pygame.Rect
    gallery: pygame.Rect
    drawers: tuple[pygame.Rect, ...]  # nine part drawers + the name drawer
    stage: pygame.Rect
    tray: pygame.Rect
    monster_midbottom: tuple[int, int]
    monster_height: int
    host_midbottom: tuple[int, int]
    host_height: int
    name_plate: pygame.Rect

    @classmethod
    def build(cls, protected: pygame.Rect, *, button: int) -> "StudioLayout":
        top = TopBar.build(protected, button)
        column = pygame.Rect(MARGIN, CONTENT_TOP, 2 * DRAWER_TILE + GAP, REFERENCE_HEIGHT - MARGIN - CONTENT_TOP)
        drawers = grid(column, len(CATEGORY_ORDER) + 1, 2, max_tile=DRAWER_TILE, gap=GAP)
        tray = pygame.Rect(REFERENCE_WIDTH - MARGIN - 240, CONTENT_TOP, 240, REFERENCE_HEIGHT - MARGIN - CONTENT_TOP)
        stage = pygame.Rect(column.right + 12, CONTENT_TOP, tray.left - 12 - (column.right + 12), column.height)
        surprise = top.left(1, button)
        save = top.right(1, button)
        return cls(
            top=top,
            undo=top.left(0, button),
            surprise=surprise,
            save=save,
            gallery=top.right(0, button),
            drawers=drawers,
            stage=stage,
            tray=tray,
            monster_midbottom=(stage.centerx + 40, stage.bottom - 2),
            monster_height=436,
            host_midbottom=(stage.left + 66, stage.bottom - 8),
            host_height=150,
            name_plate=plate_between(surprise, save),
        )

    def tiles(self, count: int) -> tuple[pygame.Rect, ...]:
        return grid(self.tray, count, 2, max_tile=112, gap=12)


@dataclass(frozen=True, slots=True)
class GalleryLayout:
    """Saved friends as big cards (3x2 per page) with page arrows beside them."""

    top: TopBar
    back: pygame.Rect
    chip: pygame.Rect
    cards: tuple[pygame.Rect, ...]
    previous: pygame.Rect
    next: pygame.Rect
    dots_centre: tuple[int, int]
    empty: pygame.Rect

    @classmethod
    def build(cls, protected: pygame.Rect, *, button: int) -> "GalleryLayout":
        top = TopBar.build(protected, button)
        arrow_w = 84
        grid_area = pygame.Rect(MARGIN + arrow_w + 14, CONTENT_TOP + 22, REFERENCE_WIDTH - 2 * (MARGIN + arrow_w + 14), REFERENCE_HEIGHT - MARGIN - CONTENT_TOP - 22)
        gap_x, gap_y = 22, 34
        width = (grid_area.width - 2 * gap_x) // 3
        height = (grid_area.height - gap_y) // 2
        cards = tuple(
            pygame.Rect(grid_area.left + col * (width + gap_x), grid_area.top + row * (height + gap_y), width, height)
            for row in range(2)
            for col in range(3)
        )[:GALLERY_PAGE_SIZE]
        arrow_h = 132
        previous = pygame.Rect(MARGIN, grid_area.centery - arrow_h // 2, arrow_w, arrow_h)
        following = pygame.Rect(REFERENCE_WIDTH - MARGIN - arrow_w, grid_area.centery - arrow_h // 2, arrow_w, arrow_h)
        back = top.left(0, button)
        chip = pygame.Rect(top.bar.right - 170, top.bar.top + 10, 170, button - 20)
        return cls(
            top=top,
            back=back,
            chip=chip,
            cards=cards,
            previous=previous,
            next=following,
            dots_centre=((back.right + chip.left) // 2, back.centery),
            empty=pygame.Rect(grid_area.centerx - 220, grid_area.top + 30, 440, 300),
        )


@dataclass(frozen=True, slots=True)
class FriendLayout:
    """One saved friend (or the just-saved one), big on its stage."""

    top: TopBar
    back: pygame.Rect
    share: pygame.Rect
    delete: pygame.Rect
    stage: pygame.Rect
    monster_midbottom: tuple[int, int]
    monster_height: int
    host_midbottom: tuple[int, int]
    host_height: int
    name_plate: pygame.Rect
    new: pygame.Rect
    gallery: pygame.Rect

    @classmethod
    def build(cls, protected: pygame.Rect, *, button: int) -> "FriendLayout":
        top = TopBar.build(protected, button)
        stage = pygame.Rect(MARGIN + 8, CONTENT_TOP, REFERENCE_WIDTH - 2 * (MARGIN + 8), REFERENCE_HEIGHT - MARGIN - CONTENT_TOP)
        size = max(button, 96)
        new = pygame.Rect(0, 0, size + 24, size)
        new.bottomright = (stage.right - 24, stage.bottom - 20)
        gallery = pygame.Rect(0, 0, size, size)
        gallery.bottomright = (new.left - 16, new.bottom)
        back = top.left(0, button)
        share = top.right(1, button)
        return cls(
            top=top,
            back=back,
            share=share,
            delete=top.right(0, button),
            stage=stage,
            monster_midbottom=(stage.centerx, stage.bottom - 2),
            monster_height=470,
            host_midbottom=(stage.left + 110, stage.bottom - 10),
            host_height=200,
            name_plate=plate_between(back, share, width=360),
            new=new,
            gallery=gallery,
        )


@dataclass(frozen=True, slots=True)
class SheetLayout:
    """A centred modal panel: preview on top, two choices below."""

    panel: pygame.Rect
    preview: pygame.Rect
    left: pygame.Rect
    right: pygame.Rect

    @classmethod
    def build(cls, protected: pygame.Rect) -> "SheetLayout":
        top = max(CONTENT_TOP - 4, protected.bottom + 10)
        height = min(440, REFERENCE_HEIGHT - MARGIN - top)
        panel = pygame.Rect(0, 0, 460, height)
        panel.midtop = (REFERENCE_WIDTH // 2, top)
        button = 104
        y = panel.bottom - 20 - button
        preview_side = y - 16 - (panel.top + 16)
        preview = pygame.Rect(0, 0, preview_side, preview_side)
        preview.midtop = (panel.centerx, panel.top + 16)
        left = pygame.Rect(panel.centerx - 24 - button, y, button, button)
        right = pygame.Rect(panel.centerx + 24, y, button, button)
        return cls(panel, preview, left, right)


__all__ = [
    "CONTENT_TOP",
    "DRAWER_TILE",
    "FriendLayout",
    "GalleryLayout",
    "SheetLayout",
    "StudioLayout",
    "TopBar",
    "grid",
    "plate_between",
]

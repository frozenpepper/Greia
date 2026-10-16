"""Shared control-kit wiring for My Greia (ADR 0037).

Layout (reference canvas, outside the protected Home/Back chrome):

* top bar beside the chrome: four picture tabs (a ``ToolStrip`` of square
  tiles: my avatar, my colours, my pictures, big/small letters) and an undo
  arrow at the far end;
* left: the live Home preview (drawn by ``HomePreview``; not focusable);
* right: a cream panel with big picture choices for the current tab, each a
  kit ``IconButton`` tile. The chosen tile is accent-filled and carries the
  shared check glyph.

Keyboard / D-pad / stick move focus between tabs, tiles and undo; Space /
Enter / south button choose; pointer and touch tap directly. This class only
maps controls to app callbacks and mirrors the model into them.
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
    IconButton,
    ToolStrip,
)

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_art import MyGreiaArt
    from .workshop_content import CUSTOM_CHOICE, REFERENCE_HEIGHT, REFERENCE_WIDTH, TABS, Tab
    from .workshop_model import ChoiceKind, Look
    from .workshop_services import MyGreiaChoices
except ImportError:
    from workshop_art import MyGreiaArt  # type: ignore[no-redef]
    from workshop_content import CUSTOM_CHOICE, REFERENCE_HEIGHT, REFERENCE_WIDTH, TABS, Tab  # type: ignore[no-redef]
    from workshop_model import ChoiceKind, Look  # type: ignore[no-redef]
    from workshop_services import MyGreiaChoices  # type: ignore[no-redef]

TAB_STRIP_ID = "tabs"
UNDO_ID = "undo"
PREVIEW_ASPECT = REFERENCE_HEIGHT / REFERENCE_WIDTH


def tile_id(kind: ChoiceKind, value: str) -> str:
    return f"{kind.value}.{value}"


def tab_id(tab: Tab) -> str:
    return f"{TAB_STRIP_ID}.{tab.value}"


@dataclass(frozen=True, slots=True)
class Geometry:
    """Resolved reference-canvas rectangles for one viewport."""

    bar: pygame.Rect
    preview: pygame.Rect
    panel: pygame.Rect
    tab_size: int


def compute_geometry(layout: ControlLayout) -> Geometry:
    tab_size = layout.control_height(72, maximum=96)
    bar = layout.top_bar(tab_size)
    top = max(bar.bottom + 18, layout.protected.bottom + layout.gap)
    bottom = layout.height - layout.margin
    content = pygame.Rect(layout.margin, top, layout.width - 2 * layout.margin, max(1, bottom - top))
    preview_w = min(int(content.width * 0.58), int(content.height / PREVIEW_ASPECT))
    preview_h = round(preview_w * PREVIEW_ASPECT)
    preview = pygame.Rect(content.x + 6, content.centery - preview_h // 2, preview_w, preview_h)
    panel_x = preview.right + 22
    panel = pygame.Rect(panel_x, content.y, content.right - panel_x, content.height)
    return Geometry(bar=bar, preview=preview, panel=panel, tab_size=tab_size)


class MyGreiaControls:
    """Own the kit controls and the ``ControlLayer`` of the My Greia screen."""

    PANEL_PAD = 14
    GAP = 10

    def __init__(
        self,
        kit: ControlKit,
        art: MyGreiaArt,
        layout: ControlLayout,
        choices: MyGreiaChoices,
        *,
        on_tab: Callable[[Tab], object],
        on_choice: Callable[[ChoiceKind, str], object],
        on_undo: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self._choices = choices
        self._on_choice = on_choice
        self.tabs = ToolStrip(
            kit.painter,
            TAB_STRIP_ID,
            [(tab.value, "", None) for tab in TABS],
            shape=BodyShape.TILE,
            on_select=lambda chosen: on_tab(Tab(chosen)),
        )
        self.undo: IconButton = kit.icon_button(UNDO_ID, pygame.Rect(0, 0, 64, 64), icon=None, on_activate=on_undo)
        self.tiles: list[IconButton] = []
        self._tile_values: dict[str, tuple[ChoiceKind, str]] = {}
        self.layer: ControlLayer = kit.layer((*self.tabs.controls, self.undo), layer_id="my_greia.controls")
        self.geometry = compute_geometry(layout)
        self._tab: Tab = TABS[0]
        self._look: Look | None = None
        self._custom = False
        self._tab_icon_keys: dict[Tab, tuple] = {}
        self._can_undo = False
        self.custom_path = None
        self._apply_bar_geometry()

    # -- geometry ---------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        self.geometry = compute_geometry(layout)
        self._apply_bar_geometry()
        self._tab_icon_keys.clear()
        if self._look is not None:
            self.show(self._tab, self._look, custom=self._custom, keep_focus=True)

    def _apply_bar_geometry(self) -> None:
        g = self.geometry
        size = g.tab_size
        for index, slot in enumerate(self.tabs.controls):
            slot.rect = pygame.Rect(g.bar.x + index * (size + 14), g.bar.y, size, size)
        self.undo.rect = pygame.Rect(g.bar.right - size, g.bar.y, size, size)
        self.undo.icon = self._kit.glyph("undo", round(size * 0.6))
        self.layer.invalidation.invalidate()

    # -- tabs + tiles ----------------------------------------------------------------

    def show(self, tab: Tab, look: Look, *, custom: bool = False, keep_focus: bool = False) -> None:
        """Rebuild the choice tiles for ``tab`` and mirror ``look`` into them."""

        self._tab = tab
        self._look = look
        self._custom = custom
        self.tabs.select(tab.value)
        builders = {
            Tab.ME: self._avatar_tiles,
            Tab.COLOURS: self._colour_tiles,
            Tab.PICTURES: self._picture_tiles,
            Tab.SIZE: self._size_tiles,
        }
        focused = self.layer.focused_id
        self.tiles = builders[tab](look)
        self._tile_values = {tile.control_id: self._value_of(tile) for tile in self.tiles}
        self.layer.set_targets((*self.tabs.controls, *self.tiles, self.undo))
        self.sync(look, can_undo=self._can_undo)
        if keep_focus and focused is not None and focused in self._tile_values:
            self.layer.focus(focused)
        elif focused is None or focused not in {c.control_id for c in self.layer.targets}:
            self.layer.focus(tab_id(tab))
        self.layer.invalidation.invalidate()

    def _value_of(self, tile: IconButton) -> tuple[ChoiceKind, str]:
        kind, _, value = tile.control_id.partition(".")
        return ChoiceKind(kind), value

    def tile_value(self, control_id: str) -> tuple[ChoiceKind, str] | None:
        return self._tile_values.get(control_id)

    def sync(self, look: Look, *, can_undo: bool = False) -> None:
        """Mirror the current look: selected tiles, tab pictures, undo."""

        self._look = look
        self._can_undo = can_undo
        for tile in self.tiles:
            kind, value = self._tile_values.get(tile.control_id, (None, None))
            selected = kind is not None and look.value(kind) == value
            if tile.selected != selected:
                tile.selected = selected
        self.undo.enabled = can_undo
        self._refresh_tab_icons(look)
        self.layer.invalidation.invalidate()

    def _refresh_tab_icons(self, look: Look) -> None:
        size = round(self.geometry.tab_size * 0.74)
        room = self._choices.background(look.background)
        accent = self._choices.accent(look.accent)
        wanted = {
            Tab.ME: ("me", look.avatar, size),
            Tab.COLOURS: ("colours", room, accent, size),
            Tab.PICTURES: ("pictures", size),
            Tab.SIZE: ("size", size),
        }
        for slot, tab in zip(self.tabs.controls, TABS):
            key = wanted[tab]
            if self._tab_icon_keys.get(tab) == key:
                continue
            self._tab_icon_keys[tab] = key
            if tab is Tab.ME:
                slot.icon = self._art.icon(look.avatar, size)
            elif tab is Tab.COLOURS:
                slot.icon = self._art.tab_colours_icon(size, room, accent)
            elif tab is Tab.PICTURES:
                slot.icon = self._art.tab_pictures_icon(size)
            else:
                slot.icon = self._art.tab_size_icon(size)

    def focus_current_tab(self) -> None:
        self.layer.focus(tab_id(self._tab), visible=True)

    def focus_in_tiles(self) -> bool:
        return self.layer.focused_id in self._tile_values

    def focus_selected_tile(self) -> None:
        chosen = next((tile for tile in self.tiles if tile.selected), self.tiles[0] if self.tiles else None)
        if chosen is not None:
            self.layer.focus(chosen.control_id, visible=True)

    # -- tile builders -------------------------------------------------------------------

    def _inner(self) -> pygame.Rect:
        return self.geometry.panel.inflate(-2 * self.PANEL_PAD, -2 * self.PANEL_PAD)

    def _grid(self, area: pygame.Rect, columns: int, rows: int, tile_h: int | None = None) -> list[pygame.Rect]:
        gap = self.GAP
        cell_w = (area.width - gap * (columns - 1)) // columns
        cell_h = (area.height - gap * (rows - 1)) // rows
        height = min(cell_h, tile_h) if tile_h is not None else cell_h
        used_h = rows * height + (rows - 1) * gap
        top = area.y + (area.height - used_h) // 2
        rects = []
        for row in range(rows):
            for column in range(columns):
                rects.append(pygame.Rect(area.x + column * (cell_w + gap), top + row * (height + gap), cell_w, height))
        return rects

    def _tile(self, kind: ChoiceKind, value: str, rect: pygame.Rect, icon: pygame.Surface | None) -> IconButton:
        return self._kit.icon_button(
            tile_id(kind, value),
            rect,
            icon=icon,
            shape=BodyShape.TILE,
            on_activate=lambda k=kind, v=value: self._on_choice(k, v),
        )

    def _avatar_tiles(self, look: Look) -> list[IconButton]:
        avatars = self._choices.avatars
        columns = 3
        rows = max(1, (len(avatars) + columns - 1) // columns)
        rects = self._grid(self._inner(), columns, rows, tile_h=124)
        tiles = []
        for avatar, rect in zip(avatars, rects):
            icon = self._art.icon(avatar, round(min(rect.width, rect.height) * 0.74))
            tiles.append(self._tile(ChoiceKind.AVATAR, avatar, rect, icon))
        return tiles

    def _colour_tiles(self, look: Look) -> list[IconButton]:
        inner = self._inner()
        divider = 18
        half = (inner.height - divider) // 2
        rooms = pygame.Rect(inner.x, inner.y, inner.width, half)
        sparkles = pygame.Rect(inner.x, inner.y + half + divider, inner.width, half)
        tiles = []
        room_rects = self._grid(rooms, 4, 2)
        for swatch, rect in zip(self._choices.backgrounds, room_rects):
            face_h = rect.height - max(2, round(rect.height * 0.07))
            size = (round(rect.width * 0.8), round(face_h * 0.72))
            icon = self._art.room_swatch(swatch.color, size)
            tiles.append(self._tile(ChoiceKind.BACKGROUND, swatch.swatch_id, rect, icon))
        star_rects = self._grid(sparkles, 4, 2)
        for swatch, rect in zip(self._choices.accents, star_rects):
            icon = self._art.sparkle_star(swatch.color, round(min(rect.width, rect.height) * 0.72))
            tiles.append(self._tile(ChoiceKind.ACCENT, swatch.swatch_id, rect, icon))
        return tiles

    def _picture_tiles(self, look: Look) -> list[IconButton]:
        options = list(self._choices.wallpapers)
        if self._custom:
            options.insert(1, CUSTOM_CHOICE)
        columns = 3
        rows = max(1, (len(options) + columns - 1) // columns)
        inner = self._inner()
        cell_w = (inner.width - self.GAP * (columns - 1)) // columns
        cell_h = (inner.height - self.GAP * (rows - 1)) // rows
        tile_h = min(cell_h, round(cell_w * 0.8))
        rects = self._grid(inner, columns, rows, tile_h=tile_h)
        room = self._choices.background(look.background)
        tiles = []
        for choice, rect in zip(options, rects):
            face_h = rect.height - max(2, round(rect.height * 0.07))
            # Cover-cropped scene: bigger pictures than a letterboxed thumbnail.
            size = (rect.width - 20, face_h - 20)
            icon = self._art.picture_tile(choice, room, size, custom=self.custom_path)
            tiles.append(self._tile(ChoiceKind.WALLPAPER, choice, rect, icon))
        return tiles

    def _size_tiles(self, look: Look) -> list[IconButton]:
        sizes = self._choices.sizes
        rects = self._grid(self._inner(), 1, len(sizes), tile_h=128)
        tiles = []
        for value, rect in zip(sizes, rects):
            icon = self._art.size_sample(value, round(rect.height * 0.62))
            tiles.append(self._tile(ChoiceKind.SIZE, value, rect, icon))
        return tiles


__all__ = ["Geometry", "MyGreiaControls", "UNDO_ID", "compute_geometry", "tab_id", "tile_id"]

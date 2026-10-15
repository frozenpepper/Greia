"""Shared control-kit wiring for Painting (ADR 0037).

Every Painting control is a kit control or a kit ``ExternalTarget`` so one
``ControlLayer`` gives pointer, touch, keyboard and controller access with the
same focus ring:

* top toolbar — gallery, undo, share/import, colouring pages, new (tile
  ``IconButton``s on the shared ``ChildUiMetrics`` toolbar geometry);
* tray — paint swatches (Activity-drawn dishes as ``ExternalTarget``s), a
  brush-size ``ToolStrip`` with true-size dots, eraser and stamp tiles;
* gallery — one ``ExternalTarget`` per visible card, small pointer-only
  delete badges, page arrows and a delete tile for the focused card;
* sheets — stamp picker, colouring-page picker and the delete confirmation
  are modal ``Overlay``s with their own small ``ControlLayer``.

The app owns what each control does; rules stay in the model.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ExternalTarget,
    IconButton,
    KitPointer,
    PointerPhase,
    ToolStrip,
)
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.ui_core import Overlay, UiEventResult

if __package__:
    from .painting_content import BRUSH_SIZES, COLORS, GALLERY_PAGE_SIZE, STAMP_IDS
else:  # pragma: no cover - runtime/script fallback
    from painting_content import BRUSH_SIZES, COLORS, GALLERY_PAGE_SIZE, STAMP_IDS


class BadgeButton(IconButton):
    """Small pointer/touch-only shortcut (keyboard users reach the same action
    through a focusable control elsewhere, so it never clutters focus order)."""

    @property
    def focusable(self) -> bool:  # type: ignore[override]
        return False


class PaintingControls:
    """Own Painting's kit controls and the main ``ControlLayer``.

    Geometry comes from the renderer (which owns ``ChildUiMetrics`` layout),
    so the toolbar stays outside the protected Home/Back chrome at every
    viewport. ``sync`` mirrors app state into control flags only when called
    after a change; the kit caches every rendered state.
    """

    def __init__(
        self,
        kit: ControlKit,
        renderer,
        *,
        gallery_icon: pygame.Surface | None,
        colouring_icon: pygame.Surface | None,
        on_gallery: Callable[[], object],
        on_undo: Callable[[], object],
        on_new: Callable[[], object],
        on_share: Callable[[], object],
        on_import: Callable[[], object],
        on_colouring: Callable[[], object],
        on_color: Callable[[int], object],
        on_size: Callable[[int], object],
        on_eraser: Callable[[], object],
        on_stamp: Callable[[], object],
        on_card: Callable[[int], object],
        on_card_delete: Callable[[int], object],
        on_page: Callable[[int], object],
        on_delete_focused: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._renderer = renderer
        self._gallery_icon = gallery_icon
        self._colouring_icon = colouring_icon
        self._on_card = on_card
        self._on_card_delete = on_card_delete
        self._dot_icons: dict[tuple[int, int, int], pygame.Surface] = {}
        self._stamp_icon: pygame.Surface | None = None

        tile = BodyShape.TILE
        self.gallery = kit.icon_button("tool.gallery", pygame.Rect(0, 0, 58, 58), icon=None, shape=tile, on_activate=on_gallery)
        self.undo = kit.icon_button("tool.undo", pygame.Rect(0, 0, 58, 58), icon=None, shape=tile, on_activate=on_undo)
        self.new = kit.icon_button(
            "tool.new", pygame.Rect(0, 0, 58, 58), icon=None, shape=tile, role=ButtonRole.PRIMARY, on_activate=on_new,
        )
        self.colouring = kit.icon_button("tool.colouring", pygame.Rect(0, 0, 58, 58), icon=None, shape=tile, on_activate=on_colouring)
        self.share = kit.icon_button("tool.share", pygame.Rect(0, 0, 58, 58), icon=None, shape=tile, on_activate=on_share)
        self.importer = kit.icon_button("tool.import", pygame.Rect(0, 0, 58, 58), icon=None, shape=tile, on_activate=on_import)
        self._on_color = on_color
        self.swatches: tuple[ExternalTarget, ...] = ()
        self.sizes: ToolStrip = kit.tool_strip(
            "size",
            [(str(index), "", None) for index in range(len(BRUSH_SIZES))],
            shape=tile,
            selected="1",
            on_select=lambda chosen: on_size(int(chosen)),
        )
        self.eraser = kit.icon_button("tool.eraser", pygame.Rect(0, 0, 60, 60), icon=None, shape=tile, on_activate=on_eraser)
        self.stamp = kit.icon_button("tool.stamp", pygame.Rect(0, 0, 60, 60), icon=None, shape=tile, on_activate=on_stamp)
        self.previous_page = kit.icon_button(
            "gallery.previous", pygame.Rect(0, 0, 96, 66), icon=None, shape=tile, on_activate=lambda: on_page(-1),
        )
        self.next_page = kit.icon_button(
            "gallery.next", pygame.Rect(0, 0, 96, 66), icon=None, shape=tile, on_activate=lambda: on_page(1),
        )
        self.delete_focused = kit.icon_button(
            "gallery.delete", pygame.Rect(0, 0, 66, 66), icon=None, shape=tile, on_activate=on_delete_focused,
        )
        self.cards: list[ExternalTarget] = []
        self.badges: list[BadgeButton] = []
        self.layer: ControlLayer = kit.layer((), layer_id="painting.controls")
        self.mode = "paint"
        self.shared_available = False
        self.colouring_available = colouring_icon is not None
        self.relayout()

    # -- geometry ------------------------------------------------------------

    def relayout(self) -> None:
        """Re-read every rect from the renderer and rescale icons once."""

        renderer = self._renderer
        metrics = renderer.metrics
        icon = metrics.px(38)
        kit = self._kit
        self.gallery.rect = renderer.toolbar_rect("gallery")
        self.undo.rect = renderer.toolbar_rect("undo")
        self.new.rect = renderer.toolbar_rect("new")
        self.colouring.rect = renderer.toolbar_rect("colouring")
        share_rect = renderer.shared_export_button()
        self._share_fits = share_rect is not None
        for button in (self.share, self.importer):
            button.rect = share_rect if share_rect is not None else pygame.Rect(-200, -200, 10, 10)
        self.gallery.icon = _scaled(self._gallery_icon, icon)
        self.undo.icon = kit.glyph("undo", icon)
        self.new.icon = kit.glyph("new", icon)
        self.colouring.icon = _scaled(self._colouring_icon, icon)
        self.share.icon = kit.glyph("share", icon)
        self.importer.icon = kit.glyph("import", icon)
        # Swatch dishes are Activity art; the kit only focuses/activates them.
        self.swatches = tuple(
            ExternalTarget(
                f"color.{index}", rect, (lambda chosen=index: self._on_color(chosen)),
                focus_radius=rect.width // 2,
            )
            for rect, index in renderer._color_buttons()
        )
        for slot, (rect, _index) in zip(self.sizes.slots, renderer._size_buttons()):
            slot.rect = rect
        eraser_rect, stamp_rect = renderer.tool_buttons()
        self.eraser.rect = eraser_rect
        self.stamp.rect = stamp_rect
        self.eraser.icon = kit.glyph("eraser", metrics.px(42))
        previous, following = renderer.gallery_nav_buttons()
        self.previous_page.rect = previous
        self.next_page.rect = following
        arrow = metrics.px(44)
        self.previous_page.icon = kit.glyph("arrow_left", arrow)
        self.next_page.icon = kit.glyph("arrow_right", arrow)
        self.delete_focused.rect = renderer.gallery_delete_button()
        self.delete_focused.icon = kit.glyph("trash", metrics.px(42))
        self._dot_icons.clear()
        self._rebuild()

    def size_icon(self, color_index: int, size_index: int, eraser: bool) -> pygame.Surface:
        """True-size brush dot in the current colour (cached, bounded 33)."""

        key = (-1 if eraser else color_index, size_index, self._renderer.metrics.px(100))
        cached = self._dot_icons.get(key)
        if cached is not None:
            return cached
        metrics = self._renderer.metrics
        diameter = max(6, metrics.px(BRUSH_SIZES[size_index]))
        ring = max(2, metrics.px(2))
        halo = max(2, metrics.px(3))
        surface = pygame.Surface((diameter + (ring + halo) * 2, diameter + (ring + halo) * 2), pygame.SRCALPHA)
        centre = surface.get_width() // 2
        fill = (255, 255, 255) if eraser else COLORS[color_index]
        # Ink | white halo | paint: the dot reads on cream and on the accent
        # (selected) tile body alike, whatever paint is chosen.
        pygame.draw.circle(surface, self._kit.theme.ink, (centre, centre), diameter // 2 + halo + ring)
        pygame.draw.circle(surface, (255, 255, 255), (centre, centre), diameter // 2 + halo)
        pygame.draw.circle(surface, fill, (centre, centre), max(1, diameter // 2))
        if len(self._dot_icons) >= 33:
            self._dot_icons.pop(next(iter(self._dot_icons)))
        self._dot_icons[key] = surface
        return surface

    # -- state ---------------------------------------------------------------

    def sync_paint(
        self,
        *,
        color_index: int,
        size_index: int,
        tool: str,
        can_undo: bool,
        stamp_icon: pygame.Surface | None,
    ) -> None:
        """Mirror paint-mode state into control flags and icons."""

        self.undo.enabled = can_undo
        eraser = tool == "eraser"
        if self.sizes.selected != str(size_index):
            self.sizes.select(str(size_index))
        for index, slot in enumerate(self.sizes.slots):
            slot.icon = self.size_icon(color_index, index, eraser)
        self.eraser.selected = eraser
        self.stamp.selected = tool == "stamp"
        if stamp_icon is not None:
            self.stamp.icon = stamp_icon
        self.layer.invalidation.invalidate()

    def sync_gallery(self, *, page: int, page_count: int, cards: Sequence[pygame.Rect], has_focus_card: bool) -> None:
        """Rebuild gallery card targets for the visible page."""

        first = page * GALLERY_PAGE_SIZE
        self.cards = [
            ExternalTarget(
                f"card.{slot}", rect, (lambda index=first + slot: self._on_card(index)),
                focus_radius=self._renderer.metrics.radius,
            )
            for slot, rect in enumerate(cards)
        ]
        badge_size = self._renderer.metrics.px(46)
        icon = self._kit.glyph("trash", self._renderer.metrics.px(28))
        self.badges = []
        for slot, rect in enumerate(cards):
            badge = BadgeButton(
                self._kit.painter,
                f"card.{slot}.delete",
                pygame.Rect(rect.right - badge_size + self._renderer.metrics.px(6), rect.top - self._renderer.metrics.px(6), badge_size, badge_size),
                icon=icon,
                shape=BodyShape.ROUND,
                on_activate=(lambda index=first + slot: self._on_card_delete(index)),
            )
            self.badges.append(badge)
        self.previous_page.visible = page_count > 1
        self.next_page.visible = page_count > 1
        self.previous_page.enabled = page > 0
        self.next_page.enabled = page < page_count - 1
        self.delete_focused.visible = has_focus_card
        self._rebuild()

    def set_mode(self, mode: str, *, shared_available: bool, colouring_available: bool) -> None:
        self.mode = mode
        self.shared_available = shared_available
        self.colouring_available = colouring_available
        self.gallery.selected = mode == "gallery"
        self._rebuild()

    def card_control_id(self, slot: int) -> str:
        return f"card.{slot}"

    def focused_card_slot(self) -> int | None:
        focused = self.layer.focused_id
        if focused and focused.startswith("card.") and focused.count(".") == 1:
            return int(focused.split(".")[1])
        return None

    def _rebuild(self) -> None:
        share_visible = self.shared_available and self._share_fits
        self.share.visible = share_visible and self.mode == "paint"
        self.importer.visible = share_visible and self.mode == "gallery"
        if self.mode == "gallery":
            targets = [
                self.gallery,
                *([self.importer] if self.importer.visible else []),
                self.new,
                *self.cards,
                *self.badges,
                self.previous_page,
                self.delete_focused,
                self.next_page,
            ]
        else:
            targets = [
                self.gallery,
                self.undo,
                *([self.share] if self.share.visible else []),
                *([self.colouring] if self.colouring_available else []),
                self.new,
                *self.swatches,
                *self.sizes.controls,
                self.eraser,
                self.stamp,
            ]
        focused = self.layer.focused_id
        visible = self.layer.focus_visible
        self.layer.set_targets(targets)
        if focused is not None and focused in {target.control_id for target in targets}:
            self.layer.focus(focused, visible=visible)
        self.layer.invalidation.invalidate()


class PaintingSheet(Overlay):
    """Small modal sheet: its own ``ControlLayer`` above a drawn backdrop.

    A pointer press and release outside ``panel`` (or CANCEL — Escape / east
    face button) dismisses it, so a child can always back out without words.
    """

    def __init__(
        self,
        sheet_id: str,
        layer: ControlLayer,
        panel: pygame.Rect,
        *,
        on_dismiss: Callable[[], object],
        draw_backdrop: Callable[[pygame.Surface], object],
    ) -> None:
        self._id = sheet_id
        self.layer = layer
        self.panel = pygame.Rect(panel)
        self._on_dismiss = on_dismiss
        self._draw_backdrop = draw_backdrop
        self._outside_down = False

    @property
    def surface_id(self) -> str:
        return self._id

    def handle_event(self, event: object) -> UiEventResult:
        if isinstance(event, KitPointer):
            inside = self.panel.collidepoint(event.position) or self.layer.hit(event.position) is not None
            if event.phase is PointerPhase.DOWN:
                self._outside_down = not inside
                if not inside:
                    return UiEventResult.HANDLED
            elif event.phase is PointerPhase.UP and self._outside_down:
                self._outside_down = False
                if not inside:
                    self._on_dismiss()
                return UiEventResult.HANDLED
            self.layer.handle_event(event)
            return UiEventResult.HANDLED
        if (
            isinstance(event, SemanticInputEvent)
            and event.edge is InputEdge.PRESSED
            and event.action is SemanticAction.CANCEL
        ):
            self._on_dismiss()
            return UiEventResult.HANDLED
        self.layer.handle_event(event)
        return UiEventResult.HANDLED

    def draw(self, target: object) -> None:
        assert isinstance(target, pygame.Surface)
        self._draw_backdrop(target)
        self.layer.draw(target)


class PaintingSheets:
    """Build Painting's three modal sheets from kit controls.

    * stamps — 6x2 tiles of shared-library stamp art above the tray;
    * pages — one large preview card per colouring page over the canvas;
    * delete — the painting itself, a trash pictogram, back (default focus)
      and a coral trash confirm: deletion is always deliberate.
    """

    def __init__(self, kit: ControlKit, renderer) -> None:
        self._kit = kit
        self._renderer = renderer

    def stamps(
        self,
        selected: int | None,
        *,
        focus_visible: bool,
        on_choose: Callable[[int], object],
        on_dismiss: Callable[[], object],
    ) -> PaintingSheet:
        renderer = self._renderer
        panel, tiles = renderer.stamp_sheet_rects()
        icon_size = tiles[0].height * 7 // 10
        buttons = [
            self._kit.icon_button(
                f"stamp.{index}", rect,
                icon=renderer.stamp_icon(asset_id, icon_size),
                shape=BodyShape.TILE, selected=index == selected,
                on_activate=(lambda chosen=index: on_choose(chosen)),
            )
            for index, (asset_id, rect) in enumerate(zip(STAMP_IDS, tiles))
        ]
        layer = self._kit.layer(buttons, layer_id="painting.stamps")
        layer.focus(f"stamp.{selected or 0}", visible=focus_visible)
        return PaintingSheet(
            "painting.stamps", layer, panel, on_dismiss=on_dismiss,
            draw_backdrop=lambda screen: renderer.draw_sheet_panel(screen, panel),
        )

    def pages(
        self,
        pages: Sequence[str],
        *,
        focus_visible: bool,
        on_choose: Callable[[str], object],
        on_dismiss: Callable[[], object],
    ) -> PaintingSheet:
        renderer = self._renderer
        metrics = renderer.metrics
        panel, cards = renderer.colouring_sheet_rects(len(pages))
        buttons = [
            self._kit.icon_button(
                f"page.{page}", rect,
                icon=renderer.outlines.preview(page, (rect.width - metrics.px(20), rect.height - metrics.px(24))),
                shape=BodyShape.TILE,
                on_activate=(lambda chosen=page: on_choose(chosen)),
            )
            for page, rect in zip(pages, cards)
        ]
        layer = self._kit.layer(buttons, layer_id="painting.pages")
        layer.focus(f"page.{pages[0]}", visible=focus_visible)

        def backdrop(screen: pygame.Surface) -> None:
            renderer.draw_dim(screen)
            renderer.draw_sheet_panel(screen, panel)

        return PaintingSheet("painting.pages", layer, panel, on_dismiss=on_dismiss, draw_backdrop=backdrop)

    def delete(
        self,
        load_preview: Callable[[tuple[int, int]], pygame.Surface | None],
        *,
        on_cancel: Callable[[], object],
        on_confirm: Callable[[], object],
    ) -> PaintingSheet:
        renderer = self._renderer
        panel, cancel_rect, confirm_rect = renderer.delete_dialog_rects()
        preview = load_preview(renderer.delete_preview_rect(panel).size)
        icon = renderer.metrics.px(46)
        cancel = self._kit.icon_button(
            "delete.cancel", cancel_rect, icon=self._kit.glyph("arrow_left", icon), shape=BodyShape.TILE,
            on_activate=on_cancel,
        )
        confirm = self._kit.icon_button(
            "delete.confirm", confirm_rect, icon=self._kit.glyph("trash", icon), shape=BodyShape.TILE,
            role=ButtonRole.PRIMARY, on_activate=on_confirm,
        )
        layer = self._kit.layer([cancel, confirm], layer_id="painting.delete")
        layer.focus("delete.cancel", visible=True)
        return PaintingSheet(
            "painting.delete", layer, panel, on_dismiss=on_cancel,
            draw_backdrop=lambda screen: renderer.draw_delete_dialog(screen, panel, preview),
        )


def _scaled(surface: pygame.Surface | None, size: int) -> pygame.Surface | None:
    if surface is None:
        return None
    if surface.get_size() == (size, size):
        return surface
    return pygame.transform.smoothscale(surface, (size, size))


__all__ = ["BadgeButton", "PaintingControls", "PaintingSheet", "PaintingSheets"]

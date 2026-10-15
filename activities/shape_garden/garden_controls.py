"""Shared control-kit wiring for Shape Garden (ADR 0037).

Every interactive element is a kit control or a kit ``ExternalTarget`` in one
``ControlLayer``, so pointer, touch, keyboard and controller share one focus
ring:

* top bar — gallery, undo, share, backdrop, ghost picture, new (tiles);
* paint shelf — seven colour pots (Activity-drawn, ``ExternalTarget``s);
* garden — one ``ExternalTarget`` per placed shape (focus = pick it up);
* tools — grow, shrink, turn, put behind (enabled with a selection);
* tray — eight shape tiles in the current colour, and the bin;
* gallery — cards, small pointer-only delete badges, page arrows, delete;
* sheets — backdrop picker, ghost-picture picker and the delete
  confirmation are modal ``Overlay``s with their own small ``ControlLayer``.

The app owns what each control does; rules stay in ``garden_model``.
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
)
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.ui_core import Overlay, UiEventResult

if __package__:
    from .garden_content import COLOUR_IDS, GALLERY_PAGE_SIZE, SHAPE_KINDS
else:  # pragma: no cover - runtime/script fallback
    from garden_content import COLOUR_IDS, GALLERY_PAGE_SIZE, SHAPE_KINDS


class BadgeButton(IconButton):
    """Small pointer/touch-only shortcut; keyboard users reach the same action
    through a focusable control elsewhere, so it never clutters focus order."""

    @property
    def focusable(self) -> bool:  # type: ignore[override]
        return False


def shape_target_id(index: int) -> str:
    return f"shape.{index}"


class GardenControls:
    """Own Shape Garden's kit controls and the main ``ControlLayer``."""

    def __init__(
        self,
        kit: ControlKit,
        renderer,
        *,
        on_gallery: Callable[[], object],
        on_undo: Callable[[], object],
        on_share: Callable[[], object],
        on_backdrop: Callable[[], object],
        on_ghost: Callable[[], object],
        on_new: Callable[[], object],
        on_colour: Callable[[str], object],
        on_tool: Callable[[str], object],
        on_tray: Callable[[int], object],
        on_bin: Callable[[], object],
        on_shape: Callable[[int], object],
        on_card: Callable[[int], object],
        on_card_delete: Callable[[int], object],
        on_page: Callable[[int], object],
        on_delete_focused: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._renderer = renderer
        self._on_shape = on_shape
        self._on_card = on_card
        self._on_card_delete = on_card_delete
        tile = BodyShape.TILE
        top = renderer.toolbar_rects()
        glyph = kit.glyph
        self.gallery = kit.icon_button("tool.gallery", top["gallery"], icon=renderer.icon("tool_gallery", 44), shape=tile, on_activate=on_gallery)
        self.undo = kit.icon_button("tool.undo", top["undo"], icon=glyph("undo", 40), shape=tile, on_activate=on_undo)
        self.share = kit.icon_button("tool.share", top["share"], icon=glyph("share", 40), shape=tile, on_activate=on_share)
        self.backdrop = kit.icon_button("tool.backdrop", top["backdrop"], icon=None, shape=tile, on_activate=on_backdrop)
        self.ghost = kit.icon_button("tool.ghost", top["ghost"], icon=renderer.icon("tool_ghost", 44), shape=tile, on_activate=on_ghost)
        self.new = kit.icon_button(
            "tool.new", top["new"], icon=glyph("new", 40), shape=tile, role=ButtonRole.PRIMARY, on_activate=on_new,
        )
        self.pots = tuple(
            ExternalTarget(f"colour.{colour}", rect, (lambda c=colour: on_colour(c)), focus_radius=rect.width // 2)
            for rect, colour in zip(renderer.pot_rects(), COLOUR_IDS)
        )
        tools = renderer.tool_rects()
        icons = {
            "grow": renderer.icon("tool_grow", 48),
            "shrink": renderer.icon("tool_shrink", 48),
            "turn": glyph("rotate", 46),
            "back": renderer.icon("tool_back", 48),
        }
        self.tools = {
            name: kit.icon_button(f"tool.{name}", rect, icon=icons[name], shape=tile, on_activate=(lambda n=name: on_tool(n)))
            for name, rect in tools.items()
        }
        self.tray = tuple(
            kit.icon_button(f"tray.{kind}", rect, icon=None, shape=tile, on_activate=(lambda i=index: on_tray(i)))
            for index, (kind, rect) in enumerate(zip(SHAPE_KINDS, renderer.tray_tiles()))
        )
        self.bin = kit.icon_button("tool.bin", renderer.bin_rect(), icon=glyph("trash", 58), shape=tile, on_activate=on_bin)
        previous, delete, following = renderer.gallery_nav_rects()
        self.previous_page = kit.icon_button("gallery.previous", previous, icon=glyph("arrow_left", 44), shape=tile, on_activate=lambda: on_page(-1))
        self.next_page = kit.icon_button("gallery.next", following, icon=glyph("arrow_right", 44), shape=tile, on_activate=lambda: on_page(1))
        self.delete_focused = kit.icon_button("gallery.delete", delete, icon=glyph("trash", 42), shape=tile, on_activate=on_delete_focused)
        self.shape_targets: list[ExternalTarget] = []
        self.cards: list[ExternalTarget] = []
        self.badges: list[BadgeButton] = []
        self.layer: ControlLayer = kit.layer((), layer_id="shape_garden.controls")
        self.mode = "garden"
        self.share_available = False

    def relayout(self) -> None:
        """Re-read the top-bar rects (they follow the protected chrome)."""
        top = self._renderer.toolbar_rects()
        for name, button in (
            ("gallery", self.gallery), ("undo", self.undo), ("share", self.share),
            ("backdrop", self.backdrop), ("ghost", self.ghost), ("new", self.new),
        ):
            button.rect = top[name]
        self.layer.invalidation.invalidate()

    # -- state -------------------------------------------------------------------

    def set_tray_icons(self, icons: Sequence[pygame.Surface | None]) -> None:
        for button, icon in zip(self.tray, icons):
            button.icon = icon
        self.layer.invalidation.invalidate()

    def sync_garden(
        self,
        *,
        shape_rects: Sequence[pygame.Rect],
        selected: bool,
        can_undo: bool,
        full: bool,
        can_grow: bool,
        can_shrink: bool,
        backdrop_icon: pygame.Surface | None,
    ) -> None:
        """Mirror the editor state into control flags (call after changes)."""
        self.undo.enabled = can_undo
        self.tools["grow"].enabled = selected and can_grow
        self.tools["shrink"].enabled = selected and can_shrink
        self.tools["turn"].enabled = selected
        self.tools["back"].enabled = selected
        self.bin.enabled = selected
        for button in self.tray:
            button.enabled = not full
        if backdrop_icon is not None:
            self.backdrop.icon = backdrop_icon
        radius = 18
        self.shape_targets = [
            ExternalTarget(shape_target_id(index), rect, (lambda i=index: self._on_shape(i)), focus_radius=radius)
            for index, rect in enumerate(shape_rects)
        ]
        self._rebuild()

    def sync_gallery(self, *, page: int, page_count: int, cards: Sequence[pygame.Rect], has_cards: bool) -> None:
        first = page * GALLERY_PAGE_SIZE
        self.cards = [
            ExternalTarget(f"card.{slot}", rect, (lambda index=first + slot: self._on_card(index)), focus_radius=18)
            for slot, rect in enumerate(cards)
        ]
        icon = self._kit.glyph("trash", 28)
        self.badges = [
            BadgeButton(
                self._kit.painter, f"card.{slot}.delete",
                pygame.Rect(rect.right - 40, rect.top - 6, 46, 46),
                icon=icon, shape=BodyShape.ROUND,
                on_activate=(lambda index=first + slot: self._on_card_delete(index)),
            )
            for slot, rect in enumerate(cards)
        ]
        self.previous_page.visible = page_count > 1
        self.next_page.visible = page_count > 1
        self.previous_page.enabled = page > 0
        self.next_page.enabled = page < page_count - 1
        self.delete_focused.visible = has_cards
        self._rebuild()

    def set_mode(self, mode: str, *, share_available: bool) -> None:
        self.mode = mode
        self.share_available = share_available
        self.gallery.selected = mode == "gallery"
        self._rebuild()

    def focused_card_slot(self) -> int | None:
        focused = self.layer.focused_id
        if focused and focused.startswith("card.") and focused.count(".") == 1:
            return int(focused.split(".")[1])
        return None

    def focused_shape(self) -> int | None:
        focused = self.layer.focused_id
        if focused and focused.startswith("shape."):
            return int(focused.split(".")[1])
        return None

    def _rebuild(self) -> None:
        self.share.visible = self.share_available and self.mode == "garden"
        garden = self.mode == "garden"
        for control in (self.undo, self.backdrop, self.ghost, *self.tools.values(), *self.tray, self.bin):
            control.visible = garden
        if garden:
            targets = [
                self.gallery, self.undo, *([self.share] if self.share.visible else []),
                self.backdrop, self.ghost, self.new,
                *self.pots, *self.shape_targets, *self.tools.values(), *self.tray, self.bin,
            ]
        else:
            targets = [
                self.gallery, self.new, *self.cards, *self.badges,
                self.previous_page, self.delete_focused, self.next_page,
            ]
        focused = self.layer.focused_id
        visible = self.layer.focus_visible
        self.layer.set_targets(targets)
        if focused is not None and focused in {target.control_id for target in targets}:
            self.layer.focus(focused, visible=visible)
        self.layer.invalidation.invalidate()


class GardenSheet(Overlay):
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


class GardenSheets:
    """Build the backdrop picker, the ghost-picture picker and delete confirm."""

    def __init__(self, kit: ControlKit, renderer) -> None:
        self._kit = kit
        self._renderer = renderer

    def pictures(
        self,
        sheet_id: str,
        choices: Sequence[tuple[str, pygame.Surface | None]],
        selected: str | None,
        *,
        columns: int,
        tile: tuple[int, int],
        focus_visible: bool,
        on_choose: Callable[[str], object],
        on_dismiss: Callable[[], object],
    ) -> GardenSheet:
        renderer = self._renderer
        panel, rects = renderer.sheet_tiles(len(choices), columns, tile)
        buttons = [
            self._kit.icon_button(
                f"{sheet_id}.{choice_id}", rect, icon=icon, shape=BodyShape.TILE,
                selected=choice_id == selected,
                on_activate=(lambda chosen=choice_id: on_choose(chosen)),
            )
            for (choice_id, icon), rect in zip(choices, rects)
        ]
        layer = self._kit.layer(buttons, layer_id=f"shape_garden.{sheet_id}")
        start = selected if selected in {choice for choice, _ in choices} else choices[0][0]
        layer.focus(f"{sheet_id}.{start}", visible=focus_visible)
        return GardenSheet(
            f"shape_garden.{sheet_id}", layer, panel, on_dismiss=on_dismiss,
            draw_backdrop=lambda screen: renderer.draw_sheet_panel(screen, panel),
        )

    def delete(
        self,
        preview: pygame.Surface | None,
        *,
        on_cancel: Callable[[], object],
        on_confirm: Callable[[], object],
    ) -> GardenSheet:
        renderer = self._renderer
        panel, _preview, cancel_rect, confirm_rect = renderer.delete_dialog_rects()
        cancel = self._kit.icon_button(
            "delete.cancel", cancel_rect, icon=self._kit.glyph("arrow_left", 46), shape=BodyShape.TILE,
            on_activate=on_cancel,
        )
        confirm = self._kit.icon_button(
            "delete.confirm", confirm_rect, icon=self._kit.glyph("trash", 46), shape=BodyShape.TILE,
            role=ButtonRole.PRIMARY, on_activate=on_confirm,
        )
        layer = self._kit.layer([cancel, confirm], layer_id="shape_garden.delete")
        layer.focus("delete.cancel", visible=True)
        return GardenSheet(
            "shape_garden.delete", layer, panel, on_dismiss=on_cancel,
            draw_backdrop=lambda screen: renderer.draw_delete_dialog(screen, preview),
        )


__all__ = ["BadgeButton", "GardenControls", "GardenSheet", "GardenSheets", "shape_target_id"]

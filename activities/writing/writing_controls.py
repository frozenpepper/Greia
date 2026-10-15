"""Shared control-kit wiring for Writing (ADR 0037).

Every Writing control is a kit control or a kit ``ExternalTarget`` so one
``ControlLayer`` gives pointer, touch, keyboard and controller access with the
same focus ring:

* top toolbar — pages (gallery), undo, emoji, share/import and new page
  (tile ``IconButton``s on the shared ``ChildUiMetrics`` toolbar geometry);
* gallery — one ``ExternalTarget`` per visible card, small pointer-only delete
  badges, page arrows and a delete tile for the focused card;
* sheets — the emoji picker, the paper-colour chooser and the delete
  confirmation are ``Overlay``s with their own small ``ControlLayer``.

Writing is a ``text`` profile Activity: the physical keyboard types, so the
app only hands keyboard navigation to these controls when the child has
deliberately moved focus into them (Tab, or any controller input).
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
    from .writing_content import GALLERY_PAGE_SIZE, TINT_IDS
else:  # pragma: no cover - runtime/script fallback
    from writing_content import GALLERY_PAGE_SIZE, TINT_IDS


class BadgeButton(IconButton):
    """Small pointer/touch-only shortcut (keyboard users reach the same action
    through a focusable control elsewhere, so it never clutters focus order)."""

    @property
    def focusable(self) -> bool:  # type: ignore[override]
        return False


class WritingControls:
    """Own Writing's toolbar/gallery kit controls and the main ``ControlLayer``.

    Geometry comes from the renderer (which owns ``ChildUiMetrics`` layout), so
    the toolbar stays outside the protected Home/Back chrome at every viewport.
    """

    def __init__(
        self,
        kit: ControlKit,
        renderer,
        editor_rect: Callable[[], pygame.Rect],
        *,
        on_gallery: Callable[[], object],
        on_undo: Callable[[], object],
        on_emoji: Callable[[], object],
        on_new: Callable[[], object],
        on_share: Callable[[], object],
        on_import: Callable[[], object],
        on_card: Callable[[int], object],
        on_card_delete: Callable[[int], object],
        on_page: Callable[[int], object],
        on_delete_focused: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._renderer = renderer
        self._editor_rect = editor_rect
        self._on_card = on_card
        self._on_card_delete = on_card_delete
        tile = BodyShape.TILE
        placeholder = pygame.Rect(0, 0, 58, 58)
        self.gallery = kit.icon_button("tool.gallery", placeholder, icon=None, shape=tile, on_activate=on_gallery)
        self.undo = kit.icon_button("tool.undo", placeholder, icon=None, shape=tile, on_activate=on_undo)
        self.emoji = kit.icon_button("tool.emoji", placeholder, icon=None, shape=tile, on_activate=on_emoji)
        self.share = kit.icon_button("tool.share", placeholder, icon=None, shape=tile, on_activate=on_share)
        self.importer = kit.icon_button("tool.import", placeholder, icon=None, shape=tile, on_activate=on_import)
        self.new = kit.icon_button(
            "tool.new", placeholder, icon=None, shape=tile, role=ButtonRole.PRIMARY, on_activate=on_new,
        )
        self.previous_page = kit.icon_button(
            "gallery.previous", pygame.Rect(0, 0, 96, 62), icon=None, shape=tile, on_activate=lambda: on_page(-1),
        )
        self.next_page = kit.icon_button(
            "gallery.next", pygame.Rect(0, 0, 96, 62), icon=None, shape=tile, on_activate=lambda: on_page(1),
        )
        self.delete_focused = kit.icon_button(
            "gallery.delete", pygame.Rect(0, 0, 62, 62), icon=None, shape=tile, on_activate=on_delete_focused,
        )
        self.cards: list[ExternalTarget] = []
        self.badges: list[BadgeButton] = []
        self.layer: ControlLayer = kit.layer((), layer_id="writing.controls")
        self.mode = "edit"
        self.shared_available = False
        self._share_fits = True
        self.relayout()

    # -- geometry ------------------------------------------------------------

    def relayout(self) -> None:
        """Re-read every rect from the renderer and rescale icons once."""

        renderer = self._renderer
        metrics = renderer.metrics
        kit = self._kit
        icon = metrics.px(38)
        for name in ("gallery", "undo", "emoji", "new"):
            getattr(self, name).rect = renderer.toolbar_rect(name)
        share_rect = renderer.shared_export_button()
        self._share_fits = share_rect is not None
        for button in (self.share, self.importer):
            button.rect = share_rect if share_rect is not None else pygame.Rect(-200, -200, 10, 10)
        book = renderer.book_icon
        self.gallery.icon = book if book is None or book.get_width() == icon else pygame.transform.smoothscale(book, (icon, icon))
        if self.gallery.icon is None:
            self.gallery.icon = kit.glyph("page", icon)
        self.undo.icon = kit.glyph("undo", icon)
        self.emoji.icon = kit.text_icon("😊", metrics.px(34))
        self.new.icon = kit.glyph("new", icon)
        self.share.icon = kit.glyph("share", icon)
        self.importer.icon = kit.glyph("import", icon)
        editor = self._editor_rect()
        previous, following = renderer.gallery_nav_buttons(editor)
        self.previous_page.rect = previous
        self.next_page.rect = following
        arrow = metrics.px(42)
        self.previous_page.icon = kit.glyph("arrow_left", arrow)
        self.next_page.icon = kit.glyph("arrow_right", arrow)
        self.delete_focused.rect = renderer.gallery_delete_button(editor)
        self.delete_focused.icon = kit.glyph("trash", metrics.px(40))
        self._rebuild()

    # -- state ---------------------------------------------------------------

    def sync_edit(self, *, can_undo: bool, emoji_open: bool) -> None:
        self.undo.enabled = can_undo
        self.emoji.selected = emoji_open
        self.layer.invalidation.invalidate()

    def sync_gallery(self, *, page: int, page_count: int, cards: Sequence[pygame.Rect], has_focus_card: bool) -> None:
        """Rebuild gallery card targets for the visible page."""

        metrics = self._renderer.metrics
        first = page * GALLERY_PAGE_SIZE
        self.cards = [
            ExternalTarget(
                f"card.{slot}", rect, (lambda index=first + slot: self._on_card(index)),
                focus_radius=metrics.radius,
            )
            for slot, rect in enumerate(cards)
        ]
        badge_size = metrics.px(44)
        icon = self._kit.glyph("trash", metrics.px(26))
        self.badges = [
            BadgeButton(
                self._kit.painter,
                f"card.{slot}.delete",
                pygame.Rect(rect.right - badge_size + metrics.px(6), rect.top - metrics.px(6), badge_size, badge_size),
                icon=icon,
                shape=BodyShape.ROUND,
                on_activate=(lambda index=first + slot: self._on_card_delete(index)),
            )
            for slot, rect in enumerate(cards)
        ]
        self.previous_page.visible = page_count > 1
        self.next_page.visible = page_count > 1
        self.previous_page.enabled = page > 0
        self.next_page.enabled = page < page_count - 1
        self.delete_focused.visible = has_focus_card
        self._rebuild()

    def set_mode(self, mode: str, *, shared_available: bool) -> None:
        self.mode = mode
        self.shared_available = shared_available
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
        self.share.visible = share_visible and self.mode == "edit"
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
                self.emoji,
                *([self.share] if self.share.visible else []),
                self.new,
            ]
        focused = self.layer.focused_id
        visible = self.layer.focus_visible
        self.layer.set_targets(targets)
        if focused is not None and focused in {target.control_id for target in targets}:
            self.layer.focus(focused, visible=visible)
        self.layer.invalidation.invalidate()


class WritingSheet(Overlay):
    """Small sheet: its own ``ControlLayer`` above a drawn backdrop.

    A modal sheet swallows every pointer event; a pointer press and release
    outside ``panel`` (or CANCEL — Escape / east face button) dismisses it, so
    a child can always back out without words. A non-modal sheet (the emoji
    picker) only claims pointer events inside its panel: the app routes the
    rest to the page and toolbar, so the child can keep writing around it.
    """

    def __init__(
        self,
        sheet_id: str,
        layer: ControlLayer,
        panel: pygame.Rect,
        *,
        on_dismiss: Callable[[], object],
        draw_backdrop: Callable[[pygame.Surface], object],
        modal: bool = True,
    ) -> None:
        self._id = sheet_id
        self.layer = layer
        self.panel = pygame.Rect(panel)
        self._modal = modal
        self._on_dismiss = on_dismiss
        self._draw_backdrop = draw_backdrop
        self._outside_down = False

    @property
    def surface_id(self) -> str:
        return self._id

    @property
    def modal(self) -> bool:  # type: ignore[override]
        return self._modal

    def claims(self, position: tuple[int, int]) -> bool:
        """Whether a pointer at ``position`` belongs to this sheet."""
        return self.modal or self.panel.collidepoint(position)

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


class WritingSheets:
    """Build Writing's three sheets from kit controls.

    * emoji — category tiles above a 9x2 grid of colour emoji (non-modal);
    * paper — six big paper colours for a new page (modal, dimmed);
    * delete — the page card itself, a trash pictogram, back (default focus)
      and a coral trash confirm: deletion is always deliberate.
    """

    def __init__(self, kit: ControlKit, renderer) -> None:
        self._kit = kit
        self._renderer = renderer

    def emoji(
        self,
        palette,
        editor_rect: pygame.Rect,
        *,
        focus_id: str | None,
        focus_visible: bool,
        on_category: Callable[[int], object],
        on_emoji: Callable[[str], object],
        on_dismiss: Callable[[], object],
    ) -> WritingSheet:
        renderer = self._renderer
        panel, category_rects, emoji_rects = renderer.emoji_sheet_rects(editor_rect)
        buttons: list[IconButton] = []
        for index, (category, rect) in enumerate(zip(palette.categories, category_rects)):
            buttons.append(self._kit.icon_button(
                f"category.{category.category_id}", rect,
                icon=self._kit.text_icon(category.icon, rect.height * 6 // 10),
                shape=BodyShape.TILE, selected=index == palette.selected_index,
                on_activate=(lambda chosen=index: on_category(chosen)),
            ))
        for slot, (cluster, rect) in enumerate(zip(palette.selected.emoji, emoji_rects)):
            buttons.append(self._kit.icon_button(
                f"emoji.{slot}", rect,
                icon=self._kit.text_icon(cluster, rect.height * 64 // 100),
                shape=BodyShape.TILE,
                on_activate=(lambda chosen=cluster: on_emoji(chosen)),
            ))
        layer = self._kit.layer(buttons, layer_id="writing.emoji")
        if focus_id is None or not layer.focus(focus_id, visible=focus_visible):
            layer.focus("emoji.0", visible=focus_visible)
        return WritingSheet(
            "writing.emoji", layer, panel, on_dismiss=on_dismiss, modal=False,
            draw_backdrop=lambda screen: renderer.draw_emoji_panel(screen, panel, category_rects),
        )

    def paper(
        self,
        current_tint: str,
        editor_rect: pygame.Rect,
        *,
        focus_visible: bool,
        on_choose: Callable[[str], object],
        on_dismiss: Callable[[], object],
    ) -> WritingSheet:
        renderer = self._renderer
        panel, tiles = renderer.paper_sheet_rects(editor_rect)
        buttons = [
            self._kit.icon_button(
                f"paper.{tint}", rect,
                icon=renderer.paper_icon(tint, rect.height * 8 // 10),
                shape=BodyShape.TILE, selected=tint == current_tint,
                on_activate=(lambda chosen=tint: on_choose(chosen)),
            )
            for tint, rect in zip(TINT_IDS, tiles)
        ]
        layer = self._kit.layer(buttons, layer_id="writing.paper")
        layer.focus(f"paper.{current_tint}", visible=focus_visible)

        def backdrop(screen: pygame.Surface) -> None:
            renderer.draw_dim(screen)
            renderer.draw_sheet_panel(screen, panel)

        return WritingSheet("writing.paper", layer, panel, on_dismiss=on_dismiss, draw_backdrop=backdrop)

    def delete(
        self,
        preview: pygame.Surface | None,
        *,
        on_cancel: Callable[[], object],
        on_confirm: Callable[[], object],
    ) -> WritingSheet:
        renderer = self._renderer
        panel, cancel_rect, confirm_rect = renderer.delete_dialog_rects()
        icon = renderer.metrics.px(46)
        cancel = self._kit.icon_button(
            "delete.cancel", cancel_rect, icon=self._kit.glyph("arrow_left", icon), shape=BodyShape.TILE,
            on_activate=on_cancel,
        )
        confirm = self._kit.icon_button(
            "delete.confirm", confirm_rect, icon=self._kit.glyph("trash", icon), shape=BodyShape.TILE,
            role=ButtonRole.PRIMARY, on_activate=on_confirm,
        )
        layer = self._kit.layer([cancel, confirm], layer_id="writing.delete")
        layer.focus("delete.cancel", visible=True)
        return WritingSheet(
            "writing.delete", layer, panel, on_dismiss=on_cancel,
            draw_backdrop=lambda screen: renderer.draw_delete_dialog(screen, panel, preview),
        )


__all__ = ["BadgeButton", "WritingControls", "WritingSheet", "WritingSheets"]

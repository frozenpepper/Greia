"""Shared control-kit wiring for Leo's Post (ADR 0037).

Every interactive element is a kit control or a kit ``ExternalTarget`` in one
``ControlLayer``, so pointer, touch, keyboard and controller share the same
focus ring and activation. No control shows words:

* composer — a four-step ``ToolStrip`` (friend, card front, stickers,
  message; each slot shows what was chosen), the tray of choices for the
  current step, the big send button and Leo's mailbox (the postbox);
* postbox — sent cards (activate = open), pointer-only trash badges, page
  arrows, a trash tile for the focused card and a new-card button;
* card view — back, flip, share to My Creations and delete;
* delivered — a new card or the postbox.

Sheets (delete confirmation, postbox full) are modal ``Overlay``s with their
own small layer; backing out is always the safe choice.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ExternalTarget,
    HudChip,
    IconButton,
    KitPointer,
    PointerPhase,
    ToolStrip,
)
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.ui_core import Overlay, UiEventResult

if __package__:
    from .postcard_layout import CardViewLayout, ComposerLayout, DeliveredLayout, PostboxLayout, SheetLayout
else:
    from postcard_layout import CardViewLayout, ComposerLayout, DeliveredLayout, PostboxLayout, SheetLayout

STEPS = ("friend", "picture", "stickers", "message")


def step_id(step: str) -> str:
    return f"step.{step}"


def card_id(slot: int) -> str:
    return f"card.{slot}"


@dataclass(frozen=True, slots=True)
class TrayItem:
    """One choice in the composer tray (a kit tile)."""

    control_id: str
    icon: pygame.Surface | None
    on_activate: Callable[[], object]
    selected: bool = False
    enabled: bool = True
    role: ButtonRole = ButtonRole.NEUTRAL


class BadgeButton(IconButton):
    """Small pointer/touch-only shortcut (keyboard users reach the same action
    through a focusable control elsewhere, so it never clutters focus order)."""

    @property
    def focusable(self) -> bool:  # type: ignore[override]
        return False


class PostcardControls:
    """Own the kit controls and the main ``ControlLayer`` for every screen."""

    def __init__(
        self,
        kit: ControlKit,
        *,
        on_step: Callable[[str], object],
        on_send: Callable[[], object],
        on_postbox: Callable[[], object],
        on_new_card: Callable[[], object],
        on_page: Callable[[int], object],
        on_delete_focused: Callable[[], object],
        on_back: Callable[[], object],
        on_flip: Callable[[], object],
        on_share: Callable[[], object],
        on_delete_open: Callable[[], object],
    ) -> None:
        self._kit = kit
        tile = BodyShape.TILE

        def button(control_id: str, callback, *, shape=tile, role=ButtonRole.NEUTRAL) -> IconButton:
            return kit.icon_button(control_id, pygame.Rect(0, 0, 64, 64), icon=None, shape=shape, role=role, on_activate=callback)

        self.steps: ToolStrip = kit.tool_strip(
            "step", [(step, "", None) for step in STEPS], shape=tile, selected="friend", on_select=on_step,
        )
        self.send = button("send", on_send, shape=BodyShape.ROUND, role=ButtonRole.PRIMARY)
        self.mailbox = button("mailbox", on_postbox)
        self.new_card = button("new", on_new_card, role=ButtonRole.PRIMARY)
        self.page_previous = button("page.previous", lambda: on_page(-1))
        self.page_next = button("page.next", lambda: on_page(1))
        self.delete_focused = button("postbox.delete", on_delete_focused)
        self.back = button("back", on_back)
        self.flip = button("flip", on_flip)
        self.share = button("share", on_share)
        self.delete_open = button("card.delete", on_delete_open)
        self.delivered_new = button("delivered.new", on_new_card, role=ButtonRole.PRIMARY)
        self.delivered_mailbox = button("delivered.mailbox", on_postbox)
        self.chip: HudChip = kit.hud_chip("postbox.count", pygame.Rect(0, 0, 160, 60), icon=None, value=0)
        self.tray: list[IconButton] = []
        self.cards: list[ExternalTarget] = []
        self.badges: list[BadgeButton] = []
        self.layer: ControlLayer = kit.layer((), layer_id="posta.controls")
        self.screen = "composer"

    # -- helpers ------------------------------------------------------------------

    def glyph(self, name: str, size: int) -> pygame.Surface | None:
        return self._kit.glyph(name, size)

    def _place(self, control: IconButton, rect: pygame.Rect, glyph: str | pygame.Surface | None, ratio: float = 0.62) -> None:
        control.rect = rect
        if isinstance(glyph, str):
            control.icon = self._kit.glyph(glyph, int(min(rect.width, rect.height) * ratio))
        else:
            control.icon = glyph
        control.visible = True
        control.enabled = True

    def _set(self, targets: Sequence, focus: str | None, *, keep_focus: bool = False) -> None:
        previous = self.layer.focused_id
        visible = self.layer.focus_visible
        self.layer.set_targets(targets)
        ids = {target.control_id for target in targets}
        if keep_focus and previous in ids and self.layer.focus(previous, visible=visible):
            pass
        elif focus is not None and focus in ids:
            self.layer.focus(focus, visible=visible)
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    # -- composer -------------------------------------------------------------------

    def show_composer(
        self,
        layout: ComposerLayout,
        step: str,
        items: Sequence[TrayItem],
        *,
        step_icons: dict[str, pygame.Surface | None],
        mailbox_icon: pygame.Surface | None,
        focus: str | None = None,
        keep_focus: bool = True,
    ) -> None:
        self.screen = "composer"
        for slot, rect in zip(self.steps.slots, layout.steps):
            slot.rect = rect
            slot.icon = step_icons.get(slot.tool_id)
        if self.steps.selected != step:
            self.steps.select(step)
        self._place(self.send, layout.send, "send", 0.56)
        self._place(self.mailbox, layout.mailbox, mailbox_icon, 1.0)
        rects = layout.tiles(len(items))
        self.tray = []
        for item, rect in zip(items, rects):
            control = self._kit.icon_button(
                item.control_id, rect, icon=item.icon, shape=BodyShape.TILE, role=item.role,
                selected=item.selected, on_activate=item.on_activate, enabled=item.enabled,
            )
            self.tray.append(control)
        targets = [*self.steps.controls, self.send, *self.tray, self.mailbox]
        self._set(targets, focus, keep_focus=keep_focus and focus is None)

    def tray_control(self, control_id: str) -> IconButton | None:
        for control in self.tray:
            if control.control_id == control_id:
                return control
        return None

    # -- postbox --------------------------------------------------------------------

    def show_postbox(
        self,
        layout: PostboxLayout,
        cards: Sequence[pygame.Rect],
        *,
        on_card: Callable[[int], object],
        on_card_delete: Callable[[int], object],
        page: int,
        page_count: int,
        used: int,
        capacity: int,
        mailbox_icon: pygame.Surface | None,
        focus_card: int | None = None,
    ) -> None:
        self.screen = "postbox"
        self._place(self.new_card, layout.new_card, "new", 0.6)
        self.chip.rect = layout.chip
        self.chip.icon = mailbox_icon
        self.chip.value = f"{used}/{capacity}"
        self.cards = [
            ExternalTarget(card_id(slot), rect, (lambda chosen=slot: on_card(chosen)), focus_radius=14)
            for slot, rect in enumerate(cards)
        ]
        badge = 52
        icon = self._kit.glyph("trash", 30)
        self.badges = [
            BadgeButton(
                self._kit.painter,
                f"card.{slot}.delete",
                pygame.Rect(rect.right - badge + 8, rect.top - 8, badge, badge),
                icon=icon,
                shape=BodyShape.ROUND,
                on_activate=(lambda chosen=slot: on_card_delete(chosen)),
            )
            for slot, rect in enumerate(cards)
        ]
        self._place(self.page_previous, layout.previous, "arrow_left", 0.5)
        self._place(self.page_next, layout.next, "arrow_right", 0.5)
        self.page_previous.visible = self.page_next.visible = page_count > 1
        self.page_previous.enabled = page > 0
        self.page_next.enabled = page < page_count - 1
        self._place(self.delete_focused, layout.delete, "trash", 0.56)
        self.delete_focused.visible = bool(cards)
        targets = [
            self.chip,
            self.new_card,
            *self.cards,
            *self.badges,
            self.page_previous,
            *([self.delete_focused] if cards else []),
            self.page_next,
        ]
        focus = card_id(focus_card) if focus_card is not None and focus_card < len(cards) else None
        self._set(targets, focus or (card_id(0) if cards else "new"))

    def focused_card_slot(self) -> int | None:
        focused = self.layer.focused_id
        if focused and focused.startswith("card.") and focused.count(".") == 1:
            return int(focused.split(".")[1])
        return None

    # -- one card ----------------------------------------------------------------------

    def show_card(self, layout: CardViewLayout, *, shared_available: bool, focus: str | None = None) -> None:
        self.screen = "card"
        self._place(self.back, layout.back, "arrow_left", 0.56)
        self._place(self.flip, layout.flip, "rotate", 0.58)
        self._place(self.share, layout.share, "share", 0.58)
        self._place(self.delete_open, layout.delete, "trash", 0.56)
        self.share.visible = shared_available
        targets = [self.back, self.flip, *([self.share] if shared_available else []), self.delete_open]
        self._set(targets, focus or "flip", keep_focus=focus is None)

    # -- delivered ----------------------------------------------------------------------

    def show_delivered(self, layout: DeliveredLayout, *, mailbox_icon: pygame.Surface | None) -> None:
        self.screen = "delivered"
        self._place(self.delivered_new, layout.new_card, "new", 0.56)
        self._place(self.delivered_mailbox, layout.mailbox, mailbox_icon, 1.0)
        self._set([self.delivered_mailbox, self.delivered_new], "delivered.new")

    def hide_all(self) -> None:
        """No controls (the postcard is flying)."""

        self.screen = "sending"
        self._set([], None)


class PostcardSheet(Overlay):
    """Small modal sheet: its own ``ControlLayer`` above a drawn backdrop.

    A pointer press and release outside ``panel`` (or CANCEL — Escape / east
    face button) chooses the safe option, so a child can always back out.
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

    def dismiss(self) -> None:
        """Choose the safe option (Escape / back)."""

        self._on_dismiss()

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
        if isinstance(event, SemanticInputEvent) and event.edge is InputEdge.PRESSED and event.action is SemanticAction.CANCEL:
            self._on_dismiss()
            return UiEventResult.HANDLED
        self.layer.handle_event(event)
        return UiEventResult.HANDLED

    def draw(self, target: object) -> None:
        assert isinstance(target, pygame.Surface)
        self._draw_backdrop(target)
        self.layer.draw(target)


class PostcardSheets:
    """Build the two modal sheets from kit controls (word-free)."""

    def __init__(self, kit: ControlKit, layout: SheetLayout) -> None:
        self._kit = kit
        self.layout = layout

    def delete(
        self,
        *,
        draw_backdrop: Callable[[pygame.Surface], object],
        on_keep: Callable[[], object],
        on_delete: Callable[[], object],
    ) -> PostcardSheet:
        layout = self.layout
        keep = self._kit.icon_button(
            "delete.keep", layout.left, icon=self._kit.glyph("arrow_left", 60), shape=BodyShape.TILE, on_activate=on_keep,
        )
        confirm = self._kit.icon_button(
            "delete.confirm", layout.right, icon=self._kit.glyph("trash", 60), shape=BodyShape.TILE,
            role=ButtonRole.PRIMARY, on_activate=on_delete,
        )
        layer = self._kit.layer([keep, confirm], layer_id="posta.delete")
        layer.focus("delete.keep", visible=True)
        return PostcardSheet("posta.delete", layer, layout.panel, on_dismiss=on_keep, draw_backdrop=draw_backdrop)

    def full(
        self,
        *,
        mailbox_icon: pygame.Surface | None,
        draw_backdrop: Callable[[pygame.Surface], object],
        on_postbox: Callable[[], object],
        on_keep: Callable[[], object],
    ) -> PostcardSheet:
        layout = self.layout
        keep = self._kit.icon_button(
            "full.keep", layout.left, icon=self._kit.glyph("arrow_left", 60), shape=BodyShape.TILE, on_activate=on_keep,
        )
        postbox = self._kit.icon_button(
            "full.postbox", layout.right, icon=mailbox_icon, shape=BodyShape.TILE, role=ButtonRole.PRIMARY,
            on_activate=on_postbox,
        )
        layer = self._kit.layer([keep, postbox], layer_id="posta.full")
        layer.focus("full.postbox", visible=True)
        return PostcardSheet("posta.full", layer, layout.panel, on_dismiss=on_keep, draw_backdrop=draw_backdrop)


__all__ = [
    "BadgeButton",
    "PostcardControls",
    "PostcardSheet",
    "PostcardSheets",
    "STEPS",
    "TrayItem",
    "card_id",
    "step_id",
]

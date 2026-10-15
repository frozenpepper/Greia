"""Shared control-kit wiring for Stories of My Voice (ADR 0037).

Every interactive element is a kit control or a kit ``ExternalTarget`` in one
``ControlLayer``, so pointer, touch, keyboard and controller share the same
focus ring and activation:

* picker — five story tiles (first card + one dot per card) and the
  My-stories tile (book + a 12-dot shelf meter);
* order — every card in the tray and every numbered slot are
  ``ExternalTarget``s (Space/Enter/south places or returns a card; pointer
  users can also drag), a hint button and the stories button;
* tell — microphone (mic / stop), play, redo, previous / next card arrows and
  progress dots;
* watch — replay and share-to-My-Creations;
* shelf — saved story cards (activate = watch), pointer-only trash badges,
  page arrows and a trash tile for the focused card, new story / save.

Sheets (delete confirmation, shelf full) are modal ``Overlay``s with their own
small layer. No control shows words: glyphs come from the shared
``icon.hud.*`` set and library pictures.
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
    ProgressDots,
)
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.ui_core import Overlay, UiEventResult

if __package__:
    from .voice_layout import OrderLayout, PickerLayout, SheetLayout, ShelfLayout, TellLayout, WatchLayout
else:
    from voice_layout import OrderLayout, PickerLayout, SheetLayout, ShelfLayout, TellLayout, WatchLayout


class BadgeButton(IconButton):
    """Small pointer/touch-only shortcut (keyboard users reach the same action
    through a focusable control elsewhere, so it never clutters focus order)."""

    @property
    def focusable(self) -> bool:  # type: ignore[override]
        return False


def tray_id(card_id: str) -> str:
    return f"tray.{card_id}"


def slot_id(index: int) -> str:
    return f"slot.{index}"


def tile_id(index: int) -> str:
    return f"story.{index}"


def shelf_card_id(slot: int) -> str:
    return f"card.{slot}"


class StoryControls:
    """Own the kit controls and the main ``ControlLayer`` for every screen."""

    def __init__(
        self,
        kit: ControlKit,
        *,
        on_picker: Callable[[], object],
        on_shelf: Callable[[], object],
        on_hint: Callable[[], object],
        on_mic: Callable[[], object],
        on_play: Callable[[], object],
        on_redo: Callable[[], object],
        on_previous: Callable[[], object],
        on_next: Callable[[], object],
        on_replay: Callable[[], object],
        on_share: Callable[[], object],
        on_page: Callable[[int], object],
        on_delete_focused: Callable[[], object],
        on_save_pending: Callable[[], object],
    ) -> None:
        self._kit = kit
        tile = BodyShape.TILE
        primary = ButtonRole.PRIMARY

        def button(control_id: str, callback, *, shape=BodyShape.ROUND, role=ButtonRole.NEUTRAL) -> IconButton:
            return kit.icon_button(control_id, pygame.Rect(0, 0, 64, 64), icon=None, shape=shape, role=role, on_activate=callback)

        self.picker = button("picker", on_picker, shape=tile)
        self.shelf = button("shelf", on_shelf, shape=tile)
        self.hint = button("hint", on_hint)
        self.mic = button("mic", on_mic, role=primary)
        self.play = button("play", on_play)
        self.redo = button("redo", on_redo)
        self.previous = button("previous", on_previous, shape=tile)
        self.next = button("next", on_next, shape=tile, role=primary)
        self.replay = button("replay", on_replay)
        self.share = button("share", on_share)
        self.page_previous = button("page.previous", lambda: on_page(-1), shape=tile)
        self.page_next = button("page.next", lambda: on_page(1), shape=tile)
        self.delete_focused = button("shelf.delete", on_delete_focused, shape=tile)
        self.new_story = button("shelf.new", on_picker, shape=tile, role=primary)
        self.save_pending = button("shelf.save", on_save_pending, shape=tile, role=primary)
        self.dots: ProgressDots = kit.progress_dots("dots", pygame.Rect(0, 0, 120, 40), total=4)
        self.tiles: list[IconButton] = []
        self.cards: list[ExternalTarget] = []
        self.slots: list[ExternalTarget] = []
        self.badges: list[BadgeButton] = []
        self.layer: ControlLayer = kit.layer((), layer_id="storie.controls")
        self.screen = "picker"

    # -- helpers ------------------------------------------------------------

    def glyph(self, name: str, size: int) -> pygame.Surface | None:
        return self._kit.glyph(name, size)

    def _place(self, control: IconButton, rect: pygame.Rect, glyph: str | pygame.Surface | None, ratio: float = 0.6) -> None:
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

    # -- screens --------------------------------------------------------------

    def show_picker(
        self,
        layout: PickerLayout,
        covers: Sequence[pygame.Surface | None],
        shelf_icon: pygame.Surface | None,
        on_story: Callable[[int], object],
        *,
        focus: int = 0,
    ) -> None:
        self.screen = "picker"
        self.tiles = [
            self._kit.icon_button(
                tile_id(index), rect, icon=icon, shape=BodyShape.TILE,
                on_activate=(lambda chosen=index: on_story(chosen)),
            )
            for index, (icon, rect) in enumerate(zip(covers, layout.tiles))
        ]
        self._place(self.shelf, layout.tiles[len(covers)], shelf_icon)
        self._set([*self.tiles, self.shelf], tile_id(focus))

    def show_order(
        self,
        layout: OrderLayout,
        tray_cards: Sequence[str],
        *,
        on_tray: Callable[[str], object],
        on_slot: Callable[[int], object],
        picker_icon: pygame.Surface | None,
    ) -> None:
        self.screen = "order"
        self.cards = [
            ExternalTarget(tray_id(card), rect, (lambda chosen=card: on_tray(chosen)), focus_radius=14)
            for card, rect in zip(tray_cards, layout.tray)
        ]
        self.slots = [
            ExternalTarget(slot_id(index), rect, (lambda chosen=index: on_slot(chosen)), focus_radius=14)
            for index, rect in enumerate(layout.slots)
        ]
        top = layout.top
        self._place(self.hint, top.right(0, top.bar.height), "hint")
        self._place(self.picker, top.right(1, top.bar.height), picker_icon, 0.7)
        self._set([self.picker, self.hint, *self.slots, *self.cards], tray_id(tray_cards[0]) if tray_cards else None)

    def sync_order(self, *, tray: Sequence[str | None], slots: Sequence[str | None], locked: set[int], busy: bool, layout: OrderLayout) -> None:
        """Mirror the board: tray targets follow their cards; slots their cards."""

        for target in self.cards:
            card = target.control_id.split(".", 1)[1]
            target.enabled = not busy and card in tray
        for index, target in enumerate(self.slots):
            target.enabled = not busy and (slots[index] is None or index not in locked)
        self.hint.enabled = not busy
        if not self._focused_is_live():
            live = [t.control_id for t in self.cards if t.enabled] or [t.control_id for t in self.slots if t.enabled]
            if live:
                self.layer.focus(live[0])
        self.layer.invalidation.invalidate()

    def show_tell(self, layout: TellLayout, count: int, *, picker_icon: pygame.Surface | None) -> None:
        self.screen = "tell"
        self._place(self.mic, layout.mic, "mic", 0.56)
        self._place(self.play, layout.play, "play", 0.5)
        self._place(self.redo, layout.redo, "redo", 0.5)
        self._place(self.previous, layout.previous, "arrow_left", 0.56)
        self._place(self.next, layout.following, "arrow_right", 0.56)
        self.dots = self._kit.progress_dots("dots", layout.dots, total=max(1, count))
        top = layout.top
        self._place(self.picker, top.right(0, top.bar.height), picker_icon, 0.7)
        self._set([self.picker, self.mic, self.play, self.redo, self.previous, self.dots, self.next], "mic")

    def sync_tell(self, *, index: int, count: int, recording: bool, counting: bool, has_voice: bool, last: bool, busy: bool) -> None:
        mic_glyph = "stop" if (recording or counting) else "mic"
        size = int(min(self.mic.rect.width, self.mic.rect.height) * 0.56)
        self.mic.icon = self._kit.glyph(mic_glyph, size)
        self.mic.selected = recording
        self.mic.enabled = not busy
        idle = not (recording or counting or busy)
        self.play.visible = has_voice
        self.redo.visible = has_voice
        self.play.enabled = self.redo.enabled = idle
        self.previous.enabled = idle and index > 0
        self.next.enabled = idle
        next_size = int(min(self.next.rect.width, self.next.rect.height) * 0.56)
        self.next.icon = self._kit.glyph("check" if last else "arrow_right", next_size)
        self.dots.set_progress(index)
        if not self._focused_is_live():
            self.layer.focus("mic")
        self.layer.invalidation.invalidate()

    def show_watch(self, layout: WatchLayout, count: int, *, top_icon: pygame.Surface | None, share: bool) -> None:
        self.screen = "watch"
        self._place(self.replay, layout.replay, "replay", 0.52)
        self._place(self.share, layout.share, "share", 0.52)
        self.share.visible = share
        self.dots = self._kit.progress_dots("dots", layout.dots, total=max(1, count))
        top = layout.top
        self._place(self.picker, top.right(0, top.bar.height), top_icon, 0.7)
        targets = [self.picker, self.replay, *([self.share] if share else []), self.dots]
        self._set(targets, "replay")

    def sync_watch(self, *, index: int, playing: bool, shared: bool, share_visible: bool) -> None:
        self.dots.set_progress(index)
        self.replay.enabled = not playing
        self.share.visible = share_visible
        self.share.selected = shared
        size = int(min(self.share.rect.width, self.share.rect.height) * 0.52)
        self.share.icon = self._kit.glyph("check" if shared else "share", size)
        self.share.enabled = share_visible and not shared
        if not self._focused_is_live():
            self.layer.focus("replay" if self.replay.enabled else "picker")
        self.layer.invalidation.invalidate()

    def show_shelf(
        self,
        layout: ShelfLayout,
        cards: Sequence[pygame.Rect],
        *,
        page: int,
        page_count: int,
        on_card: Callable[[int], object],
        on_card_delete: Callable[[int], object],
        pending: bool,
        can_save: bool,
        focus_card: int | None = None,
    ) -> None:
        self.screen = "shelf"
        self.cards = [
            ExternalTarget(shelf_card_id(slot), rect, (lambda chosen=slot: on_card(chosen)), focus_radius=16)
            for slot, rect in enumerate(cards)
        ]
        badge = 60
        trash = self._kit.glyph("trash", 34)
        self.badges = [
            BadgeButton(
                self._kit.painter,
                f"{shelf_card_id(slot)}.delete",
                pygame.Rect(rect.right - badge + 14, rect.top - 16, badge, badge),
                icon=trash,
                shape=BodyShape.ROUND,
                on_activate=(lambda chosen=slot: on_card_delete(chosen)),
            )
            for slot, rect in enumerate(cards)
        ]
        self._place(self.page_previous, layout.previous, "arrow_left", 0.56)
        self._place(self.page_next, layout.following, "arrow_right", 0.56)
        self.page_previous.visible = self.page_next.visible = page_count > 1
        self.page_previous.enabled = page > 0
        self.page_next.enabled = page < page_count - 1
        self._place(self.delete_focused, layout.delete, "trash", 0.56)
        self.delete_focused.visible = bool(cards)
        top = layout.top
        self._place(self.new_story, top.right(0, top.bar.height), "new", 0.6)
        self._place(self.save_pending, top.right(1, top.bar.height), "save", 0.6)
        self.save_pending.visible = pending
        self.save_pending.enabled = pending and can_save
        targets = [
            *([self.save_pending] if pending else []),
            self.new_story,
            *self.cards,
            *self.badges,
            self.page_previous,
            *([self.delete_focused] if cards else []),
            self.page_next,
        ]
        focus = shelf_card_id(focus_card) if focus_card is not None and focus_card < len(cards) else None
        if focus is None:
            focus = "shelf.save" if pending and can_save else (shelf_card_id(0) if cards else "shelf.new")
        self._set(targets, focus)

    def focused_shelf_slot(self) -> int | None:
        focused = self.layer.focused_id
        if focused and focused.startswith("card.") and focused.count(".") == 1:
            return int(focused.split(".")[1])
        return None

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        try:
            target = self.layer.target(focused)
        except KeyError:
            return False
        return target.focusable and target.enabled


class StorySheet(Overlay):
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


class StorySheets:
    """Build the two modal sheets from kit controls (word-free)."""

    def __init__(self, kit: ControlKit) -> None:
        self._kit = kit
        self.layout = SheetLayout.build()

    def delete(
        self,
        *,
        draw_backdrop: Callable[[pygame.Surface], object],
        on_keep: Callable[[], object],
        on_delete: Callable[[], object],
    ) -> StorySheet:
        layout = self.layout
        icon = 64
        keep = self._kit.icon_button(
            "delete.keep", layout.left, icon=self._kit.glyph("arrow_left", icon), shape=BodyShape.TILE, on_activate=on_keep,
        )
        confirm = self._kit.icon_button(
            "delete.confirm", layout.right, icon=self._kit.glyph("trash", icon), shape=BodyShape.TILE,
            role=ButtonRole.PRIMARY, on_activate=on_delete,
        )
        layer = self._kit.layer([keep, confirm], layer_id="storie.delete")
        layer.focus("delete.keep", visible=True)
        return StorySheet("storie.delete", layer, layout.panel, on_dismiss=on_keep, draw_backdrop=draw_backdrop)

    def full(
        self,
        *,
        shelf_icon: pygame.Surface | None,
        draw_backdrop: Callable[[pygame.Surface], object],
        on_shelf: Callable[[], object],
        on_watch: Callable[[], object],
    ) -> StorySheet:
        layout = self.layout
        shelf = self._kit.icon_button(
            "full.shelf", layout.left, icon=shelf_icon, shape=BodyShape.TILE, role=ButtonRole.PRIMARY, on_activate=on_shelf,
        )
        watch = self._kit.icon_button(
            "full.watch", layout.right, icon=self._kit.glyph("play", 60), shape=BodyShape.TILE, on_activate=on_watch,
        )
        layer = self._kit.layer([shelf, watch], layer_id="storie.full")
        layer.focus("full.shelf", visible=True)
        return StorySheet("storie.full", layer, layout.panel, on_dismiss=on_watch, draw_backdrop=draw_backdrop)


__all__ = [
    "BadgeButton",
    "StoryControls",
    "StorySheet",
    "StorySheets",
    "shelf_card_id",
    "slot_id",
    "tile_id",
    "tray_id",
]

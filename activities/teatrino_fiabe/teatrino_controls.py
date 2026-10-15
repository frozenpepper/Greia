"""Shared control-kit wiring for Teatrino (ADR 0037).

Every control is a kit control (or a kit ``ExternalTarget``), so one
``ControlLayer`` gives pointer, touch, keyboard and controller access with
the same focus ring, and nothing is a word:

* top bar - my shows (a little stage), scene (the current backdrop's own
  thumbnail), clear the stage (broom), the voice choice (microphone on /
  off / a voice from My Creations) and the big record / stop button;
* sound stickers - six round picture buttons over the curtains;
* puppets on stage - focus-only ``PuppetTarget``s: keyboard/controller can
  pick one up, move it and put it down; pointer drags stay with the app;
* the puppet tray - six picture tiles per page plus page arrows; a tile is
  ``selected`` while that puppet is on stage.

Sheets (library, scenes, delete confirmation, curtain call) are modal
``TheatreSheet`` overlays with their own small ``ControlLayer``.
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
    from .teatrino_art import TeatrinoArt
    from .teatrino_content import FX, MAX_SAVED_SHOWS, PUPPETS, TRAY_PAGE_SIZE, TRAY_PAGES
    from .teatrino_layout import DialogLayout, GridLayout, TheatreLayout
else:  # pragma: no cover - runtime/script fallback
    from teatrino_art import TeatrinoArt
    from teatrino_content import FX, MAX_SAVED_SHOWS, PUPPETS, TRAY_PAGE_SIZE, TRAY_PAGES
    from teatrino_layout import DialogLayout, GridLayout, TheatreLayout


class StageMode:
    """What the stage screen is doing (drives which controls are live)."""

    EDIT = "edit"
    COUNTDOWN = "countdown"
    RECORDING = "recording"
    WATCHING = "watching"


class PuppetTarget(ExternalTarget):
    """A puppet on stage as a focus target only.

    ``contains`` is always False so pointer presses fall through the kit to
    the app's drag handling; keyboard/controller focus still lands on the
    puppet (by its rect) and ACTIVATE picks it up / puts it down.
    """

    def contains(self, point: tuple[int, int]) -> bool:  # noqa: ARG002 - pointer goes to drag
        return False


class BadgeButton(IconButton):
    """Small pointer/touch-only shortcut (keyboard users reach the same action
    through a focusable control elsewhere, so it never clutters focus order)."""

    @property
    def focusable(self) -> bool:  # type: ignore[override]
        return False


class TheatreControls:
    """Own the stage screen's kit controls and its ``ControlLayer``."""

    def __init__(
        self,
        kit: ControlKit,
        art: TeatrinoArt,
        layout: TheatreLayout,
        *,
        on_shows: Callable[[], object],
        on_scene: Callable[[], object],
        on_clear: Callable[[], object],
        on_mic: Callable[[], object],
        on_rec: Callable[[], object],
        on_fx: Callable[[str], object],
        on_card: Callable[[str], object],
        on_page: Callable[[int], object],
        on_puppet: Callable[[str], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self._on_card = on_card
        self._on_puppet = on_puppet
        tile, round_ = BodyShape.TILE, BodyShape.ROUND
        blank = pygame.Rect(0, 0, 10, 10)
        self.shows = kit.icon_button("top.shows", blank, icon=None, shape=tile, on_activate=on_shows)
        self.scene = kit.icon_button("top.scene", blank, icon=None, shape=tile, on_activate=on_scene)
        self.clear = kit.icon_button("top.clear", blank, icon=None, shape=tile, on_activate=on_clear)
        self.mic = kit.icon_button("top.mic", blank, icon=None, shape=tile, on_activate=on_mic)
        self.rec = kit.icon_button("top.rec", blank, icon=None, shape=tile, on_activate=on_rec)
        self.fx = tuple(
            kit.icon_button(f"fx.{spec.sound}", blank, icon=None, shape=round_, on_activate=(lambda s=spec.sound: on_fx(s)))
            for spec in FX
        )
        self.tray_prev = kit.icon_button("tray.prev", blank, icon=None, shape=tile, on_activate=lambda: on_page(-1))
        self.tray_next = kit.icon_button("tray.next", blank, icon=None, shape=tile, on_activate=lambda: on_page(1))
        self.cards: list[IconButton] = [
            kit.icon_button(f"tray.card.{index}", blank, icon=None, shape=tile, on_activate=(lambda i=index: self._card(i)))
            for index in range(TRAY_PAGE_SIZE)
        ]
        self.puppets: list[PuppetTarget] = []
        self.layer: ControlLayer = kit.layer((), layer_id="teatrino.stage")
        self.layout = layout
        self.page = 0
        self.mode = StageMode.EDIT
        self.relayout(layout)

    # -- geometry ------------------------------------------------------------

    def relayout(self, layout: TheatreLayout) -> None:
        """Re-read every rect and rescale icons once (after a resize)."""

        self.layout = layout
        kit, art = self._kit, self._art
        icon = int(layout.control * 0.64)
        for button, rect in (
            (self.shows, layout.shows),
            (self.scene, layout.scene),
            (self.clear, layout.clear),
            (self.mic, layout.mic),
            (self.rec, layout.rec),
        ):
            button.rect = rect
        self.shows.icon = art.private_icon("tool_shows", icon) or kit.glyph("play", icon)
        self.clear.icon = kit.glyph("clear", icon)
        for button, rect, spec in zip(self.fx, layout.fx, FX):
            button.rect = rect
            button.icon = art.fx_icon(spec, int(rect.height * 0.62))
        self.tray_prev.rect = layout.tray_prev
        self.tray_next.rect = layout.tray_next
        arrow = int(min(layout.tray_prev.width, layout.tray_prev.height) * 0.62)
        self.tray_prev.icon = kit.glyph("arrow_left", arrow)
        self.tray_next.icon = kit.glyph("arrow_right", arrow)
        for card, rect in zip(self.cards, layout.cards):
            card.rect = rect
        self._fill_cards(())
        self._rebuild()

    # -- state -----------------------------------------------------------------

    def page_ids(self) -> list[str]:
        start = self.page * TRAY_PAGE_SIZE
        return [spec.puppet_id for spec in PUPPETS[start : start + TRAY_PAGE_SIZE]]

    def set_page(self, page: int, on_stage: Sequence[str]) -> None:
        self.page = page % TRAY_PAGES
        self._fill_cards(on_stage)

    def _fill_cards(self, on_stage: Sequence[str]) -> None:
        ids = self.page_ids()
        height = int(self.layout.cards[0].height * 0.78)
        for index, card in enumerate(self.cards):
            if index < len(ids):
                card.visible = True
                card.icon = self._art.puppet_icon(ids[index], height)
                card.selected = ids[index] in on_stage
            else:
                card.visible = False
        self.layer.invalidation.invalidate()

    def sync_cards(self, on_stage: Sequence[str]) -> None:
        ids = self.page_ids()
        for index, card in enumerate(self.cards):
            if index < len(ids):
                card.selected = ids[index] in on_stage
        self.layer.invalidation.invalidate()

    def card_puppet(self, index: int) -> str | None:
        ids = self.page_ids()
        return ids[index] if 0 <= index < len(ids) else None

    def card_for(self, puppet_id: str) -> IconButton | None:
        ids = self.page_ids()
        return self.cards[ids.index(puppet_id)] if puppet_id in ids else None

    def _card(self, index: int) -> None:
        puppet_id = self.card_puppet(index)
        if puppet_id is not None:
            self._on_card(puppet_id)

    def set_scene_icon(self, thumbnail: pygame.Surface | None) -> None:
        self.scene.icon = thumbnail
        self.layer.invalidation.invalidate()

    def set_mic_state(self, state: str) -> None:
        """``on`` / ``off`` / ``imported`` (a voice picked from My Creations)."""

        icon = int(self.layout.control * 0.64)
        if state == "imported":
            self.mic.icon = self._art.icon("ui.pictogram.creation", icon, variant="audio")
        else:
            self.mic.icon = self._kit.glyph("mic" if state == "on" else "mic_off", icon)
        self.mic.selected = state == "imported"
        self.layer.invalidation.invalidate()

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        icon = int(self.layout.control * 0.62)
        self.rec.icon = self._kit.glyph("stop" if mode in (StageMode.RECORDING, StageMode.WATCHING) else "rec", icon)
        self._rebuild()

    def set_puppets(self, rects: Sequence[tuple[str, pygame.Rect]]) -> None:
        """Mirror the puppets on stage as focus-only targets (cheap; per change)."""

        if [t.control_id for t in self.puppets] == [f"puppet.{pid}" for pid, _ in rects]:
            for target, (_pid, rect) in zip(self.puppets, rects):
                target._rect = pygame.Rect(rect)  # noqa: SLF001 - ExternalTarget has no rect setter
            return
        self.puppets = [
            PuppetTarget(f"puppet.{pid}", rect, (lambda p=pid: self._on_puppet(p)), focus_radius=28)
            for pid, rect in rects
        ]
        self._rebuild()

    def _rebuild(self) -> None:
        mode = self.mode
        editing = mode == StageMode.EDIT
        recording = mode == StageMode.RECORDING
        for button in (self.shows, self.scene, self.clear, self.mic):
            button.visible = mode != StageMode.WATCHING
            button.enabled = editing
        self.rec.visible = True
        self.rec.enabled = mode != StageMode.COUNTDOWN
        for button in self.fx:
            button.visible = mode != StageMode.WATCHING
            button.enabled = editing or recording
        for button in (self.tray_prev, self.tray_next, *self.cards):
            if mode == StageMode.WATCHING:
                button.visible = False
        if mode != StageMode.WATCHING:
            self.tray_prev.visible = self.tray_next.visible = True
            ids = self.page_ids()
            for index, card in enumerate(self.cards):
                card.visible = index < len(ids)
        for button in (self.tray_prev, self.tray_next, *self.cards):
            button.enabled = editing or recording
        for target in self.puppets:
            target.enabled = editing or recording
        targets = [
            self.shows,
            self.scene,
            self.clear,
            self.mic,
            self.rec,
            *self.fx,
            *self.puppets,
            self.tray_prev,
            *self.cards,
            self.tray_next,
        ]
        focused = self.layer.focused_id
        visible = self.layer.focus_visible
        self.layer.set_targets(targets)
        if focused is not None and focused in {t.control_id for t in targets}:
            self.layer.focus(focused, visible=visible)
        self.layer.invalidation.invalidate()


# ---------------------------------------------------------------------------
# Sheets
# ---------------------------------------------------------------------------


class TheatreSheet(Overlay):
    """Small modal sheet: its own ``ControlLayer`` above a drawn backdrop.

    A pointer press and release outside ``panel`` (or CANCEL - Escape / east
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
        draw_front: Callable[[pygame.Surface], object] | None = None,
    ) -> None:
        self._id = sheet_id
        self.layer = layer
        self.panel = pygame.Rect(panel)
        self._on_dismiss = on_dismiss
        self._draw_backdrop = draw_backdrop
        self._draw_front = draw_front
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
        if self._draw_front is not None:
            self._draw_front(target)


class LibraryControls:
    """The saved-shows sheet: poster tiles, delete badges, paging, shelf dots."""

    def __init__(
        self,
        kit: ControlKit,
        grid: GridLayout,
        *,
        on_close: Callable[[], object],
        on_open: Callable[[int], object],
        on_delete: Callable[[int], object],
        on_delete_focused: Callable[[], object],
        on_page: Callable[[int], object],
        on_record: Callable[[], object],
    ) -> None:
        self._kit = kit
        self.grid = grid
        icon = int(grid.close.height * 0.62)
        self.close = kit.icon_button("library.close", grid.close, icon=kit.glyph("check", icon), shape=BodyShape.TILE, on_activate=on_close)
        dots_h = max(26, int(grid.header.height * 0.42))
        dots_w = ProgressDots.preferred_width(MAX_SAVED_SHOWS, dots_h)
        dots_rect = pygame.Rect(0, 0, dots_w, dots_h)
        dots_rect.midleft = (grid.header.x + 6, grid.header.centery)
        self.shelf = kit.progress_dots("library.shelf", dots_rect, total=MAX_SAVED_SHOWS)
        self.previous = kit.icon_button(
            "library.prev", grid.previous, icon=kit.glyph("arrow_left", icon), shape=BodyShape.TILE, on_activate=lambda: on_page(-1)
        )
        self.following = kit.icon_button(
            "library.next", grid.following, icon=kit.glyph("arrow_right", icon), shape=BodyShape.TILE, on_activate=lambda: on_page(1)
        )
        self.delete_focused = kit.icon_button(
            "library.delete", grid.action, icon=kit.glyph("trash", icon), shape=BodyShape.TILE, on_activate=on_delete_focused
        )
        self.record = kit.icon_button(
            "library.record",
            grid.cards[0].union(grid.cards[min(len(grid.cards) - 1, 1)]),
            icon=kit.glyph("rec", int(grid.cards[0].height * 0.62)),
            shape=BodyShape.TILE,
            on_activate=on_record,
        )
        self._on_open = on_open
        self._on_delete = on_delete
        self.cards: list[IconButton] = []
        self.badges: list[BadgeButton] = []
        self.layer: ControlLayer = kit.layer((), layer_id="teatrino.library")

    def sync(self, posters: Sequence[pygame.Surface | None], *, first_index: int, page: int, pages: int, count: int) -> None:
        kit = self._kit
        # Pointer shortcut; never smaller than ~3/4 of the physical touch floor.
        badge_size = max(int(self.grid.cards[0].height * 0.32), int(self.grid.close.height * 0.8))
        trash = kit.glyph("trash", int(badge_size * 0.6))
        self.cards = []
        self.badges = []
        for slot, (rect, poster) in enumerate(zip(self.grid.cards, posters)):
            index = first_index + slot
            self.cards.append(
                kit.icon_button(f"library.card.{slot}", rect, icon=poster, shape=BodyShape.TILE, on_activate=(lambda i=index: self._on_open(i)))
            )
            badge = BadgeButton(
                kit.painter,
                f"library.card.{slot}.delete",
                pygame.Rect(rect.right - badge_size + 8, rect.top - 8, badge_size, badge_size),
                icon=trash,
                shape=BodyShape.ROUND,
                on_activate=(lambda i=index: self._on_delete(i)),
            )
            self.badges.append(badge)
        self.shelf.set_progress(count)
        self.previous.visible = self.following.visible = pages > 1
        self.previous.enabled = page > 0
        self.following.enabled = page < pages - 1
        self.delete_focused.visible = count > 0
        self.record.visible = count == 0
        focused = self.layer.focused_id
        visible = self.layer.focus_visible
        targets = [
            self.shelf,
            self.close,
            *([self.record] if self.record.visible else []),
            *self.cards,
            *self.badges,
            self.previous,
            self.delete_focused,
            self.following,
        ]
        self.layer.set_targets(targets)
        if focused is not None and focused in {t.control_id for t in targets}:
            self.layer.focus(focused, visible=visible)
        self.layer.invalidation.invalidate()

    def focused_slot(self) -> int | None:
        focused = self.layer.focused_id
        if focused and focused.startswith("library.card.") and focused.count(".") == 2:
            return int(focused.rsplit(".", 1)[1])
        return None


def scene_sheet_layer(
    kit: ControlKit,
    grid: GridLayout,
    thumbnails: Sequence[tuple[str, pygame.Surface | None, bool]],
    *,
    on_choose: Callable[[str], object],
    on_close: Callable[[], object],
) -> ControlLayer:
    """Scene cards (current one selected) plus the close tile."""

    icon = int(grid.close.height * 0.62)
    close = kit.icon_button("scene.close", grid.close, icon=kit.glyph("check", icon), shape=BodyShape.TILE, on_activate=on_close)
    cards = [
        kit.icon_button(
            f"scene.{scene_id}", rect, icon=thumb, shape=BodyShape.TILE, selected=selected,
            on_activate=(lambda chosen=scene_id: on_choose(chosen)),
        )
        for (scene_id, thumb, selected), rect in zip(thumbnails, grid.cards)
    ]
    layer = kit.layer([close, *cards], layer_id="teatrino.scenes")
    current = next((f"scene.{sid}" for sid, _thumb, selected in thumbnails if selected), None)
    layer.focus(current or f"scene.{thumbnails[0][0]}")
    return layer


def dialog_layer(
    kit: ControlKit,
    dialog: DialogLayout,
    buttons: Sequence[tuple[str, str, ButtonRole, Callable[[], object]]],
    *,
    layer_id: str,
    focus: str,
) -> ControlLayer:
    """Big pictogram buttons along the bottom of a dialog."""

    controls = []
    for (control_id, glyph, role, action), rect in zip(buttons, dialog.buttons):
        icon = kit.glyph(glyph, int(rect.height * 0.6)) if glyph else None
        controls.append(kit.icon_button(control_id, rect, icon=icon, shape=BodyShape.TILE, role=role, on_activate=action))
    layer = kit.layer(controls, layer_id=layer_id)
    layer.focus(focus, visible=False)
    return layer


__all__ = [
    "BadgeButton",
    "LibraryControls",
    "PuppetTarget",
    "StageMode",
    "TheatreControls",
    "TheatreSheet",
    "dialog_layer",
    "scene_sheet_layer",
]

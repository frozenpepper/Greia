"""Shared control-kit wiring for Magic Bakery (ADR 0037).

Every interactive element goes through ``greia_platform.activity_controls``:

* the pantry - one picture tile per topping (shared ``prop.food.*`` art, no
  words); only the toppings of the current order are shown;
* take one off (``undo`` glyph) and the serve bell (primary, on the counter);
* ``ProgressDots`` for the five customers of a round;
* in the make-your-own-cake ending: the whole pantry, take one off, Save to
  My Creations (primary, ``share`` glyph), a new cake and play again.

Keyboard / D-pad / stick focus and the focus ring come from the kit. Focus
never jumps to the right topping: it starts on the first tile and then stays
where the child left it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pygame

from greia_platform.activity_controls import (
    Align,
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    IconButton,
    ProgressDots,
)

if __package__:
    from .pasticceria_art import BakeryArt
    from .pasticceria_content import ORDERS_PER_ROUND, TOPPING_IDS
    from .pasticceria_layout import SIDE_BUTTON, SIDE_ICON, TILE_ICON, UNDO_ICON, UNDO_RECT, pantry_rects
else:
    from pasticceria_art import BakeryArt
    from pasticceria_content import ORDERS_PER_ROUND, TOPPING_IDS
    from pasticceria_layout import SIDE_BUTTON, SIDE_ICON, TILE_ICON, UNDO_ICON, UNDO_RECT, pantry_rects

BAR_HEIGHT = 64
BAR_ICON = 40


def topping_control(topping_id: str) -> str:
    return f"topping.{topping_id}"


class BakeryControls:
    """Own the kit controls and the single ``ControlLayer`` of every screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: BakeryArt,
        *,
        text: Callable[[str], str],
        on_topping: Callable[[str], object],
        on_undo: Callable[[], object],
        on_serve: Callable[[], object],
        on_save: Callable[[], object],
        on_new_cake: Callable[[], object],
        on_new_round: Callable[[], object],
    ) -> None:
        self._kit = kit
        self.pantry: dict[str, IconButton] = {
            topping_id: kit.icon_button(
                topping_control(topping_id),
                pygame.Rect(0, 0, 10, 10),
                icon=art.topping(topping_id, TILE_ICON),
                shape=BodyShape.TILE,
                on_activate=(lambda t=topping_id: on_topping(t)),
            )
            for topping_id in TOPPING_IDS
        }
        self.undo: IconButton = kit.icon_button("undo", UNDO_RECT, icon=kit.glyph("undo", UNDO_ICON), on_activate=on_undo)
        self.serve: IconButton = kit.icon_button(
            "serve",
            SIDE_BUTTON,
            icon=kit.glyph("bell", SIDE_ICON),
            caption=text("action.serve"),
            shape=BodyShape.TILE,
            role=ButtonRole.PRIMARY,
            on_activate=on_serve,
        )
        self.save: IconButton = kit.icon_button(
            "save",
            SIDE_BUTTON,
            icon=kit.glyph("share", SIDE_ICON),
            caption=text("action.save"),
            shape=BodyShape.TILE,
            role=ButtonRole.PRIMARY,
            on_activate=on_save,
        )
        self.new_cake: IconButton = kit.icon_button(
            "new_cake", pygame.Rect(0, 0, 10, 10), icon=kit.glyph("new", BAR_ICON), on_activate=on_new_cake
        )
        self.new_round: IconButton = kit.icon_button(
            "new_round",
            pygame.Rect(0, 0, 10, 10),
            icon=kit.glyph("replay", BAR_ICON),
            role=ButtonRole.PRIMARY,
            on_activate=on_new_round,
        )
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 120, 40), total=ORDERS_PER_ROUND)
        self.layer: ControlLayer = kit.layer((), layer_id="pasticceria.controls")
        self._layout: ControlLayout | None = None
        self._visible_pantry: tuple[str, ...] = ()
        self._free = False

    # -- layout -----------------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Top bar beside the protected chrome: round dots left, ending buttons right."""

        self._layout = layout
        height = layout.control_height(BAR_HEIGHT, maximum=76)
        bar = layout.top_bar(height)
        dots_h = max(34, int(height * 0.62))
        dots_w = ProgressDots.preferred_width(self.progress.total, dots_h)
        self.progress.rect = pygame.Rect(bar.left, bar.centery - dots_h // 2, dots_w, dots_h)
        size = height
        right = layout.row(bar, [size, size], align=Align.END, height=size, gap=12)
        self.new_cake.rect, self.new_round.rect = right
        self.layer.invalidation.invalidate()

    # -- screens ------------------------------------------------------------------------

    def show_round(self, pantry: Sequence[str]) -> None:
        """One order: its pantry tiles, take one off, the serve bell and the dots."""

        self._free = False
        self._place_pantry(tuple(pantry), free=False)
        self.serve.enabled = False
        self.undo.enabled = False
        self._show((*self._pantry_buttons(), self.undo, self.serve, self.progress))

    def show_free(self) -> None:
        """Make your own cake: the whole pantry, take one off, save, new cake, play again."""

        self._free = True
        self._place_pantry(TOPPING_IDS, free=True)
        self._show((*self._pantry_buttons(), self.undo, self.save, self.new_cake, self.new_round))

    def show_none(self) -> None:
        self.layer.set_targets(())
        self.layer.invalidation.invalidate()

    def set_busy(self, busy: bool) -> None:
        """While a scripted moment plays, the counter controls rest."""

        for button in (*self._pantry_buttons(), self.undo, self.serve):
            button.visible = not busy
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def set_cake_state(self, *, can_undo: bool, can_serve: bool) -> None:
        if self.undo.enabled != can_undo or self.serve.enabled != can_serve:
            self.undo.enabled = can_undo
            self.serve.enabled = can_serve
            self.layer.invalidation.invalidate()

    def set_free_state(self, *, can_undo: bool, can_save: bool, can_new: bool, selected: str | None) -> None:
        self.undo.enabled = can_undo
        self.save.enabled = can_save
        self.new_cake.enabled = can_new
        for topping_id, button in self.pantry.items():
            button.selected = topping_id == selected
        self.layer.invalidation.invalidate()

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()

    def tile_rect(self, topping_id: str) -> pygame.Rect | None:
        button = self.pantry.get(topping_id)
        if button is None or not button.visible or topping_id not in self._visible_pantry:
            return None
        return button.rect

    @property
    def visible_pantry(self) -> tuple[str, ...]:
        return self._visible_pantry

    # -- helpers ------------------------------------------------------------------------

    def _place_pantry(self, pantry: tuple[str, ...], *, free: bool) -> None:
        self._visible_pantry = pantry
        for button in self.pantry.values():
            button.visible = False
            button.enabled = False
            button.selected = False
        for topping_id, rect in zip(pantry, pantry_rects(len(pantry), free=free)):
            button = self.pantry[topping_id]
            button.rect = rect
            button.visible = True
            button.enabled = True
        for button in (self.undo, self.serve):
            button.visible = True

    def _pantry_buttons(self) -> tuple[IconButton, ...]:
        return tuple(self.pantry[topping_id] for topping_id in self._visible_pantry)

    def _show(self, targets) -> None:
        focused, visible = self.layer.focused_id, self.layer.focus_visible
        self.layer.set_targets(targets)
        first = topping_control(self._visible_pantry[0]) if self._visible_pantry else None
        if focused is None or not self.layer.focus(focused, visible=visible):
            self.layer.focus(first, visible=visible)
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()


__all__ = ["BakeryControls", "topping_control"]

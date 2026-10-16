"""Shared control-kit wiring for Piccola Serra (ADR 0037).

Top bar (beside -- never inside -- the protected Home/Back region):
``ProgressDots`` for the plants of this visit and a round ``hint`` button.

Bottom bar, one row of big picture tiles that changes with the phase:

* choose -- four seed packets, each showing the grown plant in its window;
* grow   -- the care tools (watering can, sun, clock, basket); no tile ever
  marks the right one -- the child reads the plant;
* order  -- the stage cards to put in order (a placed card leaves the row).

All tiles are kit ``IconButton`` TILEs, so pointer, touch, arrows/D-pad/stick
focus and Space/Enter/south-button activation come from the kit.
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
    from .serra_art import SerraArt
    from .serra_content import PLANTS, Care, Stage
    from .serra_layout import board_rect
else:
    from serra_art import SerraArt
    from serra_content import PLANTS, Care, Stage
    from serra_layout import board_rect

ICON_SHARE = 0.74
MAX_TILE = 132
TILE_GAP = 18


class SerraControls:
    """Own the kit controls and the single ``ControlLayer`` of the greenhouse."""

    def __init__(
        self,
        kit: ControlKit,
        art: SerraArt,
        layout: ControlLayout,
        plants: int,
        *,
        on_hint: Callable[[], object],
        on_seed: Callable[[str], object],
        on_care: Callable[[Care], object],
        on_card: Callable[[Stage], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self._on_seed = on_seed
        self._on_care = on_care
        self._on_card = on_card
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=plants)
        self.hint: IconButton = kit.icon_button(
            "hint", pygame.Rect(0, 0, 10, 10), icon=None, role=ButtonRole.PRIMARY, on_activate=on_hint
        )
        self.seeds: dict[str, IconButton] = {
            plant.plant_id: kit.icon_button(
                f"seed.{plant.plant_id}", pygame.Rect(0, 0, 10, 10), icon=None, shape=BodyShape.TILE,
                on_activate=lambda plant_id=plant.plant_id: self._on_seed(plant_id),
            )
            for plant in PLANTS
        }
        self.cares: dict[Care, IconButton] = {
            care: kit.icon_button(
                f"care.{care.value}", pygame.Rect(0, 0, 10, 10), icon=None, shape=BodyShape.TILE,
                on_activate=lambda care=care: self._on_care(care),
            )
            for care in Care
        }
        self.cards: dict[Stage, IconButton] = {}
        self.layer: ControlLayer = kit.layer((self.progress, self.hint), layer_id="serra.controls")
        self.bar = pygame.Rect(0, 0, 0, 0)
        self.bottom = pygame.Rect(0, 0, 0, 0)
        self.board = pygame.Rect(0, 0, 0, 0)
        self._row: tuple[str, ...] = ()
        self._row_ids: list[str] = []
        self._plant_id: str | None = None
        self._layout = layout
        self.relayout(layout)

    # -- geometry ------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        self._layout = layout
        height = layout.control_height(58, maximum=92)
        bar = layout.top_bar(height)
        self.bar = bar
        dots_h = max(30, int(height * 0.62))
        dots_w = ProgressDots.preferred_width(self.progress.total, dots_h)
        dots, hint = layout.row(bar, [dots_w, height], align=Align.END, height=height)
        self.progress.rect = pygame.Rect(dots.x, dots.centery - dots_h // 2, dots_w, dots_h)
        self.hint.rect = hint
        self.hint.icon = self._kit.glyph("hint", int(height * 0.62))
        tile_h = layout.control_height(112, maximum=124)
        self.bottom = layout.bottom_bar(tile_h)
        top = max(bar.bottom, layout.protected.bottom) + 14
        self.board = board_rect(top, self.bottom.top - 14, layout.width - layout.margin)
        self._place_row()
        self.layer.invalidation.invalidate()

    def _place_row(self) -> None:
        controls = [self.layer.target(cid) for cid in self._row_ids if cid in {t.control_id for t in self.layer.targets}]
        if not controls:
            return
        count = len(controls)
        height = self.bottom.height
        width = min(MAX_TILE, int(height * 1.12), (self.bottom.width - TILE_GAP * (count - 1)) // count)
        rects = self._layout.row(self.bottom, [width] * count, align=Align.CENTER, gap=TILE_GAP, height=height)
        icon_size = int(min(width, height) * ICON_SHARE)
        for control, rect in zip(controls, rects):
            assert isinstance(control, IconButton)
            control.rect = rect
            control.icon = self._icon_for(control.control_id, icon_size)

    def _icon_for(self, control_id: str, size: int) -> pygame.Surface | None:
        kind, _, value = control_id.partition(".")
        if kind == "seed":
            return self._art.packet(value, int(size * 1.22))
        if kind == "care":
            return self._art.care_icon(Care(value), size)
        if kind == "card" and self._plant_id is not None:
            return self._art.stage_card(self._plant_id, Stage(value), int(size * 0.84))
        return None

    # -- phases -----------------------------------------------------------------

    def show_seeds(self) -> None:
        self._set_row([self.seeds[plant.plant_id] for plant in PLANTS])

    def show_cares(self, cares: Sequence[Care]) -> None:
        self._set_row([self.cares[care] for care in cares])

    def show_cards(self, plant_id: str, deck: Sequence[Stage]) -> None:
        self._plant_id = plant_id
        self.cards = {
            stage: self._kit.icon_button(
                f"card.{stage.value}", pygame.Rect(0, 0, 10, 10), icon=None, shape=BodyShape.TILE,
                on_activate=lambda stage=stage: self._on_card(stage),
            )
            for stage in deck
        }
        self._set_row(list(self.cards.values()))

    def hide_row(self) -> None:
        self._set_row([])

    def _set_row(self, controls: Sequence[IconButton]) -> None:
        self._row_ids = [control.control_id for control in controls]
        for control in controls:
            control.visible = True
            control.enabled = True
        self.layer.set_targets((*controls, self.progress, self.hint))
        self._place_row()
        self.layer.invalidation.invalidate()

    def set_busy(self, busy: bool) -> None:
        """Disable the row while a moment plays (one answer at a time)."""

        for cid in self._row_ids:
            target = self.layer.target(cid)
            if isinstance(target, IconButton) and target.visible:
                target.enabled = not busy
        self.hint.enabled = not busy
        self.layer.invalidation.invalidate()

    def remove_card(self, stage: Stage) -> None:
        card = self.cards.get(stage)
        if card is not None:
            card.visible = False
            card.enabled = False
            if self.layer.focused_id == card.control_id:
                self.layer.ensure_focus()
            self.layer.invalidation.invalidate()

    def tile(self, control_id: str) -> IconButton | None:
        try:
            target = self.layer.target(control_id)
        except KeyError:
            return None
        return target if isinstance(target, IconButton) else None

    def row_ids(self) -> tuple[str, ...]:
        return tuple(self._row_ids)

    def focus_first(self) -> None:
        """Keyboard/controller focus starts on the first tile of a new row."""

        for cid in self._row_ids:
            target = self.layer.target(cid)
            if target.focusable:
                self.layer.focus(cid)
                return

    def sync_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()


__all__ = ["SerraControls"]

"""Shared control-kit wiring for Treno Numeri (ADR 0037).

Cargo on the platform, the two wagons and the order board are Activity-drawn
``ExternalTarget``s (the kit adds pointer activation, keyboard/D-pad/stick
focus and the focus ring); sending the train is a kit round ``IconButton``
with the shared ``go`` glyph, and journey progress is ``ProgressDots``. Rules
stay in ``Station``; this class only maps controls to the app callbacks.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.activity_controls import (
    Align,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
)

if __package__:
    from .treno_content import GO_CENTER, GO_SIZE, ITEM_SIZE, ITEM_TARGET, sign_face_rect, wagon_rect
    from .treno_model import Phase, Station
else:
    from treno_content import GO_CENTER, GO_SIZE, ITEM_SIZE, ITEM_TARGET, sign_face_rect, wagon_rect
    from treno_model import Phase, Station

GO_GLYPH = 64


def cargo_id(index: int) -> str:
    return f"cargo.{index}"


def wagon_id(index: int) -> str:
    return f"wagon.{index}"


class TrainControls:
    """Own the kit controls and the ``ControlLayer`` for the station screen."""

    def __init__(
        self,
        kit: ControlKit,
        layout: ControlLayout,
        stations: int,
        *,
        on_cargo: Callable[[int], object],
        on_wagon: Callable[[int], object],
        on_go: Callable[[], object],
        on_sign: Callable[[], object],
    ) -> None:
        self._on_cargo = on_cargo
        self.cargo: list[ExternalTarget] = []
        self.wagons: tuple[ExternalTarget, ...] = tuple(
            ExternalTarget(wagon_id(index), pygame.Rect(wagon_rect(index)), (lambda i=index: on_wagon(i)), focus_radius=18)
            for index in range(2)
        )
        self.sign = ExternalTarget("sign", pygame.Rect(sign_face_rect()).inflate(16, 16), on_sign, focus_radius=18)
        go_rect = pygame.Rect(0, 0, GO_SIZE, GO_SIZE)
        go_rect.center = GO_CENTER
        self.go: IconButton = kit.icon_button(
            "go",
            go_rect,
            icon=kit.glyph("go", GO_GLYPH),
            role=ButtonRole.PRIMARY,
            on_activate=on_go,
            enabled=False,
        )
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=stations)
        self.layer: ControlLayer = kit.layer((), layer_id="treno.controls")
        self.relayout(layout)

    # -- geometry -----------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Progress dots in the top bar beside (never inside) protected chrome."""

        height = layout.control_height(56, maximum=72)
        bar = layout.top_bar(height)
        dots_height = max(34, int(height * 0.66))
        dots_width = ProgressDots.preferred_width(self.progress.total, dots_height)
        (dots_rect,) = layout.row(bar, [dots_width], align=Align.END, height=dots_height)
        self.progress.rect = dots_rect
        self.layer.invalidation.invalidate()

    # -- station binding --------------------------------------------------------

    def bind_station(self, station: Station) -> None:
        """Create one focus target per cargo item for a new station."""

        half = ITEM_TARGET // 2
        self.cargo = [
            ExternalTarget(
                cargo_id(item.item_id),
                pygame.Rect(int(item.x) - half, int(item.y) - half, ITEM_TARGET, ITEM_TARGET),
                (lambda i=item.item_id: self._on_cargo(i)),
                focus_radius=ITEM_SIZE // 2,
            )
            for item in station.items
            if not item.locked
        ]
        self.layer.set_targets((self.sign, *self.wagons, *self.cargo, self.go, self.progress))
        self.sync(station, refocus=True)

    def sync(self, station: Station, *, refocus: bool = False) -> None:
        """Mirror station state into control enablement (cheap)."""

        loading = station.phase is Phase.LOADING
        by_id = {target.control_id: target for target in self.cargo}
        for item in station.items:
            target = by_id.get(cargo_id(item.item_id))
            if target is not None:
                target.enabled = loading and item.on_platform
        for index, target in enumerate(self.wagons):
            target.enabled = loading and station.wagon_has_cargo(index)
        self.sign.enabled = loading
        self.go.enabled = loading and station.loaded > 0
        if refocus or not self._focused_is_live():
            self.focus_default(station)
        self.layer.invalidation.invalidate()

    def focus_default(self, station: Station) -> None:
        if station.phase is Phase.LOADING:
            waiting = station.next_platform_item()
            if waiting is not None:
                self.layer.focus(cargo_id(waiting.item_id))
                return
            if self.go.enabled:
                self.layer.focus("go")
                return
        self.layer.ensure_focus()

    def _focused_is_live(self) -> bool:
        focused = self.layer.focused_id
        if focused is None:
            return False
        target = self.layer.target(focused)
        return target.focusable and target.enabled

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()


__all__ = ["TrainControls", "cargo_id", "wagon_id"]

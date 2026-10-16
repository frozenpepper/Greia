"""Shared control-kit wiring for Bridge Builders (ADR 0037).

The play screen follows Tito's Marble Run (same build -> GO -> watch pattern):

* the tray is a row of kit ``IconButton`` tiles along the bottom, one per piece
  of this crossing, each showing its plank at true scale (one board = one unit
  of river) or the pillar; the lifted piece is ``selected``, a piece already on
  the bridge shows faded and calls it back when activated;
* each span of water is a ``BridgeTarget`` (stand the lifted plank there) and
  each river rock is one too (stand the pillar there): they join keyboard /
  D-pad / stick focus and get the shared focus ring, while pointer and touch
  on the river stay with the Activity (tap, drag and drop);
* GO is the big primary pill at the right end of the tray it confirms
  (shared ``go`` glyph + the short localized GO label), so planks and GO form
  one mouse-first cluster (ADR 0037 §4a); hint is a round button (shared
  ``hint`` glyph) beside ``ProgressDots`` at the end of the top bar.

There is no other text on the play screen.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.activity_controls import (
    Align,
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    PillButton,
    ProgressDots,
)

if __package__:
    from .ponti_art import BridgeArt
    from .ponti_content import CROSSINGS_PER_SET, MAX_TRAY, Crossing
    from .ponti_layout import CrossingView, ScreenLayout
    from .ponti_model import BridgeState
else:
    from ponti_art import BridgeArt
    from ponti_content import CROSSINGS_PER_SET, MAX_TRAY, Crossing
    from ponti_layout import CrossingView, ScreenLayout
    from ponti_model import BridgeState

GLYPH_SHARE = 0.6
MAX_SEATS = 3
MAX_SPOTS = 2


def tray_id(index: int) -> str:
    return f"tray.{index}"


def seat_id(index: int) -> str:
    return f"seat.{index}"


def spot_id(index: int) -> str:
    return f"spot.{index}"


class BridgeTarget(ExternalTarget):
    """A span or rock: focusable by keyboard/controller, never hit by the kit pointer.

    Pointer and touch on the river belong to the Activity (tap, drag, drop), so
    ``contains`` is always False for the kit's pointer routing.
    """

    def contains(self, point: tuple[int, int]) -> bool:
        return False

    def set_rect(self, rect: pygame.Rect) -> None:
        self._rect = pygame.Rect(rect)


class BridgeControls:
    """Own the kit controls and the ``ControlLayer`` for the bridge screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: BridgeArt,
        layout: ControlLayout,
        *,
        go_label: str,
        on_tray: Callable[[int], object],
        on_seat: Callable[[int], object],
        on_spot: Callable[[int], object],
        on_go: Callable[[], object],
        on_hint: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self.tray: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                tray_id(index),
                pygame.Rect(0, 0, 10, 10),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda i=index: on_tray(i)),
            )
            for index in range(MAX_TRAY)
        )
        self.seats: tuple[BridgeTarget, ...] = tuple(
            BridgeTarget(seat_id(index), pygame.Rect(0, 0, 10, 10), (lambda i=index: on_seat(i)), focus_radius=16)
            for index in range(MAX_SEATS)
        )
        self.spots: tuple[BridgeTarget, ...] = tuple(
            BridgeTarget(spot_id(index), pygame.Rect(0, 0, 10, 10), (lambda i=index: on_spot(i)), focus_radius=16)
            for index in range(MAX_SPOTS)
        )
        self.go: PillButton = kit.pill_button(
            "go", pygame.Rect(0, 0, 10, 10), label=go_label, role=ButtonRole.PRIMARY, on_activate=on_go
        )
        self.hint: IconButton = kit.icon_button("hint", pygame.Rect(0, 0, 10, 10), icon=None, on_activate=on_hint)
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 10, 10), total=CROSSINGS_PER_SET)
        self.layer: ControlLayer = kit.layer(
            (*self.tray, *self.seats, *self.spots, self.go, self.hint, self.progress), layer_id="ponti.controls"
        )
        self.screen: ScreenLayout
        self._crossing: Crossing | None = None
        self._icon_state: tuple | None = None
        self.relayout(layout)

    # -- geometry ----------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> ScreenLayout:
        screen = ScreenLayout.build(layout)
        self.screen = screen
        bar = screen.bar
        height = bar.height
        dots_h = max(30, int(height * 0.62))
        dots_w = ProgressDots.preferred_width(CROSSINGS_PER_SET, dots_h)
        dots, hint = layout.row(bar, [dots_w, height], align=Align.END, height=height)
        self.progress.rect = pygame.Rect(dots.x, dots.centery - dots_h // 2, dots_w, dots_h)
        self.hint.rect = hint
        self.hint.icon = self._kit.glyph("hint", int(height * GLYPH_SHARE))
        self.go.icon = self._kit.glyph("go", int(screen.go.height * 0.56))
        self.go.rect = screen.go
        preferred = self.go.preferred_width()
        if preferred <= screen.go.width + 40:
            self.go.rect = pygame.Rect(screen.go.x, screen.go.y, max(screen.go.width, preferred), screen.go.height)
        self.go.compact = self.go.preferred_width() > self.go.rect.width
        if self._crossing is not None:
            self.set_crossing(self._crossing)
        self.layer.invalidation.invalidate()
        return screen

    def set_crossing(self, crossing: Crossing) -> None:
        self._crossing = crossing
        go_width = self.go.rect.width
        rects = self.screen.tray_rects(crossing, go_width)
        for index, button in enumerate(self.tray):
            if index < len(rects):
                button.rect = rects[index]
        # GO confirms the tray: it sits at the tray's right end (ADR 0037 §4a).
        self.go.rect = self.screen.go_rect(rects, go_width)
        self._icon_state = None

    # -- state mirroring -----------------------------------------------------------

    def sync(self, state: BridgeState, view: CrossingView, *, editable: bool, done: int) -> None:
        """Mirror the bridge into tray/targets/GO (icons rebuild only on change)."""

        crossing = state.crossing
        icon_state = (crossing.crossing_id, state.revision, tuple(state.seat_of), self.tray[0].rect.size)
        if icon_state != self._icon_state:
            self._icon_state = icon_state
            for index, button in enumerate(self.tray):
                if index < len(crossing.pieces):
                    rect = button.rect
                    size = (rect.width - 16, int((rect.height - button.lip) * 0.62))
                    button.icon = self._art.tray_icon(crossing.pieces[index], size, faded=not state.in_tray(index))
        for index, button in enumerate(self.tray):
            present = index < len(crossing.pieces)
            button.visible = present
            button.enabled = present and editable
            button.selected = present and editable and state.selected == index and state.in_tray(index)
        spans = state.spans()
        for index, target in enumerate(self.seats):
            present = index < len(spans)
            if present:
                target.set_rect(view.seat_rect(spans[index]))
            target.enabled = present and editable
            target.focusable = present
        for index, target in enumerate(self.spots):
            present = index < len(crossing.spots)
            if present:
                target.set_rect(view.spot_rect(index))
            target.enabled = present and editable
            target.focusable = present
        self.go.enabled = editable
        self.hint.enabled = editable
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()

    def focus_default(self, state: BridgeState) -> None:
        """Keyboard flow: the lifted tray piece, else GO."""

        if state.selected is not None and state.in_tray(state.selected):
            self.layer.focus(tray_id(state.selected))
        else:
            self.layer.focus("go")
        self.layer.ensure_focus()


__all__ = ["BridgeControls", "BridgeTarget", "seat_id", "spot_id", "tray_id"]

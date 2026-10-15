"""Shared control-kit wiring for Woodland Hide & Seek (ADR 0037).

The Activity draws its own scene, but every interactive element goes through
``greia_platform.activity_controls``: hiding places are ``ExternalTarget``s
(pointer/touch activation plus keyboard / D-pad / stick focus and the shared
focus ring), the request is a ``PromptBanner`` (friend picture + name, with a
listen button only when an approved name recording exists) and round progress
is ``ProgressDots``. Focus never jumps to the right answer: after everybody
hides again it stays where the child left it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pygame

from greia_platform.activity_controls import (
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    ProgressDots,
    PromptBanner,
)

if __package__:
    from .woodland_content import FINDS_PER_ROUND
    from .woodland_layout import SpotGeometry
else:
    from woodland_content import FINDS_PER_ROUND
    from woodland_layout import SpotGeometry

BANNER_HEIGHT = 72
BANNER_WIDTH = 420
ICON_SIZE = 62


def spot_id(index: int) -> str:
    return f"spot.{index}"


class WoodlandControls:
    """Own the kit controls and the single ``ControlLayer`` of the round screen."""

    def __init__(
        self,
        kit: ControlKit,
        *,
        on_spot: Callable[[int], object],
        on_listen: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._on_spot = on_spot
        self.spots: tuple[ExternalTarget, ...] = ()
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 120, 44), total=FINDS_PER_ROUND)
        self.banner_voiced: PromptBanner = kit.prompt_banner(
            "request.voiced",
            pygame.Rect(0, 0, BANNER_WIDTH, BANNER_HEIGHT),
            replay_icon=kit.glyph("listen", 34),
            on_replay=on_listen,
        )
        self.banner_plain: PromptBanner = kit.prompt_banner(
            "request", pygame.Rect(0, 0, BANNER_WIDTH, BANNER_HEIGHT)
        )
        self.banner_plain.visible = False
        self.banner_voiced.visible = False
        if self.banner_voiced.replay is not None:
            self.banner_voiced.replay.visible = False
        self.layer: ControlLayer = kit.layer((), layer_id="woodland.controls")

    # -- layout -----------------------------------------------------------------

    def place_bar(self, layout: ControlLayout) -> None:
        """Progress dots beside the protected chrome, request banner centred."""

        height = layout.control_height(BANNER_HEIGHT, maximum=84)
        bar = layout.top_bar(height)
        dots_h = max(36, int(height * 0.6))
        dots_w = ProgressDots.preferred_width(FINDS_PER_ROUND, dots_h)
        self.progress.rect = pygame.Rect(bar.left, bar.centery - dots_h // 2, dots_w, dots_h)
        free_left = self.progress.rect.right + layout.gap * 2
        width = min(BANNER_WIDTH, bar.right - free_left)
        centre = max(free_left + width // 2, layout.width // 2)
        centre = min(centre, bar.right - width // 2)
        rect = pygame.Rect(0, 0, width, height)
        rect.center = (centre, bar.centery)
        self.banner_voiced.rect = rect
        self.banner_plain.rect = rect

    def show_round(self, geometry: Sequence[SpotGeometry]) -> None:
        focused, visible = self.layer.focused_id, self.layer.focus_visible
        self.spots = tuple(
            ExternalTarget(spot_id(index), geom.hit_rect, (lambda i=index: self._on_spot(i)), focus_radius=24)
            for index, geom in enumerate(geometry)
        )
        # Back row first: the front row is registered later, so it wins taps
        # where the two overlap (the layer hit-tests last-registered first).
        self.layer.set_targets((*self.spots, self.progress, *self.banner_plain.controls, *self.banner_voiced.controls))
        if focused is None or not self.layer.focus(focused, visible=visible):
            self.layer.focus(spot_id(0), visible=visible)
        self.layer.ensure_focus()

    # -- request ------------------------------------------------------------------

    def ask(self, icon: pygame.Surface | None, text: str, *, voiced: bool) -> None:
        """Show the request (friend picture + name); listen only when voiced."""

        self.banner_voiced.visible = voiced
        if self.banner_voiced.replay is not None:
            self.banner_voiced.replay.visible = voiced
        self.banner_plain.visible = not voiced
        banner = self.banner_voiced if voiced else self.banner_plain
        banner.set_text(text, icon=icon)
        self.layer.invalidation.invalidate()

    def tell(self, icon: pygame.Surface | None, text: str) -> None:
        """Show the found friend with its position phrase ("behind the bush")."""

        self.ask(icon, text, voiced=False)

    def hide_request(self) -> None:
        self.banner_plain.visible = False
        self.banner_voiced.visible = False
        if self.banner_voiced.replay is not None:
            self.banner_voiced.replay.visible = False
        self.layer.invalidation.invalidate()

    def set_progress(self, found: int) -> None:
        self.progress.set_progress(found)
        self.layer.invalidation.invalidate()

    def focused_spot(self) -> int | None:
        focused = self.layer.focused_id
        if focused is None or not focused.startswith("spot."):
            return None
        return int(focused.split(".", 1)[1])


__all__ = ["WoodlandControls", "spot_id"]

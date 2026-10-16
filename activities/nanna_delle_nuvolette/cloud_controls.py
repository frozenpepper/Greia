"""Shared control-kit wiring for Cloud Bedtime (ADR 0037).

The night is the Activity's own drawing; its interactive parts join the kit
as ``ExternalTarget``s so keyboard, D-pad/stick and the south button move one
shared focus ring over them and activate them like a tap:

* each tray quilt (activate = pick it up / put it back);
* each little cloud (activate = give it the quilt in hand);
* ``ProgressDots`` show how many clouds are asleep (display only).

Pointer taps and drags are routed by the app itself (it needs press/drag/drop
on the same targets); the kit only owns focus, the dots and the overlay.
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
)

if __package__:
    from .cloud_content import CLOUDS_PER_NIGHT, MAX_TRAY
    from .cloud_layout import PROGRESS_HEIGHT, cloud_body
else:
    from cloud_content import CLOUDS_PER_NIGHT, MAX_TRAY
    from cloud_layout import PROGRESS_HEIGHT, cloud_body


def tile_id(index: int) -> str:
    return f"quilt.{index}"


def cloud_id(index: int) -> str:
    return f"cloud.{index}"


class CloudControls:
    """Own the focus targets, the progress dots and the single ``ControlLayer``."""

    def __init__(
        self,
        kit: ControlKit,
        *,
        on_tile: Callable[[int], object],
        on_cloud: Callable[[int], object],
    ) -> None:
        self._kit = kit
        self._on_tile = on_tile
        self.clouds: tuple[ExternalTarget, ...] = tuple(
            ExternalTarget(cloud_id(index), cloud_body(index), (lambda i=index: on_cloud(i)), focus_radius=60)
            for index in range(CLOUDS_PER_NIGHT)
        )
        self.tiles: list[ExternalTarget] = []
        self.progress: ProgressDots = kit.progress_dots(
            "progress", pygame.Rect(0, 0, 120, PROGRESS_HEIGHT), total=CLOUDS_PER_NIGHT
        )
        self.layer: ControlLayer = kit.layer((), layer_id="nanna.controls")

    def place_bar(self, layout: ControlLayout) -> None:
        """Progress dots in the top bar, just after the protected Home region."""

        height = layout.control_height(PROGRESS_HEIGHT, maximum=56)
        bar = layout.top_bar(height)
        width = ProgressDots.preferred_width(self.progress.total, height)
        self.progress.rect = pygame.Rect(bar.left, bar.top, width, height)
        self.layer.invalidation.invalidate()

    def set_tray(self, rects: Sequence[pygame.Rect]) -> None:
        self.tiles = [
            ExternalTarget(tile_id(index), rect, (lambda i=index: self._on_tile(i)), focus_radius=26)
            for index, rect in enumerate(rects[:MAX_TRAY])
        ]
        self._register()

    def _register(self) -> None:
        self.layer.set_targets((*self.tiles, *self.clouds, self.progress))
        self.layer.invalidation.invalidate()

    def sync(self, *, tiles_present: Sequence[bool], clouds_awake: Sequence[bool], playing: bool) -> None:
        """Only quilts still in the tray and clouds still awake can be focused."""

        for target, present in zip(self.tiles, tiles_present):
            target.enabled = playing and present
        for target, awake in zip(self.clouds, clouds_awake):
            target.enabled = playing and awake
        if self.layer.focused_id is not None:
            focused = self.layer.target(self.layer.focused_id)
            if not focused.focusable:
                self.layer.focused_id = None
        self.layer.invalidation.invalidate()

    def focus_first_tile(self) -> None:
        for target in self.tiles:
            if target.focusable:
                self.layer.focus(target.control_id)
                return

    def focus_cloud(self, index: int) -> None:
        if 0 <= index < len(self.clouds):
            self.layer.focus(cloud_id(index))

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()


__all__ = ["CloudControls", "cloud_id", "tile_id"]

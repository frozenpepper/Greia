"""Pygame convenience adapters for Greia Activity coordinate-space contracts.

This module is intentionally a thin renderer adapter over
`greia_platform.activity_viewport`.  Activity authors work in one logical
coordinate system; this adapter performs physical placement and pointer mapping.
Complex games may use CanvasTransform directly, while simple fixed-canvas
Activities can use PygameReferenceCanvas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from .activity_viewport import (
    ActivityViewport,
    CanvasFitMode,
    CanvasTransform,
    LogicalRect,
    ReferenceCanvasSpec,
)
from .responsive_layout import UiRect
from .system_chrome import ActivitySystemChromeLayout


def activity_viewport_for_surface(surface: pygame.Surface) -> ActivityViewport:
    """Build the Activity viewport from the actual surface + Greia chrome contract."""

    width, height = surface.get_size()
    chrome = ActivitySystemChromeLayout.for_surface(width, height)
    protected = chrome.protected_region
    return ActivityViewport.for_size(
        width,
        height,
        protected_regions=(
            UiRect(
                protected.x,
                protected.y,
                protected.width,
                protected.height,
            ),
        ),
    )


@dataclass(frozen=True, slots=True)
class PygameCanvasMapper:
    """Map one logical/reference/world coordinate space to a Pygame surface."""

    transform: CanvasTransform

    @classmethod
    def reference(
        cls,
        surface: pygame.Surface,
        spec: ReferenceCanvasSpec = ReferenceCanvasSpec(),
        *,
        safe_ui: bool = False,
        margin: int = 0,
    ) -> "PygameCanvasMapper":
        viewport = activity_viewport_for_surface(surface)
        return cls(
            viewport.reference_transform(
                spec,
                safe_ui=safe_ui,
                margin=margin,
            )
        )

    @classmethod
    def world(
        cls,
        surface: pygame.Surface,
        *,
        center: tuple[float, float],
        reference_size: tuple[float, float] = (1024.0, 600.0),
        fit: CanvasFitMode = CanvasFitMode.EXPAND,
        safe_ui: bool = False,
        margin: int = 0,
    ) -> "PygameCanvasMapper":
        viewport = activity_viewport_for_surface(surface)
        return cls(
            viewport.world_camera(
                center,
                reference_size=reference_size,
                fit=fit,
                safe_ui=safe_ui,
                margin=margin,
            )
        )

    @property
    def visible_logical_rect(self) -> LogicalRect:
        return self.transform.logical_view

    @property
    def physical_rect(self) -> pygame.Rect:
        rect = self.transform.physical_view.rounded_out()
        return pygame.Rect(rect.x, rect.y, rect.width, rect.height)

    @property
    def target_rect(self) -> pygame.Rect:
        rect = self.transform.target
        return pygame.Rect(rect.x, rect.y, rect.width, rect.height)

    def point(self, x: float, y: float) -> tuple[int, int]:
        px, py = self.transform.logical_to_physical((x, y))
        return (int(round(px)), int(round(py)))

    def rect(self, x: float, y: float, width: float, height: float) -> pygame.Rect:
        physical = self.transform.logical_rect_to_physical(
            LogicalRect(float(x), float(y), float(width), float(height))
        ).rounded_out()
        return pygame.Rect(
            physical.x,
            physical.y,
            physical.width,
            physical.height,
        )

    def length(self, logical_length: float, *, minimum_if_positive: int = 1) -> int:
        value = float(logical_length)
        scaled = int(round(value * self.transform.scale))
        if value > 0 and minimum_if_positive > 0:
            return max(int(minimum_if_positive), scaled)
        return scaled

    def pointer(
        self,
        physical_position: tuple[int | float, int | float],
        *,
        reject_outside: bool = True,
    ) -> tuple[float, float] | None:
        return self.transform.physical_to_logical(
            (float(physical_position[0]), float(physical_position[1])),
            reject_outside=reject_outside,
        )

    def logical_safe_ui_rect(self, surface: pygame.Surface) -> LogicalRect:
        """Return the automatically protected-safe UI region in this logical space.

        This is useful when a fixed/full-surface canvas intentionally renders
        beneath system chrome but needs to keep essential authored controls away
        from it.  Designers still author once; the returned safe region changes
        with the actual viewport/chrome geometry.
        """

        viewport = activity_viewport_for_surface(surface)
        safe = viewport.safe_ui_rect()
        top_left = self.transform.physical_to_logical(
            (safe.x, safe.y),
            reject_outside=False,
        )
        bottom_right = self.transform.physical_to_logical(
            (safe.right, safe.bottom),
            reject_outside=False,
        )
        assert top_left is not None and bottom_right is not None
        return LogicalRect(
            top_left[0],
            top_left[1],
            bottom_right[0] - top_left[0],
            bottom_right[1] - top_left[1],
        )


class PygameReferenceCanvas:
    """Simple one-reference-canvas drawing surface for fixed/puzzle Activities.

    The author draws onto one logical surface (1024x600 by default).  `present`
    maps it to the actual display with uniform CONTAIN or COVER behavior.

    This helper intentionally does not support EXPAND: a finite reference bitmap
    cannot invent the additional logical world that EXPAND reveals.  Use
    `PygameCanvasMapper.world` and render visible world objects instead.
    """

    def __init__(
        self,
        target: pygame.Surface,
        spec: ReferenceCanvasSpec = ReferenceCanvasSpec(),
        *,
        safe_ui: bool = False,
        margin: int = 0,
        alpha: bool = False,
    ) -> None:
        if spec.fit is CanvasFitMode.EXPAND:
            raise ValueError("PygameReferenceCanvas does not support EXPAND fit")
        self.target = target
        self.spec = spec
        self.mapper = PygameCanvasMapper.reference(
            target,
            spec,
            safe_ui=safe_ui,
            margin=margin,
        )
        flags = pygame.SRCALPHA if alpha else 0
        self.surface = pygame.Surface((spec.width, spec.height), flags)

    def pointer(
        self,
        position: tuple[int | float, int | float],
    ) -> tuple[float, float] | None:
        return self.mapper.pointer(position)

    def present(
        self,
        *,
        clear: tuple[int, int, int] | tuple[int, int, int, int] | None = None,
        smooth: bool = False,
        system_chrome: bool = True,
        pointer: bool = True,
    ) -> None:
        if clear is not None:
            self.target.fill(clear)

        transform = self.mapper.transform
        logical_origin = transform.logical_to_physical((0.0, 0.0))
        scaled_width = max(1, int(round(self.spec.width * transform.scale)))
        scaled_height = max(1, int(round(self.spec.height * transform.scale)))

        if (
            scaled_width == self.spec.width
            and scaled_height == self.spec.height
        ):
            rendered = self.surface
        elif smooth:
            rendered = pygame.transform.smoothscale(
                self.surface,
                (scaled_width, scaled_height),
            )
        else:
            rendered = pygame.transform.scale(
                self.surface,
                (scaled_width, scaled_height),
            )

        previous_clip: Any = self.target.get_clip()
        target = transform.target
        self.target.set_clip(pygame.Rect(target.x, target.y, target.width, target.height))
        try:
            self.target.blit(
                rendered,
                (int(round(logical_origin[0])), int(round(logical_origin[1]))),
            )
        finally:
            self.target.set_clip(previous_clip)

        if system_chrome:
            from .activity_ui import draw_system_chrome_overlay

            draw_system_chrome_overlay(self.target)

        if pointer:
            from .activity_ui import draw_activity_pointer

            draw_activity_pointer(self.target)


__all__ = [
    "PygameCanvasMapper",
    "PygameReferenceCanvas",
    "activity_viewport_for_surface",
]

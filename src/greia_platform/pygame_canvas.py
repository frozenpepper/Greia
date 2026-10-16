"""Pygame convenience adapters for Greia Activity coordinate-space contracts.

This module is intentionally a thin renderer adapter over
`greia_platform.activity_viewport`.  Activity authors work in one logical
coordinate system; this adapter performs physical placement and pointer mapping.
Complex games may use CanvasTransform directly, while simple fixed-canvas
Activities can use PygameReferenceCanvas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

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

    Greia Home/Back is deliberately not rendered here.  System chrome belongs
    to the trusted launcher/simulator layer above the Activity surface.  The
    legacy ``system_chrome`` keyword remains accepted temporarily during the R7
    catalogue migration, but it is ignored and must not be used by new code.
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
        # Last presented state, so a pointer-only refresh can repair the old
        # pointer area from ``surface`` instead of re-rendering the scene.
        self._last_clear: tuple[int, ...] | None = None
        self._last_smooth = False
        self._pointer_rect: pygame.Rect | None = None

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
        system_chrome: bool = False,
        pointer: bool = True,
    ) -> None:
        # R7 compatibility only: trusted Home/Back is no longer an Activity
        # rendering option.  Retain the keyword until first-party callers have
        # migrated so this authority correction does not become an API break.
        del system_chrome

        self._last_clear = tuple(clear) if clear is not None else None
        self._last_smooth = smooth
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

        self._pointer_rect = None
        if pointer:
            from .activity_ui import draw_activity_pointer

            self._pointer_rect = draw_activity_pointer(self.target)

    @property
    def _unscaled(self) -> bool:
        transform = self.mapper.transform
        return (
            int(round(self.spec.width * transform.scale)) == self.spec.width
            and int(round(self.spec.height * transform.scale)) == self.spec.height
        )

    def present_pointer(self) -> bool:
        """Refresh only Greia's pointer after ``FrameKind.POINTER``.

        Repairs the previous pointer rectangle from the last rendered logical
        frame, draws the pointer at the current mouse position and pushes just
        those two small rectangles with ``pygame.display.update``.  Returns
        False when the cheap path does not apply (scaled presentation): it
        then re-presents the unchanged logical frame and flips instead, which
        still avoids re-rendering the scene.
        """

        from .activity_ui import draw_activity_pointer

        on_display = self.target is pygame.display.get_surface()
        if not self._unscaled:
            self.present(clear=self._last_clear, smooth=self._last_smooth)
            if on_display:
                pygame.display.flip()
            return False
        dirty: list[pygame.Rect] = []
        old = self._pointer_rect
        if old is not None:
            self._repair(old)
            dirty.append(old)
        self._pointer_rect = draw_activity_pointer(self.target)
        if self._pointer_rect is not None:
            dirty.append(self._pointer_rect)
        if dirty and on_display:
            pygame.display.update(dirty)
        return True

    def plan_regions(
        self,
        regions: Iterable[pygame.Rect],
        *,
        max_passes: int = 2,
        max_fraction: float = 0.5,
    ) -> list[pygame.Rect] | None:
        """Merge dirty ``regions`` into at most ``max_passes`` rectangles.

        Returns None when a dirty-rectangle frame would not pay off (the
        merged area exceeds ``max_fraction`` of the logical surface): the
        caller then renders a full frame.  Each pass re-runs the Activity's
        whole renderer under a clip, so on the Atom a few passes are cheap
        but many are not — hence the small default.
        """

        bounds = self.surface.get_rect()
        merged = merge_regions(regions, bounds, limit=max_passes)
        if not merged or regions_area(merged) > max_fraction * bounds.width * bounds.height:
            return None
        return merged

    def render_regions(
        self,
        regions: Sequence[pygame.Rect],
        render: Callable[[], None],
    ) -> None:
        """Re-render only ``regions`` (from ``plan_regions``) of the logical surface.

        ``render`` is the Activity's normal full-scene renderer; it runs once
        per region with the logical surface clipped to it, so layering stays
        exactly that of a full frame while SDL only touches the clipped
        pixels.  The caller guarantees nothing changed outside ``regions``
        since the last presented frame.  Follow with ``present_regions``.
        """

        previous = self.surface.get_clip()
        try:
            for region in regions:
                self.surface.set_clip(region)
                render()
        finally:
            self.surface.set_clip(previous)

    def present_regions(self, regions: Sequence[pygame.Rect]) -> bool:
        """Push only logical ``regions`` (and Greia's pointer) to the display.

        The dirty-rectangle counterpart of ``present`` + ``flip`` for small
        sprites moving over a cached background: copies just those regions
        of the logical surface to the target and calls
        ``pygame.display.update`` with them.  Returns False when the cheap
        path does not apply (scaled presentation); it then presents and flips
        the whole frame instead.
        """

        from .activity_ui import draw_activity_pointer

        on_display = self.target is pygame.display.get_surface()
        if not self._unscaled:
            self.present(clear=self._last_clear, smooth=self._last_smooth)
            if on_display:
                pygame.display.flip()
            return False
        origin = self.mapper.transform.logical_to_physical((0.0, 0.0))
        ox, oy = int(round(origin[0])), int(round(origin[1]))
        bounds = self.surface.get_rect()
        dirty: list[pygame.Rect] = []
        for region in regions:
            area = region.clip(bounds)
            if area.width <= 0 or area.height <= 0:
                continue
            self.target.blit(self.surface, (area.x + ox, area.y + oy), area)
            dirty.append(area.move(ox, oy))
        old = self._pointer_rect
        if old is not None:
            self._repair(old)
            dirty.append(old)
        self._pointer_rect = draw_activity_pointer(self.target)
        if self._pointer_rect is not None:
            dirty.append(self._pointer_rect)
        if dirty and on_display:
            pygame.display.update(dirty)
        return True

    def _repair(self, rect: pygame.Rect) -> None:
        """Restore ``rect`` of the target from the last presented frame."""

        area = rect.clip(self.target.get_rect())
        if area.width <= 0 or area.height <= 0:
            return
        if self._last_clear is not None:
            self.target.fill(self._last_clear, area)
        transform = self.mapper.transform
        target = transform.target
        visible = area.clip(pygame.Rect(target.x, target.y, target.width, target.height))
        if visible.width <= 0 or visible.height <= 0:
            return
        origin = transform.logical_to_physical((0.0, 0.0))
        ox, oy = int(round(origin[0])), int(round(origin[1]))
        self.target.blit(self.surface, visible.topleft, visible.move(-ox, -oy))


def merge_regions(
    regions: Iterable[pygame.Rect],
    bounds: pygame.Rect,
    *,
    limit: int = 8,
) -> list[pygame.Rect]:
    """Clip ``regions`` to ``bounds`` and merge overlapping/touching ones.

    Keeps at most ``limit`` rectangles (the smallest neighbours are unioned)
    so a dirty-rectangle frame never degenerates into dozens of render
    passes.  Bounded and allocation-light: meant for a handful of sprites.
    """

    pending = [r.clip(bounds) for r in regions]
    pending = [r for r in pending if r.width > 0 and r.height > 0]
    merged: list[pygame.Rect] = []
    while pending:
        rect = pending.pop()
        grown = True
        while grown:
            grown = False
            for index in range(len(merged) - 1, -1, -1):
                if rect.colliderect(merged[index].inflate(2, 2)):
                    rect = rect.union(merged.pop(index))
                    grown = True
        merged.append(rect)
    while len(merged) > max(1, limit):
        merged.sort(key=lambda r: r.width * r.height)
        smallest = merged.pop(0)
        nearest = min(
            range(len(merged)),
            key=lambda i: smallest.union(merged[i]).width * smallest.union(merged[i]).height,
        )
        merged[nearest] = merged[nearest].union(smallest)
    return merged


def regions_area(regions: Iterable[pygame.Rect]) -> int:
    """Total pixel area of (already merged, non-overlapping) ``regions``."""

    return sum(r.width * r.height for r in regions)


class PygamePointerSprite:
    """Save-under Greia pointer for Activities that render straight to the display.

    Reference-canvas Activities repair the pointer from their logical surface
    (``PygameReferenceCanvas.present_pointer``).  Activities that draw at
    display resolution (Painting, Writing) have no such copy, so this sprite
    keeps the few hundred pixels *under* the pointer instead:

    * after a full render call ``draw(target)`` (it saves the patch first);
    * on ``FrameKind.POINTER`` call ``refresh(target)``: restore the old
      patch, draw at the new position, ``display.update`` the two rectangles
      — no scene re-render, no full flip (Atom N270: tens of ms saved);
    * before a partial scene update that may overlap the pointer, call
      ``erase(target)``, redraw the region, then
      ``refresh(target, extra=(region,))`` — one ``display.update`` pushes
      the region and both pointer rectangles.

    It owns one small bounded surface and no display resources.
    """

    def __init__(self, radius: int = 11) -> None:
        if radius <= 0:
            raise ValueError("radius must be positive")
        self.radius = int(radius)
        self._saved: tuple[pygame.Rect, pygame.Surface] | None = None
        self._erased: pygame.Rect | None = None  # restored, not yet pushed

    def forget(self) -> None:
        """Drop the saved patch (the target was fully repainted underneath)."""

        self._saved = None
        self._erased = None

    def draw(
        self,
        target: pygame.Surface,
        pos: tuple[int, int] | None = None,
    ) -> pygame.Rect | None:
        """Save the pixels under the pointer, then draw it; return its rect."""

        from . import activity_ui

        self._saved = None
        if pos is None:
            if not pygame.mouse.get_focused():
                return None
            pos = pygame.mouse.get_pos()
        x, y = int(pos[0]), int(pos[1])
        if x <= 0 and y <= 0:
            return None
        r = self.radius
        rect = pygame.Rect(x - r - 1, y - r - 1, 2 * r + 3, 2 * r + 3).clip(target.get_rect())
        if rect.width <= 0 or rect.height <= 0:
            return None
        self._saved = (rect, target.subsurface(rect).copy())
        activity_ui.draw_activity_pointer(target, (x, y), radius=r)
        return rect

    def erase(self, target: pygame.Surface) -> pygame.Rect | None:
        """Restore the pixels under the last drawn pointer; return that rect."""

        saved, self._saved = self._saved, None
        if saved is None:
            return None
        rect, patch = saved
        target.blit(patch, rect.topleft)
        self._erased = rect
        return rect

    def refresh(
        self,
        target: pygame.Surface,
        pos: tuple[int, int] | None = None,
        *,
        extra: tuple[pygame.Rect, ...] = (),
    ) -> list[pygame.Rect]:
        """Move the pointer and push only the changed rectangles.

        ``extra`` adds rectangles the caller already redrew (e.g. a painting
        stroke) so everything reaches the display in one ``update`` call.
        """

        rects = [rect for rect in extra if rect.width > 0 and rect.height > 0]
        self.erase(target)  # no-op when the caller already erased
        if self._erased is not None:
            rects.append(self._erased)
            self._erased = None
        new = self.draw(target, pos)
        if new is not None:
            rects.append(new)
        if rects and target is pygame.display.get_surface():
            pygame.display.update(rects)
        return rects


__all__ = [
    "PygameCanvasMapper",
    "PygamePointerSprite",
    "PygameReferenceCanvas",
    "activity_viewport_for_surface",
    "merge_regions",
    "regions_area",
]

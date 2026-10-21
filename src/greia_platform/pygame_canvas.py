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
from . import hires_surface
from .hires_surface import RAW
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

    When the display's aspect ratio differs from the reference, CONTAIN leaves
    bands (25 px above and below on a 1280x800 panel).  The canvas owns those
    bands: every full present repaints them with one solid colour (the
    adjacent scene edge, slightly darkened, or the ``clear`` colour), so they
    never keep stale Shell/launch-card pixels or Greia pointer trails.  At non-integer scales the frame is
    resampled smoothly; nearest-neighbour duplication of every Nth pixel row is
    what made scaled Activities look jagged.

    This helper intentionally does not support EXPAND: a finite reference bitmap
    cannot invent the additional logical world that EXPAND reveals.  Use
    `PygameCanvasMapper.world` and render visible world objects instead.

    Greia Home/Back is deliberately not rendered here.  System chrome belongs
    to the trusted launcher/simulator layer above the Activity surface.  The
    legacy ``system_chrome`` keyword remains accepted temporarily during the R7
    catalogue migration, but it is ignored and must not be used by new code.
    """

    #: Scene pixels sampled at each edge to choose the band colour.
    _BAND_EDGE = 4
    #: The band colour is the edge average darkened by this factor, so the
    #: band reads as a frame that belongs to the scene.
    _BAND_SHADE = 0.82
    #: A band keeps its colour until the edge average moves by more than
    #: this (any channel): a sprite passing the edge must not make it flicker,
    #: a real backdrop change (day to night) must recolour it.
    _BAND_HYSTERESIS = 28

    def __init__(
        self,
        target: pygame.Surface,
        spec: ReferenceCanvasSpec = ReferenceCanvasSpec(),
        *,
        safe_ui: bool = False,
        margin: int = 0,
        alpha: bool = False,
        hires: bool = False,
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
        # ``hires`` opts this Activity into the transparent high-resolution
        # layer: on a display clearly larger than the reference the logical
        # surface holds physical pixels, so drawing is sharp and present() is
        # a 1:1 copy.  Close to the reference the cheap path stays.
        render_scale = (
            hires_surface.hires_scale_for(self.mapper.transform.scale)
            if hires
            else None
        )
        if render_scale is not None:
            hires_surface.activate(render_scale)
        elif hires_surface.is_active():
            # A resize below the threshold: new surfaces go back to 1:1, and
            # this canvas still converts any older high-resolution sprite.
            hires_surface.activate(1.0)
        self.render_scale = render_scale or 1.0
        if hires_surface.is_active():
            self.surface = hires_surface.ScaledSurface(
                (spec.width, spec.height), flags, scale=self.render_scale
            )
        else:
            self.surface = RAW.Surface((spec.width, spec.height), flags)
        # Last presented state, so a pointer-only refresh can repair the old
        # pointer area without re-rendering or re-scaling the scene.
        self._last_clear: tuple[int, ...] | None = None
        self._last_smooth: bool | None = None
        self._pointer_rect: pygame.Rect | None = None
        # Physical pieces of the last presented frame: the (possibly scaled)
        # scene and the band fills.  Bounded: one display-sized frame at most.
        self._frame: pygame.Surface | None = None
        self._frame_rect: pygame.Rect | None = None
        self._bands: list[tuple[pygame.Rect, tuple[int, int, int]]] = []
        # Edge average behind each side's current band colour (hysteresis).
        self._band_edges: dict[str, tuple[int, int, int]] = {}

    def pointer(
        self,
        position: tuple[int | float, int | float],
    ) -> tuple[float, float] | None:
        return self.mapper.pointer(position)

    @property
    def _scaled_size(self) -> tuple[int, int]:
        scale = self.mapper.transform.scale
        return (
            max(1, int(round(self.spec.width * scale))),
            max(1, int(round(self.spec.height * scale))),
        )

    @property
    def _unscaled(self) -> bool:
        """True when the logical surface already holds the presented pixels."""

        return self._scaled_size == RAW.get_size(self.surface)

    def _smooth(self, smooth: bool | None) -> bool:
        """Resample smoothly unless the scale is an exact whole number."""

        if smooth is not None:
            return bool(smooth)
        scale = self.mapper.transform.scale
        return abs(scale - round(scale)) > 1e-6

    def _resample(
        self, source: pygame.Surface, size: tuple[int, int], smooth: bool
    ) -> pygame.Surface:
        if RAW.get_size(source) == size:
            return source
        if smooth and source.get_bitsize() in (24, 32):
            return RAW.transform.smoothscale(source, size)
        return RAW.transform.scale(source, size)

    def _origin(self) -> tuple[int, int]:
        x, y = self.mapper.transform.logical_to_physical((0.0, 0.0))
        return int(round(x)), int(round(y))

    def _target_rect(self) -> pygame.Rect:
        target = self.mapper.transform.target
        return pygame.Rect(target.x, target.y, target.width, target.height)

    def present(
        self,
        *,
        clear: tuple[int, int, int] | tuple[int, int, int, int] | None = None,
        smooth: bool | None = None,
        system_chrome: bool = False,
        pointer: bool = True,
    ) -> None:
        """Draw the logical frame onto the display surface, bands included.

        ``clear`` paints the whole target (bands included) with one colour;
        without it each band is one solid colour taken from the scene edge.  ``smooth`` forces or
        disables smooth resampling; the default chooses it for non-integer
        scales.
        """

        # R7 compatibility only: trusted Home/Back is no longer an Activity
        # rendering option.  Retain the keyword until first-party callers have
        # migrated so this authority correction does not become an API break.
        del system_chrome

        self._last_clear = tuple(clear) if clear is not None else None
        self._last_smooth = smooth
        if clear is not None:
            self.target.fill(clear)

        rendered = self._resample(self.surface, self._scaled_size, self._smooth(smooth))
        area = self._target_rect()
        frame_rect = pygame.Rect(self._origin(), RAW.get_size(rendered))
        previous_clip: Any = self.target.get_clip()
        self.target.set_clip(area)
        try:
            self.target.blit(rendered, frame_rect.topleft)
            self._bands = []
            if clear is None:
                self._bands = self._band_fills(rendered, frame_rect, area)
                for rect, colour in self._bands:
                    self.target.fill(colour, rect)
        finally:
            self.target.set_clip(previous_clip)
        self._frame = rendered
        self._frame_rect = frame_rect

        self._pointer_rect = None
        if pointer:
            from .activity_ui import draw_activity_pointer

            self._pointer_rect = draw_activity_pointer(self.target)

    def _band_fills(
        self,
        rendered: pygame.Surface,
        frame: pygame.Rect,
        area: pygame.Rect,
    ) -> list[tuple[pygame.Rect, tuple[int, int, int]]]:
        """Solid colours for the CONTAIN bands, taken from the adjacent scene edge."""

        visible = frame.clip(area)
        if visible.width <= 0 or visible.height <= 0:
            return []
        local = visible.move(-frame.x, -frame.y)
        sides = (
            ("top", pygame.Rect(visible.x, area.y, visible.width, visible.y - area.y)),
            ("bottom", pygame.Rect(visible.x, visible.bottom, visible.width, area.bottom - visible.bottom)),
            ("left", pygame.Rect(area.x, area.y, visible.x - area.x, area.height)),
            ("right", pygame.Rect(visible.right, area.y, area.right - visible.right, area.height)),
        )
        bands: list[tuple[pygame.Rect, tuple[int, int, int]]] = []
        for side, band in sides:
            if band.width <= 0 or band.height <= 0:
                continue
            bands.append((band, self._band_colour(rendered, local, side)))
        return bands

    def _band_colour(
        self, rendered: pygame.Surface, local: pygame.Rect, side: str
    ) -> tuple[int, int, int]:
        depth_y = min(self._BAND_EDGE, local.height)
        depth_x = min(self._BAND_EDGE, local.width)
        edge = {
            "top": pygame.Rect(local.x, local.y, local.width, depth_y),
            "bottom": pygame.Rect(local.x, local.bottom - depth_y, local.width, depth_y),
            "left": pygame.Rect(local.x, local.y, depth_x, local.height),
            "right": pygame.Rect(local.right - depth_x, local.y, depth_x, local.height),
        }[side]
        average = tuple(int(v) for v in RAW.transform.average_color(rendered, edge)[:3])
        previous = self._band_edges.get(side)
        if previous is not None and max(abs(a - b) for a, b in zip(average, previous)) <= self._BAND_HYSTERESIS:
            average = previous
        else:
            self._band_edges[side] = average
        return tuple(int(round(v * self._BAND_SHADE)) for v in average)  # type: ignore[return-value]

    def present_pointer(self) -> bool:
        """Refresh only Greia's pointer after ``FrameKind.POINTER``.

        Repairs the previous pointer rectangle from the last presented
        physical frame (scene and bands), draws the pointer at the current
        mouse position and pushes just those two small rectangles with
        ``pygame.display.update``.  This works at any scale: the scene is
        never re-rendered or re-scaled for a pointer move.  Returns False only
        when nothing was presented yet; it then presents and flips instead.
        """

        from .activity_ui import draw_activity_pointer

        on_display = self.target is pygame.display.get_surface()
        if self._frame is None:
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
        sprites moving over a cached background.  When the frame is scaled
        only the dirty regions are resampled (with a small logical margin so
        smooth filtering matches the full frame at their edges), and the
        cached physical frame is patched so later pointer repairs stay
        correct.  Returns False when nothing was presented yet; it then
        presents and flips the whole frame instead.
        """

        from .activity_ui import draw_activity_pointer

        on_display = self.target is pygame.display.get_surface()
        if self._frame is None or self._frame_rect is None:
            self.present(clear=self._last_clear, smooth=self._last_smooth)
            if on_display:
                pygame.display.flip()
            return False
        bounds = self.surface.get_rect()
        dirty: list[pygame.Rect] = []
        if self._unscaled:
            ox, oy = self._frame_rect.topleft
            scale = hires_surface.scale_of(self.surface)
            for region in regions:
                area = region.clip(bounds)
                if area.width <= 0 or area.height <= 0:
                    continue
                physical = hires_surface.physical_rect(area, scale)
                # The target is a plain display surface: a raw, physical blit.
                self.target.blit(self.surface, (physical.x + ox, physical.y + oy), physical)
                dirty.append(physical.move(ox, oy))
        else:
            for region in regions:
                patch = self._present_scaled_region(region, bounds)
                if patch is not None:
                    dirty.append(patch)
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

    def _present_scaled_region(
        self, region: pygame.Rect, bounds: pygame.Rect
    ) -> pygame.Rect | None:
        """Resample one logical region into the cached frame and the target."""

        assert self._frame is not None and self._frame_rect is not None
        area = region.clip(bounds)
        if area.width <= 0 or area.height <= 0:
            return None
        frame_w, frame_h = RAW.get_size(self._frame)
        sx = frame_w / self.spec.width
        sy = frame_h / self.spec.height
        # Resample a padded source so the filter sees the same neighbours as
        # the full-frame resample, then keep only the exact inner pixels.
        padded = area.inflate(4, 4).clip(bounds)
        left = int(padded.x * sx)
        top = int(padded.y * sy)
        right = min(frame_w, int(round(padded.right * sx)))
        bottom = min(frame_h, int(round(padded.bottom * sy)))
        if right <= left or bottom <= top:
            return None
        scaled = self._resample(
            self.surface.subsurface(padded),
            (right - left, bottom - top),
            self._smooth(self._last_smooth),
        )
        inner = pygame.Rect(
            int(area.x * sx),
            int(area.y * sy),
            0,
            0,
        )
        inner.width = min(frame_w, int(round(area.right * sx)) + 1) - inner.x
        inner.height = min(frame_h, int(round(area.bottom * sy)) + 1) - inner.y
        inner = inner.clip(pygame.Rect(left, top, right - left, bottom - top))
        if inner.width <= 0 or inner.height <= 0:
            return None
        source = inner.move(-left, -top)
        if self._frame is self.surface:
            self._frame = self._frame.copy()
        self._frame.blit(scaled, inner.topleft, source)
        physical = inner.move(self._frame_rect.topleft)
        visible = physical.clip(self._target_rect())
        if visible.width <= 0 or visible.height <= 0:
            return None
        self.target.blit(
            self._frame,
            visible.topleft,
            visible.move(-self._frame_rect.x, -self._frame_rect.y),
        )
        return visible

    def _repair(self, rect: pygame.Rect) -> None:
        """Restore ``rect`` of the target from the last presented frame."""

        area = rect.clip(self.target.get_rect())
        if area.width <= 0 or area.height <= 0:
            return
        if self._last_clear is not None:
            self.target.fill(self._last_clear, area)
        target_area = self._target_rect()
        for band, colour in self._bands:
            piece = area.clip(band).clip(target_area)
            if piece.width > 0 and piece.height > 0:
                self.target.fill(colour, piece)
        if self._frame is None or self._frame_rect is None:
            return
        visible = area.clip(self._frame_rect).clip(target_area)
        if visible.width <= 0 or visible.height <= 0:
            return
        self.target.blit(
            self._frame,
            visible.topleft,
            visible.move(-self._frame_rect.x, -self._frame_rect.y),
        )


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

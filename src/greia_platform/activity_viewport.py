"""Renderer-neutral Activity coordinate spaces and viewport transforms.

Greia Activities can range from ordinary responsive interfaces to fixed-layout
puzzles, drawing canvases, simulations and scrolling games.  This module gives
all of them one physical-resolution boundary without forcing every author to
maintain resolution-specific coordinates.

Coordinate spaces:

* physical: actual Activity surface pixels;
* reference: an authoring canvas, 1024x600 by default;
* world: arbitrary logical game/simulation coordinates;
* safe UI: the largest rectangular region that avoids platform-protected
  system chrome, useful for essential controls and ordinary fluid UI.

The transform math is renderer-neutral.  Pygame/Web/other runtime adapters can
consume the same semantics without making Pygame the platform contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Iterable

from .responsive_layout import UiRect


DEFAULT_REFERENCE_WIDTH = 1024
DEFAULT_REFERENCE_HEIGHT = 600


class ActivitySpatialModel(StrEnum):
    """High-level authoring model; not a hardware or renderer selection."""

    FLUID = "fluid"
    REFERENCE_CANVAS = "reference_canvas"
    WORLD_CAMERA = "world_camera"
    HYBRID = "hybrid"


class CanvasFitMode(StrEnum):
    """How a logical reference view maps to the real physical viewport."""

    CONTAIN = "contain"
    COVER = "cover"
    EXPAND = "expand"


@dataclass(frozen=True, slots=True)
class LogicalRect:
    """Floating-point rectangle in reference/world coordinates."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("logical rectangle values must be finite")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("logical rectangle dimensions must be positive")

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x <= self.right and self.y <= y <= self.bottom


@dataclass(frozen=True, slots=True)
class FloatRect:
    """Floating-point physical rectangle, retained to avoid cumulative rounding."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.x, self.y, self.width, self.height)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("physical rectangle values must be finite")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("physical rectangle dimensions must be positive")

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def contains(self, x: float, y: float) -> bool:
        return self.x <= x <= self.right and self.y <= y <= self.bottom

    def rounded_out(self) -> UiRect:
        left = math.floor(self.x)
        top = math.floor(self.y)
        right = math.ceil(self.right)
        bottom = math.ceil(self.bottom)
        return UiRect(left, top, max(0, right - left), max(0, bottom - top))


@dataclass(frozen=True, slots=True)
class ReferenceCanvasSpec:
    """One authored reference view that Greia can map to any real viewport."""

    width: int = DEFAULT_REFERENCE_WIDTH
    height: int = DEFAULT_REFERENCE_HEIGHT
    fit: CanvasFitMode = CanvasFitMode.CONTAIN

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("reference canvas dimensions must be positive")
        if not isinstance(self.fit, CanvasFitMode):
            raise TypeError("fit must be a CanvasFitMode")


@dataclass(frozen=True, slots=True)
class CanvasTransform:
    """Uniform bidirectional mapping between logical and physical coordinates.

    `logical_view` is the logical region currently visible.  In CONTAIN mode it
    is the full authored view and `physical_view` may be letterboxed.  In COVER
    mode the physical target is filled and `logical_view` is cropped.  In
    EXPAND mode the physical target is filled by *expanding* the visible logical
    world around the reference view rather than cropping or letterboxing it.
    EXPAND is especially useful for side-scrollers/top-down worlds.
    """

    target: UiRect
    logical_view: LogicalRect
    physical_view: FloatRect
    scale: float
    fit: CanvasFitMode
    reference_width: float
    reference_height: float

    def __post_init__(self) -> None:
        if self.target.width < 1 or self.target.height < 1:
            raise ValueError("target viewport must be non-empty")
        if not math.isfinite(self.scale) or self.scale <= 0:
            raise ValueError("canvas scale must be positive and finite")
        if self.reference_width <= 0 or self.reference_height <= 0:
            raise ValueError("reference dimensions must be positive")

    @classmethod
    def for_reference(
        cls,
        target: UiRect,
        spec: ReferenceCanvasSpec = ReferenceCanvasSpec(),
    ) -> "CanvasTransform":
        return cls.for_camera(
            target,
            center=(spec.width / 2.0, spec.height / 2.0),
            reference_size=(float(spec.width), float(spec.height)),
            fit=spec.fit,
        )

    @classmethod
    def for_camera(
        cls,
        target: UiRect,
        *,
        center: tuple[float, float],
        reference_size: tuple[float, float] = (
            float(DEFAULT_REFERENCE_WIDTH),
            float(DEFAULT_REFERENCE_HEIGHT),
        ),
        fit: CanvasFitMode = CanvasFitMode.EXPAND,
    ) -> "CanvasTransform":
        """Create a view centered on arbitrary logical world coordinates."""

        if target.width < 1 or target.height < 1:
            raise ValueError("target viewport must be non-empty")
        center_x, center_y = (float(center[0]), float(center[1]))
        reference_width, reference_height = (
            float(reference_size[0]),
            float(reference_size[1]),
        )
        if not all(
            math.isfinite(value)
            for value in (center_x, center_y, reference_width, reference_height)
        ):
            raise ValueError("camera values must be finite")
        if reference_width <= 0 or reference_height <= 0:
            raise ValueError("reference camera size must be positive")
        if not isinstance(fit, CanvasFitMode):
            raise TypeError("fit must be a CanvasFitMode")

        width_scale = target.width / reference_width
        height_scale = target.height / reference_height

        if fit is CanvasFitMode.CONTAIN:
            scale = min(width_scale, height_scale)
            physical_width = reference_width * scale
            physical_height = reference_height * scale
            physical = FloatRect(
                target.x + (target.width - physical_width) / 2.0,
                target.y + (target.height - physical_height) / 2.0,
                physical_width,
                physical_height,
            )
            logical = LogicalRect(
                center_x - reference_width / 2.0,
                center_y - reference_height / 2.0,
                reference_width,
                reference_height,
            )
        elif fit is CanvasFitMode.COVER:
            scale = max(width_scale, height_scale)
            visible_width = target.width / scale
            visible_height = target.height / scale
            physical = FloatRect(
                float(target.x),
                float(target.y),
                float(target.width),
                float(target.height),
            )
            logical = LogicalRect(
                center_x - visible_width / 2.0,
                center_y - visible_height / 2.0,
                visible_width,
                visible_height,
            )
        else:
            # Preserve the reference view in full and spend surplus aspect-ratio
            # space by revealing *more* world.  This is contain's scale without
            # contain's bars.
            scale = min(width_scale, height_scale)
            visible_width = target.width / scale
            visible_height = target.height / scale
            physical = FloatRect(
                float(target.x),
                float(target.y),
                float(target.width),
                float(target.height),
            )
            logical = LogicalRect(
                center_x - visible_width / 2.0,
                center_y - visible_height / 2.0,
                visible_width,
                visible_height,
            )

        return cls(
            target=target,
            logical_view=logical,
            physical_view=physical,
            scale=scale,
            fit=fit,
            reference_width=reference_width,
            reference_height=reference_height,
        )

    def logical_to_physical(self, point: tuple[float, float]) -> tuple[float, float]:
        x, y = float(point[0]), float(point[1])
        return (
            self.physical_view.x + (x - self.logical_view.x) * self.scale,
            self.physical_view.y + (y - self.logical_view.y) * self.scale,
        )

    def physical_to_logical(
        self,
        point: tuple[float, float],
        *,
        reject_outside: bool = True,
    ) -> tuple[float, float] | None:
        """Map pointer/touch pixels back into the same logical space as drawing."""

        x, y = float(point[0]), float(point[1])
        if reject_outside and not self.physical_view.contains(x, y):
            return None
        return (
            self.logical_view.x + (x - self.physical_view.x) / self.scale,
            self.logical_view.y + (y - self.physical_view.y) / self.scale,
        )

    def logical_rect_to_physical(self, rect: LogicalRect) -> FloatRect:
        left, top = self.logical_to_physical((rect.x, rect.y))
        return FloatRect(
            left,
            top,
            rect.width * self.scale,
            rect.height * self.scale,
        )

    @property
    def authored_reference_rect(self) -> LogicalRect:
        return LogicalRect(
            0.0,
            0.0,
            self.reference_width,
            self.reference_height,
        )


@dataclass(frozen=True, slots=True)
class ActivityViewport:
    """Actual Activity surface plus platform-protected physical exclusions."""

    surface: UiRect
    protected_regions: tuple[UiRect, ...] = ()

    def __post_init__(self) -> None:
        if self.surface.width < 1 or self.surface.height < 1:
            raise ValueError("Activity surface must be non-empty")
        for region in self.protected_regions:
            if region.width < 1 or region.height < 1:
                raise ValueError("protected region must be non-empty")
            if not self.surface.contains(region):
                raise ValueError("protected region must be contained by Activity surface")

    @classmethod
    def for_size(
        cls,
        width: int,
        height: int,
        *,
        protected_regions: Iterable[UiRect] = (),
    ) -> "ActivityViewport":
        return cls(
            UiRect(0, 0, int(width), int(height)),
            tuple(protected_regions),
        )

    def safe_ui_rect(self, *, margin: int = 0) -> UiRect:
        """Largest axis-aligned UI region that avoids all protected chrome.

        This lets ordinary controls use a single automatic safe rectangle even
        when trusted Home/Back chrome occupies only a corner rather than an
        entire top bar.  Background/world layers may still intentionally render
        beneath protected chrome; input there remains platform-owned.
        """

        safe = _largest_unreserved_rect(self.surface, self.protected_regions)
        return safe.inset(max(0, int(margin)))

    def reference_transform(
        self,
        spec: ReferenceCanvasSpec = ReferenceCanvasSpec(),
        *,
        safe_ui: bool = True,
        margin: int = 0,
    ) -> CanvasTransform:
        target = self.safe_ui_rect(margin=margin) if safe_ui else self.surface
        if target.width < 1 or target.height < 1:
            raise ValueError("Activity safe UI area is too small for a reference canvas")
        return CanvasTransform.for_reference(target, spec)

    def world_camera(
        self,
        center: tuple[float, float],
        *,
        reference_size: tuple[float, float] = (
            float(DEFAULT_REFERENCE_WIDTH),
            float(DEFAULT_REFERENCE_HEIGHT),
        ),
        fit: CanvasFitMode = CanvasFitMode.EXPAND,
        safe_ui: bool = False,
        margin: int = 0,
    ) -> CanvasTransform:
        """Map a logical game world camera to the real Activity viewport.

        World/background rendering normally uses the full Activity surface and
        may pass behind trusted chrome.  Set `safe_ui=True` for a board/puzzle
        whose meaningful interaction must never live beneath platform chrome.
        """

        target = self.safe_ui_rect(margin=margin) if safe_ui else self.surface
        if target.width < 1 or target.height < 1:
            raise ValueError("Activity viewport is too small for a world camera")
        return CanvasTransform.for_camera(
            target,
            center=center,
            reference_size=reference_size,
            fit=fit,
        )


def _overlaps(a: UiRect, b: UiRect) -> bool:
    return not (
        a.right <= b.x
        or b.right <= a.x
        or a.bottom <= b.y
        or b.bottom <= a.y
    )


def _largest_unreserved_rect(surface: UiRect, protected: tuple[UiRect, ...]) -> UiRect:
    if not protected:
        return surface

    xs = {surface.x, surface.right}
    ys = {surface.y, surface.bottom}
    for region in protected:
        xs.update((region.x, region.right))
        ys.update((region.y, region.bottom))
    x_values = sorted(xs)
    y_values = sorted(ys)

    best: UiRect | None = None
    best_area = -1
    best_shape = -1
    for left_index, left in enumerate(x_values[:-1]):
        for right in x_values[left_index + 1 :]:
            for top_index, top in enumerate(y_values[:-1]):
                for bottom in y_values[top_index + 1 :]:
                    candidate = UiRect(left, top, right - left, bottom - top)
                    if not surface.contains(candidate):
                        continue
                    if any(_overlaps(candidate, region) for region in protected):
                        continue
                    area = candidate.width * candidate.height
                    # On equal area, prefer the wider region: child interfaces
                    # and text generally benefit from preserving horizontal room.
                    shape = candidate.width - candidate.height
                    if (area, shape) > (best_area, best_shape):
                        best = candidate
                        best_area = area
                        best_shape = shape
    if best is None:
        raise ValueError("protected UI regions leave no usable Activity area")
    return best

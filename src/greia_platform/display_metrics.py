"""Renderer/backend-neutral display physical facts and suitability policy.

This module owns Greia's display-physical-facts domain: pixel dimensions plus
optional physical panel dimensions, a sanity gate, a landscape-first product
suitability policy, shared physical interactive-minimum sizing, and one shared
display-mode filter. It is deliberately free of hardware probing, backend
commands, device names, model profiles, and resolution allowlists.

Backend adapters (probes) and UI floors consume these value objects; this
module never touches a backend itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .hardware import DisplayMode

MM_PER_INCH = 25.4

# --- Sanity bounds -----------------------------------------------------------
# Broad "could this be a display?" limits. Product suitability is owned by
# DisplayPolicy; these bounds only reject values no real display could have.
MIN_PIXEL_DIMENSION = 1
MAX_PIXEL_DIMENSION = 16384
MIN_PHYSICAL_MM = 20.0
MAX_PHYSICAL_MM = 3000.0
MIN_SANE_DPI = 20.0
MAX_SANE_DPI = 800.0

# --- Shared interactive-minimum bounds ---------------------------------------
# Defensive clamps for PhysicalUiPolicy.minimum_pixels. They bound the returned
# minimum only; they never scale a layout.
PHYSICAL_UI_FLOOR_PX = 8
PHYSICAL_UI_CEILING_PX = 320


class DisplayMetricsSource(Enum):
    """Provenance of the physical panel dimensions in DisplayMetrics."""

    XRANDR_PHYSICAL_SIZE = "panel_physical_size"
    MANUAL_OVERRIDE = "manual_override"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DisplayMetrics:
    """Pixel dimensions plus optional physical panel size.

    Only raw facts are stored. Density values are derived on access and are
    never persisted. Instances are immutable.
    """

    pixel_width: int
    pixel_height: int
    physical_width_mm: float | None = None
    physical_height_mm: float | None = None
    source: DisplayMetricsSource = DisplayMetricsSource.UNKNOWN

    def __post_init__(self) -> None:
        if (
            isinstance(self.pixel_width, bool)
            or isinstance(self.pixel_height, bool)
            or not isinstance(self.pixel_width, int)
            or not isinstance(self.pixel_height, int)
        ):
            raise TypeError("pixel dimensions must be integers")
        if self.pixel_width < 1 or self.pixel_height < 1:
            raise ValueError("pixel dimensions must be positive")
        if not isinstance(self.source, DisplayMetricsSource):
            raise TypeError("source must be a DisplayMetricsSource")
        if (self.physical_width_mm is None) != (self.physical_height_mm is None):
            raise ValueError("physical dimensions must be both present or both absent")
        if self.physical_width_mm is not None and (
            not isinstance(self.physical_width_mm, (int, float))
            or isinstance(self.physical_width_mm, bool)
            or not isinstance(self.physical_height_mm, (int, float))
            or isinstance(self.physical_height_mm, bool)
            or not math.isfinite(self.physical_width_mm)
            or not math.isfinite(self.physical_height_mm)
            or self.physical_width_mm <= 0
            or self.physical_height_mm <= 0
        ):
            raise ValueError("physical dimensions must be positive finite numbers")

    @property
    def orientation(self) -> str:
        """One of ``landscape``, ``portrait`` or ``square`` by pixel shape."""
        if self.pixel_width > self.pixel_height:
            return "landscape"
        if self.pixel_height > self.pixel_width:
            return "portrait"
        return "square"

    @property
    def aspect_ratio(self) -> float:
        return self.pixel_width / self.pixel_height

    @property
    def physical_size_known(self) -> bool:
        """True only when plausible physical size arrived from a named source."""
        return (
            self.physical_width_mm is not None
            and self.physical_height_mm is not None
            and self.source is not DisplayMetricsSource.UNKNOWN
        )

    @property
    def pixels_per_mm_x(self) -> float | None:
        if self.physical_width_mm is None:
            return None
        return self.pixel_width / self.physical_width_mm

    @property
    def pixels_per_mm_y(self) -> float | None:
        if self.physical_height_mm is None:
            return None
        return self.pixel_height / self.physical_height_mm

    @property
    def effective_dpi_x(self) -> float | None:
        density = self.pixels_per_mm_x
        return None if density is None else density * MM_PER_INCH

    @property
    def effective_dpi_y(self) -> float | None:
        density = self.pixels_per_mm_y
        return None if density is None else density * MM_PER_INCH

    @property
    def diagonal_inches(self) -> float | None:
        if self.physical_width_mm is None or self.physical_height_mm is None:
            return None
        diagonal_mm = math.hypot(self.physical_width_mm, self.physical_height_mm)
        return diagonal_mm / MM_PER_INCH


def sanitize_display_metrics(
    pixel_width: object,
    pixel_height: object,
    physical_width_mm: object = None,
    physical_height_mm: object = None,
    source: DisplayMetricsSource = DisplayMetricsSource.UNKNOWN,
) -> DisplayMetrics | None:
    """Pure sanity gate: "could this be a display?".

    Returns ``None`` when the pixel dimensions are unusable (non-integer,
    non-positive, or beyond :data:`MAX_PIXEL_DIMENSION`). Physical dimensions
    are never invented: missing, partial, non-positive, out-of-range, or
    absurd-density physical input yields metrics with ``UNKNOWN`` source and
    no physical size. No fallback density is ever assumed.
    """
    if (
        isinstance(pixel_width, bool)
        or isinstance(pixel_height, bool)
        or not isinstance(pixel_width, int)
        or not isinstance(pixel_height, int)
    ):
        return None
    if (
        pixel_width < MIN_PIXEL_DIMENSION
        or pixel_height < MIN_PIXEL_DIMENSION
        or pixel_width > MAX_PIXEL_DIMENSION
        or pixel_height > MAX_PIXEL_DIMENSION
    ):
        return None
    if not isinstance(source, DisplayMetricsSource):
        source = DisplayMetricsSource.UNKNOWN
    width_mm = _as_finite_float(physical_width_mm)
    height_mm = _as_finite_float(physical_height_mm)
    if (
        width_mm is None
        or height_mm is None
        or not MIN_PHYSICAL_MM <= width_mm <= MAX_PHYSICAL_MM
        or not MIN_PHYSICAL_MM <= height_mm <= MAX_PHYSICAL_MM
    ):
        return DisplayMetrics(pixel_width, pixel_height)
    dpi_x = pixel_width / width_mm * MM_PER_INCH
    dpi_y = pixel_height / height_mm * MM_PER_INCH
    if not (
        MIN_SANE_DPI <= dpi_x <= MAX_SANE_DPI
        and MIN_SANE_DPI <= dpi_y <= MAX_SANE_DPI
    ):
        return DisplayMetrics(pixel_width, pixel_height)
    return DisplayMetrics(
        pixel_width,
        pixel_height,
        physical_width_mm=width_mm,
        physical_height_mm=height_mm,
        source=source,
    )


def _as_finite_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def current_mode(modes: Iterable[DisplayMode]) -> DisplayMode | None:
    """Return the first mode flagged current, or ``None`` when there is none."""
    for mode in modes:
        if mode.current:
            return mode
    return None


def metrics_from_mode(
    mode: DisplayMode | None,
    *,
    physical_width_mm: object = None,
    physical_height_mm: object = None,
    source: DisplayMetricsSource = DisplayMetricsSource.UNKNOWN,
) -> DisplayMetrics | None:
    """Build metrics for one mode; ``None`` when there is no mode to describe."""
    if mode is None:
        return None
    return sanitize_display_metrics(
        mode.width,
        mode.height,
        physical_width_mm,
        physical_height_mm,
        source,
    )


def metrics_for_output(
    output_name: str | None,
    modes: Iterable[DisplayMode],
    *,
    physical_width_mm: object = None,
    physical_height_mm: object = None,
    source: DisplayMetricsSource = DisplayMetricsSource.UNKNOWN,
) -> DisplayMetrics | None:
    """Build metrics for the current mode of a named output.

    Returns ``None`` when no output is connected/named or when no mode is
    flagged current. Never invents dimensions.
    """
    if not output_name:
        return None
    return metrics_from_mode(
        current_mode(modes),
        physical_width_mm=physical_width_mm,
        physical_height_mm=physical_height_mm,
        source=source,
    )


class DisplaySuitability(Enum):
    """Product verdict for one display's metrics under a DisplayPolicy."""

    SUPPORTED = "supported"
    SUPPORTED_WITH_REFLOW = "supported_with_reflow"
    UNKNOWN_PHYSICAL_SIZE = "unknown_physical_size"
    UNSUPPORTED_PHYSICAL_SIZE = "unsupported_physical_size"
    UNSUPPORTED_ORIENTATION = "unsupported_orientation"
    UNSUPPORTED_PIXEL_ENVELOPE = "unsupported_pixel_envelope"


@dataclass(frozen=True, slots=True)
class DisplayPolicy:
    """Landscape-first product suitability policy over display metrics.

    Thresholds are constructor-injected so tests and future products can vary
    them; :meth:`phase0` names the Phase-0 product floor. Bounds are envelopes,
    not an allowlist: arbitrary nearby pixel/physical values behave by policy.
    Orientation neutrality of the responsive-geometry layer is unaffected; this
    policy only states which displays the Phase-0 product supports.
    """

    min_pixel_width: int = 800
    min_pixel_height: int = 480
    preferred_pixel_width: int = 1024
    preferred_pixel_height: int = 600
    min_physical_width_mm: float = 80.0
    min_physical_height_mm: float = 50.0
    max_physical_width_mm: float = 2500.0
    max_physical_height_mm: float = 1600.0
    require_landscape: bool = True

    def __post_init__(self) -> None:
        if self.min_pixel_width < 1 or self.min_pixel_height < 1:
            raise ValueError("minimum pixel envelope must be positive")
        if (
            self.preferred_pixel_width < self.min_pixel_width
            or self.preferred_pixel_height < self.min_pixel_height
        ):
            raise ValueError("preferred envelope must contain the minimum envelope")
        if not (
            0 < self.min_physical_width_mm <= self.max_physical_width_mm
            and 0 < self.min_physical_height_mm <= self.max_physical_height_mm
        ):
            raise ValueError("physical envelope bounds are inconsistent")

    @classmethod
    def phase0(cls) -> "DisplayPolicy":
        """Name the Phase-0 product floor as envelope thresholds."""
        return cls()

    def evaluate(self, metrics: DisplayMetrics) -> DisplaySuitability:
        """Judge one display's metrics against this product policy."""
        if metrics is None or not isinstance(metrics, DisplayMetrics):
            raise TypeError("evaluate requires DisplayMetrics")
        if (
            metrics.pixel_width < self.min_pixel_width
            or metrics.pixel_height < self.min_pixel_height
        ):
            return DisplaySuitability.UNSUPPORTED_PIXEL_ENVELOPE
        if self.require_landscape and metrics.orientation != "landscape":
            return DisplaySuitability.UNSUPPORTED_ORIENTATION
        if not metrics.physical_size_known:
            return DisplaySuitability.UNKNOWN_PHYSICAL_SIZE
        assert metrics.physical_width_mm is not None
        assert metrics.physical_height_mm is not None
        if not (
            self.min_physical_width_mm
            <= metrics.physical_width_mm
            <= self.max_physical_width_mm
            and self.min_physical_height_mm
            <= metrics.physical_height_mm
            <= self.max_physical_height_mm
        ):
            return DisplaySuitability.UNSUPPORTED_PHYSICAL_SIZE
        if (
            metrics.pixel_width < self.preferred_pixel_width
            or metrics.pixel_height < self.preferred_pixel_height
        ):
            return DisplaySuitability.SUPPORTED_WITH_REFLOW
        return DisplaySuitability.SUPPORTED


class PhysicalUiPolicy:
    """Shared physical sizing for interactive minimums only.

    Converts a physical size (millimetres) into a pixel floor using trustworthy
    metrics, and falls back to a conservative caller-supplied pixel value when
    the physical size is unknown. Results are always clamped to
    [:data:`PHYSICAL_UI_FLOOR_PX`, :data:`PHYSICAL_UI_CEILING_PX`]. This never
    scales a layout globally; it only sizes shared interactive minimums such
    as touch targets.
    """

    @staticmethod
    def minimum_pixels(
        minimum_mm: object,
        *,
        fallback_px: object,
        metrics: DisplayMetrics | None,
    ) -> int:
        """Return the pixel minimum for ``minimum_mm`` of physical size."""
        fallback = _clamp_interactive_minimum(_as_finite_float(fallback_px))
        if fallback is None:
            fallback = PHYSICAL_UI_FLOOR_PX
        size_mm = _as_finite_float(minimum_mm)
        if size_mm is None or size_mm <= 0:
            return fallback
        density: float | None = None
        if metrics is not None and metrics.physical_size_known:
            density_x = metrics.pixels_per_mm_x
            density_y = metrics.pixels_per_mm_y
            if density_x is not None and density_y is not None:
                density = min(density_x, density_y)
        if density is None or density <= 0:
            return fallback
        return _clamp_interactive_minimum(math.floor(size_mm * density)) or fallback


def _clamp_interactive_minimum(value: float | None) -> int | None:
    if value is None or not math.isfinite(value):
        return None
    return min(PHYSICAL_UI_CEILING_PX, max(PHYSICAL_UI_FLOOR_PX, int(value)))


def filter_supported_modes(
    modes: Iterable[DisplayMode],
    *,
    physical_width_mm: object = None,
    physical_height_mm: object = None,
    source: DisplayMetricsSource = DisplayMetricsSource.UNKNOWN,
    policy: DisplayPolicy | None = None,
) -> tuple[DisplayMode, ...]:
    """Keep modes the product policy does not prove unsuitable.

    Every candidate mode is judged against the same physical panel size (a
    mode switch does not resize the panel) through :meth:`DisplayPolicy.evaluate`.
    Modes verdict ``SUPPORTED``, ``SUPPORTED_WITH_REFLOW`` or
    ``UNKNOWN_PHYSICAL_SIZE`` are kept; modes the policy proves unsuitable
    (pixel envelope, orientation, or physical envelope) are dropped. Callers
    needing per-mode verdicts can combine :func:`sanitize_display_metrics`
    with :meth:`DisplayPolicy.evaluate` directly.
    """
    active = policy or DisplayPolicy.phase0()
    kept: list[DisplayMode] = []
    for mode in modes:
        metrics = metrics_from_mode(
            mode,
            physical_width_mm=physical_width_mm,
            physical_height_mm=physical_height_mm,
            source=source,
        )
        if metrics is None:
            continue
        verdict = active.evaluate(metrics)
        if verdict in (
            DisplaySuitability.SUPPORTED,
            DisplaySuitability.SUPPORTED_WITH_REFLOW,
            DisplaySuitability.UNKNOWN_PHYSICAL_SIZE,
        ):
            kept.append(mode)
    return tuple(kept)

"""Renderer-neutral responsive geometry for Greia-owned UI surfaces.

The helpers in this module deliberately stay small and deterministic.  They are
not a constraint solver or widget framework: they provide one shared vocabulary
for viewport-derived values and collection grids so launcher, installer,
first-party Activities and future renderers do not each invent resolution
breakpoints or model-specific coordinate tables.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UiRect:
    """Small renderer-neutral integer rectangle used by layout calculations."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("rectangle dimensions must not be negative")

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def contains(self, other: "UiRect") -> bool:
        return (
            other.x >= self.x
            and other.y >= self.y
            and other.right <= self.right
            and other.bottom <= self.bottom
        )

    def inset(self, horizontal: int = 0, vertical: int | None = None) -> "UiRect":
        """Return a non-negative inset rectangle, collapsing safely if necessary."""

        horizontal = max(0, int(horizontal))
        vertical = horizontal if vertical is None else max(0, int(vertical))
        width = max(0, self.width - horizontal * 2)
        height = max(0, self.height - vertical * 2)
        return UiRect(
            self.x + min(horizontal, self.width // 2),
            self.y + min(vertical, self.height // 2),
            width,
            height,
        )


@dataclass(frozen=True, slots=True)
class Viewport:
    """Actual usable Greia viewport; hardware identity is intentionally absent."""

    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("viewport dimensions must be positive")

    @property
    def rect(self) -> UiRect:
        return UiRect(0, 0, self.width, self.height)

    @property
    def short_axis(self) -> int:
        return min(self.width, self.height)

    @property
    def long_axis(self) -> int:
        return max(self.width, self.height)

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    def bounded_px(
        self,
        reference_px: int,
        *,
        reference_short_axis: int = 600,
        minimum: int,
        maximum: int,
    ) -> int:
        """Scale one decorative/typographic measure and clamp it to useful bounds.

        Responsive *layout* should reflow before relying on this helper.  It is
        intended for local measures such as gaps, corner radii and bounded icon
        sizes, not for uniformly scaling an entire fixed-resolution canvas.
        """

        if reference_px < 0:
            raise ValueError("reference_px must not be negative")
        if reference_short_axis < 1:
            raise ValueError("reference_short_axis must be positive")
        if minimum < 0 or maximum < minimum:
            raise ValueError("invalid pixel bounds")
        scaled = round(reference_px * self.short_axis / reference_short_axis)
        return min(maximum, max(minimum, scaled))


@dataclass(frozen=True, slots=True)
class AdaptiveGridPolicy:
    """Bounded child-facing collection grid policy.

    The policy chooses geometry from available content space.  It has no device
    names and no fixed resolution breakpoints.  When the viewport becomes too
    constrained for the preferred minimum tile size, it degrades to the largest
    contained single cell rather than overflowing the viewport; callers may then
    expose scrolling/paging or reject a display mode at the display-policy layer.
    """

    minimum_item_px: int = 96
    preferred_item_px: int = 180
    maximum_item_px: int = 220
    minimum_gap_px: int = 8
    maximum_gap_px: int = 24
    maximum_columns: int = 6
    maximum_rows: int = 3

    def __post_init__(self) -> None:
        if self.minimum_item_px < 1:
            raise ValueError("minimum item size must be positive")
        if not self.minimum_item_px <= self.preferred_item_px <= self.maximum_item_px:
            raise ValueError("item size bounds are inconsistent")
        if self.minimum_gap_px < 0 or self.maximum_gap_px < self.minimum_gap_px:
            raise ValueError("gap bounds are inconsistent")
        if self.maximum_columns < 1 or self.maximum_rows < 1:
            raise ValueError("grid bounds must be positive")

    def layout(self, content: UiRect, item_count: int) -> "AdaptiveGridLayout":
        item_count = max(0, int(item_count))
        if item_count == 0 or content.width == 0 or content.height == 0:
            return AdaptiveGridLayout(
                content=content,
                columns=1,
                rows=0,
                item_px=0,
                gap_px=0,
                capacity=0,
                constrained=bool(item_count),
            )

        gap = _clamp(
            min(content.width, content.height) // 36,
            self.minimum_gap_px,
            self.maximum_gap_px,
        )

        max_columns_by_width = max(
            1,
            (content.width + gap) // (self.minimum_item_px + gap),
        )
        max_rows_by_height = max(
            1,
            (content.height + gap) // (self.minimum_item_px + gap),
        )
        columns_ceiling = min(self.maximum_columns, max_columns_by_width, item_count)
        rows_ceiling = min(self.maximum_rows, max_rows_by_height, item_count)

        best: tuple[int, int, int, int] | None = None
        # Prefer the layout that shows the most items.  For equal capacity,
        # prefer the larger tile; for another tie, prefer more columns on
        # landscape/wide spaces and fewer columns on tall/narrow spaces.
        prefer_wide = content.width >= content.height
        for rows in range(1, rows_ceiling + 1):
            for columns in range(1, columns_ceiling + 1):
                capacity = min(item_count, rows * columns)
                item_px = min(
                    self.maximum_item_px,
                    (content.width - gap * (columns - 1)) // columns,
                    (content.height - gap * (rows - 1)) // rows,
                )
                if item_px < self.minimum_item_px:
                    continue
                shape_bias = columns if prefer_wide else -columns
                candidate = (capacity, item_px, shape_bias, columns * rows)
                if best is None or candidate > best[:4]:
                    best = (*candidate, rows, columns)  # type: ignore[assignment]

        if best is None:
            item_px = max(1, min(content.width, content.height, self.maximum_item_px))
            return AdaptiveGridLayout(
                content=content,
                columns=1,
                rows=1,
                item_px=item_px,
                gap_px=0,
                capacity=1,
                constrained=item_px < self.minimum_item_px,
            )

        _, item_px, _, _, rows, columns = best  # type: ignore[misc]
        capacity = min(item_count, rows * columns)
        return AdaptiveGridLayout(
            content=content,
            columns=columns,
            rows=rows,
            item_px=item_px,
            gap_px=gap,
            capacity=capacity,
            constrained=False,
        )


@dataclass(frozen=True, slots=True)
class AdaptiveGridLayout:
    """Computed visible grid geometry with deterministic cell containment."""

    content: UiRect
    columns: int
    rows: int
    item_px: int
    gap_px: int
    capacity: int
    constrained: bool

    def __post_init__(self) -> None:
        if self.columns < 1:
            raise ValueError("columns must be positive")
        if self.rows < 0 or self.item_px < 0 or self.gap_px < 0 or self.capacity < 0:
            raise ValueError("grid geometry must not be negative")
        if self.rows == 0 and self.capacity != 0:
            raise ValueError("empty grid cannot have capacity")
        if self.capacity > self.columns * self.rows:
            raise ValueError("capacity exceeds grid geometry")

    @property
    def total_width(self) -> int:
        if self.capacity == 0:
            return 0
        return self.columns * self.item_px + max(0, self.columns - 1) * self.gap_px

    @property
    def total_height(self) -> int:
        if self.capacity == 0:
            return 0
        return self.rows * self.item_px + max(0, self.rows - 1) * self.gap_px

    @property
    def origin_x(self) -> int:
        return self.content.x + max(0, (self.content.width - self.total_width) // 2)

    @property
    def origin_y(self) -> int:
        return self.content.y + max(0, (self.content.height - self.total_height) // 2)

    def cell(self, visible_index: int) -> UiRect:
        if visible_index < 0 or visible_index >= self.capacity:
            raise IndexError("visible grid index is outside capacity")
        row, column = divmod(visible_index, self.columns)
        rect = UiRect(
            self.origin_x + column * (self.item_px + self.gap_px),
            self.origin_y + row * (self.item_px + self.gap_px),
            self.item_px,
            self.item_px,
        )
        if not self.content.contains(rect):
            raise RuntimeError("computed responsive grid cell escaped content viewport")
        return rect


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return min(maximum, max(minimum, int(value)))

"""Renderer-neutral responsive navigation geometry for the Greia launcher.

This module owns pure layout geometry for launcher page controls: previous and
next buttons, adaptive gutter versus panel-rail placement, and bounded visible
pagination indicators.

It deliberately contains no Pygame imports, no drawing routines, and no
interaction/HitTarget objects. Presentation mixins consume the resulting UiRect
structures for rendering and hit testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from greia_platform.responsive_layout import UiRect, Viewport


class PageControlsPlacement(str, Enum):
    """Placement strategy determined from available viewport and tray geometry."""

    OUTER_GUTTER = "outer_gutter"
    PANEL_RAIL = "panel_rail"
    CONTAINED_FALLBACK = "contained_fallback"


@dataclass(frozen=True, slots=True)
class PageControlsState:
    """Semantic pagination state independent of underlying paging models.

    Adapts GridPage (base launcher / profile picker) and ScrollModel.window
    (Activity catalogue) so presentation components render one unified contract.
    """

    page_index: int
    page_count: int
    previous_value: object
    next_value: object
    can_go_previous: bool
    can_go_next: bool
    page_size: int = 1

    def __post_init__(self) -> None:
        if self.page_count < 0:
            raise ValueError("page_count must be non-negative")
        if self.page_index < 0 and self.page_count > 0:
            raise ValueError("page_index must be non-negative when pages exist")
        if self.page_size < 1:
            raise ValueError("page_size must be at least 1")

    @classmethod
    def from_grid_page(
        cls,
        page: Any,
        *,
        total: int,
    ) -> "PageControlsState":
        """Adapt a GridPage or compatible paging object."""
        page_index = getattr(page, "page_index", 0)
        page_count = getattr(page, "page_count", 1)
        start = getattr(page, "start", 0)
        stop = getattr(page, "stop", total)
        page_size = getattr(page, "page_size", max(1, stop - start))

        prev_val = max(0, start - page_size)
        next_val = min(max(0, total - 1), stop)
        can_prev = page_index > 0
        can_next = page_index + 1 < page_count
        return cls(
            page_index=page_index,
            page_count=page_count,
            previous_value=prev_val,
            next_value=next_val,
            can_go_previous=can_prev,
            can_go_next=can_next,
            page_size=page_size,
        )

    @classmethod
    def from_scroll_window(
        cls,
        window: Any,
        *,
        page_capacity: int,
        total_items: int,
    ) -> "PageControlsState":
        """Adapt a ScrollModel.window from the Activity catalogue."""
        capacity = max(1, page_capacity)
        total_pages = max(1, (total_items + capacity - 1) // capacity) if total_items > 0 else 0
        current_page = window.start // capacity if total_items > 0 else 0
        can_prev = bool(getattr(window, "can_scroll_backward", False))
        can_next = bool(getattr(window, "can_scroll_forward", False))
        return cls(
            page_index=current_page,
            page_count=total_pages,
            previous_value=-1,
            next_value=1,
            can_go_previous=can_prev,
            can_go_next=can_next,
            page_size=capacity,
        )


@dataclass(frozen=True, slots=True)
class PageControlsLayout:
    """Pure geometry for page controls within a given viewport."""

    placement: PageControlsPlacement
    previous_rect: UiRect
    next_rect: UiRect
    indicator_rect: UiRect
    visible_dot_count: int
    active_dot_index: int
    dot_rects: tuple[UiRect, ...]


def resolve_page_controls_layout(
    viewport: Viewport,
    state: PageControlsState,
    *,
    panel_outer_rect: UiRect | None = None,
    panel_content_rect: UiRect | None = None,
    button_size: int = 52,
    min_gutter_margin: int = 8,
    max_visible_dots: int = 5,
) -> PageControlsLayout:
    """Resolve responsive pager geometry with constrained degradation.

    Degradation order:
    1. OUTER_GUTTER if available gutter on both sides >= button_size + 2 * min_gutter_margin.
    2. PANEL_RAIL if panel outer bezel has clearance outside panel_content_rect.
    3. CONTAINED_FALLBACK preserving button size within viewport bounds without clipping.
    """
    button_size = max(1, int(button_size))
    min_gutter_margin = max(0, int(min_gutter_margin))
    max_visible_dots = max(1, int(max_visible_dots))

    # 1. Resolve Previous / Next Button Placement & Geometry
    placement = PageControlsPlacement.OUTER_GUTTER
    if panel_outer_rect is not None:
        left_gutter = panel_outer_rect.x
        right_gutter = viewport.width - panel_outer_rect.right
        required_gutter = button_size + 2 * min_gutter_margin

        if left_gutter >= required_gutter and right_gutter >= required_gutter:
            # Wide mode: center buttons inside the outer gutters outside the panel
            placement = PageControlsPlacement.OUTER_GUTTER
            prev_x = (panel_outer_rect.x - button_size) // 2
            next_x = panel_outer_rect.right + (right_gutter - button_size) // 2
            center_y = panel_outer_rect.y + panel_outer_rect.height // 2
            prev_y = next_y = max(
                min_gutter_margin,
                min(viewport.height - button_size - min_gutter_margin, center_y - button_size // 2),
            )
        elif panel_content_rect is not None:
            left_rail = panel_content_rect.x - panel_outer_rect.x
            right_rail = panel_outer_rect.right - panel_content_rect.right
            required_rail = button_size + 4

            if left_rail >= required_rail and right_rail >= required_rail:
                # Compact mode (e.g. 800x600): center buttons in the outer panel rail,
                # guaranteed to sit outside panel_content_rect so cards are never touched.
                placement = PageControlsPlacement.PANEL_RAIL
                prev_x = panel_outer_rect.x + (left_rail - button_size) // 2
                next_x = panel_content_rect.right + (right_rail - button_size) // 2
                center_y = panel_outer_rect.y + panel_outer_rect.height // 2
                prev_y = next_y = max(
                    min_gutter_margin,
                    min(viewport.height - button_size - min_gutter_margin, center_y - button_size // 2),
                )
            else:
                # Constrained fallback
                placement = PageControlsPlacement.CONTAINED_FALLBACK
                prev_x = min_gutter_margin
                next_x = max(0, viewport.width - button_size - min_gutter_margin)
                center_y = panel_outer_rect.y + panel_outer_rect.height // 2
                prev_y = next_y = max(
                    min_gutter_margin,
                    min(viewport.height - button_size - min_gutter_margin, center_y - button_size // 2),
                )
        else:
            placement = PageControlsPlacement.CONTAINED_FALLBACK
            prev_x = min_gutter_margin
            next_x = max(0, viewport.width - button_size - min_gutter_margin)
            center_y = panel_outer_rect.y + panel_outer_rect.height // 2
            prev_y = next_y = max(
                min_gutter_margin,
                min(viewport.height - button_size - min_gutter_margin, center_y - button_size // 2),
            )
    else:
        # No panel tray: place at viewport margins or around content
        placement = PageControlsPlacement.OUTER_GUTTER
        if panel_content_rect is not None:
            left_gutter = panel_content_rect.x
            right_gutter = viewport.width - panel_content_rect.right
            prev_x = max(min_gutter_margin, (left_gutter - button_size) // 2)
            next_x = min(
                viewport.width - button_size - min_gutter_margin,
                panel_content_rect.right + (right_gutter - button_size) // 2,
            )
            center_y = panel_content_rect.y + panel_content_rect.height // 2
            prev_y = next_y = max(
                min_gutter_margin,
                min(
                    viewport.height - button_size - min_gutter_margin,
                    center_y - button_size // 2,
                ),
            )
        else:
            prev_x = min_gutter_margin
            next_x = max(0, viewport.width - button_size - min_gutter_margin)
            prev_y = next_y = max(0, (viewport.height - button_size) // 2)

    previous_rect = UiRect(max(0, prev_x), max(0, prev_y), button_size, button_size)
    next_rect = UiRect(max(0, next_x), max(0, next_y), button_size, button_size)

    # 2. Resolve Bottom Pagination Capsule & Bounded Dots
    if state.page_count <= 1:
        return PageControlsLayout(
            placement=placement,
            previous_rect=previous_rect,
            next_rect=next_rect,
            indicator_rect=UiRect(0, 0, 0, 0),
            visible_dot_count=0,
            active_dot_index=0,
            dot_rects=(),
        )

    total_pages = state.page_count
    visible_dot_count = min(total_pages, max_visible_dots)

    if total_pages <= max_visible_dots:
        active_dot_index = min(max(0, state.page_index), visible_dot_count - 1)
        window_start = 0
    else:
        half = max_visible_dots // 2
        window_start = max(0, min(state.page_index - half, total_pages - max_visible_dots))
        active_dot_index = min(max(0, state.page_index - window_start), visible_dot_count - 1)

    pill_h = 30
    dot_spacing = 14
    dots_w = (visible_dot_count - 1) * dot_spacing + 16
    # Reserve width for page counter label (e.g. "1 / 3" or "18 / 22")
    label_w = 48 if total_pages < 10 else 64
    pill_w = dots_w + label_w + 24

    # Center horizontally relative to content rect if available, else outer rect, else viewport
    if panel_outer_rect is not None and panel_content_rect is not None:
        center_x = panel_content_rect.x + panel_content_rect.width // 2
        pill_y = panel_content_rect.bottom - pill_h - 4
    elif panel_outer_rect is not None:
        center_x = panel_outer_rect.x + panel_outer_rect.width // 2
        pill_y = panel_outer_rect.bottom - pill_h - 8
    elif panel_content_rect is not None:
        center_x = panel_content_rect.x + panel_content_rect.width // 2
        pill_y = min(viewport.height - pill_h - 8, panel_content_rect.bottom + 8)
    else:
        center_x = viewport.width // 2
        pill_y = viewport.height - pill_h - 10

    pill_x = center_x - pill_w // 2
    indicator_rect = UiRect(max(0, pill_x), max(0, pill_y), pill_w, pill_h)

    # Dot hit/presentation rects
    dots_start_x = indicator_rect.x + 14
    dot_rects_list: list[UiRect] = []
    for i in range(visible_dot_count):
        dot_cx = dots_start_x + i * dot_spacing
        dot_cy = indicator_rect.y + indicator_rect.height // 2
        dot_rects_list.append(UiRect(dot_cx - 6, dot_cy - 6, 12, 12))

    return PageControlsLayout(
        placement=placement,
        previous_rect=previous_rect,
        next_rect=next_rect,
        indicator_rect=indicator_rect,
        visible_dot_count=visible_dot_count,
        active_dot_index=active_dot_index,
        dot_rects=tuple(dot_rects_list),
    )

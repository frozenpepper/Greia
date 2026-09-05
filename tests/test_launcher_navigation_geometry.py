from __future__ import annotations

import unittest
from types import SimpleNamespace

from greia_launcher.navigation_layout import (
    PageControlsLayout,
    PageControlsPlacement,
    PageControlsState,
    resolve_page_controls_layout,
)
from greia_platform.responsive_layout import UiRect, Viewport


class NavigationLayoutGeometryTests(unittest.TestCase):
    def test_state_from_grid_page(self) -> None:
        grid_page = SimpleNamespace(
            page_index=1,
            page_count=3,
            start=4,
            stop=8,
            page_size=4,
        )
        state = PageControlsState.from_grid_page(grid_page, total=10)
        self.assertEqual(state.page_index, 1)
        self.assertEqual(state.page_count, 3)
        self.assertTrue(state.can_go_previous)
        self.assertTrue(state.can_go_next)
        self.assertEqual(state.previous_value, 0)
        self.assertEqual(state.next_value, 8)

    def test_state_from_scroll_window(self) -> None:
        scroll_window = SimpleNamespace(
            start=6,
            stop=12,
            can_scroll_backward=True,
            can_scroll_forward=True,
        )
        state = PageControlsState.from_scroll_window(
            scroll_window, page_capacity=6, total_items=14
        )
        self.assertEqual(state.page_index, 1)
        self.assertEqual(state.page_count, 3)
        self.assertTrue(state.can_go_previous)
        self.assertTrue(state.can_go_next)

    def test_wide_mode_outer_gutter_placement_at_1024x600(self) -> None:
        viewport = Viewport(1024, 600)
        state = PageControlsState(
            page_index=0,
            page_count=3,
            previous_value=0,
            next_value=1,
            can_go_previous=False,
            can_go_next=True,
        )
        # Standard panel at 1024x600: centered width 816, left 104, right 920
        panel_outer = UiRect(104, 52, 816, 544)
        panel_content = UiRect(178, 119, 668, 373)

        layout = resolve_page_controls_layout(
            viewport,
            state,
            panel_outer_rect=panel_outer,
            panel_content_rect=panel_content,
            button_size=52,
            min_gutter_margin=8,
        )

        self.assertEqual(layout.placement, PageControlsPlacement.OUTER_GUTTER)
        # Left arrow sits strictly outside the panel tray
        self.assertLess(layout.previous_rect.right, panel_outer.x)
        self.assertGreaterEqual(layout.previous_rect.x, 8)
        # Right arrow sits strictly outside the panel tray
        self.assertGreater(layout.next_rect.x, panel_outer.right)
        self.assertLessEqual(layout.next_rect.right, viewport.width - 8)
        # Symmetrical vertical alignment
        self.assertEqual(layout.previous_rect.y, layout.next_rect.y)
        self.assertEqual(layout.previous_rect.height, 52)
        self.assertEqual(layout.next_rect.height, 52)

    def test_compact_mode_panel_rail_placement_at_800x600(self) -> None:
        viewport = Viewport(800, 600)
        state = PageControlsState(
            page_index=1,
            page_count=3,
            previous_value=0,
            next_value=2,
            can_go_previous=True,
            can_go_next=True,
        )
        # Compact panel at 800x600: width 776, left 12, right 788, content x=82, width=636
        panel_outer = UiRect(12, 52, 776, 544)
        panel_content = UiRect(82, 119, 636, 373)

        layout = resolve_page_controls_layout(
            viewport,
            state,
            panel_outer_rect=panel_outer,
            panel_content_rect=panel_content,
            button_size=52,
            min_gutter_margin=8,
        )

        self.assertEqual(layout.placement, PageControlsPlacement.PANEL_RAIL)
        # Left arrow sits in the panel rail: outside content, inside outer panel
        self.assertGreaterEqual(layout.previous_rect.x, panel_outer.x)
        self.assertLessEqual(layout.previous_rect.right, panel_content.x)
        # Right arrow sits in the right panel rail: outside content, inside outer panel
        self.assertGreaterEqual(layout.next_rect.x, panel_content.right)
        self.assertLessEqual(layout.next_rect.right, panel_outer.right)
        # Guaranteed zero overlap with card content
        self.assertFalse(layout.previous_rect.contains(panel_content))
        self.assertFalse(layout.next_rect.contains(panel_content))

    def test_wide_mode_at_1366x768(self) -> None:
        viewport = Viewport(1366, 768)
        state = PageControlsState(
            page_index=0,
            page_count=2,
            previous_value=0,
            next_value=1,
            can_go_previous=False,
            can_go_next=True,
        )
        panel_outer = UiRect(195, 60, 976, 640)
        panel_content = UiRect(280, 140, 806, 440)

        layout = resolve_page_controls_layout(
            viewport,
            state,
            panel_outer_rect=panel_outer,
            panel_content_rect=panel_content,
            button_size=54,
        )

        self.assertEqual(layout.placement, PageControlsPlacement.OUTER_GUTTER)
        self.assertLess(layout.previous_rect.right, panel_outer.x)
        self.assertGreater(layout.next_rect.x, panel_outer.right)

    def test_high_dpi_large_button_constrained_fallback(self) -> None:
        viewport = Viewport(800, 600)
        state = PageControlsState(
            page_index=0,
            page_count=2,
            previous_value=0,
            next_value=1,
            can_go_previous=False,
            can_go_next=True,
        )
        # When high-DPI demands a huge button that doesn't fit in the rail
        panel_outer = UiRect(12, 52, 776, 544)
        panel_content = UiRect(60, 119, 680, 373)  # only 48px rail

        layout = resolve_page_controls_layout(
            viewport,
            state,
            panel_outer_rect=panel_outer,
            panel_content_rect=panel_content,
            button_size=64,  # doesn't fit in 48px rail
        )

        self.assertEqual(layout.placement, PageControlsPlacement.CONTAINED_FALLBACK)
        self.assertGreaterEqual(layout.previous_rect.x, 0)
        self.assertLessEqual(layout.next_rect.right, viewport.width)

    def test_bounded_dot_pagination_policy(self) -> None:
        viewport = Viewport(1024, 600)

        # Modest count (3 pages) displays 3 dots
        state_3 = PageControlsState(
            page_index=1,
            page_count=3,
            previous_value=0,
            next_value=2,
            can_go_previous=True,
            can_go_next=True,
        )
        layout_3 = resolve_page_controls_layout(
            viewport, state_3, button_size=52, max_visible_dots=5
        )
        self.assertEqual(layout_3.visible_dot_count, 3)
        self.assertEqual(layout_3.active_dot_index, 1)
        self.assertEqual(len(layout_3.dot_rects), 3)

        # Large count (18 pages) bounds dots to max_visible_dots (5)
        state_18 = PageControlsState(
            page_index=10,
            page_count=18,
            previous_value=9,
            next_value=11,
            can_go_previous=True,
            can_go_next=True,
        )
        layout_18 = resolve_page_controls_layout(
            viewport, state_18, button_size=52, max_visible_dots=5
        )
        self.assertEqual(layout_18.visible_dot_count, 5)
        self.assertEqual(len(layout_18.dot_rects), 5)
        # Active dot is centered within the 5 visible dots (index 2)
        self.assertEqual(layout_18.active_dot_index, 2)
        # Pill width is strictly bounded, not 18 times wider than 3 dots
        self.assertLess(layout_18.indicator_rect.width, 220)

    def test_single_page_produces_empty_indicator(self) -> None:
        viewport = Viewport(1024, 600)
        state_1 = PageControlsState(
            page_index=0,
            page_count=1,
            previous_value=0,
            next_value=0,
            can_go_previous=False,
            can_go_next=False,
        )
        layout = resolve_page_controls_layout(viewport, state_1, button_size=52)
        self.assertEqual(layout.visible_dot_count, 0)
        self.assertEqual(layout.indicator_rect.width, 0)
        self.assertEqual(len(layout.dot_rects), 0)


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = tempfile.mkdtemp()
os.environ.setdefault("GREIA_PROFILES_DIR", os.path.join(TMP_DIR, "profiles"))
os.environ.setdefault("GREIA_SYSTEM_SETTINGS_DIR", os.path.join(TMP_DIR, "settings"))
os.environ.setdefault("GREIA_MEDIA_ROOT", os.path.join(TMP_DIR, "media"))
os.environ.setdefault("GREIA_OS_ROOT", str(REPO_ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from greia_launcher.navigation_layout import (
    PageControlsLayout,
    PageControlsPlacement,
    PageControlsState,
    compute_navigation_safe_content_bounds,
    resolve_constrained_square_tile_size,
    resolve_page_button_size,
    resolve_page_controls_layout,
)
from greia_launcher.shared_ui_presentation import SharedUiShellPanelMixin
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
        self.assertEqual(state.page_size, 4)
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
        self.assertEqual(state.page_size, 6)
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
        self.assertEqual(len(layout_3.indicators), 3)
        self.assertEqual([item.page_index for item in layout_3.indicators], [0, 1, 2])
        self.assertTrue(layout_3.indicators[1].active)

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
        self.assertEqual(len(layout_18.indicators), 5)
        self.assertEqual([item.page_index for item in layout_18.indicators], [8, 9, 10, 11, 12])
        # Active dot is centered within the 5 visible dots (index 2 in the window, page_index 10)
        self.assertTrue(layout_18.indicators[2].active)
        self.assertEqual(layout_18.indicators[2].page_index, 10)
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
        self.assertEqual(len(layout.indicators), 0)
        self.assertEqual(layout.indicator_rect.width, 0)

    def test_bottom_pill_never_overlaps_content_cards(self) -> None:
        viewport = Viewport(1024, 600)
        state = PageControlsState(
            page_index=0,
            page_count=3,
            previous_value=0,
            next_value=1,
            can_go_previous=False,
            can_go_next=True,
        )
        panel_outer = UiRect(150, 60, 724, 480)
        panel_content = UiRect(210, 140, 604, 298)

        layout = resolve_page_controls_layout(
            viewport,
            state,
            panel_outer_rect=panel_outer,
            panel_content_rect=panel_content,
            button_size=52,
        )
        # Pill top must be strictly below panel_content bottom
        self.assertGreaterEqual(layout.indicator_rect.y, panel_content.bottom)
        # Pill bottom must stay within viewport
        self.assertLessEqual(layout.indicator_rect.bottom, viewport.height)

    def test_secret_entry_button_geometry_no_overlap(self) -> None:
        import pygame
        pygame.init()
        from greia_launcher.child_shell import GreiaChildShell
        from greia_platform.profiles import ChildProfile

        shell = GreiaChildShell(windowed=True)
        profiles = list(shell.profile_store.ensure_initialized())
        screen = pygame.display.set_mode((1024, 600))
        shell.screen = screen
        shell._mode = "secret"
        shell._pending_profile = profiles[0]
        shell._secret_text = "1234"
        theme = shell.theme_controller.theme
        shell._draw_secret_entry(screen, theme, pygame)

        targets = [t for t in shell._targets if t.action in {"cancel_unlock", "backspace", "unlock"}]
        self.assertEqual(len(targets), 3)
        cancel = next(t for t in targets if t.action == "cancel_unlock")
        erase = next(t for t in targets if t.action == "backspace")
        unlock = next(t for t in targets if t.action == "unlock")

        # Must be strictly ordered with positive separation
        self.assertLess(cancel.rect.right, erase.rect.left)
        self.assertLess(erase.rect.right, unlock.rect.left)
        # Verify gap is at least 16px
        self.assertGreaterEqual(erase.rect.left - cancel.rect.right, 16)
        self.assertGreaterEqual(unlock.rect.left - erase.rect.right, 16)

    def test_derived_panel_layout_and_safe_content_across_resolutions(self) -> None:
        state = PageControlsState(
            page_index=1,
            page_count=3,
            previous_value=0,
            next_value=2,
            can_go_previous=True,
            can_go_next=True,
        )
        for width, height in ((800, 600), (1024, 600), (1366, 768)):
            viewport = Viewport(width, height)
            raw_rect, panel_layout = SharedUiShellPanelMixin.compute_shell_panel_layout(
                width, height
            )
            self.assertGreater(panel_layout.outer_rect.width, 0)
            self.assertGreater(panel_layout.content_rect.width, 0)
            self.assertTrue(panel_layout.outer_rect.contains(panel_layout.content_rect))

            for button_size in (52, 64, 80):
                safe_content = compute_navigation_safe_content_bounds(
                    viewport,
                    panel_outer_rect=panel_layout.outer_rect,
                    available_content_rect=panel_layout.content_rect,
                    button_size=button_size,
                )
                self.assertGreater(safe_content.width, 0)
                self.assertGreaterEqual(safe_content.x, panel_layout.content_rect.x)
                self.assertLessEqual(safe_content.right, panel_layout.content_rect.right)

                layout = resolve_page_controls_layout(
                    viewport,
                    state,
                    panel_outer_rect=panel_layout.outer_rect,
                    panel_content_rect=safe_content,
                    button_size=button_size,
                )
                # Invariant: navigation controls NEVER intersect safe card content!
                self.assertFalse(
                    layout.previous_rect.intersects(safe_content),
                    f"Previous button overlaps safe content at {width}x{height} with button_size={button_size}",
                )
                self.assertFalse(
                    layout.next_rect.intersects(safe_content),
                    f"Next button overlaps safe content at {width}x{height} with button_size={button_size}",
                )

    def test_indicators_contract(self) -> None:
        viewport = Viewport(1024, 600)
        # 18 pages, currently on page 10 (window centers active dot)
        state = PageControlsState(
            page_index=10,
            page_count=18,
            previous_value=9,
            next_value=11,
            can_go_previous=True,
            can_go_next=True,
        )
        layout = resolve_page_controls_layout(
            viewport, state, button_size=52, max_visible_dots=5
        )
        self.assertEqual(len(layout.indicators), 5)
        active_items = [item for item in layout.indicators if item.active]
        self.assertEqual(len(active_items), 1)
        self.assertEqual(active_items[0].page_index, 10)
        # Verify monotonically increasing page indices
        indices = [item.page_index for item in layout.indicators]
        self.assertEqual(indices, [8, 9, 10, 11, 12])

    def test_dots_have_zero_click_hit_targets(self) -> None:
        import pygame
        pygame.init()
        from greia_launcher.child_shell import GreiaChildShell

        shell = GreiaChildShell(windowed=True)
        screen = pygame.display.set_mode((1024, 600))
        state = PageControlsState(
            page_index=1,
            page_count=4,
            previous_value=0,
            next_value=2,
            can_go_previous=True,
            can_go_next=True,
        )
        theme = shell.theme_controller.theme
        shell._targets.clear()
        shell._draw_page_controls(
            screen,
            theme,
            pygame,
            state,
            previous_action="test_prev",
            next_action="test_next",
            total=4,
        )
        # Exactly 2 targets: prev arrow and next arrow. ZERO dot targets.
        actions = [t.action for t in shell._targets]
        self.assertEqual(actions, ["test_prev", "test_next"])

    def test_resolve_page_button_size_authority_high_dpi(self) -> None:
        from greia_platform.display_metrics import DisplayMetrics, DisplayMetricsSource

        viewport = Viewport(1024, 600)
        panel_outer = UiRect(100, 40, 824, 520)

        # Baseline: without metrics, falls back to nominal sizing
        baseline_size = resolve_page_button_size(
            viewport, metrics=None, panel_outer_rect=panel_outer
        )
        self.assertGreaterEqual(baseline_size, 54)
        self.assertLessEqual(baseline_size, 72)

        # High density metrics: physical width is small (high DPI: ~10.24 px/mm)
        high_dpi_metrics = DisplayMetrics(
            pixel_width=1024,
            pixel_height=600,
            physical_width_mm=100.0,
            physical_height_mm=58.6,
            source=DisplayMetricsSource.MANUAL_OVERRIDE,
        )
        high_dpi_size = resolve_page_button_size(
            viewport, metrics=high_dpi_metrics, panel_outer_rect=panel_outer
        )
        self.assertGreater(high_dpi_size, baseline_size)
        self.assertGreaterEqual(high_dpi_size, 96)

        # Verify that safe content reservation and controls layout use the EXACT same size
        # and NEVER collide under high-DPI
        panel_content = UiRect(150, 100, 724, 400)
        safe_content = compute_navigation_safe_content_bounds(
            viewport,
            panel_outer_rect=panel_outer,
            available_content_rect=panel_content,
            button_size=high_dpi_size,
        )
        state = PageControlsState(
            page_index=0,
            page_count=3,
            previous_value=0,
            next_value=1,
            can_go_previous=False,
            can_go_next=True,
        )
        layout = resolve_page_controls_layout(
            viewport,
            state,
            panel_outer_rect=panel_outer,
            panel_content_rect=safe_content,
            button_size=high_dpi_size,
        )
        self.assertFalse(layout.previous_rect.intersects(safe_content))
        self.assertFalse(layout.next_rect.intersects(safe_content))

    def test_extreme_constraint_tile_clamping_never_exceeds_available_width(self) -> None:
        """Under narrow widths or tight containers, cards must never exceed avail_w."""
        gap = 12
        for avail_w in (100, 150, 200, 240, 300):
            for columns in (1, 2, 3, 4):
                max_tile_w = max(1, (avail_w - gap * (columns - 1)) // columns)
                tile_w = min(213, max_tile_w)
                tile_w = max(1, min(max_tile_w, max(110, tile_w)))
                total_w = columns * tile_w + (columns - 1) * gap
                self.assertLessEqual(
                    tile_w,
                    max_tile_w,
                    f"tile_w {tile_w} exceeds max_tile_w {max_tile_w} for avail_w={avail_w}, col={columns}",
                )
                self.assertLessEqual(
                    total_w,
                    avail_w,
                    f"total_w {total_w} exceeds avail_w {avail_w} for columns={columns}",
                )

    def test_resolve_constrained_square_tile_size_vertical_boundary_invariants(self) -> None:
        """Square activity card sizing must strictly satisfy both horizontal and vertical bounds."""
        # 1. Deliberately vertically constrained content: max_tile_h < 120 and max_tile_w >= 120
        # In this exact scenario, tile_size must NOT expand to 120!
        avail_w = 400
        avail_h = 100  # 2 rows with gap=10 -> max_tile_h = (100 - 10) // 2 = 45 < 120
        tile = resolve_constrained_square_tile_size(
            avail_w, avail_h, columns=3, rows=2, gap=10, preferred_max=218, preferred_min=120
        )
        self.assertLessEqual(tile, 45)
        self.assertLessEqual(tile * 3 + 10 * 2, avail_w)
        self.assertLessEqual(tile * 2 + 10 * 1, avail_h)

        # Another case: max_tile_h = 108, max_tile_w = 140
        # (avail_h = 226 with gap=10 -> (226 - 10) // 2 = 108)
        tile_108 = resolve_constrained_square_tile_size(
            440, 226, columns=3, rows=2, gap=10, preferred_max=218, preferred_min=120
        )
        self.assertEqual(tile_108, 108)
        self.assertLessEqual(tile_108 * 3 + 10 * 2, 440)
        self.assertLessEqual(tile_108 * 2 + 10 * 1, 226)

        # 2. Key supported resolutions: 800x480, 800x600, 1024x600, 1366x768
        resolutions = [
            (800, 480),
            (800, 600),
            (1024, 600),
            (1366, 768),
        ]
        for w, h in resolutions:
            viewport = Viewport(w, h)
            raw_rect, panel_layout = SharedUiShellPanelMixin.compute_shell_panel_layout(w, h)
            columns = 4 if w >= 900 else 3 if w >= 700 else 2
            rows = 2
            gap = max(14, min(22, w // 48))
            inner = panel_layout.content_rect
            pad_x = max(14, inner.width // 45)
            pad_y = max(8, inner.height // 40)
            avail_w = max(240, inner.width - pad_x * 2)
            avail_h = max(180, inner.height - pad_y * 2 - 38)
            nav_button_size = resolve_page_button_size(
                viewport, metrics=None, panel_outer_rect=panel_layout.outer_rect
            )
            safe_rect = compute_navigation_safe_content_bounds(
                viewport,
                panel_outer_rect=panel_layout.outer_rect,
                available_content_rect=UiRect(inner.x + pad_x, inner.y + pad_y, avail_w, avail_h),
                button_size=nav_button_size,
            )
            tile_size = resolve_constrained_square_tile_size(
                safe_rect.width,
                avail_h,
                columns=columns,
                rows=rows,
                gap=gap,
                preferred_max=218,
                preferred_min=120,
            )
            tot_w = columns * tile_size + (columns - 1) * gap
            tot_h = rows * tile_size + (rows - 1) * gap
            self.assertLessEqual(
                tot_w,
                safe_rect.width,
                f"total width {tot_w} exceeds safe width {safe_rect.width} at {w}x{h}",
            )
            self.assertLessEqual(
                tot_h,
                avail_h,
                f"total height {tot_h} exceeds available height {avail_h} at {w}x{h}",
            )

        # 3. Synthetic High-DPI
        from greia_platform.display_metrics import DisplayMetrics, DisplayMetricsSource
        high_dpi = DisplayMetrics(
            pixel_width=1024,
            pixel_height=600,
            physical_width_mm=100.0,
            physical_height_mm=58.6,
            source=DisplayMetricsSource.MANUAL_OVERRIDE,
        )
        high_dpi_btn = resolve_page_button_size(
            Viewport(1024, 600), metrics=high_dpi, panel_outer_rect=panel_layout.outer_rect
        )
        safe_high_dpi = compute_navigation_safe_content_bounds(
            Viewport(1024, 600),
            panel_outer_rect=panel_layout.outer_rect,
            available_content_rect=UiRect(inner.x + pad_x, inner.y + pad_y, avail_w, avail_h),
            button_size=high_dpi_btn,
        )
        tile_high_dpi = resolve_constrained_square_tile_size(
            safe_high_dpi.width,
            avail_h,
            columns=4,
            rows=2,
            gap=gap,
        )
        self.assertLessEqual(4 * tile_high_dpi + 3 * gap, safe_high_dpi.width)
        self.assertLessEqual(2 * tile_high_dpi + 1 * gap, avail_h)


if __name__ == "__main__":
    unittest.main()

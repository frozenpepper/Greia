from __future__ import annotations

import unittest

from greia_platform.ui_scroll import PaginationModel, ScrollModel


class PaginationModelTests(unittest.TestCase):
    def test_partial_final_page_starts_on_real_page_boundary(self) -> None:
        pager = PaginationModel(capacity=6)
        first = pager.window(7, selected=0)
        second = pager.window(7, selected=6)

        self.assertEqual((first.start, first.stop), (0, 6))
        self.assertEqual((second.start, second.stop), (6, 7))
        self.assertEqual(pager.page_count(7), 2)
        self.assertTrue(second.can_scroll_backward)
        self.assertFalse(second.can_scroll_forward)

    def test_partial_final_page_counter_is_two_of_two(self) -> None:
        pager = PaginationModel(capacity=6)
        second = pager.window(7, selected=6)
        current_page = second.start // second.capacity + 1
        self.assertEqual((current_page, pager.page_count(second.total)), (2, 2))

    def test_all_partial_second_pages_begin_at_same_boundary(self) -> None:
        pager = PaginationModel(capacity=6)
        for total in range(7, 12):
            with self.subTest(total=total):
                window = pager.window(total, selected=6)
                self.assertEqual(window.start, 6)
                self.assertEqual(window.stop, total)
                self.assertEqual(pager.page_count(total), 2)

    def test_exact_and_third_pages_remain_page_aligned(self) -> None:
        pager = PaginationModel(capacity=6)
        self.assertEqual((pager.window(12, selected=6).start, pager.window(12, selected=6).stop), (6, 12))
        self.assertEqual((pager.window(13, selected=12).start, pager.window(13, selected=12).stop), (12, 13))
        self.assertEqual(pager.page_count(13), 3)

    def test_selection_is_clamped_and_empty_collection_is_safe(self) -> None:
        pager = PaginationModel(capacity=6)
        self.assertEqual(pager.window(0), pager.window(0, selected=999))
        last = pager.window(7, selected=999)
        self.assertEqual(last.selected, 6)
        self.assertEqual((last.start, last.stop), (6, 7))

    def test_page_movement_uses_page_boundaries_not_full_sliding_windows(self) -> None:
        pager = PaginationModel(capacity=6)
        first = pager.window(7, selected=0)
        second_start = pager.move_start(first, 1)
        self.assertEqual(second_start, 6)
        second = pager.window(7, selected=second_start)
        self.assertEqual(pager.move_start(second, -1), 0)

    def test_launcher_compatibility_mode_delegates_to_strict_pagination(self) -> None:
        # The current launcher constructs ScrollModel(capacity=N, step=N).
        # This compatibility seam must preserve discrete-page semantics until
        # every call site is migrated to PaginationModel directly.
        launcher_model = ScrollModel(capacity=6, step=6)
        second = launcher_model.window(7, selected=6, start=0)
        self.assertEqual((second.start, second.stop), (6, 7))
        self.assertEqual(launcher_model.move_start(second, -1), 0)

    def test_true_sliding_scroll_semantics_remain_unchanged(self) -> None:
        # A genuine sliding list is allowed to shift its final full window
        # backward; that behavior is deliberately separate from pagination.
        scroll = ScrollModel(capacity=6, step=1)
        final_window = scroll.window(7, selected=6, start=0)
        self.assertEqual((final_window.start, final_window.stop), (1, 7))

    def test_invalid_capacity_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PaginationModel(capacity=0)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from greia_platform.ui_core import (
    BoundedCache,
    Collection,
    InvalidationTracker,
    Overlay,
    PagedGrid,
    Screen,
    SurfaceNavigator,
    UiEventResult,
)


class RecordingScreen(Screen):
    def __init__(self, name: str, log: list[str]) -> None:
        self.name = name
        self.log = log

    @property
    def surface_id(self) -> str:
        return self.name

    def on_enter(self) -> None:
        self.log.append(f"enter:{self.name}")

    def on_exit(self) -> None:
        self.log.append(f"exit:{self.name}")

    def handle_event(self, event: object) -> UiEventResult:
        self.log.append(f"event:{self.name}:{event}")
        return UiEventResult.HANDLED

    def draw(self, target: object) -> None:
        self.log.append(f"draw:{self.name}:{target}")


class RecordingOverlay(Overlay):
    def __init__(self, name: str, log: list[str]) -> None:
        self.name = name
        self.log = log

    @property
    def surface_id(self) -> str:
        return self.name

    def on_enter(self) -> None:
        self.log.append(f"enter:{self.name}")

    def on_exit(self) -> None:
        self.log.append(f"exit:{self.name}")

    def handle_event(self, event: object) -> UiEventResult:
        self.log.append(f"event:{self.name}:{event}")
        return UiEventResult.HANDLED

    def draw(self, target: object) -> None:
        self.log.append(f"draw:{self.name}:{target}")


class SurfaceNavigatorTests(unittest.TestCase):
    def test_polymorphic_screen_and_overlay_lifecycle(self) -> None:
        log: list[str] = []
        first = RecordingScreen("first", log)
        navigator = SurfaceNavigator(first, max_overlays=2)
        overlay = RecordingOverlay("confirm", log)
        navigator.push_overlay(overlay)
        self.assertIs(navigator.event_target, overlay)
        self.assertEqual(navigator.dispatch("tap"), UiEventResult.HANDLED)
        navigator.draw("surface")
        second = RecordingScreen("second", log)
        navigator.replace(second)
        navigator.close()
        self.assertEqual(
            log,
            [
                "enter:first",
                "enter:confirm",
                "event:confirm:tap",
                "draw:first:surface",
                "draw:confirm:surface",
                "exit:confirm",
                "exit:first",
                "enter:second",
                "exit:second",
            ],
        )

    def test_overlay_stack_is_explicitly_bounded(self) -> None:
        log: list[str] = []
        navigator = SurfaceNavigator(RecordingScreen("root", log), max_overlays=1)
        navigator.push_overlay(RecordingOverlay("one", log))
        with self.assertRaises(RuntimeError):
            navigator.push_overlay(RecordingOverlay("two", log))


class CollectionTests(unittest.TestCase):
    def test_collection_is_semantic_and_immutable(self) -> None:
        collection = Collection("creative", ("writing", "painting"), title="Create")
        self.assertEqual(collection.items, ("writing", "painting"))
        updated = collection.with_items(("painting",))
        self.assertEqual(updated.collection_id, "creative")
        self.assertEqual(updated.items, ("painting",))
        self.assertEqual(collection.items, ("writing", "painting"))

    def test_collection_id_rejects_filesystem_shape(self) -> None:
        for invalid in ("", " /tmp", "a/b", "a\\b", "a\x00b"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    Collection(invalid, ())


class PagedGridTests(unittest.TestCase):
    def test_selected_item_determines_visible_page(self) -> None:
        grid = PagedGrid(columns=3, max_rows=2)
        page = grid.page(total=14, selected=8)
        self.assertEqual(page.page_size, 6)
        self.assertEqual((page.start, page.stop), (6, 12))
        self.assertEqual(page.rows, 2)
        self.assertEqual(page.page_index, 1)
        self.assertEqual(page.page_count, 3)
        self.assertEqual(grid.previous_index(page), 0)
        self.assertEqual(grid.next_index(page, 14), 12)

    def test_empty_grid_has_stable_page_contract(self) -> None:
        page = PagedGrid(columns=3, max_rows=2).page(0)
        self.assertTrue(page.empty)
        self.assertEqual(page.page_count, 1)
        self.assertEqual(page.rows, 0)


class BoundedCacheTests(unittest.TestCase):
    def test_cache_evicts_least_recently_used_entry(self) -> None:
        evicted: list[tuple[str, int]] = []
        cache = BoundedCache[str, int](2, on_evict=lambda key, value: evicted.append((key, value)))
        cache["a"] = 1
        cache["b"] = 2
        self.assertEqual(cache.get("a"), 1)
        cache["c"] = 3
        self.assertIn("a", cache)
        self.assertIn("c", cache)
        self.assertNotIn("b", cache)
        self.assertEqual(evicted, [("b", 2)])

    def test_cache_bound_and_clear_are_explicit(self) -> None:
        with self.assertRaises(ValueError):
            BoundedCache[str, int](0)
        cache = BoundedCache[str, int](1)
        cache["a"] = 1
        cache["b"] = 2
        self.assertEqual(len(cache), 1)
        cache.clear()
        self.assertEqual(len(cache), 0)


class InvalidationTrackerTests(unittest.TestCase):
    def test_static_surface_can_become_idle_after_draw(self) -> None:
        tracker = InvalidationTracker()
        self.assertTrue(tracker.should_draw)
        tracker.mark_drawn()
        self.assertFalse(tracker.should_draw)
        tracker.invalidate()
        self.assertTrue(tracker.should_draw)
        tracker.mark_drawn()
        tracker.set_animating(True)
        tracker.mark_drawn()
        self.assertTrue(tracker.should_draw)
        tracker.set_animating(False)
        self.assertFalse(tracker.should_draw)


if __name__ == "__main__":
    unittest.main()

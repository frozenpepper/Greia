from __future__ import annotations

import unittest

from greia_platform.ui_core import BoundedCache, Overlay, Screen, SurfaceNavigator, UiEventResult


class TestScreen(Screen):
    def __init__(self, log: list[str]) -> None:
        self.log = log

    @property
    def surface_id(self) -> str:
        return "root"

    def on_enter(self) -> None:
        self.log.append("enter:root")

    def on_exit(self) -> None:
        self.log.append("exit:root")

    def handle_event(self, event: object) -> UiEventResult:
        self.log.append(f"event:root:{event}")
        return UiEventResult.HANDLED

    def draw(self, target: object) -> None:
        self.log.append(f"draw:root:{target}")


class TestOverlay(Overlay):
    def __init__(self, log: list[str], *, modal: bool, result: UiEventResult) -> None:
        self.log = log
        self._modal = modal
        self.result = result

    @property
    def surface_id(self) -> str:
        return "overlay"

    @property
    def modal(self) -> bool:
        return self._modal

    def handle_event(self, event: object) -> UiEventResult:
        self.log.append(f"event:overlay:{event}")
        return self.result

    def draw(self, target: object) -> None:
        pass


class SurfaceNavigatorEdgeTests(unittest.TestCase):
    def test_close_is_idempotent_and_closed_navigator_rejects_use(self) -> None:
        log: list[str] = []
        navigator = SurfaceNavigator(TestScreen(log))
        navigator.close()
        navigator.close()
        self.assertEqual(log, ["enter:root", "exit:root"])
        with self.assertRaises(RuntimeError):
            navigator.draw("surface")

    def test_non_modal_ignored_event_falls_through(self) -> None:
        log: list[str] = []
        navigator = SurfaceNavigator(TestScreen(log))
        navigator.push_overlay(
            TestOverlay(log, modal=False, result=UiEventResult.IGNORED)
        )
        self.assertEqual(navigator.dispatch("tap"), UiEventResult.HANDLED)
        self.assertEqual(log[-2:], ["event:overlay:tap", "event:root:tap"])

    def test_modal_ignored_event_blocks_screen(self) -> None:
        log: list[str] = []
        navigator = SurfaceNavigator(TestScreen(log))
        navigator.push_overlay(
            TestOverlay(log, modal=True, result=UiEventResult.IGNORED)
        )
        self.assertEqual(navigator.dispatch("tap"), UiEventResult.IGNORED)
        self.assertNotIn("event:root:tap", log)


class BoundedCacheEdgeTests(unittest.TestCase):
    def test_replacing_none_invokes_eviction_callback(self) -> None:
        evicted: list[tuple[str, object]] = []
        cache = BoundedCache[str, object](
            1,
            on_evict=lambda key, value: evicted.append((key, value)),
        )
        cache["item"] = None
        cache["item"] = object()
        self.assertEqual(evicted, [("item", None)])


if __name__ == "__main__":
    unittest.main()

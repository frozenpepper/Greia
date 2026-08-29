from __future__ import annotations

import unittest

from greia_launcher.shell_window import NoopShellWindowController
from greia_launcher.shell_window_legacy_x import LegacyXShellWindowController


class _Display:
    def __init__(self, info: object) -> None:
        self._info = info
        self.calls = 0

    def get_wm_info(self) -> object:
        self.calls += 1
        if isinstance(self._info, Exception):
            raise self._info
        return self._info


class _Pygame:
    def __init__(self, info: object) -> None:
        self.display = _Display(info)


class _FocusBridge:
    def __init__(self, *, result: bool = True, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.windows: list[int] = []

    def focus_window(self, window_id: int) -> bool:
        self.windows.append(window_id)
        if self.error is not None:
            raise self.error
        return self.result


class LegacyXShellWindowControllerTests(unittest.TestCase):
    def test_x11_window_is_forwarded_to_native_bridge_once(self) -> None:
        bridge = _FocusBridge()
        pygame = _Pygame({"window": 42})
        controller = LegacyXShellWindowController(focus_bridge=bridge)

        self.assertTrue(controller.after_window_created(pygame))
        self.assertEqual(bridge.windows, [42])
        self.assertEqual(pygame.display.calls, 1)

    def test_controller_does_not_read_environment_to_choose_backend(self) -> None:
        bridge = _FocusBridge()
        pygame = _Pygame({"window": 42})
        controller = LegacyXShellWindowController(focus_bridge=bridge)

        self.assertTrue(controller.after_window_created(pygame))
        self.assertEqual(bridge.windows, [42])
        self.assertFalse(hasattr(controller, "_environment"))

    def test_missing_or_invalid_window_id_fails_soft(self) -> None:
        for info in ({}, {"window": 0}, {"window": "42"}, None):
            with self.subTest(info=info):
                bridge = _FocusBridge()
                controller = LegacyXShellWindowController(focus_bridge=bridge)
                self.assertFalse(controller.after_window_created(_Pygame(info)))
                self.assertEqual(bridge.windows, [])

    def test_wm_info_and_native_focus_errors_fail_soft(self) -> None:
        controller = LegacyXShellWindowController(
            focus_bridge=_FocusBridge(error=RuntimeError("x11 failed")),
        )
        self.assertFalse(controller.after_window_created(_Pygame({"window": 42})))

        controller = LegacyXShellWindowController(focus_bridge=_FocusBridge())
        self.assertFalse(
            controller.after_window_created(_Pygame(RuntimeError("wm info failed")))
        )

    def test_noop_controller_is_backend_neutral_and_has_no_side_effects(self) -> None:
        pygame = _Pygame(RuntimeError("must not inspect backend"))
        controller = NoopShellWindowController()

        self.assertTrue(controller.after_window_created(pygame))
        self.assertEqual(pygame.display.calls, 0)


if __name__ == "__main__":
    unittest.main()

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
    def __init__(
        self,
        *,
        result: bool = True,
        error: Exception | None = None,
        activity_window: int | None = 77,
    ) -> None:
        self.result = result
        self.error = error
        self.activity_window = activity_window
        self.windows: list[int] = []
        self.lookups: list[tuple[int, int]] = []
        self.raised: list[int] = []

    def focus_window(self, window_id: int) -> bool:
        self.windows.append(window_id)
        if self.error is not None:
            raise self.error
        return self.result

    def focused_window_for_process(self, process_id: int, *, excluding_window_id: int):
        self.lookups.append((process_id, excluding_window_id))
        if self.error is not None:
            raise self.error
        return self.activity_window

    def raise_and_focus_window(self, window_id: int) -> bool:
        self.raised.append(window_id)
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

    def test_exact_activity_pid_window_becomes_one_modal_lease(self) -> None:
        bridge = _FocusBridge(activity_window=77)
        controller = LegacyXShellWindowController(focus_bridge=bridge)
        pygame = _Pygame({"window": 42})

        lease = controller.prepare_activity_modal(
            pygame, session_id="session-1", activity_pid=1234
        )
        self.assertIsNotNone(lease)
        self.assertEqual(bridge.lookups, [(1234, 42)])
        self.assertEqual(lease.shell_window_id, 42)
        self.assertEqual(lease.activity_window_id, 77)
        self.assertTrue(controller.show_activity_modal(lease))
        self.assertEqual(bridge.raised, [42])
        self.assertTrue(controller.dismiss_activity_modal(lease))
        self.assertEqual(bridge.raised, [42, 77])

        # A prepared lease remains the exact owner until explicitly retired,
        # so a second request cannot alias the same native windows.
        self.assertIsNone(
            controller.prepare_activity_modal(
                pygame, session_id="session-2", activity_pid=5678
            )
        )
        controller.abandon_activity_modal(lease)
        newer = controller.prepare_activity_modal(
            pygame, session_id="session-2", activity_pid=5678
        )
        self.assertIsNotNone(newer)
        self.assertGreater(newer.generation, lease.generation)

    def test_modal_fails_closed_without_pid_owned_focused_activity_window(self) -> None:
        bridge = _FocusBridge(activity_window=None)
        controller = LegacyXShellWindowController(focus_bridge=bridge)
        pygame = _Pygame({"window": 42})
        self.assertIsNone(
            controller.prepare_activity_modal(
                pygame, session_id="session-1", activity_pid=1234
            )
        )
        self.assertEqual(bridge.lookups, [(1234, 42)])
        self.assertEqual(bridge.raised, [])

    def test_stale_or_foreign_modal_lease_cannot_raise_or_restore(self) -> None:
        bridge = _FocusBridge(activity_window=77)
        controller = LegacyXShellWindowController(focus_bridge=bridge)
        pygame = _Pygame({"window": 42})
        lease = controller.prepare_activity_modal(
            pygame, session_id="session-1", activity_pid=1234
        )
        self.assertIsNotNone(lease)
        from greia_launcher.shell_window import ShellActivityModalLease

        foreign = ShellActivityModalLease(
            lease.session_id,
            lease.generation,
            lease.activity_pid,
            lease.shell_window_id,
            lease.activity_window_id,
        )
        self.assertFalse(controller.show_activity_modal(foreign))
        self.assertFalse(controller.dismiss_activity_modal(foreign))
        self.assertEqual(bridge.raised, [])

    def test_noop_controller_is_backend_neutral_and_has_no_side_effects(self) -> None:
        pygame = _Pygame(RuntimeError("must not inspect backend"))
        controller = NoopShellWindowController()

        self.assertTrue(controller.after_window_created(pygame))
        self.assertEqual(pygame.display.calls, 0)
        self.assertIsNone(
            controller.prepare_activity_modal(
                pygame, session_id="session-1", activity_pid=1234
            )
        )


if __name__ == "__main__":
    unittest.main()

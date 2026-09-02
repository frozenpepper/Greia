from __future__ import annotations

import unittest
from unittest.mock import patch

from greia_platform.system_controls import (
    SystemControlAction,
    SystemControlApplyResult,
    SystemControlService,
    SystemControlSettings,
)
from greia_platform.system_controls_legacy_x import LegacyXMediaKeyListener


class _TransactionalStore:
    """Minimal desired-state authority exposing only the atomic mutation seam."""

    def __init__(self, current: SystemControlSettings) -> None:
        self.current = current
        self.mutate_calls = 0

    def read(self) -> SystemControlSettings:
        raise AssertionError("relative system-key updates must not use an unlocked read")

    def update(self, **_changes: object) -> SystemControlSettings:
        raise AssertionError("relative system-key updates must not split read and write")

    def mutate(self, mutation):
        self.mutate_calls += 1
        self.current = mutation(self.current)
        return self.current


class _RecordingBackend:
    def __init__(self) -> None:
        self.applied: list[SystemControlSettings] = []

    def apply(self, settings: SystemControlSettings) -> SystemControlApplyResult:
        self.applied.append(settings)
        return SystemControlApplyResult(
            applied=True,
            volume_available=True,
            brightness_available=True,
            brightness_backend="test",
        )


class _QueuedX11:
    def __init__(self, keycodes: list[int]) -> None:
        self.keycodes = list(keycodes)

    def XPending(self, _display: int) -> int:
        return len(self.keycodes)

    def XNextEvent(self, _display: int, event_pointer: object) -> int:
        keycode = self.keycodes.pop(0)
        event = event_pointer._obj  # ctypes.byref(_XEvent) target
        event.type = LegacyXMediaKeyListener._KEY_PRESS
        event.xkey.keycode = keycode
        return 0


class SystemControlTransactionTests(unittest.TestCase):
    def test_relative_key_update_uses_latest_locked_state(self) -> None:
        # Model a Parent write that has already committed immediately before the
        # physical key transaction. The key delta must be derived from that
        # latest state, not from a separately read stale snapshot.
        store = _TransactionalStore(
            SystemControlSettings(
                volume_percent=40,
                muted=True,
                brightness_percent=65,
            )
        )
        backend = _RecordingBackend()
        service = SystemControlService(store, backend)  # type: ignore[arg-type]

        result = service.handle_action(SystemControlAction.VOLUME_UP)

        self.assertTrue(result.applied)
        self.assertEqual(store.mutate_calls, 1)
        self.assertEqual(store.current.volume_percent, 45)
        self.assertFalse(store.current.muted)
        self.assertEqual(store.current.brightness_percent, 65)
        self.assertEqual(backend.applied, [store.current])

    def test_buffered_media_keys_are_drained_before_waiting_on_x_socket(self) -> None:
        listener = LegacyXMediaKeyListener.__new__(LegacyXMediaKeyListener)
        listener._display = 1
        listener._fd = 7
        listener._x11 = _QueuedX11([10, 11])
        listener._actions_by_keycode = {
            10: SystemControlAction.VOLUME_UP,
            11: SystemControlAction.VOLUME_DOWN,
        }

        # Both events are already buffered inside Xlib. Waiting on the kernel
        # socket here can delay/drop the second key until unrelated X traffic.
        with patch(
            "greia_platform.system_controls_legacy_x.select.select",
            side_effect=AssertionError("select must not run while Xlib has events"),
        ):
            first = listener.wait_action(0.25)
            second = listener.wait_action(0.25)

        self.assertIs(first, SystemControlAction.VOLUME_UP)
        self.assertIs(second, SystemControlAction.VOLUME_DOWN)
        self.assertEqual(listener._x11.keycodes, [])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from greia_launcher.display_session import (
    DisplaySessionCoordinator,
    DisplaySessionError,
    DisplaySessionPhase,
    DisplayTransport,
    DisplayTransportKind,
)


class _Backend:
    backend_id = "fake"

    def __init__(self, transport: DisplayTransport | None = None):
        self.transport = transport or DisplayTransport(
            kind=DisplayTransportKind.WAYLAND,
            sdl_video_driver="wayland",
            wayland_display="wayland-7",
            xdg_runtime_dir="/run/user/1000",
        )
        self.calls: list[tuple[str, str]] = []
        self.fail_prepare = False
        self.fail_present = False
        self.fail_restore = False

    def prepare_activity(self, session_id: str) -> DisplayTransport:
        self.calls.append(("prepare", session_id))
        if self.fail_prepare:
            raise RuntimeError("prepare exploded")
        return self.transport

    def present_activity(self, session_id: str) -> None:
        self.calls.append(("present", session_id))
        if self.fail_present:
            raise RuntimeError("present exploded")

    def restore_shell(self, session_id: str) -> None:
        self.calls.append(("restore", session_id))
        if self.fail_restore:
            raise RuntimeError("restore exploded")


class DisplayTransportTests(unittest.TestCase):
    def test_wayland_transport_exposes_only_bounded_connection_environment(self):
        transport = DisplayTransport(
            kind=DisplayTransportKind.WAYLAND,
            sdl_video_driver="wayland",
            wayland_display="wayland-3",
            xdg_runtime_dir="/run/user/1001",
        )
        self.assertEqual(
            dict(transport.environment()),
            {
                "SDL_VIDEODRIVER": "wayland",
                "WAYLAND_DISPLAY": "wayland-3",
                "XDG_RUNTIME_DIR": "/run/user/1001",
            },
        )
        self.assertNotIn("DRI_DEVICE", transport.environment())
        self.assertNotIn("GREIA_ACTIVITY_CAPABILITIES", transport.environment())

    def test_legacy_x11_requires_x_endpoint_and_authority(self):
        transport = DisplayTransport(
            kind=DisplayTransportKind.LEGACY_X11,
            sdl_video_driver="x11",
            display=":0",
            xauthority="/run/greia/xauthority",
        )
        self.assertEqual(transport.environment()["DISPLAY"], ":0")
        self.assertEqual(
            transport.environment()["XAUTHORITY"], "/run/greia/xauthority"
        )
        with self.assertRaisesRegex(ValueError, "requires display and xauthority"):
            DisplayTransport(
                kind=DisplayTransportKind.LEGACY_X11,
                sdl_video_driver="x11",
            )

    def test_direct_kmsdrm_transport_cannot_smuggle_window_system_endpoint(self):
        direct = DisplayTransport(
            kind=DisplayTransportKind.DIRECT_KMSDRM,
            sdl_video_driver="kmsdrm",
        )
        self.assertEqual(dict(direct.environment()), {"SDL_VIDEODRIVER": "kmsdrm"})
        with self.assertRaisesRegex(ValueError, "cannot carry X11/Wayland"):
            DisplayTransport(
                kind=DisplayTransportKind.DIRECT_KMSDRM,
                sdl_video_driver="kmsdrm",
                wayland_display="wayland-1",
            )
        with self.assertRaisesRegex(ValueError, "must request SDL kmsdrm"):
            DisplayTransport(
                kind=DisplayTransportKind.DIRECT_KMSDRM,
                sdl_video_driver="wayland",
            )

    def test_transport_driver_token_is_bounded(self):
        with self.assertRaisesRegex(ValueError, "unsupported characters"):
            DisplayTransport(
                kind=DisplayTransportKind.DIRECT_KMSDRM,
                sdl_video_driver="kmsdrm;evil",
            )


class DisplaySessionCoordinatorTests(unittest.TestCase):
    def test_normal_shell_activity_shell_transition(self):
        backend = _Backend()
        coordinator = DisplaySessionCoordinator(backend)
        self.assertTrue(coordinator.snapshot.shell_available)

        transport = coordinator.prepare_activity("session-1")
        self.assertIs(transport, backend.transport)
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.ACTIVITY_PREPARED)
        self.assertEqual(coordinator.snapshot.session_id, "session-1")
        self.assertEqual(coordinator.snapshot.generation, 1)

        coordinator.activity_ready("session-1")
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.ACTIVITY_VISIBLE)

        coordinator.activity_ended("session-1")
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertIsNone(coordinator.snapshot.session_id)
        self.assertIsNone(coordinator.snapshot.transport)
        self.assertEqual(
            backend.calls,
            [
                ("prepare", "session-1"),
                ("present", "session-1"),
                ("restore", "session-1"),
            ],
        )

    def test_launch_failure_after_prepare_uses_same_shell_recovery_path(self):
        backend = _Backend()
        coordinator = DisplaySessionCoordinator(backend)
        coordinator.prepare_activity("session-2")
        coordinator.abort_activity("session-2")
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(
            backend.calls,
            [("prepare", "session-2"), ("restore", "session-2")],
        )

    def test_child_crash_after_visible_uses_same_end_recovery_path(self):
        backend = _Backend()
        coordinator = DisplaySessionCoordinator(backend)
        coordinator.prepare_activity("session-crash")
        coordinator.activity_ready("session-crash")
        coordinator.activity_ended("session-crash")
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(backend.calls[-1], ("restore", "session-crash"))

    def test_prepare_failure_attempts_shell_recovery_before_returning_error(self):
        backend = _Backend()
        backend.fail_prepare = True
        coordinator = DisplaySessionCoordinator(backend)
        with self.assertRaisesRegex(DisplaySessionError, "could not prepare"):
            coordinator.prepare_activity("session-prepare-fail")
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(
            backend.calls,
            [
                ("prepare", "session-prepare-fail"),
                ("restore", "session-prepare-fail"),
            ],
        )

    def test_prepare_and_restore_failure_enters_failed_state(self):
        backend = _Backend()
        backend.fail_prepare = True
        backend.fail_restore = True
        coordinator = DisplaySessionCoordinator(backend)
        with self.assertRaisesRegex(DisplaySessionError, "shell recovery"):
            coordinator.prepare_activity("session-double-fail")
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.FAILED)
        self.assertIn("restore exploded", coordinator.snapshot.failure or "")

    def test_present_failure_recovers_shell(self):
        backend = _Backend()
        backend.fail_present = True
        coordinator = DisplaySessionCoordinator(backend)
        coordinator.prepare_activity("session-present-fail")
        with self.assertRaisesRegex(DisplaySessionError, "could not present"):
            coordinator.activity_ready("session-present-fail")
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(backend.calls[-1], ("restore", "session-present-fail"))

    def test_present_and_restore_failure_enters_failed_state(self):
        backend = _Backend()
        backend.fail_present = True
        backend.fail_restore = True
        coordinator = DisplaySessionCoordinator(backend)
        coordinator.prepare_activity("session-present-double-fail")
        with self.assertRaisesRegex(DisplaySessionError, "failed to restore"):
            coordinator.activity_ready("session-present-double-fail")
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.FAILED)
        self.assertIn("restore exploded", coordinator.snapshot.failure or "")

    def test_wrong_session_cannot_drive_active_display_transition(self):
        backend = _Backend()
        coordinator = DisplaySessionCoordinator(backend)
        coordinator.prepare_activity("session-owner")
        with self.assertRaisesRegex(DisplaySessionError, "identity"):
            coordinator.activity_ready("session-other")
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.ACTIVITY_PREPARED)
        self.assertNotIn(("present", "session-other"), backend.calls)

    def test_second_activity_cannot_prepare_until_shell_is_recovered(self):
        backend = _Backend()
        coordinator = DisplaySessionCoordinator(backend)
        coordinator.prepare_activity("session-one")
        with self.assertRaisesRegex(DisplaySessionError, "expected shell"):
            coordinator.prepare_activity("session-two")
        coordinator.abort_activity("session-one")
        coordinator.prepare_activity("session-two")
        self.assertEqual(coordinator.snapshot.session_id, "session-two")
        self.assertEqual(coordinator.snapshot.generation, 2)

    def test_invalid_session_id_is_rejected_before_backend_call(self):
        backend = _Backend()
        coordinator = DisplaySessionCoordinator(backend)
        for session_id in ("", "contains whitespace", "x" * 129):
            with self.subTest(session_id=session_id[:20]):
                with self.assertRaises((ValueError, DisplaySessionError)):
                    coordinator.prepare_activity(session_id)
        self.assertEqual(backend.calls, [])


if __name__ == "__main__":
    unittest.main()

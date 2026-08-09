from __future__ import annotations

import unittest

from greia_launcher.display_session import (
    DisplaySessionCoordinator,
    DisplaySessionError,
    DisplaySessionLease,
    DisplaySessionPhase,
    DisplayTransport,
    DisplayTransportKind,
)


class _Backend:
    backend_id = "fake"
    transport_kind = DisplayTransportKind.WAYLAND

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
        self.observed_present_phase: DisplaySessionPhase | None = None
        self.coordinator: DisplaySessionCoordinator | None = None

    def prepare_activity(self, session_id: str) -> DisplayTransport:
        self.calls.append(("prepare", session_id))
        if self.fail_prepare:
            raise RuntimeError("prepare exploded")
        return self.transport

    def present_activity(self, session_id: str) -> None:
        self.calls.append(("present", session_id))
        if self.coordinator is not None:
            self.observed_present_phase = self.coordinator.snapshot.phase
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

    def test_wayland_runtime_dir_must_be_absolute_and_endpoint_bounded(self):
        with self.assertRaisesRegex(ValueError, "must be absolute"):
            DisplayTransport(
                kind=DisplayTransportKind.WAYLAND,
                sdl_video_driver="wayland",
                wayland_display="wayland-1",
                xdg_runtime_dir="relative",
            )
        with self.assertRaisesRegex(ValueError, "whitespace/control"):
            DisplayTransport(
                kind=DisplayTransportKind.WAYLAND,
                sdl_video_driver="wayland",
                wayland_display="wayland 1",
                xdg_runtime_dir="/run/user/1000",
            )

    def test_legacy_x11_requires_bounded_x_endpoint_and_validates_optional_authority(self):
        direct_xinit = DisplayTransport(
            kind=DisplayTransportKind.LEGACY_X11,
            sdl_video_driver="x11",
            display=":0",
        )
        self.assertEqual(
            dict(direct_xinit.environment()),
            {"SDL_VIDEODRIVER": "x11", "DISPLAY": ":0"},
        )

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
        with self.assertRaisesRegex(ValueError, "X11 display is required"):
            DisplayTransport(
                kind=DisplayTransportKind.LEGACY_X11,
                sdl_video_driver="x11",
                xauthority="/run/greia/xauthority",
            )
        with self.assertRaisesRegex(ValueError, "must be absolute"):
            DisplayTransport(
                kind=DisplayTransportKind.LEGACY_X11,
                sdl_video_driver="x11",
                display=":0",
                xauthority="relative",
            )

    def test_legacy_x11_transport_cannot_carry_wayland_runtime_authority(self):
        with self.assertRaisesRegex(ValueError, "cannot carry Wayland authority"):
            DisplayTransport(
                kind=DisplayTransportKind.LEGACY_X11,
                sdl_video_driver="x11",
                display=":0",
                xauthority="/run/greia/xauthority",
                xdg_runtime_dir="/run/user/1000",
            )

    def test_transport_kind_and_sdl_backend_must_match(self):
        with self.assertRaisesRegex(ValueError, "must request SDL x11"):
            DisplayTransport(
                kind=DisplayTransportKind.LEGACY_X11,
                sdl_video_driver="wayland",
                display=":0",
                xauthority="/run/greia/xauthority",
            )
        with self.assertRaisesRegex(ValueError, "must request SDL wayland"):
            DisplayTransport(
                kind=DisplayTransportKind.WAYLAND,
                sdl_video_driver="x11",
                wayland_display="wayland-1",
                xdg_runtime_dir="/run/user/1000",
            )
        with self.assertRaisesRegex(TypeError, "DisplayTransportKind"):
            DisplayTransport(  # type: ignore[arg-type]
                kind="wayland",
                sdl_video_driver="wayland",
                wayland_display="wayland-1",
                xdg_runtime_dir="/run/user/1000",
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
    def _coordinator(
        self, backend: _Backend | None = None
    ) -> tuple[_Backend, DisplaySessionCoordinator]:
        backend = backend or _Backend()
        coordinator = DisplaySessionCoordinator(backend)
        backend.coordinator = coordinator
        return backend, coordinator

    def test_normal_shell_activity_shell_transition(self):
        backend, coordinator = self._coordinator()
        self.assertTrue(coordinator.snapshot.shell_available)

        lease = coordinator.prepare_activity("session-1")
        self.assertIsInstance(lease, DisplaySessionLease)
        self.assertIs(lease.transport, backend.transport)
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.ACTIVITY_PREPARED)
        self.assertEqual(coordinator.snapshot.session_id, "session-1")
        self.assertEqual(coordinator.snapshot.generation, 1)

        coordinator.activity_ready(lease)
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.ACTIVITY_VISIBLE)

        coordinator.activity_ended(lease)
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

    def test_present_operation_has_explicit_in_flight_phase(self):
        backend, coordinator = self._coordinator()
        lease = coordinator.prepare_activity("session-presenting")
        coordinator.activity_ready(lease)
        self.assertEqual(
            backend.observed_present_phase,
            DisplaySessionPhase.PRESENTING_ACTIVITY,
        )

    def test_launch_failure_after_prepare_uses_same_shell_recovery_path(self):
        backend, coordinator = self._coordinator()
        lease = coordinator.prepare_activity("session-2")
        coordinator.abort_activity(lease)
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(
            backend.calls,
            [("prepare", "session-2"), ("restore", "session-2")],
        )

    def test_child_crash_after_visible_uses_same_end_recovery_path(self):
        backend, coordinator = self._coordinator()
        lease = coordinator.prepare_activity("session-crash")
        coordinator.activity_ready(lease)
        coordinator.activity_ended(lease)
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(backend.calls[-1], ("restore", "session-crash"))

    def test_prepare_failure_attempts_shell_recovery_before_returning_error(self):
        backend = _Backend()
        backend.fail_prepare = True
        _, coordinator = self._coordinator(backend)
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

    def test_prepare_and_restore_failure_enters_failed_state_with_both_causes(self):
        backend = _Backend()
        backend.fail_prepare = True
        backend.fail_restore = True
        _, coordinator = self._coordinator(backend)
        with self.assertRaisesRegex(DisplaySessionError, "shell recovery"):
            coordinator.prepare_activity("session-double-fail")
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.FAILED)
        self.assertIn("prepare=prepare exploded", coordinator.snapshot.failure or "")
        self.assertIn("restore=restore exploded", coordinator.snapshot.failure or "")

    def test_present_failure_recovers_shell(self):
        backend = _Backend()
        backend.fail_present = True
        _, coordinator = self._coordinator(backend)
        lease = coordinator.prepare_activity("session-present-fail")
        with self.assertRaisesRegex(DisplaySessionError, "could not present"):
            coordinator.activity_ready(lease)
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(backend.calls[-1], ("restore", "session-present-fail"))

    def test_present_and_restore_failure_enters_failed_state_with_both_causes(self):
        backend = _Backend()
        backend.fail_present = True
        backend.fail_restore = True
        _, coordinator = self._coordinator(backend)
        lease = coordinator.prepare_activity("session-present-double-fail")
        with self.assertRaisesRegex(DisplaySessionError, "failed to restore"):
            coordinator.activity_ready(lease)
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.FAILED)
        self.assertIn("present=present exploded", coordinator.snapshot.failure or "")
        self.assertIn("restore=restore exploded", coordinator.snapshot.failure or "")

    def test_stale_lease_cannot_drive_reused_session_id(self):
        backend, coordinator = self._coordinator()
        old_lease = coordinator.prepare_activity("session-reused")
        coordinator.abort_activity(old_lease)

        new_lease = coordinator.prepare_activity("session-reused")
        self.assertEqual(old_lease.generation, 1)
        self.assertEqual(new_lease.generation, 2)
        calls_before = list(backend.calls)

        with self.assertRaisesRegex(DisplaySessionError, "stale"):
            coordinator.activity_ready(old_lease)

        self.assertEqual(backend.calls, calls_before)
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.ACTIVITY_PREPARED)
        coordinator.abort_activity(new_lease)

    def test_fabricated_value_equal_lease_is_not_ownership(self):
        _, coordinator = self._coordinator()
        lease = coordinator.prepare_activity("session-owner")
        fabricated = DisplaySessionLease(
            session_id=lease.session_id,
            generation=lease.generation,
            transport=lease.transport,
        )
        self.assertEqual(fabricated, lease)
        self.assertIsNot(fabricated, lease)
        with self.assertRaisesRegex(DisplaySessionError, "stale"):
            coordinator.activity_ready(fabricated)
        coordinator.abort_activity(lease)

    def test_callback_requires_lease_not_session_text(self):
        _, coordinator = self._coordinator()
        lease = coordinator.prepare_activity("session-owner")
        with self.assertRaisesRegex(TypeError, "DisplaySessionLease"):
            coordinator.activity_ready("session-owner")  # type: ignore[arg-type]
        coordinator.abort_activity(lease)

    def test_second_activity_cannot_prepare_until_shell_is_recovered(self):
        _, coordinator = self._coordinator()
        lease_one = coordinator.prepare_activity("session-one")
        with self.assertRaisesRegex(DisplaySessionError, "expected shell"):
            coordinator.prepare_activity("session-two")
        coordinator.abort_activity(lease_one)
        lease_two = coordinator.prepare_activity("session-two")
        self.assertEqual(coordinator.snapshot.session_id, "session-two")
        self.assertEqual(lease_two.generation, 2)

    def test_backend_transport_kind_mismatch_recovers_shell(self):
        backend = _Backend(
            DisplayTransport(
                kind=DisplayTransportKind.LEGACY_X11,
                sdl_video_driver="x11",
                display=":0",
            )
        )
        _, coordinator = self._coordinator(backend)
        with self.assertRaisesRegex(DisplaySessionError, "could not prepare"):
            coordinator.prepare_activity("session-wrong-kind")
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(
            backend.calls,
            [
                ("prepare", "session-wrong-kind"),
                ("restore", "session-wrong-kind"),
            ],
        )

    def test_invalid_backend_contract_rejected_before_use(self):
        class BadIdBackend(_Backend):
            backend_id = "contains whitespace"

        with self.assertRaisesRegex(ValueError, "unsupported characters"):
            DisplaySessionCoordinator(BadIdBackend())

        class BadKindBackend(_Backend):
            transport_kind = "wayland"  # type: ignore[assignment]

        with self.assertRaisesRegex(TypeError, "transport_kind"):
            DisplaySessionCoordinator(BadKindBackend())

    def test_invalid_session_id_is_rejected_before_backend_call(self):
        backend, coordinator = self._coordinator()
        for session_id in ("", "contains whitespace", "x" * 129):
            with self.subTest(session_id=session_id[:20]):
                with self.assertRaises(ValueError):
                    coordinator.prepare_activity(session_id)
        self.assertEqual(backend.calls, [])


if __name__ == "__main__":
    unittest.main()

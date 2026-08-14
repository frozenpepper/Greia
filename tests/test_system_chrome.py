from __future__ import annotations

import unittest

from greia_platform.system_chrome import (
    ActivitySystemChromeLayout,
    SystemNavigationAction,
)
from greia_launcher.system_chrome import (
    SystemChromeCoordinator,
    SystemChromeError,
    SystemChromeNavigationBridge,
    SystemChromePhase,
)


class RecordingChromeBackend:
    backend_id = "recording"

    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []
        self.actions: list[SystemNavigationAction] = []

    def prepare(self, session_id: str, *, back_available: bool) -> None:
        self.events.append(("prepare", session_id, back_available))

    def show(self, session_id: str) -> None:
        self.events.append(("show", session_id))

    def poll_action(self, session_id: str) -> SystemNavigationAction | None:
        self.events.append(("poll", session_id))
        return self.actions.pop(0) if self.actions else None

    def hide(self, session_id: str) -> None:
        self.events.append(("hide", session_id))


class RecordingStopController:
    def __init__(self) -> None:
        self.sessions: list[object] = []

    def request_stop(self, session: object) -> None:
        self.sessions.append(session)
        return None


class FakeSession:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


class ActivitySystemChromeLayoutTests(unittest.TestCase):
    def test_home_is_always_visible_and_fixed(self) -> None:
        without_back = ActivitySystemChromeLayout.for_surface(1024, 600)
        with_back = ActivitySystemChromeLayout.for_surface(
            1024, 600, back_available=True
        )
        self.assertEqual(without_back.home_hitbox, with_back.home_hitbox)
        self.assertEqual(without_back.protected_region, with_back.protected_region)
        self.assertEqual(without_back.visible_actions, (SystemNavigationAction.HOME,))
        self.assertEqual(
            with_back.visible_actions,
            (SystemNavigationAction.HOME, SystemNavigationAction.BACK),
        )

    def test_back_hitbox_is_reserved_even_when_hidden(self) -> None:
        layout = ActivitySystemChromeLayout.for_surface(1024, 600)
        self.assertTrue(
            layout.protected_region.contains(
                layout.back_hitbox.x, layout.back_hitbox.y
            )
        )
        self.assertIsNone(
            layout.action_at(layout.back_hitbox.x, layout.back_hitbox.y)
        )
        self.assertIs(
            layout.action_at(layout.home_hitbox.x, layout.home_hitbox.y),
            SystemNavigationAction.HOME,
        )

    def test_back_routes_only_when_platform_context_allows_it(self) -> None:
        layout = ActivitySystemChromeLayout.for_surface(
            1024, 600, back_available=True
        )
        self.assertIs(
            layout.action_at(layout.back_hitbox.x, layout.back_hitbox.y),
            SystemNavigationAction.BACK,
        )

    def test_reference_hit_target_is_child_sized_but_visual_is_smaller(self) -> None:
        layout = ActivitySystemChromeLayout.for_surface(1024, 600)
        self.assertGreaterEqual(layout.home_hitbox.width, 56)
        self.assertLess(layout.visual_size, layout.home_hitbox.width)
        self.assertLessEqual(layout.protected_region.height, 84)

    def test_tiny_surfaces_fail_instead_of_shrinking_home_away(self) -> None:
        with self.assertRaises(ValueError):
            ActivitySystemChromeLayout.for_surface(80, 40)


class SystemChromeCoordinatorTests(unittest.TestCase):
    def test_lifecycle_is_platform_owned_and_exact_lease_bound(self) -> None:
        backend = RecordingChromeBackend()
        coordinator = SystemChromeCoordinator(backend)
        lease = coordinator.prepare("session-a", back_available=False)
        self.assertIs(coordinator.snapshot.phase, SystemChromePhase.PREPARED)
        coordinator.activity_ready(lease)
        self.assertIs(coordinator.snapshot.phase, SystemChromePhase.VISIBLE)
        coordinator.activity_ended(lease)
        self.assertIs(coordinator.snapshot.phase, SystemChromePhase.HIDDEN)
        self.assertEqual(
            backend.events,
            [
                ("prepare", "session-a", False),
                ("show", "session-a"),
                ("hide", "session-a"),
            ],
        )

    def test_home_action_is_reported_without_activity_participation(self) -> None:
        backend = RecordingChromeBackend()
        backend.actions.append(SystemNavigationAction.HOME)
        coordinator = SystemChromeCoordinator(backend)
        lease = coordinator.prepare("session-a", back_available=False)
        coordinator.activity_ready(lease)
        self.assertIs(
            coordinator.poll_action(lease),
            SystemNavigationAction.HOME,
        )

    def test_unavailable_back_from_backend_fails_closed(self) -> None:
        backend = RecordingChromeBackend()
        backend.actions.append(SystemNavigationAction.BACK)
        coordinator = SystemChromeCoordinator(backend)
        lease = coordinator.prepare("session-a", back_available=False)
        coordinator.activity_ready(lease)
        with self.assertRaises(SystemChromeError):
            coordinator.poll_action(lease)
        self.assertIs(coordinator.snapshot.phase, SystemChromePhase.FAILED)

    def test_stale_lease_cannot_drive_later_generation(self) -> None:
        backend = RecordingChromeBackend()
        coordinator = SystemChromeCoordinator(backend)
        old = coordinator.prepare("session-a", back_available=False)
        coordinator.activity_ended(old)
        current = coordinator.prepare("session-b", back_available=True)
        with self.assertRaises(SystemChromeError):
            coordinator.activity_ready(old)
        coordinator.activity_ready(current)


class SystemChromeNavigationBridgeTests(unittest.TestCase):
    def test_home_requests_platform_stop_once_and_returns_shell_intent(self) -> None:
        backend = RecordingChromeBackend()
        backend.actions.extend(
            [SystemNavigationAction.HOME, SystemNavigationAction.HOME]
        )
        coordinator = SystemChromeCoordinator(backend)
        stop = RecordingStopController()
        bridge = SystemChromeNavigationBridge(coordinator, stop)  # type: ignore[arg-type]
        lease = coordinator.prepare("session-a", back_available=False)
        coordinator.activity_ready(lease)
        session = FakeSession("session-a")

        first = bridge.poll(lease, session)  # type: ignore[arg-type]
        second = bridge.poll(lease, session)  # type: ignore[arg-type]

        self.assertIsNotNone(first)
        assert first is not None
        self.assertIs(first.action, SystemNavigationAction.HOME)
        self.assertEqual(first.session_id, "session-a")
        self.assertIs(second, first)
        self.assertEqual(stop.sessions, [session])
        self.assertEqual(backend.actions, [SystemNavigationAction.HOME])

    def test_back_uses_same_platform_stop_path_but_preserves_destination_intent(self) -> None:
        backend = RecordingChromeBackend()
        backend.actions.append(SystemNavigationAction.BACK)
        coordinator = SystemChromeCoordinator(backend)
        stop = RecordingStopController()
        bridge = SystemChromeNavigationBridge(coordinator, stop)  # type: ignore[arg-type]
        lease = coordinator.prepare("session-a", back_available=True)
        coordinator.activity_ready(lease)
        session = FakeSession("session-a")

        request = bridge.poll(lease, session)  # type: ignore[arg-type]

        self.assertIsNotNone(request)
        assert request is not None
        self.assertIs(request.action, SystemNavigationAction.BACK)
        self.assertEqual(stop.sessions, [session])

    def test_bridge_rejects_cross_session_navigation(self) -> None:
        backend = RecordingChromeBackend()
        coordinator = SystemChromeCoordinator(backend)
        stop = RecordingStopController()
        bridge = SystemChromeNavigationBridge(coordinator, stop)  # type: ignore[arg-type]
        lease = coordinator.prepare("session-a", back_available=False)
        coordinator.activity_ready(lease)

        with self.assertRaises(SystemChromeError):
            bridge.poll(lease, FakeSession("session-b"))  # type: ignore[arg-type]
        self.assertEqual(stop.sessions, [])


if __name__ == "__main__":
    unittest.main()

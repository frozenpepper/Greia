from __future__ import annotations

import pathlib
import unittest

from greia_launcher.system_chrome import (
    TRUSTED_ACTION_MINIMUM_MM,
    SystemChromeCoordinator,
    SystemChromeError,
    SystemChromeNavigationBridge,
    SystemChromePhase,
    collection_policy_for_metrics,
    resolve_trusted_action_minimum_px,
)
from greia_launcher.system_chrome_legacy_x import (
    LegacyXSystemChromeBackend,
    layout_for_surface_with_metrics,
)
from greia_platform.display_metrics import (
    DisplayMetrics,
    DisplayMetricsSource,
    sanitize_display_metrics,
)
from greia_platform.system_chrome import (
    ActivitySystemChromeLayout,
    SystemNavigationAction,
)


class RecordingChromeBackend:
    backend_id = "recording"

    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []
        self.actions: list[SystemNavigationAction] = []
        self.fail_prepare = False
        self.fail_hide = False

    def prepare(self, session_id: str, *, back_available: bool) -> None:
        self.events.append(("prepare", session_id, back_available))
        if self.fail_prepare:
            raise RuntimeError("prepare failed")

    def show(self, session_id: str) -> None:
        self.events.append(("show", session_id))

    def poll_action(self, session_id: str) -> SystemNavigationAction | None:
        self.events.append(("poll", session_id))
        return self.actions.pop(0) if self.actions else None

    def hide(self, session_id: str) -> None:
        self.events.append(("hide", session_id))
        if self.fail_hide:
            raise RuntimeError("hide failed")


class RecordingStopController:
    def __init__(self) -> None:
        self.sessions: list[object] = []

    def request_stop(self, session: object) -> None:
        self.sessions.append(session)
        return None


class FakeSession:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


def _dense_metrics() -> DisplayMetrics:
    # 2048x1200 on the 222x130mm reference panel: ~234 DPI, so the shared
    # 10mm floor converts to floor(10 * 9.225) = 92px.
    metrics = sanitize_display_metrics(
        2048, 1200, 222.0, 130.0, DisplayMetricsSource.MANUAL_OVERRIDE
    )
    assert metrics is not None
    return metrics


def _reference_known_metrics() -> DisplayMetrics:
    # 1024x600 on the same panel: the 10mm floor is 46px, below every
    # existing conservative fallback, so existing geometry must be kept.
    metrics = sanitize_display_metrics(
        1024, 600, 222.0, 130.0, DisplayMetricsSource.MANUAL_OVERRIDE
    )
    assert metrics is not None
    return metrics


def _unknown_metrics() -> DisplayMetrics:
    metrics = sanitize_display_metrics(1024, 600)
    assert metrics is not None
    return metrics


class TrustedPhysicalFloorTests(unittest.TestCase):
    def test_shared_floor_is_single_sourced(self) -> None:
        self.assertEqual(TRUSTED_ACTION_MINIMUM_MM, 10.0)
        import greia_launcher.navigation_chrome_presentation as nav
        import greia_launcher.profile_chrome_presentation as profile

        self.assertIs(
            nav.resolve_trusted_action_minimum_px,
            resolve_trusted_action_minimum_px,
        )
        self.assertIs(
            profile.resolve_trusted_action_minimum_px,
            resolve_trusted_action_minimum_px,
        )

    def test_high_density_raises_minimum(self) -> None:
        self.assertEqual(
            resolve_trusted_action_minimum_px(_dense_metrics(), fallback_px=60),
            92,
        )

    def test_reference_density_keeps_existing_conservative_pixels(self) -> None:
        self.assertEqual(
            resolve_trusted_action_minimum_px(
                _reference_known_metrics(), fallback_px=60
            ),
            60,
        )

    def test_unknown_metrics_fall_back(self) -> None:
        self.assertEqual(
            resolve_trusted_action_minimum_px(_unknown_metrics(), fallback_px=60),
            60,
        )
        self.assertEqual(
            resolve_trusted_action_minimum_px(None, fallback_px=60),
            60,
        )

    def test_malformed_metrics_fail_soft_to_fallback(self) -> None:
        for bad in ("huge", 123, 45.6, object(), {"width": 1}, ["x"]):
            with self.subTest(bad=repr(bad)):
                self.assertEqual(
                    resolve_trusted_action_minimum_px(bad, fallback_px=60),
                    60,
                )

    def test_malformed_fallback_stays_bounded(self) -> None:
        for bad_fallback in ("huge", None, -5, 0, 100000, float("nan")):
            with self.subTest(bad_fallback=repr(bad_fallback)):
                result = resolve_trusted_action_minimum_px(
                    _dense_metrics(), fallback_px=bad_fallback
                )
                self.assertIsInstance(result, int)
                self.assertGreaterEqual(result, 8)
                self.assertLessEqual(result, 320)

    def test_result_never_shrinks_or_escapes_bounds(self) -> None:
        result = resolve_trusted_action_minimum_px(
            _reference_known_metrics(), fallback_px=64
        )
        self.assertEqual(result, 64)
        result = resolve_trusted_action_minimum_px(
            _dense_metrics(), fallback_px=320
        )
        self.assertEqual(result, 320)


class MetricsAwareChromeLayoutTests(unittest.TestCase):
    def test_unknown_metrics_match_base_geometry(self) -> None:
        for metrics in (None, _unknown_metrics()):
            with self.subTest(metrics=repr(metrics)):
                self.assertEqual(
                    layout_for_surface_with_metrics(1024, 600, metrics=metrics),
                    ActivitySystemChromeLayout.for_surface(1024, 600),
                )
                self.assertEqual(
                    layout_for_surface_with_metrics(
                        1024, 600, back_available=True, metrics=metrics
                    ),
                    ActivitySystemChromeLayout.for_surface(
                        1024, 600, back_available=True
                    ),
                )

    def test_reference_density_matches_base_geometry(self) -> None:
        self.assertEqual(
            layout_for_surface_with_metrics(
                1024, 600, metrics=_reference_known_metrics()
            ),
            ActivitySystemChromeLayout.for_surface(1024, 600),
        )

    def test_dense_metrics_grow_hitboxes_without_moving_home(self) -> None:
        base = ActivitySystemChromeLayout.for_surface(
            1024, 600, back_available=True
        )
        grown = layout_for_surface_with_metrics(
            1024, 600, back_available=True, metrics=_dense_metrics()
        )
        self.assertEqual(grown.home_hitbox.width, 92)
        self.assertEqual(grown.home_hitbox.height, 92)
        self.assertEqual(grown.back_hitbox.width, 92)
        # Home never moves for high DPI: origin, margin, and gap are stable.
        self.assertEqual(
            (grown.home_hitbox.x, grown.home_hitbox.y),
            (base.home_hitbox.x, base.home_hitbox.y),
        )
        self.assertEqual(
            grown.back_hitbox.x - grown.home_hitbox.right,
            base.back_hitbox.x - base.home_hitbox.right,
        )
        # The protected region still covers both hitboxes.
        self.assertTrue(
            grown.protected_region.contains(
                grown.home_hitbox.x, grown.home_hitbox.y
            )
        )
        self.assertTrue(
            grown.protected_region.contains(
                grown.back_hitbox.x, grown.back_hitbox.y
            )
        )
        # Decoration is not scaled: visual size is untouched.
        self.assertEqual(grown.visual_size, base.visual_size)
        self.assertTrue(grown.back_available)
        self.assertIs(
            grown.action_at(grown.home_hitbox.x, grown.home_hitbox.y),
            SystemNavigationAction.HOME,
        )
        self.assertIs(
            grown.action_at(grown.back_hitbox.x, grown.back_hitbox.y),
            SystemNavigationAction.BACK,
        )

    def test_surface_too_small_for_growth_fails_soft_to_base(self) -> None:
        base = ActivitySystemChromeLayout.for_surface(1024, 600)
        margin = base.home_hitbox.x
        gap = base.back_hitbox.x - base.home_hitbox.right
        hit = base.home_hitbox.width
        # Fits the base chrome exactly but cannot host the 92px grown chrome.
        width = margin * 2 + hit * 2 + gap
        height = margin * 2 + hit
        probe = ActivitySystemChromeLayout.for_surface(width, height)
        self.assertEqual(
            layout_for_surface_with_metrics(
                width, height, metrics=_dense_metrics()
            ),
            probe,
        )

    def test_collection_policy_applies_floor_only_to_minimum(self) -> None:
        base = collection_policy_for_metrics(None)
        self.assertEqual(base.minimum_item_px, 72)
        grown = collection_policy_for_metrics(_dense_metrics())
        self.assertGreater(grown.minimum_item_px, 72)
        self.assertEqual(grown.preferred_item_px, base.preferred_item_px)
        self.assertEqual(grown.maximum_item_px, base.maximum_item_px)
        self.assertEqual(grown.minimum_gap_px, base.minimum_gap_px)
        self.assertEqual(grown.maximum_gap_px, base.maximum_gap_px)
        fallback = collection_policy_for_metrics("bogus")
        self.assertEqual(fallback, base)

    def test_backend_prepare_threads_metrics(self) -> None:
        seen: dict[str, object] = {}

        class StubBridge:
            def prepare(self, *, back_available: bool, metrics=None):  # type: ignore[no-untyped-def]
                seen["back_available"] = back_available
                seen["metrics"] = metrics
                return layout_for_surface_with_metrics(
                    1024, 600,
                    back_available=back_available,
                    metrics=metrics,
                )

            def show(self) -> None:
                return None

            def poll_pointer_release(self):  # type: ignore[no-untyped-def]
                return None

            def hide(self) -> None:
                return None

        dense = _dense_metrics()
        backend = LegacyXSystemChromeBackend(bridge=StubBridge())  # type: ignore[arg-type]
        backend.prepare("session-m", back_available=True, metrics=dense)
        self.assertIs(seen["metrics"], dense)
        self.assertTrue(seen["back_available"])
        backend.hide("session-m")

        backend_plain = LegacyXSystemChromeBackend(bridge=StubBridge())  # type: ignore[arg-type]
        backend_plain.prepare("session-p", back_available=False)
        self.assertIsNone(seen["metrics"])
        backend_plain.hide("session-p")

    def test_touched_ui_code_has_no_hardware_identity_or_probing(self) -> None:
        root = pathlib.Path(__file__).resolve().parent.parent
        touched = [
            root / "src/greia_launcher/system_chrome.py",
            root / "src/greia_launcher/system_chrome_legacy_x.py",
            root / "src/greia_launcher/navigation_chrome_presentation.py",
            root / "src/greia_launcher/profile_chrome_presentation.py",
        ]
        for path in touched:
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8").lower()
                for token in ("xrandr", "xinput", "libinput", "edid", "toml"):
                    self.assertNotIn(token, source)
        for name in (
            "navigation_chrome_presentation.py",
            "profile_chrome_presentation.py",
        ):
            with self.subTest(consumer=name):
                source = (
                    root / "src/greia_launcher" / name
                ).read_text(encoding="utf-8")
                for token in ("XOpenDisplay", "XDisplayWidth", "ctypes"):
                    self.assertNotIn(token, source)
                # Metrics are injected by composition; render paths never
                # build or probe them.
                for token in (
                    "sanitize_display_metrics",
                    "metrics_from_mode",
                    "metrics_for_output",
                ):
                    self.assertNotIn(token, source)


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

    def test_prepare_failure_recovers_hidden_when_backend_cleanup_succeeds(self) -> None:
        backend = RecordingChromeBackend()
        backend.fail_prepare = True
        coordinator = SystemChromeCoordinator(backend)

        with self.assertRaisesRegex(SystemChromeError, "could not prepare"):
            coordinator.prepare("session-a", back_available=False)

        self.assertIs(coordinator.snapshot.phase, SystemChromePhase.HIDDEN)
        self.assertIsNone(coordinator.snapshot.session_id)
        self.assertEqual(
            backend.events,
            [("prepare", "session-a", False), ("hide", "session-a")],
        )

        backend.fail_prepare = False
        lease = coordinator.prepare("session-b", back_available=False)
        self.assertEqual(lease.session_id, "session-b")

    def test_prepare_failure_stays_failed_when_backend_cleanup_fails(self) -> None:
        backend = RecordingChromeBackend()
        backend.fail_prepare = True
        backend.fail_hide = True
        coordinator = SystemChromeCoordinator(backend)

        with self.assertRaises(SystemChromeError):
            coordinator.prepare("session-a", back_available=False)

        self.assertIs(coordinator.snapshot.phase, SystemChromePhase.FAILED)
        self.assertEqual(coordinator.snapshot.session_id, "session-a")
        self.assertIn("prepare failed", coordinator.snapshot.failure or "")

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

    def test_bridge_is_one_request_bounded_across_generations(self) -> None:
        backend = RecordingChromeBackend()
        backend.actions.extend([SystemNavigationAction.HOME, SystemNavigationAction.HOME])
        coordinator = SystemChromeCoordinator(backend)
        stop = RecordingStopController()
        bridge = SystemChromeNavigationBridge(coordinator, stop)  # type: ignore[arg-type]

        first_lease = coordinator.prepare("session-a", back_available=False)
        coordinator.activity_ready(first_lease)
        bridge.poll(first_lease, FakeSession("session-a"))  # type: ignore[arg-type]
        coordinator.activity_ended(first_lease)

        second_lease = coordinator.prepare("session-b", back_available=False)
        coordinator.activity_ready(second_lease)
        with self.assertRaises(SystemChromeError):
            bridge.poll(second_lease, FakeSession("session-b"))  # type: ignore[arg-type]

        bridge.clear(first_lease)
        request = bridge.poll(second_lease, FakeSession("session-b"))  # type: ignore[arg-type]
        self.assertIsNotNone(request)
        self.assertEqual(len(stop.sessions), 2)

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

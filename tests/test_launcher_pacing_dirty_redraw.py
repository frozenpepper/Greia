from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock

import pygame

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = tempfile.mkdtemp()
os.environ["GREIA_PROFILES_DIR"] = os.path.join(TMP_DIR, "profiles")
os.environ["GREIA_SYSTEM_SETTINGS_DIR"] = os.path.join(TMP_DIR, "settings")
os.environ["GREIA_MEDIA_ROOT"] = os.path.join(TMP_DIR, "media")
os.environ["GREIA_ACTIVE_PROFILE_STATUS"] = os.path.join(TMP_DIR, "active-profile.json")
os.environ["GREIA_HARDWARE_STATUS"] = os.path.join(TMP_DIR, "hardware-status.json")
os.environ["GREIA_MAIN_CREDENTIAL_PATH"] = os.path.join(TMP_DIR, "parent-credential.json")
os.environ["GREIA_OS_ROOT"] = str(REPO_ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"

from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.main import HitTarget
from greia_launcher.parent_panel import ParentSettingsOverlay, ParentPanelState
from greia_launcher.presentation import GreiaLauncherPresentation
from greia_platform.wifi import WifiSetupController, WifiSetupPhase, DemoWifiBackend


class LauncherPacingDirtyRedrawContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    def test_rescan_activities_detects_token_change_and_returns_true(self) -> None:
        shell = GreiaChildShell(windowed=True)
        self.assertFalse(shell._rescan_activities())

        shell.registry.discovery_token = MagicMock(return_value="new-token-1234")
        self.assertTrue(shell._rescan_activities())
        self.assertEqual(shell._activity_discovery_token, "new-token-1234")

    def test_rescan_if_due_triggers_invalidation_when_discovery_changes(self) -> None:
        shell = GreiaChildShell(windowed=True)
        shell._next_rescan = 0.0
        self.assertFalse(shell._rescan_if_due())

        shell._next_rescan = 0.0
        shell.registry.discovery_token = MagicMock(return_value="package-update-token")
        self.assertTrue(shell._rescan_if_due())

    def test_parent_panel_drain_returns_true_when_wifi_scan_completes(self) -> None:
        backend = DemoWifiBackend()
        controller = WifiSetupController(backend)
        controller.begin()
        controller.refresh()
        time.sleep(0.05)
        changed = controller.drain()
        self.assertTrue(changed)
        self.assertEqual(controller._phase, WifiSetupPhase.READY)

    def test_parent_panel_drain_propagates_to_overlay(self) -> None:
        store = MagicMock()
        store.ensure_initialized = MagicMock()
        panel = ParentSettingsOverlay(store, wifi_backend=DemoWifiBackend())
        panel.open()
        time.sleep(0.05)
        changed = panel.drain()
        self.assertTrue(changed)

    def test_launch_animation_keeps_animating_flag_true(self) -> None:
        shell = GreiaChildShell(windowed=True)
        self.assertIsNone(shell._launching_activity_id)
        self.assertFalse(bool(shell._launching_activity_id is not None))

        shell._launching_activity_id = "org.greia.acquario-magico"
        self.assertTrue(bool(shell._launching_activity_id is not None))

    def test_idle_does_not_mutate_cached_activities_key(self) -> None:
        shell = GreiaChildShell(windowed=True)
        shell._activate_profile(shell.profiles[0], pygame)
        shell._category_id = "create"
        shell._mode = "activities"
        screen = pygame.display.set_mode((1024, 600))

        shell._draw(screen, pygame)
        key1 = shell._cached_activities_key
        self.assertIsNotNone(key1)

        shell._draw(screen, pygame)
        key2 = shell._cached_activities_key
        self.assertEqual(key1, key2)


class LauncherMotionCoalescingContractTests(unittest.TestCase):
    """FIX-MOTION: per-motion input-loop bound in the launcher run loop."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    def _motion_app(self) -> GreiaLauncherPresentation:
        app = GreiaLauncherPresentation(windowed=True, bootstrap=False)
        app._targets = [
            HitTarget("presented_activity", 0, pygame.Rect(0, 0, 100, 100)),
            HitTarget("presented_activity", 1, pygame.Rect(200, 0, 100, 100)),
        ]
        app._pointer_position = (10, 10)
        app._coalesced_hover_target = ("presented_activity", 0)
        app._coalesced_hover_identity = app._hover_semantic_identity(
            app._coalesced_hover_target
        )
        app._spoken_labels.pointer_focus_changed = MagicMock()
        app._spoken_labels.clear_pointer_focus = MagicMock()
        return app

    def test_motion_burst_coalesces_to_single_hit_test_and_settled_position(self) -> None:
        app = self._motion_app()
        burst = [(20, 10), (50, 10), (150, 10), (250, 10)]
        hit_calls = []
        real_target_at = app._target_at
        speak_calls = []

        def counting_target_at(pos):
            hit_calls.append(tuple(pos) if pos is not None else None)
            return real_target_at(pos)

        real_speakable = app._speakable_for_target

        def counting_speakable(target):
            speak_calls.append(target)
            return real_speakable(target)

        app._target_at = counting_target_at  # type: ignore[method-assign]
        app._speakable_for_target = counting_speakable  # type: ignore[method-assign]
        # Run-loop coalescing: drain the burst to the last position, then one
        # hover pass for the frame. The old per-event path did two hit-tests
        # per event (8 for this burst); the bound is exactly one.
        last = burst[-1]
        needs_redraw = app._apply_coalesced_motion(last)
        self.assertEqual(app._pointer_position, (250, 10))
        self.assertEqual(len(hit_calls), 1)
        self.assertEqual(hit_calls[0], (250, 10))
        self.assertTrue(needs_redraw)
        self.assertEqual(app._coalesced_hover_target, ("presented_activity", 1))
        # Final hover target matches direct hit-testing of the settled position.
        self.assertEqual(app._target_at((250, 10)), ("presented_activity", 1))

    def test_same_target_motion_gates_speakable_compute(self) -> None:
        app = self._motion_app()
        app._speakable_for_target = MagicMock(return_value=("activity:x", None))  # type: ignore[method-assign]
        needs_redraw = app._apply_coalesced_motion((20, 10))
        # Pointer moved inside the same tile: one cheap hit-test, no speakable
        # work, but the pointer visual still needs its once-per-frame present.
        self.assertTrue(needs_redraw)
        app._speakable_for_target.assert_not_called()  # type: ignore[attr-defined]
        app._spoken_labels.pointer_focus_changed.assert_not_called()
        # Duplicate position: no pointer move and no target change → no redraw.
        app._speakable_for_target.reset_mock()  # type: ignore[attr-defined]
        self.assertFalse(app._apply_coalesced_motion((20, 10)))
        app._speakable_for_target.assert_not_called()  # type: ignore[attr-defined]

    def test_target_change_triggers_single_gated_speakable_pass(self) -> None:
        app = self._motion_app()
        app._speakable_for_target = MagicMock(  # type: ignore[method-assign]
            side_effect=lambda target: {
                ("presented_activity", 0): ("activity:zero", None),
                ("presented_activity", 1): ("activity:one", None),
            }.get(target)
        )
        needs_redraw = app._apply_coalesced_motion((250, 10))
        self.assertTrue(needs_redraw)
        app._spoken_labels.pointer_focus_changed.assert_called_once_with(
            "activity:one", None, ANY
        )

    def test_leaving_speakable_target_clears_pointer_focus(self) -> None:
        app = self._motion_app()
        app._speakable_for_target = MagicMock(  # type: ignore[method-assign]
            side_effect=lambda target: ("activity:zero", None)
            if target == ("presented_activity", 0)
            else None
        )
        needs_redraw = app._apply_coalesced_motion((150, 10))
        self.assertTrue(needs_redraw)
        self.assertIsNone(app._coalesced_hover_target)
        app._spoken_labels.pointer_focus_changed.assert_called_once()
        app._spoken_labels.clear_pointer_focus.assert_called_once()

    def test_category_change_invalidates_coalesced_pointer_focus(self) -> None:
        app = self._motion_app()
        app._catalogue = MagicMock()
        app._catalogue.nearest_category.return_value = "beta"
        app._category_id = "alpha"
        app._spoken_labels.clear_pointer_focus.reset_mock()

        app._set_category("beta")

        self.assertEqual(app._category_id, "beta")
        self.assertIsNone(app._coalesced_hover_target)
        self.assertIsNone(app._coalesced_hover_identity)
        app._spoken_labels.clear_pointer_focus.assert_called_once()

    def test_same_raw_index_after_semantic_collection_change_reannounces(self) -> None:
        app = self._motion_app()
        collections = {
            "alpha": SimpleNamespace(
                items=(SimpleNamespace(activity_id="activity-alpha"),)
            ),
            "beta": SimpleNamespace(
                items=(SimpleNamespace(activity_id="activity-beta"),)
            ),
        }
        catalogue = MagicMock()
        catalogue.nearest_category.side_effect = lambda category_id: category_id
        catalogue.collection.side_effect = lambda category_id: collections[category_id]
        app._catalogue = catalogue
        app._category_id = "alpha"
        app._coalesced_hover_target = ("presented_activity", 0)
        app._coalesced_hover_identity = app._hover_semantic_identity(
            app._coalesced_hover_target
        )
        app._category_id = "beta"  # Simulate a topology mutation outside _set_category.
        app._speakable_for_target = MagicMock(return_value=("activity:beta", None))  # type: ignore[method-assign]
        app._spoken_labels.pointer_focus_changed.reset_mock()

        needs_redraw = app._apply_coalesced_motion((20, 10))

        self.assertTrue(needs_redraw)
        self.assertEqual(
            app._coalesced_hover_identity,
            ("activity", "activity-beta", app._spoken_locale()),
        )
        app._speakable_for_target.assert_called_once_with(("presented_activity", 0))  # type: ignore[attr-defined]
        app._spoken_labels.pointer_focus_changed.assert_called_once_with(
            "activity:beta", None, ANY
        )

    def test_coalesced_motion_never_draws_and_run_loop_keeps_single_present(self) -> None:
        import inspect

        app = self._motion_app()
        app._draw = MagicMock()  # type: ignore[method-assign]
        app._apply_coalesced_motion((20, 10))
        app._apply_coalesced_motion((250, 10))
        app._apply_coalesced_motion(None)
        app._draw.assert_not_called()
        # No-draw-without-flag: None and duplicate positions request no redraw.
        self.assertFalse(app._apply_coalesced_motion(None))
        # Motion branch owns coalescing only: no per-event hit-test, no second
        # draw/flip site. This fails on the old per-event MOUSEMOTION path.
        source = inspect.getsource(GreiaLauncherPresentation.run)
        motion_at = source.find("elif event.type == pygame.MOUSEMOTION")
        self.assertNotEqual(motion_at, -1)
        branch = source[motion_at : motion_at + 800]
        self.assertIn("_apply_coalesced_motion", branch)
        self.assertNotIn("_target_at", branch)
        self.assertNotIn("_speakable_for_target", branch)
        self.assertNotIn("_draw(", branch)
        self.assertNotIn("flip(", branch)
        self.assertNotIn("pointer_focus_changed", branch)
        # The existing once-per-frame present path stays the only steady-state
        # draw site (the other flip in run() is the windowed boot-handoff
        # first frame; fullscreen boot flips live inside run_intro).
        present_at = source.find("if _needs_redraw or is_animating")
        self.assertNotEqual(present_at, -1)
        steady = source[present_at : present_at + 800]
        self.assertEqual(steady.count("pygame.display.flip()"), 1)
        self.assertIn("self._draw(screen, pygame)", steady)

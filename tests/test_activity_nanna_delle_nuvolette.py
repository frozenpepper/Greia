"""Comprehensive test suite for Nanna delle Nuvolette (org.greia.nanna-delle-nuvolette)."""

from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.typography import GreiaTypography

from activities.nanna_delle_nuvolette.cloud_art import CloudArt
from activities.nanna_delle_nuvolette.cloud_audio import CloudAudio
from activities.nanna_delle_nuvolette.cloud_content import BLANKETS, VALID_BLANKET_IDS
from activities.nanna_delle_nuvolette.cloud_model import CloudFriend, NightScene, REFERENCE_HEIGHT, REFERENCE_WIDTH
from activities.nanna_delle_nuvolette.cloud_renderer import CloudRenderer
from activities.nanna_delle_nuvolette.cloud_services import (
    DEFAULT_BLANKET_IDS,
    EVENT_REST_COMPLETED,
    STORAGE_KEY,
    GreiaCloudEvents,
    GreiaCloudStorage,
)
from activities.nanna_delle_nuvolette.cloud_app import CloudActivity


class TestCloudDomain(unittest.TestCase):
    """Test model invariants, blanket replacement, star limits, and readiness."""

    def test_blanket_inventory(self) -> None:
        self.assertEqual(len(BLANKETS), 6)
        self.assertEqual(len(VALID_BLANKET_IDS), 6)
        for b in BLANKETS:
            self.assertIn(b.blanket_id, VALID_BLANKET_IDS)

    def test_night_scene_creation(self) -> None:
        scene = NightScene.create_night("night-01")
        self.assertEqual(len(scene.clouds), 3)
        self.assertEqual(scene.available_stars, 9)
        self.assertFalse(scene.all_asleep)

        for c in scene.clouds:
            self.assertFalse(c.asleep)
            self.assertIsNone(c.blanket_id)
            self.assertEqual(len(c.star_ids), 0)
            self.assertFalse(c.ready_to_sleep)

    def test_tuck_blanket_and_replacement(self) -> None:
        scene = NightScene.create_night("night-01")
        cloud_id = scene.clouds[0].cloud_id

        # First blanket
        self.assertTrue(scene.tuck_blanket(cloud_id, "rose"))
        self.assertEqual(scene.clouds[0].blanket_id, "rose")

        # Replace blanket
        self.assertTrue(scene.tuck_blanket(cloud_id, "mint"))
        self.assertEqual(scene.clouds[0].blanket_id, "mint")

    def test_star_capacity_and_limit(self) -> None:
        scene = NightScene.create_night("night-01")
        cloud_id = scene.clouds[0].cloud_id

        # Add 3 stars
        self.assertTrue(scene.add_star(cloud_id))
        self.assertTrue(scene.add_star(cloud_id))
        self.assertTrue(scene.add_star(cloud_id))
        self.assertEqual(len(scene.clouds[0].star_ids), 3)
        self.assertEqual(scene.available_stars, 6)

        # 4th star rejected (cap of 3)
        self.assertFalse(scene.add_star(cloud_id))
        self.assertEqual(len(scene.clouds[0].star_ids), 3)
        self.assertEqual(scene.available_stars, 6)

    def test_ready_to_sleep_invariant(self) -> None:
        scene = NightScene.create_night("night-01")
        cloud_id = scene.clouds[0].cloud_id

        # Needs both blanket and >= 1 star
        self.assertFalse(scene.clouds[0].ready_to_sleep)

        scene.tuck_blanket(cloud_id, "amber")
        self.assertFalse(scene.clouds[0].ready_to_sleep)

        scene.add_star(cloud_id)
        self.assertTrue(scene.clouds[0].ready_to_sleep)

        # Put to sleep
        self.assertTrue(scene.put_to_sleep(cloud_id))
        self.assertTrue(scene.clouds[0].asleep)


class MockStorage:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def kv_get(self, key: str) -> str | None:
        return self._data.get(key)

    def kv_set(self, key: str, value: str) -> None:
        self._data[key] = value


class TestCloudServices(unittest.TestCase):
    """Test preference persistence, event emission, and corruption recovery."""

    def test_platform_completion_adapter_uses_supported_signature(self) -> None:
        with patch("activities.nanna_delle_nuvolette.cloud_services.emit_activity_event") as emit:
            GreiaCloudEvents().rest_completed("night-123", {"cloud_count": 3, "star_count": 4})
        emit.assert_called_once_with(
            EVENT_REST_COMPLETED,
            {"cloud_count": 3, "star_count": 4},
            idempotency_key="cloud-rest:night-123",
        )

    def test_storage_fallback_on_empty_or_corrupt(self) -> None:
        mock = MockStorage()
        storage = GreiaCloudStorage(storage=mock, key="test.cloud.pref.v1")
        # Empty
        self.assertEqual(storage.load_preferences(), DEFAULT_BLANKET_IDS)

        # Valid save & load
        valid = ("rose", "amber", "mint")
        self.assertTrue(storage.save_preferences(valid))
        self.assertEqual(storage.load_preferences(), valid)

        # Invalid save rejected
        self.assertFalse(storage.save_preferences(("invalid_id", "amber", "mint")))


class TestCloudAppInteraction(unittest.TestCase):
    """Test pointer drag/drop, all-sleep completion, and visual rendering."""

    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        activity_dir = Path(__file__).resolve().parent.parent / "activities" / "nanna_delle_nuvolette"
        self.resources = LocalizedResources(activity_dir, context)
        self.typography = GreiaTypography()
        self.art = CloudArt(REFERENCE_WIDTH, REFERENCE_HEIGHT)
        self.renderer = CloudRenderer(self.art, self.typography, self.resources)
        self.audio = CloudAudio()
        self.events = GreiaCloudEvents()
        self.storage = GreiaCloudStorage(storage=MockStorage())

    def test_platform_home_click_is_not_a_private_exit(self) -> None:
        from greia_platform.pygame_canvas import activity_viewport_for_surface
        app = CloudActivity(self.screen, self.renderer, self.audio, self.events, self.storage)
        rect = activity_viewport_for_surface(self.screen).protected_regions[0]
        app._handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (int(rect.x) + 1, int(rect.y) + 1)},
        ))
        self.assertTrue(app._running)
        self.assertEqual(app.scene.total_stars, 0)

    def test_drag_focus_loss_and_protected_drop_do_not_commit(self) -> None:
        from greia_platform.pygame_canvas import activity_viewport_for_surface
        app = CloudActivity(self.screen, self.renderer, self.audio, self.events, self.storage)
        app._selected_blanket_idx = 0
        app._drag_pos = (400, 400)
        app._handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertIsNone(app._selected_blanket_idx)
        self.assertIsNone(app._drag_pos)
        app._holding_star = True
        rect = activity_viewport_for_surface(self.screen).protected_regions[0]
        app._handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONUP,
            {"button": 1, "pos": (int(rect.x) + 1, int(rect.y) + 1)},
        ))
        self.assertFalse(app._holding_star)
        self.assertEqual(app.scene.total_stars, 0)

    def test_render_scene_without_error(self) -> None:
        scene = NightScene.create_night("test-night")
        self.renderer.draw_scene(self.screen, scene)
        self.assertEqual(self.screen.get_size(), (1024, 600))

    def test_app_session_completion(self) -> None:
        emitted_events: list[tuple[str, dict]] = []
        events_mock = GreiaCloudEvents()
        events_mock.rest_completed = lambda s_id, payload: emitted_events.append((s_id, payload))

        app = CloudActivity(
            self.screen,
            self.renderer,
            self.audio,
            events_mock,
            self.storage,
            night_id="test-night-01",
        )

        # Prepare all 3 clouds
        for c in app.scene.clouds:
            app.scene.tuck_blanket(c.cloud_id, "rose")
            app.scene.add_star(c.cloud_id)
            app.scene.put_to_sleep(c.cloud_id)

        app._check_all_asleep()
        self.assertEqual(len(emitted_events), 1)
        self.assertEqual(emitted_events[0][1]["cloud_count"], 3)
        self.assertEqual(emitted_events[0][1]["star_count"], 3)


if __name__ == "__main__":
    unittest.main()

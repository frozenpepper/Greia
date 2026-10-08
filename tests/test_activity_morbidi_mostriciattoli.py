"""Comprehensive test suite for Morbidi Mostriciattoli (org.greia.morbidi-mostriciattoli)."""

from __future__ import annotations

import os
from pathlib import Path
import random
import unittest
from unittest.mock import Mock, patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.typography import GreiaTypography

from activities.morbidi_mostriciattoli.monster_art import MonsterArt
from activities.morbidi_mostriciattoli.monster_audio import MonsterAudio
from activities.morbidi_mostriciattoli.monster_content import (
    ACCESSORY_OPTIONS,
    BODY_COLORS,
    BODY_SHAPES,
    EYE_OPTIONS,
    MOUTH_OPTIONS,
    TUFT_OPTIONS,
    VALID_ACCESSORY_IDS,
    VALID_COLOR_IDS,
    VALID_EYE_IDS,
    VALID_MOUTH_IDS,
    VALID_SHAPE_IDS,
    VALID_TUFT_IDS,
    Category,
)
from activities.morbidi_mostriciattoli.monster_model import (
    MAX_SAVED_PORTRAITS,
    MAX_UNDO_STACK,
    MonsterEditor,
    MonsterGallery,
    MonsterRecipe,
    REFERENCE_HEIGHT,
    REFERENCE_WIDTH,
)
from activities.morbidi_mostriciattoli.monster_renderer import MonsterRenderer
from activities.morbidi_mostriciattoli.monster_services import (
    EVENT_PORTRAIT_CREATED,
    STORAGE_KEY,
    GreiaMonsterEvents,
    GreiaMonsterStorage,
)
from activities.morbidi_mostriciattoli.monster_app import MonsterActivity, ViewMode


class MockStorage:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def kv_get(self, key: str) -> str | None:
        return self._data.get(key)

    def kv_set(self, key: str, value: str) -> None:
        self._data[key] = value


class TestMonsterDomain(unittest.TestCase):
    """Test part catalogue cardinality, recipe validation, undo/redo, and surprise me."""

    def test_catalogue_cardinality(self) -> None:
        self.assertEqual(len(BODY_SHAPES), 6)
        self.assertEqual(len(BODY_COLORS), 8)
        self.assertEqual(len(EYE_OPTIONS), 6)
        self.assertEqual(len(MOUTH_OPTIONS), 6)
        self.assertEqual(len(TUFT_OPTIONS), 6)
        self.assertEqual(len(ACCESSORY_OPTIONS), 6)

    def test_default_recipe_and_validation(self) -> None:
        recipe = MonsterRecipe.default_recipe("test-01")
        self.assertEqual(recipe.portrait_id, "test-01")
        self.assertEqual(recipe.name, "")
        self.assertIn(recipe.body_shape, VALID_SHAPE_IDS)
        self.assertIn(recipe.body_color, VALID_COLOR_IDS)
        self.assertIn(recipe.eyes, VALID_EYE_IDS)
        self.assertIn(recipe.mouth, VALID_MOUTH_IDS)
        self.assertIn(recipe.tuft, VALID_TUFT_IDS)
        self.assertIn(recipe.accessory, VALID_ACCESSORY_IDS)

        # Invalid field raises ValueError
        with self.assertRaises(ValueError):
            MonsterRecipe(
                portrait_id="bad",
                body_shape="invalid_shape",
                body_color="fluffy_pink",
                eyes="cyclops",
                mouth="snaggle_tooth",
                tuft="single_horn",
                accessory="bow_tie",
            )

    def test_editor_undo_redo_and_cap(self) -> None:
        editor = MonsterEditor()
        self.assertFalse(editor.can_undo())
        self.assertFalse(editor.can_redo())

        # Apply edits
        editor.select_category(Category.BODY_COLOR)
        editor.apply_option("sunny_yellow")
        self.assertTrue(editor.can_undo())
        self.assertEqual(editor.recipe.body_color, "sunny_yellow")

        editor.select_category(Category.EYES)
        editor.apply_option("two_dots")
        self.assertEqual(editor.recipe.eyes, "two_dots")

        # Undo
        self.assertTrue(editor.undo())
        self.assertEqual(editor.recipe.eyes, "cyclops")
        self.assertTrue(editor.can_redo())

        # Redo
        self.assertTrue(editor.redo())
        self.assertEqual(editor.recipe.eyes, "two_dots")

        # Undo cap 8
        for i in range(12):
            editor.select_category(Category.TUFT)
            editor.apply_option(TUFT_OPTIONS[i % len(TUFT_OPTIONS)].option_id)
        self.assertLessEqual(len(editor._undo_stack), MAX_UNDO_STACK)

    def test_surprise_me_differs_and_deterministic(self) -> None:
        editor = MonsterEditor()
        rng = random.Random(42)
        initial = editor.recipe
        self.assertTrue(editor.surprise_me(rng))
        self.assertNotEqual(editor.recipe, initial)


class TestMonsterGalleryAndStorage(unittest.TestCase):
    """Test gallery operations, 24 cap, deletion, and privacy invariant."""

    def test_gallery_cap_and_delete(self) -> None:
        gallery = MonsterGallery()
        self.assertEqual(gallery.count, 0)
        self.assertFalse(gallery.is_full)

        # Add up to 24
        for i in range(24):
            r = MonsterRecipe(
                portrait_id=f"monster-{i}",
                body_shape="round",
                body_color="fluffy_pink",
                eyes="cyclops",
                mouth="snaggle_tooth",
                tuft="single_horn",
                accessory="bow_tie",
                name=f"Monster {i}",
            )
            self.assertTrue(gallery.add(r))

        self.assertEqual(gallery.count, 24)
        self.assertTrue(gallery.is_full)

        # 25th rejected
        extra = MonsterRecipe.default_recipe("extra")
        self.assertFalse(gallery.add(extra))

        # Delete
        self.assertTrue(gallery.delete("monster-0"))
        self.assertEqual(gallery.count, 23)
        self.assertFalse(gallery.is_full)

    def test_event_adapter_emits_real_creation_with_no_child_name(self) -> None:
        recipe = MonsterRecipe.default_recipe("portrait-123").with_name("A secret")
        with patch("activities.morbidi_mostriciattoli.monster_services.emit_activity_event") as emit:
            GreiaMonsterEvents().portrait_created(recipe.portrait_id, recipe)
        emit.assert_called_once_with(
            EVENT_PORTRAIT_CREATED,
            {"portrait_id": "portrait-123", "named": True},
            idempotency_key="monster-portrait:portrait-123",
        )

    def test_storage_and_privacy_event(self) -> None:
        mock = MockStorage()
        storage = GreiaMonsterStorage(storage=mock)
        gallery = MonsterGallery()
        r = MonsterRecipe(
            portrait_id="monster-abc",
            body_shape="round",
            body_color="mint_green",
            eyes="big_goggles",
            mouth="toothy_smile",
            tuft="crown",
            accessory="party_hat",
            name="SuperSecretChildName",
        )
        gallery.add(r)
        self.assertTrue(storage.save_gallery(gallery))

        loaded = storage.load_gallery()
        self.assertEqual(loaded.count, 1)
        self.assertEqual(loaded.recipes[0].portrait_id, "monster-abc")
        self.assertEqual(loaded.recipes[0].name, "SuperSecretChildName")

        # Verify event payload never leaks name
        emitted: list[tuple[str, dict]] = []
        events = GreiaMonsterEvents()
        events.portrait_created = lambda s_id, rec: emitted.append(
            (s_id, {"portrait_id": rec.portrait_id, "named": bool(rec.name.strip())})
        )
        events.portrait_created("session-1", r)
        self.assertEqual(len(emitted), 1)
        self.assertNotIn("SuperSecretChildName", str(emitted[0][1]))
        self.assertEqual(emitted[0][1], {"portrait_id": "monster-abc", "named": True})


class TestMonsterAppInteraction(unittest.TestCase):
    """Test editor render, thumbnail LRU bounds, and interaction."""

    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        activity_dir = Path(__file__).resolve().parent.parent / "activities" / "morbidi_mostriciattoli"
        self.resources = LocalizedResources(activity_dir, context)
        self.typography = GreiaTypography()
        self.art = MonsterArt(REFERENCE_WIDTH, REFERENCE_HEIGHT, self.typography)
        self.renderer = MonsterRenderer(self.art, self.typography, self.resources)
        self.audio = MonsterAudio()
        self.events = GreiaMonsterEvents()
        self.storage = GreiaMonsterStorage(storage=MockStorage())

    def test_render_studio_and_gallery(self) -> None:
        editor = MonsterEditor()
        self.renderer.draw_editor(self.screen, editor)
        self.assertEqual(self.screen.get_size(), (1024, 600))

        gallery = MonsterGallery([MonsterRecipe.default_recipe("m1")])
        self.renderer.draw_gallery(self.screen, gallery)
        self.assertEqual(self.screen.get_size(), (1024, 600))

    def test_failed_portrait_save_preserves_editor_and_gallery(self) -> None:
        app = MonsterActivity(
            self.screen, self.renderer, self.audio, self.events, self.storage
        )
        original_editor = app.editor
        original_recipe = original_editor.recipe
        app.renderer.button_at = Mock(return_value="save")
        app.renderer.tab_at = Mock(return_value=None)
        app.renderer.option_at = Mock(return_value=None)
        app.storage.save_gallery = Mock(return_value=False)
        app.events = Mock()
        self.assertFalse(app._handle_pointer((512, 512)))
        self.assertEqual(app.gallery.count, 0)
        self.assertIs(app.editor, original_editor)
        self.assertEqual(app.editor.recipe, original_recipe)
        app.events.portrait_created.assert_not_called()

    def test_failed_portrait_delete_preserves_gallery_and_confirmation(self) -> None:
        recipe = MonsterRecipe.default_recipe("hold-123")
        app = MonsterActivity(
            self.screen, self.renderer, self.audio, self.events, self.storage
        )
        app.gallery.add(recipe)
        app.view_mode = ViewMode.GALLERY
        app.selected_portrait_id = recipe.portrait_id
        app.renderer.modal_delete_contains = Mock(return_value=True)
        app.storage.save_gallery = Mock(return_value=False)
        self.assertFalse(app._handle_pointer((512, 512)))
        self.assertEqual(app.gallery.count, 1)
        self.assertEqual(app.selected_portrait_id, "hold-123")

    def test_home_region_does_not_terminate_child_activity(self) -> None:
        from greia_platform.pygame_canvas import activity_viewport_for_surface

        app = MonsterActivity(
            self.screen, self.renderer, self.audio, self.events, self.storage
        )
        protected = activity_viewport_for_surface(self.screen).protected_regions[0]
        app._handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            {"button": 1, "pos": (int(protected.x) + 1, int(protected.y) + 1)},
        ))
        self.assertTrue(app._running)
        self.assertEqual(app.gallery.count, 0)

    def test_thumbnail_cache_lru_cap_and_clear(self) -> None:
        recipes = [MonsterRecipe.default_recipe(f"m-{i}") for i in range(16)]
        for r in recipes:
            self.renderer._get_thumbnail(r)
        self.assertLessEqual(len(self.renderer._thumb_cache), 12)

        self.renderer.clear_thumbnail_cache()
        self.assertEqual(len(self.renderer._thumb_cache), 0)


if __name__ == "__main__":
    unittest.main()

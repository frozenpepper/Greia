"""Fluffy Monsters: character creator (content, model, storage, art, app loop).

Source-level and headless (dummy SDL) evidence only; no hardware claim.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import re
import sys
import tomllib
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import hermetic_volume

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "morbidi_mostriciattoli"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from monster_content import (  # noqa: E402
    BODY_COLORS,
    BODY_SHAPES,
    CATEGORY_ORDER,
    MAX_NAME_SYLLABLES,
    MAX_SAVED_PORTRAITS,
    OPTIONS,
    PRESET_NAMES,
    SHARE_ROLE,
    SYLLABLES,
    VALID_IDS,
    Category,
    PartOption,
    Tint,
)
from monster_model import MAX_UNDO_STACK, MonsterEditor, MonsterGallery, MonsterRecipe  # noqa: E402
from monster_services import (  # noqa: E402
    DRAFT_KEY,
    EVENT_PORTRAIT_CREATED,
    STORAGE_KEY,
    GreiaMonsterEvents,
    GreiaMonsterStorage,
    picture_name,
)

PARTS = ACTIVITY_ROOT / "assets" / "runtime" / "parts"
SOURCES = ACTIVITY_ROOT / "assets" / "source"
FORBIDDEN_SVG = re.compile(
    r'<image|data:|<text|<tspan|<filter|fe[A-Z]|<mask|<pattern|<style|<script|foreignObject|<animate|blend-mode|skew|href="[^#]|sodipodi|inkscape:'
)


def setUpModule() -> None:
    hermetic_volume.install_for_module()


class MemoryStorage:
    def __init__(self) -> None:
        self.kv: dict[str, object] = {}
        self.files: dict[str, bytes] = {}
        self.fail_save = False

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        if self.fail_save and key == STORAGE_KEY:
            raise RuntimeError("storage write failed")
        json.dumps(value)
        self.kv[key] = value

    def kv_delete(self, key):
        return self.kv.pop(key, None) is not None

    def file_write_atomic(self, name, payload):
        self.files[name] = bytes(payload)

    def file_read(self, name):
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class FakeCreations:
    def __init__(self, *, fail: bool = False) -> None:
        self.published: list[tuple[str, dict]] = []
        self.fail = fail

    def publish_private_file(self, filename, **kwargs):
        if self.fail:
            raise RuntimeError("broker unavailable")
        self.published.append((filename, kwargs))
        return {}


class Events:
    def __init__(self) -> None:
        self.created: list[MonsterRecipe] = []

    def portrait_created(self, session_id, recipe):
        self.created.append(recipe)


def recipe(portrait_id: str = "m-1", **parts) -> MonsterRecipe:
    base = MonsterRecipe.default_recipe(portrait_id, created_at=1)
    for key, value in parts.items():
        base = base.with_choice(Category(key), value)
    return base


# ---------------------------------------------------------------------------------------


class ContentAndArtSourceTests(unittest.TestCase):
    def test_nine_picture_drawers_with_enough_choices(self) -> None:
        self.assertEqual(len(CATEGORY_ORDER), 9)
        for category in CATEGORY_ORDER:
            with self.subTest(category=category):
                self.assertGreaterEqual(len(OPTIONS[category]), 6)
                self.assertLessEqual(len(OPTIONS[category]), 8)  # one 2x4 tray, big tiles

    def test_every_part_has_its_rendition_and_source(self) -> None:
        stems: set[str] = set()
        for shape in BODY_SHAPES:
            stems |= {f"{shape.art}_fill", f"{shape.art}_line"}
        for category in CATEGORY_ORDER:
            for item in OPTIONS[category]:
                if isinstance(item, PartOption) and item.art is not None:
                    if item.tint is Tint.NONE or category is Category.PATTERN:
                        stems.add(item.art)
                    else:
                        stems |= {f"{item.art}_fill", f"{item.art}_line"}
        stems.add("mouth_laugh")
        for item in OPTIONS[Category.EYES]:
            if item.option_id != "happy_lashes":
                stems.add(f"{item.art}_blink")
        for stem in sorted(stems):
            with self.subTest(stem=stem):
                self.assertTrue((PARTS / f"{stem}.png").is_file())
                self.assertTrue((SOURCES / "parts" / f"{stem}.svg").is_file())

    def test_svg_sources_follow_the_authoring_rules(self) -> None:
        svgs = [*SOURCES.glob("*.svg"), *(SOURCES / "parts").glob("*.svg")]
        self.assertGreater(len(svgs), 60)
        for path in svgs:
            text = path.read_text()
            with self.subTest(svg=path.name):
                self.assertIsNone(FORBIDDEN_SVG.search(text))
                self.assertLessEqual(len(text.encode()), 6 * 1024)
                self.assertNotIn("#000000", text.upper())

    def test_runtime_art_stays_within_budget(self) -> None:
        total = sum(p.stat().st_size for p in (ACTIVITY_ROOT / "assets").rglob("*.png"))
        self.assertLess(total, 2 * 1024 * 1024)

    def test_not_momo(self) -> None:
        # Momo is the canonical purple, antennae, turquoise-feet monster.
        ids = {option_id for ids in VALID_IDS.values() for option_id in ids}
        self.assertFalse(any("antenna" in option_id for option_id in ids))
        for color in BODY_COLORS:
            r, g, b = color.base
            self.assertFalse(b > 200 and r > 130 and g < 80, color.option_id)  # no deep purple

    def test_share_role_is_accepted_by_leos_post(self) -> None:
        sys.path.insert(0, str(ROOT / "activities" / "posta_di_leo"))
        try:
            from postcard_content import FRONT_PICTURE_ROLES
        finally:
            sys.path.remove(str(ROOT / "activities" / "posta_di_leo"))
        self.assertIn(SHARE_ROLE, FRONT_PICTURE_ROLES)


class ModelTests(unittest.TestCase):
    def test_recipe_validation_and_round_trip(self) -> None:
        item = recipe(body_shape="star", body_color="peach_orange", arms="noodle", feet="boots")
        self.assertEqual(MonsterRecipe.from_json(item.to_json()), item)
        with self.assertRaises(ValueError):
            MonsterRecipe("bad", "blob", "sky_blue", "two_dots", "broad_grin", "horns", "none")
        with self.assertRaises(ValueError):
            MonsterRecipe("Has Spaces", "round", "sky_blue", "two_dots", "broad_grin", "horns", "none")

    def test_first_release_recipe_loads_with_mapped_ids(self) -> None:
        legacy = {
            "portrait_id": "0c1e7b1e-1111-4222-8333-444455556666",
            "body_shape": "bean",
            "body_color": "soft_lavender",
            "eyes": "cyclops",
            "mouth": "snaggle_tooth",
            "tuft": "little_antennas",
            "accessory": "monocle",
            "name": "Lulù",
            "created_at": 123,
        }
        loaded = MonsterRecipe.from_json(legacy)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.tuft, "round_ears")
        self.assertEqual(loaded.accessory, "glasses")
        self.assertEqual((loaded.pattern, loaded.arms, loaded.feet), ("none", "stubby", "paws"))
        self.assertEqual(loaded.name, "Lulù")
        self.assertIsNone(MonsterRecipe.from_json({**legacy, "eyes": "laser"}))

    def test_editor_blank_until_a_real_choice(self) -> None:
        editor = MonsterEditor()
        self.assertTrue(editor.is_blank)
        self.assertFalse(editor.choose(Category.BODY_SHAPE, editor.recipe.body_shape))
        self.assertTrue(editor.is_blank)
        self.assertTrue(editor.choose(Category.EYES, "cyclops"))
        self.assertFalse(editor.is_blank)
        self.assertTrue(editor.undo())
        self.assertTrue(editor.is_blank)
        self.assertFalse(editor.undo())

    def test_undo_is_bounded(self) -> None:
        editor = MonsterEditor()
        for index in range(MAX_UNDO_STACK + 6):
            editor.choose(Category.BODY_COLOR, BODY_COLORS[index % len(BODY_COLORS)].option_id)
        undos = 0
        while editor.undo():
            undos += 1
        self.assertLessEqual(undos, MAX_UNDO_STACK)

    def test_surprise_changes_the_look_and_keeps_the_name(self) -> None:
        editor = MonsterEditor()
        editor.add_syllable("BU")
        before = editor.recipe
        self.assertTrue(editor.surprise(random.Random(1)))
        self.assertNotEqual(editor.recipe.parts_key, before.parts_key)
        self.assertEqual(editor.recipe.name, "BU")

    def test_names_from_syllables(self) -> None:
        editor = MonsterEditor()
        for syllable in SYLLABLES[:MAX_NAME_SYLLABLES]:
            self.assertTrue(editor.add_syllable(syllable))
        self.assertEqual(editor.recipe.name, "".join(SYLLABLES[:MAX_NAME_SYLLABLES]))
        self.assertFalse(editor.add_syllable("BU"))
        self.assertTrue(editor.erase_syllable())
        self.assertEqual(editor.syllable_count, MAX_NAME_SYLLABLES - 1)
        self.assertFalse(editor.add_syllable("XX"))
        previous = editor.recipe.name
        self.assertTrue(editor.random_name(random.Random(3)))
        name = editor.recipe.name
        self.assertNotEqual(name, previous)
        self.assertTrue(name in PRESET_NAMES or (name[:2] in SYLLABLES and name[2:] in SYLLABLES))
        # A legacy free-text name is replaced by the first syllable tap.
        legacy = MonsterEditor(recipe().with_name("Pippo"), blank=False)
        legacy.add_syllable("KI")
        self.assertEqual(legacy.recipe.name, "KI")

    def test_gallery_keeps_24_newest_first_never_evicts(self) -> None:
        gallery = MonsterGallery()
        for index in range(MAX_SAVED_PORTRAITS):
            self.assertTrue(gallery.add(recipe(f"g-{index}")))
        self.assertTrue(gallery.is_full)
        self.assertFalse(gallery.add(recipe("extra")))
        self.assertEqual(gallery.recipes[0].portrait_id, "g-23")
        self.assertEqual(gallery.page_count(6), 4)
        seen = [item.portrait_id for page in range(4) for item in gallery.page(page, 6)]
        self.assertEqual(len(set(seen)), MAX_SAVED_PORTRAITS)
        self.assertTrue(gallery.delete("g-0"))
        self.assertFalse(gallery.delete("g-0"))


class StorageTests(unittest.TestCase):
    def test_first_release_string_catalogue_loads_and_migrates(self) -> None:
        backend = MemoryStorage()
        legacy = {
            "recipes": [
                {
                    "portrait_id": f"old-{index}",
                    "body_shape": "round",
                    "body_color": "fluffy_pink",
                    "eyes": "cyclops",
                    "mouth": "snaggle_tooth",
                    "tuft": "single_horn",
                    "accessory": "bow_tie",
                    "name": "Bubu",
                    "created_at": 1,
                }
                for index in range(3)
            ]
        }
        backend.kv[STORAGE_KEY] = json.dumps(legacy)
        storage = GreiaMonsterStorage(backend)
        gallery = storage.load_gallery()
        self.assertEqual(gallery.count, 3)
        self.assertEqual(gallery.recipes[0].tuft, "horns")
        self.assertTrue(storage.save_gallery(gallery))
        stored = backend.kv[STORAGE_KEY]
        self.assertEqual(stored["schema_version"], 2)
        self.assertEqual(storage.load_gallery().recipes, gallery.recipes)

    def test_unreadable_catalogue_is_never_overwritten(self) -> None:
        backend = MemoryStorage()
        backend.kv[STORAGE_KEY] = {"schema_version": 99, "recipes": []}
        storage = GreiaMonsterStorage(backend)
        self.assertFalse(storage.save_gallery(MonsterGallery([recipe()])))
        self.assertEqual(backend.kv[STORAGE_KEY]["schema_version"], 99)

    def test_draft_round_trip_and_clear(self) -> None:
        backend = MemoryStorage()
        storage = GreiaMonsterStorage(backend)
        item = recipe(eyes="three_sparkles").with_name("MIMI")
        self.assertTrue(storage.save_draft(item))
        self.assertEqual(storage.load_draft(), item)
        self.assertTrue(storage.save_draft(None))
        self.assertNotIn(DRAFT_KEY, backend.kv)
        self.assertIsNone(storage.load_draft())

    def test_shared_picture_needs_a_saved_friend_and_is_reclaimed_on_delete(self) -> None:
        backend = MemoryStorage()
        storage = GreiaMonsterStorage(backend)
        with self.assertRaises(ValueError):
            storage.private_png_name("m-1", b"png")
        gallery = MonsterGallery([recipe("m-1")])
        self.assertTrue(storage.save_gallery(gallery))
        name = storage.private_png_name("m-1", b"png")
        self.assertEqual(name, picture_name("m-1"))
        self.assertIn(name, backend.files)
        gallery.delete("m-1")
        self.assertTrue(storage.save_gallery(gallery))
        self.assertNotIn(name, backend.files)

    def test_creation_event_never_leaks_the_name(self) -> None:
        from unittest.mock import patch

        item = recipe("portrait-123").with_name("SECRET")
        with patch("monster_services.emit_activity_event") as emit:
            GreiaMonsterEvents().portrait_created(item.portrait_id, item)
        emit.assert_called_once_with(
            EVENT_PORTRAIT_CREATED,
            {"portrait_id": "portrait-123", "named": True},
            idempotency_key="monster-portrait:portrait-123",
        )


class ArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((64, 64))

    def test_every_part_composes_on_every_body(self) -> None:
        from monster_art import BOX_H, MonsterArt

        art = MonsterArt()
        for shape in BODY_SHAPES:
            for category in CATEGORY_ORDER:
                for item in OPTIONS[category]:
                    candidate = recipe(f"{shape.option_id}", body_shape=shape.option_id).with_choice(category, item.option_id)
                    surface = art.preview(candidate, category, 48)
                    self.assertEqual(surface.get_size(), (48, 48))
        portrait = art.portrait(recipe(), 288)
        self.assertEqual(portrait.get_height(), BOX_H)
        self.assertLessEqual(art.cached_count, 48 + 8 + 24)

    def test_body_colour_is_tinted_but_the_ink_contour_is_not(self) -> None:
        from monster_art import BOX_H, ORIGIN, MonsterArt

        art = MonsterArt()
        blue = art.portrait(recipe(body_color="sky_blue", eyes="happy_lashes", arms="none"), BOX_H)
        yellow = art.portrait(recipe(body_color="sunny_yellow", eyes="happy_lashes", arms="none"), BOX_H)
        # A point inside the round body, below the face.
        inside = (ORIGIN[0] + 128 - 50, ORIGIN[1] + 176)
        self.assertNotEqual(blue.get_at(inside)[:3], yellow.get_at(inside)[:3])
        # The body contour on the left side (x 57 on the part canvas) stays ink.
        x = ORIGIN[0] + 57
        y = ORIGIN[1] + 164
        darkest = min((blue.get_at((x + dx, y)) for dx in range(-3, 4)), key=lambda c: sum(c[:3]))
        self.assertLess(sum(darkest[:3]), 260)

    def test_blink_and_laugh_frames_differ(self) -> None:
        from monster_art import BOX_H, MonsterArt

        art = MonsterArt()
        item = recipe()
        normal = pygame.image.tobytes(art.portrait(item, BOX_H), "RGBA")
        self.assertNotEqual(normal, pygame.image.tobytes(art.portrait(item, BOX_H, blink=True), "RGBA"))
        self.assertNotEqual(normal, pygame.image.tobytes(art.portrait(item, BOX_H, laugh=True), "RGBA"))


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_is_an_honest_create_activity_that_shares_pngs(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text())
        self.assertEqual(manifest["activity"]["id"], "org.greia.morbidi-mostriciattoli")
        self.assertEqual(manifest["presentation"]["categories"], ["create"])
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertIn("controller", manifest["requirements"]["optional_capabilities"])
        self.assertEqual(manifest["creations"]["produces"], ["image/png"])
        self.assertEqual(manifest["storage"]["schema_version"], 1)
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])

    def test_four_locale_key_parity(self) -> None:
        keys = None
        for locale in ("en", "it", "es", "fr"):
            data = json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text())
            if keys is None:
                keys = set(data["strings"])
            self.assertEqual(set(data["strings"]), keys, locale)


# ---------------------------------------------------------------------------------------


def _app(*, size=(1024, 600), creations=None, backend=None, gallery=None, draft=None, locale="en"):
    from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
    from greia_platform.pygame_canvas import PygameReferenceCanvas
    from greia_platform.typography import GreiaTypography
    from monster_app import MonsterActivity
    from monster_audio import MonsterAudio

    screen = pygame.display.set_mode(size)
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    resources = LocalizedResources(ACTIVITY_ROOT, resolve_activity_locale(locale, support))
    backend = backend if backend is not None else MemoryStorage()
    storage = GreiaMonsterStorage(backend)
    if gallery is not None:
        assert storage.save_gallery(gallery)
    events = Events()
    now = [100.0]
    app = MonsterActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        storage=storage,
        events=events,
        audio=MonsterAudio(locale=locale),
        rng=random.Random(7),
        creations=creations,
        draft=draft,
        clock=lambda: now[0],
        wall_clock=lambda: 1_700_000_000,
    )
    return app, now, events, backend


class AppLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()

    def tap(self, app, control_id: str) -> bool:
        layer = app.sheet.layer if app.sheet is not None else app.controls.layer
        return app.tap(layer.target(control_id).rect.center)

    def frame(self, app, now, dt: float = 0.05) -> None:
        now[0] += dt
        app.step_frame()
        app.render()
        app.canvas.present()

    def test_build_name_save_celebrate_and_share_a_friend(self) -> None:
        from monster_app import Screen

        creations = FakeCreations()
        app, now, events, backend = _app(creations=creations)
        self.frame(app, now, 1.0)
        self.assertFalse(app.controls.save.enabled)  # no blank saves
        self.assertTrue(self.tap(app, "drawer.body_color"))
        self.assertTrue(self.tap(app, "option.body_color.peach_orange"))
        self.assertTrue(app.motion.reacting)  # the friend boings
        self.frame(app, now)
        self.tap(app, "drawer.arms")
        self.tap(app, "option.arms.noodle")
        self.tap(app, "drawer.name")
        self.tap(app, "syllable.0")
        self.tap(app, "syllable.0")
        self.assertEqual(app.editor.recipe.name, "BUBU")
        self.tap(app, "monster")  # tickle
        self.assertEqual(app.motion.kind, "giggle")
        self.frame(app, now, 3.0)
        self.assertTrue(app.controls.save.enabled)
        self.assertTrue(self.tap(app, "save"))
        self.assertIs(app.state, Screen.CELEBRATE)
        self.assertEqual(len(events.created), 1)
        self.assertEqual(app.gallery.count, 1)
        saved = app.gallery.recipes[0]
        self.assertEqual((saved.body_color, saved.arms, saved.name), ("peach_orange", "noodle", "BUBU"))
        self.assertIn("voice.saved", app.audio.played)
        self.assertIsNone(backend.kv.get(DRAFT_KEY))
        self.assertTrue(app.editor.is_blank)  # a fresh friend waits in the studio
        for _ in range(10):
            self.frame(app, now, 0.1)
        self.assertTrue(self.tap(app, "share"))
        self.assertEqual(len(creations.published), 1)
        name, kwargs = creations.published[0]
        self.assertEqual(kwargs["media_type"], "image/png")
        self.assertEqual(kwargs["role"], SHARE_ROLE)
        self.assertTrue(backend.files[name].startswith(b"\x89PNG"))
        self.tap(app, "share")  # the same friend is not published twice
        self.assertEqual(len(creations.published), 1)
        self.assertTrue(self.tap(app, "new"))
        self.assertIs(app.state, Screen.STUDIO)

    def test_failed_save_keeps_the_friend_and_announces_nothing(self) -> None:
        backend = MemoryStorage()
        app, now, events, _ = _app(backend=backend)
        self.tap(app, "drawer.eyes")
        self.tap(app, "option.eyes.cyclops")
        built = app.editor.recipe
        backend.fail_save = True
        self.tap(app, "save")
        self.assertEqual(app.gallery.count, 0)
        self.assertEqual(app.editor.recipe, built)
        self.assertEqual(events.created, [])

    def test_failed_share_is_gentle(self) -> None:
        app, now, _, _ = _app(creations=FakeCreations(fail=True))
        self.tap(app, "drawer.eyes")
        self.tap(app, "option.eyes.cyclops")
        self.tap(app, "save")
        self.tap(app, "share")
        self.assertEqual(app.shared_state, "error")

    def test_gallery_reaches_all_24_and_delete_needs_a_confirmed_sheet(self) -> None:
        from monster_app import Screen

        gallery = MonsterGallery([recipe(f"g-{index}") for index in range(MAX_SAVED_PORTRAITS)])
        app, now, _, backend = _app(gallery=gallery)
        self.tap(app, "gallery")
        self.assertIs(app.state, Screen.GALLERY)
        seen: set[str] = set()
        for page in range(4):
            for slot in range(6):
                self.tap(app, f"card.{slot}")
                self.assertIs(app.state, Screen.FRIEND)
                seen.add(app.open_id)
                self.tap(app, "back")
            if page < 3:
                self.tap(app, "page.next")
            self.frame(app, now)
        self.assertEqual(len(seen), MAX_SAVED_PORTRAITS)
        self.tap(app, "card.5")
        target = app.open_id
        self.tap(app, "delete")
        self.assertIsNotNone(app.sheet)
        self.frame(app, now)
        self.tap(app, "delete.keep")  # backing out is the safe choice
        self.assertEqual(app.gallery.count, MAX_SAVED_PORTRAITS)
        self.tap(app, "delete")
        self.tap(app, "delete.confirm")
        self.assertEqual(app.gallery.count, MAX_SAVED_PORTRAITS - 1)
        self.assertIsNone(app.gallery.get(target))
        self.assertIs(app.state, Screen.GALLERY)
        self.assertEqual(len(backend.kv[STORAGE_KEY]["recipes"]), MAX_SAVED_PORTRAITS - 1)

    def test_full_gallery_never_evicts(self) -> None:
        from monster_app import Screen

        gallery = MonsterGallery([recipe(f"g-{index}") for index in range(MAX_SAVED_PORTRAITS)])
        app, now, events, _ = _app(gallery=gallery)
        self.tap(app, "drawer.mouth")
        self.tap(app, "option.mouth.tiny_o")
        self.tap(app, "save")
        self.assertIsNotNone(app.sheet)
        self.assertEqual(app.gallery.count, MAX_SAVED_PORTRAITS)
        self.assertEqual(events.created, [])
        self.tap(app, "full.confirm")
        self.assertIs(app.state, Screen.GALLERY)
        self.assertEqual(app.editor.recipe.mouth, "tiny_o")  # the new friend is kept

    def test_keyboard_only_round(self) -> None:
        from monster_app import Screen

        app, now, events, _ = _app()
        app.controls.layer.focus("drawer.eyes", visible=True)
        app.press(pygame.K_RETURN)
        self.assertEqual(app.drawer, "eyes")
        app.controls.layer.focus("option.eyes.big_goggles", visible=True)
        app.press(pygame.K_SPACE)
        self.assertEqual(app.editor.recipe.eyes, "big_goggles")
        # Arrow navigation reaches the save button from the drawers.
        app.controls.layer.focus("undo", visible=True)
        for _ in range(8):
            app.press(pygame.K_RIGHT)
            if app.controls.layer.focused_id == "save":
                break
        self.assertEqual(app.controls.layer.focused_id, "save")
        app.press(pygame.K_RETURN)
        self.assertIs(app.state, Screen.CELEBRATE)
        self.assertEqual(len(events.created), 1)
        app.press(pygame.K_ESCAPE)
        self.assertIs(app.state, Screen.STUDIO)

    def test_controller_button_activates_the_focused_tile(self) -> None:
        app, now, _, _ = _app()
        app.controls.layer.focus("drawer.feet", visible=True)
        button = pygame.CONTROLLER_BUTTON_A
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=button, instance_id=0))
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONUP, button=button, instance_id=0))
        self.assertEqual(app.drawer, "feet")

    def test_home_region_input_is_ignored(self) -> None:
        from greia_platform.pygame_canvas import activity_viewport_for_surface

        app, now, _, _ = _app()
        protected = activity_viewport_for_surface(app.screen).protected_regions[0]
        point = (int(protected.x) + 2, int(protected.y) + 2)
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))
        self.assertTrue(app._running)

    def test_controls_stay_clear_of_protected_chrome_at_every_viewport(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            app, now, _, _ = _app(size=size)
            protected = app._layout_source.protected
            screens = [app.controls.layer.targets]
            app.open_gallery()
            screens.append(app.controls.layer.targets)
            for targets in screens:
                for target in targets:
                    with self.subTest(size=size, control=target.control_id):
                        self.assertFalse(target.rect.colliderect(protected))
                        self.assertTrue(pygame.Rect(0, 0, 1024, 600).contains(target.rect))
            for target in app.controls.layer.targets:
                if target.control_id.startswith("drawer"):
                    self.assertGreaterEqual(target.rect.width, 88)

    def test_unsaved_friend_survives_home_and_blank_friend_is_not_kept(self) -> None:
        from monster_app import Screen

        backend = MemoryStorage()
        app, now, _, _ = _app(backend=backend)
        app.shutdown()
        self.assertNotIn(DRAFT_KEY, backend.kv)
        app, now, _, _ = _app(backend=backend)
        self.tap(app, "drawer.tuft")
        self.tap(app, "option.tuft.crown")
        app.shutdown()
        draft = GreiaMonsterStorage(backend).load_draft()
        self.assertEqual(draft.tuft, "crown")
        restored, now, _, _ = _app(backend=backend, draft=draft)
        self.assertIs(restored.state, Screen.STUDIO)
        self.assertEqual(restored.editor.recipe.tuft, "crown")
        self.assertTrue(restored.controls.save.enabled)

    def test_idle_hint_points_then_nudges(self) -> None:
        app, now, _, _ = _app()
        self.frame(app, now, 1.0)
        now[0] += 7
        app.step_frame()
        self.assertIn("tray", app.effects.halos)
        self.tap(app, "drawer.eyes")
        self.tap(app, "option.eyes.cyclops")
        now[0] += 7
        app.step_frame()
        self.assertIn("save", app.effects.halos)
        now[0] += 13  # back-off: the nudging second hint comes 12 s after the first
        app.step_frame()
        self.assertIn("voice.nudge", app.audio.played)

    def test_full_round_renders_every_screen_at_small_viewports(self) -> None:
        for size in ((800, 480), (480, 320)):
            app, now, _, _ = _app(size=size, creations=FakeCreations(), locale="it")
            for drawer in ("body_shape", "body_color", "pattern", "eyes", "mouth", "tuft", "arms", "feet", "accessory", "name"):
                self.tap(app, f"drawer.{drawer}")
                self.frame(app, now)
            self.tap(app, "syllable.3")
            self.tap(app, "save")
            self.frame(app, now)
            self.tap(app, "friend.gallery")
            self.frame(app, now)
            self.tap(app, "card.0")
            self.frame(app, now)
            self.tap(app, "delete")
            self.frame(app, now)
            self.assertEqual(app.screen.get_size(), size)


if __name__ == "__main__":
    unittest.main()

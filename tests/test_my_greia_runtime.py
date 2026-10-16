"""Runtime tests for My Greia (``activities/workshop_settings``).

Source/headless evidence only: model rules, persistence mapping through the
trusted customization services, shared control-kit input (pointer, keyboard,
controller-equivalent semantic actions), the protected Home/Back region and an
app-loop run that makes choices and leaves cleanly.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
for entry in (str(ROOT / "src"), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import pygame  # noqa: E402

from greia_platform import activity_api  # noqa: E402
from greia_platform.activity_controls import ControlLayout  # noqa: E402
from greia_platform.customization import CustomizationError, ThemeStore, WallpaperImporter  # noqa: E402
from greia_platform.localization import activity_resources  # noqa: E402
from greia_platform.pygame_canvas import PygameReferenceCanvas  # noqa: E402
from greia_platform.system_chrome import ActivitySystemChromeLayout  # noqa: E402
from greia_platform.typography import GreiaTypography  # noqa: E402

ACTIVITY = ROOT / "activities" / "workshop_settings"
content = importlib.import_module("activities.workshop_settings.workshop_content")
model_mod = importlib.import_module("activities.workshop_settings.workshop_model")
services_mod = importlib.import_module("activities.workshop_settings.workshop_services")
controls_mod = importlib.import_module("activities.workshop_settings.workshop_controls")
preview_mod = importlib.import_module("activities.workshop_settings.workshop_preview")
app_mod = importlib.import_module("activities.workshop_settings.workshop_app")
main_mod = importlib.import_module("activities.workshop_settings.main")

ChoiceKind = model_mod.ChoiceKind
Look = model_mod.Look
MyGreiaModel = model_mod.MyGreiaModel
Tab = content.Tab
MEADOW = content.MEADOW_CHOICE
CUSTOM = content.CUSTOM_CHOICE


def _choices():
    Swatch = services_mod.Swatch
    return services_mod.MyGreiaChoices(
        avatars=services_mod.ordered_avatars(("unicorn", "robot", "owl", "dinosaur", "green_monster", "car")),
        backgrounds=(Swatch("cream", (247, 235, 203)), Swatch("sky", (207, 234, 247)), Swatch("mint", (217, 242, 208))),
        accents=(Swatch("sunshine", (255, 194, 52)), Swatch("grape", (148, 100, 201)), Swatch("leaf", (89, 184, 106))),
    )


class FakeCustomization:
    """In-memory CustomizationPort recording every persisted change."""

    def __init__(self, look: Look | None = None, *, refuse: set | None = None, custom: Path | None = None) -> None:
        self.look = look or Look(avatar="unicorn", background="cream", accent="sunshine")
        self.refuse = refuse or set()
        self.custom = custom
        self.applied: list[tuple[ChoiceKind, str]] = []

    def load(self):
        return services_mod.LoadedState(look=self.look, choices=_choices(), custom_wallpaper=self.custom)

    def apply(self, before, after):
        result = before
        for kind in after.changed_kinds(before):
            if kind in self.refuse:
                continue
            result = result.with_value(kind, after.value(kind))
            self.applied.append((kind, after.value(kind)))
        self.look = result
        return result


class FakeStorage:
    def __init__(self) -> None:
        self.kv: dict[str, object] = {}

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        self.kv[key] = value

    def kv_delete(self, key):
        return self.kv.pop(key, None) is not None


class SilentAudio:
    def __init__(self) -> None:
        self.events: list[str] = []

    def welcome(self):
        self.events.append("welcome")

    def play(self, name):
        self.events.append(f"sfx:{name}")

    def react(self, character, *, avatar_changed):
        self.events.append(f"react:{character}:{avatar_changed}")

    def stop_speech(self):
        self.events.append("stop")


class Clock:
    def __init__(self) -> None:
        self.now = 50.0

    def __call__(self) -> float:
        return self.now


def _overlaps(left, right) -> bool:
    return not (left.right <= right.x or right.right <= left.x or left.bottom <= right.y or right.bottom <= left.y)


class MyGreiaModelTests(unittest.TestCase):
    def test_room_colour_returns_home_to_the_meadow_and_undo_restores_the_picture(self) -> None:
        model = MyGreiaModel(Look("unicorn", "cream", "sunshine", wallpaper="bg.wallpaper.ocean"))
        transition = model.propose(ChoiceKind.BACKGROUND, "sky")
        self.assertEqual(transition.after.wallpaper, MEADOW)
        self.assertEqual(set(transition.changed), {ChoiceKind.BACKGROUND, ChoiceKind.WALLPAPER})
        model.commit(transition)
        undo = model.propose_undo()
        self.assertEqual(undo.after.wallpaper, "bg.wallpaper.ocean")
        self.assertEqual(undo.after.background, "cream")
        model.commit_undo(undo.after)
        self.assertFalse(model.can_undo)

    def test_picking_the_current_value_changes_nothing(self) -> None:
        model = MyGreiaModel(Look("unicorn", "cream", "sunshine"))
        self.assertIsNone(model.propose(ChoiceKind.AVATAR, "unicorn"))

    def test_undo_history_is_bounded(self) -> None:
        model = MyGreiaModel(Look("unicorn", "cream", "sunshine"))
        for index in range(content.UNDO_LIMIT + 8):
            model.commit(model.propose(ChoiceKind.ACCENT, "grape" if index % 2 == 0 else "leaf"))
        undone = 0
        while (transition := model.propose_undo()) is not None:
            model.commit_undo(transition.after)
            undone += 1
        self.assertEqual(undone, content.UNDO_LIMIT)

    def test_an_imported_picture_is_offered_only_while_it_exists(self) -> None:
        model = MyGreiaModel(Look("unicorn", "cream", "sunshine", wallpaper=CUSTOM), custom_available=True)
        model.commit(model.propose(ChoiceKind.WALLPAPER, "bg.wallpaper.snow"))
        self.assertFalse(model.custom_available)
        # Undo cannot recreate the replaced picture, so it keeps the current one.
        self.assertIsNone(model.propose_undo())

    def test_cast_faces_lead_the_avatar_choices(self) -> None:
        ordered = services_mod.ordered_avatars(("dinosaur", "owl", "car", "unicorn", "robot", "green_monster"))
        self.assertEqual(ordered[:4], ("unicorn", "robot", "owl", "green_monster"))
        self.assertEqual(ordered[4:], ("dinosaur", "car"))

    def test_preview_greeter_matches_the_shell_mapping(self) -> None:
        from greia_launcher import profile_chrome_presentation as shell

        for avatar in ("unicorn", "robot", "owl", "green_monster", "dinosaur", "", "car"):
            with self.subTest(avatar=avatar):
                self.assertEqual(preview_mod.greeter_for(avatar), shell.greeter_character_for(avatar))


class MyGreiaAppTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((1024, 600))
        self.clock = Clock()
        self.services = FakeCustomization()
        self.audio = SilentAudio()
        self.app = self._make_app()

    def tearDown(self) -> None:
        pygame.quit()

    def _make_app(self, size=(1024, 600)):
        self.screen = pygame.display.set_mode(size)
        return app_mod.MyGreiaApp(
            screen=self.screen,
            canvas=PygameReferenceCanvas(self.screen),
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY, requested_locale="en"),
            services=self.services,
            audio=self.audio,
            clock=self.clock,
        )

    def test_tapping_an_avatar_saves_it_and_the_friend_cheers(self) -> None:
        self.assertTrue(self.app.tap_control("avatar.robot"))
        self.assertEqual(self.services.applied, [(ChoiceKind.AVATAR, "robot")])
        self.assertEqual(self.app.model.look.avatar, "robot")
        self.assertIn("react:dani:True", self.audio.events)
        self.assertTrue(self.app.preview.animating)
        self.assertTrue(self.app.controls.layer.target("avatar.robot").selected)
        self.assertFalse(self.app.controls.layer.target("avatar.unicorn").selected)
        self.assertTrue(self.app.controls.undo.enabled)

    def test_every_tab_offers_pictures_and_keyboard_chooses_and_undoes(self) -> None:
        expected = {
            Tab.ME: ChoiceKind.AVATAR,
            Tab.COLOURS: ChoiceKind.BACKGROUND,
            Tab.PICTURES: ChoiceKind.WALLPAPER,
            Tab.SIZE: ChoiceKind.SIZE,
        }
        for tab in content.TABS:
            self.app._on_tab(tab)
            kinds = {self.app.controls.tile_value(tile.control_id)[0] for tile in self.app.controls.tiles}
            self.assertIn(expected[tab], kinds)
            for tile in self.app.controls.tiles:
                self.assertIsNotNone(tile.icon, tile.control_id)
        self.app._on_tab(Tab.ME)
        # Tab key: next picture tab; arrows + Return choose without a pointer.
        self.app.press(pygame.K_TAB)
        self.assertIs(self.app.model.tab, Tab.COLOURS)
        self.app.press(pygame.K_DOWN)
        self.assertTrue(self.app.controls.focus_in_tiles())
        self.app.press(pygame.K_RIGHT)
        focused = self.app.controls.layer.focused_id
        self.app.press(pygame.K_RETURN)
        kind, value = self.app.controls.tile_value(focused)
        self.assertEqual(self.app.model.look.value(kind), value)
        # Undo returns to the previous look and persists it.
        self.app.tap_control(controls_mod.UNDO_ID)
        self.assertEqual(self.app.model.look, Look("unicorn", "cream", "sunshine"))
        self.assertEqual(self.services.look, self.app.model.look)

    def test_sparkle_colour_retints_the_controls_live(self) -> None:
        self.app._on_tab(Tab.COLOURS)
        self.app.tap_control("accent.grape")
        self.assertEqual(self.app.kit.theme.accent, (148, 100, 201))

    def test_a_refused_save_keeps_the_old_look_and_thinks_gently(self) -> None:
        self.services.refuse = {ChoiceKind.SIZE}
        self.app._on_tab(Tab.SIZE)
        self.app.tap_control("size.large")
        self.assertEqual(self.app.model.look.size, "normal")
        self.assertEqual(self.app.last_feedback, "refused")
        self.assertFalse(self.app.model.can_undo)

    def test_cancel_returns_to_tabs_then_leaves(self) -> None:
        self.app.press(pygame.K_DOWN)
        self.assertTrue(self.app.controls.focus_in_tiles())
        self.app.press(pygame.K_ESCAPE)
        self.assertEqual(self.app.controls.layer.focused_id, controls_mod.tab_id(Tab.ME))
        self.assertTrue(self.app._running)
        self.app.press(pygame.K_ESCAPE)
        self.assertFalse(self.app._running)

    def test_protected_home_region_receives_no_activity_input(self) -> None:
        self.assertFalse(self.app.tap((20, 20)))
        self.assertEqual(self.services.applied, [])

    def test_controls_and_preview_stay_clear_of_protected_chrome_at_every_viewport(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            with self.subTest(size=size):
                app = self._make_app(size)
                layout = ControlLayout.for_canvas(app.canvas, size)
                rects = [target.rect for target in app.controls.layer.targets]
                rects.append(app.controls.geometry.preview)
                for tab in content.TABS:
                    app._on_tab(tab)
                    rects.extend(tile.rect for tile in app.controls.tiles)
                for rect in rects:
                    self.assertFalse(_overlaps(rect, layout.protected), (size, rect))
                    self.assertTrue(pygame.Rect(0, 0, 1024, 600).contains(rect), (size, rect))
                physical = ActivitySystemChromeLayout.for_surface(*size).protected_region
                self.assertGreater(physical.width, 0)

    def test_static_preview_is_composed_once_per_look(self) -> None:
        for _ in range(4):
            self.app.render()
        self.assertEqual(self.app.preview.build_count, 1)
        self.app.tap_control("avatar.owl")
        for _ in range(3):
            self.clock.now += 0.1
            self.app.step()
            self.app.render()
        self.assertEqual(self.app.preview.build_count, 2)

    def test_app_loop_makes_choices_and_leaves_cleanly(self) -> None:
        robot = self.app.controls.layer.target("avatar.robot").rect
        transform = self.app.canvas.mapper.transform
        position = tuple(int(v) for v in transform.logical_to_physical(robot.center))
        for event in (
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=position, button=1),
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=position, button=1),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0, unicode="\t"),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode=""),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0, unicode=""),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"),
            pygame.event.Event(pygame.QUIT),
        ):
            pygame.event.post(event)
        with mock.patch.object(app_mod, "mark_activity_ready") as ready:
            self.assertEqual(self.app.run(), 0)
        ready.assert_called_once()
        self.assertEqual(self.app.model.look.avatar, "robot")
        self.assertIs(self.app.model.tab, Tab.COLOURS)
        self.assertEqual(self.app.model.changes, 2)
        self.assertEqual(self.audio.events[0], "welcome")
        self.assertEqual(self.audio.events[-1], "stop")


class GreiaCustomizationTests(unittest.TestCase):
    """Real platform stores in a temporary customization directory."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        environment = {
            "GREIA_CUSTOMIZATION_DIR": self.temp.name,
            "GREIA_OS_ROOT": str(ROOT),
            "GREIA_PROFILE_ID": "child-1",
            "GREIA_PROFILE_AVATAR": "owl",
        }
        self.env = mock.patch.dict(os.environ, environment)
        self.env.start()
        for name in ("GREIA_ACTIVITY_CAPABILITIES", "GREIA_AVATAR_REQUEST_PATH"):
            os.environ.pop(name, None)
        self._clear_caches()
        self.storage = FakeStorage()
        self.service = services_mod.GreiaCustomization(self.storage)

    def tearDown(self) -> None:
        self.env.stop()
        self._clear_caches()
        self.temp.cleanup()

    @staticmethod
    def _clear_caches() -> None:
        for name in ("_root", "_catalogue", "_theme_store", "_ui_preferences_store"):
            getattr(activity_api, name).cache_clear()

    def test_load_reads_the_profile_look_and_cast_first_avatars(self) -> None:
        state = self.service.load()
        self.assertEqual(state.look.avatar, "owl")
        self.assertEqual(state.look.wallpaper, MEADOW)
        self.assertEqual(state.choices.avatars[:4], ("unicorn", "robot", "owl", "green_monster"))
        self.assertEqual(len(state.choices.backgrounds), 8)
        self.assertEqual(len(state.choices.accents), 8)

    def test_curated_picture_round_trips_through_the_managed_wallpaper(self) -> None:
        before = self.service.load().look
        after = before.with_value(ChoiceKind.WALLPAPER, "bg.wallpaper.castle")
        applied = self.service.apply(before, after)
        self.assertEqual(applied.wallpaper, "bg.wallpaper.castle")
        wallpaper = Path(self.temp.name) / "wallpaper.jpg"
        self.assertTrue(wallpaper.is_file())
        self.assertLessEqual(wallpaper.stat().st_size, WallpaperImporter.MAX_OUTPUT_BYTES)
        self.assertEqual(self.service.load().look.wallpaper, "bg.wallpaper.castle")
        # Choosing the meadow removes the managed picture again.
        self.service.apply(applied, applied.with_value(ChoiceKind.WALLPAPER, MEADOW))
        self.assertFalse(wallpaper.exists())
        self.assertEqual(self.service.load().look.wallpaper, MEADOW)

    def test_an_unknown_managed_picture_is_reported_as_custom(self) -> None:
        before = self.service.load().look
        self.service.apply(before, before.with_value(ChoiceKind.WALLPAPER, "bg.wallpaper.snow"))
        self.storage.kv.clear()
        state = self.service.load()
        self.assertEqual(state.look.wallpaper, CUSTOM)
        self.assertIsNotNone(state.custom_wallpaper)

    def test_colours_and_size_persist_in_the_platform_stores(self) -> None:
        before = self.service.load().look
        after = Look(before.avatar, "mint", "grape", before.wallpaper, "large")
        self.assertEqual(self.service.apply(before, after), after)
        theme = activity_api.get_theme()
        self.assertEqual(theme.preferences.background, "mint")
        self.assertEqual(theme.preferences.accent, "grape")
        self.assertEqual(activity_api.get_ui_preferences().interface_size.value, "large")

    def test_set_curated_wallpaper_only_accepts_wallpaper_visuals(self) -> None:
        with self.assertRaises(ValueError):
            activity_api.set_curated_wallpaper("bg.meadow_day.home")

    def test_curated_install_rejects_non_image_sources(self) -> None:
        store = ThemeStore.load(ROOT / "runtime" / "theme-defaults.toml", Path(self.temp.name))
        importer = WallpaperImporter(store, mock.Mock())
        with self.assertRaises(CustomizationError):
            importer.install_curated(ROOT / "runtime" / "theme-defaults.toml")


class MyGreiaSourcePolicyTests(unittest.TestCase):
    def test_child_flow_does_not_import_removable_media_wallpapers(self) -> None:
        for path in ACTIVITY.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for forbidden in ("list_wallpaper_candidates", "import_wallpaper", "RemovableImageScanner"):
                self.assertNotIn(forbidden, text, f"{path.name} uses {forbidden}")

    def test_main_keeps_the_historical_entry_names(self) -> None:
        self.assertIs(main_mod.MyGreiaSettings, app_mod.MyGreiaApp)
        self.assertTrue(callable(main_mod.main))


if __name__ == "__main__":
    unittest.main()

"""First-boot profile setup wizard: store marker, model, input, voice, rendering.

The wizard appears only while the profile registry holds the untouched
placeholder of a brand-new device, creates exactly one child profile through
``ProfileStore.complete_first_profile`` and lands on Home with it. These tests
cover the platform marker, the renderer-free model, keyboard/pointer/
controller navigation, silent voice fallback, rendering at 1024x600 and
800x480 in all four languages and one real headless ``GreiaChildShell`` path.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = tempfile.mkdtemp(prefix="greia-first-profile-")
os.environ["GREIA_PROFILES_DIR"] = os.path.join(TMP_DIR, "profiles")
os.environ["GREIA_SYSTEM_SETTINGS_DIR"] = os.path.join(TMP_DIR, "settings")
os.environ["GREIA_MEDIA_ROOT"] = os.path.join(TMP_DIR, "media")
os.environ["GREIA_ACTIVE_PROFILE_STATUS"] = os.path.join(TMP_DIR, "active-profile.json")
os.environ["GREIA_HARDWARE_STATUS"] = os.path.join(TMP_DIR, "hardware-status.json")
os.environ["GREIA_MAIN_CREDENTIAL_PATH"] = os.path.join(TMP_DIR, "parent-credential.json")
os.environ["GREIA_OS_ROOT"] = str(REPO_ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from greia_launcher.first_profile_copy import (
    FIRST_PROFILE_AUDIO_ROOT,
    FIRST_PROFILE_CUES,
    FIRST_PROFILE_LOCALES,
    copy_locale,
    first_profile_clip,
    first_profile_copy,
)
from greia_launcher.first_profile_presentation import (
    FIRST_PROFILE_MODE,
    ShellFirstProfileVoice,
)
from greia_launcher.first_profile_screen import FirstProfileScreen
from greia_launcher.first_profile_wizard import (
    STEP_CUES,
    FirstProfileStep,
    FirstProfileWizard,
    SilentVoice,
    normalize_display_name,
)
from greia_platform.input_core import SemanticAction
from greia_platform.profiles import (
    FIRST_PROFILE_SETUP_KEY,
    ProfileError,
    ProfilePolicy,
    ProfileStore,
)
from greia_platform.ui_core import UiEventResult

import hermetic_volume

VIEWPORTS = ((1024, 600), (800, 480))
VOICE_DOC = (
    REPO_ROOT
    / "docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/VOICE_LINES_FIRST_BOOT_WIZARD.md"
)


def setUpModule() -> None:
    hermetic_volume.install_for_module()
    pygame.init()


def tearDownModule() -> None:
    shutil.rmtree(TMP_DIR, ignore_errors=True)


def _policy() -> ProfilePolicy:
    return ProfilePolicy.load(REPO_ROOT / "runtime" / "profile-defaults.toml")


def _store(root: Path) -> ProfileStore:
    return ProfileStore(_policy(), root)


class _RecordingCommit:
    def __init__(self, store: ProfileStore) -> None:
        self.store = store
        self.calls: list[tuple[str, str, int | None]] = []

    def __call__(self, name: str, avatar: str, age: int | None):
        self.calls.append((name, avatar, age))
        return self.store.complete_first_profile(name, avatar, approximate_age=age)


# ---------------------------------------------------------------- store marker
class FirstProfileStoreMarkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(dir=TMP_DIR))
        self.store = _store(self.root)

    def test_placeholder_on_empty_registry_is_pending(self) -> None:
        (placeholder,) = self.store.ensure_initialized()
        raw = json.loads(self.store.registry_path.read_text(encoding="utf-8"))
        self.assertEqual(raw[FIRST_PROFILE_SETUP_KEY], placeholder.profile_id)
        self.assertEqual(self.store.first_profile_setup(), placeholder)
        # A second boot (Shell or Parent service) keeps it pending.
        self.store.ensure_initialized()
        self.assertEqual(self.store.first_profile_setup(), placeholder)

    def test_complete_replaces_placeholder_and_clears_marker(self) -> None:
        (placeholder,) = self.store.ensure_initialized()
        created = self.store.complete_first_profile("Anna", "owl", approximate_age=5)
        self.assertEqual(created.profile_id, placeholder.profile_id)
        self.assertEqual(
            (created.display_name, created.avatar_id, created.approximate_age),
            ("Anna", "owl", 5),
        )
        self.assertEqual(self.store.list_profiles(), (created,))
        self.assertIsNone(self.store.first_profile_setup())
        raw = json.loads(self.store.registry_path.read_text(encoding="utf-8"))
        self.assertNotIn(FIRST_PROFILE_SETUP_KEY, raw)
        with self.assertRaises(ProfileError):
            self.store.complete_first_profile("Bea", "owl")

    def test_complete_validates_through_profile_policy(self) -> None:
        self.store.ensure_initialized()
        with self.assertRaises(ProfileError):
            self.store.complete_first_profile("", "owl")
        with self.assertRaises(ProfileError):
            self.store.complete_first_profile("Anna", "not-an-avatar")
        with self.assertRaises(ProfileError):
            self.store.complete_first_profile("Anna", "owl", approximate_age=40)
        self.assertIsNotNone(self.store.first_profile_setup())

    def test_any_parent_mutation_ends_setup(self) -> None:
        (placeholder,) = self.store.ensure_initialized()
        self.store.update(placeholder.profile_id, display_name="Luca")
        self.assertIsNone(self.store.first_profile_setup())

        other = _store(Path(tempfile.mkdtemp(dir=TMP_DIR)))
        other.ensure_initialized()
        other.create("Bea", "robot")
        self.assertIsNone(other.first_profile_setup())
        with self.assertRaises(ProfileError):
            other.complete_first_profile("Anna", "owl")

    def test_existing_devices_without_marker_never_run_setup(self) -> None:
        self.store.create("Mia", "unicorn")
        self.assertEqual(len(self.store.ensure_initialized()), 1)
        self.assertIsNone(self.store.first_profile_setup())


# ---------------------------------------------------------------- wizard model
class FirstProfileWizardModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.voice = SilentVoice()
        self.wizard = FirstProfileWizard(_policy(), voice=self.voice)

    def test_steps_speak_their_cues_in_order(self) -> None:
        wizard = self.wizard
        wizard.start()
        wizard.start()  # idempotent: the welcome line plays once
        self.assertTrue(wizard.next())
        self.assertFalse(wizard.next())  # no name yet
        wizard.type_text("anna")
        self.assertTrue(wizard.next())
        self.assertTrue(wizard.next())
        wizard.select_age(6)
        self.assertTrue(wizard.next())
        self.assertIs(wizard.step, FirstProfileStep.CHECK)
        self.assertFalse(wizard.next())  # saving needs confirm()
        self.assertEqual(
            self.voice.spoken,
            [
                "first_boot.welcome",
                "first_boot.ask_name",
                "first_boot.name_empty",
                "first_boot.ask_avatar",
                "first_boot.ask_age",
                "first_boot.check",
            ],
        )
        self.assertTrue(wizard.back())
        self.assertIs(wizard.step, FirstProfileStep.AGE)

    def test_name_rules_follow_profile_policy(self) -> None:
        wizard = self.wizard
        self.assertFalse(wizard.name_valid())
        self.assertFalse(wizard.type_text("  "))  # no leading separator
        self.assertFalse(wizard.type_text("7!@"))  # digits/symbols refused
        wizard.type_text("anna  maria")
        self.assertEqual(wizard.display_name, "Anna Maria")
        self.assertTrue(wizard.name_valid())
        wizard.type_text("x" * 100)
        self.assertEqual(len(wizard.name), _policy().max_name_characters)
        while wizard.backspace():
            pass
        self.assertEqual(wizard.name, "")
        self.assertFalse(wizard.backspace())

    def test_name_normalization(self) -> None:
        self.assertEqual(normalize_display_name("ANNA"), "Anna")
        self.assertEqual(normalize_display_name("jean-luc"), "Jean-Luc")
        self.assertEqual(normalize_display_name("McKenzie"), "McKenzie")
        self.assertEqual(normalize_display_name("NICOLÒ"), "Nicolò")
        self.assertEqual(normalize_display_name("  zoé   rose "), "Zoé Rose")

    def test_avatar_and_age_choices_are_bounded(self) -> None:
        wizard = self.wizard
        self.assertEqual(wizard.avatars, _policy().avatars)
        self.assertEqual(wizard.avatar_id, _policy().default_avatar)
        self.assertFalse(wizard.select_avatar("dragon-not-in-policy"))
        self.assertTrue(wizard.select_avatar("robot"))
        self.assertFalse(wizard.select_age(42))
        self.assertTrue(wizard.select_age(4))
        wizard.step = FirstProfileStep.AGE
        wizard.skip_age()
        self.assertIsNone(wizard.approximate_age)
        self.assertIs(wizard.step, FirstProfileStep.CHECK)

    def test_confirm_creates_exactly_one_profile(self) -> None:
        store = _store(Path(tempfile.mkdtemp(dir=TMP_DIR)))
        store.ensure_initialized()
        commit = _RecordingCommit(store)
        wizard = self.wizard
        wizard.type_text("ANNA")
        wizard.select_avatar("owl")
        wizard.select_age(5)
        wizard.step = FirstProfileStep.CHECK
        profile = wizard.confirm(commit)
        self.assertEqual(commit.calls, [("Anna", "owl", 5)])
        self.assertIs(wizard.step, FirstProfileStep.CELEBRATE)
        self.assertEqual(store.list_profiles(), (profile,))
        self.assertIsNone(wizard.confirm(commit))  # no second commit
        self.assertEqual(len(commit.calls), 1)
        self.assertEqual(self.voice.spoken[-1], "first_boot.celebrate")

    def test_refused_commit_stays_and_speaks_try_again(self) -> None:
        wizard = self.wizard
        wizard.type_text("Anna")
        wizard.step = FirstProfileStep.CHECK

        def refuse(*_args):
            raise ProfileError("first-profile setup is no longer pending")

        self.assertIsNone(wizard.confirm(refuse))
        self.assertIs(wizard.step, FirstProfileStep.CHECK)
        self.assertTrue(wizard.commit_failed)
        self.assertEqual(self.voice.spoken[-1], "first_boot.try_again")

    def test_failing_voice_never_breaks_the_wizard(self) -> None:
        class Broken:
            def say(self, cue_id: str) -> bool:
                raise RuntimeError("mixer gone")

        wizard = FirstProfileWizard(_policy(), voice=Broken())
        wizard.start()
        self.assertTrue(wizard.next())
        self.assertFalse(wizard.replay())


# ---------------------------------------------------------------- copy + voice
class FirstProfileCopyAndVoiceTests(unittest.TestCase):
    def test_copy_exists_for_four_languages_with_fallback(self) -> None:
        self.assertEqual(FIRST_PROFILE_LOCALES, ("en", "it", "es", "fr"))
        for locale in FIRST_PROFILE_LOCALES:
            copy = first_profile_copy(locale)
            for field in ("welcome", "ask_name", "ask_avatar", "ask_age", "check", "celebrate", "skip"):
                self.assertTrue(getattr(copy, field).strip(), (locale, field))
        self.assertEqual(copy_locale("it-IT"), "it")
        self.assertEqual(copy_locale("es_ES"), "es")
        self.assertEqual(copy_locale("de"), "en")
        self.assertEqual(copy_locale(None), "en")
        self.assertIn("Ñ", first_profile_copy("es").extra_letters)

    def test_every_cue_is_wired_and_scripted_in_four_languages(self) -> None:
        wired = set(STEP_CUES.values()) | {"first_boot.name_empty", "first_boot.try_again"}
        self.assertEqual(wired, set(FIRST_PROFILE_CUES))
        document = VOICE_DOC.read_text(encoding="utf-8")
        for cue in FIRST_PROFILE_CUES:
            rows = [line for line in document.splitlines() if line.startswith(f"| `{cue}` |")]
            self.assertEqual(len(rows), 1, cue)
            cells = [cell.strip() for cell in rows[0].strip("|").split("|")]
            self.assertEqual(len(cells), 6, cue)  # id, trigger, EN, IT, ES, FR
            self.assertTrue(all(cells[2:]), cue)
        self.assertIn(str(FIRST_PROFILE_AUDIO_ROOT), document)

    def test_missing_audio_resolves_to_silence(self) -> None:
        root = Path(tempfile.mkdtemp(dir=TMP_DIR))
        for cue in FIRST_PROFILE_CUES:
            for locale in FIRST_PROFILE_LOCALES:
                self.assertIsNone(first_profile_clip(root, cue, locale))
        with self.assertRaises(ValueError):
            first_profile_clip(root, "first_boot.unknown", "en")

    def test_audio_fallback_order_locale_base_english(self) -> None:
        root = Path(tempfile.mkdtemp(dir=TMP_DIR))
        folder = root / FIRST_PROFILE_AUDIO_ROOT
        for locale in ("en", "it"):
            (folder / locale).mkdir(parents=True)
            (folder / locale / "welcome.wav").write_bytes(b"RIFF")
        self.assertEqual(first_profile_clip(root, "first_boot.welcome", "it-IT").parent.name, "it")
        self.assertEqual(first_profile_clip(root, "first_boot.welcome", "fr").parent.name, "en")
        self.assertIsNone(first_profile_clip(root, "first_boot.check", "fr"))

    def test_shell_voice_uses_single_player_and_allows_replay(self) -> None:
        root = Path(tempfile.mkdtemp(dir=TMP_DIR))
        (root / FIRST_PROFILE_AUDIO_ROOT / "en").mkdir(parents=True)
        (root / FIRST_PROFILE_AUDIO_ROOT / "en" / "welcome.wav").write_bytes(b"RIFF")

        class Player:
            def __init__(self) -> None:
                self.calls: list[tuple[str, Path]] = []

            def announce(self, identity, clip, _pygame):
                self.calls.append((identity, clip))
                return True

            def is_busy(self) -> bool:
                return False

        player = Player()
        voice = ShellFirstProfileVoice(root, player, "fr", pygame)
        self.assertTrue(voice.say("first_boot.welcome"))
        self.assertTrue(voice.say("first_boot.welcome"))
        self.assertFalse(voice.say("first_boot.check"))  # no clip: silent
        self.assertFalse(ShellFirstProfileVoice(root, None, "en", pygame).say("first_boot.welcome"))
        self.assertEqual(len(player.calls), 2)
        self.assertNotEqual(player.calls[0][0], player.calls[1][0])
        self.assertFalse(voice.busy())


# ---------------------------------------------------------------- screen
def _visuals():
    from greia_launcher.visual_assets import load_launcher_assets
    from greia_platform.pygame_visual_assets import PygameVisualSurfaceCache

    assets = load_launcher_assets(
        REPO_ROOT / "assets/catalog/core_icons_v1.toml",
        REPO_ROOT / "assets/catalog/shared_visuals_v1.toml",
    )
    cache = PygameVisualSurfaceCache.for_pygame(assets.catalogue, max_entries=32)
    catalogue = assets.catalogue

    def resolver(asset_id: str, variant: str) -> Path:
        return catalogue.get_visual(asset_id).path_for(variant)

    def pose(name: str, size: int):
        return cache.get("character.leo", variant=name, size=(size, size))

    return resolver, pose


class FirstProfileScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from greia_platform.typography import GreiaTypography

        cls.typography = GreiaTypography(REPO_ROOT / "assets/fonts/nunito-sans")
        cls.resolver, cls.pose = _visuals()

    def _screen(self, locale: str, size: tuple[int, int], store: ProfileStore | None = None):
        surface = pygame.display.set_mode(size)
        voice = SilentVoice()
        wizard = FirstProfileWizard(_policy(), voice=voice)
        if store is None:
            store = _store(Path(tempfile.mkdtemp(dir=TMP_DIR)))
            store.ensure_initialized()
        screen = FirstProfileScreen(
            wizard,
            typography=self.typography,
            commit=_RecordingCommit(store),
            locale=locale,
            pose=self.pose,
            visual_resolver=self.resolver,
        )
        screen.on_enter()
        return surface, screen, wizard, voice

    def _assert_layout_sane(self, surface, screen, label) -> None:
        bounds = surface.get_rect()
        rects = {cid: screen.control_rect(cid) for cid in screen.control_ids()}
        for cid, rect in rects.items():
            self.assertTrue(bounds.contains(rect), (label, cid, rect))
            self.assertGreaterEqual(min(rect.size), 28, (label, cid))
        items = list(rects.items())
        for index, (first, a) in enumerate(items):
            for second, b in items[index + 1:]:
                self.assertFalse(a.colliderect(b), (label, first, second))
        field = screen._geometry.get("field")
        if field is not None:
            self.assertTrue(bounds.contains(field), label)
            for cid, rect in rects.items():
                self.assertFalse(field.colliderect(rect), (label, "field", cid))

    def test_every_step_renders_in_four_languages_at_reference_sizes(self) -> None:
        for size in VIEWPORTS:
            for locale in FIRST_PROFILE_LOCALES:
                surface, screen, wizard, _voice = self._screen(locale, size)
                with self.subTest(size=size, locale=locale):
                    for step in FirstProfileStep:
                        if step is FirstProfileStep.CELEBRATE:
                            wizard.type_text("Anna")
                            wizard.step = FirstProfileStep.CHECK
                            screen.draw(surface)
                            screen.activate("next")
                        else:
                            wizard.step = step
                        surface.fill((0, 0, 0))
                        screen.draw(surface)
                        self.assertFalse(screen.error, (size, locale, step))
                        self._assert_layout_sane(surface, screen, (size, locale, step.value))
                        # Opaque full-frame composition: no black left behind.
                        self.assertNotEqual(surface.get_at((size[0] // 2, size[1] - 3))[:3], (0, 0, 0))
                    self.assertIs(wizard.step, FirstProfileStep.CELEBRATE)
                    screen.on_exit()

    def test_keyboard_navigation_and_typing(self) -> None:
        surface, screen, wizard, voice = self._screen("it", (1024, 600))
        screen.draw(surface)
        self.assertEqual(screen.key(pygame.K_RETURN), UiEventResult.HANDLED)
        screen.draw(surface)
        self.assertIs(wizard.step, FirstProfileStep.NAME)
        self.assertTrue(screen.wants_text_input)
        # Arrow keys reveal focus on "A", move right to "B", Enter types it.
        screen.key(pygame.K_RIGHT)
        self.assertTrue(screen.layer.focus_visible)
        self.assertEqual(screen.layer.focused_id, "key:B")
        screen.key(pygame.K_RETURN)
        self.assertEqual(wizard.name, "B")
        # Physical typing (TEXTINPUT) hides focus; Space then types a space.
        self.assertTrue(screen.text("ea"))
        self.assertFalse(screen.layer.focus_visible)
        screen.key(pygame.K_SPACE)
        self.assertTrue(screen.text(" "))
        screen.text("Rè")
        self.assertEqual(wizard.display_name, "Bea Rè")
        screen.key(pygame.K_BACKSPACE)
        screen.key(pygame.K_BACKSPACE)
        screen.key(pygame.K_BACKSPACE)
        self.assertEqual(wizard.display_name, "Bea")
        screen.key(pygame.K_RETURN)  # focus hidden: Enter means "next"
        self.assertIs(wizard.step, FirstProfileStep.AVATAR)
        self.assertFalse(screen.wants_text_input)
        screen.key(pygame.K_ESCAPE)
        self.assertIs(wizard.step, FirstProfileStep.NAME)

    def test_pointer_clicks_drive_the_whole_flow(self) -> None:
        store = _store(Path(tempfile.mkdtemp(dir=TMP_DIR)))
        store.ensure_initialized()
        surface, screen, wizard, _voice = self._screen("en", (800, 480), store)

        def tap(control_id: str) -> UiEventResult:
            screen.draw(surface)
            return screen.click(screen.control_rect(control_id).center)

        tap("next")
        for letter in "LEO":
            tap(f"key:{letter}")
        self.assertEqual(wizard.display_name, "Leo")
        tap("next")
        tap("avatar:robot")
        tap("next")
        tap("age:7")
        tap("next")
        self.assertIs(wizard.step, FirstProfileStep.CHECK)
        self.assertEqual(store.list_profiles()[0].display_name, "Explorer")
        tap("next")
        self.assertIs(wizard.step, FirstProfileStep.CELEBRATE)
        (profile,) = store.list_profiles()
        self.assertEqual((profile.display_name, profile.avatar_id, profile.approximate_age), ("Leo", "robot", 7))
        self.assertIsNone(store.first_profile_setup())
        # Hover only changes control state, never the wizard.
        screen.pointer_move((5, 5))
        self.assertTrue(screen.needs_frame(screen._clock() + 1.0))

    def test_celebration_is_bounded_and_skippable(self) -> None:
        surface, screen, wizard, _voice = self._screen("fr", (1024, 600))
        clock = [100.0]
        screen._clock = lambda: clock[0]
        wizard.type_text("Zoé")
        wizard.step = FirstProfileStep.CHECK
        screen.draw(surface)
        screen.activate("next")
        self.assertIs(wizard.step, FirstProfileStep.CELEBRATE)
        self.assertEqual(screen.click((10, 10)), UiEventResult.HANDLED)  # too early
        self.assertFalse(screen.celebration_done())
        clock[0] += screen.CELEBRATE_MIN_SECONDS + 0.1
        self.assertTrue(screen.celebration_done())
        screen._voice_busy = lambda: True
        self.assertFalse(screen.celebration_done())
        clock[0] += screen.CELEBRATE_MAX_SECONDS
        self.assertTrue(screen.celebration_done())
        self.assertEqual(screen.key(pygame.K_SPACE), UiEventResult.REQUEST_CLOSE)
        screen.on_exit()
        self.assertFalse(screen.needs_frame())


# ---------------------------------------------------------------- real Shell
class FirstProfileShellIntegrationTests(unittest.TestCase):
    """One real headless GreiaChildShell per scenario (each boot costs ~5 s)."""

    def _boot(self, profiles_dir: Path):
        from greia_launcher.child_shell import GreiaChildShell

        os.environ["GREIA_PROFILES_DIR"] = str(profiles_dir)
        os.environ["GREIA_ACTIVE_PROFILE_STATUS"] = str(profiles_dir.parent / "active.json")
        os.environ["GREIA_DEVICE_LOCALE"] = "it"
        self.addCleanup(os.environ.pop, "GREIA_DEVICE_LOCALE", None)
        surface = pygame.display.set_mode((1024, 600))
        return surface, GreiaChildShell(windowed=True)

    def test_brand_new_device_runs_setup_once_and_lands_on_home(self) -> None:
        profiles_dir = Path(tempfile.mkdtemp(dir=TMP_DIR)) / "profiles"
        surface, shell = self._boot(profiles_dir)
        self.assertEqual(shell._mode, FIRST_PROFILE_MODE)
        shell._draw(surface, pygame)
        view = shell._first_profile_screen
        self.assertEqual(view.copy, first_profile_copy("it"))
        # Controller path: semantic actions arrive as Shell key handling.
        shell._handle_semantic_action(SemanticAction.ACTIVATE, pygame)
        shell._draw(surface, pygame)
        self.assertIs(view.wizard.step, FirstProfileStep.NAME)
        shell._handle_semantic_action(SemanticAction.NAV_DOWN, pygame)
        self.assertEqual(view.layer.focused_id, "key:I")
        shell._handle_semantic_action(SemanticAction.ACTIVATE, pygame)
        self.assertTrue(shell._handle_shell_text_input("da"))
        self.assertEqual(view.wizard.display_name, "Ida")
        for _ in range(3):  # name -> avatar -> age -> check (age skipped by Next)
            shell._handle_key(pygame.K_RETURN, pygame)
            shell._draw(surface, pygame)
        self.assertIs(view.wizard.step, FirstProfileStep.CHECK)
        shell._handle_key(pygame.K_RETURN, pygame)
        self.assertIs(view.wizard.step, FirstProfileStep.CELEBRATE)
        view._celebrate_started -= 30
        self.assertTrue(shell._present_ambient_frame(surface, pygame, view._clock()))
        self.assertEqual(shell._mode, "activities")
        self.assertEqual(shell._active_profile.profile.display_name, "Ida")
        registry = ProfileStore(_policy(), profiles_dir)
        self.assertEqual(len(registry.list_profiles()), 1)
        self.assertIsNone(registry.first_profile_setup())
        # The next boot shows the ordinary picker (no silent resume).
        _surface, again = self._boot(profiles_dir)
        self.assertEqual(again._mode, "profiles")

    def test_parent_created_child_ends_setup_and_existing_devices_skip_it(self) -> None:
        profiles_dir = Path(tempfile.mkdtemp(dir=TMP_DIR)) / "profiles"
        surface, shell = self._boot(profiles_dir)
        self.assertEqual(shell._mode, FIRST_PROFILE_MODE)
        shell._draw(surface, pygame)
        # A Parent adds a child from the Parent service meanwhile.
        ProfileStore(_policy(), profiles_dir).create("Sara", "owl")
        shell._rescan_profiles()
        self.assertEqual(shell._mode, "profiles")
        self.assertIsNone(shell._first_profile_screen)
        shell._draw(surface, pygame)
        self.assertEqual(len(shell.profiles), 2)

        existing = Path(tempfile.mkdtemp(dir=TMP_DIR)) / "profiles"
        ProfileStore(_policy(), existing).create("Mia", "robot")
        _surface, picker = self._boot(existing)
        self.assertEqual(picker._mode, "profiles")


class FirstProfileSourceContractTests(unittest.TestCase):
    def test_wizard_writes_only_through_the_profile_store(self) -> None:
        for name in ("first_profile_wizard.py", "first_profile_screen.py", "first_profile_presentation.py"):
            source = (REPO_ROOT / "src/greia_launcher" / name).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"profiles\.json|open\(|write_text|_write_unlocked", source), name)


if __name__ == "__main__":
    unittest.main()

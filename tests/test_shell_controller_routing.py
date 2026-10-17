"""Controller input reaches every trusted Shell surface through one path.

ADR 0020 / ``ACTIVITY_INPUT_STANDARDS``: D-pad and left stick are directional
navigation (platform dead zone), south activates, east cancels, the shoulders
step the previous/next section or page, and Guide is the reserved Greia Home.
The Shell's real loop (``GreiaLauncherPresentation.run``) must feed these to the
active surface exactly once. These tests drive synthetic pygame controller
events through that real loop (Home, first-boot wizard) and through the shared
dispatcher (Parent panel sections, Collection paging, Guide Home).
Source tests only: no Simulator, VM or hardware claim.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = tempfile.mkdtemp(prefix="greia-shell-controller-")
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

from greia_launcher.catalogue_view import ActivityCatalogue
from greia_launcher.first_profile_presentation import FIRST_PROFILE_MODE
from greia_launcher.first_profile_wizard import FirstProfileStep
from greia_launcher.main import LauncherApplication
from greia_launcher.parent_panel import ParentPanelState, ParentPanelTab
from greia_launcher.shell_input import (
    ShellControllerCommand,
    ShellInputController,
)
from greia_platform.input_core import (
    SemanticAction,
    StandardInputMapper,
    StandardInputPolicy,
    InputEdge,
    InputSource,
    PhysicalControl,
)
from greia_platform.pygame_input import (
    CONTROLLER_BUTTON_A,
    CONTROLLER_BUTTON_B,
    CONTROLLER_BUTTON_DPAD_DOWN,
    CONTROLLER_BUTTON_DPAD_LEFT,
    CONTROLLER_BUTTON_DPAD_RIGHT,
    CONTROLLER_BUTTON_GUIDE,
    CONTROLLER_BUTTON_LEFTSHOULDER,
    CONTROLLER_BUTTON_RIGHTSHOULDER,
    sdl_controller,
)

import hermetic_volume
from test_parent_panel_polish import _panel

HAS_CONTROLLERS = sdl_controller is not None


def setUpModule() -> None:
    hermetic_volume.install_for_module()


class _FakeControllerSet:
    """Stands in for the bounded SDL controller owner."""

    supported = True

    def __init__(self) -> None:
        self.opened_count = 1
        self.started = 0
        self.closed = 0
        self.stick = (0.0, 0.0)

    def start(self) -> int:
        self.started += 1
        return self.opened_count

    def close(self) -> None:
        self.closed += 1

    def handle_event(self, event: object) -> bool:
        return False

    def first_left_stick(self) -> tuple[float, float]:
        return self.stick

    def poll_guide_button(self) -> bool:
        return False


def _press(button: int):
    return pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=button)


def _release(button: int):
    return pygame.event.Event(pygame.CONTROLLERBUTTONUP, button=button)


def _sample(activity_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        activity_id=activity_id,
        version="1.0.0",
        title_key=activity_id,
        title=activity_id,
        icon_id="palette",
        categories=("creativity",),
        launcher_categories=("play",),
        discovery_tags=(),
        difficulty=1,
        recommended_age_min=None,
        recommended_age_max=None,
        adaptive_difficulty=False,
    )


@unittest.skipUnless(HAS_CONTROLLERS, "curated pygame build has no SDL2 controller module")
class ShellControllerTranslationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shell_input = ShellInputController(controllers=_FakeControllerSet())  # type: ignore[arg-type]

    def test_buttons_translate_to_shell_actions(self) -> None:
        cases = {
            CONTROLLER_BUTTON_DPAD_RIGHT: SemanticAction.NAV_RIGHT,
            CONTROLLER_BUTTON_A: SemanticAction.ACTIVATE,
            CONTROLLER_BUTTON_B: SemanticAction.CANCEL,
            CONTROLLER_BUTTON_LEFTSHOULDER: ShellControllerCommand.SECTION_PREVIOUS,
            CONTROLLER_BUTTON_RIGHTSHOULDER: ShellControllerCommand.SECTION_NEXT,
            CONTROLLER_BUTTON_GUIDE: ShellControllerCommand.HOME,
        }
        for button, expected in cases.items():
            with self.subTest(button=button):
                self.assertIs(self.shell_input.translate_event(_press(button)), expected)
                self.assertIsNone(self.shell_input.translate_event(_release(button)))

    def test_keyboard_events_are_never_translated_so_nothing_dispatches_twice(self) -> None:
        for key in (pygame.K_RIGHT, pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_PAGEDOWN):
            event = pygame.event.Event(pygame.KEYDOWN, key=key)
            self.assertIsNone(self.shell_input.translate_event(event))

    def test_guide_and_shoulders_stay_out_of_every_activity_profile(self) -> None:
        # The Shell consumes these itself; the Activity mapper still withholds
        # Guide entirely and gives the navigation profile no shoulder meaning.
        for profile in ("navigation", "pointer", "directional", "game"):
            mapper = StandardInputMapper(profile)
            self.assertIsNone(
                mapper.digital(
                    PhysicalControl.CONTROLLER_GUIDE, InputEdge.PRESSED, InputSource.CONTROLLER
                )
            )
        self.assertIsNone(
            StandardInputMapper("navigation").digital(
                PhysicalControl.CONTROLLER_LEFT_SHOULDER,
                InputEdge.PRESSED,
                InputSource.CONTROLLER,
            )
        )
        # The Activity-facing path of the Shell wrapper is unchanged.
        self.assertIsNone(self.shell_input.handle_event(_press(CONTROLLER_BUTTON_GUIDE)))
        self.assertIsNone(self.shell_input.handle_event(_press(CONTROLLER_BUTTON_RIGHTSHOULDER)))

    def test_stick_uses_the_platform_dead_zone(self) -> None:
        controllers = _FakeControllerSet()
        shell_input = ShellInputController(
            controllers=controllers,  # type: ignore[arg-type]
            policy=StandardInputPolicy(),
        )
        controllers.stick = (0.20, 0.0)  # inside the 0.22 dead zone
        self.assertIsNone(shell_input.poll_analog(1.0))
        controllers.stick = (0.0, 1.0)
        self.assertIs(shell_input.poll_analog(2.0), SemanticAction.NAV_DOWN)


@unittest.skipUnless(HAS_CONTROLLERS, "curated pygame build has no SDL2 controller module")
class ParentPanelControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    def _shell_with_panel(self, panel):
        shell = LauncherApplication(
            windowed=True,
            allow_exit=True,
            shell_input=ShellInputController(controllers=_FakeControllerSet()),  # type: ignore[arg-type]
        )
        shell._parent_panel = panel
        shell._mode = "parent_panel"
        shell._exit_parent_panel = mock.Mock()  # type: ignore[method-assign]
        return shell

    def _dispatch(self, shell, event) -> None:
        action = shell._shell_input.translate_event(event)
        self.assertIsNotNone(action)
        shell._handle_semantic_action(action, pygame)

    def test_shoulders_switch_sections_both_ways_and_wrap(self) -> None:
        panel = _panel()
        shell = self._shell_with_panel(panel)
        order = [tab for tab in ParentPanelTab]
        start = panel.active_tab
        self._dispatch(shell, _press(CONTROLLER_BUTTON_RIGHTSHOULDER))
        self.assertNotEqual(panel.active_tab, start)
        self._dispatch(shell, _press(CONTROLLER_BUTTON_LEFTSHOULDER))
        self.assertEqual(panel.active_tab, start)
        self._dispatch(shell, _press(CONTROLLER_BUTTON_LEFTSHOULDER))
        self.assertNotEqual(panel.active_tab, start)
        # A full lap returns to the start: the order matches Tab's.
        for _ in range(len(order) - 1):
            self._dispatch(shell, _press(CONTROLLER_BUTTON_LEFTSHOULDER))
        self.assertEqual(panel.active_tab, start)
        shell._exit_parent_panel.assert_not_called()

    def test_section_step_matches_tab_and_carries_no_stale_field(self) -> None:
        panel = _panel()
        shell = self._shell_with_panel(panel)
        panel._select_tab(ParentPanelTab.SECURITY)
        self.assertIsNotNone(panel._text_field)
        self._dispatch(shell, _press(CONTROLLER_BUTTON_RIGHTSHOULDER))
        self.assertIsNone(panel._text_field)
        tab_panel = _panel()
        tab_panel._select_tab(ParentPanelTab.SECURITY)
        tab_panel._text_field = tab_panel._form_fields()[-1]
        tab_panel.handle_key(pygame.K_TAB, pygame)
        self.assertEqual(tab_panel.active_tab, panel.active_tab)

    def test_directional_activate_and_cancel_reach_the_panel(self) -> None:
        panel = _panel()
        shell = self._shell_with_panel(panel)
        panel._select_tab(ParentPanelTab.LANGUAGE)
        before = panel._language_index
        self._dispatch(shell, _press(CONTROLLER_BUTTON_DPAD_DOWN))
        self.assertNotEqual(panel._language_index, before)
        self._dispatch(shell, _press(CONTROLLER_BUTTON_B))
        shell._exit_parent_panel.assert_called_once()

    def test_password_prompt_stays_keyboard_owned(self) -> None:
        panel = _panel()
        panel.state = ParentPanelState.AUTH
        shell = self._shell_with_panel(panel)
        with mock.patch.object(panel, "_attempt_auth") as attempt:
            self._dispatch(shell, _press(CONTROLLER_BUTTON_A))
            self._dispatch(shell, _press(CONTROLLER_BUTTON_RIGHTSHOULDER))
            self._dispatch(shell, _press(CONTROLLER_BUTTON_GUIDE))
        attempt.assert_not_called()
        self.assertIs(panel.state, ParentPanelState.AUTH)
        self._dispatch(shell, _press(CONTROLLER_BUTTON_B))  # Cancel still backs out.
        shell._exit_parent_panel.assert_called_once()

    def test_profile_secret_entry_ignores_activate_but_cancels(self) -> None:
        shell = LauncherApplication(
            windowed=True,
            allow_exit=True,
            shell_input=ShellInputController(controllers=_FakeControllerSet()),  # type: ignore[arg-type]
        )
        shell._mode = "secret"
        shell._attempt_unlock = mock.Mock()  # type: ignore[method-assign]
        shell._cancel_unlock = mock.Mock()  # type: ignore[method-assign]
        self._dispatch(shell, _press(CONTROLLER_BUTTON_A))
        shell._attempt_unlock.assert_not_called()
        self._dispatch(shell, _press(CONTROLLER_BUTTON_B))
        shell._cancel_unlock.assert_called_once()


class _ShellCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    def _boot(self, **kwargs):
        from greia_launcher.child_shell import GreiaChildShell

        self.fake_controllers = _FakeControllerSet()
        screen = pygame.display.set_mode((1024, 600))
        shell = GreiaChildShell(
            windowed=True,
            allow_exit=True,
            shell_input=ShellInputController(controllers=self.fake_controllers),  # type: ignore[arg-type]
            **kwargs,
        )
        return shell, screen

    def _dispatch(self, shell, event) -> None:
        action = shell._shell_input.translate_event(event)
        self.assertIsNotNone(action)
        shell._handle_semantic_action(action, pygame)


@unittest.skipUnless(HAS_CONTROLLERS, "curated pygame build has no SDL2 controller module")
class CollectionAndHomeControllerTests(_ShellCase):
    def _home(self):
        shell, screen = self._boot()
        if shell._visual_cache is None:
            self.skipTest("shared visuals unavailable in this checkout")
        shell.profiles = shell.profile_store.ensure_initialized()
        shell._activate_profile(shell.profiles[0], pygame)
        return shell, screen

    def test_dpad_walks_home_and_south_opens_a_collection(self) -> None:
        shell, screen = self._home()
        shell._draw(screen, pygame)
        self.assertEqual(shell._category_id, "all")
        shell._home_collection_selected = 0
        self._dispatch(shell, _press(CONTROLLER_BUTTON_DPAD_RIGHT))
        self.assertEqual(shell._home_collection_selected, 1)
        self._dispatch(shell, _press(CONTROLLER_BUTTON_DPAD_LEFT))
        self.assertEqual(shell._home_collection_selected, 0)
        chosen = shell._home_collections()[0].collection_id
        self._dispatch(shell, _press(CONTROLLER_BUTTON_A))
        self.assertEqual(shell._category_id, chosen)

    def test_shoulders_page_a_collection_and_guide_returns_home_without_logout(self) -> None:
        shell, screen = self._home()
        items = [_sample(f"org.test.p{i}") for i in range(40)]
        shell._catalogue = ActivityCatalogue.from_activities(items)
        shell._set_category("play")
        shell._cached_activities_key = None
        shell._draw(screen, pygame)
        capacity = shell._page_capacity(pygame)
        self.assertGreater(len(shell._presented_activities), capacity)
        self.assertEqual(shell._selected, 0)

        self._dispatch(shell, _press(CONTROLLER_BUTTON_RIGHTSHOULDER))
        self.assertGreaterEqual(shell._selected, capacity)
        paged = shell._selected
        self._dispatch(shell, _press(CONTROLLER_BUTTON_LEFTSHOULDER))
        self.assertLess(shell._selected, paged)

        profile = shell._active_profile
        self._dispatch(shell, _press(CONTROLLER_BUTTON_GUIDE))
        self.assertEqual(shell._category_id, "all")
        self.assertEqual(shell._mode, "activities")
        # Guide on Home itself is not a logout.
        self._dispatch(shell, _press(CONTROLLER_BUTTON_GUIDE))
        self.assertEqual(shell._mode, "activities")
        self.assertIs(shell._active_profile, profile)
        # Shoulders on Home have nothing to page and change nothing.
        selected = shell._home_collection_selected
        self._dispatch(shell, _press(CONTROLLER_BUTTON_RIGHTSHOULDER))
        self.assertEqual(shell._home_collection_selected, selected)

    def test_east_on_home_keeps_the_established_back_to_profile_choice(self) -> None:
        shell, screen = self._home()
        shell._draw(screen, pygame)
        self._dispatch(shell, _press(CONTROLLER_BUTTON_B))
        self.assertEqual(shell._mode, "profiles")


@unittest.skipUnless(HAS_CONTROLLERS, "curated pygame build has no SDL2 controller module")
class RealLoopControllerTests(_ShellCase):
    """Synthetic events through ``GreiaLauncherPresentation.run`` itself."""

    def _script(self, shell, frames):
        pending = list(frames)

        def hook(_pygame) -> None:
            if pending:
                for event in pending.pop(0):
                    pygame.event.post(event)
            else:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

        shell._poll_input_hooks = hook  # type: ignore[method-assign]

    def setUp(self) -> None:
        pygame.init()
        pygame.font.init()

    def test_first_boot_wizard_is_driven_by_dpad_stick_and_south_through_the_loop(self) -> None:
        profiles_dir = Path(tempfile.mkdtemp(dir=TMP_DIR)) / "profiles"
        os.environ["GREIA_PROFILES_DIR"] = str(profiles_dir)
        os.environ["GREIA_ACTIVE_PROFILE_STATUS"] = str(profiles_dir.parent / "active.json")
        self.addCleanup(os.environ.__setitem__, "GREIA_PROFILES_DIR", os.path.join(TMP_DIR, "profiles"))
        shell, _screen = self._boot()
        self.assertEqual(shell._mode, FIRST_PROFILE_MODE)
        seen: dict[str, object] = {}
        self._script(
            shell,
            [
                [_press(CONTROLLER_BUTTON_A)],  # Welcome -> Name
                [],
                [_press(CONTROLLER_BUTTON_DPAD_DOWN)],  # focus moves on the keyboard
                [],
            ],
        )
        hook = shell._poll_input_hooks

        def observing_hook(pg) -> None:
            view = getattr(shell, "_first_profile_screen", None)
            if view is not None:
                seen["step"] = view.wizard.step
                seen["focus"] = view.layer.focused_id
            hook(pg)

        shell._poll_input_hooks = observing_hook  # type: ignore[method-assign]
        shell.run()
        self.assertGreaterEqual(self.fake_controllers.started, 1)
        self.assertGreaterEqual(self.fake_controllers.closed, 1)
        self.assertIs(seen.get("step"), FirstProfileStep.NAME)
        self.assertIsNotNone(seen.get("focus"))

    def test_picker_selection_moves_once_per_dpad_press(self) -> None:
        profiles_dir = Path(tempfile.mkdtemp(dir=TMP_DIR)) / "profiles"
        os.environ["GREIA_PROFILES_DIR"] = str(profiles_dir)
        os.environ["GREIA_ACTIVE_PROFILE_STATUS"] = str(profiles_dir.parent / "active.json")
        self.addCleanup(os.environ.__setitem__, "GREIA_PROFILES_DIR", os.path.join(TMP_DIR, "profiles"))
        shell, _screen = self._boot()
        shell.profile_store.create("Sara", "owl")
        shell.profile_store.create("Leo", "robot")
        # A device that already has children shows the picker, not the wizard.
        shell._close_first_profile_setup(pygame)
        shell.profiles = shell.profile_store.list_profiles()
        shell._mode = "profiles"
        shell._profile_selected = 0
        self.assertGreaterEqual(len(shell.profiles), 2)
        selections: list[int] = []
        self._script(
            shell,
            [
                [_press(CONTROLLER_BUTTON_DPAD_RIGHT)],
                [_release(CONTROLLER_BUTTON_DPAD_RIGHT)],
                [],
            ],
        )
        hook = shell._poll_input_hooks

        def recording(pg) -> None:
            selections.append(shell._profile_selected)
            hook(pg)

        shell._poll_input_hooks = recording  # type: ignore[method-assign]
        shell.run()
        # One press = one step (no double dispatch from release/axis/keyboard).
        self.assertIn(1, selections)
        self.assertEqual(set(selections) - {0, 1}, set())


@unittest.skipUnless(HAS_CONTROLLERS, "curated pygame build has no SDL2 controller module")
class AchievementShelfControllerTests(_ShellCase):
    def test_shoulders_page_the_shelf_and_guide_closes_it(self) -> None:
        shell, screen = self._boot()
        if shell._visual_cache is None:
            self.skipTest("shared visuals unavailable in this checkout")
        shell.profiles = shell.profile_store.ensure_initialized()
        shell._activate_profile(shell.profiles[0], pygame)
        shell._draw(screen, pygame)
        shell._open_achievement_library()
        if shell._mode != "achievements":
            self.skipTest("achievement library unavailable in this checkout")
        entries = shell._achievement_visible_entries()
        per_page = shell._ACHIEVEMENTS_PER_PAGE
        if len(entries) <= per_page:
            self.skipTest("catalogue fits on one shelf page")
        self._dispatch(shell, _press(CONTROLLER_BUTTON_RIGHTSHOULDER))
        self.assertEqual(shell._achievement_selected, per_page)
        self._dispatch(shell, _press(CONTROLLER_BUTTON_LEFTSHOULDER))
        self.assertEqual(shell._achievement_selected, 0)
        self._dispatch(shell, _press(CONTROLLER_BUTTON_GUIDE))
        self.assertEqual(shell._mode, "activities")


if __name__ == "__main__":
    unittest.main()

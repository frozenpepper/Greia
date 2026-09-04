from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

import pygame

from greia_launcher.main import LauncherApplication
from greia_launcher.shell_input import ShellInputController
from greia_platform.input_core import (
    SemanticAction,
    StandardInputPolicy,
)
from greia_platform.pygame_input import (
    CONTROLLER_BUTTON_A,
    CONTROLLER_BUTTON_DPAD_DOWN,
    CONTROLLER_BUTTON_DPAD_LEFT,
    CONTROLLER_BUTTON_DPAD_RIGHT,
    CONTROLLER_BUTTON_DPAD_UP,
    CONTROLLER_BUTTON_GUIDE,
)


class _FakeControllerSet:
    def __init__(self) -> None:
        self.supported = True
        self.opened_count = 1
        self.started_count = 0
        self.closed_count = 0
        self.stick = (0.0, 0.0)
        self.guide_pressed = False

    def start(self) -> int:
        self.started_count += 1
        return self.opened_count

    def close(self) -> None:
        self.closed_count += 1

    def handle_event(self, event: object) -> bool:
        return False

    def first_left_stick(self) -> tuple[float, float]:
        return self.stick

    def poll_guide_button(self) -> bool:
        return self.guide_pressed


class LauncherControllerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_semantic_action_maps_to_navigation_keys(self) -> None:
        fake_controllers = _FakeControllerSet()
        shell_input = ShellInputController(controllers=fake_controllers)  # type: ignore[arg-type]
        launcher = LauncherApplication(
            windowed=True,
            allow_exit=True,
            shell_input=shell_input,
        )
        launcher.profiles = [
            mock.MagicMock(profile_id="p1", has_secret=False),
            mock.MagicMock(profile_id="p2", has_secret=False),
        ]
        launcher._profile_selected = 0
        launcher._mode = "profiles"

        # NAV_RIGHT advances selection
        launcher._handle_semantic_action(SemanticAction.NAV_RIGHT, pygame)
        self.assertEqual(launcher._profile_selected, 1)

        # NAV_LEFT steps selection back
        launcher._handle_semantic_action(SemanticAction.NAV_LEFT, pygame)
        self.assertEqual(launcher._profile_selected, 0)

        # NAV_DOWN wraps selection
        launcher._handle_semantic_action(SemanticAction.NAV_DOWN, pygame)
        self.assertEqual(launcher._profile_selected, 1)

        # NAV_UP steps back
        launcher._handle_semantic_action(SemanticAction.NAV_UP, pygame)
        self.assertEqual(launcher._profile_selected, 0)

        # ACTIVATE selects profile
        with mock.patch.object(launcher, "_select_profile") as mock_select:
            launcher._handle_semantic_action(SemanticAction.ACTIVATE, pygame)
            mock_select.assert_called_once_with(launcher.profiles[0], pygame)

        # CANCEL triggers exit if allow_exit is True
        self.assertFalse(
            launcher._handle_semantic_action(SemanticAction.CANCEL, pygame)
        )

    def test_controller_events_drive_shell_navigation(self) -> None:
        try:
            from pygame._sdl2 import controller as _sdl_controller  # noqa: F401
        except ImportError:
            self.skipTest("curated pygame build has no SDL2 controller module")

        fake_controllers = _FakeControllerSet()
        shell_input = ShellInputController(controllers=fake_controllers)  # type: ignore[arg-type]
        launcher = LauncherApplication(
            windowed=True,
            allow_exit=True,
            shell_input=shell_input,
        )
        launcher.profiles = [
            mock.MagicMock(profile_id="p1", has_secret=False),
            mock.MagicMock(profile_id="p2", has_secret=False),
        ]
        launcher._profile_selected = 0
        launcher._mode = "profiles"

        event_right = pygame.event.Event(
            pygame.CONTROLLERBUTTONDOWN,
            button=CONTROLLER_BUTTON_DPAD_RIGHT,
        )
        action = launcher._shell_input.handle_event(event_right)
        self.assertEqual(action, SemanticAction.NAV_RIGHT)
        launcher._handle_semantic_action(action, pygame)
        self.assertEqual(launcher._profile_selected, 1)

        # Guide button is reserved: handle_event returns None
        event_guide = pygame.event.Event(
            pygame.CONTROLLERBUTTONDOWN,
            button=CONTROLLER_BUTTON_GUIDE,
        )
        action_guide = launcher._shell_input.handle_event(event_guide)
        self.assertIsNone(action_guide)

    def test_analog_stick_polling_navigates_shell(self) -> None:
        fake_controllers = _FakeControllerSet()
        fake_controllers.stick = (1.0, 0.0)
        policy = StandardInputPolicy(
            navigation_repeat_delay_seconds=0.30,
            navigation_repeat_interval_seconds=0.10,
        )
        shell_input = ShellInputController(
            controllers=fake_controllers,  # type: ignore[arg-type]
            policy=policy,
        )
        launcher = LauncherApplication(
            windowed=True,
            allow_exit=True,
            shell_input=shell_input,
        )
        launcher.profiles = [
            mock.MagicMock(profile_id="p1", has_secret=False),
            mock.MagicMock(profile_id="p2", has_secret=False),
        ]
        launcher._profile_selected = 0
        launcher._mode = "profiles"

        # Poll at t=1.0 -> NAV_RIGHT
        action = launcher._shell_input.poll_analog(1.0)
        self.assertEqual(action, SemanticAction.NAV_RIGHT)
        launcher._handle_semantic_action(action, pygame)
        self.assertEqual(launcher._profile_selected, 1)

        # Poll at t=1.1 -> None (within repeat delay)
        action_delay = launcher._shell_input.poll_analog(1.1)
        self.assertIsNone(action_delay)

        # Poll at t=1.31 -> NAV_RIGHT (repeat)
        action_repeat = launcher._shell_input.poll_analog(1.31)
        self.assertEqual(action_repeat, SemanticAction.NAV_RIGHT)
        launcher._handle_semantic_action(action_repeat, pygame)
        self.assertEqual(launcher._profile_selected, 0)


if __name__ == "__main__":
    unittest.main()

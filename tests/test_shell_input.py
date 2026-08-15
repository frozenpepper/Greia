from __future__ import annotations

import unittest

import pygame

from greia_launcher.shell_input import ShellInputController
from greia_platform.input_core import SemanticAction, StandardInputPolicy
from greia_platform.pygame_input import (
    CONTROLLER_BUTTON_A,
    CONTROLLER_BUTTON_DPAD_RIGHT,
    CONTROLLER_BUTTON_GUIDE,
)


class _Controllers:
    supported = True

    def __init__(self) -> None:
        self.opened_count = 0
        self.started = 0
        self.closed = 0
        self.stick = (0.0, 0.0)
        self.topology_event_types: set[int] = set()

    def start(self) -> int:
        self.started += 1
        self.opened_count = 1
        return self.opened_count

    def close(self) -> None:
        self.closed += 1
        self.opened_count = 0

    def handle_event(self, event) -> bool:
        return event.type in self.topology_event_types

    def first_left_stick(self) -> tuple[float, float]:
        return self.stick


class ShellInputControllerTests(unittest.TestCase):
    def test_lifecycle_owns_and_releases_bounded_controller_set(self) -> None:
        controllers = _Controllers()
        shell = ShellInputController(controllers=controllers)  # type: ignore[arg-type]
        snapshot = shell.start()
        self.assertEqual(snapshot.opened_controllers, 1)
        self.assertEqual(controllers.started, 1)
        shell.close()
        self.assertEqual(controllers.closed, 1)
        self.assertEqual(shell.snapshot.opened_controllers, 0)

    def test_keyboard_event_is_not_double_handled_by_controller_wrapper(self) -> None:
        controllers = _Controllers()
        shell = ShellInputController(controllers=controllers)  # type: ignore[arg-type]
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)
        self.assertIsNone(shell.handle_event(event))

    def test_controller_dpad_and_south_face_use_navigation_semantics(self) -> None:
        try:
            from pygame._sdl2 import controller as _sdl_controller  # noqa: F401
        except ImportError:
            self.skipTest("curated pygame build has no SDL2 controller module")

        controllers = _Controllers()
        shell = ShellInputController(controllers=controllers)  # type: ignore[arg-type]
        right = pygame.event.Event(
            pygame.CONTROLLERBUTTONDOWN,
            button=CONTROLLER_BUTTON_DPAD_RIGHT,
        )
        activate = pygame.event.Event(
            pygame.CONTROLLERBUTTONDOWN,
            button=CONTROLLER_BUTTON_A,
        )
        self.assertIs(shell.handle_event(right), SemanticAction.NAV_RIGHT)
        self.assertIs(shell.handle_event(activate), SemanticAction.ACTIVATE)

    def test_guide_remains_reserved_and_never_reaches_shell_activity_navigation(self) -> None:
        try:
            from pygame._sdl2 import controller as _sdl_controller  # noqa: F401
        except ImportError:
            self.skipTest("curated pygame build has no SDL2 controller module")

        controllers = _Controllers()
        shell = ShellInputController(controllers=controllers)  # type: ignore[arg-type]
        guide = pygame.event.Event(
            pygame.CONTROLLERBUTTONDOWN,
            button=CONTROLLER_BUTTON_GUIDE,
        )
        self.assertIsNone(shell.handle_event(guide))

    def test_left_stick_emits_initial_direction_then_bounded_repeat(self) -> None:
        controllers = _Controllers()
        controllers.stick = (1.0, 0.0)
        policy = StandardInputPolicy(
            navigation_repeat_delay_seconds=0.30,
            navigation_repeat_interval_seconds=0.10,
        )
        shell = ShellInputController(
            controllers=controllers,  # type: ignore[arg-type]
            policy=policy,
        )
        self.assertIs(shell.poll_analog(1.0), SemanticAction.NAV_RIGHT)
        self.assertIsNone(shell.poll_analog(1.20))
        self.assertIs(shell.poll_analog(1.30), SemanticAction.NAV_RIGHT)
        self.assertIsNone(shell.poll_analog(1.35))
        self.assertIs(shell.poll_analog(1.40), SemanticAction.NAV_RIGHT)

    def test_neutral_stick_resets_repeat_and_direction_change_fires_immediately(self) -> None:
        controllers = _Controllers()
        shell = ShellInputController(controllers=controllers)  # type: ignore[arg-type]
        controllers.stick = (1.0, 0.0)
        self.assertIs(shell.poll_analog(1.0), SemanticAction.NAV_RIGHT)
        controllers.stick = (0.0, 0.0)
        self.assertIsNone(shell.poll_analog(1.1))
        self.assertIsNone(shell.snapshot.held_analog_direction)
        controllers.stick = (-1.0, 0.0)
        self.assertIs(shell.poll_analog(1.2), SemanticAction.NAV_LEFT)


if __name__ == "__main__":
    unittest.main()

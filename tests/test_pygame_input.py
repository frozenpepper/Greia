from __future__ import annotations

import unittest
from unittest.mock import patch

import pygame

from greia_platform.input_core import (
    InputEdge,
    InputSource,
    InteractionProfile,
    PhysicalControl,
    SemanticAction,
)
from greia_platform.pygame_input import (
    CONTROLLER_BUTTON_A,
    CONTROLLER_BUTTON_GUIDE,
    MAX_CONTROLLER_SCAN,
    MAX_OPEN_CONTROLLERS,
    PygameControllerSet,
    PygameInputTranslator,
)


class PygameInputTranslatorTests(unittest.TestCase):
    def test_keyboard_navigation_uses_shared_semantic_mapping(self) -> None:
        translator = PygameInputTranslator(InteractionProfile.NAVIGATION)
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        translated = translator.digital(event)
        self.assertIsNotNone(translated)
        assert translated is not None
        self.assertIs(translated.action, SemanticAction.ACTIVATE)
        self.assertIs(translated.edge, InputEdge.PRESSED)
        self.assertIs(translated.source, InputSource.KEYBOARD)

    def test_keyboard_physical_translation_is_runtime_neutral(self) -> None:
        translator = PygameInputTranslator(InteractionProfile.GAME)
        event = pygame.event.Event(pygame.KEYUP, key=pygame.K_LEFT)
        translated = translator.physical_digital(event)
        self.assertEqual(
            translated,
            (PhysicalControl.KEY_LEFT, InputEdge.RELEASED, InputSource.KEYBOARD),
        )

    def test_controller_guide_never_becomes_activity_semantic_action(self) -> None:
        translator = PygameInputTranslator(InteractionProfile.GAME)
        if not translator.controller_translation_available:
            self.skipTest("curated pygame build has no SDL2 controller module")

        event = pygame.event.Event(
            pygame.CONTROLLERBUTTONDOWN,
            button=CONTROLLER_BUTTON_GUIDE,
        )
        physical = translator.physical_digital(event)
        self.assertIsNotNone(physical)
        assert physical is not None
        self.assertIs(physical[0], PhysicalControl.CONTROLLER_GUIDE)
        self.assertIsNone(translator.digital(event))

    def test_controller_south_face_maps_to_game_primary(self) -> None:
        translator = PygameInputTranslator(InteractionProfile.GAME)
        if not translator.controller_translation_available:
            self.skipTest("curated pygame build has no SDL2 controller module")

        event = pygame.event.Event(
            pygame.CONTROLLERBUTTONDOWN,
            button=CONTROLLER_BUTTON_A,
        )
        translated = translator.digital(event)
        self.assertIsNotNone(translated)
        assert translated is not None
        self.assertIs(translated.action, SemanticAction.PRIMARY)
        self.assertIs(translated.source, InputSource.CONTROLLER)


class PygameControllerSetTests(unittest.TestCase):
    def test_bounds_are_small_and_explicit(self) -> None:
        self.assertEqual(MAX_OPEN_CONTROLLERS, 4)
        self.assertEqual(MAX_CONTROLLER_SCAN, 16)
        with self.assertRaises(ValueError):
            PygameControllerSet(maximum_open=9)
        with self.assertRaises(ValueError):
            PygameControllerSet(maximum_open=4, maximum_scan=3)

    def test_missing_controller_module_degrades_without_device_authority(self) -> None:
        controllers = PygameControllerSet()
        with patch("greia_platform.pygame_input.sdl_controller", None):
            self.assertEqual(controllers.start(), 0)
            self.assertEqual(controllers.opened_count, 0)
            self.assertEqual(controllers.first_left_stick(), (0.0, 0.0))
            controllers.close()


if __name__ == "__main__":
    unittest.main()

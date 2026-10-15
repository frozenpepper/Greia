"""Game-rule and shared-control-kit tests for Pasticceria Magica."""

from __future__ import annotations

import os
from pathlib import Path
import random
import unittest

from activities.pasticceria_magica.pasticceria_model import PasticceriaModel
from activities.pasticceria_magica.pasticceria_content import CAKE_SLOTS


class PasticceriaRulesTests(unittest.TestCase):
    def test_correct_order_requires_exact_ingredients(self) -> None:
        model = PasticceriaModel(rng=random.Random(2))
        for topping, amount in model.current_order:
            for _ in range(amount):
                self.assertIsNotNone(model.place_topping(topping))
        self.assertTrue(model.check_order_correct())
        model.apply_correct_order()
        self.assertEqual(model.recipes_served, 1)
        self.assertEqual(model.stars, 1)
        self.assertEqual(model.score, 15)
        self.assertFalse(model.placed_toppings)

    def test_extra_ingredient_and_missing_ingredient_do_not_count(self) -> None:
        model = PasticceriaModel()
        self.assertFalse(model.check_order_correct())
        model.place_topping(model.current_order[0][0])
        self.assertFalse(model.check_order_correct())
        self.assertFalse(model.place_topping("__not_a_topping__"))
        self.assertLessEqual(len(model.placed_toppings), len(CAKE_SLOTS))

    def test_pattern_progress_and_free_mode_do_not_invent_recipes(self) -> None:
        model = PasticceriaModel()
        _, answer, choices = model.current_pattern
        self.assertIn(answer, choices)
        self.assertTrue(model.check_pattern_candidate(answer))
        model.apply_correct_pattern()
        self.assertEqual(model.stars, 1)
        model.switch_mode("free")
        model.apply_free_serve()
        self.assertEqual(model.recipes_served, 0)


class PasticceriaControlKitTests(unittest.TestCase):
    """Keyboard/controller focus drives the same callbacks as pointer taps."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame

        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _app(self):
        import pygame
        from greia_platform.activity_ui import ChildUiMetrics
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from activities.pasticceria_magica.pasticceria_app import PasticceriaApp
        from activities.pasticceria_magica.pasticceria_renderer import PasticceriaRenderer

        screen = pygame.display.get_surface()
        root = Path(__file__).resolve().parents[1] / "activities" / "pasticceria_magica"
        context = resolve_activity_locale("en", ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it"))
        resources = LocalizedResources(root, context)
        typography = GreiaTypography()
        model = PasticceriaModel(rng=random.Random(1))
        app = PasticceriaApp(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            metrics=ChildUiMetrics.for_size(*screen.get_size()),
            typography=typography,
            model=model,
            renderer=PasticceriaRenderer(typography, resources),
            resources=resources,
        )
        return app, model

    def _key(self, app, key) -> None:
        import pygame

        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def test_keyboard_reaches_tabs_pantry_and_serve(self) -> None:
        import pygame

        app, model = self._app()
        layer = app.controls.layer
        self.assertEqual(layer.focused_id, "mode.orders")
        self._key(app, pygame.K_RIGHT)
        self.assertEqual(layer.focused_id, "mode.patterns")
        self._key(app, pygame.K_SPACE)
        self.assertEqual(model.mode, "patterns")
        self._key(app, pygame.K_LEFT)
        self._key(app, pygame.K_RETURN)
        self.assertEqual(model.mode, "orders")
        self._key(app, pygame.K_DOWN)
        self.assertTrue(layer.focused_id.startswith("topping."))
        self._key(app, pygame.K_SPACE)
        self.assertEqual(len(model.placed_toppings), 1)
        for _ in range(4):
            self._key(app, pygame.K_DOWN)
        self._key(app, pygame.K_RIGHT)
        self.assertEqual(layer.focused_id, "serve")
        self._key(app, pygame.K_SPACE)
        self.assertEqual(model.feedback_text != "", True)

    def test_pointer_taps_keep_original_targets_and_cake_removal(self) -> None:
        from activities.pasticceria_magica.pasticceria_controls import TOPPING_RECTS

        app, model = self._app()
        app.handle_pointer(TOPPING_RECTS[0].center)
        self.assertEqual(len(model.placed_toppings), 1)
        _, _, x, y = model.placed_toppings[0]
        app.handle_pointer((x, y))
        self.assertEqual(model.placed_toppings, [])
        app.handle_pointer((485, 38))
        self.assertEqual(model.mode, "patterns")

    def test_controller_dpad_and_south_button(self) -> None:
        import pygame
        from greia_platform import pygame_input

        if pygame_input.sdl_controller is None or pygame_input._CONTROLLER_BUTTON_DOWN < 0:
            self.skipTest("SDL controller events unavailable in this pygame build")
        app, model = self._app()
        down = pygame_input._CONTROLLER_BUTTON_DOWN
        app.handle_event(pygame.event.Event(down, button=pygame_input.CONTROLLER_BUTTON_DPAD_RIGHT))
        app.handle_event(pygame.event.Event(down, button=pygame_input.CONTROLLER_BUTTON_DPAD_RIGHT))
        app.handle_event(pygame.event.Event(down, button=pygame_input.CONTROLLER_BUTTON_A))
        self.assertEqual(model.mode, "free")


if __name__ == "__main__":
    unittest.main()

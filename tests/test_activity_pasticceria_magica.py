"""Pure game-rule tests for Pasticceria Magica; no screen or voice required."""

from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()

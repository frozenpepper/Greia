"""Serra domain progression tests without display, audio or persistence fixtures."""

from __future__ import annotations

import unittest

from activities.piccola_serra.serra_model import SerraModel
from activities.piccola_serra.serra_content import TARGET_HARVEST


class SerraGrowthTests(unittest.TestCase):
    def test_each_plant_needs_seed_water_sun_water_then_harvest(self) -> None:
        model = SerraModel()
        for stage, tool in enumerate((0, 1, 2, 1, 3)):
            self.assertEqual(model.pots[0]["stage"], stage)
            self.assertIsNone(model.apply_tool(0, (tool + 1) % 4, 0))
            self.assertEqual(model.pots[0]["stage"], stage)
            self.assertIsNotNone(model.apply_tool(0, tool, 0))
        self.assertEqual(model.pots[0]["stage"], 0)
        self.assertEqual(model.harvest_count, 1)

    def test_harvest_completion_only_after_real_growth_cycles(self) -> None:
        model = SerraModel()
        for number in range(TARGET_HARVEST):
            for tool in (0, 1, 2, 1):
                self.assertIsNotNone(model.apply_tool(0, tool, number))
            result = model.apply_tool(0, 3, number)
            self.assertIsNotNone(result)
            self.assertEqual(bool(result.get("victory")), number + 1 == TARGET_HARVEST)
        self.assertTrue(model.is_victory)
        self.assertEqual(model.harvest_count, TARGET_HARVEST)
        model.reset()
        self.assertFalse(model.is_victory)
        self.assertEqual(model.harvest_count, 0)


if __name__ == "__main__":
    unittest.main()

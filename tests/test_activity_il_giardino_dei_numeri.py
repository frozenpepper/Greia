"""Tests for Il Giardino dei Numeri Activity (manifest, model, services)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "il_giardino_dei_numeri"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

from giardino_model import GardenModel, ItemKind
from giardino_services import GiardinoServices, GiardinoStorageState


class GiardinoDeiNumeriTests(unittest.TestCase):
    def test_manifest_metadata(self) -> None:
        manifest_path = ACTIVITY_ROOT / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))

        # Activity identity
        act = data["activity"]
        self.assertEqual(act["id"], "org.greia.il-giardino-dei-numeri")
        self.assertEqual(act["title_key"], "activity.il_giardino_dei_numeri.title")
        self.assertEqual(act["languages"], ["it", "en"])

        # Education & audience
        edu = data["education"]
        self.assertEqual(edu["difficulty"], 1)
        self.assertEqual(edu["recommended_age_min"], 2)
        self.assertEqual(edu["recommended_age_max"], 4)
        self.assertEqual(edu["difficulty_min"], 1)
        self.assertEqual(edu["difficulty_max"], 3)
        self.assertTrue(edu["adaptive_difficulty"])

        # Events
        event_ids = [e["id"] for e in edu["events"]]
        self.assertIn("garden.set_counted", event_ids)
        self.assertIn("garden.basket_filled", event_ids)

    def test_counting_model_progression(self) -> None:
        model = GardenModel(difficulty_level=1)
        model.setup_round(count=3)
        self.assertEqual(model.target_count, 3)
        self.assertEqual(len(model.items), 3)
        self.assertEqual(model.counted_count, 0)
        self.assertFalse(model.celebrating)

        # Tap first item
        outcome, order = model.handle_tap(model.items[0].x, model.items[0].y)
        self.assertEqual(outcome, "counted")
        self.assertEqual(order, 1)
        self.assertEqual(model.counted_count, 1)
        self.assertTrue(model.items[0].counted)
        self.assertEqual(model.dani_mood, "happy")

        # Tap first item again -> giggle, does not count again
        outcome, order = model.handle_tap(model.items[0].x, model.items[0].y)
        self.assertEqual(outcome, "giggle")
        self.assertEqual(model.counted_count, 1)

        # Tap ground -> miss, adds ripple
        prev_ripples = len(model.ripple_effects)
        outcome, _ = model.handle_tap(10, 10)
        self.assertEqual(outcome, "miss")
        self.assertEqual(len(model.ripple_effects), prev_ripples + 1)

        # Tap second item
        outcome, order = model.handle_tap(model.items[1].x, model.items[1].y)
        self.assertEqual(outcome, "counted")
        self.assertEqual(order, 2)
        self.assertEqual(model.counted_count, 2)
        self.assertFalse(model.celebrating)

        # Tap third item -> completion
        outcome, order = model.handle_tap(model.items[2].x, model.items[2].y)
        self.assertEqual(outcome, "counted")
        self.assertEqual(order, 3)
        self.assertEqual(model.counted_count, 3)
        self.assertTrue(model.pending_celebration)
        self.assertEqual(model.baskets_filled, 1)

        # Model update after spoken number delay triggers celebration and milestone event
        events = model.update(1.1)
        self.assertTrue(model.celebrating)
        self.assertIn("garden.set_counted", events)

    def test_services_state_and_safe_events(self) -> None:
        services = GiardinoServices()
        # Should safely handle when no platform context is active
        services.emit_event("garden.set_counted")
        state = services.load_state()
        self.assertIsInstance(state, GiardinoStorageState)


if __name__ == "__main__":
    unittest.main()

"""Tests for L'Alfabeto di Leo Activity (manifest, model, services)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "alfabeto_leo"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

from alfabeto_model import AlfabetoModel, GameMode, LETTERS_CATALOGUE
from alfabeto_services import AlfabetoServices, AlfabetoStorageState


class AlfabetoLeoTests(unittest.TestCase):
    def test_manifest_metadata(self) -> None:
        manifest_path = ACTIVITY_ROOT / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))

        act = data["activity"]
        self.assertEqual(act["id"], "org.greia.alfabeto-leo")
        self.assertEqual(act["title_key"], "activity.alfabeto_leo.title")
        self.assertEqual(act["languages"], ["it", "en"])

        edu = data["education"]
        self.assertEqual(edu["difficulty"], 1)
        self.assertEqual(edu["recommended_age_min"], 2)
        self.assertEqual(edu["recommended_age_max"], 4)
        self.assertEqual(edu["difficulty_min"], 1)
        self.assertEqual(edu["difficulty_max"], 3)
        self.assertTrue(edu["adaptive_difficulty"])

        event_ids = [e["id"] for e in edu["events"]]
        self.assertIn("letter.discovered", event_ids)
        self.assertIn("alphabet.parade_completed", event_ids)

    def test_alphabet_catalogue_coverage(self) -> None:
        self.assertEqual(len(LETTERS_CATALOGUE), 26)
        chars = [item.char for item in LETTERS_CATALOGUE]
        self.assertEqual("".join(chars), "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        for item in LETTERS_CATALOGUE:
            self.assertTrue(item.char.isupper())
            self.assertTrue(item.word_it.isupper())
            self.assertTrue(item.word_en.isupper())
            self.assertEqual(item.word_for("it"), item.word_it)
            self.assertEqual(item.word_for("en"), item.word_en)

    def test_model_explore_and_guess_mechanics(self) -> None:
        model = AlfabetoModel(locale="it")
        self.assertEqual(model.mode, GameMode.EXPLORE)

        # Explore mode selection
        ok = model.select_letter("M")
        self.assertTrue(ok)
        self.assertEqual(model.active_letter.char, "M")
        self.assertEqual(model.active_letter.word_it, "MELA")
        self.assertIn("M", model.discovered_letters)

        # Switch to guess mode
        model.switch_mode(GameMode.GUESS)
        self.assertEqual(model.mode, GameMode.GUESS)
        self.assertEqual(len(model.guess_choices), 3)
        self.assertIn(model.target_letter, model.guess_choices)

        # Test wrong guess -> wobble, no penalty
        distractor = next(c for c in model.guess_choices if c.char != model.target_letter.char)
        res, _ = model.handle_guess_choice(distractor.char)
        self.assertEqual(res, "wobble")
        self.assertEqual(model.wobble_card, distractor.char)
        self.assertFalse(model.guess_solved)

        # Test correct guess -> solved, celebration
        res, solved_item = model.handle_guess_choice(model.target_letter.char)
        self.assertEqual(res, "correct")
        self.assertEqual(solved_item.char, model.target_letter.char)
        self.assertTrue(model.guess_solved)
        self.assertTrue(model.celebrating)

        # Update triggers event
        events = model.update(0.1)
        self.assertIn("letter.discovered", events)

    def test_services_safe_fallback(self) -> None:
        services = AlfabetoServices()
        services.emit_event("letter.discovered")
        state = services.load_state()
        self.assertIsInstance(state, AlfabetoStorageState)


if __name__ == "__main__":
    unittest.main()

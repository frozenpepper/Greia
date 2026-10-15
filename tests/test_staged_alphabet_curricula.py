"""Source-only staged Spanish/French alphabet curriculum, including Ñ."""
from __future__ import annotations

from pathlib import Path
import sys
import random
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "activities" / "alfabeto_leo"))

from alfabeto_model import (  # noqa: E402
    LETTERS_CATALOGUE, PICTURE_PENDING, GardenPlanner, GardenRound, StepKind,
    get_letter_catalogue, teaching_groups,
)


class StagedAlphabetCurriculumTests(unittest.TestCase):
    def test_existing_en_it_alphabet_and_examples_unchanged(self) -> None:
        expected = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for locale in ("it", "en-GB"):
            with self.subTest(locale=locale):
                letters = get_letter_catalogue(locale)
                self.assertEqual("".join(item.char for item in letters), expected)
                self.assertEqual(letters, tuple(LETTERS_CATALOGUE))
        self.assertEqual(LETTERS_CATALOGUE[0].word_for("it"), "APE")
        self.assertEqual(LETTERS_CATALOGUE[0].word_for("en"), "APPLE")

    def test_spanish_alphabet_has_27_real_learning_letters(self) -> None:
        letters = get_letter_catalogue("es-ES")
        self.assertEqual("".join(item.char for item in letters), "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ")
        self.assertEqual(len(letters), 27)
        self.assertEqual(len({i.char for i in letters}), 27)
        self.assertEqual(letters[14].word_for("es-MX"), "ÑANDÚ")
        for item in letters:
            self.assertTrue(item.word_for("es").startswith(item.char))
            self.assertTrue(item.picture_for("es"))
        with self.assertRaises(ValueError):
            letters[14].word_for("en")

    def test_french_alphabet_preserves_accents_in_example_words(self) -> None:
        letters = get_letter_catalogue("fr_FR")
        self.assertEqual(len(letters), 26)
        self.assertEqual(letters[21].word_for("fr-FR"), "VÉLO")
        for item in letters:
            self.assertTrue(item.word_for("fr").startswith(item.char))
            self.assertTrue(item.picture_for("fr"))
        with self.assertRaises(ValueError):
            get_letter_catalogue("zh-CN")

    def test_spanish_teaching_groups_and_garden_round_include_enye(self) -> None:
        groups = teaching_groups("es")
        self.assertEqual(sum(len(group) for group in groups), 27)
        enye_group = next(index for index, group in enumerate(groups) if "Ñ" in group)
        planner = GardenPlanner(random.Random(4), locale="es")
        round_ = GardenRound(planner.build(enye_group), group=enye_group)
        self.assertIn("Ñ", [item.char for item in round_.letters])
        enye = next(step for step in round_.steps if step.kind is StepKind.MEET and step.letter.char == "Ñ")
        self.assertEqual(enye.letter.word_for("es"), "ÑANDÚ")
        self.assertEqual(enye.letter.picture_for("es"), PICTURE_PENDING)  # staged: no art yet
        # Italian/English/French lessons never offer Ñ, not even as a decoy.
        for locale in ("it", "en", "fr"):
            planner = GardenPlanner(random.Random(4), locale=locale)
            for group in range(planner.group_count + 1):
                for step in planner.build(group):
                    self.assertNotIn("Ñ", [item.char for item in step.choices] + [step.letter.char])

    def test_activity_stays_two_language_until_voice_approved(self) -> None:
        import tomllib
        manifest = tomllib.loads(
            (ROOT / "activities/alfabeto_leo/activity.toml").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])

    def test_real_alphabet_audio_inventory_counts_enye_and_blocks_scripts(self) -> None:
        from tools.audit_greia_language_coverage import _alphabet_lesson_audio

        errors: list[str] = []
        cues = _alphabet_lesson_audio(ROOT, errors)
        self.assertEqual(errors, [])
        for locale, expected in (("it", 56), ("en", 56), ("es", 58), ("fr", 56)):
            with self.subTest(locale=locale):
                relevant = [row for row in cues if row["locale"] == locale]
                self.assertEqual(len(relevant), expected)
                self.assertEqual(len({row["path"] for row in relevant}), expected)
                self.assertTrue(all(row["state"] == "BLOCKED_TEXT" for row in relevant))
                self.assertEqual(any(row["path"].endswith("letter_Ñ.wav") for row in relevant), locale == "es")




if __name__ == "__main__":
    unittest.main()

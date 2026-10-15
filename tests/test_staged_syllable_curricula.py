"""Pure-domain staged curricula; not a claim of certified learning audio."""
from __future__ import annotations

import random
import sys
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "activities/sillabe_magiche"
sys.path.insert(0, str(PACKAGE))

from sillabe_audio import recorded_clip_checker  # noqa: E402
from sillabe_content import (  # noqa: E402
    CONSONANTS_IT, VOWELS_IT, WORDS_DATA_EN, WORDS_DATA_IT,
    approved_syllables, get_syllable_curriculum, train_words,
)
from sillabe_model import Phase, StepKind, TrainRoundFactory, TrainSession  # noqa: E402


class StagedSyllableCurriculumTests(unittest.TestCase):
    def test_existing_language_semantics_unchanged(self) -> None:
        self.assertEqual(get_syllable_curriculum("it").words, tuple(WORDS_DATA_IT))
        self.assertEqual(get_syllable_curriculum("en-US").words, tuple(WORDS_DATA_EN))
        self.assertEqual(get_syllable_curriculum("it").consonants, tuple(CONSONANTS_IT))
        self.assertEqual(get_syllable_curriculum("en").vowels, tuple(VOWELS_IT))
        self.assertIn("esatto", get_syllable_curriculum("it").praise_cues)
        self.assertIn("great_job", get_syllable_curriculum("en").praise_cues)

    def test_es_fr_have_distinct_real_word_syllable_candidates(self) -> None:
        for locale in ("es-ES", "fr-FR"):
            with self.subTest(locale=locale):
                corpus = get_syllable_curriculum(locale)
                self.assertEqual(len(corpus.words), 16)
                self.assertEqual(len(corpus.tabs), 3)
                stems = set()
                for word, (first, second), picture, stem in corpus.words:
                    self.assertEqual(word, first + second)
                    self.assertTrue(picture)
                    self.assertTrue(stem.isascii() and stem.islower() and stem.isalpha())
                    self.assertNotIn(stem, stems)
                    stems.add(stem)
                language = locale[:2]
                factory = TrainRoundFactory(
                    random.Random(42), locale, clip_exists=recorded_clip_checker(PACKAGE, language)
                )
                session = TrainSession(factory.build_set(2), level=2)
                while not session.is_complete:
                    if session.phase is Phase.CLAP:
                        session.clap()
                        continue
                    step = session.current_step
                    challenge = session.current_challenge
                    self.assertEqual(step.target_syllable, challenge.word.syllables[step.wagon])
                    session.select_choice(step.correct_index)
        self.assertEqual(get_syllable_curriculum("fr").words[4][0], "VÉLO")
        for unsupported in ("de-DE", "zh-CN"):
            with self.assertRaises(ValueError):
                get_syllable_curriculum(unsupported)

    def test_staged_trains_never_invent_phonemes(self) -> None:
        for locale, expected_labels in (("es", "MPLSTNDF"), ("fr", "MPLTS")):
            with self.subTest(locale=locale):
                curriculum = get_syllable_curriculum(locale)
                self.assertEqual("".join(curriculum.consonants), expected_labels)
                self.assertEqual(len(curriculum.syllable_families), len(expected_labels))
                approved = set(approved_syllables(locale))
                parts = {part for _, segments, _, _ in curriculum.words for part in segments}
                families = {syl for _, family in curriculum.syllable_families for syl in family}
                self.assertEqual(approved, families | parts)
                recorded = recorded_clip_checker(PACKAGE, locale)
                for level in (1, 2, 3):
                    for seed in range(15):
                        factory = TrainRoundFactory(random.Random(seed), locale, clip_exists=recorded)
                        self.assertTrue(all(recorded(f"syl_{s.lower()}") for s in factory.approved))
                        for challenge in factory.build_set(level):
                            for step in challenge.steps:
                                offered = {step.syllable_for(i) for i in range(len(step.choices))}
                                self.assertTrue(offered <= approved, offered - approved)
                                if locale == "fr":
                                    self.assertIs(step.kind, StepKind.SYLLABLE)
                if locale == "fr":
                    self.assertNotIn("ME", approved)
                    self.assertIn("MÉ", approved)
                    # Family syllables without a French recording are never offered.
                    self.assertNotIn("MÉ", TrainRoundFactory(random.Random(1), "fr", clip_exists=recorded).approved)
                else:
                    self.assertNotIn("CE", approved)  # Not in the ES families or words.

    def test_curated_families_are_well_formed(self) -> None:
        for locale in ("es", "fr"):
            curriculum = get_syllable_curriculum(locale)
            seen: set[str] = set()
            for label, family in curriculum.syllable_families:
                self.assertEqual(len(family), 5)
                self.assertEqual(len(set(family)), 5)
                self.assertTrue(all(syl.startswith(label) for syl in family))
                self.assertFalse(seen & set(family))
                seen.update(family)
            self.assertTrue(train_words(locale))

    def test_staged_languages_are_not_advertised(self) -> None:
        manifest = tomllib.loads((PACKAGE / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])

    def test_source_syllable_audio_inventory_exposes_required_unvoiced_cues(self) -> None:
        from tools.audit_greia_language_coverage import _syllable_lesson_audio

        errors: list[str] = []
        cues = _syllable_lesson_audio(ROOT, errors)
        self.assertEqual(errors, [])
        for locale in ("es", "fr"):
            with self.subTest(locale=locale):
                scoped = [row for row in cues if row["locale"] == locale]
                self.assertEqual(len(scoped), {"es": 115, "fr": 93}[locale])
                self.assertEqual(len(scoped), len({row["path"] for row in scoped}))
                self.assertEqual(len([row for row in scoped if row["path"].split("/")[-1].startswith("word_")]), 16)
                self.assertTrue(any(row["state"] == "BLOCKED_TEXT" for row in scoped))
                self.assertTrue(all(row["speaker"] == "UNASSIGNED" for row in scoped))
                # A ledger must reflect actual on-screen and playable cues,
                # not phantom combinations from the old Italian grid.
                filenames = {row["path"].split("/")[-1] for row in scoped}
                if locale == "fr":
                    self.assertIn("find_mé.wav", filenames)
                    self.assertNotIn("find_ba.wav", filenames)
                    self.assertIn("syl_ba.wav", filenames)  # Builder-only part.
                    self.assertNotIn("find_me.wav", filenames)
                else:
                    self.assertIn("find_ma.wav", filenames)
                    self.assertNotIn("find_ca.wav", filenames)
                    self.assertIn("syl_ca.wav", filenames)  # Builder-only part.

                self.assertTrue(any(row["path"].endswith("word_bebe.wav") and row["text"] == "bébé" for row in scoped) if locale == "fr" else
                                any(row["path"].endswith("word_luna.wav") and row["text"] == "luna" for row in scoped))

    def test_nonliteral_word_tables_are_never_executed_by_inventory(self) -> None:
        import tempfile
        from tools.audit_greia_language_coverage import _syllable_lesson_audio

        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "activities/sillabe_magiche"
            package.mkdir(parents=True)
            marker = Path(temp) / "EXECUTED"
            (package / "sillabe_content.py").write_text(
                'WORDS_DATA_ES: list = __import__("pathlib").Path(' + repr(str(marker)) + ').touch()\n',
                encoding="utf-8",
            )
            errors: list[str] = []
            self.assertEqual(_syllable_lesson_audio(Path(temp), errors), [])
            self.assertTrue(errors)
            self.assertFalse(marker.exists())




if __name__ == "__main__":
    unittest.main()

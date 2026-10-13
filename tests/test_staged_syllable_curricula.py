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

from sillabe_content import (  # noqa: E402
    CONSONANTS_IT, VOWELS_IT, WORDS_DATA_EN, WORDS_DATA_IT,
    get_syllable_curriculum,
)
from sillabe_model import SillabeSession  # noqa: E402


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
                for word, (first, second), symbol, stem in corpus.words:
                    self.assertEqual(word, first + second)
                    self.assertTrue(symbol)
                    self.assertTrue(stem.isascii() and stem.islower() and stem.isalpha())
                    self.assertNotIn(stem, stems)
                    stems.add(stem)
                session = SillabeSession(
                    words_pool=list(corpus.words),
                    consonants_pool=corpus.consonants,
                    vowels_pool=corpus.vowels,
                    rng=random.Random(42),
                )
                for _ in corpus.words:
                    word_entry, choices = session.start_word_round()
                    self.assertEqual(word_entry[0], word_entry[1][0] + word_entry[1][1])
                    self.assertIn(session.cur_s1, choices)
                    self.assertIn(session.cur_s2, choices)
                    session.advance_word()
        self.assertEqual(get_syllable_curriculum("fr").words[4][0], "VÉLO")
        for unsupported in ("de-DE", "zh-CN"):
            with self.assertRaises(ValueError):
                get_syllable_curriculum(unsupported)

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
                self.assertGreaterEqual(len(scoped), 170)
                self.assertEqual(len(scoped), len({row["path"] for row in scoped}))
                self.assertEqual(len([row for row in scoped if row["path"].split("/")[-1].startswith("word_")]), 16)
                self.assertTrue(any(row["state"] == "BLOCKED_TEXT" for row in scoped))
                self.assertTrue(all(row["speaker"] == "UNASSIGNED" for row in scoped))
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

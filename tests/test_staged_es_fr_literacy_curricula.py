"""Pure-source regression for staged Spanish/French literacy lessons.

The two Activities deliberately remain EN/IT in their manifests pending
human phonological review and reviewed spoken audio; tests prove lesson
content is not silently substituted from another language.
"""
from __future__ import annotations

from pathlib import Path
import random
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
for directory in ("festa_delle_rime", "officina_dei_suoni"):
    path = str(ROOT / "activities" / directory)
    if path not in sys.path:
        sys.path.insert(0, path)

from rhyme_content import get_corpus  # noqa: E402
from rhyme_model import RhymeRoundFactory  # noqa: E402
from sound_content import get_sound_units  # noqa: E402
from sound_workshop_model import SoundRoundFactory  # noqa: E402


class StagedLiteracyCurriculumTests(unittest.TestCase):
    def test_rhyme_corpora_are_distinct_and_have_no_wrong_language_fallback(self) -> None:
        for locale in ("es", "fr"):
            with self.subTest(locale=locale):
                pairs, families = get_corpus(locale)
                self.assertEqual(len(pairs), 8)
                self.assertEqual(len(families), 6)
                self.assertEqual(get_corpus(locale + "-ES"), (pairs, families))
                self.assertNotEqual(pairs, get_corpus("it")[0])
                self.assertNotEqual(pairs, get_corpus("en")[0])
                # Alliteration teaching is based on the *audible* shared onset.
                # Source spelling is an initial guard; native hearing review
                # remains a blocker before any child-visible promotion.
                for family in families:
                    self.assertEqual(len(family), 3)
                    self.assertEqual(len({item.item_id for item in family}), 3)
                    self.assertEqual(len({item.item_id[0] for item in family}), 1)
                for pair in pairs:
                    self.assertNotEqual(pair[0].item_id, pair[1].item_id)
                for level in range(1, 5):
                    challenges = RhymeRoundFactory(random.Random(107 + level), locale).build_set(level)
                    self.assertEqual(len(challenges), 8)
                    self.assertTrue(all(c.choices[c.correct_index] in c.choices for c in challenges))
        self.assertIs(get_corpus("IT")[0], get_corpus("it")[0])
        with self.assertRaises(ValueError):
            get_corpus("de")

    def test_sound_corpora_keep_actual_locale_words_and_sound_ids(self) -> None:
        for locale in ("es", "fr"):
            with self.subTest(locale=locale):
                units = get_sound_units(locale)
                self.assertEqual(len(units), 8)
                self.assertIs(get_sound_units(locale + "-FR"), units)
                self.assertNotEqual(units, get_sound_units("it"))
                self.assertEqual(len({u.grapheme_upper for u in units}), 8)
                for unit in units:
                    self.assertEqual(unit.audio_id, unit.phoneme_id)
                    self.assertEqual(len(unit.words), 3)
                    self.assertEqual(len({w.word_id for w in unit.words}), 3)
                    for word in unit.words:
                        self.assertEqual(word.initial_sound_id, unit.phoneme_id)
                        self.assertTrue(word.label.startswith(unit.grapheme_upper))
                        self.assertEqual(word.label[1:], word.remainder)
                for level in range(1, 4):
                    challenges = SoundRoundFactory(random.Random(207 + level), locale).build_set(level)
                    self.assertEqual(len(challenges), 6)
                    self.assertTrue(all(len(c.choices) == 3 for c in challenges))
        with self.assertRaises(ValueError):
            get_sound_units("de")

    def test_staged_lessons_are_not_advertised_without_approved_speech(self) -> None:
        for activity in ("festa_delle_rime", "officina_dei_suoni"):
            with self.subTest(activity=activity):
                manifest = tomllib.loads((ROOT / "activities" / activity / "activity.toml").read_text(encoding="utf-8"))
                self.assertEqual(manifest["activity"]["languages"], ["it", "en"])


    def test_source_only_inventory_contains_staged_voices_without_fake_scripts(self) -> None:
        from tools.audit_greia_language_coverage import _literacy_lesson_audio

        for activity, expected in (
            ("festa_delle_rime", {"es": 31, "fr": 29}),
            ("officina_dei_suoni", {"es": 32, "fr": 32}),
        ):
            errors: list[str] = []
            cues = _literacy_lesson_audio(ROOT, activity, errors)
            self.assertEqual(errors, [])
            for locale, count in expected.items():
                with self.subTest(activity=activity, locale=locale):
                    relevant = [c for c in cues if c["locale"] == locale]
                    self.assertEqual(len(relevant), count)
                    self.assertEqual(len({c["cue_id"] for c in relevant}), count)
                    self.assertTrue(all(c["source"] == f"activities/{activity}" for c in relevant))
                    self.assertTrue(all(c["path"].startswith(f"assets/audio/{locale}/") for c in relevant))
                    self.assertTrue(all(c["speaker"] == "UNASSIGNED" for c in relevant))
                    if activity == "festa_delle_rime":
                        self.assertTrue(all(c["state"] == "BLOCKED_TEXT" for c in relevant))
                    else:
                        blocked = [c for c in relevant if c["state"] == "BLOCKED_TEXT"]
                        self.assertEqual(len(blocked), 8)
                        self.assertTrue(any(c["text"] == "fée" for c in relevant) if locale == "fr" else
                                        any(c["text"] == "lápiz" for c in relevant))

    def test_inventory_never_executes_untrusted_lesson_source(self) -> None:
        import tempfile
        from tools.audit_greia_language_coverage import _literacy_lesson_audio

        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "activities" / "festa_delle_rime"
            package.mkdir(parents=True)
            sentinel = Path(temp) / "DANGER"
            (package / "rhyme_content.py").write_text(
                'RHYME_PAIRS_ES: Final = __import__("pathlib").Path('
                + repr(str(sentinel)) + ').touch()\n',
                encoding="utf-8",
            )
            errors: list[str] = []
            self.assertEqual(_literacy_lesson_audio(Path(temp), "festa_delle_rime", errors), [])
            self.assertTrue(errors)
            self.assertFalse(sentinel.exists())


if __name__ == "__main__":
    unittest.main()

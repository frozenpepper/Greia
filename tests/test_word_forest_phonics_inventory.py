"""Source-only acceptance for language-relative Word Forest recording cues."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import tempfile
import unittest

from tools.audit_greia_language_coverage import _foresta_lesson_audio


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_DIR = ROOT / "activities" / "foresta_parole"


class WordForestPhonicsInventoryTests(unittest.TestCase):
    def test_all_four_phonics_catalogues_produce_distinct_audio_candidates(self) -> None:
        errors: list[str] = []
        cues = _foresta_lesson_audio(ROOT, errors)
        self.assertEqual(errors, [])
        expected = {"it": 20, "en": 22, "es": 21, "fr": 21}
        for locale, lessons in expected.items():
            with self.subTest(locale=locale):
                group = [item for item in cues if item["locale"] == locale]
                self.assertEqual(len(group), 3 * lessons)
                self.assertEqual(len({item["cue_id"] for item in group}), len(group))
                self.assertEqual(
                    Counter(item["cue_id"].split(".")[1] for item in group),
                    {"letter": lessons, "prompt": lessons, "word": lessons},
                )

    def test_staged_language_lesson_audio_is_integrated_and_unspecified_scripts_stay_blocked(self) -> None:
        errors: list[str] = []
        cues = _foresta_lesson_audio(ROOT, errors)
        self.assertEqual(errors, [])
        for cue in cues:
            if cue["locale"] not in ("es", "fr"):
                continue
            with self.subTest(locale=cue["locale"], cue=cue["cue_id"]):
                self.assertEqual(cue["source"], "activities/foresta_parole")
                self.assertTrue(cue["path"].startswith(f"assets/audio/{cue['locale']}/"))
                # ES/FR phonics recordings were integrated and owner-approved;
                # the audit must see the committed files (English fallback is
                # allowed for any cue that is ever missing, so existence is the
                # meaningful inventory fact, not absence).
                self.assertTrue(cue["file_exists"])
                self.assertEqual(cue["speaker"], "UNASSIGNED")
                self.assertEqual(cue["kind"], "UNASSIGNED")
                role = cue["cue_id"].split(".")[1]
                if role in ("letter", "prompt"):
                    self.assertIsNone(cue["text"])
                    self.assertEqual(cue["state"], "BLOCKED_TEXT")
                else:
                    self.assertTrue(cue["text"])
                    self.assertEqual(cue["state"], "EXISTING_ASSET_NEEDS_REVIEW")


    def test_child_visible_text_comes_from_localized_resources(self) -> None:
        import json

        app_source = (ACTIVITY_DIR / "foresta_app.py").read_text(encoding="utf-8")
        # The only child-visible copy is the completion card; prompts are
        # picture + voice, and example words come from the lesson data.
        self.assertIn('self.resources.text("victory.title")', app_source)
        self.assertIn('self.resources.text("button.play_again")', app_source)
        for locale in ("en", "it", "es", "fr"):
            with self.subTest(locale=locale):
                bundle = json.loads((ACTIVITY_DIR / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
                self.assertTrue(bundle["strings"]["victory.title"].strip())
                self.assertTrue(bundle["strings"]["button.play_again"].strip())

    def test_nonliteral_phonics_source_is_never_executed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "activities/foresta_parole"
            package.mkdir(parents=True)
            (package / "foresta_content.py").write_text(
                'PHONICS_DATA: Final = __import__("os").getcwd()\n',
                encoding="utf-8",
            )
            errors: list[str] = []
            self.assertEqual(_foresta_lesson_audio(Path(temp), errors), [])
            self.assertTrue(errors)
            self.assertIn("cannot inventory", errors[0])


if __name__ == "__main__":
    unittest.main()

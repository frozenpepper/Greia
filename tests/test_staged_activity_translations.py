"""Staged multilingual Activity copy: key parity without false voice claims.

These locale bundles are intentionally not advertised in activity.toml
while mandatory title WAVs and remaining dialog/visual acceptance are missing.
"""
from __future__ import annotations

from pathlib import Path
from string import Formatter
import json
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGED = (
    "painting", "writing", "shape_garden", "piccola_serra",
    "memory_meraviglie", "clinica_cuccioli",
)


def _fields(text: str) -> set[str]:
    return {
        name for _, name, _, _ in Formatter().parse(text)
        if name is not None
    }


class StagedActivityTranslationTests(unittest.TestCase):
    def test_staged_bundles_have_same_keys_and_placeholders_as_source(self) -> None:
        for activity in STAGED:
            root = ROOT / "activities" / activity
            english = json.loads((root / "locales/en.json").read_text(encoding="utf-8"))
            italian = json.loads((root / "locales/it.json").read_text(encoding="utf-8"))
            for locale in ("es", "fr"):
                with self.subTest(activity=activity, locale=locale):
                    path = root / f"locales/{locale}.json"
                    localized = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(localized["schema_version"], 1)
                    self.assertEqual(localized["locale"], locale)
                    self.assertEqual(localized["direction"], "ltr")
                    self.assertEqual(set(localized["strings"]), set(english["strings"]))
                    self.assertEqual(set(localized["strings"]), set(italian["strings"]))
                    for key, value in localized["strings"].items():
                        self.assertTrue(isinstance(value, str) and value.strip())
                        self.assertEqual(
                            _fields(value), _fields(english["strings"][key]),
                            f"{activity}/{locale}/{key}: missing interpolation placeholders"
                        )
                    self.assertEqual(localized["audio"], {})

    def test_translation_stage_does_not_falsely_advertise_speech(self) -> None:
        for activity in STAGED:
            manifest = tomllib.loads(
                (ROOT / "activities" / activity / "activity.toml").read_text(encoding="utf-8")
            )
            declared = manifest["activity"]["languages"]
            self.assertEqual(set(declared), {"en", "it"},
                             f"{activity}: do not claim ES/FR before voice acceptance")

    def test_staging_does_not_duplicate_english_copy_for_all_strings(self) -> None:
        for activity in STAGED:
            english = json.loads(
                (ROOT / "activities" / activity / "locales/en.json").read_text(encoding="utf-8")
            )["strings"]
            for locale in ("es", "fr"):
                translated = json.loads(
                    (ROOT / "activities" / activity / "locales" / f"{locale}.json").read_text(
                        encoding="utf-8"
                    )
                )["strings"]
                # Grid dimensions and international emoji are not translated,
                # but at least one actual UI phrase must be distinct.
                self.assertTrue(
                    any(translated[key] != value for key, value in english.items()),
                    f"{activity}/{locale} appears copied wholesale from English"
                )


if __name__ == "__main__":
    unittest.main()

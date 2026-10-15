"""Child-facing text consistency for the creative/play Activities audited in batch 3.

Source-level contract (no hardware/runtime claim): bundle strings are stored in
natural case so ADR 0034 (CAPITALS by default, profile normal-case option) can
apply through ``LocalizedResources.text``; locale bundles keep key parity; the
manifest title key always resolves; and Posta di Leo wraps child-authored text
inside its card instead of running under the stamp picker.
"""

from __future__ import annotations

import json
import os
import sys
import tomllib
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src",):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

AUDITED = (
    "officina_dei_suoni", "painting", "piccola_serra", "posta_di_leo",
    "quattro_amici", "sottomarino_giramondo", "specchi_magici",
    "stelle_incantate", "teatrino_fiabe", "treno_numeri", "viaggio_delfino",
    "workshop_settings", "writing", "faccine_momo", "storie_della_mia_voce",
    "orchestra_animali",
)
LANGUAGES = ("en", "it", "es", "fr")


def _bundle(activity: str, language: str) -> dict:
    path = ROOT / "activities" / activity / "locales" / f"{language}.json"
    return json.loads(path.read_text(encoding="utf-8"))


class BundleCaseAndTitleTests(unittest.TestCase):
    def test_bundle_strings_are_not_hand_uppercased(self) -> None:
        for activity in AUDITED:
            for language in LANGUAGES:
                for key, value in _bundle(activity, language)["strings"].items():
                    letters = [c for c in value if c.isalpha()]
                    if len(letters) < 3:
                        continue
                    with self.subTest(activity=activity, language=language, key=key):
                        self.assertNotEqual(
                            value, value.upper(),
                            "store natural case; ADR 0034 applies CAPITALS at render time",
                        )

    def test_manifest_title_key_resolves_in_every_bundle(self) -> None:
        for activity in AUDITED:
            manifest = tomllib.loads(
                (ROOT / "activities" / activity / "activity.toml").read_text(encoding="utf-8")
            )
            title_key = manifest["activity"]["title_key"]
            for language in LANGUAGES:
                strings = _bundle(activity, language)["strings"]
                with self.subTest(activity=activity, language=language):
                    self.assertTrue(
                        title_key in strings or "activity.title" in strings,
                        f"{title_key} has no title string",
                    )

    def test_teatrino_uses_standard_schema_in_all_four_languages(self) -> None:
        reference = _bundle("teatrino_fiabe", "en")
        for language in LANGUAGES:
            data = _bundle("teatrino_fiabe", language)
            with self.subTest(language=language):
                self.assertEqual(data["schema_version"], 1)
                self.assertEqual(set(data["strings"]), set(reference["strings"]))
                for legacy in ("ui", "puppets", "backdrops", "activity"):
                    self.assertNotIn(legacy, data)
        self.assertNotEqual(reference["strings"]["activity.title"], "Teatrino Fiabe")


class PostcardWrapTests(unittest.TestCase):
    def test_long_message_wraps_inside_the_message_lane(self) -> None:
        import pygame

        sys.path.insert(0, str(ROOT / "activities" / "posta_di_leo"))
        try:
            pygame.init()
            pygame.display.set_mode((64, 64))
            from greia_platform.typography import FontRole, GreiaTypography
            import postcard_renderer

            typography = GreiaTypography()
            renderer = postcard_renderer.PostcardRenderer.__new__(postcard_renderer.PostcardRenderer)
            renderer._typography = typography
            renderer._wrap_key = None
            renderer._wrap_value = ()
            text = "Ciao Leo! Oggi ho visto un arcobaleno enorme sopra la casa di nonna e poi abbiamo mangiato la torta"
            spans = renderer._wrapped_spans(text, FontRole.DISPLAY, 32, postcard_renderer.MESSAGE_LANE_WIDTH)
            self.assertGreater(len(spans), 1)
            self.assertEqual(spans[0][0], 0)
            self.assertEqual(spans[-1][1], len(text))
            for (_, previous_end), (start, _) in zip(spans, spans[1:]):
                self.assertEqual(previous_end, start)
            for start, end in spans:
                width = typography.measure(text[start:end].rstrip(), FontRole.DISPLAY, 32).width
                self.assertLessEqual(width, postcard_renderer.MESSAGE_LANE_WIDTH)
            self.assertLessEqual(len(spans), postcard_renderer.MAX_MESSAGE_LINES)
        finally:
            sys.path.remove(str(ROOT / "activities" / "posta_di_leo"))
            pygame.quit()


if __name__ == "__main__":
    unittest.main()

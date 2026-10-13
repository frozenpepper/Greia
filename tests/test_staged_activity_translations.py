"""Staged multilingual Activity copy: key parity without false voice claims.

These locale bundles are intentionally not advertised in activity.toml
while mandatory title WAVs and remaining dialog/visual acceptance are missing.
"""
from __future__ import annotations

from pathlib import Path
from string import Formatter
import ast
import json
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGED = (
    "painting", "writing", "shape_garden", "piccola_serra",
    "memory_meraviglie", "clinica_cuccioli", "acquario_magico",
    "torre_forme", "volo_draghetto", "colline_allegre",
    "quattro_stagioni", "corsa_bacche", "bottega_delle_misure",
    "bosco_numeri", "il_giardino_dei_numeri", "faccine_momo",
    "luci_di_momo", "costruiamo_ponti", "casa_del_dieci",
    "workshop_settings", "specchi_magici", "nascondino_bosco",
    "nanna_delle_nuvolette", "orchestra_animali", "treno_numeri",
    "quattro_amici", "pasticceria_magica",
    "baia_delle_orche", "cucciolo_mio", "la_discesa_della_biglia",
    "labirinto_magico", "mondo_contrari", "morbidi_mostriciattoli",
    "posta_di_leo", "stelle_incantate", "storie_della_mia_voce",
    "teatrino_fiabe", "viaggio_delfino",
)

# These five have translated *instructions*, not adapted reading curricula.
# The Word Forest deliberately omits its English-specific spelling and
# phonics example keys rather than pretending they match Spanish/French
# letters, phonemes, or valid playable target words.
CURRICULUM_UI_ONLY = (
    "alfabeto_leo", "festa_delle_rime", "officina_dei_suoni",
    "sillabe_magiche", "foresta_parole",
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

    def test_curriculum_ui_translations_do_not_claim_lesson_adaptation(self) -> None:
        for activity in CURRICULUM_UI_ONLY:
            base = ROOT / "activities" / activity
            source = json.loads((base / "locales/en.json").read_text(encoding="utf-8"))
            manifest = tomllib.loads((base / "activity.toml").read_text(encoding="utf-8"))
            self.assertEqual(set(manifest["activity"]["languages"]), {"en", "it"})
            for locale in ("es", "fr"):
                with self.subTest(activity=activity, locale=locale):
                    bundle = json.loads((base / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
                    self.assertEqual(bundle["locale"], locale)
                    self.assertEqual(bundle["audio"], {})
                    self.assertTrue(bundle["strings"])
                    self.assertEqual(set(bundle["strings"]) - set(source["strings"]), set())
                    for key, value in bundle["strings"].items():
                        self.assertTrue(value.strip())
                        for token in ("$letter", "$word", "$score", "$stars", "$char"):
                            self.assertEqual(
                                token in value, token in source["strings"][key],
                                f"{activity}/{locale}/{key}/{token}",
                            )

    def test_word_forest_english_phonics_content_is_explicitly_untranslated(self) -> None:
        base = ROOT / "activities/foresta_parole/locales"
        english = json.loads((base / "en.json").read_text(encoding="utf-8"))["strings"]
        target_lesson_keys = {
            key for key in english if key.startswith(("word.", "phonics."))
        }
        self.assertTrue(target_lesson_keys)
        for locale in ("es", "fr"):
            ui = json.loads((base / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
            self.assertTrue(target_lesson_keys.isdisjoint(ui))
            self.assertTrue(set(ui).issubset(english))

    def test_existing_dolphin_voice_cues_use_exact_caption_keys_in_both_base_locales(self) -> None:
        base = ROOT / "activities/viaggio_delfino/locales"
        for locale in ("en", "it"):
            data = json.loads((base / f"{locale}.json").read_text(encoding="utf-8"))
            cues = {k: v for k, v in data["audio"].items() if k.endswith(".voice")}
            self.assertEqual(len(cues), 7)
            for key, value in cues.items():
                caption = key[:-6] + ".caption"
                self.assertEqual(value["caption_key"], caption)
                self.assertIn(caption, data["strings"])
                self.assertTrue(data["strings"][caption].strip())

    def test_numeric_template_targets_remain_intact(self) -> None:
        """Dollar targets are consumed by old activities, not Python format()."""
        for activity in ("bosco_numeri", "casa_del_dieci"):
            root = ROOT / "activities" / activity / "locales"
            source = json.loads((root / "en.json").read_text(encoding="utf-8"))["strings"]
            for locale in ("es", "fr"):
                text = json.loads((root / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
                for key, original in source.items():
                    for token in ("$num", "$target"):
                        if token in original:
                            self.assertIn(token, text[key], f"{activity}/{locale}/{key}")

    def test_number_train_plurals_match_reachable_count_targets(self) -> None:
        """No fabricated 'one apple' bug: the actual train generates >=2.

        Its prompt.load source string is currently dormant in the renderer.
        If station generation ever allows 1, this test must fail until
        the actual consumer and ES/FR item variants handle singular.
        """
        source = ast.parse(
            (ROOT / "activities/treno_numeri/treno_content.py").read_text(encoding="utf-8")
        )
        literals = {}
        for node in source.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id in {"ADDITION_PAIRS", "COUNT_CHOICES"}:
                    literals[node.target.id] = ast.literal_eval(node.value)
        self.assertEqual(set(literals), {"ADDITION_PAIRS", "COUNT_CHOICES"})
        targets = [sum(pair) for pair in literals["ADDITION_PAIRS"]] + list(literals["COUNT_CHOICES"])
        self.assertTrue(targets)
        self.assertGreaterEqual(min(targets), 2)
        for locale in ("en", "it", "es", "fr"):
            text = json.loads(
                (ROOT / "activities/treno_numeri/locales" / f"{locale}.json").read_text(encoding="utf-8")
            )["strings"]
            self.assertIn("{count}", text["prompt.load"])
            self.assertIn("{item}", text["prompt.load"])

    def test_dollar_variables_remain_unchanged_in_every_staged_locale(self) -> None:
        """Legacy activity strings use Template($name), not str.format()."""
        for activity in STAGED:
            base = ROOT / "activities" / activity / "locales"
            source = json.loads((base / "en.json").read_text(encoding="utf-8"))["strings"]
            for locale in ("es", "fr"):
                translated = json.loads((base / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
                for key, original in source.items():
                    for token in ("$num", "$target", "$word", "$letter", "$score", "$stars", "$count"):
                        if token in original:
                            self.assertIn(token, translated[key], f"{activity}/{locale}/{key}")

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

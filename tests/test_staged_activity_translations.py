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
    "teatrino_fiabe", "viaggio_delfino", "sottomarino_giramondo",
)

# These five have translated *instructions*, not adapted reading curricula.
# The Word Forest deliberately omits its English-specific spelling and
# phonics example keys rather than pretending they match Spanish/French
# letters, phonemes, or valid playable target words.
CURRICULUM_UI_ONLY = (
    "alfabeto_leo", "festa_delle_rime", "officina_dei_suoni",
    "sillabe_magiche", "foresta_parole",
)

ENCYCLOPEDIA_PARTIAL = "enciclopedia_greia"


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

    def test_submarine_orders_and_spoken_aliases_have_consistent_translation(self) -> None:
        package = ROOT / "activities/sottomarino_giramondo/locales"
        reference = json.loads((package / "en.json").read_text(encoding="utf-8"))
        self.assertEqual(len(reference["audio"]), 55)
        for locale in ("es", "fr"):
            strings = json.loads((package / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
            for direction in ("ahead", "stop", "left", "right", "compliment"):
                self.assertEqual(
                    strings[f"order.{direction}"], strings[f"voice.order.{direction}"],
                    f"{locale}: spoken instruction and on-screen instruction disagree"
                )
            for kind in ("coral", "kelp", "krill"):
                self.assertEqual(
                    strings[f"voice.creature.{kind}"],
                    strings[f"voice.creature_{kind}"],
                    f"{locale}: old and new voice cue aliases disagree",
                )
            for creature in ("whale", "turtle", "dolphin", "manta",
                             "clownfish", "coral", "kelp", "krill"):
                for number in range(1, 5):
                    self.assertTrue(strings[f"voice.fact.{creature}.{number}"].strip())
            # Source audio contains explicit button/encounter cues whose
            # approved recordings/transcripts still need manual extraction.
            self.assertIn("voice.btn.light", reference["audio"])
            self.assertNotIn("voice.btn.light", strings)

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

    def test_all_built_in_activities_are_accounted_for_by_source_stage(self) -> None:
        actual = {
            path.name for path in (ROOT / "activities").iterdir()
            if path.is_dir() and (path / "activity.toml").is_file()
        }
        registered = set(STAGED) | set(CURRICULUM_UI_ONLY) | {ENCYCLOPEDIA_PARTIAL}
        self.assertEqual(actual, registered)
        self.assertTrue(set(STAGED).isdisjoint(CURRICULUM_UI_ONLY))
        self.assertEqual(len(actual), 45)

    def test_encyclopedia_partial_animals_and_navigation_does_not_claim_science_audio(self) -> None:
        base = ROOT / "activities/enciclopedia_greia"
        en = json.loads((base / "locales/en.json").read_text(encoding="utf-8"))
        it = json.loads((base / "locales/it.json").read_text(encoding="utf-8"))
        self.assertEqual(len(en["strings"]), 246)
        self.assertEqual(len(en["audio"]), 200)
        manifest = tomllib.loads((base / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["activity"]["languages"]), {"en", "it"})
        for locale in ("es", "fr"):
            with self.subTest(locale=locale):
                staged = json.loads((base / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
                strings = staged["strings"]
                self.assertEqual(staged["audio"], {})
                self.assertEqual(len(strings), 51)
                self.assertEqual(len(set(en["strings"]) - set(strings)), 195)
                self.assertTrue(set(strings).issubset(en["strings"]))
                self.assertTrue(set(strings).issubset(it["strings"]))
                for animal in ("lion", "elephant", "octopus", "bee", "penguin", "frog"):
                    for suffix in ("title", "intro"):
                        self.assertTrue(strings[f"{animal}.{suffix}"].strip())
                self.assertTrue(strings["home.title"].strip())
                self.assertTrue(strings["section.animals"].strip())

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

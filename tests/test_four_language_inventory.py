"""Provider-free source-inventory regression for four-language rollout."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.audit_greia_language_coverage import build_inventory, write_recording_ledger
from tools.audit_launcher_spoken_labels import _load_collection_ids


class FourLanguageInventoryTests(unittest.TestCase):
    def test_launcher_audit_includes_my_creations_even_if_clip_missing(self) -> None:
        self.assertIn("my_creations", _load_collection_ids())

    def test_audio_and_string_gaps_are_distinct_and_source_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            activity = root / "activities" / "fictional"
            (activity / "locales").mkdir(parents=True)
            (activity / "activity.toml").write_text(
                '[activity]\nname = "fictional"\n', encoding="utf-8"
            )
            (activity / "main.py").write_text(
                'audio.play_voice("hello")\n', encoding="utf-8"
            )
            for locale in ("en", "it"):
                (activity / "locales" / f"{locale}.json").write_text(
                    json.dumps({
                        "schema_version": 1, "locale": locale,
                        "strings": {
                            "activity.title": "A hello",
                            "instruction.hello": "Hello!",
                        },
                        "audio": {
                            "activity.title": {
                                "path": f"locales/{locale}/audio/title.wav",
                                "caption_key": "activity.title",
                            },
                            "instruction.hello": {
                                "path": f"locales/{locale}/audio/hello.ogg",
                                "caption_key": "instruction.hello",
                            },
                        },
                    }),
                    encoding="utf-8",
                )
            existing = activity / "locales" / "en" / "audio"
            existing.mkdir(parents=True)
            (existing / "title.wav").write_bytes(b"fixture")
            report = build_inventory(root)
            self.assertEqual(report["structural_errors"], [])
            entry = report["activities"]["fictional"]
            self.assertTrue(entry["locale_text"]["en"]["bundle_exists"])
            self.assertFalse(entry["locale_text"]["es"]["bundle_exists"])
            self.assertIn("instruction.hello",
                          entry["locale_text"]["es"]["missing_reference_keys"])
            self.assertIn("activities/fictional/main.py",
                          entry["audio_modules_to_review"])
            candidates = {
                (x["locale"], x["cue_id"]): x
                for x in report["spoken_resources"]
            }
            self.assertTrue(candidates[("en", "activity.title")]["file_exists"])
            self.assertEqual(candidates[("en", "instruction.hello")]["state"],
                             "MISSING_AUDIO")
            self.assertEqual(candidates[("es", "activity.title")]["state"],
                             "BLOCKED_TEXT")
            self.assertIsNone(candidates[("es", "activity.title")]["path"])
            self.assertEqual(report["summary"]["fr"]["activity_bundles"], 0)

    def test_text_stage_does_not_claim_product_language_support(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "activities" / "little_game"
            (package / "locales").mkdir(parents=True)
            (package / "activity.toml").write_text(
                '[activity]\nlanguages = ["en", "it"]\n', encoding="utf-8"
            )
            for locale, strings in {
                "en": {"activity.title": "Little Game", "btn.go": "Go"},
                "it": {"activity.title": "Gioco", "btn.go": "Vai"},
                "es": {"activity.title": "Juego", "btn.go": "Ir"},
                "fr": {"activity.title": "Jeu"},
            }.items():
                (package / "locales" / f"{locale}.json").write_text(
                    json.dumps({"locale": locale, "strings": strings, "audio": {}}),
                    encoding="utf-8",
                )
            report = build_inventory(root)
            self.assertEqual(report["structural_errors"], [])
            entry = report["activities"]["little_game"]
            self.assertEqual(entry["advertised_languages"], ["en", "it"])
            self.assertEqual(entry["locale_text"]["es"]["stage"], "SOURCE_TEXT_KEYS_ONLY")
            self.assertFalse(entry["locale_text"]["es"]["advertised_by_manifest"])
            self.assertEqual(entry["locale_text"]["fr"]["stage"], "INCOMPLETE_TEXT_KEYS")
            self.assertFalse(entry["locale_text"]["fr"]["advertised_by_manifest"])
            self.assertEqual(report["summary"]["es"]["text_key_complete_bundles"], 1)
            self.assertEqual(report["summary"]["es"]["advertised_activity_locales"], 0)

    def test_missing_platform_portal_is_inventoried_without_wav_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "activities" / "fake" / "locales").mkdir(parents=True)
            (root / "activities" / "fake" / "activity.toml").write_text(
                "[activity]\n", encoding="utf-8"
            )
            catalogue = root / "src" / "greia_launcher"
            catalogue.mkdir(parents=True)
            (catalogue / "catalogue_view.py").write_text(
                'BROWSE_ACTIVITIES_ID = "browse"\n'
                'MY_CREATIONS_PORTAL_ID = "my_creations"\n'
                'PRIMARY_COLLECTION_IDS = ("create", "play")\n'
                'DISCOVERY_GROUP_IDS = ("drawing",)\n',
                encoding="utf-8",
            )
            report = build_inventory(root)
            self.assertEqual(report["structural_errors"], [])
            matches = [
                x for x in report["spoken_resources"]
                if x["cue_id"] == "collection.my_creations"
            ]
            self.assertEqual(len(matches), 4)
            self.assertTrue(all(not x["file_exists"] for x in matches))
            self.assertTrue(all(x["state"] == "BLOCKED_TEXT" for x in matches))

    def test_recording_ledger_uses_package_paths_and_no_fake_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            activity = root / "activities" / "mini"
            (activity / "locales" / "en" / "audio").mkdir(parents=True)
            (activity / "activity.toml").write_text("[activity]\n", encoding="utf-8")
            (activity / "locales" / "en" / "audio" / "activity-title.wav").write_bytes(b"known clip")
            for locale in ("en", "it", "es", "fr"):
                (activity / "locales" / f"{locale}.json").write_text(json.dumps({
                    "locale": locale,
                    "strings": {"activity.title": {
                        "en": "Little Game", "it": "Gioco", "es": "Juego", "fr": "Jeu"
                    }[locale]},
                    "audio": {"activity.title": {
                        "path": f"locales/{locale}/audio/activity-title.wav",
                        "caption_key": "activity.title"
                    }} if locale == "en" else {},
                }), encoding="utf-8")
            report = build_inventory(root)
            output = root / "tmp" / "recording-ledger.csv"
            count = write_recording_ledger(root, report, output)
            with output.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(count, len(rows))
            title = {(x["locale"], x["cue_id"]): x for x in rows}
            en = title[("en", "activity.title")]
            self.assertEqual(en["state"], "EXISTING_REVIEW_PENDING")
            self.assertEqual(en["existing_asset_sha256"],
                             hashlib.sha256(b"known clip").hexdigest())
            self.assertEqual(en["output_path"],
                             "activities/mini/locales/en/audio/activity-title.wav")
            self.assertNotEqual(en["state"], "EXISTING_ACCEPTED")
            es = title[("es", "activity.title")]
            self.assertEqual(es["state"], "MISSING_AUDIO")
            self.assertEqual(es["exact_text"], "Juego")
            self.assertEqual(es["speaker"], "UNASSIGNED")
            self.assertEqual(es["output_path"],
                             "activities/mini/locales/es/audio/activity-title.wav")

    def test_launcher_spoken_text_comes_from_real_source_dictionary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "activities" / "mini").mkdir(parents=True)
            (root / "activities" / "mini" / "activity.toml").write_text(
                "[activity]\n", encoding="utf-8"
            )
            source = root / "src" / "greia_launcher"
            source.mkdir(parents=True)
            (source / "catalogue_view.py").write_text(
                'BROWSE_ACTIVITIES_ID = "browse"\n'
                'MY_CREATIONS_PORTAL_ID = "my_creations"\n'
                'PRIMARY_COLLECTION_IDS = ("create",)\n'
                'DISCOVERY_GROUP_IDS = ("drawing",)\n'
                '_CATEGORY_TRANSLATIONS: dict[str, dict[str, str]] = {\n'
                '    MY_CREATIONS_PORTAL_ID: {\n'
                '        "en": "My Creations", "it": "Le mie creazioni",\n'
                '        "es": "Mis creaciones", "fr": "Mes créations"},\n'
                '}\n',
                encoding="utf-8",
            )
            report = build_inventory(root)
            self.assertEqual(report["structural_errors"], [])
            candidates = [
                x for x in report["spoken_resources"]
                if x["cue_id"] == "collection.my_creations"
            ]
            self.assertEqual(
                {x["locale"]: x["text"] for x in candidates},
                {"en": "My Creations", "it": "Le mie creazioni",
                 "es": "Mis creaciones", "fr": "Mes créations"},
            )
            self.assertTrue(all(x["state"] == "MISSING_AUDIO" for x in candidates))

    def test_unsafe_audio_paths_cannot_be_reported_as_existing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            activity = root / "activities" / "unsafe"
            (activity / "locales").mkdir(parents=True)
            (activity / "activity.toml").write_text("[activity]\n", encoding="utf-8")
            (activity / "locales" / "en.json").write_text(json.dumps({
                "locale": "en", "strings": {"activity.title": "Unsafe"},
                "audio": {"activity.title": {
                    "path": "../private.wav", "caption_key": "activity.title",
                }},
            }), encoding="utf-8")
            report = build_inventory(root)
            item = next(x for x in report["spoken_resources"]
                        if x["source"] == "activities/unsafe" and x["locale"] == "en")
            self.assertFalse(item["file_exists"])
            self.assertEqual(item["state"], "MISSING_AUDIO")
            output = root / "tmp" / "unsafe-recordings.csv"
            write_recording_ledger(root, report, output)
            with output.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            row = next(
                x for x in rows if x["source"] == "activities/unsafe"
                and x["locale"] == "en"
            )
            self.assertEqual(row["state"], "PATH_REVIEW_REQUIRED")
            self.assertEqual(row["output_path"], "")



if __name__ == "__main__":
    unittest.main()

"""Provider-free source-inventory regression for four-language rollout."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.audit_greia_language_coverage import build_inventory


class FourLanguageInventoryTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

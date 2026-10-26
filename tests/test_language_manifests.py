"""Language-folder discovery and optional UI resources (no GUI/model required)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import greia_platform.system_language as language


class ManifestLanguageTests(unittest.TestCase):
    @staticmethod
    def _write(root: Path, code: str, name: str, order: int) -> None:
        folder = root / code
        folder.mkdir()
        (folder / "manifest.json").write_text(
            json.dumps({
                "schema_version": 1, "locale": code, "name": name,
                "native_name": name, "flag": "🏳️", "order": order,
                "direction": "ltr",
            }), encoding="utf-8",
        )

    def test_real_catalogue_controls_both_installer_and_os_registry(self):
        self.assertEqual(language.SUPPORTED_SYSTEM_LANGUAGES, language.load_system_languages())
        self.assertEqual(language.SUPPORTED_SYSTEM_LOCALES[0], "en")
        self.assertTrue({"en", "it", "es", "fr"}.issubset(language.SUPPORTED_SYSTEM_LOCALES))

    def test_new_language_directory_changes_catalogue_without_source_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "de", "Deutsch", 5)
            self._write(root, "en", "English", 0)
            result = language.load_system_languages(root)
            self.assertEqual([item.locale for item in result], ["en", "de"])
            self.assertEqual(result[1].native_name, "Deutsch")

    def test_language_metadata_is_bounded_and_match_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "en", "English", 0)
            self._write(root, "de", "German", 20)
            invalid = root / "de" / "manifest.json"
            data = json.loads(invalid.read_text())
            data["locale"] = "fr"
            invalid.write_text(json.dumps(data))
            with self.assertRaises(language.SystemLanguageError):
                language.load_system_languages(root)

    def test_missing_english_fails_early(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "de", "German", 20)
            with self.assertRaises(language.SystemLanguageError):
                language.load_system_languages(root)

    def test_optional_ui_catalogue_supplies_translation_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "en", "English", 0)
            ui = root / "en" / "ui.json"
            ui.write_text(json.dumps({
                "schema_version": 1,
                "installer": {"Continue": "Proceed"},
                "parent": {"parent.title": "Grown-up controls"},
            }), encoding="utf-8")
            with patch.object(language, "LANGUAGE_ROOT", root):
                language._language_ui_cached.cache_clear()
                self.assertEqual(language.language_ui("en", "installer")["Continue"], "Proceed")
                self.assertEqual(language.language_ui("en", "parent")["parent.title"], "Grown-up controls")
            language._language_ui_cached.cache_clear()

    def test_scaffolding_stages_json_without_offering_new_language(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
        from scaffold_greia_language import prepare
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            example = root / "activities" / "demo" / "locales"
            example.mkdir(parents=True)
            (example / "en.json").write_text(json.dumps({
                "schema_version": 1, "locale": "en",
                "strings": {"activity.title": "A new game"}, "audio": {"intro": {"path": "intro.wav"}},
            }), encoding="utf-8")
            created = prepare("de", root)
            self.assertEqual(len(created), 2)
            ui = json.loads((root / "src/greia_platform/languages/de/ui.json").read_text())
            self.assertIn("parent", ui)
            self.assertIn("installer", ui)
            translated = json.loads((example / "de.json").read_text())
            self.assertEqual(translated["locale"], "de")
            self.assertEqual(translated["audio"], {})
            self.assertFalse((root / "src/greia_platform/languages/de/manifest.json").exists())
            with self.assertRaises(FileExistsError):
                prepare("de", root)

    def test_bad_optional_catalogue_cannot_inject_object_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, "en", "English", 0)
            (root / "en" / "ui.json").write_text(
                json.dumps({"schema_version": 1, "parent": {"broken": ["not a string"]}}),
                encoding="utf-8",
            )
            with patch.object(language, "LANGUAGE_ROOT", root):
                language._language_ui_cached.cache_clear()
                with self.assertRaises(language.SystemLanguageError):
                    language.language_ui("en", "parent")
            language._language_ui_cached.cache_clear()


if __name__ == "__main__":
    unittest.main()

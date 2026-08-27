from __future__ import annotations

import ast
import json
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "activities" / "enciclopedia_greia"


class EncyclopediaSourceContractTests(unittest.TestCase):
    def test_manifest_is_offline_first_and_bilingual(self) -> None:
        with (ACTIVITY / "activity.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        self.assertEqual(raw["activity"]["id"], "org.greia.enciclopedia")
        self.assertEqual(raw["activity"]["languages"], ["it", "en"])
        self.assertEqual(raw["input"]["profile"], "navigation")
        self.assertNotIn("network", raw["requirements"]["required_capabilities"])
        self.assertNotIn("network", raw["requirements"]["optional_capabilities"])
        self.assertEqual(raw["permissions"]["requested"], [])

    def test_first_pass_runtime_registry_has_home_plus_six_sections(self) -> None:
        source = (ACTIVITY / "enciclopedia_catalogue.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        value = next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "IMPLEMENTED_PAGE_IDS" for target in node.targets)
        )
        ids = tuple(item.value for item in value.elts if isinstance(item, ast.Constant))
        self.assertEqual(
            ids,
            ("home", "animals", "space", "earth", "body", "machines", "history"),
        )

    def test_locales_have_matching_child_facing_keys(self) -> None:
        bundles = []
        for locale in ("it", "en"):
            bundles.append(json.loads((ACTIVITY / "locales" / f"{locale}.json").read_text(encoding="utf-8")))
        self.assertEqual(set(bundles[0]["strings"]), set(bundles[1]["strings"]))
        self.assertEqual(bundles[0]["audio"], {})
        self.assertEqual(bundles[1]["audio"], {})

    def test_no_runtime_tts_or_speech_recognition_backends(self) -> None:
        forbidden = ("speech_recognition", "pyttsx", "gtts", "whisper", "vosk")
        combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in ACTIVITY.rglob("*.py"))
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, combined)

    def test_all_python_sources_parse(self) -> None:
        for path in ACTIVITY.rglob("*.py"):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    unittest.main()

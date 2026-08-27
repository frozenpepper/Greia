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

    def test_first_pass_runtime_registry_tracks_only_real_pages(self) -> None:
        source = (ACTIVITY / "enciclopedia_catalogue.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        value = next(
            node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "IMPLEMENTED_PAGE_IDS"
                for target in node.targets
            )
        )
        ids = tuple(
            item.value
            for item in value.elts
            if isinstance(item, ast.Constant)
        )
        self.assertEqual(
            ids,
            (
                "home",
                "animals",
                "animals.octopus",
                "space",
                "space.saturn",
                "earth",
                "earth.volcano",
                "body",
                "body.heart",
                "machines",
                "machines.gears",
                "history",
                "history.fossils",
            ),
        )

    def test_locales_have_matching_child_facing_keys(self) -> None:
        bundles = []
        for locale in ("it", "en"):
            bundles.append(
                json.loads(
                    (ACTIVITY / "locales" / f"{locale}.json").read_text(
                        encoding="utf-8"
                    )
                )
            )
        self.assertEqual(set(bundles[0]["strings"]), set(bundles[1]["strings"]))
        self.assertEqual(bundles[0]["audio"], {})
        self.assertEqual(bundles[1]["audio"], {})

    def test_pilot_entries_are_research_backed(self) -> None:
        cases = {
            ROOT / "encyclopedia" / "research" / "animals" / "octopus.md": (
                "NOAA Fisheries",
                "Smithsonian Ocean",
                "Eight arms, not tentacles",
                "Three hearts",
            ),
            ROOT / "encyclopedia" / "research" / "space" / "saturn.md": (
                "NASA Science",
                "sixth planet",
                "gas giant",
                "billions of separate",
            ),
            ROOT / "encyclopedia" / "research" / "earth" / "volcano.md": (
                "U.S. Geological Survey",
                "Magma below, lava above",
                "Gas and pressure matter",
                "Ash and fragments",
            ),
            ROOT / "encyclopedia" / "research" / "body" / "heart.md": (
                "National Heart, Lung, and Blood Institute",
                "Four chambers",
                "Heartbeat and valves",
                "Faster during exercise",
            ),
            ROOT / "encyclopedia" / "research" / "machines" / "gears.md": (
                "Open University",
                "Neighbors reverse direction",
                "Size changes speed",
                "Rotary motion can become straight motion",
            ),
            ROOT / "encyclopedia" / "research" / "history" / "fossils.md": (
                "National Park Service",
                "Body and trace fossils differ",
                "Fossilization is rare",
                "Fossils tell stories about the past",
            ),
        }
        for path, required in cases.items():
            with self.subTest(page=path.stem):
                text = path.read_text(encoding="utf-8")
                for marker in required:
                    self.assertIn(marker, text)

    def test_subject_specific_pilots_do_not_leak_into_engine(self) -> None:
        engine = (ACTIVITY / "enciclopedia_engine.py").read_text(encoding="utf-8").lower()
        for subject in ("octopus", "saturn", "volcano", "heart", "gear", "fossil"):
            with self.subTest(subject=subject):
                self.assertNotIn(subject, engine)

    def test_no_runtime_tts_or_speech_recognition_backends(self) -> None:
        forbidden = ("speech_recognition", "pyttsx", "gtts", "whisper", "vosk")
        combined = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in ACTIVITY.rglob("*.py")
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, combined)

    def test_all_python_sources_parse(self) -> None:
        for path in ACTIVITY.rglob("*.py"):
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    unittest.main()

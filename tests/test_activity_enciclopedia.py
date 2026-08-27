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
                "animals.lion",
                "animals.elephant",
                "animals.octopus",
                "animals.bee",
                "animals.penguin",
                "animals.frog",
                "space",
                "space.sun",
                "space.mercury",
                "space.venus",
                "space.earth",
                "space.moon",
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

    def test_researched_entries_keep_authoring_provenance(self) -> None:
        cases = {
            ROOT / "encyclopedia" / "research" / "animals" / "lion.md": (
                "Smithsonian's National Zoo",
                "Social pride",
                "Roar",
                "Strong front body",
            ),
            ROOT / "encyclopedia" / "research" / "animals" / "elephant.md": (
                "Smithsonian's National Zoo",
                "Versatile trunk",
                "Cooling ears",
                "Social touch",
            ),
            ROOT / "encyclopedia" / "research" / "animals" / "octopus.md": (
                "NOAA Fisheries",
                "Smithsonian Ocean",
                "Eight arms, not tentacles",
                "Three hearts",
            ),
            ROOT / "encyclopedia" / "research" / "animals" / "bee.md": (
                "USDA Forest Service",
                "Flowers provide food",
                "Pollen travels",
                "Most wild bees are solitary",
            ),
            ROOT / "encyclopedia" / "research" / "animals" / "penguin.md": (
                "Australian Antarctic Program",
                "A bird built for swimming",
                "Not all ice",
                "Breeding varies by species",
            ),
            ROOT / "encyclopedia" / "research" / "animals" / "frog.md": (
                "American Museum of Natural History",
                "A common frog cycle",
                "Metamorphosis changes the body",
                "Not one universal recipe",
            ),
            ROOT / "encyclopedia" / "research" / "space" / "sun.md": (
                "NASA Science",
                "Our star",
                "Fusion powers it",
                "Different parts rotate at different speeds",
            ),
            ROOT / "encyclopedia" / "research" / "space" / "mercury.md": (
                "NASA Science",
                "Closest and smallest",
                "Fast year",
                "Polar ice",
            ),
            ROOT / "encyclopedia" / "research" / "space" / "venus.md": (
                "NASA Science",
                "Hottest planet",
                "Cloud-covered rocky surface",
                "Backward, slow rotation",
            ),
            ROOT / "encyclopedia" / "research" / "space" / "earth.md": (
                "NASA Science",
                "Rotation makes day and night",
                "A water world",
                "Tilt makes seasons",
            ),
            ROOT / "encyclopedia" / "research" / "space" / "moon.md": (
                "NASA Science",
                "Phases are changing views of sunlight",
                "The Moon really rotates",
                "Lower gravity",
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

    def test_subject_specific_pages_do_not_leak_into_engine_code(self) -> None:
        source = (ACTIVITY / "enciclopedia_engine.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        identifiers = {
            node.id.casefold()
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        }
        imported_modules = {
            node.module.casefold()
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        for subject in (
            "lion",
            "elephant",
            "octopus",
            "bee",
            "penguin",
            "frog",
            "sun",
            "mercury",
            "venus",
            "moon",
            "saturn",
            "volcano",
            "heart",
            "gears",
            "fossils",
        ):
            with self.subTest(subject=subject):
                self.assertNotIn(subject, identifiers)
                self.assertFalse(
                    any(subject in module for module in imported_modules),
                    f"engine imports subject-specific module containing {subject!r}",
                )

    def test_space_section_uses_semantic_targets_and_pre_reader_hit_radius(self) -> None:
        source = (ACTIVITY / "pages" / "space.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        assignments = {
            target.id: node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        target_ids = tuple(
            item.value
            for item in assignments["_TARGET_IDS"].elts
            if isinstance(item, ast.Constant)
        )
        self.assertEqual(
            target_ids,
            (
                "sun",
                "mercury",
                "venus",
                "earth",
                "moon",
                "mars",
                "jupiter",
                "saturn",
                "uranus",
                "neptune",
            ),
        )
        self.assertGreaterEqual(assignments["_TARGET_HIT_RADIUS"].value, 32)

    def test_repeated_text_rasterization_is_activity_bounded(self) -> None:
        source = (ACTIVITY / "enciclopedia_services.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        classes = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }
        cached = classes["CachedEncyclopediaTypography"]
        self.assertTrue(
            any(
                isinstance(base, ast.Name) and base.id == "GreiaTypography"
                for base in cached.bases
            )
        )
        assignments = {
            target.id: node.value
            for node in cached.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        self.assertEqual(assignments["MAX_TEXT_SURFACES"].value, 160)

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

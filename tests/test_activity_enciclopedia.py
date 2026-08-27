from __future__ import annotations

import ast
import json
from pathlib import Path, PurePosixPath
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "activities" / "enciclopedia_greia"
AUTHORING_CATALOGUE = ROOT / "encyclopedia" / "pages" / "catalogue.py"

SECTION_PAGE_IDS = {"home", "animals", "space", "earth", "body", "machines", "history"}
RESEARCH_TOPICS = {
    "animals": ("lion", "elephant", "octopus", "bee", "penguin", "frog"),
    "space": (
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
    "earth": ("volcano", "rain", "ocean", "tree", "rainbow"),
    "body": ("heart", "lungs", "bones", "teeth", "senses"),
    "machines": ("gears", "magnet", "bicycle", "airplane", "bridge"),
    "history": ("dinosaurs", "fossils", "mammoth", "cave_paintings", "pyramids"),
}
RESEARCH_FILES = {
    f"{category}.{topic}": ROOT / "encyclopedia" / "research" / category / f"{topic}.md"
    for category, topics in RESEARCH_TOPICS.items()
    for topic in topics
}


class EncyclopediaSourceContractTests(unittest.TestCase):
    @staticmethod
    def _assignment(tree: ast.Module, name: str) -> ast.AST:
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                return node.value
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == name
                and node.value is not None
            ):
                return node.value
        raise AssertionError(f"missing module assignment: {name}")

    @staticmethod
    def _literal_strings(node: ast.AST) -> tuple[str, ...]:
        assert isinstance(node, (ast.Tuple, ast.List))
        return tuple(
            item.value
            for item in node.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        )

    @staticmethod
    def _call_string_args(node: ast.AST, index: int) -> tuple[str, ...]:
        assert isinstance(node, (ast.Tuple, ast.List))
        values: list[str] = []
        for item in node.elts:
            if not isinstance(item, ast.Call) or len(item.args) <= index:
                continue
            value = item.args[index]
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                values.append(value.value)
        return tuple(values)

    @classmethod
    def _call_second_string_args(cls, node: ast.AST) -> tuple[str, ...]:
        return cls._call_string_args(node, 1)

    @classmethod
    def _runtime_page_ids(cls) -> tuple[str, ...]:
        tree = ast.parse(
            (ACTIVITY / "enciclopedia_catalogue.py").read_text(encoding="utf-8")
        )
        return cls._literal_strings(cls._assignment(tree, "IMPLEMENTED_PAGE_IDS"))

    @classmethod
    def _planned_page_ids(cls) -> tuple[str, ...]:
        tree = ast.parse(AUTHORING_CATALOGUE.read_text(encoding="utf-8"))
        return cls._call_string_args(cls._assignment(tree, "PLANNED_PAGES"), 0)

    def test_manifest_is_offline_first_and_bilingual(self) -> None:
        with (ACTIVITY / "activity.toml").open("rb") as handle:
            raw = tomllib.load(handle)
        self.assertEqual(raw["activity"]["id"], "org.greia.enciclopedia")
        self.assertEqual(raw["activity"]["languages"], ["it", "en"])
        self.assertEqual(raw["input"]["profile"], "navigation")
        self.assertNotIn("network", raw["requirements"]["required_capabilities"])
        self.assertNotIn("network", raw["requirements"]["optional_capabilities"])
        self.assertEqual(raw["permissions"]["requested"], [])

    def test_runtime_registry_matches_complete_authoring_v01_plan(self) -> None:
        actual = self._runtime_page_ids()
        planned = self._planned_page_ids()
        self.assertEqual(actual, planned)
        self.assertEqual(len(actual), 43)
        self.assertEqual(len(set(actual)), 43)
        self.assertEqual(set(actual).intersection(SECTION_PAGE_IDS), SECTION_PAGE_IDS)

    def test_every_implemented_factual_entry_has_research_authority(self) -> None:
        expected_factual = set(self._runtime_page_ids()) - SECTION_PAGE_IDS
        self.assertEqual(set(RESEARCH_FILES), expected_factual)

        ready_markers = (
            "**Research state:** READY FOR AUTHORING",
            "**Research status:** READY FOR AUTHORING",
            "**Research status:** READY FOR PILOT AUTHORING",
        )
        accepted_claim_markers = ("## Accepted claims", "## Accepted pilot claims")
        interaction_markers = ("## Interaction → fact mapping", "## Interaction-to-claim mapping")
        narration_markers = ("## Approved narration wording", "## Child-facing wording contract")

        for page_id, path in RESEARCH_FILES.items():
            with self.subTest(page_id=page_id):
                text = path.read_text(encoding="utf-8")
                self.assertIn(f"**Page ID:** `{page_id}`", text)
                self.assertTrue(any(marker in text for marker in ready_markers))
                self.assertTrue(any(marker in text for marker in accepted_claim_markers))
                self.assertIn("## Scope guardrails", text)
                self.assertTrue(any(marker in text for marker in interaction_markers))
                self.assertTrue(any(marker in text for marker in narration_markers))
                self.assertIn("https://", text)

    def test_high_risk_misconception_guardrails_are_preserved(self) -> None:
        cases = {
            "animals.bee": "Most wild bees are solitary",
            "animals.penguin": "Not all ice",
            "animals.frog": "Not one universal recipe",
            "space.venus": "Hottest planet",
            "space.moon": "The Moon really rotates",
            "earth.rain": "Clouds are not giant bags",
            "earth.ocean": "one connected global ocean",
            "earth.tree": "Do not say all tree roots",
            "body.lungs": "Do not describe lungs as balloons",
            "body.bones": "Do not teach the adult count of 206 bones",
            "body.teeth": "Do not imply every child has the same number",
            "body.senses": "tongue taste-map",
            "machines.magnet": "Do not say magnets attract all metals",
            "machines.bicycle": "Do not imply gears create energy",
            "machines.airplane": "Never use the false equal-transit-time explanation",
            "machines.bridge": "Do not imply one bridge type is always strongest",
            "history.dinosaurs": "Never show humans living alongside non-avian dinosaurs",
            "history.mammoth": "Never classify mammoths as dinosaurs",
            "history.cave_paintings": "Never invent a specific ritual",
            "history.pyramids": "No aliens",
        }
        for page_id, marker in cases.items():
            with self.subTest(page_id=page_id):
                self.assertIn(marker, RESEARCH_FILES[page_id].read_text(encoding="utf-8"))

    def test_locales_have_matching_strings_and_safe_audio_mappings(self) -> None:
        bundles = {
            locale: json.loads(
                (ACTIVITY / "locales" / f"{locale}.json").read_text(encoding="utf-8")
            )
            for locale in ("it", "en")
        }
        self.assertEqual(
            set(bundles["it"]["strings"]),
            set(bundles["en"]["strings"]),
        )

        for locale, bundle in bundles.items():
            audio = bundle["audio"]
            self.assertIsInstance(audio, dict)
            for cue_id, cue_spec in audio.items():
                with self.subTest(locale=locale, cue_id=cue_id):
                    self.assertTrue(cue_id.startswith("encyclopedia."))
                    self.assertIsInstance(cue_spec, dict)
                    self.assertIn("path", cue_spec)
                    self.assertTrue(set(cue_spec).issubset({"path", "caption_key"}))
                    relative_path = cue_spec["path"]
                    self.assertIsInstance(relative_path, str)
                    path = PurePosixPath(relative_path)
                    self.assertFalse(path.is_absolute())
                    self.assertNotIn("..", path.parts)
                    self.assertIn(path.suffix, {".ogg", ".wav"})
                    self.assertGreaterEqual(len(path.parts), 2)
                    self.assertEqual(path.parts[0], "assets")
                    if path.parts[:2] == ("assets", "audio"):
                        self.assertGreaterEqual(len(path.parts), 4)
                        self.assertEqual(path.parts[2], locale)
                    caption_key = cue_spec.get("caption_key")
                    if caption_key is not None:
                        self.assertIsInstance(caption_key, str)

    def test_space_section_has_no_dead_major_body_destinations(self) -> None:
        tree = ast.parse((ACTIVITY / "pages" / "space.py").read_text(encoding="utf-8"))
        expected = (
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
        )
        target_ids = self._literal_strings(self._assignment(tree, "_TARGET_IDS"))
        self.assertEqual(target_ids, expected)
        implemented = self._assignment(tree, "IMPLEMENTED_ENTRY_IDS")
        self.assertIsInstance(implemented, ast.Dict)
        implemented_ids = tuple(
            key.value for key in implemented.keys if isinstance(key, ast.Constant)
        )
        self.assertEqual(implemented_ids, expected)
        hit_radius = self._assignment(tree, "_TARGET_HIT_RADIUS")
        self.assertIsInstance(hit_radius, ast.Constant)
        self.assertGreaterEqual(hit_radius.value, 32)

    def test_section_destination_maps_resolve_only_real_pages(self) -> None:
        earth_tree = ast.parse((ACTIVITY / "pages" / "earth.py").read_text(encoding="utf-8"))
        earth_pages = self._call_second_string_args(self._assignment(earth_tree, "DESTINATIONS"))
        self.assertEqual(
            earth_pages,
            ("earth.rain", "earth.tree", "earth.rainbow", "earth.volcano", "earth.ocean"),
        )

        body_tree = ast.parse((ACTIVITY / "pages" / "body.py").read_text(encoding="utf-8"))
        body_pages = self._call_second_string_args(self._assignment(body_tree, "BODY_TARGETS"))
        self.assertEqual(
            body_pages,
            ("body.senses", "body.teeth", "body.lungs", "body.heart", "body.bones"),
        )

        machines_tree = ast.parse((ACTIVITY / "pages" / "machines.py").read_text(encoding="utf-8"))
        machines_pages = self._call_second_string_args(self._assignment(machines_tree, "MACHINE_TARGETS"))
        self.assertEqual(
            machines_pages,
            ("machines.gears", "machines.magnet", "machines.bicycle", "machines.airplane", "machines.bridge"),
        )

        history_tree = ast.parse((ACTIVITY / "pages" / "history.py").read_text(encoding="utf-8"))
        history_pages = self._call_second_string_args(self._assignment(history_tree, "MOMENTS"))
        self.assertEqual(
            history_pages,
            ("history.dinosaurs", "history.fossils", "history.mammoth", "history.cave_paintings", "history.pyramids"),
        )

        mapped = earth_pages + body_pages + machines_pages + history_pages
        self.assertTrue(set(mapped).issubset(self._runtime_page_ids()))

    def test_subject_specific_pages_do_not_leak_into_engine_code(self) -> None:
        source = (ACTIVITY / "enciclopedia_engine.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        identifiers = {node.id.casefold() for node in ast.walk(tree) if isinstance(node, ast.Name)}
        imported_modules = {
            node.module.casefold()
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        subject_tokens = {
            page_id.rsplit(".", 1)[-1]
            for page_id in self._runtime_page_ids()
            if page_id not in SECTION_PAGE_IDS
        }
        for subject in subject_tokens:
            with self.subTest(subject=subject):
                self.assertNotIn(subject, identifiers)
                self.assertFalse(
                    any(subject in module for module in imported_modules),
                    f"engine imports subject-specific module containing {subject!r}",
                )

    def test_repeated_text_rasterization_is_activity_bounded(self) -> None:
        source = (ACTIVITY / "enciclopedia_services.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
        cached = classes["CachedEncyclopediaTypography"]
        self.assertTrue(
            any(isinstance(base, ast.Name) and base.id == "GreiaTypography" for base in cached.bases)
        )
        assignments = {
            target.id: node.value
            for node in cached.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        self.assertEqual(assignments["MAX_TEXT_SURFACES"].value, 160)

    def test_page_hot_paths_do_not_decode_or_smoothscale_assets(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in (ACTIVITY / "pages").glob("*.py")
        )
        self.assertNotIn("pygame.image.load(", combined)
        self.assertNotIn("pygame.transform.smoothscale(", combined)
        self.assertNotIn("pygame.font.Font(", combined)
        self.assertNotIn("pygame.font.SysFont(", combined)

    def test_no_runtime_tts_speech_recognition_or_ai_backends(self) -> None:
        forbidden = (
            "speech_recognition",
            "pyttsx",
            "gtts",
            "whisper",
            "vosk",
            "openai",
            "anthropic",
            "requests.get(",
            "urllib.request",
        )
        combined = "\n".join(
            path.read_text(encoding="utf-8").lower() for path in ACTIVITY.rglob("*.py")
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

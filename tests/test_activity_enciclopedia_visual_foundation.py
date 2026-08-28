from __future__ import annotations

import ast
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = ROOT / "activities" / "enciclopedia_greia"
SOURCE = ACTIVITY / "assets" / "source"
RUNTIME = ACTIVITY / "assets" / "runtime"
BUILD_TOOL = ROOT / "tools" / "build_encyclopedia_visual_assets.py"

EXPECTED_STEMS = {
    "home_discovery_book",
    "animals_field_table",
    "lion_savanna",
    "saturn_observatory",
    "gears_workbench",
    "pyramids_diorama",
}
EXPECTED_ART = {f"{stem}.png" for stem in EXPECTED_STEMS}


class EncyclopediaVisualFoundationTests(unittest.TestCase):
    @staticmethod
    def _assignment(tree: ast.Module, name: str) -> ast.AST:
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                return node.value
        raise AssertionError(f"missing module assignment: {name}")

    @classmethod
    def _literal_assignment(cls, path: Path, name: str):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return ast.literal_eval(cls._assignment(tree, name))

    @staticmethod
    def _svg_target_centers(path: Path) -> dict[str, tuple[int, int]]:
        root = ET.parse(path).getroot()
        result: dict[str, tuple[int, int]] = {}
        for element in root.iter():
            target = element.attrib.get("data-target")
            center = element.attrib.get("data-center")
            if target is None or center is None:
                continue
            x_text, y_text = center.split(",", 1)
            result[target] = (int(x_text), int(y_text))
        return result

    def test_six_editable_golden_master_sources_exist(self) -> None:
        actual = {path.stem for path in SOURCE.glob("*.svg")}
        self.assertTrue(EXPECTED_STEMS.issubset(actual))
        for stem in EXPECTED_STEMS:
            text = (SOURCE / f"{stem}.svg").read_text(encoding="utf-8")
            with self.subTest(stem=stem):
                self.assertIn('viewBox="0 0 1024 600"', text)
                self.assertIn("<svg", text)
                self.assertGreater(len(text), 1000)

    def test_build_recipe_is_explicit_and_matches_sources(self) -> None:
        source = BUILD_TOOL.read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = ast.literal_eval(self._assignment(tree, "NAMES"))
        self.assertEqual(set(names), EXPECTED_STEMS)
        self.assertIn("cairosvg.svg2png", source)
        self.assertIn("output_width=REFERENCE_SIZE[0]", source)
        self.assertIn("output_height=REFERENCE_SIZE[1]", source)
        self.assertIn("TemporaryDirectory", source)
        self.assertIn('"--check"', source)
        self.assertIn("rebuilt.read_bytes() != committed.read_bytes()", source)

    def test_visual_library_has_hard_bound_and_explicit_art_map(self) -> None:
        source = (ACTIVITY / "enciclopedia_services.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        cls = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "VisualLibrary"
        )
        assignments = {
            target.id: node.value
            for node in cls.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        self.assertLessEqual(assignments["MAX_SURFACES"].value, 48)
        art_assets = ast.literal_eval(assignments["ART_ASSETS"])
        self.assertEqual(set(art_assets.values()), EXPECTED_ART)
        self.assertEqual(len(art_assets), len(EXPECTED_ART))
        self.assertTrue(all(name.endswith(".png") for name in art_assets.values()))

    def test_page_hot_paths_do_not_decode_or_scale_assets(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ACTIVITY / "pages").glob("*.py")
        )
        self.assertNotIn("pygame.image.load(", combined)
        self.assertNotIn("pygame.transform.smoothscale(", combined)

    def test_golden_master_pages_use_authored_scenes(self) -> None:
        cases = {
            "home.py": "encyclopedia.home.discovery_book",
            "animals.py": "encyclopedia.animals.field_table",
            "lion.py": "encyclopedia.animals.lion.savanna",
            "saturn.py": "encyclopedia.space.saturn.observatory",
            "gears.py": "encyclopedia.machines.gears.workbench",
            "pyramids.py": "encyclopedia.history.pyramids.diorama",
        }
        for filename, semantic_id in cases.items():
            text = (ACTIVITY / "pages" / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertIn("draw_authored_scene", text)
                self.assertIn(semantic_id, text)

    def test_selection_world_art_centers_match_input_semantics(self) -> None:
        home_path = ACTIVITY / "pages" / "home.py"
        home_ids = self._literal_assignment(home_path, "PORTAL_IDS")
        home_centers = self._literal_assignment(home_path, "PORTAL_CENTERS")
        self.assertEqual(
            dict(zip(home_ids, home_centers)),
            self._svg_target_centers(SOURCE / "home_discovery_book.svg"),
        )

        animals_path = ACTIVITY / "pages" / "animals.py"
        animal_centers = self._literal_assignment(animals_path, "ANIMAL_CENTERS")
        animal_ids = ("lion", "elephant", "octopus", "bee", "penguin", "frog")
        self.assertEqual(
            dict(zip(animal_ids, animal_centers)),
            self._svg_target_centers(SOURCE / "animals_field_table.svg"),
        )

    def test_runtime_pack_is_complete_if_generated(self) -> None:
        """Source stage may precede generated PNG commit; partial packs are forbidden."""

        if not RUNTIME.exists():
            return
        present = {path.name for path in RUNTIME.glob("*.png")}
        if not present:
            return
        self.assertEqual(present.intersection(EXPECTED_ART), EXPECTED_ART)
        total = 0
        for name in EXPECTED_ART:
            data = (RUNTIME / name).read_bytes()
            with self.subTest(name=name):
                self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertGreater(len(data), 1000)
                self.assertGreaterEqual(len(data), 24)
                self.assertEqual(struct.unpack(">II", data[16:24]), (1024, 600))
            total += len(data)
        self.assertLess(total, 2 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()

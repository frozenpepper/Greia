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

GOLDEN_MASTER_STEMS = {
    "home_discovery_book",
    "animals_field_table",
    "lion_savanna",
    "saturn_observatory",
    "gears_workbench",
    "pyramids_diorama",
}
SECTION_STEMS = {
    "space_gallery_observatory",
    "earth_gallery_landscape",
    "body_gallery_discovery_room",
    "machines_gallery_workbench",
    "history_gallery_time_trail",
}
EXPECTED_STEMS = GOLDEN_MASTER_STEMS | SECTION_STEMS
GOLDEN_MASTER_ART = {f"{stem}.png" for stem in GOLDEN_MASTER_STEMS}
SECTION_ART = {f"{stem}.png" for stem in SECTION_STEMS}
EXPECTED_ART = GOLDEN_MASTER_ART | SECTION_ART


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

    @classmethod
    def _dataclass_target_centers(
        cls,
        path: Path,
        assignment_name: str,
        *,
        center_arg: int,
    ) -> dict[str, tuple[int, int]]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        value = cls._assignment(tree, assignment_name)
        if not isinstance(value, (ast.Tuple, ast.List)):
            raise AssertionError(f"{assignment_name} must be a literal tuple/list")
        result: dict[str, tuple[int, int]] = {}
        for item in value.elts:
            if not isinstance(item, ast.Call):
                raise AssertionError(f"{assignment_name} items must be constructor calls")
            target_id = ast.literal_eval(item.args[0])
            center = ast.literal_eval(item.args[center_arg])
            result[str(target_id)] = (int(center[0]), int(center[1]))
        return result

    @classmethod
    def _earth_destination_centers(cls, path: Path) -> dict[str, tuple[int, int]]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        value = cls._assignment(tree, "DESTINATIONS")
        if not isinstance(value, (ast.Tuple, ast.List)):
            raise AssertionError("DESTINATIONS must be a literal tuple/list")
        result: dict[str, tuple[int, int]] = {}
        for item in value.elts:
            if not isinstance(item, ast.Call) or len(item.args) < 3:
                raise AssertionError("DESTINATIONS items must be EarthDestination calls")
            target_id = str(ast.literal_eval(item.args[0]))
            rect_call = item.args[2]
            if not isinstance(rect_call, ast.Call) or len(rect_call.args) != 4:
                raise AssertionError("EarthDestination rect must be pygame.Rect(x, y, w, h)")
            x, y, width, height = (int(ast.literal_eval(arg)) for arg in rect_call.args)
            result[target_id] = (x + width // 2, y + height // 2)
        return result

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

    @staticmethod
    def _svg_stage_bounds(path: Path, stage_id: str) -> tuple[int, int, int, int]:
        root = ET.parse(path).getroot()
        for element in root.iter():
            if element.attrib.get("data-stage") != stage_id:
                continue
            raw = element.attrib.get("data-bounds")
            if raw is None:
                raise AssertionError(f"SVG stage {stage_id!r} is missing data-bounds")
            values = tuple(int(part) for part in raw.split(","))
            if len(values) != 4:
                raise AssertionError(f"SVG stage {stage_id!r} needs x,y,width,height")
            return values
        raise AssertionError(f"missing SVG stage: {stage_id}")

    def test_editable_golden_master_and_section_sources_exist(self) -> None:
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
        golden = set(ast.literal_eval(self._assignment(tree, "GOLDEN_MASTER_NAMES")))
        sections = set(ast.literal_eval(self._assignment(tree, "SECTION_NAMES")))
        self.assertEqual(golden, GOLDEN_MASTER_STEMS)
        self.assertEqual(sections, SECTION_STEMS)
        self.assertEqual(golden | sections, EXPECTED_STEMS)
        self.assertIn("cairosvg.svg2png", source)
        self.assertIn("output_width=REFERENCE_SIZE[0]", source)
        self.assertIn("output_height=REFERENCE_SIZE[1]", source)
        self.assertIn("TemporaryDirectory", source)
        self.assertIn('"--check"', source)
        self.assertIn('choices=("all", "golden", "sections")', source)
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

    def test_e3_section_pages_use_authored_scenes_with_fallbacks(self) -> None:
        cases = {
            "space.py": "encyclopedia.space.gallery.observatory",
            "earth.py": "encyclopedia.earth.gallery.landscape",
            "body.py": "encyclopedia.body.gallery.discovery_room",
            "machines.py": "encyclopedia.machines.gallery.workbench",
            "history.py": "encyclopedia.history.gallery.time_trail",
        }
        for filename, semantic_id in cases.items():
            text = (ACTIVITY / "pages" / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertIn("draw_authored_scene", text)
                self.assertIn(semantic_id, text)
                self.assertIn("fallback", text.lower())

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

    def test_e3_static_section_art_centers_match_input_semantics(self) -> None:
        earth_centers = self._earth_destination_centers(ACTIVITY / "pages" / "earth.py")
        self.assertEqual(
            earth_centers,
            self._svg_target_centers(SOURCE / "earth_gallery_landscape.svg"),
        )

        body_centers = self._dataclass_target_centers(
            ACTIVITY / "pages" / "body.py",
            "BODY_TARGETS",
            center_arg=2,
        )
        self.assertEqual(
            body_centers,
            self._svg_target_centers(SOURCE / "body_gallery_discovery_room.svg"),
        )

        machine_centers = self._dataclass_target_centers(
            ACTIVITY / "pages" / "machines.py",
            "MACHINE_TARGETS",
            center_arg=2,
        )
        self.assertEqual(
            machine_centers,
            self._svg_target_centers(SOURCE / "machines_gallery_workbench.svg"),
        )

        history_path = ACTIVITY / "pages" / "history.py"
        history_ids = self._literal_assignment(history_path, "HISTORY_TARGET_IDS")
        history_centers = self._literal_assignment(history_path, "HISTORY_TARGET_CENTERS")
        self.assertEqual(
            dict(zip(history_ids, history_centers)),
            self._svg_target_centers(SOURCE / "history_gallery_time_trail.svg"),
        )

    def test_space_live_solar_system_stays_inside_authored_stage(self) -> None:
        space_path = ACTIVITY / "pages" / "space.py"
        tree = ast.parse(space_path.read_text(encoding="utf-8"))
        center_x, center_y = ast.literal_eval(self._assignment(tree, "SOLAR_SYSTEM_CENTER"))
        code_bounds = tuple(
            ast.literal_eval(self._assignment(tree, "SOLAR_SYSTEM_STAGE_BOUNDS"))
        )
        svg_bounds = self._svg_stage_bounds(
            SOURCE / "space_gallery_observatory.svg",
            "solar-system",
        )
        self.assertEqual(code_bounds, svg_bounds)
        stage_x, stage_y, stage_width, stage_height = code_bounds
        stage_right = stage_x + stage_width
        stage_bottom = stage_y + stage_height

        planets = self._assignment(tree, "PLANETS")
        self.assertIsInstance(planets, (ast.Tuple, ast.List))
        for item in planets.elts:
            self.assertIsInstance(item, ast.Call)
            planet_id = str(ast.literal_eval(item.args[0]))
            radius_x = int(ast.literal_eval(item.args[2]))
            radius_y = int(ast.literal_eval(item.args[3]))
            size = int(ast.literal_eval(item.args[4]))
            # Saturn's visible ring extends eight pixels beyond its disc. The
            # open-entry marker may extend ten pixels beyond a planet on x.
            visual_x_margin = max(size + 10, size + (8 if planet_id == "saturn" else 0))
            visual_y_margin = size
            with self.subTest(planet=planet_id):
                self.assertGreaterEqual(center_x - radius_x - visual_x_margin, stage_x)
                self.assertLessEqual(center_x + radius_x + visual_x_margin, stage_right)
                self.assertGreaterEqual(center_y - radius_y - visual_y_margin, stage_y)
                self.assertLessEqual(center_y + radius_y + visual_y_margin, stage_bottom)

        # The Moon orbits Earth, so its maximum excursion is Earth's orbit plus
        # the 28x14 Moon orbit and four-pixel disc.
        earth = next(
            item
            for item in planets.elts
            if str(ast.literal_eval(item.args[0])) == "earth"
        )
        earth_rx = int(ast.literal_eval(earth.args[2]))
        earth_ry = int(ast.literal_eval(earth.args[3]))
        self.assertGreaterEqual(center_x - earth_rx - 28 - 4, stage_x)
        self.assertLessEqual(center_x + earth_rx + 28 + 4, stage_right)
        self.assertGreaterEqual(center_y - earth_ry - 14 - 4, stage_y)
        self.assertLessEqual(center_y + earth_ry + 14 + 4, stage_bottom)

    def test_runtime_pack_is_complete_per_visual_tranche(self) -> None:
        """Golden art is complete; E3 section art may be absent, never partial."""

        if not RUNTIME.exists():
            return
        present = {path.name for path in RUNTIME.glob("*.png")}
        if not present:
            return

        self.assertEqual(present.intersection(GOLDEN_MASTER_ART), GOLDEN_MASTER_ART)
        section_present = present.intersection(SECTION_ART)
        self.assertIn(len(section_present), (0, len(SECTION_ART)))

        expected_present = GOLDEN_MASTER_ART | section_present
        total = 0
        for name in expected_present:
            data = (RUNTIME / name).read_bytes()
            with self.subTest(name=name):
                self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertGreater(len(data), 1000)
                self.assertGreaterEqual(len(data), 24)
                self.assertEqual(struct.unpack(">II", data[16:24]), (1024, 600))
            total += len(data)
        self.assertLess(total, 4 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()

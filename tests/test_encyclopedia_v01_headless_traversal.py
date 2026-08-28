from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image


REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / "tools"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

TOOL = TOOLS / "encyclopedia_v01_headless_traversal.py"
spec = importlib.util.spec_from_file_location(
    "encyclopedia_v01_headless_traversal_under_test",
    TOOL,
)
assert spec is not None and spec.loader is not None
traversal = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = traversal
spec.loader.exec_module(traversal)

from encyclopedia.pages.catalogue import PLANNED_PAGES  # noqa: E402


class EncyclopediaHeadlessTraversalContractTests(unittest.TestCase):
    def test_entry_plans_cover_exactly_the_frozen_36_factual_pages(self) -> None:
        plans = traversal.build_entry_plans()
        planned = tuple(page.page_id for page in PLANNED_PAGES if page.role == "entry")
        self.assertEqual(tuple(plan.page_id for plan in plans), planned)
        self.assertEqual(len(plans), 36)
        self.assertEqual(len({plan.page_id for plan in plans}), 36)

    def test_section_inventory_is_six_and_counts_match_frozen_scope(self) -> None:
        self.assertEqual(
            traversal.SECTION_ORDER,
            ("animals", "space", "earth", "body", "machines", "history"),
        )
        self.assertEqual(
            {section: len(items) for section, items in traversal.SECTION_ENTRY_ORDER.items()},
            {
                "animals": 6,
                "space": 10,
                "earth": 5,
                "body": 5,
                "machines": 5,
                "history": 5,
            },
        )

    def test_home_routes_match_the_runtime_three_column_portal_grid(self) -> None:
        self.assertEqual(traversal._section_home_route("animals"), ())
        self.assertEqual(traversal._section_home_route("space"), ("RIGHT",))
        self.assertEqual(traversal._section_home_route("earth"), ("RIGHT", "RIGHT"))
        self.assertEqual(traversal._section_home_route("body"), ("DOWN",))
        self.assertEqual(traversal._section_home_route("machines"), ("DOWN", "RIGHT"))
        self.assertEqual(
            traversal._section_home_route("history"),
            ("DOWN", "RIGHT", "RIGHT"),
        )

    def test_space_entry_routes_are_relative_to_earth_default_focus(self) -> None:
        self.assertEqual(traversal._entry_route("space", "space.sun"), ("LEFT",) * 3)
        self.assertEqual(traversal._entry_route("space", "space.mercury"), ("LEFT",) * 2)
        self.assertEqual(traversal._entry_route("space", "space.earth"), ())
        self.assertEqual(traversal._entry_route("space", "space.moon"), ("RIGHT",))
        self.assertEqual(traversal._entry_route("space", "space.neptune"), ("RIGHT",) * 6)

    def test_grid_section_routes_cover_non_rectangular_last_rows(self) -> None:
        self.assertEqual(traversal._entry_route("animals", "animals.frog"), ("DOWN", "RIGHT", "RIGHT"))
        self.assertEqual(traversal._entry_route("body", "body.bones"), ("DOWN", "DOWN"))
        self.assertEqual(traversal._entry_route("machines", "machines.bridge"), ("DOWN", "RIGHT"))

    def test_primary_interaction_is_bounded_semantic_activate_only(self) -> None:
        plans = traversal.build_entry_plans()
        self.assertTrue(plans)
        self.assertTrue(all(plan.interaction_keys == ("RETURN",) for plan in plans))
        source = TOOL.read_text(encoding="utf-8")
        # Internal page traversal must stay on the public semantic navigation
        # contract. Pointer input is reserved for the platform-owned Home return
        # inside the shared headless helper, not for finding page hotspots.
        self.assertNotIn("_bridge_click(", source)

    def test_changed_pixel_fraction_reports_identical_and_changed_frames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = root / "before.png"
            identical = root / "identical.png"
            changed = root / "changed.png"
            Image.new("RGB", (4, 4), (0, 0, 0)).save(before)
            Image.new("RGB", (4, 4), (0, 0, 0)).save(identical)
            image = Image.new("RGB", (4, 4), (0, 0, 0))
            image.putpixel((1, 2), (255, 0, 0))
            image.save(changed)

            self.assertEqual(traversal.changed_pixel_fraction(before, identical), 0.0)
            self.assertAlmostEqual(
                traversal.changed_pixel_fraction(before, changed),
                1 / 16,
            )


if __name__ == "__main__":
    unittest.main()

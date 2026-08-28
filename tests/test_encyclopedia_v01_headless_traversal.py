from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

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

    def test_post_key_frame_predicate_rejects_under_advance_and_accepts_threshold(self) -> None:
        predicate = traversal.HeadlessEncyclopediaTraversal._post_key_frame_predicate
        base = {"mode": "activity", "frame_count": 100}

        # Default one-frame behavior: +1 must be enough, +0 must not.
        self.assertTrue(predicate(base, before=99, min_frame_advance=1))
        self.assertFalse(predicate(base, before=100, min_frame_advance=1))

        # Multi-frame settle: +1 and +2 must not satisfy a three-frame requirement.
        for advance in (1, 2):
            state = {"mode": "activity", "frame_count": 100 + advance}
            self.assertFalse(
                predicate(state, before=100, min_frame_advance=3),
                f"predicate accepted +{advance} advance when min_frame_advance=3",
            )

        # +3 satisfies the three-frame requirement; +4 is also fine.
        self.assertTrue(
            predicate({"mode": "activity", "frame_count": 103}, before=100, min_frame_advance=3)
        )
        self.assertTrue(
            predicate({"mode": "activity", "frame_count": 104}, before=100, min_frame_advance=3)
        )

        # Non-activity frames must never satisfy the predicate, regardless of count.
        self.assertFalse(
            predicate({"mode": "profiles", "frame_count": 200}, before=100, min_frame_advance=1)
        )
        self.assertFalse(
            predicate({"mode": "profiles", "frame_count": 200}, before=100, min_frame_advance=3)
        )

    def test_post_key_frame_predicate_rejects_zero_or_negative_advance(self) -> None:
        predicate = traversal.HeadlessEncyclopediaTraversal._post_key_frame_predicate
        with self.assertRaises(ValueError):
            predicate({"mode": "activity", "frame_count": 5}, before=5, min_frame_advance=0)
        with self.assertRaises(ValueError):
            predicate({"mode": "activity", "frame_count": 5}, before=5, min_frame_advance=-1)

    def test_key_min_frame_advance_uses_predicate_and_dispatches_bridge(self) -> None:
        runner = traversal.HeadlessEncyclopediaTraversal(
            workspace_dir=Path(tempfile.gettempdir()) / "unused-workspace",
            evidence_dir=Path(tempfile.gettempdir()) / "unused-evidence",
            locale="it",
            viewport="1024x600",
        )
        # Fake child: only attribute _key reads through the helper chain.
        runner._child = mock.MagicMock()
        runner._child.poll.return_value = None

        with mock.patch.object(
            traversal.headless,
            "_http_get_json",
            return_value={"mode": "activity", "frame_count": 10},
        ) as state_calls, mock.patch.object(
            traversal.headless,
            "_bridge_key",
            return_value=True,
        ) as bridge_calls, mock.patch.object(
            traversal.headless,
            "_wait_for_state",
            return_value={"mode": "activity", "frame_count": 13},
        ) as wait_calls:
            returned = runner._key(
                "RETURN",
                stage="test settle",
                min_frame_advance=traversal.PAGE_CHANGE_FRAME_ADVANCE,
            )

        # Bridge received exactly the requested key.
        self.assertEqual([call.args for call in bridge_calls.call_args_list], [("RETURN",)])
        # The wait predicate used the three-frame minimum (returns +3 frame, satisfies +3).
        self.assertEqual(returned["frame_count"], 13)
        self.assertEqual(state_calls.call_count, 1)
        predicate_arg = wait_calls.call_args.args[0]
        self.assertFalse(predicate_arg({"mode": "activity", "frame_count": 11}))
        self.assertFalse(predicate_arg({"mode": "activity", "frame_count": 12}))
        self.assertTrue(predicate_arg({"mode": "activity", "frame_count": 13}))
        self.assertFalse(predicate_arg({"mode": "profiles", "frame_count": 13}))

    def test_keys_propagates_min_frame_advance(self) -> None:
        runner = traversal.HeadlessEncyclopediaTraversal(
            workspace_dir=Path(tempfile.gettempdir()) / "unused-workspace",
            evidence_dir=Path(tempfile.gettempdir()) / "unused-evidence",
            locale="it",
            viewport="1024x600",
        )
        with mock.patch.object(runner, "_key", return_value={"mode": "activity"}) as key_calls:
            runner._keys(
                ("DOWN", "RIGHT"),
                stage="settle focus",
                min_frame_advance=traversal.PAGE_CHANGE_FRAME_ADVANCE,
            )
        self.assertEqual(key_calls.call_count, 2)
        for recorded in key_calls.call_args_list:
            self.assertEqual(
                recorded.kwargs.get("min_frame_advance"),
                traversal.PAGE_CHANGE_FRAME_ADVANCE,
            )

    def test_page_change_call_sites_use_multi_frame_settle(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        # The page-changing settle contract is a single global constant. No
        # call site is allowed to silently fall back to the one-frame default
        # for any reason, and no per-page branch is allowed to add a special
        # case to the key/settle helper.
        self.assertEqual(source.count("PAGE_CHANGE_FRAME_ADVANCE = 3"), 1)
        # Four page-changing call sites (Home->section RETURN, section->entry
        # RETURN, entry->section ESCAPE, section->Home ESCAPE) must each
        # request the multi-frame settle explicitly.
        self.assertGreaterEqual(
            source.count("min_frame_advance=PAGE_CHANGE_FRAME_ADVANCE"),
            4,
        )
        # The one-frame "frame_count > before" predicate must not reappear
        # anywhere in the file: the settle contract is the only path.
        self.assertNotIn("frame_count > before", source)
        # Page-specific identifiers (Sun/Neptune) must not appear inside a
        # branch of the key/settle helper. SECTION_ENTRY_ORDER legitimately
        # contains them as child-visible nav order, so we scope the check to
        # the body of the new helper.
        helper = source.split("def _post_key_frame_predicate", 1)[1]
        self.assertNotIn('"space.sun"', helper)
        self.assertNotIn('"space.neptune"', helper)


if __name__ == "__main__":
    unittest.main()

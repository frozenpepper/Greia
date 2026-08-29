from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_TOOL = ROOT / "tools" / "build_encyclopedia_visual_assets.py"
CAPTURE_TOOL = ROOT / "tools" / "encyclopedia_v01_section_review_capture.py"
REVIEW_TOOL = ROOT / "tools" / "encyclopedia_v01_section_review.py"
EXPECTED_SECTIONS = (
    "animals",
    "space",
    "earth",
    "body",
    "machines",
    "history",
)
EXPECTED_REVIEW_TAGS = ("home", *EXPECTED_SECTIONS)
EXPECTED_RUNTIME_ART = {
    "home_discovery_book.png",
    "animals_field_table.png",
    "lion_savanna.png",
    "saturn_observatory.png",
    "gears_workbench.png",
    "pyramids_diorama.png",
    "space_gallery_observatory.png",
    "earth_gallery_landscape.png",
    "body_gallery_discovery_room.png",
    "machines_gallery_workbench.png",
    "history_gallery_time_trail.png",
}


class EncyclopediaE3ReviewToolTests(unittest.TestCase):
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

    def test_full_build_check_rejects_stale_runtime_pngs(self) -> None:
        source = BUILD_TOOL.read_text(encoding="utf-8")
        tree = ast.parse(source)
        golden = tuple(ast.literal_eval(self._assignment(tree, "GOLDEN_MASTER_NAMES")))
        sections = tuple(ast.literal_eval(self._assignment(tree, "SECTION_NAMES")))
        expected_names = {filename.removesuffix(".png") for filename in EXPECTED_RUNTIME_ART}
        self.assertEqual(set(golden + sections), expected_names)
        self.assertIn("if names == NAMES", source)
        self.assertIn("unexpected = sorted(present - expected)", source)
        self.assertIn("UNEXPECTED", source)

    def test_capture_scope_is_home_plus_exact_six_sections(self) -> None:
        tree = ast.parse(CAPTURE_TOOL.read_text(encoding="utf-8"))
        sections = tuple(ast.literal_eval(self._assignment(tree, "SECTION_ORDER")))
        shot_numbers = dict(ast.literal_eval(self._assignment(tree, "SHOT_NUMBER")))
        self.assertEqual(sections, EXPECTED_SECTIONS)
        self.assertEqual(tuple(shot_numbers), EXPECTED_REVIEW_TAGS)
        self.assertEqual(tuple(shot_numbers.values()), tuple(range(1, 8)))

    def test_capture_requires_the_complete_eleven_png_runtime_pack(self) -> None:
        source = CAPTURE_TOOL.read_text(encoding="utf-8")
        tree = ast.parse(source)
        runtime_art = set(ast.literal_eval(self._assignment(tree, "EXPECTED_RUNTIME_ART")))
        self.assertEqual(runtime_art, EXPECTED_RUNTIME_ART)
        self.assertIn("present_art != EXPECTED_RUNTIME_ART", source)
        self.assertIn("missing runtime art", source)
        self.assertIn("unexpected runtime art", source)

    def test_capture_evidence_is_bound_to_one_clean_exact_source_tree(self) -> None:
        source = CAPTURE_TOOL.read_text(encoding="utf-8")
        required_fragments = (
            '"rev-parse", "HEAD"',
            '"status", "--short", "--untracked-files=all"',
            "checkout is not clean",
            "_runtime_art_sha256()",
            '"source-sha.txt"',
            '"capture-manifest.json"',
            '"runtime_art_sha256"',
            "final_sha != source_sha",
            "final_runtime_hashes != runtime_hashes",
            'status="PASS"',
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)
        self.assertNotIn('"--untracked-files=no"', source)

    def test_capture_requires_each_runtime_png_to_match_committed_head_blob(self) -> None:
        source = CAPTURE_TOOL.read_text(encoding="utf-8")
        required_fragments = (
            "def _runtime_art_git_blobs()",
            '"rev-parse", f"HEAD:{relative}"',
            '"hash-object", relative',
            "runtime art is not committed in HEAD",
            "runtime art differs from committed HEAD blob",
            '"runtime_art_git_blobs"',
            "final_runtime_git_blobs != runtime_git_blobs",
            "committed runtime-art blobs changed while E3 evidence was being captured",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_review_builder_requires_the_same_seven_reference_pages(self) -> None:
        tree = ast.parse(REVIEW_TOOL.read_text(encoding="utf-8"))
        pages = ast.literal_eval(self._assignment(tree, "PAGES"))
        tags = tuple(row[1] for row in pages)
        filenames = tuple(row[2] for row in pages)
        self.assertEqual(tags, EXPECTED_REVIEW_TAGS)
        self.assertEqual(
            filenames,
            (
                "01-home.png",
                "02-animals.png",
                "03-space.png",
                "04-earth.png",
                "05-body.png",
                "06-machines.png",
                "07-history.png",
            ),
        )

    def test_review_builder_refuses_incomplete_or_unbound_evidence(self) -> None:
        source = REVIEW_TOOL.read_text(encoding="utf-8")
        tree = ast.parse(source)
        runtime_art = set(ast.literal_eval(self._assignment(tree, "EXPECTED_RUNTIME_ART")))
        self.assertEqual(runtime_art, EXPECTED_RUNTIME_ART)
        required_fragments = (
            'manifest.get("status") != "PASS"',
            'manifest.get("source_sha") != source_sha',
            "selected != EXPECTED_TAGS or completed != EXPECTED_TAGS",
            "set(hashes) != EXPECTED_RUNTIME_ART",
            'manifest.get("runtime_art_git_blobs")',
            "set(git_blobs) != EXPECTED_RUNTIME_ART",
            "invalid runtime-art Git blob",
            '"source-sha.txt"',
            '"capture-manifest.json"',
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)


if __name__ == "__main__":
    unittest.main()

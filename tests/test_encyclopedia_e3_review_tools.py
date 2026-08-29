from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
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


class EncyclopediaE3ReviewToolTests(unittest.TestCase):
    @staticmethod
    def _assignment(tree: ast.Module, name: str) -> ast.AST:
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                return node.value
        raise AssertionError(f"missing module assignment: {name}")

    def test_capture_scope_is_home_plus_exact_six_sections(self) -> None:
        tree = ast.parse(CAPTURE_TOOL.read_text(encoding="utf-8"))
        sections = tuple(ast.literal_eval(self._assignment(tree, "SECTION_ORDER")))
        shot_numbers = dict(ast.literal_eval(self._assignment(tree, "SHOT_NUMBER")))
        self.assertEqual(sections, EXPECTED_SECTIONS)
        self.assertEqual(tuple(shot_numbers), EXPECTED_REVIEW_TAGS)
        self.assertEqual(tuple(shot_numbers.values()), tuple(range(1, 8)))

    def test_capture_evidence_is_bound_to_one_clean_exact_source_tree(self) -> None:
        source = CAPTURE_TOOL.read_text(encoding="utf-8")
        required_fragments = (
            '"rev-parse", "HEAD"',
            '"status", "--short", "--untracked-files=no"',
            "tracked checkout is dirty",
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


if __name__ == "__main__":
    unittest.main()

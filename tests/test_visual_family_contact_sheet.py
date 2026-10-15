"""Actual visual-family sheet must use source packages, not mock brand art."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.visual_family_contact_sheet import (
    CAST, EXPRESSIONS, VisualFamilyError, collect_samples, render_sheet,
)


class VisualFamilyContactSheetTests(unittest.TestCase):
    def test_canonical_catalog_and_builtins_are_separate_families(self) -> None:
        root = Path(__file__).resolve().parents[1]
        samples = collect_samples(root)
        by_group = {group: [item for item in samples if item.group == group]
                    for group in ("CORE", "ACTIVITY", "CAST")}
        self.assertEqual(len(by_group["CORE"]), 30)
        self.assertEqual(len(by_group["ACTIVITY"]), 45)
        self.assertEqual(len(by_group["CAST"]), len(CAST) * len(EXPRESSIONS))
        self.assertTrue(all(item.source.is_file() for item in samples))

    def test_sheet_created_once_with_valid_png_and_exact_counts(self) -> None:
        from PIL import Image
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "families.png"
            counts = render_sheet(root, output)
            self.assertEqual(counts, {"core": 30, "activity": 45, "cast": 30})
            with Image.open(output) as img:
                self.assertEqual(img.format, "PNG")
                self.assertGreater(img.width, 1000)
                self.assertGreater(img.height, 1000)
            with self.assertRaisesRegex(VisualFamilyError, "already exists"):
                render_sheet(root, output)


if __name__ == "__main__":
    unittest.main()

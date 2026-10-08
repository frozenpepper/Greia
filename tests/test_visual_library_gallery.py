"""The offline visual browser reuses authoring metadata, not runtime discovery."""
from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from tools.visual_library_gallery import VisualGalleryError, render_gallery, write_gallery


class VisualLibraryGalleryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "assets" / "visual"
        source.mkdir(parents=True)
        (source / "sample.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        (self.root / "out").mkdir()

    def _item(self, **overrides: object) -> dict[str, object]:
        record = {
            "id": "nature.tree.oak",
            "library_status": "preferred",
            "source_path": "assets/visual/sample.svg",
            "collection_name": "Nature & Landscape",
            "role": "tree",
            "notes": "Child-safe tree silhouette",
        }
        record.update(overrides)
        return record

    def test_safe_source_preview_and_html_escaping(self) -> None:
        output = self.root / "out" / "gallery.html"
        page = render_gallery([
            self._item(notes='<img src=x onerror="alert(1)">'),
        ], repository=self.root, output=output)
        self.assertIn("nature.tree.oak", page)
        self.assertIn("sample.svg", page)
        self.assertNotIn('<img src=x onerror="alert(1)">', page)
        self.assertIn("&lt;img src=x", page)
        self.assertIn('data-status="preferred"', page)

    def test_traversal_missing_source_and_duplicate_identity_refused(self) -> None:
        output = self.root / "out" / "gallery.html"
        for path in ("../escape.svg", "assets/visual/not-here.svg"):
            with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                render_gallery([self._item(source_path=path)], repository=self.root, output=output)
        with self.assertRaisesRegex(VisualGalleryError, "duplicate"):
            render_gallery([self._item(), self._item()], repository=self.root, output=output)

    def test_writes_once_without_overwriting_artifacts(self) -> None:
        output = self.root / "out" / "gallery.html"
        self.assertEqual(write_gallery([self._item()], repository=self.root, output=output), output)
        self.assertTrue(output.is_file())
        with self.assertRaisesRegex(VisualGalleryError, "already exists"):
            write_gallery([self._item()], repository=self.root, output=output)


if __name__ == "__main__":
    unittest.main()

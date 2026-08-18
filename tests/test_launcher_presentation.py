from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from greia_launcher.activity_icon import ActivityIconError, package_icon_path
from greia_launcher.catalogue_view import ActivityCatalogue


def activity(activity_id: str, *categories: str) -> SimpleNamespace:
    return SimpleNamespace(activity_id=activity_id, categories=categories)


class ActivityCatalogueTests(unittest.TestCase):
    def test_all_collection_and_semantic_categories_are_stable(self) -> None:
        paint = activity("org.greia.paint", "creative", "art")
        maze = activity("org.greia.maze", "thinking")
        catalogue = ActivityCatalogue.from_activities((paint, maze))
        self.assertEqual(catalogue.category_ids, ("all", "art", "creative", "thinking"))
        self.assertEqual(catalogue.collection("all").items, (paint, maze))
        self.assertEqual(catalogue.collection("creative").items, (paint,))
        self.assertEqual(catalogue.collection("thinking").items, (maze,))

    def test_unknown_category_falls_back_to_all(self) -> None:
        catalogue = ActivityCatalogue.from_activities((activity("org.greia.paint", "creative"),))
        self.assertEqual(catalogue.nearest_category("missing"), "all")


class PackageActivityIconTests(unittest.TestCase):
    def test_activity_can_own_a_png_inside_its_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            icon = root / "assets" / "icon.png"
            icon.parent.mkdir()
            icon.write_bytes(b"not-decoded-here")
            manifest = SimpleNamespace(root=root, icon_id="package:assets/icon.png")
            self.assertEqual(package_icon_path(manifest), icon)

    def test_catalogue_icon_id_remains_backwards_compatible(self) -> None:
        manifest = SimpleNamespace(root=Path("/does/not/matter"), icon_id="paint")
        self.assertIsNone(package_icon_path(manifest))

    def test_package_icon_cannot_escape_or_use_executable_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for icon_id in (
                "package:../outside.png",
                "package:/absolute.png",
                "package:icon.py",
                "package:",
            ):
                with self.subTest(icon_id=icon_id):
                    manifest = SimpleNamespace(root=root, icon_id=icon_id)
                    with self.assertRaises(ActivityIconError):
                        package_icon_path(manifest)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from greia_launcher.activity_icon import ActivityIconError, package_icon_path
from greia_launcher.catalogue_view import ActivityCatalogue


def activity(
    activity_id: str,
    *education_categories: str,
    launcher_categories: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        activity_id=activity_id,
        categories=education_categories,
        launcher_categories=launcher_categories,
    )


def png_header(width: int, height: int) -> bytes:
    # Enough real PNG structure for the platform's dependency-free header
    # validator: signature + IHDR length/type + dimensions + remaining IHDR bytes.
    return (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x06\x00\x00\x00"
    )


class ActivityCatalogueTests(unittest.TestCase):
    def test_launcher_categories_are_separate_from_education_taxonomy(self) -> None:
        paint = activity(
            "org.greia.paint",
            "creativity",
            "fine_motor",
            launcher_categories=("create",),
        )
        maze = activity(
            "org.greia.maze",
            "geometry",
            "problem_solving",
            launcher_categories=("play", "learn"),
        )
        settings = activity(
            "org.greia.settings",
            "digital_literacy",
            launcher_categories=("my_greia",),
        )
        catalogue = ActivityCatalogue.from_activities((paint, maze, settings))
        self.assertEqual(
            catalogue.category_ids,
            ("all", "create", "play", "learn", "my_greia"),
        )
        self.assertEqual(catalogue.collection("all").items, (paint, maze, settings))
        self.assertEqual(catalogue.collection("create").items, (paint,))
        self.assertEqual(catalogue.collection("play").items, (maze,))
        self.assertEqual(catalogue.collection("learn").items, (maze,))
        self.assertNotIn("fine_motor", catalogue.category_ids)

    def test_old_package_without_presentation_categories_keeps_compatibility(self) -> None:
        old = activity("org.greia.old", "creative", "art")
        catalogue = ActivityCatalogue.from_activities((old,))
        self.assertEqual(catalogue.category_ids, ("all", "art", "creative"))

    def test_unknown_category_falls_back_to_all(self) -> None:
        catalogue = ActivityCatalogue.from_activities(
            (activity("org.greia.paint", "creative", launcher_categories=("create",)),)
        )
        self.assertEqual(catalogue.nearest_category("missing"), "all")


class PackageActivityIconTests(unittest.TestCase):
    def test_activity_can_own_a_bounded_png_inside_its_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            icon = root / "assets" / "icon.png"
            icon.parent.mkdir()
            icon.write_bytes(png_header(256, 256))
            manifest = SimpleNamespace(root=root, icon_id="package:assets/icon.png")
            self.assertEqual(package_icon_path(manifest), icon)

    def test_catalogue_icon_id_remains_backwards_compatible(self) -> None:
        manifest = SimpleNamespace(root=Path("/does/not/matter"), icon_id="paint")
        self.assertIsNone(package_icon_path(manifest))

    def test_package_icon_rejects_invalid_header_and_extreme_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            icon = root / "icon.png"
            manifest = SimpleNamespace(root=root, icon_id="package:icon.png")

            icon.write_bytes(b"not-a-png")
            with self.assertRaisesRegex(ActivityIconError, "PNG icon"):
                package_icon_path(manifest)

            icon.write_bytes(png_header(4096, 4096))
            with self.assertRaisesRegex(ActivityIconError, "dimensions"):
                package_icon_path(manifest)

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

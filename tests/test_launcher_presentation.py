from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from greia_launcher.activity_icon import ActivityIconError, package_icon_path
from greia_launcher.catalogue_view import (
    BROWSE_ACTIVITIES_ID,
    ActivityCatalogue,
)
from greia_launcher.presentation import _activity_title


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

    def test_launcher_categories_have_stable_semantic_icons(self) -> None:
        catalogue = ActivityCatalogue.from_activities(
            (
                activity("org.greia.paint", launcher_categories=("create",)),
                activity("org.greia.maze", launcher_categories=("play", "learn")),
                activity("org.greia.settings", launcher_categories=("my_greia",)),
            )
        )
        self.assertEqual(catalogue.collection("all").icon_id, "backpack")
        self.assertEqual(catalogue.collection("create").icon_id, "palette")
        self.assertEqual(catalogue.collection("play").icon_id, "puzzle_pieces")
        self.assertEqual(catalogue.collection("learn").icon_id, "book")
        self.assertEqual(catalogue.collection("my_greia").icon_id, "unicorn")

    def test_arbitrary_category_does_not_create_a_primary_home_destination(self) -> None:
        clinic = activity(
            "org.greia.clinic",
            launcher_categories=("care", "play"),
        )
        catalogue = ActivityCatalogue.from_activities((clinic,))
        self.assertEqual(catalogue.category_ids, ("all", "play"))
        self.assertEqual(
            tuple(item.collection_id for item in catalogue.home_collections),
            ("play",),
        )
        self.assertEqual(catalogue.collection("play").items, (clinic,))
        self.assertNotIn("care", catalogue.category_ids)

    def test_unknown_only_activity_uses_bounded_browse_fallback(self) -> None:
        storybook = activity(
            "org.greia.storybook",
            launcher_categories=("storybook",),
        )
        catalogue = ActivityCatalogue.from_activities((storybook,))
        self.assertEqual(catalogue.category_ids, ("all", BROWSE_ACTIVITIES_ID))
        self.assertEqual(catalogue.collection(BROWSE_ACTIVITIES_ID).items, (storybook,))
        self.assertEqual(
            tuple(item.collection_id for item in catalogue.home_collections),
            (BROWSE_ACTIVITIES_ID,),
        )

    def test_browse_contains_only_activities_without_a_primary_destination(self) -> None:
        clinic = activity(
            "org.greia.clinic",
            launcher_categories=("care", "play"),
        )
        odd = activity(
            "org.greia.odd",
            launcher_categories=("experimental",),
        )
        catalogue = ActivityCatalogue.from_activities((clinic, odd))
        self.assertEqual(catalogue.collection("play").items, (clinic,))
        self.assertEqual(catalogue.collection(BROWSE_ACTIVITIES_ID).items, (odd,))

    def test_old_package_without_presentation_categories_keeps_recoverability(self) -> None:
        old = activity("org.greia.old", "creative", "art")
        catalogue = ActivityCatalogue.from_activities((old,))
        self.assertEqual(catalogue.category_ids, ("all", BROWSE_ACTIVITIES_ID))
        self.assertEqual(catalogue.collection(BROWSE_ACTIVITIES_ID).items, (old,))
        self.assertEqual(catalogue.collection(BROWSE_ACTIVITIES_ID).icon_id, "backpack")

    def test_unknown_category_falls_back_to_all(self) -> None:
        catalogue = ActivityCatalogue.from_activities(
            (activity("org.greia.paint", "creative", launcher_categories=("create",)),)
        )
        self.assertEqual(catalogue.nearest_category("missing"), "all")

    def test_activity_title_is_always_human_readable(self) -> None:
        explicit = SimpleNamespace(
            activity_id="org.greia.painting",
            title_key="Painting",
        )
        localized_key = SimpleNamespace(
            activity_id="org.greia.shape-garden",
            title_key="activity.shape_garden.title",
        )
        self.assertEqual(_activity_title(explicit), "Painting")
        self.assertEqual(_activity_title(localized_key), "Shape Garden")


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

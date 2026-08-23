from __future__ import annotations

import unittest
from pathlib import Path

from greia_platform.activity_package_format import (
    ACTIVITY_PACKAGE_CONTAINER,
    ACTIVITY_PACKAGE_EXTENSION,
    ACTIVITY_PACKAGE_MANIFEST,
    ACTIVITY_PACKAGE_MEDIA_TYPE,
    ensure_activity_package_filename,
    is_activity_package_filename,
)


class ActivityPackageFormatTests(unittest.TestCase):
    def test_distribution_identity_is_explicit_zip_with_custom_extension(self) -> None:
        self.assertEqual(ACTIVITY_PACKAGE_EXTENSION, ".greiaactivity")
        self.assertEqual(ACTIVITY_PACKAGE_MEDIA_TYPE, "application/vnd.greia.activity+zip")
        self.assertEqual(ACTIVITY_PACKAGE_CONTAINER, "zip")
        self.assertEqual(ACTIVITY_PACKAGE_MANIFEST, "activity.toml")

    def test_file_picker_name_match_is_case_insensitive_and_extension_specific(self) -> None:
        self.assertTrue(is_activity_package_filename("drawing.greiaactivity"))
        self.assertTrue(is_activity_package_filename(Path("DRAWING.GREIAACTIVITY")))
        self.assertFalse(is_activity_package_filename("drawing.zip"))
        self.assertFalse(is_activity_package_filename("drawing.greiaactivity.zip"))

    def test_authoring_output_helper_replaces_zip_or_appends_extension(self) -> None:
        self.assertEqual(
            ensure_activity_package_filename("drawing.zip"),
            Path("drawing.greiaactivity"),
        )
        self.assertEqual(
            ensure_activity_package_filename("drawing"),
            Path("drawing.greiaactivity"),
        )
        self.assertEqual(
            ensure_activity_package_filename("drawing.greiaactivity"),
            Path("drawing.greiaactivity"),
        )


if __name__ == "__main__":
    unittest.main()

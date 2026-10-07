"""Release Activity staging copies only the declared, validated subset."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from greia_platform.activity_release import ReleaseSelectionError
from tools.stage_release_activities import stage_release_activities


PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT / "runtime" / "child-runtime.toml"


def _selection(path: Path, *, status: str, entries: list[tuple[str, str]]) -> Path:
    lines = [
        "schema_version = 1",
        "",
        "[release]",
        'id = "greia.test"',
        f'status = "{status}"',
    ]
    for activity_id, package in entries:
        lines += [
            "",
            "[[activities]]",
            f'activity_id = "{activity_id}"',
            f'package = "{package}"',
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


class StageReleaseActivitiesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "activities"
        self.source.mkdir()
        for package in ("painting", "writing", "shape_garden"):
            shutil.copytree(PROJECT / "activities" / package, self.source / package)

    def test_only_explicit_subset_is_staged_and_registry_validated(self):
        selection = _selection(
            self.root / "selection.toml",
            status="approved",
            entries=[
                ("org.greia.painting", "painting"),
                ("org.greia.writing", "writing"),
            ],
        )
        output = self.root / "staged"
        release_id, ids = stage_release_activities(
            selection_path=selection,
            activities_root=self.source,
            runtime_path=RUNTIME,
            output_root=output,
            allow_draft=False,
        )
        self.assertEqual(release_id, "greia.test")
        self.assertEqual(ids, ("org.greia.painting", "org.greia.writing"))
        self.assertEqual(
            sorted(path.name for path in output.iterdir()),
            ["painting", "writing"],
        )
        self.assertFalse((output / "shape_garden").exists())

    def test_expected_id_mismatch_fails_without_publishing_output(self):
        selection = _selection(
            self.root / "bad.toml",
            status="approved",
            entries=[("org.greia.writing", "painting")],
        )
        output = self.root / "staged"
        with self.assertRaisesRegex(ReleaseSelectionError, "identities"):
            stage_release_activities(
                selection_path=selection,
                activities_root=self.source,
                runtime_path=RUNTIME,
                output_root=output,
                allow_draft=False,
            )
        self.assertFalse(output.exists())

    def test_draft_requires_explicit_developer_override(self):
        selection = _selection(
            self.root / "draft.toml",
            status="draft",
            entries=[("org.greia.painting", "painting")],
        )
        output = self.root / "staged"
        with self.assertRaisesRegex(ReleaseSelectionError, "draft"):
            stage_release_activities(
                selection_path=selection,
                activities_root=self.source,
                runtime_path=RUNTIME,
                output_root=output,
                allow_draft=False,
            )
        self.assertFalse(output.exists())

        release_id, ids = stage_release_activities(
            selection_path=selection,
            activities_root=self.source,
            runtime_path=RUNTIME,
            output_root=output,
            allow_draft=True,
        )
        self.assertEqual((release_id, ids), ("greia.test", ("org.greia.painting",)))

    def test_selected_package_symlink_fails_without_output(self):
        selection = _selection(
            self.root / "selection.toml",
            status="approved",
            entries=[("org.greia.painting", "painting")],
        )
        source_file = self.source / "writing" / "activity.toml"
        link = self.source / "painting" / "forbidden-link"
        try:
            link.symlink_to(source_file)
        except OSError:
            self.skipTest("symlinks unavailable")
        output = self.root / "staged"
        with self.assertRaisesRegex(ReleaseSelectionError, "symlink"):
            stage_release_activities(
                selection_path=selection,
                activities_root=self.source,
                runtime_path=RUNTIME,
                output_root=output,
                allow_draft=False,
            )
        self.assertFalse(output.exists())

    def test_existing_output_is_never_merged_or_deleted(self):
        selection = _selection(
            self.root / "selection.toml",
            status="approved",
            entries=[("org.greia.painting", "painting")],
        )
        output = self.root / "staged"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseSelectionError, "already exists"):
            stage_release_activities(
                selection_path=selection,
                activities_root=self.source,
                runtime_path=RUNTIME,
                output_root=output,
                allow_draft=False,
            )
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()

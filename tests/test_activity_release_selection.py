"""First-party release selection policy is explicit, deterministic and fail closed."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.activity_release import (
    FirstPartyReleaseSelection,
    MANDATORY_SYSTEM_ACTIVITIES,
    ReleaseSelectionError,
    ReleaseSelectionStatus,
)


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


class ActivityReleaseSelectionTests(unittest.TestCase):
    def test_sorted_approved_subset_is_accepted(self):
        selection = FirstPartyReleaseSelection.from_dict({
            "schema_version": 1,
            "release": {"id": "greia.test", "status": "approved"},
            "activities": [
                {"activity_id": "org.greia.painting", "package": "painting"},
                {"activity_id": "org.greia.writing", "package": "writing"},
            ],
        })
        self.assertEqual(selection.status, ReleaseSelectionStatus.APPROVED)
        self.assertEqual(
            selection.activity_ids,
            ("org.greia.painting", "org.greia.writing"),
        )
        selection.require_approved()

    def test_draft_and_empty_approved_rosters_refuse_release(self):
        draft = FirstPartyReleaseSelection.from_dict({
            "schema_version": 1,
            "release": {"id": "greia.test", "status": "draft"},
            "activities": [],
        })
        with self.assertRaisesRegex(ReleaseSelectionError, "draft"):
            draft.require_approved()

        empty = FirstPartyReleaseSelection.from_dict({
            "schema_version": 1,
            "release": {"id": "greia.test", "status": "approved"},
            "activities": [],
        })
        with self.assertRaisesRegex(ReleaseSelectionError, "empty"):
            empty.require_approved()

    def test_unsorted_duplicate_or_unsafe_entries_fail(self):
        cases = [
            [
                {"activity_id": "org.greia.writing", "package": "writing"},
                {"activity_id": "org.greia.painting", "package": "painting"},
            ],
            [
                {"activity_id": "org.greia.painting", "package": "painting"},
                {"activity_id": "org.greia.painting", "package": "painting2"},
            ],
            [
                {"activity_id": "org.greia.painting", "package": "../painting"},
            ],
        ]
        for activities in cases:
            with self.subTest(activities=activities):
                with self.assertRaises(ReleaseSelectionError):
                    FirstPartyReleaseSelection.from_dict({
                        "schema_version": 1,
                        "release": {"id": "greia.test", "status": "draft"},
                        "activities": activities,
                    })

    def test_child_roster_cannot_claim_trusted_system_package(self):
        system = MANDATORY_SYSTEM_ACTIVITIES[0]
        for entry in (
            {"activity_id": system.activity_id, "package": "painting"},
            {"activity_id": "org.greia.painting", "package": system.package_relpath},
        ):
            with self.subTest(entry=entry):
                with self.assertRaisesRegex(ReleaseSelectionError, "system Activities"):
                    FirstPartyReleaseSelection.from_dict({
                        "schema_version": 1,
                        "release": {"id": "greia.test", "status": "draft"},
                        "activities": [entry],
                    })

    def test_policy_file_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            actual = _write(
                root / "actual.toml",
                'schema_version = 1\n[release]\nid = "greia.test"\nstatus = "draft"\n',
            )
            link = root / "selection.toml"
            try:
                link.symlink_to(actual)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(ReleaseSelectionError, "symlink"):
                FirstPartyReleaseSelection.load(link)


if __name__ == "__main__":
    unittest.main()

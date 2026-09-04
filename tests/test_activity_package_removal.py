from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from greia_parent.protocol import API_BASE, CAPABILITIES, RESOURCES, api_index_payload
from greia_platform.activity_packages import ActivityPackageError, ActivityPackageService


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT_ROOT / "runtime/child-runtime.toml"
PAINTING = PROJECT_ROOT / "activities/painting"


def write_activity_archive(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source).as_posix())


class ActivityPackageRemovalTests(unittest.TestCase):
    def test_uninstall_removes_parent_package_code_but_preserves_profile_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            profile_data = root / "profiles" / "greta" / "activity-data" / "org.greia.painting" / "save.json"
            profile_data.parent.mkdir(parents=True)
            profile_data.write_text('{"drawing":"kept"}\n', encoding="utf-8")

            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=RUNTIME,
                built_in_root=root / "empty-builtins",
            )
            installed = service.install_archive(archive)
            self.assertTrue((service.active_root / installed.activity_id).is_dir())

            removed = service.uninstall(installed.activity_id)

            self.assertEqual(removed.activity_id, installed.activity_id)
            self.assertTrue(removed.profile_data_preserved)
            self.assertFalse((service.active_root / installed.activity_id).exists())
            self.assertFalse((service.versions_root / installed.activity_id).exists())
            self.assertFalse(service._receipt_path(installed.activity_id).exists())
            self.assertEqual(profile_data.read_text(encoding="utf-8"), '{"drawing":"kept"}\n')

            reinstalled = service.install_archive(archive)
            self.assertEqual(reinstalled.activity_id, installed.activity_id)

    def test_uninstall_cannot_target_built_in_or_unknown_activity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=RUNTIME,
                built_in_root=PROJECT_ROOT / "activities",
            )
            with self.assertRaisesRegex(ActivityPackageError, "not a removable"):
                service.uninstall("org.greia.painting")
            self.assertTrue((PROJECT_ROOT / "activities" / "painting" / "activity.toml").is_file())

    def test_parent_protocol_declares_remove_fail_closed(self) -> None:
        self.assertFalse(CAPABILITIES["activities.remove"])
        resource = next(item for item in RESOURCES if item.name == "activity_package")
        self.assertEqual(resource.path, f"{API_BASE}/activities/{{activity_id}}")
        self.assertEqual(resource.methods, ("DELETE",))

    def test_install_override_carries_matching_remove_capability(self) -> None:
        enabled = api_index_payload({"activities.install": True})["capabilities"]
        disabled = api_index_payload({"activities.install": False})["capabilities"]
        self.assertTrue(enabled["activities.install"])
        self.assertTrue(enabled["activities.remove"])
        self.assertFalse(disabled["activities.install"])
        self.assertFalse(disabled["activities.remove"])

    def test_failed_install_leaves_no_orphan_publish_state(self) -> None:
        """2A atomic publish: a failed package leaves no residue behind.

        After a same-id install that fails validation, the previous active
        set is intact, no new immutable version directory appears, and no
        staging residue survives the transaction cleanup.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=RUNTIME,
                built_in_root=root / "empty-builtins",
            )
            installed = service.install_archive(archive)
            versions_before = {
                path.relative_to(service.versions_root)
                for path in service.versions_root.rglob("*")
            }

            bad_source = root / "bad-painting"
            import shutil

            shutil.copytree(PAINTING, bad_source, symlinks=True)
            (bad_source / "payload.run").write_bytes(b"#!/bin/sh\n")
            bad = root / "bad.greiaactivity"
            with zipfile.ZipFile(bad, "w", compression=zipfile.ZIP_DEFLATED) as package:
                for path in sorted(bad_source.rglob("*")):
                    if path.is_file():
                        package.write(path, path.relative_to(bad_source).as_posix())
            with self.assertRaisesRegex(
                ActivityPackageError, "forbidden package suffix"
            ):
                service.install_archive(bad)

            self.assertTrue(
                (service.active_root / installed.activity_id / "activity.toml").is_file()
            )
            self.assertTrue(service._receipt_path(installed.activity_id).is_file())
            self.assertEqual(
                {
                    path.relative_to(service.versions_root)
                    for path in service.versions_root.rglob("*")
                },
                versions_before,
            )
            leftovers = [
                path
                for path in service.staging_root.iterdir()
                if path.name.startswith("install-") or path.name.startswith("remove-")
            ]
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()

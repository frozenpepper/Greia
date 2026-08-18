from __future__ import annotations

import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from greia_platform.activity_packages import ActivityPackageError, ActivityPackageService
from greia_platform.trust import PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT_ROOT / "runtime/child-runtime.toml"
PAINTING = PROJECT_ROOT / "activities/painting"


def write_activity_archive(
    source: Path,
    destination: Path,
    *,
    manifest_transform: callable | None = None,
) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source).as_posix()
            if relative == "activity.toml" and manifest_transform is not None:
                text = path.read_text(encoding="utf-8")
                archive.writestr(relative, manifest_transform(text))
            else:
                archive.write(path, relative)


class ActivityPackageServiceTests(unittest.TestCase):
    def test_parent_package_installs_to_separate_atomic_active_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=RUNTIME,
                built_in_root=root / "empty-builtins",
            )
            receipt = service.install_archive(archive)

            self.assertEqual(receipt.package_trust, PackageTrust.PARENT_TRUSTED_UNSIGNED)
            self.assertEqual(receipt.source_id, service.SOURCE_ID)
            active = service.active_root / receipt.activity_id
            immutable = service.versions_root / receipt.activity_id / receipt.package_digest
            self.assertTrue((active / "activity.toml").is_file())
            self.assertTrue((immutable / "activity.toml").is_file())
            self.assertEqual(
                (active / "activity.toml").read_bytes(),
                (immutable / "activity.toml").read_bytes(),
            )
            self.assertEqual(
                os.stat(active / "activity.toml").st_ino,
                os.stat(immutable / "activity.toml").st_ino,
            )
            self.assertFalse(os.stat(active / "activity.toml").st_mode & 0o222)
            self.assertTrue(
                (service.receipts_root / f"{receipt.activity_id}.json").is_file()
            )

            with self.assertRaisesRegex(ActivityPackageError, "already installed"):
                service.install_archive(archive)

    def test_receipt_failure_cannot_publish_executable_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=RUNTIME,
                built_in_root=root / "empty-builtins",
            )
            with mock.patch.object(
                service,
                "_write_receipt",
                side_effect=OSError("disk full"),
            ):
                with self.assertRaises(ActivityPackageError):
                    service.install_archive(archive)
            self.assertEqual(tuple(service.active_root.iterdir()), ())

    def test_interrupted_immutable_version_is_reused_after_digest_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=RUNTIME,
                built_in_root=root / "empty-builtins",
            )
            first = service.install_archive(archive)
            active = service.active_root / first.activity_id
            # Simulate a safe pre-commit/crash residue by making the active path
            # absent while retaining the immutable version and audit metadata.
            active.rename(root / "detached-active")
            service._receipt_path(first.activity_id).unlink()

            second = service.install_archive(archive)
            self.assertEqual(second.package_digest, first.package_digest)
            self.assertTrue((service.active_root / first.activity_id / "activity.toml").is_file())

    def test_package_identity_cannot_collide_with_built_in_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=RUNTIME,
                built_in_root=PROJECT_ROOT / "activities",
            )
            with self.assertRaises(ActivityPackageError):
                service.install_archive(archive)
            self.assertFalse(any(service.active_root.iterdir()))

    def test_missing_package_owned_icon_is_rejected_before_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "bad-icon.greiaactivity"
            write_activity_archive(
                PAINTING,
                archive,
                manifest_transform=lambda text: text.replace(
                    'icon = "palette"',
                    'icon = "package:assets/missing.png"',
                ),
            )
            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=RUNTIME,
                built_in_root=root / "empty-builtins",
            )
            with self.assertRaisesRegex(ActivityPackageError, "icon"):
                service.install_archive(archive)
            self.assertFalse(any(service.active_root.iterdir()))

    def test_archive_path_escape_is_rejected_before_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "escape.greiaactivity"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("../escape.txt", "bad")
                package.writestr("activity.toml", "bad")
            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=RUNTIME,
                built_in_root=root / "empty-builtins",
            )
            with self.assertRaisesRegex(ActivityPackageError, "escapes archive root"):
                service.install_archive(archive)
            self.assertFalse((root / "escape.txt").exists())
            self.assertFalse(any(service.active_root.iterdir()))

    def test_archive_requires_manifest_at_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "nested.greiaactivity"
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("nested/activity.toml", "[activity]\nid='x'\n")
            service = ActivityPackageService(
                state_root=root / "packages",
                runtime_catalogue=RUNTIME,
                built_in_root=root / "empty-builtins",
            )
            with self.assertRaisesRegex(ActivityPackageError, "archive root"):
                service.install_archive(archive)
            self.assertFalse(any(service.active_root.iterdir()))


if __name__ == "__main__":
    unittest.main()

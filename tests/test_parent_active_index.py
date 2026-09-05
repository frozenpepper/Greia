from __future__ import annotations

import shutil
import tempfile
import threading
import unittest
import zipfile
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from greia_platform.activities import ActivityRegistry
from greia_platform.activity_index import ActivityIndex
from greia_platform.activity_packages import (
    ACTIVE_INDEX_FILENAME,
    ACTIVITIES_DIRNAME,
    ActivityPackageError,
    ActivityPackageService,
)
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME = PROJECT_ROOT / "runtime/child-runtime.toml"
PAINTING = PROJECT_ROOT / "activities/painting"
SECOND_ID = "org.greia.secondpainting"


def write_activity_archive(
    source: Path,
    destination: Path,
    *,
    manifest_transform: Callable[[str], str] | None = None,
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


def make_service(root: Path) -> ActivityPackageService:
    return ActivityPackageService(
        state_root=root / "packages",
        runtime_catalogue=RUNTIME,
        built_in_root=root / "empty-builtins",
    )


def second_id_transform(text: str) -> str:
    return text.replace('id = "org.greia.painting"', f'id = "{SECOND_ID}"')


def snapshot_active(service: ActivityPackageService) -> dict[str, bytes]:
    active = service.active_root
    return {
        path.relative_to(active).as_posix(): path.read_bytes()
        for path in sorted(active.rglob("*"))
        if path.is_file()
    }


class ParentActiveGenerationTests(unittest.TestCase):
    def test_publish_creates_versioned_index_with_active_indirection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            service = make_service(root)
            receipt = service.install_archive(archive)

            generation_id = service.active_generation_id()
            self.assertIsNotNone(generation_id)
            assert generation_id is not None
            # Platform-owned indirection is a regular file, never a symlink
            # and never inside an Activity package.
            pointer = service.active_pointer
            self.assertTrue(pointer.is_file())
            self.assertFalse(pointer.is_symlink())
            self.assertEqual(pointer.read_text(encoding="utf-8").strip(), generation_id)

            generation = service.generations_root / generation_id
            activities = generation / ACTIVITIES_DIRNAME
            index_path = generation / ACTIVE_INDEX_FILENAME
            self.assertTrue((activities / receipt.activity_id / "activity.toml").is_file())
            self.assertTrue(index_path.is_file())
            self.assertEqual(service.active_root, activities)
            self.assertIsNotNone(service.active_index_path())

            # No symlinks anywhere inside the published active set.
            for path in activities.rglob("*"):
                self.assertFalse(
                    path.is_symlink(), f"symlink inside active package: {path}"
                )

            # The stored index is a complete T31 snapshot of the active set.
            index = ActivityIndex.load_file(index_path)
            self.assertEqual(index.source_id, service.SOURCE_ID)
            self.assertEqual(index.package_trust, PackageTrust.PARENT_TRUSTED_UNSIGNED)
            self.assertEqual(len(index.registrations), 1)
            entry = index.registrations[0]
            self.assertEqual(entry.activity_id, receipt.activity_id)
            self.assertEqual(entry.package_digest, receipt.package_digest)

            # The loader reconstructs the live registration without tree
            # re-reads: pin the registry scan to raise and prove the index
            # path does not touch it.
            with mock.patch.object(
                ActivityRegistry,
                "discover_registrations",
                side_effect=AssertionError("index load must not rescan trees"),
            ):
                loaded = service.load_active_registrations()
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].manifest.activity_id, receipt.activity_id)
            self.assertEqual(loaded[0].package_digest, receipt.package_digest)
            self.assertEqual(loaded[0].package_trust, PackageTrust.PARENT_TRUSTED_UNSIGNED)
            self.assertEqual(loaded[0].source_id, service.SOURCE_ID)

    def test_fault_between_index_write_and_publish_keeps_previous_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, first_archive)
            service = make_service(root)
            first = service.install_archive(first_archive)

            generation_before = service.active_generation_id()
            index_before = service.active_index_path()
            assert generation_before is not None and index_before is not None
            index_bytes_before = index_before.read_bytes()
            active_before = snapshot_active(service)
            receipt_before = service._receipt_path(first.activity_id).read_bytes()

            second_archive = root / "second.greiaactivity"
            write_activity_archive(
                PAINTING, second_archive, manifest_transform=second_id_transform
            )
            # Fault injection at the exact commit seam: the new generation
            # (activities plus index) is fully staged, then the atomic pointer
            # swap fails. Boot must still expose the previous complete set.
            with mock.patch.object(
                service,
                "_publish_generation",
                side_effect=OSError("simulated power loss at publish"),
            ):
                with self.assertRaises(ActivityPackageError):
                    service.install_archive(second_archive)

            self.assertEqual(service.active_generation_id(), generation_before)
            self.assertEqual(service.active_index_path().read_bytes(), index_bytes_before)  # type: ignore[union-attr]
            self.assertEqual(snapshot_active(service), active_before)
            self.assertEqual(
                service._receipt_path(first.activity_id).read_bytes(), receipt_before
            )
            # The failed set never became visible through the index either.
            loaded_ids = {
                item.manifest.activity_id for item in service.load_active_registrations()
            }
            self.assertEqual(loaded_ids, {first.activity_id})
            # No half-published staging residue survives.
            leftovers = [
                path
                for path in service.generations_root.iterdir()
                if path.name.startswith(".staging-")
            ]
            self.assertEqual(leftovers, [])

            # Positive control: without the fault the same second package
            # publishes a new complete generation holding both sets plus one
            # joint index.
            second = service.install_archive(second_archive)
            generation_after = service.active_generation_id()
            self.assertIsNotNone(generation_after)
            self.assertNotEqual(generation_after, generation_before)
            joint_ids = {
                item.manifest.activity_id for item in service.load_active_registrations()
            }
            self.assertEqual(joint_ids, {first.activity_id, second.activity_id})
            joint_index = ActivityIndex.load_file(service.active_index_path())  # type: ignore[arg-type]
            self.assertEqual(
                {entry.activity_id for entry in joint_index.registrations}, joint_ids
            )

    def test_corrupt_mutable_package_cannot_become_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good_archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, good_archive)
            service = make_service(root)
            good = service.install_archive(good_archive)

            generation_before = service.active_generation_id()
            index_bytes_before = service.active_index_path().read_bytes()  # type: ignore[union-attr]
            active_before = snapshot_active(service)
            receipt_before = service._receipt_path(good.activity_id).read_bytes()
            versions_before = {
                path.relative_to(service.versions_root)
                for path in service.versions_root.rglob("*")
            }

            # Deliberately corrupt mutable package: a forbidden native suffix
            # that validation must refuse before anything becomes active.
            bad_source = root / "bad-painting"
            shutil.copytree(PAINTING, bad_source, symlinks=True)
            (bad_source / "payload.run").write_bytes(b"#!/bin/sh\n")
            bad_archive = root / "bad.greiaactivity"
            with zipfile.ZipFile(bad_archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
                for path in sorted(bad_source.rglob("*")):
                    if path.is_file():
                        package.write(path, path.relative_to(bad_source).as_posix())
            with self.assertRaises(ActivityPackageError):
                service.install_archive(bad_archive)

            self.assertEqual(service.active_generation_id(), generation_before)
            self.assertEqual(service.active_index_path().read_bytes(), index_bytes_before)  # type: ignore[union-attr]
            self.assertEqual(snapshot_active(service), active_before)
            self.assertEqual(
                service._receipt_path(good.activity_id).read_bytes(), receipt_before
            )
            self.assertEqual(
                {
                    path.relative_to(service.versions_root)
                    for path in service.versions_root.rglob("*")
                },
                versions_before,
            )
            loaded_ids = {
                item.manifest.activity_id for item in service.load_active_registrations()
            }
            self.assertEqual(loaded_ids, {good.activity_id})
            staging_leftovers = [
                path
                for path in service.staging_root.iterdir()
                if path.name.startswith("install-")
            ]
            self.assertEqual(staging_leftovers, [])
            generation_leftovers = [
                path
                for path in service.generations_root.iterdir()
                if path.name.startswith(".staging-")
            ]
            self.assertEqual(generation_leftovers, [])

    def test_same_source_reinstall_keeps_prior_set_intact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            service = make_service(root)
            first = service.install_archive(archive)

            generation_before = service.active_generation_id()
            index_bytes_before = service.active_index_path().read_bytes()  # type: ignore[union-attr]
            active_before = snapshot_active(service)
            receipt_before = service._receipt_path(first.activity_id).read_bytes()

            with self.assertRaisesRegex(ActivityPackageError, "already installed"):
                service.install_archive(archive)

            self.assertEqual(service.active_generation_id(), generation_before)
            self.assertEqual(service.active_index_path().read_bytes(), index_bytes_before)  # type: ignore[union-attr]
            self.assertEqual(snapshot_active(service), active_before)
            self.assertEqual(
                service._receipt_path(first.activity_id).read_bytes(), receipt_before
            )
            # Exactly one versioned generation remains live; no residue.
            live = [
                path
                for path in service.generations_root.iterdir()
                if path.is_dir() and not path.name.startswith(".")
            ]
            self.assertEqual(len(live), 1)
            self.assertEqual(live[0].name, generation_before)

    def test_uninstall_publishes_new_generation_without_touching_child_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            profile_data = (
                root / "profiles" / "greta" / "activity-data"
                / "org.greia.painting" / "save.json"
            )
            profile_data.parent.mkdir(parents=True)
            profile_data.write_text('{"drawing":"kept"}\n', encoding="utf-8")
            service = make_service(root)
            installed = service.install_archive(archive)
            generation_before = service.active_generation_id()

            removed = service.uninstall(installed.activity_id)

            self.assertEqual(removed.activity_id, installed.activity_id)
            self.assertTrue(removed.profile_data_preserved)
            generation_after = service.active_generation_id()
            self.assertIsNotNone(generation_after)
            self.assertNotEqual(generation_after, generation_before)
            self.assertEqual(service.load_active_registrations(), ())
            empty_index = ActivityIndex.load_file(service.active_index_path())  # type: ignore[arg-type]
            self.assertEqual(empty_index.registrations, ())
            self.assertFalse(service._receipt_path(installed.activity_id).exists())
            self.assertFalse((service.versions_root / installed.activity_id).exists())
            self.assertEqual(
                profile_data.read_text(encoding="utf-8"), '{"drawing":"kept"}\n'
            )

    def test_concurrent_first_time_roots_converge_on_one_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = make_service(root)
            count = 8
            start = threading.Barrier(count + 1)
            errors: list[BaseException] = []

            def worker() -> None:
                start.wait()
                try:
                    service._ensure_roots()
                except BaseException as exc:  # pragma: no cover - recorded
                    errors.append(exc)

            threads = [threading.Thread(target=worker) for _ in range(count)]
            for thread in threads:
                thread.start()
            start.wait()
            for thread in threads:
                thread.join(timeout=10)
                self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])
            live = [
                path
                for path in service.generations_root.iterdir()
                if path.is_dir() and not path.name.startswith(".")
            ]
            self.assertEqual(len(live), 1)
            self.assertIsNotNone(service.active_generation_id())
            self.assertTrue(service.active_index_path().is_file())  # type: ignore[union-attr]

    def test_active_source_binding_matches_generation_layout(self) -> None:
        """T36 read contract: generation dirs plus the active indirection."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "painting.greiaactivity"
            write_activity_archive(PAINTING, archive)
            service = make_service(root)
            service.install_archive(archive)
            source = service.active_source()
            self.assertEqual(source.source_id, service.SOURCE_ID)
            self.assertIs(source.trust, PackageTrust.PARENT_TRUSTED_UNSIGNED)
            self.assertEqual(source.root, service.active_root)
            self.assertTrue(ActivitySource(source.root, source.trust, source.source_id))


if __name__ == "__main__":
    unittest.main()

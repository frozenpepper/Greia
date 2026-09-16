"""Image-build integration of the built-in Activity index (T33).

Covers the ``build/lib/compose.sh`` transaction (consumed for role `target`
by ``build/build-image.sh``) that invokes the T32
generator (``tools/build_activity_index.py``) and installs the final index
under the image-owned path ``usr/share/greia/activity-index-v1.json`` from
the same build transaction as the built-in Activity content.

The tests exercise a harness helper (``_run_image_index_transaction``) that
mirrors the exact production block in ``build-image.sh``: stage the
generator output to a temporary file, abort nonzero without touching the
image-owned index on any generation failure, and atomically install
(``install -D -m 0644`` semantics) only on success. A static test pins the
production wiring so the harness cannot drift from the build script.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from greia_platform.activities import package_digest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL = PROJECT_ROOT / "tools" / "build_activity_index.py"
RUNTIME_PATH = PROJECT_ROOT / "runtime" / "child-runtime.toml"
# T01: the index transaction lives in the shared composition engine; the thin
# target consumer invokes it through compose_root --role target.
BUILD_SCRIPT = PROJECT_ROOT / "build" / "lib" / "compose.sh"
THIN_CONSUMER = PROJECT_ROOT / "build" / "build-image.sh"
IMAGE_INDEX_RELPATH = Path("usr/share/greia/activity-index-v1.json")
BUILT_IN_SOURCE_ID = "greia-system"


def _make_source_tree(temporary: str) -> Path:
    """Copy two small first-party packages into an isolated source root."""
    root = Path(temporary) / "activities"
    root.mkdir(parents=True)
    for name in ("shape_garden", "painting"):
        source = PROJECT_ROOT / "activities" / name
        if source.is_dir():
            shutil.copytree(source, root / name)
    return root


def _install_content_like_build(source_root: Path, rootfs: Path) -> Path:
    """Mirror the build's content install: source tree into the fake image."""
    installed = rootfs / "opt" / "greia-os" / "activities"
    shutil.copytree(
        source_root,
        installed,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    return installed


def _run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )


def _run_image_index_transaction(
    source_root: Path,
    image_index: Path,
    runtime_path: Path = RUNTIME_PATH,
) -> subprocess.CompletedProcess[str]:
    """Mirror the T33 block in build-image.sh against a fake image root.

    Stages generator output to a sibling temporary file, then installs it to
    ``image_index`` (``install -D -m 0644`` semantics) only when generation
    succeeds. On failure returns the nonzero result with the image-owned
    index untouched and no staging residue — the build-fails-closed path.
    """
    staging = image_index.parent / (image_index.name + ".staging")
    image_index.parent.mkdir(parents=True, exist_ok=True)
    result = _run_tool(
        "--activities", str(source_root),
        "--runtime", str(runtime_path),
        "--output", str(staging),
    )
    staging_tmp = staging.with_name(staging.name + ".tmp")
    if result.returncode != 0:
        for leftover in (staging, staging_tmp):
            try:
                leftover.unlink(missing_ok=True)
            except OSError:
                pass
        return result
    shutil.copyfile(staging, image_index)
    os.chmod(image_index, 0o644)
    for leftover in (staging, staging_tmp):
        try:
            leftover.unlink(missing_ok=True)
        except OSError:
            pass
    return result


class ImageActivityIndexTests(unittest.TestCase):
    def test_build_script_wires_generator_fail_closed(self) -> None:
        text = BUILD_SCRIPT.read_text(encoding="utf-8")
        # The generator is invoked during image construction.
        self.assertIn("tools/build_activity_index.py", text)
        # Same source transaction: the generator reads the exact source root
        # whose content the build installs, with the child runtime catalogue.
        self.assertIn('"$project_root/activities"', text)
        self.assertIn("child-runtime.toml", text)
        # The final index ships under the image-owned path.
        self.assertIn("usr/share/greia/activity-index-v1.json", text)
        # Fail-closed block: nonzero abort, no half-installed index, atomic
        # install only on success. The engine is a sourced library, so the
        # abort is `return 1` propagated through compose_root to the
        # set -e consumer (which exits); the staging cleanup + atomic
        # install semantics are unchanged.
        marker = "# T33 built-in index"
        self.assertIn(marker, text)
        block = text.split(marker, 1)[1].split("compose_install_live_content", 1)[0]
        self.assertIn("return 1", block)
        self.assertIn("rm -f", block)
        self.assertIn("install -D -m 0644", block)
        self.assertIn('compose_install_greia_content "$rootfs" "$role" || return 1', text)
        consumer = THIN_CONSUMER.read_text(encoding="utf-8")
        self.assertIn('compose_root --profile "$PROFILE_PATH" --role target --root "$ROOTFS"', consumer)
        # Scope guard: the index transaction touches no initramfs, module, or
        # partition-layout machinery.
        for forbidden in (
            "update-initramfs",
            "MODULES",
            "mkpart",
            "sgdisk",
            "parted",
        ):
            self.assertNotIn(forbidden, block)

    def test_same_transaction_index_matches_installed_content(self) -> None:
        from greia_platform.activity_index import ActivityIndex
        from greia_platform.trust import PackageTrust

        with tempfile.TemporaryDirectory() as temporary:
            source_root = _make_source_tree(temporary)
            rootfs = Path(temporary) / "rootfs"
            installed_root = _install_content_like_build(source_root, rootfs)
            image_index = rootfs / IMAGE_INDEX_RELPATH
            result = _run_image_index_transaction(source_root, image_index)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(image_index.is_file())
            self.assertEqual(
                stat.S_IMODE(image_index.stat().st_mode), 0o644
            )
            payload = image_index.read_bytes()
            self.assertTrue(payload.endswith(b"\n"))
            index = ActivityIndex.load_file(image_index)
            self.assertEqual(index.source_id, BUILT_IN_SOURCE_ID)
            self.assertEqual(index.package_trust, PackageTrust.BUILT_IN)
            self.assertGreaterEqual(len(index.registrations), 1)
            activity_ids = [entry.activity_id for entry in index.registrations]
            self.assertEqual(activity_ids, sorted(activity_ids))
            for entry in index.registrations:
                source_copy = source_root / entry.package_relpath
                installed_copy = installed_root / entry.package_relpath
                self.assertTrue(installed_copy.is_dir())
                # Index and installed content resolve from the same source
                # transaction: digests agree on both sides of the install.
                self.assertEqual(
                    entry.package_digest, package_digest(source_copy)
                )
                self.assertEqual(
                    entry.package_digest, package_digest(installed_copy)
                )

    def test_generation_failure_preserves_seeded_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = _make_source_tree(temporary)
            rootfs = Path(temporary) / "rootfs"
            _install_content_like_build(source_root, rootfs)
            image_index = rootfs / IMAGE_INDEX_RELPATH
            seeded = _run_image_index_transaction(source_root, image_index)
            self.assertEqual(seeded.returncode, 0, msg=seeded.stderr)
            before = image_index.read_bytes()
            # Inject an invalid built-in package: a forbidden executable
            # suffix the authoritative registry tree validation must reject.
            (source_root / "shape_garden" / "evil.sh").write_text(
                "#!/bin/sh\nexit 0\n", encoding="utf-8"
            )
            failed = _run_image_index_transaction(source_root, image_index)
            self.assertNotEqual(failed.returncode, 0)
            # Build aborts with no half-installed index: the seeded output is
            # byte-preserved and no staging residue remains.
            self.assertEqual(image_index.read_bytes(), before)
            staging = image_index.parent / (image_index.name + ".staging")
            self.assertFalse(staging.exists())
            self.assertFalse(
                staging.with_name(staging.name + ".tmp").exists()
            )
            self.assertFalse(
                image_index.with_name(image_index.name + ".tmp").exists()
            )

    def test_generation_failure_creates_no_index_when_none_existed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source_root = _make_source_tree(temporary)
            (source_root / "shape_garden" / "payload.exe").write_bytes(b"MZ")
            rootfs = Path(temporary) / "rootfs"
            image_index = rootfs / IMAGE_INDEX_RELPATH
            result = _run_image_index_transaction(source_root, image_index)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(image_index.exists())
            staging = image_index.parent / (image_index.name + ".staging")
            self.assertFalse(staging.exists())
            self.assertFalse(
                staging.with_name(staging.name + ".tmp").exists()
            )

    def test_checked_source_index_consistent(self) -> None:
        from greia_platform.activity_index import ActivityIndex
        from greia_platform.trust import PackageTrust

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "activity-index-v1.json"
            result = _run_tool(
                "--activities", str(PROJECT_ROOT / "activities"),
                "--runtime", str(RUNTIME_PATH),
                "--output", str(destination),
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            index = ActivityIndex.load_file(destination)
            self.assertEqual(index.source_id, BUILT_IN_SOURCE_ID)
            self.assertEqual(index.package_trust, PackageTrust.BUILT_IN)
            self.assertGreaterEqual(len(index.registrations), 1)
            for entry in index.registrations:
                on_disk = PROJECT_ROOT / "activities" / entry.package_relpath
                self.assertEqual(
                    entry.package_digest, package_digest(on_disk)
                )


if __name__ == "__main__":
    unittest.main()

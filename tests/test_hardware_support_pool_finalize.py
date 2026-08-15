from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.finalize_hardware_support_pool import PoolFinalizeError, finalize_pool


class HardwareSupportPoolFinalizeTests(unittest.TestCase):
    def make_candidate_manifest(self, root: Path) -> Path:
        path = root / "candidates.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "suite": "trixie",
                    "architecture": "amd64",
                    "candidate_packages": ["firmware-realtek", "intel-microcode"],
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_finalizer_hashes_payloads_and_builds_flat_apt_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pool = root / "support"
            deb_dir = pool / "pool"
            deb_dir.mkdir(parents=True)
            package = deb_dir / "firmware-realtek_1_all.deb"
            package.write_bytes(b"fake-debian-package")
            candidates = self.make_candidate_manifest(root)
            control = (
                "Package: firmware-realtek\n"
                "Version: 1\n"
                "Architecture: all\n"
                "Description: test firmware\n"
            )
            with mock.patch("tools.finalize_hardware_support_pool._control", return_value=control):
                manifest = finalize_pool(pool, candidates, 1024 * 1024)

            self.assertEqual(manifest["package_count"], 1)
            self.assertEqual(manifest["provided_candidate_packages"], ["firmware-realtek"])
            self.assertEqual(manifest["unavailable_candidate_packages"], ["intel-microcode"])
            entry = manifest["packages"][0]
            self.assertTrue(entry["candidate"])
            self.assertEqual(entry["filename"], "pool/firmware-realtek_1_all.deb")
            self.assertEqual(len(entry["sha256"]), 64)
            packages_text = (pool / "Packages").read_text(encoding="utf-8")
            self.assertIn("Package: firmware-realtek", packages_text)
            self.assertIn("Filename: pool/firmware-realtek_1_all.deb", packages_text)
            with gzip.open(pool / "Packages.gz", "rt", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), packages_text)
            persisted = json.loads((pool / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["packages"], manifest["packages"])

    def test_pool_size_bound_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pool = root / "support"
            deb_dir = pool / "pool"
            deb_dir.mkdir(parents=True)
            (deb_dir / "firmware-realtek_1_all.deb").write_bytes(b"x" * 20)
            candidates = self.make_candidate_manifest(root)
            with self.assertRaises(PoolFinalizeError):
                finalize_pool(pool, candidates, 10)

    def test_duplicate_package_architecture_versions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pool = root / "support"
            deb_dir = pool / "pool"
            deb_dir.mkdir(parents=True)
            (deb_dir / "firmware-realtek_1_all.deb").write_bytes(b"one")
            (deb_dir / "firmware-realtek_2_all.deb").write_bytes(b"two")
            candidates = self.make_candidate_manifest(root)
            controls = [
                "Package: firmware-realtek\nVersion: 1\nArchitecture: all\n",
                "Package: firmware-realtek\nVersion: 2\nArchitecture: all\n",
            ]
            with mock.patch("tools.finalize_hardware_support_pool._control", side_effect=controls):
                with self.assertRaises(PoolFinalizeError):
                    finalize_pool(pool, candidates, 1024 * 1024)

    def test_symlinked_deb_is_not_admitted_to_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pool = root / "support"
            deb_dir = pool / "pool"
            deb_dir.mkdir(parents=True)
            outside = root / "outside.deb"
            outside.write_bytes(b"outside")
            (deb_dir / "firmware-realtek_1_all.deb").symlink_to(outside)
            candidates = self.make_candidate_manifest(root)
            manifest = finalize_pool(pool, candidates, 1024 * 1024)
            self.assertEqual(manifest["package_count"], 0)
            self.assertEqual(manifest["provided_candidate_packages"], [])


if __name__ == "__main__":
    unittest.main()

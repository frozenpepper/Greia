from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from greia_installer.hardware_support import (
    HardwareSupportPoolError,
    HardwareSupportPoolPackage,
    VerifiedHardwareSupportPool,
)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def make_pool(root: Path, *, payload: bytes = b"firmware", extra_deb: bool = False) -> Path:
    pool = root / "support"
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    deb = deb_dir / "firmware-realtek_1_all.deb"
    deb.write_bytes(payload)
    if extra_deb:
        (deb_dir / "unmanifested_1_all.deb").write_bytes(b"extra")
    packages_payload = b"Package: firmware-realtek\n"
    packages_gzip_payload = b"gzip-placeholder"
    (pool / "Packages").write_bytes(packages_payload)
    (pool / "Packages.gz").write_bytes(packages_gzip_payload)
    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 1,
        "total_bytes": len(payload),
        "provided_candidate_packages": ["firmware-realtek"],
        "provided_firmware_packages": ["firmware-realtek"],
        "provided_microcode_packages": [],
        "firmware_providers": {
            "rtl.bin": ["firmware-realtek"],
            "rtl_nic/rtl8106e-1.fw": ["firmware-realtek"],
            "rtl_nic/rtl8168g-2.fw": ["firmware-realtek"],
        },
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": "firmware-realtek",
                "version": "1",
                "architecture": "all",
                "filename": "pool/firmware-realtek_1_all.deb",
                "size": len(payload),
                "sha256": digest(payload),
                "candidate": True,
            }
        ],
        "repository_indexes": {
            "Packages": {
                "size": len(packages_payload),
                "sha256": digest(packages_payload),
            },
            "Packages.gz": {
                "size": len(packages_gzip_payload),
                "sha256": digest(packages_gzip_payload),
            },
        },
    }
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool


class InstallerHardwareSupportPoolTests(unittest.TestCase):
    def test_verified_pool_accepts_exact_manifested_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool_root = make_pool(Path(temporary))
            pool = VerifiedHardwareSupportPool.load(
                pool_root,
                expected_suite="trixie",
                expected_architecture="amd64",
            )
        self.assertEqual(pool.provided_candidates, frozenset({"firmware-realtek"}))
        self.assertEqual(pool.provided_firmware, frozenset({"firmware-realtek"}))
        self.assertEqual(pool.provided_microcode, frozenset())
        self.assertEqual(pool.require_candidates(["firmware-realtek"]), ("firmware-realtek",))
        self.assertEqual(pool.require_firmware(["firmware-realtek"]), ("firmware-realtek",))
        self.assertEqual(
            pool.apt_source_line,
            "deb [trusted=yes] file:/run/greia-hardware-support ./",
        )

    def test_firmware_provider_lookup_supports_exact_and_kernel_glob_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool = VerifiedHardwareSupportPool.load(make_pool(Path(temporary)))
        self.assertEqual(pool.packages_for_firmware("rtl.bin"), ("firmware-realtek",))
        self.assertEqual(
            pool.packages_for_firmware("rtl_nic/rtl*.fw"),
            ("firmware-realtek",),
        )
        self.assertEqual(pool.packages_for_firmware("missing.bin"), ())

    def test_multiple_providers_choose_smallest_verified_candidate_for_same_file(self) -> None:
        small = HardwareSupportPoolPackage(
            "firmware-small",
            "1",
            "all",
            "pool/firmware-small.deb",
            10,
            "0" * 64,
            True,
        )
        large = HardwareSupportPoolPackage(
            "firmware-large",
            "1",
            "all",
            "pool/firmware-large.deb",
            100,
            "1" * 64,
            True,
        )
        pool = VerifiedHardwareSupportPool(
            Path("/verified"),
            "trixie",
            "amd64",
            (large, small),
            frozenset({"firmware-large", "firmware-small"}),
            frozenset({"firmware-large", "firmware-small"}),
            frozenset(),
            110,
            (("shared.bin", ("firmware-large", "firmware-small")),),
        )
        self.assertEqual(pool.packages_for_firmware("shared.bin"), ("firmware-small",))

    def test_unsafe_firmware_pattern_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool = VerifiedHardwareSupportPool.load(make_pool(Path(temporary)))
        with self.assertRaisesRegex(HardwareSupportPoolError, "path/pattern"):
            pool.packages_for_firmware("../escape.bin")

    def test_firmware_provider_may_not_reference_non_firmware_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool_root = make_pool(Path(temporary))
            manifest_path = pool_root / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["firmware_providers"]["rtl.bin"] = ["tlp"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(HardwareSupportPoolError, "non-firmware"):
                VerifiedHardwareSupportPool.load(pool_root)

    def test_firmware_cannot_be_reclassified_as_microcode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool = VerifiedHardwareSupportPool.load(make_pool(Path(temporary)))
            with self.assertRaisesRegex(HardwareSupportPoolError, "not verified microcode"):
                pool.require_microcode(["firmware-realtek"])

    def test_digest_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool_root = make_pool(Path(temporary))
            (pool_root / "pool/firmware-realtek_1_all.deb").write_bytes(b"changed!!")
            with self.assertRaises(HardwareSupportPoolError):
                VerifiedHardwareSupportPool.load(pool_root)

    def test_repository_index_digest_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool_root = make_pool(Path(temporary))
            (pool_root / "Packages").write_bytes(b"changed")
            with self.assertRaisesRegex(HardwareSupportPoolError, "index changed"):
                VerifiedHardwareSupportPool.load(pool_root)

    def test_unmanifested_deb_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool_root = make_pool(Path(temporary), extra_deb=True)
            with self.assertRaisesRegex(HardwareSupportPoolError, "unmanifested"):
                VerifiedHardwareSupportPool.load(pool_root)

    def test_unmanifested_symlinked_deb_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pool_root = make_pool(root)
            outside = root / "outside.deb"
            outside.write_bytes(b"outside")
            (pool_root / "pool/unmanifested_1_all.deb").symlink_to(outside)
            with self.assertRaisesRegex(HardwareSupportPoolError, "symlinked"):
                VerifiedHardwareSupportPool.load(pool_root)

    def test_wrong_suite_or_architecture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool_root = make_pool(Path(temporary))
            with self.assertRaisesRegex(HardwareSupportPoolError, "suite"):
                VerifiedHardwareSupportPool.load(pool_root, expected_suite="bookworm")
            with self.assertRaisesRegex(HardwareSupportPoolError, "architecture"):
                VerifiedHardwareSupportPool.load(pool_root, expected_architecture="i386")

    def test_unprovided_candidate_cannot_be_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool = VerifiedHardwareSupportPool.load(make_pool(Path(temporary)))
            with self.assertRaisesRegex(HardwareSupportPoolError, "not available"):
                pool.require_candidates(["firmware-iwlwifi"])


if __name__ == "__main__":
    unittest.main()

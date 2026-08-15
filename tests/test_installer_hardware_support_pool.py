from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from greia_installer.hardware_support import (
    HardwareSupportPoolError,
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
    (pool / "Packages").write_text("Package: firmware-realtek\n", encoding="utf-8")
    (pool / "Packages.gz").write_bytes(b"gzip-placeholder")
    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 1,
        "total_bytes": len(payload),
        "provided_candidate_packages": ["firmware-realtek"],
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
        self.assertEqual(pool.require_candidates(["firmware-realtek"]), ("firmware-realtek",))
        self.assertEqual(
            pool.apt_source_line,
            "deb [trusted=yes] file:/run/greia-hardware-support ./",
        )

    def test_digest_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool_root = make_pool(Path(temporary))
            (pool_root / "pool/firmware-realtek_1_all.deb").write_bytes(b"changed!!")
            with self.assertRaises(HardwareSupportPoolError):
                VerifiedHardwareSupportPool.load(pool_root)

    def test_unmanifested_deb_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pool_root = make_pool(Path(temporary), extra_deb=True)
            with self.assertRaisesRegex(HardwareSupportPoolError, "unmanifested"):
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

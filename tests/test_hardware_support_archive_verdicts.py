"""R4-D-PARSER: build-time and runtime verdicts agree on every malformed archive.

Feeds the same ``hardware-support.tar.zst`` bytes through:

- build/release inspection
  (``greia_installer.hardware_support.installed_size_bound_from_support_archive``),
- runtime inspection
  (``greia_platform.candidate_support.inspect_support_metadata`` on the
  same bytes embedded as the ``.greiaupdate`` member),

and asserts identical accept/reject verdicts for every malformed shape
listed in the task brief: unexpected directory/file, symlink, hardlink,
device node, FIFO, traversal, duplicate member, missing manifest,
missing package, unmanifested ``.deb``, digest/size/installed-size/
repository-index mismatch and member-count/compressed-size/
decompressed-size overflow.

Overflow cases use patched-down bounds so the test stays fast while
still proving both paths enforce the *same* shared bound; a separate
test pins the production bounds to the single 512 MiB value.
"""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_installer import hardware_support_archive as _shared
from greia_installer.hardware_support import (
    HardwareSupportPoolError,
    installed_size_bound_from_support_archive,
)
from greia_platform import candidate_support as _runtime
from greia_platform.system_updates import (
    MAX_HARDWARE_SUPPORT_BYTES,
    SystemUpdateInbox,
    build_update_bundle,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


_FW = b"fw-deb-bytes"
_UC = b"uc-deb-bytes"
_PKGS = b"Package: firmware-test\n"
_PKGS_GZ = b"gzip-placeholder"


def _manifest(
    *,
    fw: bytes = _FW,
    uc: bytes = _UC,
    installed_fw: int = 100 * 1024,
    installed_uc: int = 200 * 1024,
    pkgs: bytes = _PKGS,
    pkgs_gz: bytes = _PKGS_GZ,
) -> dict:
    return {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 2,
        "total_bytes": len(fw) + len(uc),
        "total_installed_bytes": installed_fw + installed_uc,
        "provided_candidate_packages": ["firmware-test", "microcode-test"],
        "provided_firmware_packages": ["firmware-test"],
        "provided_microcode_packages": ["microcode-test"],
        "broad_firmware_packages": ["firmware-test"],
        "firmware_providers": {"rtl.bin": ["firmware-test"]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": "firmware-test",
                "version": "1",
                "architecture": "all",
                "filename": "pool/firmware-test_1_all.deb",
                "size": len(fw),
                "sha256": _sha(fw),
                "candidate": True,
                "installed_bytes": installed_fw,
            },
            {
                "package": "microcode-test",
                "version": "1",
                "architecture": "amd64",
                "filename": "pool/microcode-test_1_amd64.deb",
                "size": len(uc),
                "sha256": _sha(uc),
                "candidate": True,
                "installed_bytes": installed_uc,
            },
        ],
        "repository_indexes": {
            "Packages": {"size": len(pkgs), "sha256": _sha(pkgs)},
            "Packages.gz": {"size": len(pkgs_gz), "sha256": _sha(pkgs_gz)},
        },
    }


def _tar_bytes(entries: list[tuple[tarfile.TarInfo, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for info, payload in entries:
            info.size = len(payload)
            info.mtime = 0
            tar.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


def _reg(name: str, payload: bytes, mode: int = 0o644) -> tuple[tarfile.TarInfo, bytes]:
    info = tarfile.TarInfo(name=name)
    info.type = tarfile.REGTYPE
    info.mode = mode
    return info, payload


def _compress(raw_tar: bytes) -> bytes:
    import zstandard

    return zstandard.ZstdCompressor(level=3).compress(raw_tar)


def _valid_members(manifest: dict | None = None) -> list[tuple[tarfile.TarInfo, bytes]]:
    manifest = manifest if manifest is not None else _manifest()
    return [
        _reg("manifest.json", json.dumps(manifest).encode()),
        _reg("Packages", _PKGS),
        _reg("Packages.gz", _PKGS_GZ),
        _reg("pool/firmware-test_1_all.deb", _FW),
        _reg("pool/microcode-test_1_amd64.deb", _UC),
    ]


def _mutate(
    members: list[tuple[tarfile.TarInfo, bytes]],
    transform,
) -> bytes:
    members = list(members)
    transform(members)
    return _compress(_tar_bytes(members))


def _build_verdicts(raw_compressed: bytes, root: Path) -> tuple[bool, bool]:
    """Return (build_accepts, runtime_accepts) for the same bytes."""
    hw_path = root / "case.tar.zst"
    hw_path.write_bytes(raw_compressed)
    try:
        installed_size_bound_from_support_archive(hw_path)
        build_ok = True
    except HardwareSupportPoolError:
        build_ok = False
    import zstandard

    work = root / "bundle-work"
    work.mkdir(parents=True, exist_ok=True)
    payload_path = work / "slot.ext4.zst"
    payload_path.write_bytes(zstandard.ZstdCompressor(level=3).compress(b"payload"))
    bundle = work / "candidate.greiaupdate"
    if bundle.exists():
        bundle.unlink()
    build_update_bundle(
        payload_path=payload_path,
        hardware_support_path=hw_path,
        output_path=bundle,
        version="0.99.0",
        release_id="greia-parser-verdicts",
        platform_family="verdicts",
        architecture="verdictarch",
        profile="verdictprofile",
        payload_uncompressed_bytes=len(b"payload"),
        minimum_slot_bytes=len(b"payload"),
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
        release_notes="parser verdict probe",
    )
    inspected = SystemUpdateInbox(root / "state").receive(bundle)
    manifest = inspected.manifest
    assert manifest.hardware_support_sha256 is not None
    assert manifest.hardware_support_size is not None
    try:
        _runtime.inspect_support_metadata(
            inspected.path,
            expected_sha=manifest.hardware_support_sha256,
            expected_size=manifest.hardware_support_size,
        )
        runtime_ok = True
    except _runtime.CandidateSupportError:
        runtime_ok = False
    return build_ok, runtime_ok


class IdenticalVerdictTests(unittest.TestCase):
    def _assert_same_verdict(self, raw: bytes, *, expect_accept: bool) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_ok, runtime_ok = _build_verdicts(raw, root)
        self.assertEqual(
            build_ok, runtime_ok, "build and runtime verdicts must agree"
        )
        self.assertEqual(build_ok, expect_accept)

    def test_valid_archive_accepted_by_both(self) -> None:
        raw = _compress(_tar_bytes(_valid_members()))
        self._assert_same_verdict(raw, expect_accept=True)

    def test_unexpected_directory_rejected(self) -> None:
        members = _valid_members()
        info = tarfile.TarInfo(name="extra-dir")
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        members.append((info, b""))
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_unexpected_file_rejected(self) -> None:
        members = _valid_members() + [_reg("unexpected-top-level.txt", b"x")]
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_nested_pool_file_rejected(self) -> None:
        members = _valid_members() + [_reg("pool/sub/extra.deb", b"x")]
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_symlink_rejected(self) -> None:
        info = tarfile.TarInfo(name="pool/evil.deb")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        members = _valid_members() + [(info, b"")]
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_hardlink_rejected(self) -> None:
        info = tarfile.TarInfo(name="pool/evil.deb")
        info.type = tarfile.LNKTYPE
        info.linkname = "pool/firmware-test_1_all.deb"
        members = _valid_members() + [(info, b"")]
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_device_node_rejected(self) -> None:
        info = tarfile.TarInfo(name="pool/node.deb")
        info.type = tarfile.CHRTYPE
        members = _valid_members() + [(info, b"")]
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_fifo_rejected(self) -> None:
        info = tarfile.TarInfo(name="Packages")
        info.type = tarfile.FIFOTYPE
        members = [m for m in _valid_members() if m[0].name != "Packages"]
        members.append((info, b""))
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_traversal_rejected(self) -> None:
        for arcname in ("../escape.txt", "/abs.txt", "pool/../../escape.deb"):
            with self.subTest(arcname=arcname):
                members = _valid_members() + [_reg(arcname, b"x")]
                self._assert_same_verdict(
                    _compress(_tar_bytes(members)), expect_accept=False
                )

    def test_duplicate_member_rejected(self) -> None:
        members = _valid_members() + [_reg("Packages", _PKGS)]
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_missing_manifest_rejected(self) -> None:
        members = [m for m in _valid_members() if m[0].name != "manifest.json"]
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_missing_package_rejected(self) -> None:
        members = [
            m for m in _valid_members() if m[0].name != "pool/uc.deb"
            if m[0].name != "pool/microcode-test_1_amd64.deb"
        ]
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_unmanifested_deb_rejected(self) -> None:
        members = _valid_members() + [_reg("pool/extra_1_all.deb", b"extra")]
        self._assert_same_verdict(_compress(_tar_bytes(members)), expect_accept=False)

    def test_digest_mismatch_rejected(self) -> None:
        manifest = _manifest()
        manifest["packages"][0]["sha256"] = _sha(b"something-else")
        self._assert_same_verdict(
            _compress(_tar_bytes(_valid_members(manifest))), expect_accept=False
        )

    def test_size_mismatch_rejected(self) -> None:
        manifest = _manifest()
        manifest["packages"][0]["size"] = len(_FW) + 1
        manifest["total_bytes"] = manifest["packages"][0]["size"] + len(_UC)
        self._assert_same_verdict(
            _compress(_tar_bytes(_valid_members(manifest))), expect_accept=False
        )

    def test_installed_size_mismatch_rejected(self) -> None:
        manifest = _manifest()
        manifest["total_installed_bytes"] = manifest["total_installed_bytes"] + 1
        self._assert_same_verdict(
            _compress(_tar_bytes(_valid_members(manifest))), expect_accept=False
        )

    def test_repository_index_mismatch_rejected(self) -> None:
        manifest = _manifest()
        manifest["repository_indexes"]["Packages"]["sha256"] = _sha(b"tampered")
        self._assert_same_verdict(
            _compress(_tar_bytes(_valid_members(manifest))), expect_accept=False
        )

    def test_member_count_overflow_rejected(self) -> None:
        raw = _compress(_tar_bytes(_valid_members()))
        with (
            mock.patch.object(_shared, "MAX_ARCHIVE_MEMBERS", 4),
            mock.patch.object(_runtime, "MAX_CANDIDATE_SUPPORT_MEMBERS", 4),
        ):
            self._assert_same_verdict(raw, expect_accept=False)

    def test_compressed_size_overflow_rejected(self) -> None:
        raw = _compress(_tar_bytes(_valid_members()))
        with (
            mock.patch.object(_shared, "MAX_ARCHIVE_COMPRESSED_BYTES", 16),
            mock.patch.object(_runtime, "MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES", 16),
        ):
            self._assert_same_verdict(raw, expect_accept=False)

    def test_decompressed_size_overflow_rejected(self) -> None:
        raw = _compress(_tar_bytes(_valid_members()))
        with (
            mock.patch.object(_shared, "MAX_ARCHIVE_UNCOMPRESSED_BYTES", 16),
            mock.patch.object(
                _runtime, "MAX_CANDIDATE_SUPPORT_UNCOMPRESSED_BYTES", 16
            ),
        ):
            self._assert_same_verdict(raw, expect_accept=False)


class SingleProductionBoundTests(unittest.TestCase):
    def test_compressed_bound_is_single_production_value(self) -> None:
        from greia_installer import hardware_support as _build

        self.assertEqual(_shared.MAX_ARCHIVE_COMPRESSED_BYTES, 512 * 1024 * 1024)
        self.assertEqual(
            _runtime.MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES,
            _shared.MAX_ARCHIVE_COMPRESSED_BYTES,
        )
        self.assertEqual(
            _build._MAX_SUPPORT_ARCHIVE_BYTES, _shared.MAX_ARCHIVE_COMPRESSED_BYTES
        )
        self.assertEqual(
            MAX_HARDWARE_SUPPORT_BYTES, _shared.MAX_ARCHIVE_COMPRESSED_BYTES
        )
        # Single ownership: aliases must be the same object as the shared
        # canonical, so a future value-matched second literal fails.
        self.assertIs(
            _runtime.MAX_CANDIDATE_SUPPORT_COMPRESSED_BYTES,
            _shared.MAX_ARCHIVE_COMPRESSED_BYTES,
        )
        self.assertIs(
            _build._MAX_SUPPORT_ARCHIVE_BYTES, _shared.MAX_ARCHIVE_COMPRESSED_BYTES
        )
        self.assertIs(
            MAX_HARDWARE_SUPPORT_BYTES, _shared.MAX_ARCHIVE_COMPRESSED_BYTES
        )

    def test_metadata_shape_carries_stable_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = _compress(_tar_bytes(_valid_members()))
            hw_path = root / "case.tar.zst"
            hw_path.write_bytes(raw)
            build_bound = installed_size_bound_from_support_archive(hw_path)
            build_ok, runtime_ok = _build_verdicts(raw, root)
            self.assertTrue(build_ok)
            self.assertTrue(runtime_ok)
            self.assertEqual(build_bound, 300 * 1024)
            metadata = _shared.inspect_archive_file(hw_path)
            self.assertEqual(metadata.total_installed_bytes, build_bound)
            self.assertGreater(metadata.extracted_size_bound, 0)
            self.assertEqual(metadata.member_count, 5)
            self.assertEqual(len(metadata.packages), 2)


if __name__ == "__main__":
    unittest.main()

"""T05: hardware-support installed-size accounting from Installed-Size.

Production-proof: a pool whose compressed `.deb` bytes are tiny but whose
Debian `Installed-Size` is large must be refused by the real
`SlotFinalizer` capacity gate when the slot fits compressed bytes but not
installed bytes. The bound travels end to end:

  finalize_pool (Installed-Size KiB * 1024 + overhead)
  -> manifest `installed_bytes` / `total_installed_bytes`
  -> VerifiedHardwareSupportPool.load (validated, archive `total_bytes` kept
     separately for transfer/storage)
  -> pool_to_support_set -> ReleaseSupportSet.installed_size_bound
  -> SlotFinalizer capacity gate (`_required_slot_bytes`)

All state stays in disposable tmpdirs; no SSH/mount/flash/apt work runs.
`_control` (the `dpkg-deb -f` seam) is faked with realistic control text
because the fixture `.deb` files are tiny synthetic payloads, not real
Debian archives — the same seam the existing finalize tests fake. The
capacity gate itself is the real production `SlotFinalizer.finalize`.
"""

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_installer import slots as installer_slots
from greia_installer.hardware_support import VerifiedHardwareSupportPool
from greia_platform.persistent_layout import InstalledLayoutRecord
from greia_platform.slot_writer import (
    DestinationSlot,
    HardwareInventoryAttestation,
    LoopbackSlotFile,
    SlotFinalizeError,
    SlotFinalizer,
    SlotProfilePolicy,
    SlotWriter,
    VerifiedReleaseMember,
)
from tools.finalize_hardware_support_pool import (
    _INSTALLED_BYTES_OVERHEAD_PER_PACKAGE,
    PoolFinalizeError,
    finalize_pool,
)


_FW = "firmware-realtek"
_UC = "amd64-microcode"
_INSTALL_SHA = "ab" * 32


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _candidate_manifest(root: Path) -> Path:
    path = root / "candidates.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "suite": "trixie",
                "architecture": "amd64",
                "firmware_packages": [_FW],
                "microcode_packages": [_UC],
                "candidate_packages": [_FW, _UC],
                "firmware_providers": {"rtl.bin": [_FW]},
            }
        ),
        encoding="utf-8",
    )
    return path


def _controls(path: Path) -> str:
    # Tiny archives (tens of bytes) with GiB-scale installed footprints:
    # archive bytes << Installed-Size bytes. Sizes are chosen so the
    # installed total (~1.07 GiB) straddles the 1 GiB minimum slot bound:
    # the same slot fits compressed bytes but not installed bytes.
    if path.name.startswith("firmware-realtek"):
        return (
            "Package: firmware-realtek\nVersion: 1\nArchitecture: all\n"
            "Installed-Size: 716800\n"
        )
    return (
        "Package: amd64-microcode\nVersion: 1\nArchitecture: amd64\n"
        "Installed-Size: 409600\n"
    )


class _FakeFilesystem:
    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        return None

    def expand_to_capacity(self) -> None:
        return None

    def mount(self) -> Path:
        return self.mount_dir

    def unmount(self) -> None:
        return None

    def sync(self) -> None:
        return None

    def write_file(self, relative_path: str, data: bytes) -> None:
        return None

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return ()

    def check_completeness(self) -> None:
        return None

    def check_health(self) -> None:
        return None


class _FakePackageInstaller:
    def install(
        self, firmware: tuple[str, ...], microcode: tuple[str, ...]
    ) -> tuple[object, ...]:
        raise AssertionError("capacity gate must refuse before any install")


def _record(slot_bytes: int) -> InstalledLayoutRecord:
    return InstalledLayoutRecord.from_dict(
        {
            "accepted_release_id": "greia-0.14.0",
            "accepted_slot": "A",
            "boot_backend": "grub-ab-v1",
            "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
            "install_profile": "modern-amd64",
            "install_target_sha256": _INSTALL_SHA,
            "installed_at_unix": 1757000000,
            "layout_id": "modern-gpt-ab-v1",
            "persist": {
                "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
                "partuuid": "33333333-4444-5555-6666-777777777777",
            },
            "platform_family": "standard-x86-64",
            "schema_version": 1,
            "slot_bytes": slot_bytes,
            "system_a": {
                "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "partuuid": "11111111-2222-3333-4444-555555555555",
            },
            "system_b": {
                "filesystem_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                "partuuid": "22222222-3333-4444-5555-666666666666",
            },
        }
    )


class InstalledSizeBoundTests(unittest.TestCase):
    def test_compressed_fit_but_installed_refused_through_real_finalizer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_root = root / "support"
            (pool_root / "pool").mkdir(parents=True)
            (pool_root / "pool/firmware-realtek_1_all.deb").write_bytes(b"fw-tiny")
            (pool_root / "pool/amd64-microcode_1_amd64.deb").write_bytes(b"uc-tiny")
            candidates = _candidate_manifest(root)
            with mock.patch(
                "tools.finalize_hardware_support_pool._control", side_effect=_controls
            ):
                manifest = finalize_pool(pool_root, candidates, 1024 * 1024)

            expected_fw = 716800 * 1024 + _INSTALLED_BYTES_OVERHEAD_PER_PACKAGE
            expected_uc = 409600 * 1024 + _INSTALLED_BYTES_OVERHEAD_PER_PACKAGE
            expected_total = expected_fw + expected_uc
            by_name = {entry["package"]: entry for entry in manifest["packages"]}
            self.assertEqual(by_name[_FW]["installed_bytes"], expected_fw)
            self.assertEqual(by_name[_UC]["installed_bytes"], expected_uc)
            self.assertEqual(manifest["total_installed_bytes"], expected_total)
            # Archive bytes stay tiny and separate (transfer/storage bound).
            self.assertLess(manifest["total_bytes"], 100)
            self.assertGreater(manifest["total_installed_bytes"], 1024 * 1024 * 1024)

            pool = VerifiedHardwareSupportPool.load(pool_root)
            self.assertEqual(pool.total_bytes, manifest["total_bytes"])
            self.assertEqual(pool.total_installed_bytes, expected_total)
            self.assertGreater(pool.total_installed_bytes, pool.total_bytes * 1000)

            hw = b"hwset-member"
            support = installer_slots.pool_to_support_set(
                pool,
                support_digest=hashlib.sha256(hw).hexdigest(),
                support_size=len(hw),
            )
            # Provenance: the bound comes from the installed total, never
            # the compressed archive total.
            self.assertEqual(support.installed_size_bound, pool.total_installed_bytes)
            self.assertNotEqual(support.installed_size_bound, pool.total_bytes)

            payload = bytes((index * 31 + 7) % 256 for index in range(64 * 1024))
            member = VerifiedReleaseMember(
                release_id="greia-0.15.0",
                payload_sha256=hashlib.sha256(payload).hexdigest(),
                payload_size=len(payload),
                payload_uncompressed_bytes=len(payload),
                minimum_slot_bytes=len(payload),
                hardware_support_sha256=hashlib.sha256(hw).hexdigest(),
                hardware_support_size=len(hw),
            )
            # Sensitivity control: the same slot fits the compressed bound
            # but not the installed bound (growth/reserve zeroed to isolate
            # the support-bound effect). Capacity is the 1 GiB minimum slot
            # bound so a real DestinationSlot can be built.
            lean_writer = SlotWriter(growth_bytes=0, metadata_reserve_bytes=0)
            compressed_required = lean_writer.required_slot_bytes(
                member, pool.total_bytes
            )
            installed_required = lean_writer.required_slot_bytes(
                member, support.installed_size_bound
            )
            self.assertGreater(installed_required, compressed_required)
            capacity = 1024 * 1024 * 1024
            self.assertLess(compressed_required, capacity)
            self.assertGreater(installed_required, capacity)

            destination = DestinationSlot.resolve_from_layout(
                _record(capacity), "B"
            )
            store = LoopbackSlotFile.create(root / "slot.img", capacity)
            try:
                # Stage under compressed accounting (what the old buggy
                # bound would have allowed) so the write token exists; the
                # production finalizer must still refuse on installed size.
                write = lean_writer.write(
                    member=member,
                    destination=destination,
                    source=io.BytesIO(payload),
                    storage=store,
                    support_installed_bytes=pool.total_bytes,
                )
                mount_dir = root / "mnt"
                mount_dir.mkdir(exist_ok=True)
                with self.assertRaisesRegex(SlotFinalizeError, "headroom"):
                    SlotFinalizer(
                        growth_bytes=0, metadata_reserve_bytes=0
                    ).finalize(
                        write=write,
                        destination=destination,
                        filesystem=_FakeFilesystem(mount_dir),  # type: ignore[arg-type]
                        package_installer=_FakePackageInstaller(),  # type: ignore[arg-type]
                        inventory=HardwareInventoryAttestation(token="ab" * 32),
                        support=support,
                        profile_policy=SlotProfilePolicy(
                            layout_id="modern-gpt-ab-v1",
                            system_slot_bytes=capacity,
                            boot_backend="grub-ab-v1",
                            persist_filesystem_uuid="cccccccc-dddd-eeee-ffff-000000000000",
                            boot_control_filesystem_uuid="dddddddd-eeee-ffff-0000-111111111111",
                        ),
                    )
            finally:
                store.close()

    def test_missing_installed_size_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_root = root / "support"
            (pool_root / "pool").mkdir(parents=True)
            (pool_root / "pool/firmware-realtek_1_all.deb").write_bytes(b"tiny")
            candidates = root / "candidates.json"
            candidates.write_text(
                json.dumps(
                    {
                        "firmware_packages": [_FW],
                        "microcode_packages": [],
                        "candidate_packages": [_FW],
                        "firmware_providers": {"rtl.bin": [_FW]},
                    }
                ),
                encoding="utf-8",
            )
            control = "Package: firmware-realtek\nVersion: 1\nArchitecture: all\n"
            with mock.patch(
                "tools.finalize_hardware_support_pool._control",
                return_value=control,
            ):
                with self.assertRaisesRegex(PoolFinalizeError, "Installed-Size"):
                    finalize_pool(pool_root, candidates, 1024 * 1024)

    def test_manifest_without_installed_bound_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_root = root / "support"
            (pool_root / "pool").mkdir(parents=True)
            fw = b"fw-bytes"
            (pool_root / "pool/firmware-realtek_1_all.deb").write_bytes(fw)
            packages_payload = b"Package: firmware-realtek\n"
            packages_gzip_payload = b"gzip-placeholder"
            (pool_root / "Packages").write_bytes(packages_payload)
            (pool_root / "Packages.gz").write_bytes(packages_gzip_payload)
            manifest = {
                "schema_version": 1,
                "suite": "trixie",
                "architecture": "amd64",
                "package_count": 1,
                "total_bytes": len(fw),
                "provided_candidate_packages": [_FW],
                "provided_firmware_packages": [_FW],
                "provided_microcode_packages": [],
                "broad_firmware_packages": [_FW],
                "firmware_providers": {"rtl.bin": [_FW]},
                "unavailable_candidate_packages": [],
                "packages": [
                    {
                        "package": _FW,
                        "version": "1",
                        "architecture": "all",
                        "filename": "pool/firmware-realtek_1_all.deb",
                        "size": len(fw),
                        "sha256": _sha(fw),
                        "candidate": True,
                        # No installed_bytes: old compressed-only manifest.
                    }
                ],
                "repository_indexes": {
                    "Packages": {
                        "size": len(packages_payload),
                        "sha256": _sha(packages_payload),
                    },
                    "Packages.gz": {
                        "size": len(packages_gzip_payload),
                        "sha256": _sha(packages_gzip_payload),
                    },
                },
            }
            (pool_root / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            from greia_installer.hardware_support import HardwareSupportPoolError

            with self.assertRaises(HardwareSupportPoolError):
                VerifiedHardwareSupportPool.load(pool_root)


if __name__ == "__main__":
    unittest.main()

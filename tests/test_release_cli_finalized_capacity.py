"""T02: release CLI enforces full finalized-slot capacity via single owner.

Proves, through the real production path, that profile-based
``tools/greia_update.py build`` refuses guaranteed-unstageable bundles
before output publication using the same finalized-slot capacity formula
as runtime::

    max(base, minimum) + support installed-size bound
        + finalization growth + metadata/reserve <= slot capacity

Production path crossed: ``main(build --profile-file)`` ->
``_check_profile_capacity`` (derives the support bound from verified
hardware-support metadata, delegates the decision to the single owner
``greia_installer.layout.require_finalized_slot_capacity``) ->
``build_update_bundle``/``inspect_update_bundle``. The agreement leg
compares the CLI result against the real
``SlotWriter.required_slot_bytes()`` for identical facts.

No SSH, mounts, flashing, Docker, signing or network involved. All
fixtures live in disposable tmpdirs.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = PROJECT_ROOT / "tools" / "greia_update.py"

spec = importlib.util.spec_from_file_location("greia_update_tool_t02", TOOL_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

from greia_installer.hardware_support import (  # noqa: E402
    HardwareSupportPoolError,
    VerifiedHardwareSupportPool,
    installed_size_bound_from_support_archive,
    support_installed_size_bound,
)
from greia_installer.layout import require_finalized_slot_capacity  # noqa: E402
from greia_platform.slot_writer import (  # noqa: E402
    FINALIZATION_GROWTH_BYTES,
    SLOT_METADATA_RESERVE_BYTES,
    SlotWriter,
    VerifiedReleaseMember,
)

try:
    import zstandard

    _ZSTANDARD = True
except ImportError:  # pragma: no cover - test host carries zstandard
    _ZSTANDARD = False

ACER_PROFILE = PROJECT_ROOT / "build" / "profiles" / "acer-aspire-one-i386-ab.toml"
GENERIC_PROFILE = PROJECT_ROOT / "build" / "profiles" / "legacy-x86-i686.toml"

ACER_SLOT_BYTES = 1610612736
GENERIC_SLOT_BYTES = 1073741824

MIB = 1024 * 1024

_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_payload(directory: Path) -> Path:
    # Tiny fixture for the DEVELOPER-ONLY unverified seam: the file itself
    # only needs valid zstd framing. Production facts travel via the payload
    # receipt (see test_payload_receipt_binding.py); every profile-based
    # argv below carries --developer-allow-unverified-payload-facts.
    payload = directory / "payload.ext4.zst"
    payload.write_bytes(_ZSTD_MAGIC + b"\x00" * 4096)
    return payload


def _write_support_archive(
    directory: Path,
    *,
    name: str,
    members: list[tuple[str, bytes]],
) -> Path:
    assert _ZSTANDARD, "zstandard backend is required for support fixtures"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for arcname, data in members:
            info = tarfile.TarInfo(name=arcname)
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            tar.addfile(info, io.BytesIO(data))
    compressed = zstandard.ZstdCompressor().compress(buffer.getvalue())
    output = directory / name
    output.write_bytes(compressed)
    return output


def _support_manifest(
    deb_payload: bytes, installed_bytes: int, *, deb_name: str = "pool/firmware-test_1_all.deb"
) -> dict:
    packages_payload = b"Package: firmware-test\n"
    packages_gzip_payload = b"gzip-placeholder"
    return {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 1,
        "total_bytes": len(deb_payload),
        "total_installed_bytes": installed_bytes,
        "provided_candidate_packages": ["firmware-test"],
        "provided_firmware_packages": ["firmware-test"],
        "provided_microcode_packages": [],
        "broad_firmware_packages": ["firmware-test"],
        "firmware_providers": {"rtl.bin": ["firmware-test"]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": "firmware-test",
                "version": "1",
                "architecture": "all",
                "filename": deb_name,
                "size": len(deb_payload),
                "sha256": _sha(deb_payload),
                "candidate": True,
                "installed_bytes": installed_bytes,
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


def _make_support_archive(
    directory: Path,
    *,
    name: str = "hw-support.tar.zst",
    deb_payload: bytes = b"tiny-deb",
    installed_bytes: int = 200 * MIB,
) -> Path:
    """Build a verifiable hardware-support.tar.zst with crafted accounting.

    The compressed ``.deb`` member stays tiny while the manifest's
    ``installed_bytes``/``total_installed_bytes`` carry a large installed
    footprint — the sensitivity control that proves the CLI bound comes
    from verified metadata, never compressed bytes.
    """
    manifest = _support_manifest(deb_payload, installed_bytes)
    return _write_support_archive(
        directory,
        name=name,
        members=[
            ("manifest.json", json.dumps(manifest).encode("utf-8")),
            ("Packages", b"Package: firmware-test\n"),
            ("Packages.gz", b"gzip-placeholder"),
            ("pool/firmware-test_1_all.deb", deb_payload),
        ],
    )


def _make_pool_dir(root: Path, *, installed_bytes: int = 32 * 1024) -> Path:
    """Write a minimal load()-verifiable hardware-support pool directory."""
    pool = root / "hw-pool"
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    payload = b"firmware"
    (deb_dir / "firmware-realtek_1_all.deb").write_bytes(payload)
    packages_payload = b"Package: firmware-realtek\n"
    packages_gzip_payload = b"gzip-placeholder"
    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 1,
        "total_bytes": len(payload),
        "total_installed_bytes": len(payload) + installed_bytes,
        "provided_candidate_packages": ["firmware-realtek"],
        "provided_firmware_packages": ["firmware-realtek"],
        "provided_microcode_packages": [],
        "broad_firmware_packages": ["firmware-realtek"],
        "firmware_providers": {"rtl.bin": ["firmware-realtek"]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": "firmware-realtek",
                "version": "1",
                "architecture": "all",
                "filename": "pool/firmware-realtek_1_all.deb",
                "size": len(payload),
                "sha256": _sha(payload),
                "candidate": True,
                "installed_bytes": len(payload) + installed_bytes,
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
    (pool / "Packages").write_bytes(packages_payload)
    (pool / "Packages.gz").write_bytes(packages_gzip_payload)
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool


def _build_argv(
    tmp: Path,
    payload: Path,
    *,
    base: int,
    minimum: int | None,
    profile: Path,
    output: Path,
    hardware_support: Path | None = None,
) -> list[str]:
    argv = [
        "build",
        "--payload",
        str(payload),
        "--payload-uncompressed-bytes",
        str(base),
        "--developer-allow-unverified-payload-facts",
        "--profile-file",
        str(profile),
        "--version",
        "0.14.0",
        "--persist-read-min",
        "1",
        "--persist-read-max",
        "1",
        "--persist-write",
        "1",
        "--output",
        str(output),
    ]
    if minimum is not None:
        argv.extend(["--minimum-slot-bytes", str(minimum)])
    if hardware_support is not None:
        argv.extend(["--hardware-support", str(hardware_support)])
    return argv


def _member(base: int, minimum: int) -> VerifiedReleaseMember:
    hw = b"hwset-member"
    return VerifiedReleaseMember(
        release_id="greia-0.15.0",
        payload_sha256=_sha(b"payload"),
        payload_size=7,
        payload_uncompressed_bytes=base,
        minimum_slot_bytes=minimum,
        hardware_support_sha256=_sha(hw),
        hardware_support_size=len(hw),
    )


class ReleaseCliFinalizedCapacityTests(unittest.TestCase):
    def test_platform_reserve_bounds_are_current(self) -> None:
        self.assertEqual(FINALIZATION_GROWTH_BYTES, 64 * MIB)
        self.assertEqual(SLOT_METADATA_RESERVE_BYTES, 16 * MIB)

    def test_fits_before_reserves_but_fails_after_refused(self) -> None:
        # 1 GiB base/minimum fits the 1 GiB generic slot under the old
        # base-only guard, but the finalized total (base + 64 MiB growth
        # + 16 MiB reserve) exceeds it and must be refused before output.
        base = minimum = 1000000000
        required = minimum + FINALIZATION_GROWTH_BYTES + SLOT_METADATA_RESERVE_BYTES
        self.assertGreater(required, GENERIC_SLOT_BYTES)
        target = module._target_from_profile_file(GENERIC_PROFILE)
        with self.assertRaisesRegex(module.SystemUpdateError, "cross-profile"):
            module._check_profile_capacity(
                target,
                payload_uncompressed_bytes=base,
                minimum_slot_bytes=minimum,
            )
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _make_payload(tmp)
            output = tmp / "out.greiaupdate"
            rc = module.main(
                _build_argv(
                    tmp,
                    payload,
                    base=base,
                    minimum=minimum,
                    profile=GENERIC_PROFILE,
                    output=output,
                )
            )
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())

    def test_refusal_reports_every_capacity_fact(self) -> None:
        base = minimum = 1000000000
        required = minimum + FINALIZATION_GROWTH_BYTES + SLOT_METADATA_RESERVE_BYTES
        target = module._target_from_profile_file(GENERIC_PROFILE)
        with self.assertRaisesRegex(module.SystemUpdateError, "legacy-x86-i686") as ctx:
            module._check_profile_capacity(
                target,
                payload_uncompressed_bytes=base,
                minimum_slot_bytes=minimum,
            )
        message = str(ctx.exception)
        for token in (
            str(GENERIC_SLOT_BYTES),
            f"base={base}",
            f"minimum={minimum}",
            "support_installed=0",
            f"finalization_growth={FINALIZATION_GROWTH_BYTES}",
            f"metadata_reserve={SLOT_METADATA_RESERVE_BYTES}",
            f"required={required}",
        ):
            self.assertIn(token, message)

    def test_support_accepted_at_bundle_time_with_machine_check_deferred(self) -> None:
        # Acer candidate sized so the finalized total fits with support
        # term 0 but would exceed the slot under the old whole-pool term.
        # Bundle time has no machine inventory: it proves base payload plus
        # generic reserves fit and verifies the support metadata, while the
        # exact machine-selected capacity is enforced pre-mutation by the
        # installer/updater gates through the same formula owner.
        base = minimum = 1500000000
        support_bound = 100 * MIB
        without = minimum + FINALIZATION_GROWTH_BYTES + SLOT_METADATA_RESERVE_BYTES
        self.assertLessEqual(without, ACER_SLOT_BYTES)
        self.assertGreater(without + support_bound, ACER_SLOT_BYTES)
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _make_payload(tmp)
            support = _make_support_archive(
                tmp, deb_payload=b"tiny-deb", installed_bytes=support_bound
            )
            # Compressed bytes stay tiny: acceptance must not depend on the
            # archive size either way.
            self.assertLess(support.stat().st_size, MIB)
            accepted = tmp / "accepted.greiaupdate"
            rc = module.main(
                _build_argv(
                    tmp,
                    payload,
                    base=base,
                    minimum=minimum,
                    profile=ACER_PROFILE,
                    output=accepted,
                )
            )
            self.assertEqual(rc, 0)
            self.assertTrue(accepted.is_file())
            bundled = tmp / "bundled-with-support.greiaupdate"
            rc = module.main(
                _build_argv(
                    tmp,
                    payload,
                    base=base,
                    minimum=minimum,
                    profile=ACER_PROFILE,
                    output=bundled,
                    hardware_support=support,
                )
            )
            self.assertEqual(rc, 0)
            self.assertTrue(bundled.is_file())
            # Corrupt support metadata is still refused at bundle time: the
            # verification side effect stays even though the capacity term
            # no longer uses the whole-pool total.
            tampered = tmp / "tampered.tar.zst"
            raw = bytearray(support.read_bytes())
            raw[len(raw) // 2] ^= 0xFF
            tampered.write_bytes(bytes(raw))
            refused = tmp / "refused.greiaupdate"
            rc = module.main(
                _build_argv(
                    tmp,
                    payload,
                    base=base,
                    minimum=minimum,
                    profile=ACER_PROFILE,
                    output=refused,
                    hardware_support=tampered,
                )
            )
            self.assertEqual(rc, 2)
            self.assertFalse(refused.exists())

    def test_valid_acer_candidate_accepted(self) -> None:
        base = 1073741824
        minimum = 1074790400
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _make_payload(tmp)
            output = tmp / "greia-0.14.0-acer-aspire-one-i386-ab.greiaupdate"
            rc = module.main(
                _build_argv(
                    tmp,
                    payload,
                    base=base,
                    minimum=minimum,
                    profile=ACER_PROFILE,
                    output=output,
                )
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())
            from greia_platform.system_updates import inspect_update_bundle

            inspected = inspect_update_bundle(output)
            self.assertEqual(inspected.manifest.profile, "acer-aspire-one-i386-ab")
            self.assertEqual(
                inspected.manifest.payload_minimum_slot_bytes, minimum
            )

    def test_absent_support_yields_zero_bound(self) -> None:
        self.assertEqual(module._support_installed_bytes(None), 0)
        self.assertEqual(support_installed_size_bound(None), 0)

    def test_installed_size_from_verified_metadata_not_compressed_bytes(self) -> None:
        installed = 200 * MIB
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            support = _make_support_archive(
                tmp, deb_payload=b"tiny-deb", installed_bytes=installed
            )
            # Sensitivity control: compressed bytes are orders of magnitude
            # below the installed footprint; the bound must be the latter.
            self.assertLess(support.stat().st_size, MIB)
            self.assertEqual(
                installed_size_bound_from_support_archive(support), installed
            )
            self.assertEqual(
                module._support_installed_bytes(support), installed
            )
            pool = _make_pool_dir(tmp)
            verified = VerifiedHardwareSupportPool.load(pool)
            self.assertEqual(
                support_installed_size_bound(pool), verified.total_installed_bytes
            )
            self.assertGreater(verified.total_installed_bytes, 0)

    def test_tampered_support_archive_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            # Inflated installed total whose package sum disagrees: the
            # manifest is doctored before compression, so framing stays valid
            # while the installed accounting no longer verifies.
            deb = b"tiny-deb"
            manifest = _support_manifest(deb, 200 * MIB)
            manifest["total_installed_bytes"] = 200 * MIB + 1
            broken = _write_support_archive(
                tmp,
                name="broken.tar.zst",
                members=[
                    ("manifest.json", json.dumps(manifest).encode("utf-8")),
                    ("Packages", b"Package: firmware-test\n"),
                    ("Packages.gz", b"gzip-placeholder"),
                    ("pool/firmware-test_1_all.deb", deb),
                ],
            )
            with self.assertRaises(HardwareSupportPoolError):
                installed_size_bound_from_support_archive(broken)
            # A manifest digest that does not match the member bytes.
            swapped_manifest = _support_manifest(b"other-bytes", MIB)
            swapped = _write_support_archive(
                tmp,
                name="swapped.tar.zst",
                members=[
                    ("manifest.json", json.dumps(swapped_manifest).encode("utf-8")),
                    ("Packages", b"Package: firmware-test\n"),
                    ("Packages.gz", b"gzip-placeholder"),
                    ("pool/firmware-test_1_all.deb", b"different-bytes"),
                ],
            )
            with self.assertRaises(HardwareSupportPoolError):
                installed_size_bound_from_support_archive(swapped)
            with self.assertRaises(HardwareSupportPoolError):
                installed_size_bound_from_support_archive(tmp / "missing.tar.zst")

    def test_cli_proves_base_reserves_while_writer_proves_selected_support(self) -> None:
        # Bundle time has no machine inventory: the CLI proves base payload
        # plus generic reserves against the profile slot (support term 0),
        # while the writer/owner formula proves the same base plus the
        # verified selected-set bound. One formula owner, two stages.
        base = minimum = 1400000000
        support_bound = 100 * MIB
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            support = _make_support_archive(
                tmp, deb_payload=b"tiny-deb", installed_bytes=support_bound
            )
            bound = module._support_installed_bytes(support)
            self.assertEqual(bound, support_bound)
            member = _member(base, minimum)
            writer_required = SlotWriter().required_slot_bytes(member, bound)
            owner_required = require_finalized_slot_capacity(
                slot_bytes=ACER_SLOT_BYTES,
                base_bytes=base,
                minimum_slot_bytes=minimum,
                support_installed_bytes=bound,
            )
            self.assertEqual(writer_required, owner_required)
            target = module._target_from_profile_file(ACER_PROFILE)
            cli_required = module._check_profile_capacity(
                target,
                payload_uncompressed_bytes=base,
                minimum_slot_bytes=minimum,
                hardware_support_path=support,
            )
            self.assertEqual(
                cli_required,
                max(base, minimum)
                + FINALIZATION_GROWTH_BYTES
                + SLOT_METADATA_RESERVE_BYTES,
            )
            self.assertEqual(cli_required, writer_required - support_bound)

    def test_explicit_identity_builds_skip_profile_capacity_proof(self) -> None:
        # No --profile-file means no profile slot bound: even facts that
        # would fail the generic profile check must still build (no guessing).
        # Explicit identity is a DEVELOPER-ONLY low-level seam
        # (R4-G3-RECEIPT-HARDENING): bare typed sizes now require the
        # developer seam flag, receipt verification otherwise applies.
        base = minimum = 1600000000
        target = module.UpdateTarget("legacy-x86", "i386", "legacy-x86-i686", None, None)
        self.assertIsNone(
            module._check_profile_capacity(
                target,
                payload_uncompressed_bytes=base,
                minimum_slot_bytes=minimum,
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _make_payload(tmp)
            # Bare typed sizes without receipt and without the developer
            # seam now refuse with no output.
            refused = tmp / "explicit-refused.greiaupdate"
            rc = module.main(
                [
                    "build",
                    "--payload",
                    str(payload),
                    "--payload-uncompressed-bytes",
                    str(base),
                    "--minimum-slot-bytes",
                    str(minimum),
                    "--platform-family",
                    "legacy-x86",
                    "--architecture",
                    "i386",
                    "--profile",
                    "legacy-x86-i686",
                    "--version",
                    "0.14.0",
                    "--persist-read-min",
                    "1",
                    "--persist-read-max",
                    "1",
                    "--persist-write",
                    "1",
                    "--output",
                    str(refused),
                ]
            )
            self.assertEqual(rc, 2)
            self.assertFalse(refused.exists())
            output = tmp / "explicit.greiaupdate"
            rc = module.main(
                [
                    "build",
                    "--payload",
                    str(payload),
                    "--payload-uncompressed-bytes",
                    str(base),
                    "--minimum-slot-bytes",
                    str(minimum),
                    "--developer-allow-unverified-payload-facts",
                    "--platform-family",
                    "legacy-x86",
                    "--architecture",
                    "i386",
                    "--profile",
                    "legacy-x86-i686",
                    "--version",
                    "0.14.0",
                    "--persist-read-min",
                    "1",
                    "--persist-read-max",
                    "1",
                    "--persist-write",
                    "1",
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())

    def test_unverifiable_support_refused_before_output(self) -> None:
        base = 1073741824
        minimum = 1074790400
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            payload = _make_payload(tmp)
            bogus = tmp / "bogus.tar.zst"
            bogus.write_bytes(_ZSTD_MAGIC + b"not-a-tar")
            output = tmp / "out.greiaupdate"
            rc = module.main(
                _build_argv(
                    tmp,
                    payload,
                    base=base,
                    minimum=minimum,
                    profile=ACER_PROFILE,
                    output=output,
                    hardware_support=bogus,
                )
            )
            self.assertEqual(rc, 2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

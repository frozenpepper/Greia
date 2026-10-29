"""POSTR1-P3-UPDATE-PROOF3: shipped updater product composition (Gate P3).

Drives the shipped composition root
``greia_platform.system_updates.build_live_update_service()`` with its
installed-system defaults (no ``seams`` argument) against a trusted A/B
``installed-layout.json``. Trust/layout/boot-backend resolve and the
installed default now binds the production inactive-slot destination
factories (POSTR1-P3-UPDATE-SEAMS); with no devices present, staging the
current inbox candidate fails closed naming the inactive-slot device
path, with no fallback to a fake/loop store.

POSTR1-P3-UPDATE-ACTIVATION removed the
``ConditionPathExists=/run/greia-os/enable-privileged-transactions`` gate
from the shipped units: the unit-contract tests below assert the
activated contract (gate absent, narrow on-demand socket activation
preserved structurally). The preregistered pre-intro timing comparison
(P1-P4) is DEFERRED by owner authority
(``postr1--POSTR1-P3-PREINTRO-TIMING-MEASURE--001``) and is not exercised
or claimed here.

All state stays in disposable tmpdirs; no valued disk, no loop device.
Device-positive staging on disposable loopback is proven separately on a
privileged Linux host (attempt evidence, outside this tree).
"""

from __future__ import annotations

import configparser
import json
import os
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest import mock

from greia_platform.grub_ab import GrubEnvBackend
from greia_platform.persistent_layout import (
    InstalledLayoutRecord,
    emit_persist_schema_marker,
    persist_schema_marker_path,
)
from greia_platform.system_updates import (
    SystemUpdateInbox,
    UpdateBackendUnavailable,
    UpdateSlotSeams,
    build_live_update_service,
    build_update_bundle,
    load_installed_layout_record,
)
from update_mount_fixtures import installed_mount_patchers


@contextmanager
def _patched_env(**overrides: str):
    previous = dict(os.environ)
    os.environ.update(overrides)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)


ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = (
    ROOT / "build" / "overlay" / "etc" / "systemd" / "system"
    / "greia-system-update.service"
)
SOCKET_PATH = (
    ROOT / "build" / "overlay" / "etc" / "systemd" / "system"
    / "greia-system-update.socket"
)

_SLOT_BYTES = 1024 * 1024 * 1024

_FAMILY = "legacy-x86"
_ARCH = "i386"
_PROFILE = "legacy-x86-i686"
_VERSION = "0.16.0"

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32

_R8_ID = "greia-0.16.0"
_R8_SEQ = 8
_R9_ID = "greia-0.17.0"
_R9_SEQ = 9

# (POSTR1-P3-UPDATE-ACTIVATION removed the enable gate; the activated
# contract asserts its absence, so no gate constant is pinned here.)


def _record_dict() -> dict[str, object]:
    return {
        "accepted_release_id": _R8_ID,
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": _PROFILE,
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": "legacy-bios-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": _FAMILY,
        "schema_version": 1,
        "slot_bytes": _SLOT_BYTES,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }


def _canonical_record(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _payload(size: int, tag: bytes) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size))
    raw = tag + body[len(tag):]
    fixed = bytearray(raw)
    if fixed[510:512] == b"\x55\xaa":
        fixed[510:512] = b"\x00\x00"
    if fixed[512:520] == b"EFI PART":
        fixed[512:520] = b"\x00" * 8
    return bytes(fixed)


def _parse_unit(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str  # type: ignore[assignment]
    parser.read(path, encoding="utf-8")
    return parser


def _directive_values(path: Path, name: str) -> set[str]:
    """Collect every value of a (possibly repeated) unit directive."""
    values: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(name + "="):
            values.update(stripped.split("=", 1)[1].split())
    return values


def _assert_no_condition_directive(path: Path) -> None:
    """The activated contract carries no Condition* directive (comments ok).

    POSTR1-P3-UPDATE-ACTIVATION removed the enable gate: ``Condition``
    may still appear inside ``#`` comments documenting the removal, but
    never as a parsed ``[Unit]`` directive.
    """
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped or stripped.startswith("["):
            continue
        assert not stripped.startswith("Condition"), (
            f"activated contract must not gate on Condition*: {stripped!r} "
            f"in {path.name}"
        )


def _pool_tree(root: Path, *, dirname: str = "hw-pool") -> Path:
    """Write a minimal verified hardware-support pool (pure file IO)."""
    import hashlib

    fw = b"p3-proof-firmware-bytes"
    uc = b"p3-proof-microcode-bytes"
    pool = root / dirname
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    (deb_dir / "firmware-realtek_1_all.deb").write_bytes(fw)
    (deb_dir / "amd64-microcode_1_amd64.deb").write_bytes(uc)
    packages_payload = b"Package: firmware-realtek\n"
    packages_gzip_payload = b"gzip-placeholder"
    (pool / "Packages").write_bytes(packages_payload)
    (pool / "Packages.gz").write_bytes(packages_gzip_payload)

    def _sha(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 2,
        "total_bytes": len(fw) + len(uc),
        "total_installed_bytes": len(fw) + len(uc) + 2 * 32 * 1024,
        "provided_candidate_packages": ["firmware-realtek", "amd64-microcode"],
        "provided_firmware_packages": ["firmware-realtek"],
        "provided_microcode_packages": ["amd64-microcode"],
        "broad_firmware_packages": ["firmware-realtek"],
        "firmware_providers": {"rtl.bin": ["firmware-realtek"]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": "firmware-realtek", "version": "1",
                "architecture": "all", "filename": "pool/firmware-realtek_1_all.deb",
                "size": len(fw), "sha256": _sha(fw), "candidate": True,
                "installed_bytes": len(fw) + 32 * 1024,
            },
            {
                "package": "amd64-microcode", "version": "1",
                "architecture": "amd64", "filename": "pool/amd64-microcode_1_amd64.deb",
                "size": len(uc), "sha256": _sha(uc), "candidate": True,
                "installed_bytes": len(uc) + 32 * 1024,
            },
        ],
        "repository_indexes": {
            "Packages": {"size": len(packages_payload), "sha256": _sha(packages_payload)},
            "Packages.gz": {"size": len(packages_gzip_payload), "sha256": _sha(packages_gzip_payload)},
        },
    }
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool


def _hw_archive_from_pool(pool_dir: Path, output: Path) -> None:
    """Archive a pool tree as the candidate's tar.zst member (Repair D).

    Mirrors ``tools/build_release.py`` ``build_hardware_support_set``:
    deterministic PAX tar of the exact release tree, zstd-compressed.
    """
    import io
    import tarfile

    import zstandard

    members = [
        pool_dir / "manifest.json",
        pool_dir / "Packages",
        pool_dir / "Packages.gz",
    ]
    members.extend(sorted((pool_dir / "pool").glob("*.deb")))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for member in sorted(
            members, key=lambda p: p.relative_to(pool_dir).as_posix()
        ):
            arcname = member.relative_to(pool_dir).as_posix()
            info = tar.gettarinfo(str(member), arcname=arcname)
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            info.mode = 0o644
            with member.open("rb") as src:
                tar.addfile(info, src)
    output.write_bytes(zstandard.ZstdCompressor(level=3).compress(buffer.getvalue()))


class ShippedDefaultCompositionTests(unittest.TestCase):
    """Shipped defaults bind production seams; staging stays fail-closed."""

    def test_installed_default_binds_production_seams(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_dir = root / "state"
            marker_path = persist_schema_marker_path(state_dir)
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker_path.write_bytes(emit_persist_schema_marker(1))
            layout_path = root / "installed-layout.json"
            layout_path.write_bytes(_canonical_record(_record_dict()))
            boot_dir = root / "boot-control"
            boot_dir.mkdir(parents=True, exist_ok=True)
            grub = GrubEnvBackend.initialize(boot_dir, default_slot="A")
            pool = _pool_tree(root)
            (root / "sysfs").mkdir(parents=True, exist_ok=True)

            # Requirement 1: shipped default composition (no `seams` argument).
            with _patched_env(
                GREIA_SYSTEM_VERSION=_VERSION,
                GREIA_SYSTEM_PLATFORM_FAMILY=_FAMILY,
                GREIA_SYSTEM_ARCHITECTURE=_ARCH,
                GREIA_SYSTEM_PROFILE=_PROFILE,
                GREIA_UPDATE_HARDWARE_SUPPORT_POOL=str(pool),
                GREIA_UPDATE_SYSFS_DEVICES=str(root / "sysfs"),
            ):
                authority = build_live_update_service(
                    state_dir=state_dir,
                    layout_record_path=layout_path,
                    persist_root=state_dir,
                    boot_backend=grub,
                    boot_backend_auto=False,
                )
            backend = authority.backend
            # Trust/layout resolve: backend reports available on the A/B record.
            self.assertTrue(backend.available)
            status = backend.status_payload()
            self.assertTrue(status["available"])
            record = load_installed_layout_record(layout_path)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertIsInstance(record, InstalledLayoutRecord)
            self.assertIsNotNone(record.system_b)
            self.assertEqual(record.boot_control.active_slot, "A")
            self.assertEqual(record.accepted_slot, "A")
            # Default seams bind the production destination factories
            # (POSTR1-P3-UPDATE-SEAMS): the shipped main() path composes
            # with seams=None, so every factory is bound here.
            self.assertIsInstance(backend.seams, UpdateSlotSeams)
            for name in (
                "slot_store_factory",
                "filesystem_factory",
                "package_installer_factory",
                "inventory_factory",
                "support_set_factory",
                "profile_policy_factory",
                "selection_factory",
                "installed_contract_factory",
            ):
                self.assertIsNotNone(
                    getattr(backend.seams, name),
                    f"production {name} must be bound by default",
                )

            # Build one unsigned v3 inbox candidate for the patched identity.
            import zstandard

            work = root / "releases" / "r9"
            work.mkdir(parents=True, exist_ok=True)
            raw = _payload(220 * 1024, b"postr1-red:")
            (work / "slot.ext4.zst").write_bytes(
                zstandard.ZstdCompressor(level=3).compress(raw)
            )
            # Repair D: the bundle carries the candidate's own pool member.
            _hw_archive_from_pool(
                _pool_tree(root, dirname="candidate-pool"), work / "hw.tar.zst"
            )
            bundle = work / "r9.greiaupdate"
            build_update_bundle(
                payload_path=work / "slot.ext4.zst",
                hardware_support_path=work / "hw.tar.zst",
                output_path=bundle,
                version=_R9_ID.split("-", 1)[1],
                release_id=_R9_ID,
                platform_family=_FAMILY,
                architecture=_ARCH,
                profile=_PROFILE,
                payload_uncompressed_bytes=len(raw),
                minimum_slot_bytes=len(raw),
                persist_read_schema_min=1,
                persist_read_schema_max=1,
                persist_write_schema=1,
                release_notes="POSTR1-P1-UPDATER-RED characterization release.",
            )
            SystemUpdateInbox(state_dir).receive(bundle)
            verified = authority.verify_current_candidate()
            self.assertTrue(verified.present)
            self.assertEqual(verified.release_id, _R9_ID)

            # Requirement 3 spies: record destination-seam demand + writes.
            requested: list[str] = []
            original_require = backend._require_seam  # type: ignore[attr-defined]

            def _spying_require(name: str, factory):  # type: ignore[no-untyped-def]
                requested.append(name)
                return original_require(name, factory)

            backend._require_seam = _spying_require  # type: ignore[method-assign]
            layout_before = layout_path.read_bytes()
            boot_before = grub.inspect().default_slot
            journal_file = (
                state_dir / "system-updates" / "journal" / "boot-journal.json"
            )
            state_before = sorted(
                str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
            )
            try:
                # Staging fails closed naming the absent inactive-slot
                # device path (no devices in this offline proof), not a
                # generic crash and never a degraded empty-seam refusal.
                with ExitStack() as stack:
                    for patcher in installed_mount_patchers(_UUID_P_FS):
                        stack.enter_context(patcher)
                    with self.assertRaises(UpdateBackendUnavailable) as raised:
                        authority.stage_current_candidate()
            finally:
                backend._require_seam = original_require  # type: ignore[method-assign]
            message = str(raised.exception)
            self.assertIn("inactive-slot", message)
            self.assertNotIn("destination seam is not configured", message)

            # Requirement 3: no active/accepted slot touched, no fallback to
            # a fake/loop destination store. The production path may demand
            # the support/contract/inventory/filesystem seams and fail
            # closed inside topology observation (no devices here), but it
            # must never reach the raw inactive-slot store or the package
            # installer.
            self.assertNotIn("inactive-slot store", requested)
            self.assertNotIn("slot package installer", requested)
            self.assertFalse(journal_file.exists())
            self.assertEqual(layout_path.read_bytes(), layout_before)
            self.assertEqual(grub.inspect().default_slot, boot_before)
            self.assertEqual(grub.inspect().default_slot, "A")
            state_after = sorted(
                str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
            )
            # Only inbox/status/accepted/journal-parent side effects are
            # allowed; no slot image or loop store appears.
            new_files = [p for p in state_after if p not in state_before]
            for extra in new_files:
                self.assertNotIn("slot-", extra)
                self.assertNotIn(".img", extra)
            self.assertTrue(load_installed_layout_record(layout_path) is not None)
            final_record = load_installed_layout_record(layout_path)
            assert final_record is not None
            self.assertEqual(final_record.accepted_slot, "A")

            # GREEN: the installed composition is closed. Production seams
            # are bound by default; with no devices present, staging
            # refuses at the inactive-slot device path with no slot write,
            # no journal, and no loop/fake fallback store.
            self.assertTrue(backend.available)
            self.assertTrue(status["available"])


class ShippedUnitContractTests(unittest.TestCase):
    """Structured contract on the shipped update unit/socket declarations."""

    def test_service_declarations(self) -> None:
        parser = _parse_unit(SERVICE_PATH)
        # Activated contract (POSTR1-P3-UPDATE-ACTIVATION): the enable
        # gate is absent; on-demand activation is structural (socket
        # Requires/After, no boot target), never a Condition* directive.
        self.assertFalse(parser.has_option("Unit", "ConditionPathExists"))
        _assert_no_condition_directive(SERVICE_PATH)
        self.assertEqual(parser.get("Service", "User").strip(), "root")
        # The offline slot worker runs arbitrary Debian maintainer scripts.
        # systemd sandboxing here caused real physical installer/update
        # failures; locality comes from the Unix socket, not unit filters.
        for directive in (
            "ProtectSystem",
            "CapabilityBoundingSet",
            "AmbientCapabilities",
            "RestrictAddressFamilies",
            "RestrictSUIDSGID",
            "TasksMax",
        ):
            with self.subTest(directive=directive):
                self.assertFalse(parser.has_option("Service", directive))
        self.assertIn(
            "/var/lib/greia-os",
            parser.get("Unit", "RequiresMountsFor"),
        )
        self.assertIn(
            "/run/greia-persist",
            parser.get("Unit", "RequiresMountsFor"),
        )
        # v3 carries no key material: no key trust root is granted.
        raw = SERVICE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("system-update-keys", raw)
        self.assertNotIn("GREIA_UPDATE_TRUSTED_KEY_DIR", raw)
        self.assertIn("GREIA_INSTALLED_LAYOUT_RECORD", raw)
        self.assertNotIn("GREIA_SYSTEM_VERSION", raw)
        self.assertNotIn("GREIA_SYSTEM_PLATFORM_FAMILY", raw)
        self.assertNotIn("GREIA_SYSTEM_ARCHITECTURE", raw)
        self.assertNotIn("GREIA_SYSTEM_PROFILE", raw)
        # Never boot-enabled: no [Install] section, no WantedBy=.
        self.assertFalse(parser.has_section("Install"))
        self.assertNotIn("WantedBy=", raw)

    def test_socket_declarations(self) -> None:
        parser = _parse_unit(SOCKET_PATH)
        # Activated contract: gate absent on the socket too; the listener
        # stays on sockets.target with narrow on-demand identity.
        self.assertFalse(parser.has_option("Unit", "ConditionPathExists"))
        _assert_no_condition_directive(SOCKET_PATH)
        self.assertEqual(
            parser.get("Socket", "ListenStream").strip(),
            "/run/greia-os/system-update.sock",
        )
        self.assertEqual(parser.get("Socket", "SocketMode").strip(), "0660")
        self.assertEqual(parser.get("Socket", "SocketGroup").strip(), "greiapanel")
        self.assertEqual(parser.get("Socket", "Accept").strip(), "no")
        self.assertIn("WantedBy=sockets.target", SOCKET_PATH.read_text(encoding="utf-8"))
        raw = SOCKET_PATH.read_text(encoding="utf-8")
        self.assertNotIn("GREIA_SYSTEM_VERSION", raw)
        self.assertNotIn("GREIA_SYSTEM_PLATFORM_FAMILY", raw)
        self.assertNotIn("GREIA_SYSTEM_ARCHITECTURE", raw)
        self.assertNotIn("GREIA_SYSTEM_PROFILE", raw)


if __name__ == "__main__":
    unittest.main()

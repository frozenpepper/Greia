"""T04: real SystemUpdateService orchestration integration harness.

Replaces the false exact-service claim (``tools/x8_qemu/runner.py`` only
exercises ``SlotWriter``/``SlotFinalizer`` capacity bounds and never imports
the service): this test invokes the real orchestration chain on a
support-carrying candidate through the production composition points:

real v3 inspected bundle -> ``SystemUpdateService`` compatibility ->
``SlotBackedSystemUpdateBackend.stage`` -> PERSIST schema compatibility seam
-> candidate support stage (``CandidateSupportStage.open`` exactly once) ->
support resolution (``pool_to_support_set``) -> full capacity calculation
(``require_finalized_slot_capacity`` == ``SlotWriter.required_slot_bytes``)
-> inactive semantic destination (``store:system-b`` only) -> ``SlotWriter``
-> ``SlotFinalizer`` -> canonical fstab specialization -> package installer
seam -> journal/status -> inbox deletion only after successful stage.

The fixture carries a small valid hardware-support archive: real minimal
``.deb`` files whose Debian ``Installed-Size`` (KiB) control fields drive
the manifest ``installed_bytes`` accounting
(``installed_bytes = Installed-Size * 1024 + 32 KiB`` per
``tools/finalize_hardware_support_pool.py``), a valid
``VerifiedHardwareSupportPool.load()`` structure (manifest, Packages,
Packages.gz, pool/*.deb with size/digest binding, sum equality), and no
network. The final installer is a recording injected implementation that
returns the pool's own verified records (no ``apt-get``/``chroot``).

Single-materialization is instrumented: exactly one
``extract_support_tree`` call, no intermediate ``.tar.zst.tmp`` copy, the
resolver pool and the installer pool are the identical stage-owned
instance, and the staging root is removed on success and on failure.

Sensitivity: stubbing the support factory (wrong digest) or the service
identity (wrong architecture) refuses before any slot contact; a tampered
candidate is preserved in the inbox for retry. The harness proves
orchestration only and claims no kernel/systemd capability behavior.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_platform import candidate_support as _candidate_support
from greia_platform.boot_transaction import BootTransactionJournal
from greia_platform.candidate_support import (
    CandidateSupportStage,
    staging_parent_for,
)
from greia_platform.fstab import FSTAB_REL_PATH, render_fstab
from greia_platform.persistent_layout import emit_persist_schema_marker
from greia_platform.slot_writer import (
    REQUIRED_SLOT_COMPLETENESS_DIRS,
    REQUIRED_SLOT_COMPLETENESS_FILES,
    HardwareInventoryAttestation,
    LoopbackSlotFile,
    SlotProfilePolicy,
    SlotWriter,
    check_slot_completeness,
    resolve_hardware_selection,
)
from greia_platform.system_updates import (
    SlotBackedSystemUpdateBackend,
    SystemIdentity,
    SystemUpdateError,
    SystemUpdateInbox,
    SystemUpdateService,
    UpdateSlotSeams,
    build_update_bundle,
    inspect_update_bundle,
)


_FAMILY = "standard-x86-64"
_ARCH = "x86-64"
_PROFILE = "modern-amd64"

_FIRMWARE = "t04-firmware"
_MICROCODE = "t04-microcode"

_SLOT_BYTES = 1024 * 1024 * 1024

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_UUID_BOOT_FS = "dddddddd-eeee-ffff-0000-111111111111"
_INSTALL_SHA = "ab" * 32

_INVENTORY_TOKEN = "cd" * 32

#: Per-package metadata overhead from tools/finalize_hardware_support_pool.py
#: (``_INSTALLED_BYTES_OVERHEAD_PER_PACKAGE``): ``installed_bytes`` is the
#: Debian ``Installed-Size`` (KiB) payload plus this allowance, never the
#: compressed ``.deb`` bytes.
_INSTALLED_OVERHEAD_BYTES = 32 * 1024

_FW_INSTALLED_KIB = 48
_UC_INSTALLED_KIB = 64


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Minimal real .deb files (ar archive with Installed-Size control metadata)
# ---------------------------------------------------------------------------

def _ar_member(name: str, data: bytes) -> bytes:
    """Encode one GNU ar member (short names only, Debian style)."""
    encoded = (name + "/").encode("ascii")
    if len(encoded) > 16:
        raise ValueError(f"ar member name too long: {name}")
    header = (
        encoded.ljust(16, b" ")
        + b"0".ljust(12, b" ")
        + b"0".ljust(6, b" ")
        + b"0".ljust(6, b" ")
        + b"100644".ljust(8, b" ")
        + str(len(data)).encode("ascii").ljust(10, b" ")
        + b"`\n"
    )
    assert len(header) == 60
    body = bytes(data)
    if len(body) % 2:
        body += b"\n"
    return header + body


def _tar_gz(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for arcname in sorted(members):
            payload = members[arcname]
            info = tarfile.TarInfo(name=arcname)
            info.size = len(payload)
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(payload))
    return gzip.compress(buffer.getvalue(), mtime=0)


def _make_deb(
    path: Path,
    *,
    package: str,
    architecture: str,
    installed_kib: int,
) -> tuple[int, str, int]:
    """Write a minimal valid .deb; return (size, sha256, installed_bytes).

    The ``Installed-Size`` control field is real metadata inside the
    package; the manifest ``installed_bytes`` below derives from it with
    the production formula, so capacity accounting proves the installed
    bound rather than the compressed transfer bytes.
    """
    control = (
        f"Package: {package}\n"
        f"Version: 1\n"
        f"Architecture: {architecture}\n"
        f"Installed-Size: {installed_kib}\n"
        f"Description: T04 orchestration fixture\n"
    ).encode("utf-8")
    data_payload = f"t04-payload-for-{package}\n".encode("utf-8")
    control_tar = _tar_gz({"control": control})
    data_tar = _tar_gz({f"usr/share/t04/{package}.bin": data_payload})
    deb = (
        b"!<arch>\n"
        + _ar_member("debian-binary", b"2.0\n")
        + _ar_member("control.tar.gz", control_tar)
        + _ar_member("data.tar.gz", data_tar)
    )
    path.write_bytes(deb)
    installed_bytes = installed_kib * 1024 + _INSTALLED_OVERHEAD_BYTES
    return len(deb), _sha(deb), installed_bytes


def _pool_tree(root: Path) -> tuple[Path, int]:
    """Write a minimal verified pool; return (pool_dir, total_installed)."""
    pool = root / "support-pool"
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    fw_size, fw_sha, fw_installed = _make_deb(
        deb_dir / f"{_FIRMWARE}_1_all.deb",
        package=_FIRMWARE,
        architecture="all",
        installed_kib=_FW_INSTALLED_KIB,
    )
    uc_size, uc_sha, uc_installed = _make_deb(
        deb_dir / f"{_MICROCODE}_1_amd64.deb",
        package=_MICROCODE,
        architecture="amd64",
        installed_kib=_UC_INSTALLED_KIB,
    )
    packages_text = (
        f"Package: {_FIRMWARE}\nVersion: 1\nArchitecture: all\n"
        f"Filename: pool/{_FIRMWARE}_1_all.deb\nSize: {fw_size}\n"
        f"SHA256: {fw_sha}\nInstalled-Size: {_FW_INSTALLED_KIB}\n\n"
        f"Package: {_MICROCODE}\nVersion: 1\nArchitecture: amd64\n"
        f"Filename: pool/{_MICROCODE}_1_amd64.deb\nSize: {uc_size}\n"
        f"SHA256: {uc_sha}\nInstalled-Size: {_UC_INSTALLED_KIB}\n\n"
    ).encode("utf-8")
    packages_gz = gzip.compress(packages_text, mtime=0)
    (pool / "Packages").write_bytes(packages_text)
    (pool / "Packages.gz").write_bytes(packages_gz)
    total = fw_size + uc_size
    total_installed = fw_installed + uc_installed
    manifest = {
        "schema_version": 1,
        "suite": "trixie",
        "architecture": "amd64",
        "package_count": 2,
        "total_bytes": total,
        "total_installed_bytes": total_installed,
        "provided_candidate_packages": [_FIRMWARE, _MICROCODE],
        "provided_firmware_packages": [_FIRMWARE],
        "provided_microcode_packages": [_MICROCODE],
        "broad_firmware_packages": [_FIRMWARE],
        "firmware_providers": {"t04-firmware.bin": [_FIRMWARE]},
        "unavailable_candidate_packages": [],
        "dependency_closures": {
            _FIRMWARE: [_FIRMWARE],
            _MICROCODE: [_MICROCODE],
        },
        "packages": [
            {
                "package": _FIRMWARE, "version": "1",
                "architecture": "all",
                "filename": f"pool/{_FIRMWARE}_1_all.deb",
                "size": fw_size, "sha256": fw_sha, "candidate": True,
                "installed_bytes": fw_installed,
            },
            {
                "package": _MICROCODE, "version": "1",
                "architecture": "amd64",
                "filename": f"pool/{_MICROCODE}_1_amd64.deb",
                "size": uc_size, "sha256": uc_sha, "candidate": True,
                "installed_bytes": uc_installed,
            },
        ],
        "repository_indexes": {
            "Packages": {"size": len(packages_text), "sha256": _sha(packages_text)},
            "Packages.gz": {"size": len(packages_gz), "sha256": _sha(packages_gz)},
        },
    }
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool, total_installed


def _hw_archive(pool_dir: Path, output: Path) -> bytes:
    """Deterministic tar.zst of a pool tree."""
    import zstandard

    members = [pool_dir / "manifest.json", pool_dir / "Packages", pool_dir / "Packages.gz"]
    members.extend(sorted((pool_dir / "pool").glob("*.deb")))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for member in sorted(members, key=lambda p: p.relative_to(pool_dir).as_posix()):
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
    compressed = zstandard.ZstdCompressor(level=3).compress(buffer.getvalue())
    output.write_bytes(compressed)
    return compressed


def _payload_raw(size: int = 128 * 1024) -> bytes:
    return bytes((index * 31 + 7) % 256 for index in range(size))


def _candidate_bundle(
    root: Path,
    raw: bytes,
    *,
    name: str,
    hw_path: Path,
    release_id: str = "greia-t04-orchestration",
    minimum_slot_bytes: int | None = None,
) -> Path:
    import zstandard

    work = root / f"release-{name}"
    work.mkdir(parents=True, exist_ok=True)
    payload_path = work / "slot.ext4.zst"
    payload_path.write_bytes(zstandard.ZstdCompressor(level=3).compress(raw))
    bundle = work / name
    if bundle.exists():
        bundle.unlink()
    build_update_bundle(
        payload_path=payload_path,
        hardware_support_path=hw_path,
        output_path=bundle,
        version="0.99.0",
        release_id=release_id,
        platform_family=_FAMILY,
        architecture=_ARCH,
        profile=_PROFILE,
        payload_uncompressed_bytes=len(raw),
        minimum_slot_bytes=minimum_slot_bytes if minimum_slot_bytes is not None else len(raw),
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
        release_notes="T04 orchestration proof release.",
    )
    return bundle


def _layout_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.14.0",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": _PROFILE,
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": "modern-gpt-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": _FAMILY,
        "schema_version": 1,
        "slot_bytes": _SLOT_BYTES,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _populate_completeness(mount_dir: Path) -> None:
    for rel_path in REQUIRED_SLOT_COMPLETENESS_DIRS:
        (mount_dir / rel_path).mkdir(parents=True, exist_ok=True)
    for rel_path in REQUIRED_SLOT_COMPLETENESS_FILES:
        candidate = mount_dir / rel_path
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if candidate.is_symlink() or not candidate.is_file():
            candidate.write_bytes(b"#!/bin/sh\nexit 0\n")
            try:
                candidate.chmod(0o755)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Harness: production support-stage path, injected destination seams
# ---------------------------------------------------------------------------

class _DiskFilesystem:
    """Non-destructive destination filesystem writing through to a tmpdir."""

    def __init__(self, mount_dir: Path, ops: list[str]) -> None:
        self.mount_dir = mount_dir
        self.ops = ops
        self.files: dict[str, bytes] = {}
        self.bound_uuid: str | None = None
        self.mounted = False

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self.ops.append("bind")
        self.bound_uuid = filesystem_uuid

    def expand_to_capacity(self) -> None:
        self.ops.append("expand")

    def mount(self) -> Path:
        self.ops.append("mount")
        self.mounted = True
        return self.mount_dir

    def unmount(self) -> None:
        self.ops.append("unmount")
        self.mounted = False

    def sync(self) -> None:
        self.ops.append("sync")

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self.mounted:
            raise AssertionError("slot writes require a mounted destination")
        if ".." in Path(relative_path).parts or Path(relative_path).is_absolute():
            raise AssertionError(f"unsafe slot write: {relative_path}")
        self.ops.append(f"write:{relative_path}")
        self.files[relative_path] = bytes(data)
        target = self.mount_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required if name not in self.files)

    def check_completeness(self) -> None:
        self.ops.append("completeness")
        check_slot_completeness(self.mount_dir)

    def check_health(self) -> None:
        self.ops.append("health")


class _RecordingInstaller:
    """Recording injected installer returning the pool's verified records."""

    def __init__(self, harness: "_Harness") -> None:
        self._harness = harness

    def install(
        self, firmware: tuple[str, ...], microcode: tuple[str, ...]
    ) -> tuple[object, ...]:
        harness = self._harness
        harness.installer_calls.append((tuple(firmware), tuple(microcode)))
        stage = harness.support_stage
        assert isinstance(stage, CandidateSupportStage)
        harness.installer_pool_ids.append(id(stage.pool))
        support = harness.last_support
        assert support is not None
        names = tuple(firmware) + tuple(microcode)
        return tuple(support.record_for(name) for name in names)


class _Harness:
    """One stage's seams: real support materialization, fake destinations."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_dir = root / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.contacts: list[str] = []
        self.filesystem_ops: list[str] = []
        self.installer_calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
        self.resolver_pool_ids: list[int] = []
        self.installer_pool_ids: list[int] = []
        self.support_stage: CandidateSupportStage | None = None
        self.last_support: object | None = None
        self.cleanup_count = 0
        self.last_closed_stage: CandidateSupportStage | None = None
        mount_dir = root / "mnt"
        mount_dir.mkdir(parents=True, exist_ok=True)
        _populate_completeness(mount_dir)
        self.filesystem = _DiskFilesystem(mount_dir, self.filesystem_ops)

    def staging_parent(self) -> Path:
        parent = staging_parent_for(self.state_dir)
        parent.mkdir(parents=True, exist_ok=True)
        return parent

    # -- factories ------------------------------------------------------
    def slot_store_factory(self, destination: object) -> object:
        role = str(getattr(destination, "role", "system-b"))
        self.contacts.append(f"store:{role}")
        capacity = int(getattr(destination, "slot_capacity_bytes", 0))
        return LoopbackSlotFile.create(self.root / f"slot-{role}.img", capacity)

    def filesystem_factory(self) -> object:
        self.contacts.append("filesystem")
        return self.filesystem

    def package_installer_factory(self) -> object:
        self.contacts.append("package-installer")
        return _RecordingInstaller(self)

    def inventory_factory(self) -> object:
        self.contacts.append("inventory")
        return HardwareInventoryAttestation(token=_INVENTORY_TOKEN)

    def support_set_factory(self, bundle: object) -> object:
        from greia_installer.slots import pool_to_support_set

        self.contacts.append("support")
        manifest = getattr(bundle, "manifest")
        identity = (
            str(getattr(bundle, "path", "")),
            getattr(manifest, "hardware_support_sha256", None),
            getattr(manifest, "hardware_support_size", None),
            getattr(manifest, "hardware_support_extracted_bytes_bound", None),
        )
        current = self.support_stage
        if (
            current is not None
            and isinstance(current, CandidateSupportStage)
            and not current.closed
            and current.stage_identity() == identity
        ):
            stage = current
        else:
            if current is not None:
                try:
                    current.close()
                except Exception:
                    pass
            stage = CandidateSupportStage.open(
                Path(getattr(bundle, "path")),
                manifest,
                self.staging_parent(),
            )
            self.support_stage = stage
        pool = getattr(stage, "pool", None)
        self.resolver_pool_ids.append(id(pool))
        support = pool_to_support_set(
            pool,
            support_digest=manifest.hardware_support_sha256,
            support_size=manifest.hardware_support_size,
        )
        self.last_support = support
        return support

    def profile_policy_factory(self, record: object) -> object:
        self.contacts.append("policy")
        return SlotProfilePolicy(
            layout_id=str(getattr(record, "layout_id")),
            system_slot_bytes=int(getattr(record, "slot_bytes")),
            boot_backend=str(getattr(record, "boot_backend")),
            persist_filesystem_uuid=str(
                getattr(getattr(record, "persist"), "filesystem_uuid")
            ),
            boot_control_filesystem_uuid=_UUID_BOOT_FS,
        )

    def selection_factory(self, support: object, token: str) -> object | None:
        from greia_platform.hardware_enablement import (
            HardwareSupportPlan,
            HardwareSupportRecommendation,
            SupportDisposition,
            SupportKind,
        )

        self.contacts.append("selection")
        if token != _INVENTORY_TOKEN:
            raise AssertionError("selection token must be the attested inventory token")
        plan = HardwareSupportPlan(
            inventory_token=token,
            recommendations=(
                HardwareSupportRecommendation(
                    package=_FIRMWARE,
                    kind=SupportKind.FIRMWARE,
                    disposition=SupportDisposition.AUTO_ELIGIBLE,
                    source="t04-proof",
                ),
                HardwareSupportRecommendation(
                    package=_MICROCODE,
                    kind=SupportKind.MICROCODE,
                    disposition=SupportDisposition.AUTO_ELIGIBLE,
                    source="t04-proof",
                ),
            ),
            complete=True,
        )
        return resolve_hardware_selection(plan=plan, support=support)  # type: ignore[arg-type]

    def installed_contract_factory(self) -> bytes:
        self.contacts.append("contract")
        return emit_persist_schema_marker(1)

    def support_pool_factory(self, bundle: object) -> object | None:
        stage = self.support_stage
        if stage is None or getattr(stage, "closed", True):
            return None
        return getattr(stage, "pool", None)

    def support_stage_cleanup(self) -> None:
        stage = self.support_stage
        self.support_stage = None
        if stage is None:
            return
        self.cleanup_count += 1
        self.last_closed_stage = stage  # type: ignore[assignment]
        try:
            stage.close()
        except Exception:
            pass

    def seams(self) -> UpdateSlotSeams:
        return UpdateSlotSeams(
            slot_store_factory=self.slot_store_factory,
            filesystem_factory=self.filesystem_factory,
            package_installer_factory=self.package_installer_factory,
            inventory_factory=self.inventory_factory,
            support_set_factory=self.support_set_factory,
            profile_policy_factory=self.profile_policy_factory,
            selection_factory=self.selection_factory,
            installed_contract_factory=self.installed_contract_factory,
            support_stage_cleanup=self.support_stage_cleanup,
            support_pool_factory=self.support_pool_factory,
        )


def _compose(root: Path, harness: _Harness) -> tuple[SystemUpdateService, SlotBackedSystemUpdateBackend, Path]:
    layout_path = root / "installed-layout.json"
    layout_path.write_bytes(
        (json.dumps(_layout_dict(), sort_keys=True) + "\n").encode()
    )
    backend = SlotBackedSystemUpdateBackend(
        harness.state_dir,
        layout_record_path=layout_path,
        seams=harness.seams(),
    )
    service = SystemUpdateService(
        harness.state_dir,
        SystemIdentity("0.14.0", _FAMILY, _ARCH, _PROFILE),
        backend,
    )
    return service, backend, layout_path


def _staging_names(state_dir: Path) -> list[str]:
    parent = state_dir / "system-updates" / "candidate-support"
    if not parent.is_dir():
        return []
    return sorted(p.name for p in parent.iterdir())


def _assert_no_compressed_tmp(state_dir: Path) -> None:
    parent = state_dir / "system-updates" / "candidate-support"
    if not parent.is_dir():
        return
    leftovers = list(parent.rglob("*.tar.zst.tmp"))
    assert leftovers == [], f"intermediate compressed temp file escaped: {leftovers}"


class ServiceOrchestrationTests(unittest.TestCase):
    """The real service/backend chain stages a support-carrying candidate."""

    def test_full_orchestration_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_dir, total_installed = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            hw_bytes = _hw_archive(pool_dir, hw_path)
            raw = _payload_raw()
            bundle_path = _candidate_bundle(root, raw, name="candidate.greiaupdate", hw_path=hw_path)
            harness = _Harness(root)
            service, backend, _ = _compose(root, harness)
            self.assertIsInstance(backend, SlotBackedSystemUpdateBackend)
            self.assertIs(service.backend, backend)

            inbox = SystemUpdateInbox(harness.state_dir)
            received = inbox.receive(bundle_path)
            candidate_on_disk = Path(received.path)
            self.assertTrue(candidate_on_disk.is_file())

            from greia_installer.layout import require_finalized_slot_capacity

            with mock.patch.object(
                _candidate_support, "extract_support_tree",
                side_effect=_candidate_support.extract_support_tree,
            ) as tree_spy, mock.patch.object(
                _candidate_support, "_extract_one",
                side_effect=_candidate_support._extract_one,
            ) as member_spy:
                staged = service.stage(candidate_on_disk)

            # Real service/backend orchestration ran (not a stub path).
            self.assertEqual(staged.manifest.release_id, "greia-t04-orchestration")
            self.assertIn("store:system-b", harness.contacts)
            self.assertNotIn("store:system-a", harness.contacts)
            for seam in ("support", "contract", "selection", "inventory",
                         "filesystem", "package-installer", "policy"):
                self.assertIn(seam, harness.contacts)

            # Single materialization: exactly one tree extraction, member
            # bytes streamed once, no intermediate compressed copy.
            self.assertEqual(tree_spy.call_count, 1)
            self.assertGreater(member_spy.call_count, 0)
            _assert_no_compressed_tmp(harness.state_dir)

            # Resolver pool and installer pool are the identical stage pool.
            self.assertEqual(len(harness.resolver_pool_ids), 1)
            self.assertEqual(len(harness.installer_pool_ids), 1)
            self.assertEqual(harness.resolver_pool_ids[0], harness.installer_pool_ids[0])
            stage = harness.last_closed_stage
            # The backend finally closed the stage (cleanup true).
            self.assertIsNotNone(stage)
            assert stage is not None
            self.assertTrue(stage.closed)
            self.assertEqual(stage.pool.root, stage.root.resolve())  # type: ignore[attr-defined]
            self.assertEqual(harness.cleanup_count, 1)
            self.assertIsNone(harness.support_stage)
            self.assertEqual(_staging_names(harness.state_dir), [])

            # Support accounting is the installed bound, not compressed bytes.
            support = harness.last_support
            assert support is not None
            self.assertEqual(
                support.installed_size_bound,  # type: ignore[attr-defined]
                total_installed,
            )
            self.assertGreater(
                support.installed_size_bound,  # type: ignore[attr-defined]
                len(hw_bytes),
            )
            self.assertEqual(
                support.support_digest,  # type: ignore[attr-defined]
                _sha(hw_bytes),
            )

            # Full capacity calculation agrees across the single owner and
            # the writer: the stage succeeding proves the bound held.
            from greia_platform.slot_writer import VerifiedReleaseMember

            member = VerifiedReleaseMember.from_manifest(staged.manifest)
            writer_required = SlotWriter().required_slot_bytes(
                member,
                support.installed_size_bound,  # type: ignore[attr-defined]
            )
            owner_required = require_finalized_slot_capacity(
                slot_bytes=_SLOT_BYTES,
                base_bytes=len(raw),
                minimum_slot_bytes=len(raw),
                support_installed_bytes=total_installed,
            )
            self.assertEqual(writer_required, owner_required)
            self.assertLessEqual(writer_required, _SLOT_BYTES)

            # Inactive semantic destination with the role-stable UUID.
            self.assertEqual(harness.filesystem.bound_uuid, _UUID_B_FS)
            self.assertIn("mount", harness.filesystem_ops)
            self.assertIn("completeness", harness.filesystem_ops)
            self.assertIn("health", harness.filesystem_ops)

            # Canonical fstab specialization for the destination UUID.
            fstab_on_disk = harness.filesystem.mount_dir / FSTAB_REL_PATH
            self.assertTrue(fstab_on_disk.is_file())
            self.assertEqual(
                fstab_on_disk.read_text(encoding="ascii"),
                render_fstab(
                    _UUID_B_FS,
                    persist_filesystem_uuid=_UUID_P_FS,
                    boot_control_filesystem_uuid=_UUID_BOOT_FS,
                ),
            )
            self.assertIn(FSTAB_REL_PATH, harness.filesystem.files)

            # Selection + installer invocation through the verified pool.
            self.assertEqual(
                harness.installer_calls,
                [((_FIRMWARE,), (_MICROCODE,))],
            )

            # Journal/status name the staged candidate on the inactive slot.
            journal = BootTransactionJournal.load(backend.journal_dir)
            self.assertEqual(journal.candidate_slot, "B")
            self.assertEqual(journal.accepted_slot, "A")
            self.assertEqual(journal.release_id, "greia-t04-orchestration")
            self.assertEqual(journal.state.value, "update_staged")
            status = service.status_payload()
            self.assertTrue(status["activation"]["available"])
            self.assertEqual(status["activation"]["candidate_slot"], "B")

            # Inbox large candidate removed only after successful stage.
            self.assertFalse(candidate_on_disk.exists())
            inbox_status = inbox.status_payload()
            self.assertTrue(inbox_status.get("staged"))

    def test_compatibility_refusal_preserves_inbox_with_zero_slot_contact(self) -> None:
        """A wrong-architecture candidate never reaches the slot seam."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_dir, _ = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _hw_archive(pool_dir, hw_path)
            bundle_path = _candidate_bundle(
                root, _payload_raw(), name="candidate.greiaupdate", hw_path=hw_path
            )
            harness = _Harness(root)
            _, backend, _ = _compose(root, harness)
            wrong = SystemUpdateService(
                harness.state_dir,
                SystemIdentity("0.14.0", _FAMILY, "wrong-arch", _PROFILE),
                backend,
            )
            inbox = SystemUpdateInbox(harness.state_dir)
            received = inbox.receive(bundle_path)
            with self.assertRaises(SystemUpdateError):
                wrong.stage(Path(received.path))
            self.assertEqual(harness.contacts, [])
            # The unstageable candidate is preserved for retry.
            self.assertTrue(Path(received.path).exists())

    def test_stub_support_factory_is_refused_before_slot_contact(self) -> None:
        """Sensitivity: a non-production support path cannot stage.

        Replacing the release-bound support factory with a stub that
        returns a foreign digest must refuse before any destination
        contact, proving the test would fail if wired to a stub path.
        """
        from greia_platform.slot_writer import ReleaseSupportSet

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_dir, _ = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _hw_archive(pool_dir, hw_path)
            bundle_path = _candidate_bundle(
                root, _payload_raw(), name="candidate.greiaupdate", hw_path=hw_path
            )
            harness = _Harness(root)
            service, _, _ = _compose(root, harness)

            def foreign_support(bundle: object) -> object:
                return ReleaseSupportSet(
                    support_digest="0" * 64,
                    support_size=1,
                    installed_size_bound=0,
                    provided_firmware=frozenset(),
                    provided_microcode=frozenset(),
                    packages=(),
                )

            service.backend.seams = UpdateSlotSeams(
                slot_store_factory=harness.slot_store_factory,
                filesystem_factory=harness.filesystem_factory,
                package_installer_factory=harness.package_installer_factory,
                inventory_factory=harness.inventory_factory,
                support_set_factory=foreign_support,
                installed_contract_factory=harness.installed_contract_factory,
            )
            inspected = inspect_update_bundle(bundle_path)
            with self.assertRaises(SystemUpdateError):
                service.backend.stage(inspected)
            self.assertNotIn("store:system-b", harness.contacts)
            self.assertNotIn("store:system-a", harness.contacts)

    def test_failed_stage_preserves_inbox_for_retry(self) -> None:
        """A capacity-refused candidate stays queued; nothing is discarded."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pool_dir, total_installed = _pool_tree(root)
            hw_path = root / "hw.tar.zst"
            _hw_archive(pool_dir, hw_path)
            raw = _payload_raw()
            # Minimum slot bytes far beyond the 1 GiB slot: the shared
            # capacity owner refuses before any destination mutation.
            bundle_path = _candidate_bundle(
                root, raw,
                name="oversized.greiaupdate",
                hw_path=hw_path,
                minimum_slot_bytes=_SLOT_BYTES + total_installed + 1,
            )
            harness = _Harness(root)
            service, _, _ = _compose(root, harness)
            inbox = SystemUpdateInbox(harness.state_dir)
            received = inbox.receive(bundle_path)
            with self.assertRaises(SystemUpdateError):
                service.stage(Path(received.path))
            self.assertNotIn("store:system-b", harness.contacts)
            self.assertTrue(Path(received.path).exists())
            self.assertEqual(_staging_names(harness.state_dir), [])


class StaticUnitContractTests(unittest.TestCase):
    """Retained unit restrictions/capabilities plus systemd validation."""

    ROOT = Path(__file__).resolve().parents[1]
    SERVICE = ROOT / "build/overlay/etc/systemd/system/greia-system-update.service"
    INSTALLER = (
        ROOT / "build/installer-overlay/etc/systemd/system/greia-install-transaction.service"
    )

    def test_update_service_runs_unconfined_root_package_scripts(self) -> None:
        text = self.SERVICE.read_text(encoding="utf-8")
        self.assertIn("User=root", text)
        self.assertIn("Group=root", text)
        active = [
            line.split("=", 1)[0].strip()
            for line in text.splitlines()
            if line and not line.lstrip().startswith(("#", ";", "["))
            and "=" in line
        ]
        for directive in (
            "CapabilityBoundingSet",
            "AmbientCapabilities",
            "RestrictAddressFamilies",
            "ProtectSystem",
            "ReadWritePaths",
            "RestrictSUIDSGID",
            "TasksMax",
        ):
            with self.subTest(directive=directive):
                self.assertNotIn(directive, active)
        self.assertIn(
            "ExecStart=/usr/bin/python3 -m greia_platform.update_privileged "
            "--socket-activated",
            text,
        )
        # Socket-activated only: never wanted at boot, no install section.
        self.assertNotIn("WantedBy=", text)
        self.assertNotIn("[Install]", text)
        self.assertIn("Requires=greia-system-update.socket", text)

    def test_installer_service_runs_unconfined_root_package_scripts(self) -> None:
        text = self.INSTALLER.read_text(encoding="utf-8")
        self.assertIn("User=root", text)
        self.assertIn("Group=root", text)
        active = [
            line.split("=", 1)[0].strip()
            for line in text.splitlines()
            if line and not line.lstrip().startswith(("#", ";", "["))
            and "=" in line
        ]
        for directive in (
            "CapabilityBoundingSet",
            "AmbientCapabilities",
            "RestrictAddressFamilies",
            "ProtectSystem",
            "ReadWritePaths",
            "RestrictSUIDSGID",
            "TasksMax",
        ):
            with self.subTest(directive=directive):
                self.assertNotIn(directive, active)
        self.assertNotIn("WantedBy=", text)

    def test_systemd_analyze_verify_where_available(self) -> None:
        analyzer = shutil.which("systemd-analyze")
        if analyzer is None:
            self.skipTest("systemd-analyze is not available on this host")
        for unit in (self.SERVICE, self.INSTALLER):
            import subprocess

            completed = subprocess.run(
                [analyzer, "verify", str(unit)],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(
                completed.returncode, 0,
                f"systemd-analyze verify failed for {unit.name}: {completed.stderr}",
            )


if __name__ == "__main__":
    unittest.main()

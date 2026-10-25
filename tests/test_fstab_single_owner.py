"""Single shared fstab renderer (T03 Repair C).

One owner — ``src/greia_platform/fstab.py`` — carries the canonical
destination ``/etc/fstab`` policy. Fresh target assembly (``compose.sh`` via
``GREIA_ROOT_UUID`` and ``greia_installer.engine``) and ``SlotFinalizer``
all render through it; role A gets UUID A, role B gets UUID B, no
release-builder template UUID survives, and the tmpfs lines never change.
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from greia_installer.engine import InstallationEngine
from greia_platform import slot_writer as slot_module
from greia_platform.fstab import (
    FSTAB_FILE_MODE,
    FSTAB_REL_PATH,
    render_fstab,
    write_fstab,
)
from greia_platform.hardware_enablement import HardwareInventory
from greia_platform.persistent_layout import InstalledLayoutRecord
from greia_platform.slot_writer import (
    DestinationSlot,
    HardwareInventoryAttestation,
    InstalledPackage,
    LoopbackSlotFile,
    ReleaseSupportSet,
    SlotFinalizeError,
    SlotFinalizer,
    SlotProfilePolicy,
    SlotWriter,
    VerifiedReleaseMember,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENGINE_SH = PROJECT_ROOT / "build/lib/compose.sh"

_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_UUID_BOOT_FS = "eeeeeeee-ffff-0000-1111-222222222222"
_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_P = "33333333-4444-5555-6666-777777777777"
#: Release-builder template filesystem UUID: the deterministic base payload
#: carries this identity, so any finalized fstab still carrying it proves
#: the role UUID was cloned instead of restored.
_TEMPLATE_UUID = "dddddddd-eeee-ffff-0000-111111111111"
_INSTALL_SHA = "ab" * 32

_FW_PAYLOAD = b"firmware-bytes"
_UC_PAYLOAD = b"microcode-bytes"

EXPECTED_TMPFS_TMP = "tmpfs /tmp tmpfs nosuid,nodev,noexec,mode=1777,size=64M 0 0"
EXPECTED_TMPFS_VAR = "tmpfs /var/tmp tmpfs nosuid,nodev,noexec,mode=1777,size=32M 0 0"
_VERSIONED_KERNEL = b"versioned kernel fixture 6.1.0-greia-amd64\n"
_VERSIONED_INITRAMFS = b"versioned initramfs fixture 6.1.0-greia-amd64\n"


def _record(**overrides: object) -> InstalledLayoutRecord:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.14.0",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "modern-amd64",
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": "modern-gpt-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": "standard-x86-64",
        "schema_version": 1,
        "slot_bytes": 1024 * 1024 * 1024,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return InstalledLayoutRecord.from_dict(base)


def _payload(size: int = 200 * 1024) -> bytes:
    return bytes((index * 31 + 7) % 256 for index in range(size))


def _member(payload: bytes) -> VerifiedReleaseMember:
    hw = b"hwset-member"
    return VerifiedReleaseMember(
        release_id="greia-0.15.0",
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        payload_size=len(payload),
        payload_uncompressed_bytes=len(payload),
        minimum_slot_bytes=len(payload),
        hardware_support_sha256=hashlib.sha256(hw).hexdigest(),
        hardware_support_size=len(hw),
    )


def _support() -> ReleaseSupportSet:
    return ReleaseSupportSet(
        support_digest=hashlib.sha256(b"hwset-member").hexdigest(),
        support_size=len(b"hwset-member"),
        installed_size_bound=1024,
        provided_firmware=frozenset({"firmware-realtek"}),
        provided_microcode=frozenset({"amd64-microcode"}),
        packages=(
            InstalledPackage(
                "firmware-realtek", "1", "all",
                hashlib.sha256(_FW_PAYLOAD).hexdigest(), "firmware",
            ),
            InstalledPackage(
                "amd64-microcode", "1", "amd64",
                hashlib.sha256(_UC_PAYLOAD).hexdigest(), "microcode",
            ),
        ),
    )


def _policy() -> SlotProfilePolicy:
    return SlotProfilePolicy(
        layout_id="modern-gpt-ab-v1",
        system_slot_bytes=1024 * 1024 * 1024,
        boot_backend="grub-ab-v1",
        persist_filesystem_uuid=_UUID_P_FS,
        boot_control_filesystem_uuid=_UUID_BOOT_FS,
    )


def _inventory() -> HardwareInventoryAttestation:
    return HardwareInventoryAttestation.from_inventory(
        HardwareInventory((), truncated=False, scan_errors=0)
    )


def _populate_slot_completeness(mount_dir: Path) -> None:
    for rel_path in slot_module.REQUIRED_SLOT_COMPLETENESS_DIRS:
        (mount_dir / rel_path).mkdir(parents=True, exist_ok=True)
    for rel_path in slot_module.REQUIRED_SLOT_COMPLETENESS_FILES:
        candidate = mount_dir / rel_path
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if candidate.is_symlink() or not candidate.is_file():
            candidate.write_bytes(b"#!/bin/sh\nexit 0\n")
            try:
                candidate.chmod(0o755)
            except OSError:
                pass
    # Match the real release payload shape: one versioned kernel/initramfs
    # pair is copied to the stable generic inputs consumed by SlotFinalizer.
    boot_dir = mount_dir / "boot"
    boot_dir.mkdir(parents=True, exist_ok=True)
    versioned_kernel = boot_dir / "vmlinuz-6.1.0-greia-amd64"
    versioned_initramfs = boot_dir / "initrd.img-6.1.0-greia-amd64"
    versioned_kernel.write_bytes(_VERSIONED_KERNEL)
    versioned_initramfs.write_bytes(_VERSIONED_INITRAMFS)
    shutil.copyfile(versioned_kernel, boot_dir / "vmlinuz-generic")
    shutil.copyfile(versioned_initramfs, boot_dir / "initrd-generic")


class DirBackedSlotFilesystem:
    """Destination-only seam that persists writes to the mounted tree.

    Unlike a dict-recording fake, ``write_file`` lands real bytes under the
    mount directory, so reading ``mount_dir/etc/fstab`` back proves the
    production write path (bind -> mount -> write -> readback) instead of a
    Python-dict seam.
    """

    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir
        self.ops: list[str] = []
        self.bound_uuid: str | None = None
        self.expanded = False
        self.mounted = False

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self.ops.append("bind")
        self.bound_uuid = filesystem_uuid

    def expand_to_capacity(self) -> None:
        self.ops.append("expand")
        self.expanded = True

    def mount(self) -> Path:
        self.ops.append("mount")
        if self.mounted:
            raise SlotFinalizeError("slot is already mounted")
        self.mounted = True
        return self.mount_dir

    def unmount(self) -> None:
        self.ops.append("unmount")
        self.mounted = False

    def sync(self) -> None:
        self.ops.append("sync")

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self.mounted:
            raise SlotFinalizeError("slot writes require a mounted destination")
        self.ops.append(f"write:{relative_path}")
        target = self.mount_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes(data))

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            name
            for name in required
            if not (self.mount_dir / name).is_file()
        )

    def check_completeness(self) -> None:
        self.ops.append("completeness")
        slot_module.check_slot_completeness(self.mount_dir)

    def check_health(self) -> None:
        self.ops.append("health")


class FakeSlotPackageInstaller:
    def __init__(self, support: ReleaseSupportSet) -> None:
        self.support = support

    def install(
        self,
        firmware: tuple[str, ...],
        microcode: tuple[str, ...],
    ) -> tuple[InstalledPackage, ...]:
        ordered = tuple(sorted(set(firmware))) + tuple(
            name for name in sorted(set(microcode)) if name not in set(firmware)
        )
        found: list[InstalledPackage] = []
        for name in ordered:
            for package in self.support.packages:
                if package.name == name:
                    found.append(package)
        if {package.name for package in found} != set(ordered):
            raise SlotFinalizeError("fake installer cannot provide requested set")
        return tuple(found)


def _finalize_to_dir(
    root: Path,
    payload: bytes,
    record: InstalledLayoutRecord,
    slot: str,
) -> tuple[Path, DirBackedSlotFilesystem]:
    """Stage ``payload`` and run the real ``SlotFinalizer.finalize``.

    No seam fakery of the UUID write: ``bind_filesystem_uuid`` receives the
    layout-resolved role UUID through the production finalize path, and the
    fstab assertion below reads the persisted on-disk file back.
    """
    destination = DestinationSlot.resolve_from_layout(record, slot)
    member = _member(payload)
    support = _support()
    store = LoopbackSlotFile.create(
        root / f"slot-{slot.lower()}.img", destination.slot_capacity_bytes
    )
    try:
        write = SlotWriter().write(
            member=member,
            destination=destination,
            source=io.BytesIO(payload),
            storage=store,
            support_installed_bytes=support.installed_size_bound,
        )
    finally:
        store.close()
    mount_dir = root / f"mnt-{slot.lower()}"
    mount_dir.mkdir(parents=True, exist_ok=True)
    _populate_slot_completeness(mount_dir)
    filesystem = DirBackedSlotFilesystem(mount_dir)
    SlotFinalizer().finalize(
        write=write,
        destination=destination,
        filesystem=filesystem,  # type: ignore[arg-type]
        package_installer=FakeSlotPackageInstaller(support),  # type: ignore[arg-type]
        inventory=_inventory(),
        support=support,
        profile_policy=_policy(),
        firmware_packages=("firmware-realtek",),
        microcode_packages=("amd64-microcode",),
        slot_config={"locale": "en"},
    )
    return mount_dir, filesystem


class SingleRendererPolicyTests(unittest.TestCase):
    def test_render_carries_exact_canonical_policy(self) -> None:
        text = render_fstab(_UUID_B_FS)
        lines = text.splitlines()
        self.assertEqual(
            lines[0],
            f"UUID={_UUID_B_FS} / ext4 defaults,noatime,errors=remount-ro 0 1",
        )
        self.assertEqual(lines[1], EXPECTED_TMPFS_TMP)
        self.assertEqual(lines[2], EXPECTED_TMPFS_VAR)
        self.assertEqual(len(lines), 3)
        self.assertTrue(text.endswith("\n"))

    def test_render_rejects_invalid_uuid_fail_closed(self) -> None:
        for bad in ("", "not-a-uuid", _TEMPLATE_UUID.upper().replace("-", "x")):
            with self.assertRaises(ValueError):
                render_fstab(bad)

    def test_render_normalizes_uuid_case(self) -> None:
        self.assertEqual(
            render_fstab(_UUID_B_FS.upper()),
            render_fstab(_UUID_B_FS),
        )


class FreshAssemblyEquivalenceTests(unittest.TestCase):
    def test_installer_engine_matches_shared_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            InstallationEngine._write_root_fstab(root, _UUID_A_FS)
            self.assertEqual(
                (root / "etc/fstab").read_text(encoding="ascii"),
                render_fstab(_UUID_A_FS),
            )

    def test_installer_engine_rejects_invalid_uuid(self) -> None:
        from greia_installer.engine import InstallationError

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(InstallationError, "invalid root"):
                InstallationEngine._write_root_fstab(Path(tmp), "nope")
            self.assertFalse((Path(tmp) / "etc/fstab").exists())

    def test_compose_sh_matches_shared_renderer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rootfs"
            root.mkdir()
            script = (
                "set -euo pipefail; "
                f'source "{ENGINE_SH}"; '
                f'COMPOSE_PROJECT_ROOT="{PROJECT_ROOT}" '
                f'GREIA_ROOT_UUID="{_UUID_A_FS}" '
                f'compose_write_fstab "{root}"'
            )
            completed = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertEqual(
                (root / "etc/fstab").read_text(encoding="ascii"),
                render_fstab(_UUID_A_FS),
            )

    def test_compose_sh_fails_closed_without_uuid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rootfs"
            root.mkdir()
            script = (
                "set -euo pipefail; "
                f'source "{ENGINE_SH}"; '
                f'COMPOSE_PROJECT_ROOT="{PROJECT_ROOT}" '
                "unset GREIA_ROOT_UUID; "
                f'compose_write_fstab "{root}"'
            )
            completed = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse((root / "etc/fstab").exists())

    def test_no_second_fstab_implementation(self) -> None:
        # The policy string lives in exactly one module; the shell seam and
        # both Python call sites only forward to it (T11 re-checks this).
        owner = (PROJECT_ROOT / "src/greia_platform/fstab.py").read_text()
        self.assertIn("errors=remount-ro", owner)
        for path in (
            PROJECT_ROOT / "src/greia_installer/engine.py",
            PROJECT_ROOT / "src/greia_platform/slot_writer.py",
            PROJECT_ROOT / "build/lib/compose.sh",
        ):
            text = path.read_text()
            self.assertNotIn("errors=remount-ro", text, msg=str(path))
            self.assertNotIn("size=64M", text, msg=str(path))


class FinalizerSpecializationTests(unittest.TestCase):
    def test_finalized_slot_carries_role_uuid_fstab_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mount_dir, filesystem = _finalize_to_dir(
                root, _payload(), _record(), "B"
            )
            # Bind used the real layout-resolved role UUID (no seam fakery).
            self.assertEqual(filesystem.bound_uuid, _UUID_B_FS)
            # fstab was specialized after bind+mount, before acceptance.
            self.assertIn("bind", filesystem.ops)
            self.assertIn("mount", filesystem.ops)
            self.assertIn(f"write:{FSTAB_REL_PATH}", filesystem.ops)
            self.assertLess(
                filesystem.ops.index("bind"),
                filesystem.ops.index(f"write:{FSTAB_REL_PATH}"),
            )
            self.assertLess(
                filesystem.ops.index("mount"),
                filesystem.ops.index(f"write:{FSTAB_REL_PATH}"),
            )
            self.assertLess(
                filesystem.ops.index(f"write:{FSTAB_REL_PATH}"),
                filesystem.ops.index("health"),
            )
            on_disk = (mount_dir / FSTAB_REL_PATH).read_text(encoding="ascii")
            self.assertEqual(
                on_disk,
                render_fstab(
                    _UUID_B_FS,
                    persist_filesystem_uuid=_UUID_P_FS,
                    boot_control_filesystem_uuid=_UUID_BOOT_FS,
                ),
            )
            self.assertIn(f"UUID={_UUID_B_FS} / ext4", on_disk)
            self.assertIn(EXPECTED_TMPFS_TMP, on_disk)
            self.assertIn(EXPECTED_TMPFS_VAR, on_disk)
            self.assertNotIn(_TEMPLATE_UUID, on_disk)

    def test_ab_slots_differ_only_in_role_uuid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = _payload()
            mount_b, _ = _finalize_to_dir(root, payload, _record(), "B")
            record_a = _record(
                accepted_slot="B",
                boot_control={"active_slot": "B", "kind": "grub-env-v1"},
            )
            second = root / "second"
            second.mkdir()
            mount_a, _ = _finalize_to_dir(second, payload, record_a, "A")
            fstab_a = (mount_a / FSTAB_REL_PATH).read_text(encoding="ascii")
            fstab_b = (mount_b / FSTAB_REL_PATH).read_text(encoding="ascii")
            self.assertEqual(
                fstab_a,
                render_fstab(
                    _UUID_A_FS,
                    persist_filesystem_uuid=_UUID_P_FS,
                    boot_control_filesystem_uuid=_UUID_BOOT_FS,
                ),
            )
            self.assertEqual(
                fstab_b,
                render_fstab(
                    _UUID_B_FS,
                    persist_filesystem_uuid=_UUID_P_FS,
                    boot_control_filesystem_uuid=_UUID_BOOT_FS,
                ),
            )
            # Only the root UUID differs between slot A and slot B.
            self.assertEqual(fstab_a.splitlines()[1:], fstab_b.splitlines()[1:])
            self.assertEqual(
                fstab_a.splitlines()[1:],
                fstab_b.splitlines()[1:],
            )
            self.assertNotIn(_TEMPLATE_UUID, fstab_a + fstab_b)

    def test_fresh_and_finalized_policy_are_equivalent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fresh = Path(tmp) / "fresh"
            fresh.mkdir()
            InstallationEngine._write_root_fstab(fresh, _UUID_A_FS)
            fresh_text = (fresh / "etc/fstab").read_text(encoding="ascii")
            mount_a, _ = _finalize_to_dir(
                root,
                _payload(4096),
                _record(
                    accepted_slot="B",
                    boot_control={"active_slot": "B", "kind": "grub-env-v1"},
                ),
                "A",
            )
            finalized_text = (mount_a / FSTAB_REL_PATH).read_text(
                encoding="ascii"
            )
            # The legacy single-root path remains unchanged; an A/B
            # finalizer additionally binds the verified shared filesystems.
            self.assertEqual(fresh_text, render_fstab(_UUID_A_FS))
            self.assertEqual(
                finalized_text,
                render_fstab(
                    _UUID_A_FS,
                    persist_filesystem_uuid=_UUID_P_FS,
                    boot_control_filesystem_uuid=_UUID_BOOT_FS,
                ),
            )


class FstabFileModeTests(unittest.TestCase):
    """T16: one canonical fstab mode (``0o644``) on every write path."""

    def test_canonical_mode_constant_is_0644(self) -> None:
        self.assertEqual(FSTAB_FILE_MODE, 0o644)

    def test_write_fstab_lands_0644_under_restrictive_umask(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.umask(0o077)
            try:
                path = write_fstab(Path(tmp), _UUID_A_FS)
            finally:
                os.umask(old)
            self.assertEqual(path.read_text(encoding="ascii"), render_fstab(_UUID_A_FS))
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o644)

    def test_engine_write_lands_0644_under_restrictive_umask(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.umask(0o077)
            try:
                InstallationEngine._write_root_fstab(Path(tmp), _UUID_A_FS)
            finally:
                os.umask(old)
            target = Path(tmp) / "etc/fstab"
            self.assertEqual(target.read_text(encoding="ascii"), render_fstab(_UUID_A_FS))
            self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o644)

    def test_compose_write_lands_0644_under_restrictive_umask(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rootfs"
            root.mkdir()
            script = (
                "set -euo pipefail; "
                "umask 077; "
                f'source "{ENGINE_SH}"; '
                f'COMPOSE_PROJECT_ROOT="{PROJECT_ROOT}" '
                f'GREIA_ROOT_UUID="{_UUID_A_FS}" '
                f'compose_write_fstab "{root}"'
            )
            completed = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            target = root / "etc/fstab"
            self.assertEqual(target.read_text(encoding="ascii"), render_fstab(_UUID_A_FS))
            self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o644)

    def test_dir_backed_finalizer_leaves_0644_and_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = os.umask(0o077)
            try:
                InstallationEngine._write_root_fstab(root / "fresh", _UUID_B_FS)
                mount_dir, _ = _finalize_to_dir(root, _payload(), _record(), "B")
            finally:
                os.umask(old)
            fresh_text = (root / "fresh" / "etc/fstab").read_text(encoding="ascii")
            finalized_path = mount_dir / FSTAB_REL_PATH
            finalized_text = finalized_path.read_text(encoding="ascii")
            # Legacy fresh assembly stays root-only. A/B finalization adds
            # its installer-bound PERSIST and shared boot-control mounts.
            self.assertEqual(fresh_text, render_fstab(_UUID_B_FS))
            self.assertEqual(
                finalized_text,
                render_fstab(
                    _UUID_B_FS,
                    persist_filesystem_uuid=_UUID_P_FS,
                    boot_control_filesystem_uuid=_UUID_BOOT_FS,
                ),
            )
            self.assertIn(f"UUID={_UUID_B_FS} / ext4", finalized_text)
            self.assertIn(EXPECTED_TMPFS_TMP, finalized_text)
            self.assertIn(EXPECTED_TMPFS_VAR, finalized_text)
            self.assertNotIn(_TEMPLATE_UUID, finalized_text)
            # ... and the canonical on-disk mode on both paths, even with
            # a restrictive umask at fresh-write time.
            self.assertEqual(
                stat.S_IMODE(os.stat(root / "fresh" / "etc/fstab").st_mode), 0o644
            )
            self.assertEqual(stat.S_IMODE(os.stat(finalized_path).st_mode), 0o644)

    def test_block_seam_finalizer_overrides_0600_to_0644(self) -> None:
        """Real ``SlotFinalizer`` + real ``BlockSlotFilesystem`` (tmp mount).

        The block seam still forces ``0o600`` on every ``write_file``; the
        finalizer's explicit post-write chmod must leave on-disk
        ``etc/fstab`` at ``0o644`` while sibling finalized files stay at
        ``0o600``. Content is asserted from persisted bytes.
        """
        from greia_platform.block_slots import (
            BlockSlotFilesystem,
            ResolvedSlotDevice,
        )

        class _ModeRunner:
            def __init__(self) -> None:
                self.uuids: dict[str, str] = {}

            def blkid_uuid(self, device: Path) -> str:
                return self.uuids[str(device)]

            def set_uuid(self, device: Path, filesystem_uuid: str) -> None:
                self.uuids[str(device)] = filesystem_uuid

            def check(self, device: Path) -> None:
                return None

            def expand(self, device: Path) -> None:
                return None

            def mount(self, device: Path, mountpoint: Path) -> None:
                mountpoint.mkdir(parents=True, exist_ok=True)
                _populate_slot_completeness(mountpoint)

            def unmount(self, mountpoint: Path) -> None:
                return None

            def sync(self) -> None:
                return None

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = _record()
            destination = DestinationSlot.resolve_from_layout(record, "B")
            payload = _payload()
            member = _member(payload)
            support = _support()
            store = LoopbackSlotFile.create(
                root / "slot-b.img", destination.slot_capacity_bytes
            )
            try:
                write = SlotWriter().write(
                    member=member,
                    destination=destination,
                    source=io.BytesIO(payload),
                    storage=store,
                    support_installed_bytes=support.installed_size_bound,
                )
            finally:
                store.close()
            node = root / "dev-sda3"
            with node.open("wb") as handle:
                handle.truncate(destination.slot_capacity_bytes)
            resolved = ResolvedSlotDevice(
                semantic_slot="B",
                role="system-b",
                device_node=node,
                partuuid=_UUID_B,
                filesystem_uuid=_UUID_B_FS,
                capacity_bytes=destination.slot_capacity_bytes,
                disk_id="disk0",
                layout_id="modern-gpt-ab-v1",
            )
            runner = _ModeRunner()
            mount_root = root / "mnt"
            mount_root.mkdir()
            filesystem = BlockSlotFilesystem(resolved, runner, mount_root)  # type: ignore[arg-type]
            SlotFinalizer().finalize(
                write=write,
                destination=destination,
                filesystem=filesystem,  # type: ignore[arg-type]
                package_installer=FakeSlotPackageInstaller(support),  # type: ignore[arg-type]
                inventory=_inventory(),
                support=support,
                profile_policy=_policy(),
                firmware_packages=("firmware-realtek",),
                microcode_packages=("amd64-microcode",),
                slot_config={"locale": "en"},
            )
            mounts = [child for child in mount_root.iterdir() if child.is_dir()]
            self.assertEqual(len(mounts), 1)
            fstab_path = mounts[0] / FSTAB_REL_PATH
            persisted = fstab_path.read_bytes()
            self.assertEqual(
                persisted,
                render_fstab(
                    _UUID_B_FS,
                    persist_filesystem_uuid=_UUID_P_FS,
                    boot_control_filesystem_uuid=_UUID_BOOT_FS,
                ).encode("ascii"),
            )
            self.assertEqual(stat.S_IMODE(os.stat(fstab_path).st_mode), 0o644)
            self.assertIn(EXPECTED_TMPFS_TMP.encode("ascii"), persisted)
            self.assertNotIn(_TEMPLATE_UUID.encode("ascii"), persisted)
            for source_name, alias_name, expected in (
                ("vmlinuz-generic", "vmlinuz-greia", _VERSIONED_KERNEL),
                ("initrd-generic", "initramfs-greia.img", _VERSIONED_INITRAMFS),
            ):
                source = mounts[0] / "boot" / source_name
                alias = mounts[0] / "boot" / alias_name
                self.assertEqual(source.read_bytes(), expected)
                self.assertEqual(alias.read_bytes(), expected)
                self.assertEqual(os.stat(source).st_ino, os.stat(alias).st_ino)
            # The shared block seam keeps its 0o600 default for non-fstab
            # finalized files.
            for rel in (
                slot_module.FINALIZED_GENERIC_REL_PATH,
                slot_module.RELEASE_IDENTITY_REL_PATH,
                slot_module.SLOT_PROFILE_REL_PATH,
                slot_module.RECEIPT_REL_PATH,
            ):
                sibling = mounts[0] / rel
                self.assertTrue(sibling.is_file(), msg=rel)
                self.assertEqual(
                    stat.S_IMODE(os.stat(sibling).st_mode), 0o600, msg=rel
                )


if __name__ == "__main__":
    unittest.main()

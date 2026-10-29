"""POSTR1-P2-INSTALLER-POOL-UNMOUNT: installer detaches pool bind mounts before slot unmount.

Regression for the Gate-P2 firmware-carrying seam defect: the EXECUTE path
bind-mounts the hardware-support pool into the mounted SYSTEM slot (recorded
in the installer's ``mounted`` list) and the slot unmount used to fail busy
(``umount: target is busy``), masking any chroot/apt result. The production
installer seam (``device_seams._package_installer_factory``) now threads an
owned per-EXECUTE ``mounted`` list through the shared
``SharedSlotPackageInstaller`` and wraps it in
``InstallerPoolBindCleanupPackageInstaller``, which detaches every added
bind mount in reverse order via ``umount`` argv arrays before returning —
the same shape as the updater ``_LazyTargetPackageInstaller`` path.

All fixtures are disposable tmpdirs; no device, mount, chroot or apt work
runs. The "busy slot unmount" is simulated faithfully: the recording slot
filesystem refuses ``unmount`` while the shared ``mounted`` list is
non-empty, exactly the kernel behaviour a lingering bind mount produces.
"""

from __future__ import annotations

import hashlib
import inspect
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from greia_installer.hardware_support import VerifiedHardwareSupportPool
from greia_installer.hardware_support_install import detach_recorded_mounts
from greia_installer.slots import InstallerPoolBindCleanupPackageInstaller
from greia_platform.block_slots import SharedSlotPackageInstaller
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

_FW = b"firmware-bytes"
_UC = b"microcode-bytes"
_FIRMWARE = "firmware-realtek"
_MICROCODE = "amd64-microcode"
_SLOT_BYTES = 1024 * 1024 * 1024


def _record(**overrides: object) -> InstalledLayoutRecord:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.14.0",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "modern-amd64",
        "install_target_sha256": "ab" * 32,
        "installed_at_unix": 1757000000,
        "layout_id": "modern-gpt-ab-v1",
        "persist": {
            "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
            "partuuid": "33333333-4444-5555-6666-777777777777",
        },
        "platform_family": "standard-x86-64",
        "schema_version": 1,
        "slot_bytes": _SLOT_BYTES,
        "system_a": {
            "filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "partuuid": "11111111-2222-3333-4444-555555555555",
        },
        "system_b": {
            "filesystem_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
            "partuuid": "22222222-3333-4444-5555-666666666666",
        },
    }
    base.update(overrides)
    return InstalledLayoutRecord.from_dict(base)


def _make_pool(root: Path) -> Path:
    """Verified on-disk support pool carrying firmware + microcode."""
    pool = root / "support"
    deb_dir = pool / "pool"
    deb_dir.mkdir(parents=True)
    (deb_dir / "firmware-realtek_1_all.deb").write_bytes(_FW)
    (deb_dir / "amd64-microcode_1_amd64.deb").write_bytes(_UC)
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
        "total_bytes": len(_FW) + len(_UC),
        "total_installed_bytes": len(_FW) + len(_UC) + 2 * 32 * 1024,
        "provided_candidate_packages": [_FIRMWARE, _MICROCODE],
        "provided_firmware_packages": [_FIRMWARE],
        "provided_microcode_packages": [_MICROCODE],
        "broad_firmware_packages": [_FIRMWARE],
        "firmware_providers": {"rtl.bin": [_FIRMWARE]},
        "unavailable_candidate_packages": [],
        "packages": [
            {
                "package": _FIRMWARE, "version": "1",
                "architecture": "all", "filename": "pool/firmware-realtek_1_all.deb",
                "size": len(_FW), "sha256": _sha(_FW), "candidate": True,
                "installed_bytes": len(_FW) + 32 * 1024,
            },
            {
                "package": _MICROCODE, "version": "1",
                "architecture": "amd64", "filename": "pool/amd64-microcode_1_amd64.deb",
                "size": len(_UC), "sha256": _sha(_UC), "candidate": True,
                "installed_bytes": len(_UC) + 32 * 1024,
            },
        ],
        "repository_indexes": {
            "Packages": {"size": len(packages_payload), "sha256": _sha(packages_payload)},
            "Packages.gz": {
                "size": len(packages_gzip_payload),
                "sha256": _sha(packages_gzip_payload),
            },
        },
    }
    (pool / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pool


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


def _support(member: VerifiedReleaseMember) -> ReleaseSupportSet:
    return ReleaseSupportSet(
        support_digest=member.hardware_support_sha256,
        support_size=member.hardware_support_size,
        installed_size_bound=1024,
        provided_firmware=frozenset({_FIRMWARE}),
        provided_microcode=frozenset({_MICROCODE}),
        packages=(
            InstalledPackage(
                _FIRMWARE, "1", "all",
                hashlib.sha256(_FW).hexdigest(), "firmware",
            ),
            InstalledPackage(
                _MICROCODE, "1", "amd64",
                hashlib.sha256(_UC).hexdigest(), "microcode",
            ),
        ),
    )


class RecordingRunner:
    """Offline stand-in for the production hardware-support runner.

    Records every argv array; mount/chroot/apt commands succeed unless
    ``fail_on`` names a command word to fail with the real (simulated)
    tool error. ``umount`` commands always succeed — detach is
    best-effort and must never mask the install result.
    """

    def __init__(
        self, *, fail_on: str | None = None, events: list[str] | None = None
    ) -> None:
        self.commands: list[list[str]] = []
        self.fail_on = fail_on
        self.events = events

    def run(self, command, *, check: bool = True):  # type: ignore[no-untyped-def]
        argv = list(command)
        assert all(isinstance(word, str) and word for word in argv), (
            "installer commands must be non-empty text argv arrays"
        )
        self.commands.append(argv)
        if argv and argv[0] == "umount" and self.events is not None:
            self.events.append(f"detach:{Path(argv[-1]).name}")
        if self.fail_on and any(self.fail_on in word for word in argv):
            raise RuntimeError(f"E: simulated apt failure on: {' '.join(argv)}")
        return None


class BusyUnmountRunner(RecordingRunner):
    def run(self, command, *, check: bool = True):  # type: ignore[no-untyped-def]
        result = super().run(command, check=check)
        argv = list(command)
        if argv and argv[0] == "umount":
            return SimpleNamespace(returncode=1)
        return SimpleNamespace(returncode=0)


class BusyAwareSlotFilesystem:
    """Destination-only fake with kernel-faithful busy-unmount semantics.

    ``unmount`` refuses with ``target is busy`` while the shared installer
    ``mounted`` list is non-empty — the exact failure a lingering pool bind
    mount produces on the production ``BlockSlotFilesystem`` path. A shared
    ``events`` log records detach-relevant ordering across the runner and
    the filesystem.
    """

    def __init__(
        self,
        mount_dir: Path,
        *,
        mounted: list[Path],
        events: list[str],
    ) -> None:
        self.mount_dir = mount_dir
        self.mounted = mounted
        self.events = events
        self.files: dict[str, bytes] = {}
        self._is_mounted = False

    def bind_filesystem_uuid(self, filesystem_uuid: str) -> None:
        self.events.append("bind")

    def expand_to_capacity(self) -> None:
        self.events.append("expand")

    def mount(self) -> Path:
        self.events.append("slot-mount")
        self.mount_dir.mkdir(parents=True, exist_ok=True)
        self._is_mounted = True
        return self.mount_dir

    def unmount(self) -> None:
        if self.mounted:
            self.events.append("slot-unmount-busy")
            raise SlotFinalizeError(
                f"slot unmount failed: umount: target is busy ({self.mounted[0]})"
            )
        self.events.append("slot-unmount")
        self._is_mounted = False

    def sync(self) -> None:
        self.events.append("sync")

    def write_file(self, relative_path: str, data: bytes) -> None:
        if not self._is_mounted:
            raise SlotFinalizeError("slot writes require a mounted destination")
        self.files[relative_path] = bytes(data)

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required if name not in self.files)

    def check_completeness(self) -> None:
        from greia_platform.slot_writer import check_slot_completeness

        self.events.append("completeness")
        check_slot_completeness(self.mount_dir)

    def check_health(self) -> None:
        self.events.append("health")


def _build_production_shaped_installer(
    *,
    runner: RecordingRunner,
    target_root: Path,
    pool: VerifiedHardwareSupportPool,
    mounted: list[Path],
) -> InstallerPoolBindCleanupPackageInstaller:
    """Mirror the production seam: owned list + shared installer + wrapper."""
    shared = SharedSlotPackageInstaller(
        runner=runner,  # type: ignore[arg-type]
        target_root=target_root,
        pool=pool,  # type: ignore[arg-type]
        mounted=mounted,
    )
    return InstallerPoolBindCleanupPackageInstaller(
        inner=shared,  # type: ignore[arg-type]
        runner=runner,  # type: ignore[arg-type]
        mounted=mounted,
    )


def _finalize_through_seam(
    *,
    runner: RecordingRunner,
    use_cleanup_wrapper: bool,
) -> dict[str, object]:
    """Run one real ``SlotFinalizer.finalize`` over the installer seam.

    Returns the event log, the tracking list, the receipt (on success) and
    the raised error (on failure) for ordering assertions.
    """
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        pool = VerifiedHardwareSupportPool.load(_make_pool(root))
        mount_dir = root / "slot-b"
        mount_dir.mkdir(parents=True, exist_ok=True)
        from greia_platform.slot_writer import (
            REQUIRED_SLOT_COMPLETENESS_DIRS,
            REQUIRED_SLOT_COMPLETENESS_FILES,
        )

        for rel_path in REQUIRED_SLOT_COMPLETENESS_DIRS:
            (mount_dir / rel_path).mkdir(parents=True, exist_ok=True)
        for rel_path in REQUIRED_SLOT_COMPLETENESS_FILES:
            candidate = mount_dir / rel_path
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_bytes(b"#!/bin/sh\nexit 0\n")
            try:
                candidate.chmod(0o755)
            except OSError:
                pass
        mounted: list[Path] = []
        events: list[str] = []
        runner.events = events

        if use_cleanup_wrapper:
            package_installer = _build_production_shaped_installer(
                runner=runner, target_root=mount_dir, pool=pool, mounted=mounted
            )
        else:
            package_installer = SharedSlotPackageInstaller(
                runner=runner,  # type: ignore[arg-type]
                target_root=mount_dir,
                pool=pool,  # type: ignore[arg-type]
                mounted=mounted,
            )
        filesystem = BusyAwareSlotFilesystem(
            mount_dir, mounted=mounted, events=events
        )

        record = _record()
        destination = DestinationSlot.resolve_from_layout(record, "B")
        payload = bytes((index * 31 + 7) % 256 for index in range(64 * 1024))
        member = _member(payload)
        support = _support(member)
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
            inventory = HardwareInventoryAttestation(token="ab" * 32)
            policy = SlotProfilePolicy(
                layout_id="modern-gpt-ab-v1",
                system_slot_bytes=destination.slot_capacity_bytes,
                boot_backend="grub-ab-v1",
                persist_filesystem_uuid="cccccccc-dddd-eeee-ffff-000000000000",
                boot_control_filesystem_uuid="dddddddd-eeee-ffff-0000-111111111111",
            )
            receipt = SlotFinalizer().finalize(
                write=write,
                destination=destination,
                filesystem=filesystem,  # type: ignore[arg-type]
                package_installer=package_installer,  # type: ignore[arg-type]
                inventory=inventory,
                support=support,
                profile_policy=policy,
                firmware_packages=(_FIRMWARE,),
                microcode_packages=(_MICROCODE,),
            )
            error: BaseException | None = None
        except BaseException as exc:  # noqa: BLE001 - ordering evidence needs it
            receipt = None  # type: ignore[assignment]
            error = exc
        finally:
            store.close()

        return {
            "events": events,
            "mounted": list(mounted),
            "receipt": receipt,
            "error": error,
            "commands": [list(command) for command in runner.commands],
        }


class InstallerPoolMountCleanupTests(unittest.TestCase):
    """Detach-before-unmount ordering at the production installer seam."""

    def test_firmware_pool_detaches_before_slot_unmount(self) -> None:
        outcome = _finalize_through_seam(
            runner=RecordingRunner(), use_cleanup_wrapper=True
        )
        self.assertIsNone(outcome["error"], f"finalize must succeed: {outcome['error']!r}")
        self.assertIsNotNone(outcome["receipt"])
        events = outcome["events"]
        assert isinstance(events, list)
        # The tracked /run root recursively owns the nested support-pool bind.
        detach_at = events.index("detach:run")
        unmount_at = events.index("slot-unmount")
        self.assertLess(
            detach_at, unmount_at,
            f"bind detach must precede slot unmount: {events}",
        )
        self.assertNotIn("slot-unmount-busy", events)
        # No stale tracking entry survives the EXECUTE.
        self.assertEqual(outcome["mounted"], [])
        # Detach used umount argv arrays (never a shell string).
        umounts = [
            command for command in outcome["commands"]  # type: ignore[union-attr]
            if command and command[0] == "umount"
        ]
        self.assertEqual(len(umounts), 4)
        for command in umounts:
            self.assertIsInstance(command, list)
            self.assertTrue(all(isinstance(word, str) for word in command))

    def test_failed_install_still_detaches_and_surfaces_real_error(self) -> None:
        outcome = _finalize_through_seam(
            runner=RecordingRunner(fail_on="install"), use_cleanup_wrapper=True
        )
        error = outcome["error"]
        self.assertIsNotNone(error, "the simulated apt failure must propagate")
        assert error is not None
        # The real chroot/apt reason surfaces — never a busy-unmount mask.
        self.assertIn("simulated apt failure", str(error))
        self.assertNotIn("target is busy", str(error))
        events = outcome["events"]
        assert isinstance(events, list)
        self.assertIn("detach:run", events)
        self.assertNotIn("slot-unmount-busy", events)
        self.assertEqual(outcome["mounted"], [])

    def test_detach_runs_in_reverse_order_and_truncates(self) -> None:
        runner = RecordingRunner()
        mounted: list[Path] = [Path("/pre-existing/other-mount")]
        inner_calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

        class _Inner:
            def install(self, firmware, microcode):  # type: ignore[no-untyped-def]
                inner_calls.append((tuple(firmware), tuple(microcode)))
                first = Path("/target/run/greia-hardware-support")
                second = first / "nested"
                mounted.append(first)
                mounted.append(second)
                return ()

        wrapper = InstallerPoolBindCleanupPackageInstaller(
            inner=_Inner(),  # type: ignore[arg-type]
            runner=runner,  # type: ignore[arg-type]
            mounted=mounted,
        )
        wrapper.install((_FIRMWARE,), (_MICROCODE,))
        umounts = [c for c in runner.commands if c and c[0] == "umount"]
        self.assertEqual(
            [c[-1] for c in umounts],
            ["/target/run/greia-hardware-support"],
            "nested recorded mounts collapse to one recursive root",
        )
        # Only the added slice is truncated; the pre-existing entry survives.
        self.assertEqual(mounted, [Path("/pre-existing/other-mount")])
        self.assertEqual(inner_calls, [((_FIRMWARE,), (_MICROCODE,))])

    def test_failed_recursive_detach_fails_closed_and_retains_mount(self) -> None:
        runner = BusyUnmountRunner()
        mounted: list[Path] = []

        class _Inner:
            def install(self, firmware, microcode):  # type: ignore[no-untyped-def]
                mounted.append(Path("/target/dev"))
                return ()

        wrapper = InstallerPoolBindCleanupPackageInstaller(
            inner=_Inner(),  # type: ignore[arg-type]
            runner=runner,  # type: ignore[arg-type]
            mounted=mounted,
        )
        with self.assertRaisesRegex(Exception, "cleanup could not detach"):
            wrapper.install((_FIRMWARE,), (_MICROCODE,))
        self.assertEqual(
            [command for command in runner.commands if command[0] == "umount"],
            [["umount", "--recursive", "--", "/target/dev"]],
        )
        self.assertEqual(mounted, [Path("/target/dev")])

    def test_production_seam_threads_owned_list_through_wrapper(self) -> None:
        import greia_installer.device_seams as seams_mod

        source = Path(seams_mod.__file__).read_text(encoding="utf-8")
        self.assertIn(
            "InstallerPoolBindCleanupPackageInstaller", source,
            "production seam must wrap the shared installer in the cleanup wrapper",
        )
        self.assertNotIn(
            "mounted=[]", source,
            "production seam must thread an owned mounted list, not a throwaway",
        )
        # The wrapper detaches via umount argv arrays; the runner stays shell-free.
        cleanup_source = inspect.getsource(detach_recorded_mounts)
        self.assertIn('["umount", "--recursive", "--"', cleanup_source)
        self.assertNotIn('"-l"', cleanup_source)
        runner_source = inspect.getsource(seams_mod.SubprocessHardwareSupportRunner.run)
        self.assertIn("shell=False", runner_source)
        self.assertNotIn("shell=True", runner_source)


class SensitivityControlTests(unittest.TestCase):
    """Positive control: without the detach, the busy ordering reproduces.

    Removing the cleanup wrapper (the pre-fix seam shape: shared installer
    with a never-detached ``mounted`` list) must reproduce the Gate-P2
    failure — slot unmount refused busy — proving this regression is
    sensitive to the claimed mechanism rather than vacuously green.
    """

    def test_missing_detach_reproduces_busy_unmount(self) -> None:
        outcome = _finalize_through_seam(
            runner=RecordingRunner(), use_cleanup_wrapper=False
        )
        error = outcome["error"]
        self.assertIsNotNone(error, "without detach the busy unmount must fail")
        assert error is not None
        self.assertIn("target is busy", str(error))
        events = outcome["events"]
        assert isinstance(events, list)
        self.assertIn("slot-unmount-busy", events)
        self.assertEqual(len(outcome["mounted"]), 6)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

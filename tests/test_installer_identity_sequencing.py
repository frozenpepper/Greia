"""POSTR1-P2 identity-sequencing tests: MBR PARTUUID authority is observed.

Production identity observation happens AFTER the destructive
partition/filesystem effects that create the identities, never before. On
a real blank target no caller-supplied mapping can satisfy the binding:
the orchestrator partitions first, then invokes the post-layout observer
seam ``observer(target, plan)``, then validates the result through the T1
typed normalizers plus the partition-number gate. A fabricated UUID4
labeled as an MBR PARTUUID, a cross-disk mix, a swapped partition number,
or any observation failure refuses fail-closed — after partitioning but
before a single SYSTEM_A payload byte is written.

Coverage (all offline, zero disk contact):

- validator unit level: valid MBR observation binds; blank-target
  observation (before partitions) refuses; fabricated/cross-disk/
  number-mismatch/wrong-scheme/cloned identities refuse;
- orchestrator level: the observer fires after partitioning and before
  slot storage; observation failure aborts before SYSTEM_A write;
- executor level: ``build_ab_executor`` never invokes the observer
  pre-layout; it binds the seam the orchestrator calls post-layout;
- production wiring: ``build_post_layout_mbr_observer`` routes through
  the real ``observe_partition_identities`` mechanism (scripted block
  runner), not a bypass;
- sensitivity: break (fabricated PARTUUID) -> RED -> restore -> GREEN.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from greia_installer.disk import DeviceObservation
from greia_installer.fresh_ab_install import (
    AbExecutorFacts,
    FreshAbInstallError,
    FreshAbInstallRequest,
    FreshAbInstallSeams,
    build_ab_executor,
    execute_fresh_ab_install,
)
from greia_installer.layout import (
    LayoutError,
    MbrCommandResult,
    MbrProbeRunner,
    ProfileSizing,
    build_post_layout_mbr_observer,
    plan_for_profile,
    validate_observed_identities_against_plan,
)
from greia_installer.persist import PersistCommandResult, PersistCommandRunner
from greia_platform.slot_writer import SlotFinalizeError
from greia_platform.system_updates import (
    build_update_bundle,
    inspect_update_bundle,
)

HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None

GIB = 1024 * 1024 * 1024
MIB = 1024 * 1024

_PROFILE = "legacy-x86-i686"
_FAMILY = "legacy-x86"
_ARCH = "i386"
_INSTALL_SHA = "ab" * 32
_PASSWORD_HASH = "grub.pbkdf2.sha512.10000." + "A" * 128
_HW_BODY = b"hwset-payload" * 64
_HW_BYTES = b"\x28\xb5\x2f\xfd" + _HW_BODY
_SUPPORT_BOUND = 1 * MIB
_MBR_SIGNATURE = "a1b2c3d4"
_PERSIST_FS_UUID = "cccccccc-cccc-cccc-cccc-ccccccccccc3"


def _payload(size: int = 128 * 1024) -> bytes:
    return bytes((index * 31 + 7) % 256 for index in range(size))


def _target(size_bytes: int = 8 * GIB) -> DeviceObservation:
    return DeviceObservation(
        name="sda",
        path=Path("/dev/sda"),
        size_bytes=size_bytes,
        device_type="disk",
        model="Test disk",
        serial="SERIAL-1",
        transport="sata",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn="WWN-1",
        major_minor="8:0",
    )


def _sizing(slot_bytes: int = 1 * GIB) -> ProfileSizing:
    return ProfileSizing(
        layout_adapter_id="legacy-bios-ab-v1",
        slot_bytes=slot_bytes,
        persist_minimum_bytes=256 * MIB,
        boot_backend="grub-ab-v1",
    )


def _plan():
    return plan_for_profile(_sizing(), device_size_bytes=8 * GIB)


def _observed_mbr_identities(signature: str = _MBR_SIGNATURE):
    return {
        "system-a": {
            "scheme": "MBR_PARTUUID",
            "partuuid": f"{signature}-02",
            "filesystem_uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        },
        "system-b": {
            "scheme": "MBR_PARTUUID",
            "partuuid": f"{signature}-03",
            "filesystem_uuid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
        },
        "persist": {
            "scheme": "MBR_PARTUUID",
            "partuuid": f"{signature}-04",
            "filesystem_uuid": "dddddddd-dddd-dddd-dddd-ddddddddddd4",
        },
    }


class RecordingPartitionRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command) -> None:
        assert isinstance(command, list)
        self.commands.append(list(command))
        return None


class SparseSlotStorage:
    def __init__(self, capacity_bytes: int) -> None:
        self._capacity = capacity_bytes
        self._chunks: dict[int, bytes] = {}
        self.flushes = 0

    @property
    def capacity_bytes(self) -> int:
        return self._capacity

    def write_at(self, offset: int, data: bytes) -> None:
        if offset < 0 or offset + len(data) > self._capacity or not data:
            raise AssertionError("slot store write outside range")
        self._chunks[offset] = bytes(data)

    def read_at(self, offset: int, length: int) -> bytes:
        if offset < 0 or length <= 0 or offset + length > self._capacity:
            raise AssertionError("slot store read outside range")
        assembled = bytearray(length)
        for start, chunk in self._chunks.items():
            overlap_start = max(offset, start)
            overlap_end = min(offset + length, start + len(chunk))
            if overlap_start < overlap_end:
                assembled[overlap_start - offset : overlap_end - offset] = (
                    chunk[overlap_start - start : overlap_end - start]
                )
        return bytes(assembled)

    def flush(self) -> None:
        self.flushes += 1


class FakeSlotFilesystem:
    def __init__(self, mount_dir: Path) -> None:
        self.mount_dir = mount_dir
        self.ops: list[str] = []
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
        if self.mounted:
            raise SlotFinalizeError("slot is already mounted")
        self.mounted = True
        self.mount_dir.mkdir(parents=True, exist_ok=True)
        # Simulate a staged slot carrying real Greia userspace so the
        # shared completeness smoke passes (uses the shared path set).
        from greia_platform.slot_writer import (
            REQUIRED_SLOT_COMPLETENESS_DIRS,
            REQUIRED_SLOT_COMPLETENESS_FILES,
        )

        for rel_path in REQUIRED_SLOT_COMPLETENESS_DIRS:
            (self.mount_dir / rel_path).mkdir(parents=True, exist_ok=True)
        for rel_path in REQUIRED_SLOT_COMPLETENESS_FILES:
            candidate = self.mount_dir / rel_path
            candidate.parent.mkdir(parents=True, exist_ok=True)
            if candidate.is_symlink() or not candidate.is_file():
                candidate.write_bytes(b"#!/bin/sh\nexit 0\n")
                try:
                    candidate.chmod(0o755)
                except OSError:
                    pass
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
        self.files[relative_path] = bytes(data)

    def missing_files(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required if name not in self.files)

    def check_completeness(self) -> None:
        from greia_platform.slot_writer import check_slot_completeness

        self.ops.append("completeness")
        check_slot_completeness(self.mount_dir)

    def check_health(self) -> None:
        self.ops.append("health")


class FakePackageInstaller:
    def install(self, firmware, microcode):  # type: ignore[no-untyped-def]
        if tuple(firmware) or tuple(microcode):
            raise AssertionError("empty support set installs nothing")
        return ()


class FakePersistRunner(PersistCommandRunner):
    def __init__(self, *, readback_uuid: str) -> None:
        self.commands: list[list[str]] = []
        self._readback = readback_uuid
        self._blkid_calls = 0

    def run(self, command) -> PersistCommandResult:
        assert isinstance(command, list)
        self.commands.append(list(command))
        name = command[0]
        if name == "blkid":
            self._blkid_calls += 1
            if self._blkid_calls == 1:
                return PersistCommandResult(stdout="", returncode=1)
            return PersistCommandResult(stdout=self._readback, returncode=0)
        if name in ("mkfs.ext4", "mount", "umount"):
            return PersistCommandResult(stdout="", returncode=0)
        raise AssertionError(f"unexpected PERSIST command: {name}")


class ScriptedProbeRunner(MbrProbeRunner):
    """Block-layer stand-in: scripted blkid answers behind the real path."""

    def __init__(
        self,
        *,
        disk_signature: str = _MBR_SIGNATURE,
        fs_uuids: dict[str, str] | None = None,
    ) -> None:
        self._signature = disk_signature
        self._fs_uuids = fs_uuids or {
            "2": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
            "3": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2",
            "4": "dddddddd-dddd-dddd-dddd-ddddddddddd4",
        }
        self.calls: list[list[str]] = []

    def run(self, command) -> MbrCommandResult:
        argv = list(command)
        self.calls.append(argv)
        assert argv[0] == "blkid"
        locator = argv[-1]
        if "-s" not in argv:
            raise AssertionError("probe must select a field")
        field = argv[argv.index("-s") + 1]
        if field == "PTUUID":
            if not self._signature:
                return MbrCommandResult(stdout="", returncode=1)
            return MbrCommandResult(stdout=self._signature, returncode=0)
        if field == "PARTUUID":
            # Locator forms: /dev/sda2 (letter base) or /dev/loop0p2
            # (digit base); the partition number is the trailing digits.
            digits = "".join(
                ch for ch in locator[::-1] if ch.isdigit()
            )[::-1] or "0"
            part_number = int(digits, 10)
            return MbrCommandResult(
                stdout=f"{self._signature}-{part_number:02d}", returncode=0
            )
        if field == "UUID":
            digits = "".join(
                ch for ch in locator[::-1] if ch.isdigit()
            )[::-1] or "0"
            part_number = int(digits, 10)
            return MbrCommandResult(
                stdout=self._fs_uuids[str(part_number)], returncode=0
            )
        raise AssertionError(f"unexpected probe field: {field}")


class BlankProbeRunner(MbrProbeRunner):
    """A blank target: no table, no signature, no partitions (pre-layout)."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def run(self, command) -> MbrCommandResult:
        self.calls.append(list(command))
        return MbrCommandResult(stdout="", returncode=1)


class PostLayoutObserverValidationTests(unittest.TestCase):
    """The validator binds observed facts, never fabricated ones."""

    def test_valid_mbr_observation_binds(self) -> None:
        bound = validate_observed_identities_against_plan(
            plan=_plan(), identities=_observed_mbr_identities()
        )
        self.assertEqual(bound["system-a"]["partuuid"], f"{_MBR_SIGNATURE}-02")
        self.assertEqual(bound["system-b"]["partuuid"], f"{_MBR_SIGNATURE}-03")
        self.assertEqual(bound["persist"]["partuuid"], f"{_MBR_SIGNATURE}-04")
        self.assertTrue(
            all(entry["scheme"] == "MBR_PARTUUID" for entry in bound.values())
        )

    def test_observation_before_partitions_refuses(self) -> None:
        # A blank target carries no table: the production observer path
        # fails closed instead of binding a guessed disk identity.
        observer = build_post_layout_mbr_observer(BlankProbeRunner())
        with self.assertRaisesRegex(LayoutError, "no disk signature"):
            observer(_target(), _plan())

    def test_fabricated_mbr_uuid_refuses(self) -> None:
        import uuid as _uuid

        fabricated = _observed_mbr_identities()
        fabricated["system-a"] = dict(
            fabricated["system-a"], partuuid=str(_uuid.uuid4())
        )
        with self.assertRaisesRegex(LayoutError, "not authoritative"):
            validate_observed_identities_against_plan(
                plan=_plan(), identities=fabricated
            )

    def test_cross_disk_identity_refuses(self) -> None:
        mixed = _observed_mbr_identities()
        mixed["system-b"] = dict(mixed["system-b"], partuuid="deadbeef-03")
        with self.assertRaisesRegex(LayoutError, "cross-disk"):
            validate_observed_identities_against_plan(
                plan=_plan(), identities=mixed
            )

    def test_partition_number_mismatch_refuses(self) -> None:
        swapped = _observed_mbr_identities()
        swapped["system-a"] = dict(
            swapped["system-a"], partuuid=f"{_MBR_SIGNATURE}-03"
        )
        swapped["system-b"] = dict(
            swapped["system-b"], partuuid=f"{_MBR_SIGNATURE}-02"
        )
        with self.assertRaisesRegex(LayoutError, "partition number"):
            validate_observed_identities_against_plan(
                plan=_plan(), identities=swapped
            )

    def test_wrong_scheme_refuses(self) -> None:
        mismatched = {
            role: dict(values, scheme="GPT_GUID")
            for role, values in _observed_mbr_identities().items()
        }
        with self.assertRaisesRegex(LayoutError, "scheme"):
            validate_observed_identities_against_plan(
                plan=_plan(), identities=mismatched
            )

    def test_cloned_filesystem_uuid_refuses(self) -> None:
        cloned = _observed_mbr_identities()
        cloned["system-b"] = dict(
            cloned["system-b"],
            filesystem_uuid=cloned["system-a"]["filesystem_uuid"],
        )
        with self.assertRaisesRegex(LayoutError, "unique"):
            validate_observed_identities_against_plan(
                plan=_plan(), identities=cloned
            )


class OrchestratorSequencingTests(unittest.TestCase):
    """The orchestrator observes after partitioning, before SYSTEM_A."""

    def _bundle(self, root: Path, payload: bytes) -> Path:
        import zstandard

        compressed = zstandard.ZstdCompressor(level=3).compress(payload)
        payload_path = root / "payload.ext4.zst"
        payload_path.write_bytes(compressed)
        hw_path = root / "hw.tar.zst"
        hw_path.write_bytes(_HW_BYTES)
        bundle = root / "r11.greiaupdate"
        if bundle.exists():
            bundle.unlink()
        build_update_bundle(
            payload_path=payload_path,
            hardware_support_path=hw_path,
            output_path=bundle,
            version="0.15.0",
            release_id="greia-0.15.0",
            platform_family=_FAMILY,
            architecture=_ARCH,
            profile=_PROFILE,
            payload_uncompressed_bytes=len(payload),
            minimum_slot_bytes=len(payload) + MIB,
            persist_read_schema_min=1,
            persist_read_schema_max=1,
            persist_write_schema=1,
        )
        return bundle

    def _harness(self, root: Path, payload: bytes, observer):
        bundle = self._bundle(root, payload)
        manifest = inspect_update_bundle(bundle).manifest
        persist_stage = root / "persist-stage"
        persist_stage.mkdir()
        boot_control = root / "boot-control"
        backend_state = root / "backend-state"
        journal = root / "journal"
        for directory in (boot_control, backend_state, journal):
            directory.mkdir()
        touched: list[str] = []
        order: list[str] = []

        def _storage(role: str):  # type: ignore[no-untyped-def]
            order.append(f"slot-storage:{role}")
            touched.append(role)
            return SparseSlotStorage(1 * GIB)

        def _recording_observer(target, plan):  # type: ignore[no-untyped-def]
            order.append("observe")
            return observer(target, plan)

        runner = RecordingPartitionRunner()
        seams = FreshAbInstallSeams(
            partition_runner=runner,  # type: ignore[arg-type]
            slot_storage_factory=_storage,
            slot_filesystem_factory=lambda: FakeSlotFilesystem(root / "mnt"),
            package_installer_factory=FakePackageInstaller,
            inventory_token="cd" * 32,
            support_digest=manifest.hardware_support_sha256,
            support_size=manifest.hardware_support_size,
            support_installed_bound=_SUPPORT_BOUND,
            persist_runner=FakePersistRunner(readback_uuid=_PERSIST_FS_UUID),
            persist_stage_dir=persist_stage,
            persist_uuid_factory=lambda: uuid.UUID(_PERSIST_FS_UUID),
            boot_control_dir=boot_control,
            backend_state_dir=backend_state,
            journal_dir=journal,
            post_layout_identity_observer=_recording_observer,
        )
        request = FreshAbInstallRequest(
            bundle_path=bundle,
            expected_profile_id=_PROFILE,
            expected_platform_family=_FAMILY,
            expected_architecture=_ARCH,
            sizing=_sizing(),
            target=_target(),
            support_installed_bytes=_SUPPORT_BOUND,
            install_target_sha256=_INSTALL_SHA,
            password_hash=_PASSWORD_HASH,
            installed_at_unix=1757000000,
        )
        return {
            "seams": seams,
            "request": request,
            "runner": runner,
            "touched": touched,
            "order": order,
            "observed": _observed_mbr_identities(),
        }

    def _fresh_harness(self, observer):
        directory = tempfile.mkdtemp(prefix="p2-seq-")
        self.addCleanup(shutil.rmtree, directory, True)
        return self._harness(Path(directory), _payload(), observer)

    def test_observer_fires_after_partitioning_before_slot_write(self) -> None:
        def _observer(target, plan):  # type: ignore[no-untyped-def]
            return _observed_mbr_identities()

        harness = self._fresh_harness(_observer)
        result = execute_fresh_ab_install(harness["request"], harness["seams"])
        # Partitioning ran, then observation, then SYSTEM_A storage.
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["order"][0], "observe")
        self.assertEqual(harness["order"][1], "slot-storage:A")
        self.assertEqual(harness["touched"], ["A"])
        self.assertEqual(
            result.receipt.filesystem_uuid,
            harness["observed"]["system-a"]["filesystem_uuid"],
        )
        self.assertEqual(
            result.record.system_a.partuuid,
            harness["observed"]["system-a"]["partuuid"],
        )

    def test_observation_failure_aborts_before_system_a_write(self) -> None:
        def _failing(target, plan):  # type: ignore[no-untyped-def]
            raise LayoutError("block probe reported no disk signature")

        harness = self._fresh_harness(_failing)
        with self.assertRaisesRegex(
            FreshAbInstallError, "observation refused"
        ):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["touched"], [])

    def test_fabricated_mbr_partuuid_refused_for_identity_reasons(self) -> None:
        import uuid as _uuid

        def _fabricated(target, plan):  # type: ignore[no-untyped-def]
            mapping = _observed_mbr_identities()
            mapping["system-a"] = dict(
                mapping["system-a"], partuuid=str(_uuid.uuid4())
            )
            return mapping

        harness = self._fresh_harness(_fabricated)
        with self.assertRaisesRegex(
            FreshAbInstallError, "system-a.partuuid is not authoritative"
        ):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["touched"], [])

    def test_cross_disk_identity_refused_for_identity_reasons(self) -> None:
        def _mixed(target, plan):  # type: ignore[no-untyped-def]
            mapping = _observed_mbr_identities()
            mapping["persist"] = dict(
                mapping["persist"], partuuid="deadbeef-04"
            )
            return mapping

        harness = self._fresh_harness(_mixed)
        with self.assertRaisesRegex(FreshAbInstallError, "cross-disk"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["touched"], [])

    def test_partition_number_mismatch_refused_for_identity_reasons(self) -> None:
        def _swapped(target, plan):  # type: ignore[no-untyped-def]
            mapping = _observed_mbr_identities()
            mapping["persist"] = dict(
                mapping["persist"], partuuid=f"{_MBR_SIGNATURE}-02"
            )
            mapping["system-a"] = dict(
                mapping["system-a"], partuuid=f"{_MBR_SIGNATURE}-04"
            )
            return mapping

        harness = self._fresh_harness(_swapped)
        with self.assertRaisesRegex(FreshAbInstallError, "partition number"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertTrue(harness["runner"].commands)
        self.assertEqual(harness["touched"], [])

    def test_sensitivity_fabricated_red_restore_green(self) -> None:
        """Break -> RED -> restore -> GREEN at the observation boundary."""
        import uuid as _uuid

        state = {"fabricate": True}

        def _observer(target, plan):  # type: ignore[no-untyped-def]
            mapping = _observed_mbr_identities()
            if state["fabricate"]:
                mapping["system-b"] = dict(
                    mapping["system-b"], partuuid=str(_uuid.uuid4())
                )
            return mapping

        harness = self._fresh_harness(_observer)
        # RED: the fabricated MBR PARTUUID is refused for identity reasons.
        with self.assertRaisesRegex(FreshAbInstallError, "not authoritative"):
            execute_fresh_ab_install(harness["request"], harness["seams"])
        # Restore the exact intended observation -> GREEN.
        state["fabricate"] = False
        result = execute_fresh_ab_install(harness["request"], harness["seams"])
        self.assertEqual(result.receipt.slot, "A")
        self.assertEqual(
            result.record.system_b.partuuid,  # type: ignore[union-attr]
            harness["observed"]["system-b"]["partuuid"],
        )

    def test_executor_never_invokes_observer_pre_layout(self) -> None:
        bundle_dir = tempfile.mkdtemp(prefix="p2-seq-exec-")
        self.addCleanup(shutil.rmtree, bundle_dir, True)
        root = Path(bundle_dir)
        bundle = self._bundle(root, _payload())
        manifest = inspect_update_bundle(bundle).manifest
        persist_stage = root / "persist-stage"
        persist_stage.mkdir()
        boot_control = root / "boot-control"
        backend_state = root / "backend-state"
        journal = root / "journal"
        for directory in (boot_control, backend_state, journal):
            directory.mkdir()
        calls: list[tuple[str, int]] = []
        runners: list[RecordingPartitionRunner] = []

        def _observer(target, plan):  # type: ignore[no-untyped-def]
            calls.append((target.name, len(runners[0].commands)))
            return _observed_mbr_identities()

        def _seams(target):  # type: ignore[no-untyped-def]
            runner = RecordingPartitionRunner()
            runners.append(runner)
            return FreshAbInstallSeams(
                partition_runner=runner,  # type: ignore[arg-type]
                slot_storage_factory=lambda role: SparseSlotStorage(1 * GIB),
                slot_filesystem_factory=lambda: FakeSlotFilesystem(root / "mnt"),
                package_installer_factory=FakePackageInstaller,
                inventory_token="cd" * 32,
                support_digest=manifest.hardware_support_sha256,
                support_size=manifest.hardware_support_size,
                support_installed_bound=_SUPPORT_BOUND,
                persist_runner=FakePersistRunner(readback_uuid=_PERSIST_FS_UUID),
                persist_stage_dir=persist_stage,
                persist_uuid_factory=lambda: uuid.UUID(_PERSIST_FS_UUID),
                boot_control_dir=boot_control,
                backend_state_dir=backend_state,
                journal_dir=journal,
            )

        facts = AbExecutorFacts(
            bundle_path=bundle,
            expected_profile_id=_PROFILE,
            expected_platform_family=_FAMILY,
            expected_architecture=_ARCH,
            sizing=_sizing(),
            support_installed_bytes=_SUPPORT_BOUND,
            password_hash=_PASSWORD_HASH,
        )
        executor = build_ab_executor(facts, _seams, identities_factory=_observer)
        # Binding the executor performs zero observation (no pre-compute).
        self.assertEqual(calls, [])

        class _Authorization:
            target_identity = _INSTALL_SHA

        from greia_platform.hardware import HardwareSettings

        settings = HardwareSettings(
            schema_version=2,
            touchpad_tap=False,
            touchpad_speed=0.35,
            mouse_speed=0.0,
            natural_scrolling=False,
            resolution="auto",
            keyboard_layout="us",
            mic_gain=2.0,
            disable_while_typing=False,
        )
        outcome = executor(_Authorization(), settings, "en", _target())
        self.assertEqual(outcome.release_id, "greia-0.15.0")
        # Exactly one post-layout observation, after partitioning ran.
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "sda")
        self.assertGreater(calls[0][1], 0)


class ProductionObserverWiringTests(unittest.TestCase):
    """The production seam reaches the real observation mechanism."""

    def test_production_observer_routes_through_block_observation(self) -> None:
        runner = ScriptedProbeRunner()
        observer = build_post_layout_mbr_observer(runner)
        observed = observer(_target(), _plan())
        self.assertEqual(observed["system-a"]["partuuid"], f"{_MBR_SIGNATURE}-02")
        self.assertEqual(observed["system-b"]["partuuid"], f"{_MBR_SIGNATURE}-03")
        self.assertEqual(observed["persist"]["partuuid"], f"{_MBR_SIGNATURE}-04")
        self.assertEqual(
            observed["system-a"]["filesystem_uuid"],
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        )
        # The seam exercised the real mechanism: PTUUID + per-partition
        # PARTUUID/UUID probes through the controlled blkid tool path.
        probed = [" ".join(call) for call in runner.calls]
        self.assertTrue(any("PTUUID" in call for call in probed))
        self.assertTrue(any("PARTUUID" in call for call in probed))
        self.assertTrue(any(re.search(r"-s UUID( |$)", call) for call in probed))

    def test_production_observer_validates_before_binding(self) -> None:
        bound = validate_observed_identities_against_plan(
            plan=_plan(),
            identities=build_post_layout_mbr_observer(ScriptedProbeRunner())(
                _target(), _plan()
            ),
        )
        self.assertEqual(bound["persist"]["partuuid"], f"{_MBR_SIGNATURE}-04")


if __name__ == "__main__":
    unittest.main()

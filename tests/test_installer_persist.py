"""A8-PERSIST creation/mount orchestration proofs (source gate, fake runner).

All block commands run against a FakePersistRunner, never a valued device:
the locator is a disposable ``/dev/loopN``-style observation and no test
performs losetup/parted/mkfs/mount. Mounts are simulated (the runner
records the argument arrays; directory work happens directly on disposable
tmpdirs). Real loop-device execution stays in the deferred hardware
backlog (source-first amendment 2026-09-06).
"""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
import unittest
import uuid
from dataclasses import replace
from pathlib import Path

from greia_installer.disk import DeviceObservation
from greia_installer.layout import adapter_for
from greia_installer.persist import (
    PERSIST_LABEL,
    PERSIST_TRANSACTION_MODE,
    FreshPersistSpec,
    PersistCommandResult,
    PersistCommandRunner,
    PersistError,
    initialize_fresh_persist,
    open_installed_persist,
    persist_node_for,
    persist_transaction_path,
    present_canonical_paths,
    unmount_persist,
)
from greia_platform.persistent_layout import (
    MIN_PERSIST_BYTES,
    PERSISTENT_NAMESPACE_ORDER,
    BlockTopology,
    MountKind,
    PartitionFact,
    PersistRecoveryRequired as PlatformRecovery,
    build_namespace_map,
    emit_persist_schema_marker,
    parse_persist_schema_marker,
    persist_record_path,
    persist_schema_marker_path,
)
from greia_platform.system_updates import verify_persistent_state_contract_bytes


SLOT_BYTES = 1024**3
DEVICE_BYTES = 8 * 1024**3

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_UUID_X = "44444444-5555-6666-7777-888888888888"
_UUID_X_FS = "dddddddd-eeee-ffff-0000-111111111111"


def disposable_target(
    *, path: str = "/dev/loop99", device_type: str = "disk"
) -> DeviceObservation:
    return DeviceObservation(
        name=Path(path).name,
        path=Path(path),
        size_bytes=DEVICE_BYTES,
        device_type=device_type,
        model="disposable loop file",
        serial="PRIVATE-SERIAL",
        transport="ata",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn="PRIVATE-WWN",
        major_minor="7:99",
    )


def legacy_plan():
    return adapter_for("legacy-bios-ab-v1").plan(
        device_size_bytes=DEVICE_BYTES,
        slot_bytes=SLOT_BYTES,
        persist_minimum_bytes=MIN_PERSIST_BYTES,
    )


def fresh_spec(**overrides):
    base = {
        "platform_family": "legacy-x86",
        "install_profile": "legacy-acer",
        "install_target_sha256": "ab" * 32,
        "installed_at_unix": 1757000000,
        "boot_active_slot": "A",
        "accepted_slot": "A",
        "accepted_release_id": "greia-0.14.0",
        "slot_bytes": SLOT_BYTES,
        "system_a": {"partuuid": _UUID_A, "filesystem_uuid": _UUID_A_FS},
        "system_b": {"partuuid": _UUID_B, "filesystem_uuid": _UUID_B_FS},
        "persist_partuuid": _UUID_P,
    }
    base.update(overrides)
    return FreshPersistSpec(**base)


def matching_topology(**overrides):
    persist_fs = overrides.pop("persist_fs", _UUID_P_FS)
    persist_part = overrides.pop("persist_part", _UUID_P)
    system_a = overrides.pop("system_a", (_UUID_A, _UUID_A_FS))
    system_b = overrides.pop("system_b", (_UUID_B, _UUID_B_FS))
    disk = overrides.pop("disk", "loop99disk")
    assert not overrides
    facts = [
        PartitionFact.create(
            role="system-a",
            partuuid=system_a[0],
            filesystem_uuid=system_a[1],
            size_bytes=SLOT_BYTES,
            disk_id=disk,
        ),
        PartitionFact.create(
            role="system-b",
            partuuid=system_b[0],
            filesystem_uuid=system_b[1],
            size_bytes=SLOT_BYTES,
            disk_id=disk,
        ),
        PartitionFact.create(
            role="persist",
            partuuid=persist_part,
            filesystem_uuid=persist_fs,
            size_bytes=MIN_PERSIST_BYTES,
            disk_id=disk,
        ),
    ]
    return BlockTopology(partitions=tuple(facts))


class FakePersistRunner(PersistCommandRunner):
    """Records argument arrays; blkid answers are scripted per call.

    ``device_tree`` simulates block-device content: a successful ``mount``
    copies the tree's children into the (empty) mountpoint, modelling how
    a real mount makes device content visible at the staging path.
    ``umount`` is a recorded no-op, as in a mock.
    """

    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.blkid_responses: list[tuple[str, int]] = []
        self.fail_mount = False
        self.fail_commands: set[str] = set()
        self.device_tree: Path | None = None

    def run(self, command) -> PersistCommandResult:
        assert isinstance(command, list), "runner must receive an argument array"
        assert all(isinstance(word, str) and word for word in command)
        self.commands.append(list(command))
        name = command[0]
        if name == "blkid":
            if self.blkid_responses:
                stdout, returncode = self.blkid_responses.pop(0)
            else:
                stdout, returncode = ("", 1)
            return PersistCommandResult(stdout=stdout, returncode=returncode)
        if name == "mount":
            if self.fail_mount:
                return PersistCommandResult(stdout="", returncode=1)
            if self.device_tree is not None:
                mountpoint = Path(command[-1])
                for child in self.device_tree.iterdir():
                    destination = mountpoint / child.name
                    if child.is_dir() and not child.is_symlink():
                        shutil.copytree(child, destination, symlinks=True)
                    else:
                        shutil.copy2(child, destination, follow_symlinks=False)
            return PersistCommandResult(stdout="", returncode=0)
        if name in self.fail_commands:
            return PersistCommandResult(stdout="", returncode=1)
        return PersistCommandResult(stdout="", returncode=0)

    def names(self) -> list[str]:
        return [command[0] for command in self.commands]


def fixed_uuid_factory() -> uuid.UUID:
    return uuid.UUID(_UUID_P_FS)


def do_fresh(
    runner: FakePersistRunner, mountpoint: Path, **spec_overrides
):
    return initialize_fresh_persist(
        target=disposable_target(),
        plan=legacy_plan(),
        spec=fresh_spec(**spec_overrides),
        mountpoint=mountpoint,
        runner=runner,
        uuid_factory=fixed_uuid_factory,
    )


class PersistNodeTests(unittest.TestCase):
    def test_node_derived_from_plan_role_with_p_separator(self) -> None:
        node = persist_node_for(disposable_target(), legacy_plan())
        self.assertEqual(node, Path("/dev/loop99p4"))

    def test_non_disk_and_relative_targets_rejected_with_zero_commands(self) -> None:
        runner = FakePersistRunner()
        with self.assertRaises(PersistError):
            persist_node_for(
                disposable_target(device_type="part"), legacy_plan()
            )
        with self.assertRaises(PersistError):
            persist_node_for(
                disposable_target(path="loop99"), legacy_plan()
            )
        self.assertEqual(runner.commands, [])


class FreshInitTests(unittest.TestCase):
    def test_fresh_creates_mounts_initializes_exactly_once_then_unmounts(self) -> None:
        runner = FakePersistRunner()
        runner.blkid_responses = [("", 1), (_UUID_P_FS + "\n", 0)]
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            stage.mkdir()
            result = do_fresh(runner, stage)
            self.assertEqual(result.persist_filesystem_uuid, _UUID_P_FS)
            # Ordered command proof: probe, create, readback, mount, unmount.
            self.assertEqual(
                runner.names(), ["blkid", "mkfs.ext4", "blkid", "mount", "umount"]
            )
            mkfs = runner.commands[1]
            self.assertEqual(
                mkfs,
                [
                    "mkfs.ext4", "-F", "-m", "1", "-L", PERSIST_LABEL,
                    "-U", _UUID_P_FS, "/dev/loop99p4",
                ],
            )
            self.assertEqual(
                runner.commands[3],
                ["mount", "-t", "ext4", "-o", "nodev,nosuid",
                 "/dev/loop99p4", str(stage)],
            )
            self.assertEqual(runner.commands[4], ["umount", str(stage)])
            # Layout authority + both schema markers + contract + transaction root.
            record_path = persist_record_path(stage)
            self.assertEqual(stat.S_IMODE(record_path.stat().st_mode), 0o600)
            marker_path = persist_schema_marker_path(stage)
            marker_raw = marker_path.read_bytes()
            self.assertEqual(marker_raw, emit_persist_schema_marker(1))
            self.assertEqual(parse_persist_schema_marker(marker_raw), 1)
            self.assertEqual(
                result.record.persist.filesystem_uuid, _UUID_P_FS
            )
            self.assertEqual(result.record.persist.partuuid, _UUID_P)
            namespaces = sorted(
                child.name for child in (stage / "greia" / "namespaces").iterdir()
            )
            self.assertEqual(namespaces, sorted(PERSISTENT_NAMESPACE_ORDER))
            for child in (stage / "greia" / "namespaces").iterdir():
                if child.name == "machine-identity":
                    self.assertEqual([path.name for path in child.iterdir()], ["machine-id"])
                    self.assertEqual((child / "machine-id").read_bytes(), b"")
                elif child.name == "layout-authority":
                    self.assertEqual(
                        [path.name for path in child.iterdir()],
                        ["installed-layout.json"],
                    )
                else:
                    self.assertEqual(list(child.iterdir()), [])
            verify_persistent_state_contract_bytes(
                (stage / "greia" / "persistent-state-contract.json").read_bytes()
            )
            journal = persist_transaction_path(stage)
            self.assertTrue(journal.is_dir())
            self.assertFalse(journal.is_symlink())
            self.assertEqual(stat.S_IMODE(journal.stat().st_mode),
                             PERSIST_TRANSACTION_MODE)
            self.assertEqual(list(journal.iterdir()), [])

    def test_second_fresh_refused_before_any_destructive_command(self) -> None:
        first = FakePersistRunner()
        first.blkid_responses = [("", 1), (_UUID_P_FS + "\n", 0)]
        with tempfile.TemporaryDirectory() as directory:
            stage_a = Path(directory) / "a"
            stage_a.mkdir()
            do_fresh(first, stage_a)
            # A later attempt that re-mounts the initialized tree still
            # refuses — exactly once — even though the occupant UUID equals
            # the intended identity. The refusal comes from the
            # post-mount initialization gates, never from a silent wipe.
            stage_b = Path(directory) / "b"
            stage_b.mkdir()
            second = FakePersistRunner()
            second.blkid_responses = [(_UUID_P_FS + "\n", 0)]
            second.device_tree = stage_a
            with self.assertRaisesRegex(
                PersistError, "(never re-mint|transaction root)"
            ):
                do_fresh(second, stage_b)
            self.assertNotIn("mkfs.ext4", second.names())
            self.assertIn("umount", second.names())

    def test_adopt_adapter_formatted_matching_uuid_skips_mkfs(self) -> None:
        # Adapter-formatted PERSIST whose blkid UUID already equals the
        # intended (observed) identity is adopted exactly once: no second
        # mkfs, then mount + exactly-once initialization with that identity.
        runner = FakePersistRunner()
        runner.blkid_responses = [(_UUID_P_FS + "\n", 0)]
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            stage.mkdir()
            result = do_fresh(runner, stage)
            self.assertEqual(result.persist_filesystem_uuid, _UUID_P_FS)
            self.assertEqual(runner.names(), ["blkid", "mount", "umount"])
            self.assertNotIn("mkfs.ext4", runner.names())
            self.assertEqual(
                result.record.persist.filesystem_uuid, _UUID_P_FS
            )
            journal = persist_transaction_path(stage)
            self.assertTrue(journal.is_dir())
            self.assertFalse(journal.is_symlink())

    def test_foreign_uuid_refused_before_any_destructive_command(self) -> None:
        # A foreign occupant (blkid UUID != intended identity) still
        # refuses fail-closed at the pre-check with zero destructive work.
        runner = FakePersistRunner()
        runner.blkid_responses = [(_UUID_X_FS + "\n", 0)]
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            stage.mkdir()
            with self.assertRaisesRegex(PersistError, "already exists"):
                do_fresh(runner, stage)
            self.assertEqual(runner.names(), ["blkid"])

    def test_partial_init_fails_closed_and_detaches(self) -> None:
        # Fault injection: the mounted device reveals a partial occupant
        # (a file blocking one namespace directory), so initialization
        # fails after mkfs+mount. Must detach and present no authority.
        runner = FakePersistRunner()
        runner.blkid_responses = [("", 1), (_UUID_P_FS + "\n", 0)]
        with tempfile.TemporaryDirectory() as directory:
            device = Path(directory) / "device"
            blocker = device / "greia" / "namespaces" / "layout-authority"
            blocker.parent.mkdir(parents=True)
            blocker.write_bytes(b"partial occupant")
            runner.device_tree = device
            stage = Path(directory) / "stage"
            stage.mkdir()
            with self.assertRaises(PersistError):
                do_fresh(runner, stage)
            # Failed closed: mount ran, detach issued, no record presented.
            self.assertEqual(
                runner.names(), ["blkid", "mkfs.ext4", "blkid", "mount", "umount"]
            )
            self.assertFalse(persist_record_path(stage).exists())
            # No silent resume: the occupant still blocks a retry. The
            # retry observes the same (matching) occupant UUID, adopts the
            # node, then fails closed at the initialization gates.
            retry = FakePersistRunner()
            retry.blkid_responses = [(_UUID_P_FS + "\n", 0)]
            retry.device_tree = device
            with tempfile.TemporaryDirectory() as other:
                stage_b = Path(other) / "stage"
                stage_b.mkdir()
                with self.assertRaisesRegex(
                    PersistError, "(never re-mint|namespace exists)"
                ):
                    do_fresh(retry, stage_b)
                self.assertNotIn("mkfs.ext4", retry.names())
                self.assertIn("umount", retry.names())

    def test_readback_mismatch_rejected_without_initialization(self) -> None:
        runner = FakePersistRunner()
        runner.blkid_responses = [("", 1), (_UUID_A_FS + "\n", 0)]
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            stage.mkdir()
            with self.assertRaisesRegex(PersistError, "read back"):
                do_fresh(runner, stage)
            self.assertEqual(runner.names(), ["blkid", "mkfs.ext4", "blkid"])
            self.assertFalse((stage / "greia").exists())

    def test_mountpoint_symlink_and_nonempty_rejected_with_zero_commands(self) -> None:
        runner = FakePersistRunner()
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / "real"
            real.mkdir()
            link = Path(directory) / "link"
            os.symlink(real, link)
            with self.assertRaisesRegex(PersistError, "symbolic link"):
                do_fresh(runner, link)
            busy = Path(directory) / "busy"
            busy.mkdir()
            (busy / "stale").write_text("x")
            with self.assertRaisesRegex(PersistError, "empty"):
                do_fresh(runner, busy)
            relative = Path("relative-stage")
            with self.assertRaisesRegex(PersistError, "absolute"):
                do_fresh(runner, relative)
            self.assertEqual(runner.commands, [])

    def test_no_shell_metacharacters_in_any_command(self) -> None:
        runner = FakePersistRunner()
        runner.blkid_responses = [("", 1), (_UUID_P_FS + "\n", 0)]
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            stage.mkdir()
            do_fresh(runner, stage)
            for command in runner.commands:
                for word in command:
                    for marker in (";", "&", "|", "$", "`", "(", ")", "<", ">", "\n"):
                        self.assertNotIn(marker, word)

    def test_bad_spec_rejected_before_mount_or_init(self) -> None:
        runner = FakePersistRunner()
        runner.blkid_responses = [("", 1), (_UUID_P_FS + "\n", 0)]
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            stage.mkdir()
            with self.assertRaises(PersistError):
                do_fresh(runner, stage, persist_partuuid="not-a-uuid")
            # Device-level probe/create/readback ran, but mount/init never did.
            self.assertEqual(runner.names(), ["blkid", "mkfs.ext4", "blkid"])


class ExistingOpenTests(unittest.TestCase):
    def _seed_device(self, runner: FakePersistRunner, device: Path):
        device.mkdir(parents=True, exist_ok=True)
        runner.blkid_responses = [("", 1), (_UUID_P_FS + "\n", 0)]
        return do_fresh(runner, device)

    def _open(self, runner, device: Path, stage: Path, topology):
        runner.device_tree = device
        return open_installed_persist(
            target=disposable_target(),
            plan=legacy_plan(),
            topology=topology,
            mountpoint=stage,
            runner=runner,
        )

    def test_open_round_trip_leaves_mounted_for_consumer(self) -> None:
        seed = FakePersistRunner()
        with tempfile.TemporaryDirectory() as directory:
            device = Path(directory) / "device"
            seeded = self._seed_device(seed, device)
            stage = Path(directory) / "stage"
            stage.mkdir()
            opener = FakePersistRunner()
            opened = self._open(opener, device, stage, matching_topology())
            self.assertEqual(opened.record, seeded.record)
            self.assertEqual(tuple(opened.namespace_map.namespaces),
                             PERSISTENT_NAMESPACE_ORDER)
            self.assertEqual(
                opener.commands[0],
                ["mount", "-t", "ext4", "-o", "ro,nodev,nosuid",
                 "/dev/loop99p4", str(stage)],
            )
            self.assertNotIn("umount", opener.names())
            self.assertNotIn("mkfs.ext4", opener.names())
            unmount_persist(stage, opener)
            self.assertEqual(opener.commands[-1], ["umount", str(stage)])

    def test_missing_record_enters_recovery_without_reinit(self) -> None:
        opener = FakePersistRunner()
        with tempfile.TemporaryDirectory() as directory:
            device = Path(directory) / "device"
            device.mkdir()
            stage = Path(directory) / "stage"
            stage.mkdir()
            with self.assertRaises(PlatformRecovery):
                self._open(opener, device, stage, matching_topology())
            self.assertIn("umount", opener.names())
            self.assertNotIn("mkfs.ext4", opener.names())
            self.assertEqual(list(stage.iterdir()), [])

    def test_corrupt_record_enters_recovery(self) -> None:
        seed = FakePersistRunner()
        with tempfile.TemporaryDirectory() as directory:
            device = Path(directory) / "device"
            self._seed_device(seed, device)
            record_path = persist_record_path(device)
            record_path.write_bytes(b"{not json")
            os.chmod(record_path, 0o600)
            stage = Path(directory) / "stage"
            stage.mkdir()
            opener = FakePersistRunner()
            with self.assertRaises(PlatformRecovery):
                self._open(opener, device, stage, matching_topology())
            self.assertIn("umount", opener.names())
            self.assertNotIn("mkfs.ext4", opener.names())

    def test_swapped_slots_enter_recovery(self) -> None:
        seed = FakePersistRunner()
        with tempfile.TemporaryDirectory() as directory:
            device = Path(directory) / "device"
            self._seed_device(seed, device)
            stage = Path(directory) / "stage"
            stage.mkdir()
            opener = FakePersistRunner()
            swapped = matching_topology(
                system_a=(_UUID_B, _UUID_B_FS),
                system_b=(_UUID_A, _UUID_A_FS),
            )
            with self.assertRaisesRegex(PlatformRecovery, "swap"):
                self._open(opener, device, stage, swapped)
            self.assertIn("umount", opener.names())
            self.assertNotIn("mkfs.ext4", opener.names())

    def test_wrong_persist_uuid_and_partuuid_and_ancestry_enter_recovery(self) -> None:
        seed = FakePersistRunner()
        with tempfile.TemporaryDirectory() as directory:
            device = Path(directory) / "device"
            self._seed_device(seed, device)
            base = matching_topology()
            split_ancestry = BlockTopology(
                partitions=tuple(
                    replace(fact, disk_id="otherdisk")
                    if fact.role == "persist"
                    else fact
                    for fact in base.partitions
                )
            )
            for label, topology in (
                ("uuid", matching_topology(persist_fs=_UUID_X_FS)),
                ("partuuid", matching_topology(persist_part=_UUID_X)),
                ("ancestry", split_ancestry),
            ):
                stage = Path(directory) / f"stage-{label}"
                stage.mkdir()
                opener = FakePersistRunner()
                with self.assertRaises(PlatformRecovery, msg=label):
                    self._open(opener, device, stage, topology)
                self.assertIn("umount", opener.names())
                self.assertNotIn("mkfs.ext4", opener.names())

    def test_mount_failure_and_missing_transaction_root_enter_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            failing = FakePersistRunner()
            failing.fail_mount = True
            device = Path(directory) / "device"
            device.mkdir()
            stage = Path(directory) / "stage"
            stage.mkdir()
            with self.assertRaises(PlatformRecovery):
                self._open(failing, device, stage, matching_topology())
            self.assertNotIn("mkfs.ext4", failing.names())

            seed = FakePersistRunner()
            device_b = Path(directory) / "device-b"
            self._seed_device(seed, device_b)
            shutil.rmtree(persist_transaction_path(device_b))
            stage_b = Path(directory) / "stage-b"
            stage_b.mkdir()
            opener = FakePersistRunner()
            with self.assertRaisesRegex(PlatformRecovery, "transaction root"):
                self._open(opener, device_b, stage_b, matching_topology())
            self.assertIn("umount", opener.names())

    def test_symlink_record_rejected(self) -> None:
        seed = FakePersistRunner()
        with tempfile.TemporaryDirectory() as directory:
            device = Path(directory) / "device"
            self._seed_device(seed, device)
            record_path = persist_record_path(device)
            stolen = record_path.read_bytes()
            record_path.unlink()
            decoy = device / "decoy.json"
            decoy.write_bytes(stolen)
            os.symlink(decoy, record_path)
            stage = Path(directory) / "stage"
            stage.mkdir()
            opener = FakePersistRunner()
            with self.assertRaises(PlatformRecovery):
                self._open(opener, device, stage, matching_topology())
            self.assertIn("umount", opener.names())


class SlotPresentationTests(unittest.TestCase):
    def test_canonical_paths_materialized_as_real_directories(self) -> None:
        table = build_namespace_map()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "slot"
            root.mkdir()
            presented = present_canonical_paths(root, table)
            self.assertTrue(presented)
            for mount in table.mount_plan():
                candidate = root.joinpath(mount.target.lstrip("/"))
                probe = candidate.parent if mount.kind == MountKind.BIND_FILE else candidate
                self.assertTrue(probe.is_dir(), mount.target)
                self.assertFalse(os.path.islink(probe), mount.target)
            self.assertTrue((root / "etc" / "greia-os").is_dir())

    def test_symlink_escape_refused(self) -> None:
        table = build_namespace_map()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "slot"
            root.mkdir()
            outside = Path(directory) / "outside"
            outside.mkdir()
            link = root / "var" / "lib" / "greia-os"
            link.parent.mkdir(parents=True)
            os.symlink(outside, link)
            with self.assertRaisesRegex(PersistError, "symbolic link"):
                present_canonical_paths(root, table)


if __name__ == "__main__":
    unittest.main()

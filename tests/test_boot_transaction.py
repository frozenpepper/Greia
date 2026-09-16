"""L7-BOOT source-scope tests: artifact sets, backends, journal, initramfs roles.

R0/R1 only: files and fakes. No physical boot-control writes, no bootloader
changes, no EEPROM contact. Fake GRUB/Pi backends persist state to regular
files so one-shot consumption, failure fallback and crash reconcile are
proven without hardware.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import re
import stat
import tempfile
import unittest
from pathlib import Path

from greia_platform import boot_transaction as boot_module
from greia_platform.boot_transaction import (
    AB_BOOT_BACKENDS,
    BootArtifactError,
    BootArtifactRole,
    BootArtifactSet,
    BootBackendState,
    BootJournalError,
    BootTransactionBackend,
    BootTransactionCoordinator,
    BootTransactionError,
    BootTransactionJournal,
    BootTransactionState,
    FakeGrubBackend,
    FakePiTrybootBackend,
    InitramfsArtifact,
    InitramfsRole,
    JOURNAL_FILE_MODE,
    JOURNAL_FILE_NAME,
    coordinator_accepts_backend,
    require_recovery_path,
)
from greia_platform.persistent_layout import InstalledLayoutRecord
from greia_platform.slot_writer import FINALIZER_VERSION, FinalizationReceipt

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_INSTALL_SHA = "ab" * 32
_KERNEL_A = hashlib.sha256(b"candidate-kernel-bytes").hexdigest()
_INITRAMFS_A = hashlib.sha256(b"candidate-initramfs-bytes").hexdigest()
_INVENTORY = "cd" * 32
_SUPPORT = "ef" * 32


def _record_dict(**overrides: object) -> dict[str, object]:
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
    return base


def _pi_record_dict(**overrides: object) -> dict[str, object]:
    base = _record_dict(
        boot_backend="pi-tryboot-ab-v1",
        boot_control={"active_slot": "A", "kind": "pi-tryboot-v1"},
        install_profile="pi-400",
        layout_id="pi-mbr-tryboot-ab-v1",
        platform_family="arm64",
    )
    base.update(overrides)
    return base


def _receipt(slot: str, *, kernel: str = _KERNEL_A, initramfs: str = _INITRAMFS_A,
             layout_id: str = "modern-gpt-ab-v1") -> FinalizationReceipt:
    return FinalizationReceipt(
        schema_version=1,
        finalizer_version=FINALIZER_VERSION,
        release_id="greia-0.15.0",
        slot=slot,
        role=f"system-{slot.lower()}",
        base_sha256=kernel,
        base_bytes=200 * 1024,
        support_sha256=_SUPPORT,
        support_size=1024,
        inventory_token=_INVENTORY,
        packages=(),
        packages_digest=hashlib.sha256(b"\n").hexdigest(),
        generic_kernel_sha256=kernel,
        host_initramfs_sha256=initramfs,
        filesystem_uuid=_UUID_B_FS if slot == "B" else _UUID_A_FS,
        layout_id=layout_id,
        slot_capacity_bytes=1024 * 1024 * 1024,
    )


def _grub_artifacts() -> tuple[BootArtifactSet, BootArtifactSet]:
    record = InstalledLayoutRecord.from_dict(_record_dict())
    return (
        BootArtifactSet.from_finalization(receipt=_receipt("B"), record=record),
        BootArtifactSet.from_finalization(receipt=_receipt("A"), record=record),
    )


def _pi_artifacts(kernel: bytes, initramfs: bytes) -> tuple[BootArtifactSet, BootArtifactSet]:
    record = InstalledLayoutRecord.from_dict(_pi_record_dict())
    candidate = BootArtifactSet.from_finalization(
        receipt=_receipt(
            "B",
            kernel=hashlib.sha256(kernel).hexdigest(),
            initramfs=hashlib.sha256(initramfs).hexdigest(),
            layout_id="pi-mbr-tryboot-ab-v1",
        ),
        record=record,
    )
    accepted = BootArtifactSet.from_finalization(
        receipt=_receipt(
            "A",
            kernel=hashlib.sha256(b"accepted-kernel").hexdigest(),
            initramfs=hashlib.sha256(b"accepted-initramfs").hexdigest(),
            layout_id="pi-mbr-tryboot-ab-v1",
        ),
        record=record,
    )
    return candidate, accepted


class BootArtifactSetTests(unittest.TestCase):
    def test_from_finalization_binds_layout_root_and_roles(self) -> None:
        record = InstalledLayoutRecord.from_dict(_record_dict())
        artifacts = BootArtifactSet.from_finalization(
            receipt=_receipt("B"), record=record
        )
        self.assertEqual(artifacts.slot, "B")
        self.assertEqual(artifacts.root_partuuid, _UUID_B)
        self.assertEqual(artifacts.root_filesystem_uuid, _UUID_B_FS)
        self.assertEqual(artifacts.generic_kernel_sha256, _KERNEL_A)
        self.assertEqual(artifacts.generic_initramfs_sha256, _INITRAMFS_A)
        self.assertEqual(
            artifacts.role_digests,
            {
                BootArtifactRole.GENERIC_KERNEL.value: _KERNEL_A,
                BootArtifactRole.GENERIC_INITRAMFS.value: _INITRAMFS_A,
            },
        )
        self.assertEqual(artifacts.grub_entry_name, "greia-b")
        self.assertEqual(artifacts.kernel_cmdline_root(), f"root=PARTUUID={_UUID_B}")

    def test_adapter_paths_are_slot_stable(self) -> None:
        record = InstalledLayoutRecord.from_dict(_record_dict())
        first = BootArtifactSet.from_finalization(receipt=_receipt("A"), record=record)
        second = BootArtifactSet.from_finalization(receipt=_receipt("B"), record=record)
        self.assertEqual(first.kernel_path, second.kernel_path)
        self.assertEqual(first.initramfs_path, second.initramfs_path)
        self.assertEqual(first.grub_entry_name, "greia-a")
        self.assertNotEqual(first.grub_entry_name, second.grub_entry_name)

    def test_pi_roles_and_backend_isolation(self) -> None:
        record = InstalledLayoutRecord.from_dict(_pi_record_dict())
        artifacts = BootArtifactSet.from_finalization(
            receipt=_receipt("B", layout_id="pi-mbr-tryboot-ab-v1"), record=record
        )
        self.assertEqual(artifacts.pi_boot_role, "BOOT_B")
        with self.assertRaises(BootArtifactError):
            _ = artifacts.grub_entry_name
        grub_record = InstalledLayoutRecord.from_dict(_record_dict())
        grub_artifacts = BootArtifactSet.from_finalization(
            receipt=_receipt("A"), record=grub_record
        )
        with self.assertRaises(BootArtifactError):
            _ = grub_artifacts.pi_boot_role

    def test_rejects_layout_mismatch_and_single_root(self) -> None:
        record = InstalledLayoutRecord.from_dict(_record_dict())
        with self.assertRaises(BootArtifactError):
            BootArtifactSet.from_finalization(
                receipt=_receipt("B", layout_id="pi-mbr-tryboot-ab-v1"), record=record
            )
        single = InstalledLayoutRecord.from_dict(
            _record_dict(
                boot_backend="none-v1",
                boot_control={"active_slot": None, "kind": "none-v1"},
                layout_id="bios-single-ext4",
                accepted_slot=None,
                system_b=None,
            )
        )
        with self.assertRaises(BootArtifactError):
            BootArtifactSet.from_finalization(receipt=_receipt("A"), record=single)

    def test_rejects_bad_slot_and_unknown_backend(self) -> None:
        with self.assertRaises(BootTransactionError):
            BootArtifactSet.from_finalization(
                receipt=_receipt("C"),
                record=InstalledLayoutRecord.from_dict(_record_dict()),
            )
        with self.assertRaises(BootArtifactError):
            BootArtifactSet(
                slot="A", layout_id="modern-gpt-ab-v1", boot_backend="none-v1",
                generic_kernel_sha256=_KERNEL_A, generic_initramfs_sha256=_INITRAMFS_A,
                root_partuuid=_UUID_A, root_filesystem_uuid=_UUID_A_FS,
                release_id="greia-0.15.0",
            )


class InitramfsRoleTests(unittest.TestCase):
    def test_finalized_generic_from_receipt_and_recovery_path(self) -> None:
        artifact = InitramfsArtifact.finalized_generic_from_receipt(receipt=_receipt("B"))
        self.assertEqual(artifact.role, InitramfsRole.FINALIZED_GENERIC)
        self.assertEqual(artifact.producer, "slot-finalizer-v1")
        self.assertEqual(artifact.sha256, _INITRAMFS_A)
        self.assertIs(require_recovery_path([artifact]), artifact)

    def test_base_is_deterministic_build_input(self) -> None:
        artifact = InitramfsArtifact(
            role=InitramfsRole.BASE, sha256=_KERNEL_A,
            producer="release-builder-v1",
            release_id="greia-0.15.0",
        )
        self.assertIsNone(artifact.derived_from_sha256)
        # BASE alone is not a per-slot recovery path.
        with self.assertRaises(BootArtifactError):
            require_recovery_path([artifact])

    def test_host_fast_is_never_the_sole_recovery_path(self) -> None:
        fast = InitramfsArtifact(
            role=InitramfsRole.HOST_FAST, sha256="12" * 32,
            producer="host-derivative-v1",
            release_id="greia-0.15.0",
            derived_from_sha256=_INITRAMFS_A,
        )
        with self.assertRaises(BootArtifactError):
            require_recovery_path([fast])
        with self.assertRaises(BootArtifactError):
            require_recovery_path([])
        generic = InitramfsArtifact.finalized_generic_from_receipt(receipt=_receipt("B"))
        self.assertIs(require_recovery_path([fast, generic]), generic)

    def test_producer_role_binding_and_derivation_rules(self) -> None:
        with self.assertRaises(BootArtifactError):
            InitramfsArtifact(
                role=InitramfsRole.BASE, sha256=_KERNEL_A,
                producer="slot-finalizer-v1",
                release_id="greia-0.15.0",
            )
        with self.assertRaises(BootArtifactError):
            InitramfsArtifact(
                role=InitramfsRole.HOST_FAST, sha256="12" * 32,
                producer="host-derivative-v1",
                release_id="greia-0.15.0",
            )
        with self.assertRaises(BootArtifactError):
            InitramfsArtifact(
                role=InitramfsRole.FINALIZED_GENERIC, sha256=_INITRAMFS_A,
                producer="slot-finalizer-v1",
                release_id="greia-0.15.0",
                derived_from_sha256=_KERNEL_A,
            )


class FakeGrubBackendTests(unittest.TestCase):
    def test_success_one_shot_and_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            candidate, accepted = _grub_artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            armed = coordinator.arm()
            self.assertEqual(armed.one_shot_slot, "B")
            # Persistent default stays accepted until health commit.
            self.assertEqual(armed.default_slot, "A")
            self.assertEqual(backend.entry_name("B"), "greia-b")
            self.assertEqual(backend.simulate_reboot(), "B")
            # Re-attach proves file persistence across the reboot boundary.
            rebooted = FakeGrubBackend.attach(root / "grub")
            resumed = BootTransactionCoordinator.resume(
                journal_dir=root / "journal", backend=rebooted,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
            )
            observed, decision = resumed.observe_boot()
            self.assertEqual(observed, "B")
            self.assertEqual(
                resumed.journal.state, BootTransactionState.CANDIDATE_BOOTING
            )
            committed = resumed.commit()
            self.assertEqual(committed.default_slot, "B")
            self.assertIsNone(committed.one_shot_slot)
            self.assertEqual(resumed.journal.state, BootTransactionState.ACCEPTED)
            readiness = rebooted.verify_rollback_ready()
            self.assertTrue(readiness.ready)
            self.assertEqual(readiness.accepted_slot, "B")

    def test_one_shot_consumption_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            candidate, accepted = _grub_artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            coordinator.arm()
            self.assertEqual(backend.simulate_reboot(), "B")
            # No health commit: the next boot is the accepted default again.
            self.assertEqual(backend.simulate_reboot(), "A")
            rebooted = FakeGrubBackend.attach(root / "grub")
            resumed = BootTransactionCoordinator.resume(
                journal_dir=root / "journal", backend=rebooted,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
            )
            observed, _ = resumed.observe_boot()
            self.assertEqual(observed, "A")
            self.assertEqual(resumed.journal.state, BootTransactionState.ROLLED_BACK)
            self.assertEqual(rebooted.inspect().default_slot, "A")

    def test_failed_candidate_marks_rolled_back(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            candidate, accepted = _grub_artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            coordinator.arm()
            # Candidate kernel fails: firmware boots the accepted default.
            backend.reconcile("A")
            observed, _ = coordinator.observe_boot()
            self.assertEqual(observed, "A")
            self.assertEqual(coordinator.journal.state, BootTransactionState.ROLLED_BACK)
            with self.assertRaises(BootTransactionError):
                coordinator.commit()

    def test_arm_and_commit_guards(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            with self.assertRaises(BootTransactionError):
                backend.arm_one_shot("A")
            with self.assertRaises(BootTransactionError):
                backend.observe_booted_slot()
            with self.assertRaises(BootTransactionError):
                backend.commit_accepted("B")
            backend.arm_one_shot("B")
            with self.assertRaises(BootTransactionError):
                backend.arm_one_shot("B")
            readiness = backend.verify_rollback_ready()
            self.assertFalse(readiness.ready)

    def test_corrupt_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            state_path = root / "grub" / "grub-boot-state.json"
            state_path.write_text("{corrupt", encoding="utf-8")
            os.chmod(state_path, JOURNAL_FILE_MODE)
            with self.assertRaises(BootTransactionError):
                backend.inspect()
            state_path.unlink()
            with self.assertRaises(BootTransactionError):
                backend.inspect()


class FakePiBackendTests(unittest.TestCase):
    _KERNEL = b"pi-candidate-kernel-bytes"
    _INITRAMFS = b"pi-candidate-initramfs-bytes"

    def test_success_tryboot_and_durable_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakePiTrybootBackend.initialize(root / "pi", default_slot="A")
            candidate, accepted = _pi_artifacts(self._KERNEL, self._INITRAMFS)
            manifest = backend.stage_candidate_boot(
                "B", kernel_bytes=self._KERNEL,
                initramfs_bytes=self._INITRAMFS, artifacts=candidate,
            )
            self.assertEqual(manifest["boot_role"], "BOOT_B")
            backend.verify_boot_pair("B", candidate)
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            armed = coordinator.arm()
            self.assertEqual(armed.one_shot_slot, "B")
            self.assertEqual(armed.default_slot, "A")
            self.assertEqual(backend.simulate_reboot(), "B")
            rebooted = FakePiTrybootBackend.attach(root / "pi")
            resumed = BootTransactionCoordinator.resume(
                journal_dir=root / "journal", backend=rebooted,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
            )
            observed, _ = resumed.observe_boot()
            self.assertEqual(observed, "B")
            committed = resumed.commit()
            self.assertEqual(committed.default_slot, "B")
            autoboot = (root / "pi" / "boot_control" / "autoboot.txt").read_text(
                encoding="utf-8"
            )
            self.assertEqual(autoboot, "boot_partition=3\n")
            self.assertEqual(resumed.journal.state, BootTransactionState.ACCEPTED)
            self.assertTrue(rebooted.verify_rollback_ready().ready)

    def test_tryboot_consumption_returns_to_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakePiTrybootBackend.initialize(root / "pi", default_slot="A")
            candidate, _ = _pi_artifacts(self._KERNEL, self._INITRAMFS)
            backend.stage_candidate_boot(
                "B", kernel_bytes=self._KERNEL,
                initramfs_bytes=self._INITRAMFS, artifacts=candidate,
            )
            backend.arm_one_shot("B")
            self.assertEqual(backend.simulate_reboot(), "B")
            self.assertEqual(backend.simulate_reboot(), "A")

    def test_staging_and_arm_guards(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakePiTrybootBackend.initialize(root / "pi", default_slot="A")
            candidate, accepted = _pi_artifacts(self._KERNEL, self._INITRAMFS)
            with self.assertRaises(BootTransactionError):
                backend.arm_one_shot("B")
            with self.assertRaises(BootTransactionError):
                backend.stage_candidate_boot(
                    "B", kernel_bytes=b"wrong",
                    initramfs_bytes=self._INITRAMFS, artifacts=candidate,
                )
            with self.assertRaises(BootTransactionError):
                backend.stage_candidate_boot(
                    "A", kernel_bytes=self._KERNEL,
                    initramfs_bytes=self._INITRAMFS, artifacts=accepted,
                )
            backend.stage_candidate_boot(
                "B", kernel_bytes=self._KERNEL,
                initramfs_bytes=self._INITRAMFS, artifacts=candidate,
            )
            with self.assertRaises(BootArtifactError):
                backend.stage_candidate_boot(
                    "B", kernel_bytes=self._KERNEL,
                    initramfs_bytes=self._INITRAMFS, artifacts=accepted,
                )
            # Tamper after staging: verification fails closed.
            (root / "pi" / "boot_b" / "kernel.img").write_bytes(b"tampered")
            with self.assertRaises(BootTransactionError):
                backend.verify_boot_pair("B", candidate)

    def test_corrupt_boot_control_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakePiTrybootBackend.initialize(root / "pi", default_slot="A")
            control = root / "pi" / "boot_control"
            for bad in ("", "boot_partition=9\n", "garbage\n", "boot_partition=2"):
                (control / "autoboot.txt").write_text(bad, encoding="utf-8")
                os.chmod(control / "autoboot.txt", JOURNAL_FILE_MODE)
                with self.assertRaises(BootTransactionError, msg=f"payload={bad!r}"):
                    backend.inspect()
            (control / "autoboot.txt").unlink()
            with self.assertRaises(BootTransactionError):
                backend.inspect()

    def test_no_eeprom_surface(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            backend = FakePiTrybootBackend.initialize(Path(raw) / "pi", default_slot="A")
            names = [name.lower() for name in dir(backend)]
            self.assertFalse(any("eeprom" in name for name in names))
            self.assertFalse(any("eeprom" in name for name in dir(type(backend))))

    def test_boot_control_files_are_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakePiTrybootBackend.initialize(root / "pi", default_slot="A")
            candidate, _ = _pi_artifacts(self._KERNEL, self._INITRAMFS)
            backend.stage_candidate_boot(
                "B", kernel_bytes=self._KERNEL,
                initramfs_bytes=self._INITRAMFS, artifacts=candidate,
            )
            backend.arm_one_shot("B")
            for path in (root / "pi").rglob("*"):
                if path.is_file() and not path.is_symlink():
                    self.assertEqual(
                        stat.S_IMODE(path.stat().st_mode), 0o600, msg=str(path)
                    )


class JournalTests(unittest.TestCase):
    def test_crash_between_arm_and_record_resumes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            candidate, accepted = _grub_artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            # Crash after backend arm, before the journal records it.
            backend.arm_one_shot("B")
            backend.simulate_reboot()
            rebooted = FakeGrubBackend.attach(root / "grub")
            resumed = BootTransactionCoordinator.resume(
                journal_dir=root / "journal", backend=rebooted,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
            )
            observed, decision = resumed.reconcile_after_crash()
            self.assertEqual(observed, "B")
            self.assertEqual(decision.transition, BootTransactionState.CANDIDATE_BOOTING)
            self.assertEqual(
                resumed.journal.state, BootTransactionState.CANDIDATE_BOOTING
            )

    def test_reconcile_without_observation_refuses_to_guess(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            candidate, accepted = _grub_artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            observed, decision = coordinator.reconcile_after_crash()
            self.assertIsNone(observed)
            self.assertIsNone(decision.transition)
            self.assertEqual(coordinator.journal.state, BootTransactionState.UPDATE_STAGED)

    def test_first_install_flow(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            record = InstalledLayoutRecord.from_dict(_record_dict())
            artifact_a = BootArtifactSet.from_finalization(
                receipt=_receipt("A"), record=record
            )
            coordinator = BootTransactionCoordinator.begin_first_install(
                journal_dir=root / "journal", backend=backend, artifact_a=artifact_a
            )
            self.assertEqual(
                coordinator.journal.state, BootTransactionState.FIRST_INSTALL_PENDING
            )
            with self.assertRaises(BootTransactionError):
                coordinator.arm()
            self.assertEqual(backend.simulate_reboot(), "A")
            observed, _ = coordinator.observe_boot()
            self.assertEqual(observed, "A")
            coordinator.commit()
            self.assertEqual(coordinator.journal.state, BootTransactionState.ACCEPTED)

    def test_journal_guards(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            candidate, accepted = _grub_artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            journal = coordinator.journal
            with self.assertRaises(BootJournalError):
                journal.record(BootTransactionState.ACCEPTED, "skip ahead")
            with self.assertRaises(BootJournalError):
                BootTransactionJournal.begin_update(
                    root / "journal", layout_id="modern-gpt-ab-v1",
                    boot_backend="grub-ab-v1", release_id="greia-0.15.0",
                    candidate_slot="B", accepted_slot="A",
                )
            coordinator.mark_failed("candidate userspace never became healthy")
            self.assertEqual(journal.state, BootTransactionState.FAILED)
            with self.assertRaises(BootJournalError):
                journal.record(BootTransactionState.ACCEPTED, "late commit")
            with self.assertRaises(BootJournalError):
                coordinator.mark_failed("again")

    def test_corrupt_journal_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            candidate, accepted = _grub_artifacts()
            BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            journal_path = root / "journal" / JOURNAL_FILE_NAME
            pristine = json.loads(journal_path.read_text(encoding="utf-8"))
            # Same content, non-canonical encoding: still rejected.
            journal_path.write_bytes(
                (json.dumps(pristine) + "\n").encode("utf-8")
            )
            os.chmod(journal_path, JOURNAL_FILE_MODE)
            with self.assertRaises(BootJournalError):
                BootTransactionJournal.load(root / "journal")
            mutations = (
                {"state": "accepted"},
                {"transitions": []},
            )
            for mutation in mutations:
                payload = json.loads(json.dumps(pristine))
                payload.update(mutation)
                journal_path.write_bytes(
                    (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
                )
                os.chmod(journal_path, JOURNAL_FILE_MODE)
                with self.assertRaises(BootJournalError):
                    BootTransactionJournal.load(root / "journal")
            payload = json.loads(json.dumps(pristine))
            payload["transitions"].append(
                {"actor": "parent", "note": "x", "seq": 99, "state": "failed"}
            )
            journal_path.write_bytes(
                (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
            )
            os.chmod(journal_path, JOURNAL_FILE_MODE)
            with self.assertRaises(BootJournalError):
                BootTransactionJournal.load(root / "journal")
            journal_path.write_text("{not json", encoding="utf-8")
            os.chmod(journal_path, JOURNAL_FILE_MODE)
            with self.assertRaises(BootJournalError):
                BootTransactionJournal.load(root / "journal")

    def test_journal_file_gates(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            candidate, accepted = _grub_artifacts()
            BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            journal_path = root / "journal" / JOURNAL_FILE_NAME
            os.chmod(journal_path, 0o644)
            with self.assertRaises(BootTransactionError):
                BootTransactionJournal.load(root / "journal")
            os.chmod(journal_path, JOURNAL_FILE_MODE)
            BootTransactionJournal.load(root / "journal")


class CoordinatorProtocolTests(unittest.TestCase):
    def test_one_interface_serves_both_backends(self) -> None:
        self.assertIn("grub-ab-v1", AB_BOOT_BACKENDS)
        self.assertIn("pi-tryboot-ab-v1", AB_BOOT_BACKENDS)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            grub = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            pi = FakePiTrybootBackend.initialize(root / "pi", default_slot="A")
            self.assertTrue(coordinator_accepts_backend(grub))
            self.assertTrue(coordinator_accepts_backend(pi))
            for backend in (grub, pi):
                self.assertTrue(coordinator_accepts_backend(backend))
                protocol_methods = {
                    name
                    for name, member in inspect.getmembers(BootTransactionBackend)
                    if callable(member) and not name.startswith("_")
                }
                for name in protocol_methods:
                    self.assertTrue(
                        callable(getattr(backend, name, None)),
                        msg=f"{type(backend).__name__} lacks {name}",
                    )
                state = backend.inspect()
                self.assertIsInstance(state, BootBackendState)
                self.assertEqual(state.default_slot, "A")
                self.assertIsNone(state.one_shot_slot)

    def test_no_arbitrary_boot_target_api(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backends = (
                FakeGrubBackend.initialize(root / "grub", default_slot="A"),
                FakePiTrybootBackend.initialize(root / "pi", default_slot="A"),
            )
            for backend in backends:
                for bad in ("C", "", "/dev/sda1", "greia-a", "BOOT_B", "../x", "a"):
                    with self.assertRaises(BootTransactionError, msg=f"{backend}/{bad}"):
                        backend.arm_one_shot(bad)
                    with self.assertRaises(BootTransactionError, msg=f"{backend}/{bad}"):
                        backend.commit_accepted(bad)
                    with self.assertRaises(BootTransactionError, msg=f"{backend}/{bad}"):
                        backend.reconcile(bad)
                arm_params = list(
                    inspect.signature(type(backend).arm_one_shot).parameters
                )
                self.assertEqual(arm_params, ["self", "candidate"])
                commit_params = list(
                    inspect.signature(type(backend).commit_accepted).parameters
                )
                self.assertEqual(commit_params, ["self", "slot"])

    def test_backend_mismatch_and_slot_binding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            candidate, accepted = _grub_artifacts()
            with self.assertRaises(BootTransactionError):
                BootTransactionCoordinator.begin_update(
                    journal_dir=root / "journal", backend=backend,
                    candidate_artifacts=accepted, accepted_artifacts=accepted,
                    release_id="greia-0.15.0",
                )
            pi_record = InstalledLayoutRecord.from_dict(_pi_record_dict())
            pi_candidate = BootArtifactSet.from_finalization(
                receipt=_receipt("B", layout_id="pi-mbr-tryboot-ab-v1"),
                record=pi_record,
            )
            with self.assertRaises(BootTransactionError):
                BootTransactionCoordinator.begin_update(
                    journal_dir=root / "journal2", backend=backend,
                    candidate_artifacts=pi_candidate, accepted_artifacts=accepted,
                    release_id="greia-0.15.0",
                )

    def test_module_has_no_privileged_or_manager_surface(self) -> None:
        source = Path(boot_module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess", "os.system", "shell=True", "shell=",
            "/dev/", "class .*Manager", "class .*Daemon", "class .*Parser",
        ):
            self.assertIsNone(
                re.search(forbidden, source), msg=f"forbidden surface: {forbidden}"
            )


if __name__ == "__main__":
    unittest.main()

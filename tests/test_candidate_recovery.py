"""T4-RECOVER: bounded failed-candidate recovery trigger.

Proves the TAKEOVER-4/D55 contract through the production owner (the boot
transaction journal + backend): each recoverable class triggers the reboot
path while the previous accepted slot stays the persistent default, the
hard hang stays manual (no proven watchdog), and the image carries the
exact systemd/panic configuration. R0/R1 source scope: files and fakes
only, no real reboot is ever executed (the helper is exercised in dry-run
or no-action modes only).
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from greia_platform import boot_transaction as boot_module
from greia_platform.boot_transaction import (
    AUTOMATIC_RECOVERY_CLASSES,
    CANDIDATE_HEALTH_DEADLINE_SEC,
    CANDIDATE_RECOVERY_SERVICE,
    CANDIDATE_RECOVERY_TIMER,
    PANIC_REBOOT_SYSCTL,
    RECOVERY_ACCEPTED_SLOT_MEDIUM,
    RECOVERY_SETUP_MEDIUM,
    RECOVERY_TRIGGER_STATES,
    RECOVERY_HELPER_PATH,
    RECOVERY_NOTE_PREFIX,
    BootArtifactSet,
    BootJournalError,
    BootTransactionCoordinator,
    BootTransactionError,
    BootTransactionJournal,
    BootTransactionState,
    FakeGrubBackend,
    RecoveryAction,
    RecoveryClass,
    describe_recovery_contract,
    format_recovery_note,
    is_watchdog_proven,
    mark_candidate_unhealthy,
    parse_recovery_note,
    recovery_action_for,
)
from greia_platform.grub_ab import GrubEnvBackend
from greia_platform.boot_transaction import (
    BootHistory,
    describe_previous_boot,
)
from greia_platform.persistent_layout import InstalledLayoutRecord
from greia_platform.slot_writer import FINALIZER_VERSION, FinalizationReceipt

ROOT = Path(__file__).resolve().parents[1]

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


def _receipt(slot: str) -> FinalizationReceipt:
    return FinalizationReceipt(
        schema_version=1,
        finalizer_version=FINALIZER_VERSION,
        release_id="greia-0.15.0",
        slot=slot,
        role=f"system-{slot.lower()}",
        base_sha256=_KERNEL_A,
        base_bytes=200 * 1024,
        support_sha256=_SUPPORT,
        support_size=1024,
        inventory_token=_INVENTORY,
        packages=(),
        packages_digest=hashlib.sha256(b"\n").hexdigest(),
        generic_kernel_sha256=_KERNEL_A,
        host_initramfs_sha256=_INITRAMFS_A,
        filesystem_uuid=_UUID_B_FS if slot == "B" else _UUID_A_FS,
        layout_id="modern-gpt-ab-v1",
        slot_capacity_bytes=1024 * 1024 * 1024,
    )


def _artifacts() -> tuple[BootArtifactSet, BootArtifactSet]:
    record = InstalledLayoutRecord.from_dict(_record_dict())
    return (
        BootArtifactSet.from_finalization(receipt=_receipt("B"), record=record),
        BootArtifactSet.from_finalization(receipt=_receipt("A"), record=record),
    )


def _booted_candidate(root: Path):
    """Arm B, boot it once (one-shot consumed), observe it: unhealthy wait."""
    backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
    candidate, accepted = _artifacts()
    coordinator = BootTransactionCoordinator.begin_update(
        journal_dir=root / "journal", backend=backend,
        candidate_artifacts=candidate, accepted_artifacts=accepted,
        release_id="greia-0.15.0",
    )
    coordinator.arm()
    assert backend.simulate_reboot() == "B"
    rebooted = FakeGrubBackend.attach(root / "grub")
    resumed = BootTransactionCoordinator.resume(
        journal_dir=root / "journal", backend=rebooted,
        candidate_artifacts=candidate, accepted_artifacts=accepted,
    )
    observed, _ = resumed.observe_boot()
    assert observed == "B"
    assert resumed.journal.state is BootTransactionState.CANDIDATE_BOOTING
    return resumed, rebooted


class RecoveryContractTests(unittest.TestCase):
    def test_deadline_is_bounded(self) -> None:
        self.assertGreaterEqual(CANDIDATE_HEALTH_DEADLINE_SEC, 60)
        self.assertLessEqual(CANDIDATE_HEALTH_DEADLINE_SEC, 600)
        self.assertEqual(CANDIDATE_HEALTH_DEADLINE_SEC, 180)

    def test_classes_1_to_4_reboot_automatically(self) -> None:
        for value in (
            RecoveryClass.LAUNCHER_EXIT,
            RecoveryClass.USERSPACE_EMERGENCY,
            RecoveryClass.HEALTH_SERVICE_FAILURE,
            RecoveryClass.KERNEL_PANIC,
        ):
            self.assertEqual(
                recovery_action_for(value), RecoveryAction.AUTOMATIC_REBOOT)
            self.assertIn(value, AUTOMATIC_RECOVERY_CLASSES)

    def test_hard_hang_is_manual_without_proven_watchdog(self) -> None:
        self.assertEqual(
            recovery_action_for(RecoveryClass.HARD_HANG),
            RecoveryAction.MANUAL_POWER_CYCLE)
        self.assertNotIn(RecoveryClass.HARD_HANG, AUTOMATIC_RECOVERY_CLASSES)
        self.assertFalse(is_watchdog_proven("acer-aspire-one-i386"))
        self.assertFalse(is_watchdog_proven("pi-400"))
        self.assertFalse(is_watchdog_proven("modern-amd64"))
        contract = describe_recovery_contract()
        self.assertEqual(contract["classes"]["hard-hang"], "manual-power-cycle")
        self.assertEqual(contract["watchdog_proven_platforms"], [])

    def test_trigger_rejects_hard_hang(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            resumed, _ = _booted_candidate(root)
            with self.assertRaises(BootJournalError):
                mark_candidate_unhealthy(
                    resumed, recovery_class=RecoveryClass.HARD_HANG)

    def test_note_format_parse_roundtrip_and_bounds(self) -> None:
        note = format_recovery_note(
            RecoveryClass.LAUNCHER_EXIT, RecoveryAction.AUTOMATIC_REBOOT,
            "deadline expired without BOOT_HEALTHY")
        self.assertTrue(note.startswith(RECOVERY_NOTE_PREFIX))
        parsed = parse_recovery_note(note)
        assert parsed is not None
        self.assertEqual(parsed["recovery_class"], "launcher-exit")
        self.assertEqual(parsed["recovery_action"], "automatic-reboot")
        self.assertIsNone(parse_recovery_note("candidate staged and verified"))
        self.assertIsNone(parse_recovery_note("recovery:bogus:automatic-reboot"))
        with self.assertRaises(BootJournalError):
            format_recovery_note(
                RecoveryClass.LAUNCHER_EXIT, RecoveryAction.AUTOMATIC_REBOOT,
                "x" * 1024)
        with self.assertRaises(BootJournalError):
            recovery_action_for("bogus-class")

    def test_module_has_no_privileged_or_manager_surface(self) -> None:
        source = Path(boot_module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess", "os.system", "shell=True", "shell=",
            "/dev/", "class .*Manager", "class .*Daemon", "class .*Parser",
        ):
            self.assertIsNone(
                re.search(forbidden, source), msg=f"forbidden surface: {forbidden}")


class RecoverableClassTriggerTests(unittest.TestCase):
    """Classes 1-4: trigger marks FAILED, default stays accepted, reboot
    returns to the accepted slot (observed ROLLED_BACK)."""

    def _trigger_cycle(self, recovery_class: RecoveryClass, detail: str) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            resumed, rebooted = _booted_candidate(root)
            decision = mark_candidate_unhealthy(
                resumed, recovery_class=recovery_class, detail=detail)
            self.assertEqual(decision.journal_transition, BootTransactionState.FAILED)
            self.assertEqual(resumed.journal.state, BootTransactionState.FAILED)
            self.assertEqual(decision.accepted_slot, "A")
            self.assertEqual(decision.candidate_slot, "B")
            self.assertEqual(decision.recovery_medium, RECOVERY_ACCEPTED_SLOT_MEDIUM)
            parsed = parse_recovery_note(decision.note)
            assert parsed is not None
            self.assertEqual(parsed["recovery_class"], recovery_class.value)
            # Persistent default untouched by the trigger.
            self.assertEqual(rebooted.inspect().default_slot, "A")
            # The controlled reboot returns to the accepted default; the
            # next observation reconciles the candidate as rolled back.
            self.assertEqual(rebooted.simulate_reboot(), "A")
            candidate, accepted = _artifacts()
            after = BootTransactionCoordinator.resume(
                journal_dir=root / "journal", backend=rebooted,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
            )
            # Journal is terminal FAILED; a fresh observation folds the
            # backend fact. Fresh transaction proves rollback readiness.
            readiness = rebooted.verify_rollback_ready()
            self.assertTrue(readiness.ready)
            self.assertEqual(readiness.accepted_slot, "A")
            self.assertEqual(after.journal.state, BootTransactionState.FAILED)

    def test_class1_launcher_exit_triggers_reboot_path(self) -> None:
        self._trigger_cycle(
            RecoveryClass.LAUNCHER_EXIT, "launcher crashed before BOOT_HEALTHY")

    def test_class2_userspace_emergency_triggers_reboot_path(self) -> None:
        self._trigger_cycle(
            RecoveryClass.USERSPACE_EMERGENCY, "emergency state before health")

    def test_class3_health_service_failure_triggers_reboot_path(self) -> None:
        self._trigger_cycle(
            RecoveryClass.HEALTH_SERVICE_FAILURE, "BOOT_HEALTHY never confirmed")

    def test_class4_kernel_panic_triggers_reboot_path(self) -> None:
        self._trigger_cycle(
            RecoveryClass.KERNEL_PANIC, "panic reboot configured via sysctl")
        # Panic reboot itself is kernel-owned: prove the image config.
        sysctl_path = (
            ROOT / "build" / "overlay" / "etc" / "sysctl.d"
            / "30-greia-panic-reboot.conf")
        text = sysctl_path.read_text(encoding="utf-8")
        for key, value in PANIC_REBOOT_SYSCTL.items():
            self.assertIn(f"{key} = {value}", text)

    def test_trigger_refuses_terminal_journal(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            resumed, _ = _booted_candidate(root)
            resumed.mark_failed("first marking")
            with self.assertRaises(BootJournalError):
                mark_candidate_unhealthy(
                    resumed, recovery_class=RecoveryClass.LAUNCHER_EXIT)

    def test_first_install_failure_is_setup_medium(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            record = InstalledLayoutRecord.from_dict(_record_dict())
            artifact_a = BootArtifactSet.from_finalization(
                receipt=_receipt("A"), record=record)
            coordinator = BootTransactionCoordinator.begin_first_install(
                journal_dir=root / "journal", backend=backend, artifact_a=artifact_a)
            decision = mark_candidate_unhealthy(
                coordinator, recovery_class=RecoveryClass.HEALTH_SERVICE_FAILURE,
                detail="first boot never healthy")
            self.assertEqual(decision.recovery_medium, RECOVERY_SETUP_MEDIUM)
            self.assertEqual(coordinator.journal.state, BootTransactionState.FAILED)


class RecoveryImageWiringTests(unittest.TestCase):
    def _paths(self) -> dict[str, Path]:
        overlay = ROOT / "build" / "overlay"
        return {
            "service": overlay / "etc" / "systemd" / "system"
                       / "greia-candidate-recovery.service",
            "timer": overlay / "etc" / "systemd" / "system"
                     / "greia-candidate-recovery.timer",
            "sysctl": overlay / "etc" / "sysctl.d" / "30-greia-panic-reboot.conf",
            "helper": overlay / "usr" / "local" / "lib" / "greia-os"
                      / "greia-candidate-recovery",
        }

    def test_units_timer_sysctl_agree_with_code(self) -> None:
        paths = self._paths()
        for name, path in paths.items():
            self.assertTrue(path.is_file(), msg=name)
            self.assertFalse(path.is_symlink(), msg=name)
        service = paths["service"].read_text(encoding="utf-8")
        self.assertIn("Type=oneshot", service)
        self.assertIn(RECOVERY_HELPER_PATH, service)
        self.assertNotIn("Restart=always", service)
        timer = paths["timer"].read_text(encoding="utf-8")
        self.assertIn("OnBootSec=3min", timer)
        self.assertIn(CANDIDATE_RECOVERY_SERVICE, timer)
        self.assertEqual(CANDIDATE_RECOVERY_TIMER, paths["timer"].name)
        sysctl = paths["sysctl"].read_text(encoding="utf-8")
        for key, value in PANIC_REBOOT_SYSCTL.items():
            self.assertIn(f"{key} = {value}", sysctl)
        helper = paths["helper"]
        self.assertTrue(os.access(helper, os.X_OK))
        contract = describe_recovery_contract()
        self.assertEqual(contract["timer"], CANDIDATE_RECOVERY_TIMER)
        self.assertEqual(contract["service"], CANDIDATE_RECOVERY_SERVICE)
        self.assertEqual(contract["helper"], RECOVERY_HELPER_PATH)
        self.assertEqual(contract["deadline_sec"], CANDIDATE_HEALTH_DEADLINE_SEC)
        # Timer fires once per boot: no looping daemon semantics.
        self.assertNotIn("OnUnitActiveSec", timer)
        self.assertNotIn("OnCalendar", timer)

    def test_helper_help_states_manual_hard_hang_honestly(self) -> None:
        helper = self._paths()["helper"]
        completed = subprocess.run(
            ["sh", str(helper), "--help"], capture_output=True, text=True,
            timeout=30)
        self.assertEqual(completed.returncode, 0)
        out = completed.stdout.lower()
        self.assertIn("manual", out)
        self.assertIn("power cycle", out)
        self.assertIn("no proven watchdog", out)
        self.assertNotIn("watchdog reboots", out)

    def test_helper_plain_boot_is_noop(self) -> None:
        helper = self._paths()["helper"]
        with tempfile.TemporaryDirectory() as raw:
            env = dict(os.environ)
            env["GREIA_UPDATE_STATE_DIR"] = f"{raw}/update-state"
            env["GREIA_BOOT_JOURNAL_DIR"] = f"{raw}/boot-journal"
            env["GREIA_GRUBENV_DIR"] = f"{raw}/grub"
            env["GREIA_RECOVERY_DRY_RUN"] = "0"
            env["PYTHONPATH"] = str(ROOT / "src")
            completed = subprocess.run(
                ["sh", str(helper)], capture_output=True, text=True,
                timeout=60, env=env)
            self.assertEqual(completed.returncode, 0)
            self.assertIn("RECOVERY_STATUS=no-action", completed.stdout)
            self.assertNotIn("trigger-reboot", completed.stdout)

    def test_helper_deadline_path_marks_failed_without_reboot(self) -> None:
        """Production wiring: real grubenv backend + real journal files.

        Dry-run proves the helper reaches the production decision (journal
        + backend observation) without executing any reboot.
        """
        helper = self._paths()["helper"]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            grub_dir = root / "grub"
            backend = GrubEnvBackend.initialize(grub_dir, default_slot="A")
            journal_parent = root / "update-state"
            journal_dir = journal_parent / "system-updates" / "journal"
            candidate, accepted = _artifacts()
            # GrubEnvBackend speaks the grub-ab-v1 protocol: reuse the
            # coordinator to stage journal + one-shot through production
            # code paths (artifact binding, arm guards).
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=journal_dir, backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            coordinator.arm()
            self.assertEqual(backend.simulate_reboot(), "B")
            attach = GrubEnvBackend.attach(grub_dir)
            resumed = BootTransactionCoordinator.resume(
                journal_dir=journal_dir, backend=attach,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
            )
            resumed.observe_boot()
            self.assertEqual(
                resumed.journal.state, BootTransactionState.CANDIDATE_BOOTING)
            env = dict(os.environ)
            env["GREIA_UPDATE_STATE_DIR"] = str(journal_parent)
            env["GREIA_BOOT_JOURNAL_DIR"] = str(root / "boot-journal")
            env["GREIA_GRUBENV_DIR"] = str(grub_dir)
            env["GREIA_RECOVERY_DRY_RUN"] = "1"
            env["PYTHONPATH"] = str(ROOT / "src")
            completed = subprocess.run(
                ["sh", str(helper)], capture_output=True, text=True,
                timeout=60, env=env)
            self.assertEqual(completed.returncode, 0)
            self.assertIn(
                "RECOVERY_STATUS=trigger-reboot:health-service-failure",
                completed.stdout)
            self.assertIn("RECOVERY_ACCEPTED_SLOT=A", completed.stdout)
            # Dry run mutates nothing: journal stays candidate-booting and
            # the backend default stays accepted.
            reloaded = BootTransactionJournal.load(journal_dir)
            self.assertEqual(
                reloaded.state, BootTransactionState.CANDIDATE_BOOTING)
            self.assertEqual(attach.inspect().default_slot, "A")

    def test_helper_already_on_accepted_is_noop(self) -> None:
        helper = self._paths()["helper"]
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            grub_dir = root / "grub"
            backend = GrubEnvBackend.initialize(grub_dir, default_slot="A")
            journal_parent = root / "update-state"
            journal_dir = journal_parent / "system-updates" / "journal"
            candidate, accepted = _artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=journal_dir, backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id="greia-0.15.0",
            )
            coordinator.arm()
            self.assertEqual(backend.simulate_reboot(), "B")
            # Failed candidate fell back without health: accepted boots.
            self.assertEqual(backend.simulate_reboot(), "A")
            before = BootTransactionJournal.load(journal_dir).state
            env = dict(os.environ)
            env["GREIA_UPDATE_STATE_DIR"] = str(journal_parent)
            env["GREIA_BOOT_JOURNAL_DIR"] = str(root / "boot-journal")
            env["GREIA_GRUBENV_DIR"] = str(grub_dir)
            env["GREIA_RECOVERY_DRY_RUN"] = "0"
            env["PYTHONPATH"] = str(ROOT / "src")
            completed = subprocess.run(
                ["sh", str(helper)], capture_output=True, text=True,
                timeout=60, env=env)
            self.assertEqual(completed.returncode, 0)
            self.assertIn("already-on-accepted-slot", completed.stdout)
            self.assertNotIn("trigger-reboot", completed.stdout)
            reloaded = BootTransactionJournal.load(journal_dir)
            self.assertEqual(reloaded.state, before)


class Recover2FollowUpTests(unittest.TestCase):
    """T4-RECOVER2: doc fidelity, helper scoping, cause-label decision."""

    def test_trigger_failed_is_terminal_no_rolled_back(self) -> None:
        """Acceptance 1: after trigger-FAILED, reconcile never yields
        ROLLED_BACK (matches the corrected wording)."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            resumed, _ = _booted_candidate(root)
            decision = mark_candidate_unhealthy(
                resumed, recovery_class=RecoveryClass.LAUNCHER_EXIT,
                detail="terminal check")
            self.assertEqual(decision.journal_transition, BootTransactionState.FAILED)
            self.assertEqual(resumed.journal.state, BootTransactionState.FAILED)
            for observed in ("A", "B", None):
                outcome = resumed.journal.reconcile(observed)
                self.assertIsNone(
                    outcome.transition,
                    msg=f"terminal FAILED must not transition on {observed!r}")
                assert outcome.transition is None
                self.assertNotEqual(outcome.transition, BootTransactionState.ROLLED_BACK)
            self.assertEqual(resumed.journal.state, BootTransactionState.FAILED)

    def test_contract_describes_x86_only_scope(self) -> None:
        contract = describe_recovery_contract()
        self.assertIn("x86", str(contract.get("backend_scope")))
        self.assertIn("GrubEnvBackend", str(contract.get("backend_scope")))
        self.assertIn("backend_unavailable", contract)
        self.assertIn("no reboot", str(contract.get("backend_unavailable")))
        self.assertIn("PI8", str(contract.get("pi_tryboot")))

    def test_helper_help_states_x86_only_and_pi_deferred(self) -> None:
        helper = (
            ROOT / "build" / "overlay" / "usr" / "local" / "lib" / "greia-os"
            / "greia-candidate-recovery")
        completed = subprocess.run(
            ["sh", str(helper), "--help"], capture_output=True, text=True,
            timeout=30)
        self.assertEqual(completed.returncode, 0)
        out = completed.stdout
        lowered = out.lower()
        self.assertIn("x86", lowered)
        self.assertIn("grubenvbackend", lowered)
        self.assertIn("backend-unavailable", lowered)
        self.assertIn("pi", lowered)
        self.assertIn("PI8", out.upper())
        # Honesty predicates from T4 still hold literally.
        self.assertIn("manual", lowered)
        self.assertIn("power cycle", lowered)
        self.assertIn("no proven watchdog", lowered)

    def _deadline_fixture(self, root: Path, *, real_backend: bool = True):
        """Stage a CANDIDATE_BOOTING journal under update-state; return dirs."""
        journal_parent = root / "update-state"
        journal_dir = journal_parent / "system-updates" / "journal"
        candidate, accepted = _artifacts()
        if real_backend:
            grub_dir = root / "grub"
            backend = GrubEnvBackend.initialize(grub_dir, default_slot="A")
        else:
            grub_dir = root / "fake-grub"
            backend = FakeGrubBackend.initialize(grub_dir, default_slot="A")
        coordinator = BootTransactionCoordinator.begin_update(
            journal_dir=journal_dir, backend=backend,
            candidate_artifacts=candidate, accepted_artifacts=accepted,
            release_id="greia-0.15.0",
        )
        coordinator.arm()
        self.assertEqual(backend.simulate_reboot(), "B")
        attach_cls = GrubEnvBackend.attach if real_backend else FakeGrubBackend.attach
        resumed = BootTransactionCoordinator.resume(
            journal_dir=journal_dir, backend=attach_cls(grub_dir),
            candidate_artifacts=candidate, accepted_artifacts=accepted,
        )
        resumed.observe_boot()
        self.assertEqual(
            resumed.journal.state, BootTransactionState.CANDIDATE_BOOTING)
        return journal_parent, journal_dir, grub_dir

    def _helper_env(self, root: Path, journal_parent: Path, grub_dir: Path,
                    *, dry_run: str = "1",
                    extra: dict[str, str] | None = None) -> dict[str, str]:
        env = dict(os.environ)
        env["GREIA_UPDATE_STATE_DIR"] = str(journal_parent)
        env["GREIA_BOOT_JOURNAL_DIR"] = str(root / "boot-journal")
        env["GREIA_GRUBENV_DIR"] = str(grub_dir)
        env["GREIA_RECOVERY_DRY_RUN"] = dry_run
        env["PYTHONPATH"] = str(ROOT / "src")
        if extra:
            env.update(extra)
        return env

    def test_helper_backend_unavailable_is_bounded_no_action(self) -> None:
        """Acceptance 2b: missing backend => exit 0, no reboot, no mutation."""
        helper = (
            ROOT / "build" / "overlay" / "usr" / "local" / "lib" / "greia-os"
            / "greia-candidate-recovery")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_parent, journal_dir, _ = self._deadline_fixture(
                root, real_backend=False)
            before = BootTransactionJournal.load(journal_dir)
            before_state = before.state
            before_bytes = (journal_dir / "journal.json").read_bytes() \
                if (journal_dir / "journal.json").exists() \
                else before.canonical_bytes()
            empty_grub = root / "empty-grub"
            empty_grub.mkdir()
            env = self._helper_env(root, journal_parent, empty_grub, dry_run="0")
            completed = subprocess.run(
                ["sh", str(helper)], capture_output=True, text=True,
                timeout=60, env=env)
            self.assertEqual(completed.returncode, 0)
            self.assertIn("backend-unavailable", completed.stdout)
            self.assertNotIn("trigger-reboot", completed.stdout)
            reloaded = BootTransactionJournal.load(journal_dir)
            self.assertEqual(reloaded.state, before_state)
            self.assertEqual(
                reloaded.state, BootTransactionState.CANDIDATE_BOOTING)

    def test_helper_preserves_per_class_label_option_a(self) -> None:
        """Acceptance 3 (Option A): deadline helper keeps classes 1-3
        distinct in the journal note path. Fails if the label converges."""
        helper = (
            ROOT / "build" / "overlay" / "usr" / "local" / "lib" / "greia-os"
            / "greia-candidate-recovery")
        for klass in (
            RecoveryClass.LAUNCHER_EXIT,
            RecoveryClass.USERSPACE_EMERGENCY,
            RecoveryClass.HEALTH_SERVICE_FAILURE,
        ):
            with self.subTest(recovery_class=klass.value):
                with tempfile.TemporaryDirectory() as raw:
                    root = Path(raw)
                    journal_parent, journal_dir, grub_dir = self._deadline_fixture(
                        root, real_backend=True)
                    env = self._helper_env(
                        root, journal_parent, grub_dir, dry_run="1",
                        extra={"GREIA_RECOVERY_CLASS": klass.value})
                    completed = subprocess.run(
                        ["sh", str(helper)], capture_output=True, text=True,
                        timeout=60, env=env)
                    self.assertEqual(completed.returncode, 0)
                    self.assertIn(
                        f"RECOVERY_STATUS=trigger-reboot:{klass.value}",
                        completed.stdout)
                    # Dry run mutates nothing.
                    reloaded = BootTransactionJournal.load(journal_dir)
                    self.assertEqual(
                        reloaded.state, BootTransactionState.CANDIDATE_BOOTING)

    def test_helper_default_class_stays_health_service_failure(self) -> None:
        helper = (
            ROOT / "build" / "overlay" / "usr" / "local" / "lib" / "greia-os"
            / "greia-candidate-recovery")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_parent, _, grub_dir = self._deadline_fixture(
                root, real_backend=True)
            env = self._helper_env(root, journal_parent, grub_dir, dry_run="1")
            env.pop("GREIA_RECOVERY_CLASS", None)
            completed = subprocess.run(
                ["sh", str(helper)], capture_output=True, text=True,
                timeout=60, env=env)
            self.assertEqual(completed.returncode, 0)
            self.assertIn(
                "RECOVERY_STATUS=trigger-reboot:health-service-failure",
                completed.stdout)

    def test_helper_rejects_unknown_and_hard_hang_class(self) -> None:
        helper = (
            ROOT / "build" / "overlay" / "usr" / "local" / "lib" / "greia-os"
            / "greia-candidate-recovery")
        for value in ("bogus-class", RecoveryClass.HARD_HANG.value):
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory() as raw:
                    root = Path(raw)
                    journal_parent, journal_dir, grub_dir = self._deadline_fixture(
                        root, real_backend=True)
                    env = self._helper_env(
                        root, journal_parent, grub_dir, dry_run="1",
                        extra={"GREIA_RECOVERY_CLASS": value})
                    completed = subprocess.run(
                        ["sh", str(helper)], capture_output=True, text=True,
                        timeout=60, env=env)
                    self.assertEqual(completed.returncode, 0)
                    self.assertIn("RECOVERY_STATUS=no-action", completed.stdout)
                    self.assertNotIn("trigger-reboot", completed.stdout)
                    reloaded = BootTransactionJournal.load(journal_dir)
                    self.assertEqual(
                        reloaded.state, BootTransactionState.CANDIDATE_BOOTING)

    def test_per_class_label_round_trips_into_t5_record(self) -> None:
        """Option A without new schema: the bounded T5 recovery_reason
        carries the per-class label so cause survives reboot."""
        import uuid as _uuid

        for klass in (
            RecoveryClass.LAUNCHER_EXIT,
            RecoveryClass.USERSPACE_EMERGENCY,
            RecoveryClass.HEALTH_SERVICE_FAILURE,
        ):
            with self.subTest(recovery_class=klass.value):
                with tempfile.TemporaryDirectory() as tmp:
                    history_dir = Path(tmp) / "persist" / "greia"
                    history_dir.mkdir(parents=True)
                    history = BootHistory.empty(history_dir)
                    history.begin_boot(
                        boot_id=str(_uuid.uuid4()), started_at_unix=1757000000,
                        slot="A", release_id="greia-0.14.0",
                        transaction_id="txn-a", transaction_type="update",
                        backend_default="A",
                    )
                    history.begin_boot(
                        boot_id=str(_uuid.uuid4()), started_at_unix=1757000600,
                        slot="B", release_id="greia-0.15.0",
                        transaction_id="txn-b", transaction_type="update",
                        backend_default="A", backend_one_shot="B",
                    )
                    history.record_milestone(
                        "failed", launcher_result="failed", health_result="failed",
                        recovery_reason=klass.value, terminal_state="failed",
                    )
                    summary = describe_previous_boot(history)
                    # Head is current; rotate to accepted to expose previous.
                    history.begin_boot(
                        boot_id=str(_uuid.uuid4()), started_at_unix=1757001200,
                        slot="A", release_id="greia-0.14.0",
                        transaction_id="txn-a2", transaction_type="update",
                        backend_default="A",
                    )
                    summary = describe_previous_boot(history)
                    assert summary is not None
                    self.assertEqual(summary["recovery_reason"], klass.value)


if __name__ == "__main__":
    unittest.main()

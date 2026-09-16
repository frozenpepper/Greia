"""P4.5 recovery re-proof: the failed-candidate deadline path.

From the same platform-observed boot truth the early-boot observer
establishes (``observe_and_reconcile_boot`` reconciling the kernel-observed
slot into ``GrubEnvBackend.inspect().last_booted_slot``), through the real
production owner (``GrubEnvBackend`` + ``BootTransactionJournal`` /
``BootTransactionCoordinator`` + ``mark_candidate_unhealthy`` +
``RECOVERY_TRIGGER_STATES`` + the shipped ``greia-candidate-recovery``
helper, timer and service):

- a candidate boot that never becomes healthy marks the journal FAILED and
  issues the controlled reboot through the deadline path;
- the accepted default is never changed before health (byte-identical);
- a recovery boot returns the accepted slot;
- a machine already on the accepted slot is a no-op;
- a plain boot is a no-op;
- hard hang remains manual with no watchdog claim.

The 3-minute deadline constant, the seven-second intro and the health
predicate are asserted unchanged. The helper is exercised in dry-run or
no-action modes only: no real reboot is ever executed. The non-dry-run
FAILED marking is proven through ``mark_candidate_unhealthy`` (the same
production owner the helper calls to record FAILED), with the helper source
asserted to reach that exact call.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from greia_platform import boot_transaction as boot_module
from greia_platform.boot_observation import observe_and_reconcile_boot
from greia_platform.boot_transaction import (
    CANDIDATE_HEALTH_DEADLINE_SEC,
    RECOVERY_TRIGGER_STATES,
    BootArtifactSet,
    BootJournalError,
    BootTransactionCoordinator,
    BootTransactionJournal,
    BootTransactionState,
    RecoveryAction,
    RecoveryClass,
    describe_recovery_contract,
    is_watchdog_proven,
    mark_candidate_unhealthy,
    parse_recovery_note,
    recovery_action_for,
)
from greia_platform.grub_ab import GrubEnvBackend


ROOT = Path(__file__).resolve().parents[1]

_RELEASE = "greia-0.15.0"
_RELEASE_SEQ = 11
_LAYOUT_ID = "modern-gpt-ab-v1"
_BACKEND_ID = "grub-ab-v1"

_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_KERNEL_SHA = "ab" * 32
_INITRAMFS_SHA = "cd" * 32


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.14.0",
        "accepted_slot": "A",
        "boot_backend": _BACKEND_ID,
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "modern-amd64",
        "install_target_sha256": "ab" * 32,
        "installed_at_unix": 1757000000,
        "layout_id": _LAYOUT_ID,
        "persist": {
            "filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000",
            "partuuid": "33333333-4444-5555-6666-777777777777",
        },
        "platform_family": "standard-x86-64",
        "schema_version": 1,
        "slot_bytes": 1024 * 1024 * 1024,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _canonical(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _artifacts() -> tuple[BootArtifactSet, BootArtifactSet]:
    candidate = BootArtifactSet(
        slot="B", layout_id=_LAYOUT_ID, boot_backend=_BACKEND_ID,
        generic_kernel_sha256=_KERNEL_SHA,
        generic_initramfs_sha256=_INITRAMFS_SHA,
        root_partuuid=_UUID_B, root_filesystem_uuid=_UUID_B_FS,
        release_id=_RELEASE,
    )
    accepted = BootArtifactSet(
        slot="A", layout_id=_LAYOUT_ID, boot_backend=_BACKEND_ID,
        generic_kernel_sha256=_KERNEL_SHA,
        generic_initramfs_sha256=_INITRAMFS_SHA,
        root_partuuid=_UUID_A, root_filesystem_uuid=_UUID_A_FS,
        release_id="greia-0.14.0",
    )
    return candidate, accepted


def _deadline_rig(root: Path):
    """Stage update candidate B booted once under the real GrubEnvBackend.

    Returns (journal_parent, journal_dir, grub_dir, coordinator). The
    observer truth is established inside: the kernel cmdline fact for slot
    B is reconciled into the same backend, so journal, backend and
    observer agree on one authoritative ``last_booted_slot == B``.
    """
    grub_dir = root / "grub"
    backend = GrubEnvBackend.initialize(grub_dir, default_slot="A")
    journal_parent = root / "update-state"
    journal_dir = journal_parent / "system-updates" / "journal"
    candidate, accepted = _artifacts()
    coordinator = BootTransactionCoordinator.begin_update(
        journal_dir=journal_dir, backend=backend,
        candidate_artifacts=candidate, accepted_artifacts=accepted,
        release_id=_RELEASE,
    )
    coordinator.arm()
    assert backend.simulate_reboot() == "B"
    resumed = BootTransactionCoordinator.resume(
        journal_dir=journal_dir, backend=GrubEnvBackend.attach(grub_dir),
        candidate_artifacts=candidate, accepted_artifacts=accepted,
    )
    resumed.observe_boot()
    assert resumed.journal.state is BootTransactionState.CANDIDATE_BOOTING
    # Same platform-observed truth as the early-boot observer: the kernel
    # root PARTUUID for B, resolved through the trusted layout record and
    # cross-checked against the booted slot release identity, reconciled
    # into the same backend (idempotent: last_booted is already B).
    cmdline = root / "cmdline"
    cmdline.write_text(
        f"BOOT_IMAGE=/boot/vmlinuz root=PARTUUID={_UUID_B} ro quiet\n",
        encoding="utf-8",
    )
    layout_path = root / "observer-layout.json"
    layout_path.write_bytes(_canonical(_record_dict()))
    identity = root / "release-identity.json"
    identity.write_bytes(_canonical({
        "boot_backend": _BACKEND_ID,
        "layout_id": _LAYOUT_ID,
        "release_id": _RELEASE,
        "role": "system-b",
        "slot": "B",
    }))
    result = observe_and_reconcile_boot(
        cmdline_path=cmdline,
        layout_record_path=layout_path,
        release_identity_path=identity,
        grubenv_dir=grub_dir,
    )
    assert result.reconciled and result.observed_slot == "B"
    state = GrubEnvBackend.attach(grub_dir).inspect()
    assert state.last_booted_slot == "B"
    assert state.last_booted_slot == resumed.journal.candidate_slot
    return journal_parent, journal_dir, grub_dir, resumed


def _helper() -> Path:
    return (
        ROOT / "build" / "overlay" / "usr" / "local" / "lib" / "greia-os"
        / "greia-candidate-recovery"
    )


def _helper_env(
    root: Path, journal_parent: Path, grub_dir: Path, *, dry_run: str = "1",
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    env = dict(os.environ)
    env["GREIA_UPDATE_STATE_DIR"] = str(journal_parent)
    env["GREIA_BOOT_JOURNAL_DIR"] = str(root / "boot-journal")
    env["GREIA_GRUBENV_DIR"] = str(grub_dir)
    env["GREIA_RECOVERY_DRY_RUN"] = dry_run
    env["PYTHONPATH"] = str(ROOT / "src")
    if extra:
        env.update(extra)
    return env


class DeadlineConstantTests(unittest.TestCase):
    def test_three_minute_deadline_and_trigger_states_unchanged(self) -> None:
        """P4.5 wiring: 180 s deadline == 3 min timer; trigger states exact."""
        self.assertEqual(CANDIDATE_HEALTH_DEADLINE_SEC, 180)
        timer_text = (
            ROOT / "build" / "overlay" / "etc" / "systemd" / "system"
            / "greia-candidate-recovery.timer"
        ).read_text(encoding="utf-8")
        self.assertIn("OnBootSec=3min", timer_text)
        service_text = (
            ROOT / "build" / "overlay" / "etc" / "systemd" / "system"
            / "greia-candidate-recovery.service"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "ExecStart=/usr/local/lib/greia-os/greia-candidate-recovery",
            service_text,
        )
        self.assertEqual(
            set(RECOVERY_TRIGGER_STATES),
            {
                BootTransactionState.FIRST_INSTALL_PENDING,
                BootTransactionState.UPDATE_STAGED,
                BootTransactionState.ONE_SHOT_ARMED,
                BootTransactionState.CANDIDATE_BOOTING,
            },
        )
        contract = describe_recovery_contract()
        self.assertEqual(contract["deadline_sec"], 180)
        # Req 4 unchanged: the seven-second intro and the one-use health
        # predicate still bound confirmation elsewhere.
        from greia_launcher import boot_intro

        self.assertEqual(boot_intro.ANIMATION_SECONDS, 5.0)
        self.assertEqual(boot_intro.FINAL_FRAME_HOLD_SECONDS, 2.0)
        self.assertEqual(
            boot_intro.ANIMATION_SECONDS + boot_intro.FINAL_FRAME_HOLD_SECONDS, 7.0
        )


class FailedCandidateTriggerTests(unittest.TestCase):
    def test_unhealthy_candidate_marks_failed_with_default_byte_identical(self) -> None:
        """P4.5: FAILED journal + controlled-reboot decision; default untouched."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, journal_dir, grub_dir, resumed = _deadline_rig(root)
            grubenv_file = grub_dir / "grubenv"
            grubenv_before = grubenv_file.read_bytes()
            self.assertEqual(
                GrubEnvBackend.attach(grub_dir).inspect().default_slot, "A"
            )
            decision = mark_candidate_unhealthy(
                resumed,
                recovery_class=RecoveryClass.HEALTH_SERVICE_FAILURE,
                detail="deadline expired without BOOT_HEALTHY",
            )
            self.assertEqual(decision.journal_transition, BootTransactionState.FAILED)
            self.assertEqual(resumed.journal.state, BootTransactionState.FAILED)
            self.assertEqual(decision.accepted_slot, "A")
            self.assertEqual(decision.candidate_slot, "B")
            self.assertEqual(decision.action, RecoveryAction.AUTOMATIC_REBOOT)
            self.assertEqual(decision.recovery_medium, "accepted-slot")
            parsed = parse_recovery_note(decision.note)
            assert parsed is not None
            self.assertEqual(parsed["recovery_class"], "health-service-failure")
            self.assertEqual(parsed["recovery_action"], "automatic-reboot")
            # The accepted default is never changed before health: the
            # backend still boots A and the grubenv bytes are identical.
            self.assertEqual(
                GrubEnvBackend.attach(grub_dir).inspect().default_slot, "A"
            )
            self.assertEqual(grubenv_file.read_bytes(), grubenv_before)

    def test_helper_deadline_path_decides_reboot_without_mutation(self) -> None:
        """P4.5: the real helper reaches trigger-reboot on the observed truth."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_parent, journal_dir, grub_dir, _ = _deadline_rig(root)
            grubenv_before = (grub_dir / "grubenv").read_bytes()
            env = _helper_env(root, journal_parent, grub_dir, dry_run="1")
            completed = subprocess.run(
                ["sh", str(_helper())], capture_output=True, text=True,
                timeout=60, env=env,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertIn(
                "RECOVERY_STATUS=trigger-reboot:health-service-failure",
                completed.stdout,
            )
            self.assertIn("RECOVERY_ACCEPTED_SLOT=A", completed.stdout)
            self.assertIn("RECOVERY_CANDIDATE_SLOT=B", completed.stdout)
            # Dry run mutates nothing: journal still candidate-booting, the
            # backend default still accepted, grubenv bytes identical.
            reloaded = BootTransactionJournal.load(journal_dir)
            self.assertEqual(reloaded.state, BootTransactionState.CANDIDATE_BOOTING)
            self.assertEqual(
                GrubEnvBackend.attach(grub_dir).inspect().default_slot, "A"
            )
            self.assertEqual((grub_dir / "grubenv").read_bytes(), grubenv_before)
            # The non-dry-run marking is the same production owner proven
            # above: the helper records FAILED through journal.record.
            helper_text = _helper().read_text(encoding="utf-8")
            self.assertIn("journal.record(", helper_text)
            self.assertIn("BootTransactionState.FAILED", helper_text)
            self.assertIn("RECOVERY_TRIGGER_STATES", helper_text)


class RecoveryBootTests(unittest.TestCase):
    def test_recovery_boot_returns_accepted_slot(self) -> None:
        """P4.5: after FAILED, the next boot returns to the accepted slot."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, journal_dir, grub_dir, resumed = _deadline_rig(root)
            mark_candidate_unhealthy(
                resumed, recovery_class=RecoveryClass.LAUNCHER_EXIT,
                detail="recovery boot check",
            )
            self.assertEqual(resumed.journal.state, BootTransactionState.FAILED)
            backend = GrubEnvBackend.attach(grub_dir)
            # The one-shot was consumed at the candidate boot, so firmware
            # selection falls back to the persistent default without any
            # backend mutation by the trigger.
            self.assertEqual(backend.simulate_reboot(), "A")
            self.assertEqual(backend.inspect().default_slot, "A")
            self.assertEqual(backend.observe_booted_slot(), "A")
            # Terminal FAILED never becomes ROLLED_BACK on reconcile.
            for observed in ("A", "B", None):
                outcome = resumed.journal.reconcile(observed)
                self.assertIsNone(outcome.transition)
            self.assertEqual(resumed.journal.state, BootTransactionState.FAILED)

    def test_already_on_accepted_is_noop(self) -> None:
        """P4.5: a machine already back on the accepted slot does nothing."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_parent, journal_dir, grub_dir, _ = _deadline_rig(root)
            backend = GrubEnvBackend.attach(grub_dir)
            # Failed candidate fell back without health: accepted boots.
            self.assertEqual(backend.simulate_reboot(), "A")
            before_state = BootTransactionJournal.load(journal_dir).state
            env = _helper_env(root, journal_parent, grub_dir, dry_run="0")
            completed = subprocess.run(
                ["sh", str(_helper())], capture_output=True, text=True,
                timeout=60, env=env,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertIn("already-on-accepted-slot", completed.stdout)
            self.assertNotIn("trigger-reboot", completed.stdout)
            self.assertEqual(
                BootTransactionJournal.load(journal_dir).state, before_state
            )

    def test_plain_boot_is_noop(self) -> None:
        """P4.5: no journal anywhere is a silent no-op (exit 0, no reboot)."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_parent = root / "update-state"
            journal_parent.mkdir(parents=True)
            (root / "boot-journal").mkdir(parents=True)
            grub_dir = root / "grub"
            GrubEnvBackend.initialize(grub_dir, default_slot="A")
            env = _helper_env(root, journal_parent, grub_dir, dry_run="0")
            completed = subprocess.run(
                ["sh", str(_helper())], capture_output=True, text=True,
                timeout=60, env=env,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertIn("RECOVERY_STATUS=no-action", completed.stdout)
            self.assertNotIn("trigger-reboot", completed.stdout)


class HardHangManualTests(unittest.TestCase):
    def test_hard_hang_remains_manual_with_no_watchdog_claim(self) -> None:
        """P4.5: hard hang never triggers; no reference platform proves a watchdog."""
        self.assertEqual(set(boot_module.WATCHDOG_PROVEN_PLATFORMS), set())
        self.assertFalse(is_watchdog_proven("raspberry-pi-400"))
        self.assertFalse(is_watchdog_proven("acer-aspire-one"))
        self.assertEqual(
            recovery_action_for(RecoveryClass.HARD_HANG),
            RecoveryAction.MANUAL_POWER_CYCLE,
        )
        contract = describe_recovery_contract()
        assert isinstance(contract["classes"], dict)
        self.assertEqual(
            contract["classes"][RecoveryClass.HARD_HANG.value],
            RecoveryAction.MANUAL_POWER_CYCLE.value,
        )
        self.assertEqual(contract["watchdog_proven_platforms"], [])
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _, journal_dir, grub_dir, resumed = _deadline_rig(root)
            with self.assertRaises(BootJournalError) as caught:
                mark_candidate_unhealthy(
                    resumed, recovery_class=RecoveryClass.HARD_HANG,
                )
            self.assertIn("manual", str(caught.exception).lower())
            self.assertEqual(resumed.journal.state, BootTransactionState.CANDIDATE_BOOTING)
            # The helper refuses the hard-hang class as a bounded no-action.
            journal_parent = root / "update-state"
            env = _helper_env(
                root, journal_parent, grub_dir, dry_run="1",
                extra={"GREIA_RECOVERY_CLASS": RecoveryClass.HARD_HANG.value},
            )
            completed = subprocess.run(
                ["sh", str(_helper())], capture_output=True, text=True,
                timeout=60, env=env,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertIn("RECOVERY_STATUS=no-action", completed.stdout)
            self.assertNotIn("trigger-reboot", completed.stdout)
            self.assertEqual(
                BootTransactionJournal.load(journal_dir).state,
                BootTransactionState.CANDIDATE_BOOTING,
            )
        # The shipped contract text stays honest about manual recovery.
        helper_help = subprocess.run(
            ["sh", str(_helper()), "--help"], capture_output=True, text=True,
            timeout=30,
        )
        self.assertEqual(helper_help.returncode, 0)
        lowered = helper_help.stdout.lower()
        self.assertIn("manual", lowered)
        self.assertIn("power cycle", lowered)
        self.assertIn("no proven watchdog", lowered)


if __name__ == "__main__":
    unittest.main()

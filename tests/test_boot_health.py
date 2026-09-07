"""L7-HEALTH source-scope tests: trusted one-use post-intro BOOT_HEALTHY.

R0/R1 only: files and fakes. No slot/boot writes, no bootloader changes, no
EEPROM contact. The L7-BOOT fake GRUB backend stands in for firmware; the
fake actual-identity observer stands in for the production root
PARTUUID/release reader. Every negative family from the brief is proven
against production code: Parent peer, same-UID Activity-like child, stale
boot attempt, stale transaction, wrong slot, wrong release, wrong root
PARTUUID, replayed credential, pre-intro confirmation, post-completion
confirmation, and untrusted Activity already launched.
"""

from __future__ import annotations

import hashlib
import inspect
import os
import tempfile
import unittest
from pathlib import Path

import greia_launcher.boot_health as launcher_health
import greia_platform.boot_health as health_module
from greia_launcher.boot_health import TRUSTED_BOOTSTRAP_PATH
from greia_launcher.bootstrap import BootLifecycleGuard
from greia_platform.boot_health import (
    ACCEPTED_SLOT_MEDIUM,
    ActualBootIdentity,
    BootHealthCredentialVault,
    BootHealthError,
    BootHealthyProtocol,
    FakeActualBootIdentity,
    HealthyCommittingTicket,
    IntroEvidence,
    SETUP_MEDIUM,
)
from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootTransactionCoordinator,
    BootTransactionState,
    FakeGrubBackend,
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
_KERNEL = hashlib.sha256(b"candidate-kernel-bytes").hexdigest()
_INITRAMFS = hashlib.sha256(b"candidate-initramfs-bytes").hexdigest()
_INVENTORY = "cd" * 32
_SUPPORT = "ef" * 32

_RELEASE = "greia-0.15.0"
_RELEASE_SEQ = 11
_ACCEPTED_RELEASE = "greia-0.14.0"
_ACCEPTED_SEQ = 7

_PARENT_PEER = "greia_parent.server:ParentPanel"
_ACTIVITY_PEER = "activity.runtime:ActivityRuntime"


def _record_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": _ACCEPTED_RELEASE,
        "accepted_release_sequence": _ACCEPTED_SEQ,
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
        release_id=_RELEASE,
        release_sequence=_RELEASE_SEQ,
        slot=slot,
        role=f"system-{slot.lower()}",
        base_sha256=_KERNEL,
        base_bytes=200 * 1024,
        support_sha256=_SUPPORT,
        support_size=1024,
        inventory_token=_INVENTORY,
        packages=(),
        packages_digest=hashlib.sha256(b"\n").hexdigest(),
        generic_kernel_sha256=_KERNEL,
        host_initramfs_sha256=_INITRAMFS,
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


def _candidate_identity() -> ActualBootIdentity:
    return ActualBootIdentity(
        booted_slot="B",
        root_partuuid=_UUID_B,
        release_id=_RELEASE,
        release_sequence=_RELEASE_SEQ,
    )


def _interactive_guard() -> BootLifecycleGuard:
    guard = BootLifecycleGuard()
    guard.mark_display_ready()
    guard.mark_first_frame_visible()
    guard.begin_preparing_runtime()
    guard.mark_interactive_ready()
    return guard


class _Harness:
    """One update transaction booted into CANDIDATE_BOOTING with a protocol."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
        candidate, accepted = _artifacts()
        self.candidate = candidate
        self.accepted = accepted
        self.coordinator = BootTransactionCoordinator.begin_update(
            journal_dir=root / "journal", backend=self.backend,
            candidate_artifacts=candidate, accepted_artifacts=accepted,
            release_id=_RELEASE, release_sequence=_RELEASE_SEQ,
        )
        self.coordinator.arm()
        self.backend.simulate_reboot()
        self.rebooted = FakeGrubBackend.attach(root / "grub")
        self.coordinator = BootTransactionCoordinator.resume(
            journal_dir=root / "journal", backend=self.rebooted,
            candidate_artifacts=candidate, accepted_artifacts=accepted,
        )
        observed, _ = self.coordinator.observe_boot()
        assert observed == "B"
        assert self.coordinator.journal.state is BootTransactionState.CANDIDATE_BOOTING
        self.vault = BootHealthCredentialVault(root / "vault")
        self.observer = FakeActualBootIdentity(_candidate_identity())
        self.protocol = BootHealthyProtocol(
            coordinator=self.coordinator,
            candidate_root_partuuid=_UUID_B,
            candidate_release_id=_RELEASE,
            candidate_release_sequence=_RELEASE_SEQ,
            vault=self.vault,
            observer=self.observer,
            trusted_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
        )
        self.guard = _interactive_guard()

    def provision(self, *, attempt: str = "attempt-1"):
        return self.protocol.provision_for_boot_attempt(
            boot_attempt=attempt, peer_uid=os.getuid()
        )

    def good_intro(self) -> IntroEvidence:
        return IntroEvidence(
            first_frame_visible=True,
            intro_completed=True,
            lifecycle_state="interactive_ready",
            untrusted_activity_launched=False,
        )

    def confirm_ok(self, *, attempt: str = "attempt-1"):
        record = self.provision(attempt=attempt)
        return self.protocol.confirm(
            token=record.token,
            boot_attempt=attempt,
            peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            peer_uid=os.getuid(),
            intro=self.good_intro(),
        )


class BootHealthySuccessTests(unittest.TestCase):
    def test_update_end_to_end_through_trusted_seam(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            record = launcher_health.provision_post_intro_credential(
                harness.protocol, guard=harness.guard, boot_attempt="attempt-1"
            )
            self.assertTrue(harness.vault.credential_live())
            # Untrusted launch is barred before acceptance; built-in is not.
            with self.assertRaises(BootHealthError):
                harness.protocol.check_untrusted_launch("developer_unsigned")
            harness.protocol.check_untrusted_launch("built_in")
            ticket = launcher_health.confirm_post_intro_healthy(
                harness.protocol,
                guard=harness.guard,
                token=record.token,
                boot_attempt="attempt-1",
                first_frame_visible=True,
                intro_completed=True,
                untrusted_activity_launched=False,
            )
            self.assertIsInstance(ticket, HealthyCommittingTicket)
            # Credential is invalidated before the gate opens.
            self.assertFalse(harness.vault.credential_live())
            with self.assertRaises(BootHealthError):
                harness.protocol.check_untrusted_launch("parent_trusted_unsigned")
            outcome = harness.protocol.finalize(ticket)
            self.assertEqual(outcome.accepted_slot, "B")
            self.assertEqual(outcome.release_id, _RELEASE)
            self.assertFalse(outcome.first_install)
            self.assertEqual(outcome.recovery_medium_if_failed, ACCEPTED_SLOT_MEDIUM)
            self.assertEqual(
                harness.coordinator.journal.state, BootTransactionState.ACCEPTED
            )
            harness.protocol.check_untrusted_launch("developer_unsigned")

    def test_first_install_uses_setup_medium_never_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            record_layout = InstalledLayoutRecord.from_dict(_record_dict())
            artifact_a = BootArtifactSet.from_finalization(
                receipt=_receipt("A"), record=record_layout
            )
            coordinator = BootTransactionCoordinator.begin_first_install(
                journal_dir=root / "journal", backend=backend, artifact_a=artifact_a
            )
            self.assertEqual(backend.simulate_reboot(), "A")
            observed, _ = coordinator.observe_boot()
            self.assertEqual(observed, "A")
            vault = BootHealthCredentialVault(root / "vault")
            observer = FakeActualBootIdentity(
                ActualBootIdentity(
                    booted_slot="A",
                    root_partuuid=_UUID_A,
                    release_id=_RELEASE,
                    release_sequence=_RELEASE_SEQ,
                )
            )
            protocol = BootHealthyProtocol(
                coordinator=coordinator,
                candidate_root_partuuid=_UUID_A,
                candidate_release_id=_RELEASE,
                candidate_release_sequence=_RELEASE_SEQ,
                vault=vault,
                observer=observer,
                trusted_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            credential = protocol.provision_for_boot_attempt(
                boot_attempt="attempt-1", peer_uid=os.getuid()
            )
            ticket = protocol.confirm(
                token=credential.token,
                boot_attempt="attempt-1",
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=os.getuid(),
                intro=IntroEvidence(
                    first_frame_visible=True,
                    intro_completed=True,
                    lifecycle_state="interactive_ready",
                    untrusted_activity_launched=False,
                ),
            )
            self.assertTrue(ticket.first_install)
            outcome = protocol.finalize(ticket)
            self.assertEqual(outcome.accepted_slot, "A")
            self.assertTrue(outcome.first_install)
            self.assertEqual(outcome.recovery_medium_if_failed, SETUP_MEDIUM)
            self.assertNotIn("rollback", outcome.recovery_medium_if_failed)
            self.assertNotIn("rollback", str(outcome.as_dict()))


class BootHealthyNegativeTests(unittest.TestCase):
    def test_parent_peer_fails_and_credential_survives(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            record = harness.provision()
            with self.assertRaises(BootHealthError):
                harness.protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=_PARENT_PEER,
                    peer_uid=0,
                    intro=harness.good_intro(),
                )
            # Failed attempt consumed nothing: the real launcher can still use it.
            self.assertTrue(harness.vault.credential_live())
            ticket = harness.protocol.confirm(
                token=record.token,
                boot_attempt="attempt-1",
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=os.getuid(),
                intro=harness.good_intro(),
            )
            harness.protocol.finalize(ticket)

    def test_same_uid_activity_like_child_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            record = harness.provision()
            # Same OS identity as the child launcher, but an Activity peer path.
            with self.assertRaises(BootHealthError):
                harness.protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=_ACTIVITY_PEER,
                    peer_uid=os.getuid(),
                    intro=harness.good_intro(),
                )

    def test_stale_boot_attempt_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            record = harness.provision(attempt="attempt-1")
            with self.assertRaises(BootHealthError):
                harness.protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-2",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=os.getuid(),
                    intro=harness.good_intro(),
                )

    def test_stale_transaction_credential_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            harness = _Harness(root)
            record = harness.provision()
            # A second transaction shares the vault dir but has its own id.
            backend2 = FakeGrubBackend.initialize(root / "grub2", default_slot="A")
            candidate, accepted = _artifacts()
            coordinator2 = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal2", backend=backend2,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id=_RELEASE, release_sequence=_RELEASE_SEQ,
            )
            self.assertNotEqual(
                coordinator2.journal.transaction_id,
                harness.coordinator.journal.transaction_id,
            )
            protocol2 = BootHealthyProtocol(
                coordinator=coordinator2,
                candidate_root_partuuid=_UUID_B,
                candidate_release_id=_RELEASE,
                candidate_release_sequence=_RELEASE_SEQ,
                vault=harness.vault,
                observer=harness.observer,
                trusted_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            with self.assertRaises(BootHealthError):
                protocol2.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=os.getuid(),
                    intro=harness.good_intro(),
                )

    def test_wrong_slot_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            record = harness.provision()
            harness.observer._identity = ActualBootIdentity(
                booted_slot="A",
                root_partuuid=_UUID_A,
                release_id=_RELEASE,
                release_sequence=_RELEASE_SEQ,
            )
            with self.assertRaises(BootHealthError):
                harness.protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=os.getuid(),
                    intro=harness.good_intro(),
                )

    def test_wrong_release_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            record = harness.provision()
            harness.observer._identity = ActualBootIdentity(
                booted_slot="B",
                root_partuuid=_UUID_B,
                release_id=_ACCEPTED_RELEASE,
                release_sequence=_ACCEPTED_SEQ,
            )
            with self.assertRaises(BootHealthError):
                harness.protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=os.getuid(),
                    intro=harness.good_intro(),
                )

    def test_wrong_root_partuuid_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            record = harness.provision()
            harness.observer._identity = ActualBootIdentity(
                booted_slot="B",
                root_partuuid=_UUID_A,
                release_id=_RELEASE,
                release_sequence=_RELEASE_SEQ,
            )
            with self.assertRaises(BootHealthError):
                harness.protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=os.getuid(),
                    intro=harness.good_intro(),
                )

    def test_replayed_credential_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            record = harness.provision()
            ticket = harness.protocol.confirm(
                token=record.token,
                boot_attempt="attempt-1",
                peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                peer_uid=os.getuid(),
                intro=harness.good_intro(),
            )
            with self.assertRaises(BootHealthError):
                harness.protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=os.getuid(),
                    intro=harness.good_intro(),
                )
            harness.protocol.finalize(ticket)

    def test_pre_intro_confirmation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            # Seam refuses before INTERACTIVE_READY without touching the vault.
            early = BootLifecycleGuard()
            early.mark_display_ready()
            early.mark_first_frame_visible()
            early.begin_preparing_runtime()
            record = harness.provision()
            with self.assertRaises(BootHealthError):
                launcher_health.confirm_post_intro_healthy(
                    harness.protocol,
                    guard=early,
                    token=record.token,
                    boot_attempt="attempt-1",
                    first_frame_visible=True,
                    intro_completed=False,
                    untrusted_activity_launched=False,
                )
            self.assertTrue(harness.vault.credential_live())

    def test_first_frame_alone_is_never_enough(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            record = harness.provision()
            # Phase-6 READY=1 without the completed 7-second intro.
            ready_only = IntroEvidence(
                first_frame_visible=True,
                intro_completed=False,
                lifecycle_state="first_frame_visible",
                untrusted_activity_launched=False,
            )
            self.assertFalse(ready_only.is_post_intro_interactive)
            with self.assertRaises(BootHealthError):
                harness.protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=os.getuid(),
                    intro=ready_only,
                )

    def test_post_completion_confirmation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            ticket = harness.confirm_ok()
            harness.protocol.finalize(ticket)
            self.assertEqual(
                harness.coordinator.journal.state, BootTransactionState.ACCEPTED
            )
            with self.assertRaises(BootHealthError):
                harness.protocol.provision_for_boot_attempt(
                    boot_attempt="attempt-2", peer_uid=os.getuid()
                )
            with self.assertRaises(BootHealthError):
                harness.protocol.finalize(ticket)

    def test_untrusted_activity_already_launched_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            record = harness.provision()
            with self.assertRaises(BootHealthError):
                harness.protocol.confirm(
                    token=record.token,
                    boot_attempt="attempt-1",
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=os.getuid(),
                    intro=IntroEvidence(
                        first_frame_visible=True,
                        intro_completed=True,
                        lifecycle_state="interactive_ready",
                        untrusted_activity_launched=True,
                    ),
                )

    def test_finalize_refuses_identity_moved_under_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            ticket = harness.confirm_ok()
            harness.observer._identity = ActualBootIdentity(
                booted_slot="A",
                root_partuuid=_UUID_A,
                release_id=_RELEASE,
                release_sequence=_RELEASE_SEQ,
            )
            with self.assertRaises(BootHealthError):
                harness.protocol.finalize(ticket)

    def test_provision_before_candidate_boot_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            backend = FakeGrubBackend.initialize(root / "grub", default_slot="A")
            candidate, accepted = _artifacts()
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=root / "journal", backend=backend,
                candidate_artifacts=candidate, accepted_artifacts=accepted,
                release_id=_RELEASE, release_sequence=_RELEASE_SEQ,
            )
            protocol = BootHealthyProtocol(
                coordinator=coordinator,
                candidate_root_partuuid=_UUID_B,
                candidate_release_id=_RELEASE,
                candidate_release_sequence=_RELEASE_SEQ,
                vault=BootHealthCredentialVault(root / "vault"),
                observer=FakeActualBootIdentity(_candidate_identity()),
                trusted_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
            )
            with self.assertRaises(BootHealthError):
                protocol.provision_for_boot_attempt(
                    boot_attempt="attempt-1", peer_uid=os.getuid()
                )

    def test_double_provision_same_attempt_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            harness = _Harness(Path(raw))
            harness.provision()
            with self.assertRaises(BootHealthError):
                harness.provision()


class BootHealthyBoundaryTests(unittest.TestCase):
    def test_intro_timing_is_unchanged(self) -> None:
        from greia_launcher import boot_intro

        self.assertEqual(boot_intro.ANIMATION_SECONDS, 5.0)
        self.assertEqual(boot_intro.FINAL_FRAME_HOLD_SECONDS, 2.0)
        self.assertEqual(
            boot_intro.ANIMATION_SECONDS + boot_intro.FINAL_FRAME_HOLD_SECONDS, 7.0
        )

    def test_trusted_path_is_single_sourced(self) -> None:
        self.assertEqual(
            TRUSTED_BOOTSTRAP_PATH, "greia_launcher.bootstrap:LauncherBootstrap"
        )
        self.assertEqual(
            launcher_health.trusted_bootstrap_path(), TRUSTED_BOOTSTRAP_PATH
        )

    def test_module_has_no_privileged_or_manager_surface(self) -> None:
        for module in (health_module, launcher_health):
            source = inspect.getsource(module)
            for marker in (
                "import subprocess",
                "os.system",
                "shell=",
                "/dev/",
                "class .*Manager",
                "class .*Daemon",
                "class .*Parser",
            ):
                self.assertIsNone(
                    __import__("re").search(marker, source),
                    f"forbidden surface {marker!r} in {module.__name__}",
                )

    def test_health_module_writes_no_boot_state(self) -> None:
        source = inspect.getsource(health_module)
        for marker in ("parted", "mkfs", "mount(", "grub-install", "EEPROM", "eeprom"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()

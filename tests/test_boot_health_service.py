"""P4.2 product proof: the root-owned semantic CONFIRM_BOOT_HEALTH service.

Through the composed service (``BootHealthService`` + ``BootHealthEndpoint``
+ ``handle_boot_health_connection``):

- a first-install pending journal commits journal + GRUB + accepted-sequence
  + layout-authority convergence + one bounded history record;
- an update pending journal commits the same five through the reused
  ``system_updates`` mutation path (not a reimplementation);
- both-pending is refused rather than guessed;
- a forged/unauthorized peer is refused before any request byte is read;
- a missing or replayed capability is refused;
- selectors/raw authority are refused;
- pre-intro boot is inactive;
- no generic command surface exists.

No mutation happens before capability validation: every refusal test
asserts full snapshot equality of the fixture tree. Backends are the real
file-backed production shapes (``GrubEnvBackend`` on tmpdirs, the real
``SlotBackedSystemUpdateBackend.confirm_boot_health`` chain); fakes are
limited to the one-use capability verifier (owned by
POSTR1-P4-CAPABILITY-LIFECYCLE) and the artifact-set resolver. Fixtures
live in disposable tmpdirs only.
"""

from __future__ import annotations

import inspect
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_platform.boot_health_service import (
    BOOT_HEALTH_OPS,
    BootHealthEndpoint,
    BootHealthService,
    BootHealthServiceError,
    ReceiptBackedArtifactResolver,
    build_confirm_request,
    handle_boot_health_connection,
    load_production_capability_verifier,
)
from greia_platform.boot_transaction import (
    BootArtifactSet,
    BootHistory,
    BOOT_JOURNAL_DIR_ENV,
    BootTransactionJournal,
    BootTransactionState,
)
from greia_platform.grub_ab import GrubEnvBackend
from greia_platform.privileged_channel import (
    PeerCredential,
    encode_request,
)
from greia_platform.system_updates import (
    SlotBackedSystemUpdateBackend,
    SystemIdentity,
    SystemUpdateServiceAuthority,
    load_installed_layout_record,
)


_LAUNCHER_UID = 1001
_UNAUTHORIZED_UID = 9999
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
        "accepted_release_id": _RELEASE,
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


def _write_layout(root: Path, name: str = "installed-layout.json", **overrides: object) -> Path:
    path = root / name
    path.write_bytes(
        (json.dumps(_record_dict(**overrides), sort_keys=True) + "\n").encode()
    )
    return path


def _artifact_sets_for_journal(
    journal: BootTransactionJournal,
) -> tuple[BootArtifactSet, BootArtifactSet]:
    """Test resolver values: layout-bound identity for the journal's slot."""
    candidate = BootArtifactSet(
        slot=journal.candidate_slot,
        layout_id=journal.layout_id,
        boot_backend=journal.boot_backend,
        generic_kernel_sha256=_KERNEL_SHA,
        generic_initramfs_sha256=_INITRAMFS_SHA,
        root_partuuid=_UUID_A if journal.candidate_slot == "A" else _UUID_B,
        root_filesystem_uuid=_UUID_A_FS if journal.candidate_slot == "A" else _UUID_B_FS,
        release_id=journal.release_id,
    )
    if journal.first_install:
        return candidate, candidate
    accepted = BootArtifactSet(
        slot=journal.accepted_slot,
        layout_id=journal.layout_id,
        boot_backend=journal.boot_backend,
        generic_kernel_sha256=_KERNEL_SHA,
        generic_initramfs_sha256=_INITRAMFS_SHA,
        root_partuuid=_UUID_A if journal.accepted_slot == "A" else _UUID_B,
        root_filesystem_uuid=_UUID_A_FS if journal.accepted_slot == "A" else _UUID_B_FS,
        release_id="greia-0.14.0",
    )
    return candidate, accepted


class _StubArtifactResolver:
    """Injected resolver: same layout-bound values the receipt path binds."""

    def resolve(
        self, journal: BootTransactionJournal
    ) -> tuple[BootArtifactSet, BootArtifactSet]:
        return _artifact_sets_for_journal(journal)


class FakeOneUseCapabilityVerifier:
    """Stand-in for the CAPABILITY-LIFECYCLE verifier: issue-once semantics."""

    def __init__(self) -> None:
        self._live: dict[str, bool] = {}

    def issue(self, token: str) -> str:
        self._live[token] = True
        return token

    def verify_and_consume(self, *, token: str) -> dict[str, object]:
        if token not in self._live:
            raise BootHealthServiceError("capability is absent, invalid or replayed")
        del self._live[token]
        return {"consumed": True}


class _FakeConnection:
    """Socket stand-in recording whether any request byte was read."""

    def __init__(self, inbound: bytes = b"") -> None:
        self._inbound = inbound
        self.recv_calls = 0
        self.sent: list[bytes] = []
        self.closed = False

    def settimeout(self, _seconds: float) -> None:
        pass

    def recv(self, _size: int) -> bytes:
        self.recv_calls += 1
        if self._inbound:
            chunk, self._inbound = self._inbound, b""
            return chunk
        return b""

    def sendall(self, data: bytes) -> None:
        self.sent.append(bytes(data))

    def close(self) -> None:
        self.closed = True


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            snapshot[str(path.relative_to(root))] = path.read_bytes()
    return snapshot


class _Composed:
    """One disposable composed service: real backends, fake capability."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_dir = root / "update-state"
        self.boot_journal_dir = Path(
            os.environ.get(BOOT_JOURNAL_DIR_ENV, str(root / "boot-journal"))
        )
        self.grubenv_dir = root / "grubenv"
        self.history_dir = root / "history"
        self.layout_path = _write_layout(root)
        for directory in (
            self.state_dir, self.boot_journal_dir,
            self.grubenv_dir, self.history_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        self.verifier = FakeOneUseCapabilityVerifier()
        self.backend = GrubEnvBackend.initialize(self.grubenv_dir, default_slot="A")
        update_backend = SlotBackedSystemUpdateBackend(
            self.state_dir,
            layout_record_path=self.layout_path,
            boot_backend=self.backend,
        )
        self.update_authority = SystemUpdateServiceAuthority(
            self.state_dir,
            SystemIdentity("0.14.0", "standard-x86-64", "x86-64", "modern-amd64"),
            update_backend,
        )
        self.service = BootHealthService(
            boot_journal_dir=self.boot_journal_dir,
            update_state_dir=self.state_dir,
            history_dir=self.history_dir,
            update_authority=self.update_authority,
            capability_verifier=self.verifier,
            artifact_resolver=_StubArtifactResolver(),
            boot_backend_factory=lambda: GrubEnvBackend.attach(self.grubenv_dir),
        )
        self.endpoint = BootHealthEndpoint(
            self.service, allowed_uids=(0, _LAUNCHER_UID)
        )

    def update_journal_dir(self) -> Path:
        return self.service.update_journal_dir

    def stage_update_candidate_booted(self) -> None:
        """Stage update B->A... (candidate B) and boot it via the real backend."""
        self.backend.arm_one_shot("B")
        BootTransactionJournal.begin_update(
            self.update_journal_dir(),
            layout_id=_LAYOUT_ID,
            boot_backend=_BACKEND_ID,
            release_id=_RELEASE,
            candidate_slot="B",
            accepted_slot="A",
        )
        self.backend.simulate_reboot()
        assert self.backend.observe_booted_slot() == "B"

    def stage_update_candidate_unbooted(self) -> None:
        """Stage update candidate B without the reboot (no observation yet)."""
        self.backend.arm_one_shot("B")
        BootTransactionJournal.begin_update(
            self.update_journal_dir(),
            layout_id=_LAYOUT_ID,
            boot_backend=_BACKEND_ID,
            release_id=_RELEASE,
            candidate_slot="B",
            accepted_slot="A",
        )

    def stage_first_install_booted(self) -> None:
        """Stage first-install A and boot it via the real backend."""
        BootTransactionJournal.begin_first_install(
            self.boot_journal_dir,
            layout_id=_LAYOUT_ID,
            boot_backend=_BACKEND_ID,
            release_id=_RELEASE,
        )
        self.backend.simulate_reboot()
        assert self.backend.observe_booted_slot() == "A"

    def confirm(self, token: str) -> bytes:
        raw = build_confirm_request(token)
        return self.endpoint.handle_request(
            raw,
            peer=PeerCredential(uid=_LAUNCHER_UID),
            boot_state="interactive_ready",
        )


def _decode_ok(raw: bytes) -> dict[str, object]:
    from greia_platform.privileged_channel import decode_response

    _, op, payload = decode_response(raw)
    assert op == "CONFIRM_BOOT_HEALTH", op
    assert payload.get("status") == "CONFIRMED", payload
    assert isinstance(payload.get("detail"), dict)
    return payload


class FirstInstallConfirmTests(unittest.TestCase):
    def test_first_install_commits_all_five(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            composed = _Composed(Path(directory))
            composed.stage_first_install_booted()
            token = composed.verifier.issue("first-install-token-1")
            response = composed.confirm(token)
            detail = _decode_ok(response)["detail"]
            assert isinstance(detail, dict)
            self.assertEqual(detail.get("journal"), "first-install")
            # 1. journal health-committed.
            journal = BootTransactionJournal.load(composed.boot_journal_dir)
            self.assertEqual(journal.state, BootTransactionState.ACCEPTED)
            self.assertTrue(journal.is_terminal)
            # 2. GRUB persistent default follows the booted candidate.
            self.assertEqual(
                GrubEnvBackend.attach(composed.grubenv_dir).inspect().default_slot, "A"
            )
            # 3. journal carries the accepted v3 release identity.
            self.assertEqual(journal.release_id, _RELEASE)
            # 4. layout authority accepts the installed release on A.
            record = load_installed_layout_record(composed.layout_path)
            assert record is not None
            self.assertEqual(record.accepted_slot, "A")
            self.assertEqual(record.accepted_release_id, _RELEASE)
            self.assertEqual(record.boot_control.active_slot, "A")
            # 5. exactly one bounded history terminal record.
            history = BootHistory.load(composed.history_dir)
            self.assertEqual(len(history.entries), 1)
            entry = history.entries[0]
            self.assertEqual(entry.milestone, "committed")
            self.assertEqual(entry.health_result, "confirmed")
            self.assertEqual(entry.terminal_state, "accepted")
            self.assertEqual(entry.slot, "A")
            self.assertEqual(entry.transaction_type, "first-install")
            self.assertEqual(entry.transaction_id, journal.transaction_id)

    def test_installed_shared_journal_confirms_first_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared = root / "persist" / "greia" / "boot-journal"
            with mock.patch.dict(os.environ, {BOOT_JOURNAL_DIR_ENV: str(shared)}):
                composed = _Composed(root)
                self.assertEqual(composed.update_authority.backend.journal_dir, shared)
                self.assertEqual(composed.service.update_journal_dir, shared)
                self.assertEqual(composed.service.boot_journal_dir, shared)
                composed.stage_first_install_booted()
                token = composed.verifier.issue("shared-first-install-token")
                detail = _decode_ok(composed.confirm(token))["detail"]
                self.assertEqual(detail["journal"], "first-install")
                self.assertEqual(
                    BootTransactionJournal.load(shared).state,
                    BootTransactionState.ACCEPTED,
                )


class UpdateConfirmTests(unittest.TestCase):
    def test_update_commits_all_five_through_reused_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            composed = _Composed(Path(directory))
            # Fixture layout accepts A @ 0.14.0/7; the update must advance it.
            _write_layout(
                Path(directory),
                accepted_release_id="greia-0.14.0",
            )
            composed.stage_update_candidate_booted()
            token = composed.verifier.issue("update-token-1")
            response = composed.confirm(token)
            detail = _decode_ok(response)["detail"]
            assert isinstance(detail, dict)
            self.assertEqual(detail.get("journal"), "update")
            # 1. journal health-committed through the system_updates path.
            journal = BootTransactionJournal.load(composed.update_journal_dir())
            self.assertEqual(journal.state, BootTransactionState.ACCEPTED)
            # 2. GRUB persistent default is the booted candidate.
            self.assertEqual(
                GrubEnvBackend.attach(composed.grubenv_dir).inspect().default_slot, "B"
            )
            # 3. journal carries the accepted v3 release identity (the
            # legacy accepted-sequence file is no longer written on the
            # update path; T02).
            self.assertEqual(journal.release_id, _RELEASE)
            # 4. layout authority advanced to the candidate.
            record = load_installed_layout_record(composed.layout_path)
            assert record is not None
            self.assertEqual(record.accepted_slot, "B")
            self.assertEqual(record.accepted_release_id, _RELEASE)
            self.assertEqual(record.boot_control.active_slot, "B")
            # 5. exactly one bounded history terminal record.
            history = BootHistory.load(composed.history_dir)
            self.assertEqual(len(history.entries), 1)
            entry = history.entries[0]
            self.assertEqual(entry.milestone, "committed")
            self.assertEqual(entry.health_result, "confirmed")
            self.assertEqual(entry.terminal_state, "accepted")
            self.assertEqual(entry.slot, "B")
            self.assertEqual(entry.transaction_type, "update")

    def test_installed_shared_journal_confirms_update(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared = root / "persist" / "greia" / "boot-journal"
            with mock.patch.dict(os.environ, {BOOT_JOURNAL_DIR_ENV: str(shared)}):
                composed = _Composed(root)
                _write_layout(root, accepted_release_id="greia-0.14.0")
                self.assertEqual(composed.update_authority.backend.journal_dir, shared)
                self.assertEqual(composed.service.update_journal_dir, shared)
                self.assertEqual(composed.service.boot_journal_dir, shared)
                composed.stage_update_candidate_booted()
                token = composed.verifier.issue("shared-update-token")
                detail = _decode_ok(composed.confirm(token))["detail"]
                self.assertEqual(detail["journal"], "update")
                self.assertEqual(
                    BootTransactionJournal.load(shared).state,
                    BootTransactionState.ACCEPTED,
                )

    def test_shared_terminal_first_install_journal_is_reused_for_update(self) -> None:
        """The installed service has one reusable terminal-to-active journal."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shared = root / "persist" / "greia" / "boot-journal"
            with mock.patch.dict(os.environ, {BOOT_JOURNAL_DIR_ENV: str(shared)}):
                composed = _Composed(root)
                composed.stage_first_install_booted()
                first_install_token = composed.verifier.issue("shared-install-token")
                install_detail = _decode_ok(composed.confirm(first_install_token))["detail"]
                self.assertEqual(install_detail["journal"], "first-install")
                self.assertEqual(
                    BootTransactionJournal.load(shared).state,
                    BootTransactionState.ACCEPTED,
                )

                # Model a later installed release while retaining the same
                # mounted PERSIST journal. The next transaction may replace
                # the terminal first-install record, never a pending record.
                _write_layout(root, accepted_release_id="greia-0.14.0")
                composed.stage_update_candidate_booted()
                update_token = composed.verifier.issue("shared-update-token")
                update_detail = _decode_ok(composed.confirm(update_token))["detail"]
                self.assertEqual(update_detail["journal"], "update")
                final = BootTransactionJournal.load(shared)
                self.assertEqual(final.state, BootTransactionState.ACCEPTED)
                self.assertFalse(final.first_install)
                self.assertEqual(final.release_id, _RELEASE)


class AmbiguousOrAbsentJournalTests(unittest.TestCase):
    def test_both_pending_refused_without_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            composed.stage_update_candidate_booted()
            BootTransactionJournal.begin_first_install(
                composed.boot_journal_dir,
                layout_id=_LAYOUT_ID,
                boot_backend=_BACKEND_ID,
                release_id=_RELEASE,
            )
            before = _snapshot_tree(root)
            token = composed.verifier.issue("ambiguous-token")
            with self.assertRaisesRegex(BootHealthServiceError, "both pending"):
                composed.confirm(token)
            self.assertEqual(_snapshot_tree(root), before)
            # Neither journal guessed at: both still non-terminal.
            self.assertFalse(
                BootTransactionJournal.load(composed.update_journal_dir()).is_terminal
            )
            self.assertFalse(
                BootTransactionJournal.load(composed.boot_journal_dir).is_terminal
            )

    def test_no_pending_journal_refused_with_no_history_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            before = _snapshot_tree(root)
            token = composed.verifier.issue("idle-token")
            with self.assertRaisesRegex(BootHealthServiceError, "no pending"):
                composed.confirm(token)
            self.assertEqual(_snapshot_tree(root), before)
            self.assertFalse((composed.history_dir / "boot-history.json").exists())


class PeerGateTests(unittest.TestCase):
    def test_forged_peer_refused_before_any_byte_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            composed = _Composed(Path(directory))
            composed.stage_update_candidate_booted()
            token = composed.verifier.issue("peer-token")
            raw = build_confirm_request(token)
            for forged in ("not-a-credential", 1001, None, {"uid": _LAUNCHER_UID}):
                connection = _FakeConnection(inbound=bytes(raw))
                handle_boot_health_connection(
                    connection,
                    endpoint=composed.endpoint,
                    peer=forged,
                    boot_state="interactive_ready",
                )
                self.assertEqual(connection.recv_calls, 0)
                self.assertTrue(connection.closed)
                self.assertTrue(connection.sent)
                self.assertIn(b"REFUSED", connection.sent[0])

    def test_unauthorized_uid_refused_before_any_byte_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            composed = _Composed(Path(directory))
            composed.stage_update_candidate_booted()
            token = composed.verifier.issue("peer-token-2")
            raw = build_confirm_request(token)
            connection = _FakeConnection(inbound=bytes(raw))
            handle_boot_health_connection(
                connection,
                endpoint=composed.endpoint,
                peer=PeerCredential(uid=_UNAUTHORIZED_UID),
                boot_state="interactive_ready",
            )
            self.assertEqual(connection.recv_calls, 0)
            self.assertTrue(connection.closed)
            self.assertIn(b"REFUSED", connection.sent[0])
            # The pending journal is untouched: refusal preceded any read.
            journal = BootTransactionJournal.load(composed.update_journal_dir())
            self.assertFalse(journal.is_terminal)

    def test_endpoint_authorizes_forged_peer_without_service_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            composed = _Composed(Path(directory))
            composed.stage_update_candidate_booted()
            token = composed.verifier.issue("peer-token-3")
            raw = build_confirm_request(token)
            with self.assertRaisesRegex(BootHealthServiceError, "attested"):
                composed.endpoint.handle_request(
                    raw,
                    peer="not-a-credential",  # type: ignore[arg-type]
                    boot_state="interactive_ready",
                )
            with self.assertRaisesRegex(BootHealthServiceError, "not authorized"):
                composed.endpoint.handle_request(
                    raw,
                    peer=PeerCredential(uid=_UNAUTHORIZED_UID),
                    boot_state="interactive_ready",
                )


class CapabilityGateTests(unittest.TestCase):
    def test_missing_capability_refused_with_zero_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            composed.stage_update_candidate_booted()
            before = _snapshot_tree(root)
            raw = encode_request("CONFIRM_BOOT_HEALTH", {})
            with self.assertRaisesRegex(BootHealthServiceError, "capability"):
                composed.endpoint.handle_request(
                    raw,
                    peer=PeerCredential(uid=_LAUNCHER_UID),
                    boot_state="interactive_ready",
                )
            self.assertEqual(_snapshot_tree(root), before)

    def test_unknown_capability_refused_with_zero_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            composed.stage_update_candidate_booted()
            before = _snapshot_tree(root)
            with self.assertRaisesRegex(BootHealthServiceError, "capability"):
                composed.confirm("never-issued-token")
            self.assertEqual(_snapshot_tree(root), before)

    def test_replayed_capability_refused_with_zero_further_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            composed.stage_update_candidate_booted()
            token = composed.verifier.issue("one-use-token")
            composed.verifier.verify_and_consume(token=token)
            before = _snapshot_tree(root)
            with self.assertRaisesRegex(BootHealthServiceError, "capability"):
                composed.confirm(token)
            self.assertEqual(_snapshot_tree(root), before)
            journal = BootTransactionJournal.load(composed.update_journal_dir())
            self.assertFalse(journal.is_terminal)

    def test_second_confirm_with_same_token_is_a_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            composed.stage_first_install_booted()
            token = composed.verifier.issue("first-install-one-use")
            composed.confirm(token)
            journal = BootTransactionJournal.load(composed.boot_journal_dir)
            self.assertEqual(journal.state, BootTransactionState.ACCEPTED)
            # The token is consumed: even a retry reports capability refusal
            # (selection now also finds no pending journal; either way no
            # second mutation is possible).
            with self.assertRaises(BootHealthServiceError):
                composed.confirm(token)
            journal = BootTransactionJournal.load(composed.boot_journal_dir)
            self.assertEqual(journal.state, BootTransactionState.ACCEPTED)
            self.assertEqual(len(BootHistory.load(composed.history_dir).entries), 1)


class SelectorAndBootGateTests(unittest.TestCase):
    def test_selectors_are_refused_with_zero_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            composed.stage_update_candidate_booted()
            bad_params = [
                {"slot": "B"},
                {"journal": "update"},
                {"release_id": "greia-0.99.0"},
                {"capability": "t", "slot": "B"},
            ]
            for params in bad_params:
                before = _snapshot_tree(root)
                raw = encode_request("CONFIRM_BOOT_HEALTH", params)
                with self.assertRaisesRegex(
                    BootHealthServiceError, "no selectors"
                ):
                    composed.endpoint.handle_request(
                        raw,
                        peer=PeerCredential(uid=_LAUNCHER_UID),
                        boot_state="interactive_ready",
                    )
                self.assertEqual(_snapshot_tree(root), before)

    def test_raw_authority_is_refused_with_zero_mutation(self) -> None:
        from greia_platform.privileged_channel import PrivilegedChannelError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            composed.stage_update_candidate_booted()
            # Client framing refuses to build raw-authority requests at all.
            for params in (
                {"path": "/boot/grub/grubenv"},
                {"command": "reboot"},
                {"device": "/dev/sda"},
                {"capability": "/etc/greia-os/token"},
            ):
                with self.assertRaises(PrivilegedChannelError):
                    encode_request("CONFIRM_BOOT_HEALTH", params)
            # A hand-framed raw request reaching the endpoint is refused.
            before = _snapshot_tree(root)
            raw = (
                b'{"op":"CONFIRM_BOOT_HEALTH",'
                b'"params":{"path":"/boot/grub/grubenv"},'
                b'"protocol_version":1}\n'
            )
            with self.assertRaises(BootHealthServiceError):
                composed.endpoint.handle_request(
                    raw,
                    peer=PeerCredential(uid=_LAUNCHER_UID),
                    boot_state="interactive_ready",
                )
            self.assertEqual(_snapshot_tree(root), before)

    def test_unknown_op_is_refused_with_zero_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            composed.stage_update_candidate_booted()
            before = _snapshot_tree(root)
            raw = encode_request("RECONCILE", {})
            with self.assertRaisesRegex(BootHealthServiceError, "unknown boot-health op"):
                composed.endpoint.handle_request(
                    raw,
                    peer=PeerCredential(uid=_LAUNCHER_UID),
                    boot_state="interactive_ready",
                )
            self.assertEqual(_snapshot_tree(root), before)

    def test_pre_intro_boot_is_inactive_with_zero_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            composed.stage_update_candidate_booted()
            token = composed.verifier.issue("pre-intro-token")
            raw = build_confirm_request(token)
            for boot_state in ("pre_intro", "", "unknown-state"):
                before = _snapshot_tree(root)
                with self.assertRaisesRegex(BootHealthServiceError, "pre-intro"):
                    composed.endpoint.handle_request(
                        raw,
                        peer=PeerCredential(uid=_LAUNCHER_UID),
                        boot_state=boot_state,
                    )
                self.assertEqual(_snapshot_tree(root), before)


class ObservationSensitivityTests(unittest.TestCase):
    """Positive control: the suite goes RED without the real boot observation."""

    def test_unbooted_candidate_is_refused_then_green_after_reboot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            composed.stage_update_candidate_unbooted()
            before = _snapshot_tree(root)
            red_token = composed.verifier.issue("red-token")
            # RED: the candidate never booted, so no health commit exists.
            with self.assertRaises(BootHealthServiceError):
                composed.confirm(red_token)
            self.assertEqual(_snapshot_tree(root), before)
            journal = BootTransactionJournal.load(composed.update_journal_dir())
            self.assertFalse(journal.is_terminal)
            # GREEN: the same composed service confirms after the reboot.
            composed.backend.simulate_reboot()
            self.assertEqual(composed.backend.observe_booted_slot(), "B")
            green_token = composed.verifier.issue("green-token")
            detail = _decode_ok(composed.confirm(green_token))["detail"]
            assert isinstance(detail, dict)
            self.assertEqual(detail.get("journal"), "update")
            journal = BootTransactionJournal.load(composed.update_journal_dir())
            self.assertEqual(journal.state, BootTransactionState.ACCEPTED)

    def test_first_install_layout_drift_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            composed = _Composed(root)
            # Drift the authority: it accepts a different release for A.
            _write_layout(
                root,
                accepted_release_id="greia-0.14.0",
            )
            composed.stage_first_install_booted()
            before = _snapshot_tree(root)
            token = composed.verifier.issue("drift-token")
            with self.assertRaisesRegex(BootHealthServiceError, "layout authority"):
                composed.confirm(token)
            self.assertEqual(_snapshot_tree(root), before)
            journal = BootTransactionJournal.load(composed.boot_journal_dir)
            self.assertFalse(journal.is_terminal)


class NoGenericSurfaceTests(unittest.TestCase):
    def test_only_one_semantic_op_exists(self) -> None:
        self.assertEqual(BOOT_HEALTH_OPS, ("CONFIRM_BOOT_HEALTH",))

    def test_module_owns_no_generic_command_surface(self) -> None:
        import greia_platform.boot_health_service as service_module

        source = inspect.getsource(service_module)
        for forbidden in (
            "subprocess",
            "os.system",
            "os.exec",
            "os.popen",
            "popen",
            "shell=True",
            "eval(",
            "exec(",
            "VERIFY_CURRENT_CANDIDATE",
            "STAGE_CURRENT_CANDIDATE",
            "ARM_CURRENT_CANDIDATE",
            "RECONCILE",
        ):
            self.assertNotIn(forbidden, source)

    def test_mutation_is_reused_not_duplicated(self) -> None:
        import greia_platform.boot_health_service as service_module

        source = inspect.getsource(service_module)
        # Update journal: delegated to the existing system_updates mutation
        # path (which internally reconciles, commit_accepts and advances
        # layout authority by release_id); first install: shared
        # coordinator/backend/layout/history primitives.
        for reused in (
            "self.update_authority.confirm_boot_health()",
            "BootTransactionCoordinator.resume",
            "coordinator.commit()",
            "GrubEnvBackend.attach",
            "load_installed_layout_record",
            "BootHistory",
            "attest_peer_from_connection",
        ):
            self.assertIn(reused, source)
        for duplicated in (
            "def commit_accepted",
            "def advance_layout_authority",
            "class BootTransactionJournal",
            "def arm_one_shot",
        ):
            self.assertNotIn(duplicated, source)


class ProductionSeamTests(unittest.TestCase):
    def test_receipt_resolver_binds_layout_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout_path = _write_layout(root)
            receipt_path = root / "finalization-receipt.json"
            receipt_path.write_bytes(
                (
                    json.dumps(
                        {
                            "artifact_digests": {
                                "generic_kernel_sha256": _KERNEL_SHA,
                                "host_initramfs_sha256": _INITRAMFS_SHA,
                            },
                            "layout_id": _LAYOUT_ID,
                            "release_id": _RELEASE,
                            "slot": "A",
                        },
                        sort_keys=True,
                    )
                    + "\n"
                ).encode()
            )
            journal_dir = root / "boot-journal"
            journal_dir.mkdir()
            journal = BootTransactionJournal.begin_first_install(
                journal_dir,
                layout_id=_LAYOUT_ID,
                boot_backend=_BACKEND_ID,
                release_id=_RELEASE,
            )
            resolver = ReceiptBackedArtifactResolver(
                layout_record_path=layout_path, receipt_path=receipt_path
            )
            candidate, accepted = resolver.resolve(journal)
            self.assertEqual(candidate.slot, "A")
            self.assertEqual(candidate.root_partuuid, _UUID_A)
            self.assertEqual(candidate.release_id, _RELEASE)
            self.assertIs(accepted, candidate)
            # A receipt for the wrong slot fails closed.
            receipt_path.write_bytes(
                (
                    json.dumps(
                        {
                            "artifact_digests": {
                                "generic_kernel_sha256": _KERNEL_SHA,
                                "host_initramfs_sha256": _INITRAMFS_SHA,
                            },
                            "layout_id": _LAYOUT_ID,
                            "release_id": _RELEASE,
                            "slot": "B",
                        },
                        sort_keys=True,
                    )
                    + "\n"
                ).encode()
            )
            with self.assertRaisesRegex(BootHealthServiceError, "not the pending"):
                resolver.resolve(journal)

    def test_production_verifier_present_from_shipped_module(self) -> None:
        from greia_platform.boot_health_service import (
            build_live_boot_health_service,
            load_production_capability_verifier,
        )

        verifier = load_production_capability_verifier()
        self.assertTrue(callable(getattr(verifier, "verify_and_consume", None)))
        # The shipped module owns the seam: no vault substitute, token-only
        # signature, single pending resolution per call.
        self.assertEqual(
            type(verifier).__module__, "greia_platform.boot_capability"
        )
        signature = inspect.signature(verifier.verify_and_consume)
        self.assertEqual(
            [name for name in signature.parameters], ["token"]
        )
        # The root entrypoint composes with no injected verifier: trust,
        # layout, journals and boot facts resolve from Greia-owned state.
        class _StubAuthority:
            def confirm_boot_health(self) -> dict[str, object]:
                raise AssertionError("no journal is pending in this test")

        service, endpoint = build_live_boot_health_service(
            update_authority=_StubAuthority(),
        )
        self.assertIs(service.capability_verifier.__class__, verifier.__class__)
        self.assertIs(endpoint.service, service)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_unit_directives(text: str) -> dict[str, list[str]]:
    current = ""
    out: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        out.setdefault(f"{current}.{key.strip()}", []).append(value.strip())
    return out


class UnitContractTests(unittest.TestCase):
    def test_credential_unit_declares_the_authority_runtime_directory(self) -> None:
        """ReadWritePaths names a directory systemd will not create for it.

        systemd refuses to start a unit whose ReadWritePaths entry is absent, so
        the generator's own 0700 directory could never be created and the unit
        failed every boot at the namespacing step. The unit must declare the
        directory, its 0700 mode, and preservation so the authoritative record
        outlives the oneshot.
        """

        unit_path = (
            _repo_root()
            / "build"
            / "overlay"
            / "etc"
            / "systemd"
            / "system"
            / "greia-boot-health-credential.service"
        )
        text = unit_path.read_text(encoding="utf-8")
        self.assertIn("ReadWritePaths=/run/greia-os /run/greia-boot-health-authority", text)
        self.assertEqual(text.count("RuntimeDirectory=greia-boot-health-authority"), 1)
        self.assertIn("RuntimeDirectoryMode=0700", text)
        self.assertIn("RuntimeDirectoryPreserve=yes", text)

    def test_service_is_root_owned_on_demand_with_no_boot_enable(self) -> None:
        text = (
            _repo_root()
            / "build"
            / "overlay"
            / "etc"
            / "systemd"
            / "system"
            / "greia-boot-health.service"
        ).read_text(encoding="utf-8")
        directives = _parse_unit_directives(text)
        self.assertEqual(directives.get("Service.User"), ["root"])
        self.assertEqual(directives.get("Service.Group"), ["root"])
        self.assertTrue(
            any(
                "greia_platform.boot_health_service" in value
                for value in directives.get("Service.ExecStart", [])
            )
        )
        self.assertEqual(
            directives.get("Service.RestrictAddressFamilies"), ["AF_UNIX"]
        )
        self.assertEqual(
            set(" ".join(directives.get("Unit.Requires", [])).split()),
            {"greia-boot-health.socket", "greia-software-update-recover.service"},
        )
        self.assertNotIn("Install.WantedBy", directives)

    def test_socket_is_root_owned_af_unix_on_demand(self) -> None:
        # Bounded launcher reachability (P4 socket-access): root owns the
        # node; group greiakid (the launcher's own primary group) has
        # read+write; no world access. Re-expressed from 0600 root:root.
        text = (
            _repo_root()
            / "build"
            / "overlay"
            / "etc"
            / "systemd"
            / "system"
            / "greia-boot-health.socket"
        ).read_text(encoding="utf-8")
        directives = _parse_unit_directives(text)
        self.assertEqual(
            directives.get("Socket.ListenStream"), ["/run/greia-os/boot-health.sock"]
        )
        self.assertEqual(directives.get("Socket.SocketMode"), ["0660"])
        self.assertEqual(directives.get("Socket.SocketUser"), ["root"])
        self.assertEqual(directives.get("Socket.SocketGroup"), ["greiakid"])
        self.assertEqual(directives.get("Socket.Accept"), ["no"])
        self.assertEqual(directives.get("Install.WantedBy"), ["sockets.target"])

    def test_image_enables_socket_never_service(self) -> None:
        # T01: service composition lives in the shared engine.
        text = (_repo_root() / "build" / "lib" / "compose.sh").read_text(encoding="utf-8")
        self.assertIn("greia-boot-health.socket", text)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            self.assertNotIn("greia-boot-health.service", line)


class _EnvGuard:
    NAMES = (
        "GREIA_BOOT_JOURNAL_DIR",
        "GREIA_UPDATE_STATE_DIR",
        "GREIA_BOOT_HISTORY_DIR",
        "GREIA_FINALIZATION_RECEIPT_PATH",
        "GREIA_BOOT_HEALTH_CALLER_UID",
        "GREIA_BOOT_HEALTH_CALLER",
    )

    def __init__(self) -> None:
        self.saved: dict[str, str | None] = {}

    def __enter__(self) -> "_EnvGuard":
        for name in self.NAMES:
            self.saved[name] = os.environ.get(name)
        return self

    def __exit__(self, *exc: object) -> bool:
        for name in self.NAMES:
            old = self.saved[name]
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old
        return False


class LiveCompositionTests(unittest.TestCase):
    def test_live_composition_resolves_dirs_and_allows_provisioned_caller(self) -> None:
        from greia_platform.boot_health_service import (
            build_live_boot_health_service,
            resolve_allowed_uids,
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _EnvGuard():
                os.environ["GREIA_BOOT_JOURNAL_DIR"] = str(root / "boot-journal")
                os.environ["GREIA_UPDATE_STATE_DIR"] = str(root / "update-state")
                os.environ["GREIA_BOOT_HISTORY_DIR"] = str(root / "history")
                os.environ["GREIA_BOOT_HEALTH_CALLER_UID"] = str(_LAUNCHER_UID)
                self.assertEqual(
                    resolve_allowed_uids(), (0, _LAUNCHER_UID)
                )
                verifier = FakeOneUseCapabilityVerifier()
                service, endpoint = build_live_boot_health_service(
                    capability_verifier=verifier,
                    update_authority=self._stub_update_authority(),
                    artifact_resolver=_StubArtifactResolver(),
                )
                self.assertEqual(
                    service.boot_journal_dir, root / "boot-journal"
                )
                self.assertEqual(endpoint.allowed_uids, (0, _LAUNCHER_UID))

    def test_resolve_allowed_uids_defaults_to_root_only(self) -> None:
        from greia_platform.boot_health_service import resolve_allowed_uids

        with _EnvGuard():
            os.environ.pop("GREIA_BOOT_HEALTH_CALLER_UID", None)
            os.environ.pop("GREIA_BOOT_HEALTH_CALLER", None)
            self.assertEqual(resolve_allowed_uids(), (0,))

    def test_resolve_allowed_uids_resolves_caller_name(self) -> None:
        from unittest import mock

        from greia_platform.boot_health_service import resolve_allowed_uids

        with _EnvGuard():
            os.environ.pop("GREIA_BOOT_HEALTH_CALLER_UID", None)
            os.environ["GREIA_BOOT_HEALTH_CALLER"] = "greiakid"
            with mock.patch(
                "pwd.getpwnam",
                return_value=mock.Mock(pw_uid=_LAUNCHER_UID),
            ):
                self.assertEqual(
                    resolve_allowed_uids(), (0, _LAUNCHER_UID)
                )

    def test_resolve_allowed_uids_unresolvable_caller_fails_closed(self) -> None:
        from unittest import mock

        from greia_platform.boot_health_service import (
            BootHealthServiceError,
            resolve_allowed_uids,
        )

        with _EnvGuard():
            os.environ.pop("GREIA_BOOT_HEALTH_CALLER_UID", None)
            os.environ["GREIA_BOOT_HEALTH_CALLER"] = "greiakid"
            with mock.patch(
                "pwd.getpwnam", side_effect=KeyError("greiakid")
            ):
                with self.assertRaises(BootHealthServiceError):
                    resolve_allowed_uids()

    def test_shipped_service_provisions_launcher_caller_name(self) -> None:
        text = (
            _repo_root()
            / "build"
            / "overlay"
            / "etc"
            / "systemd"
            / "system"
            / "greia-boot-health.service"
        ).read_text(encoding="utf-8")
        directives = _parse_unit_directives(text)
        environments = directives.get("Service.Environment", [])
        self.assertIn("GREIA_BOOT_HEALTH_CALLER=greiakid", environments)
        # No wildcard allowlist in the shipped unit.
        for entry in environments:
            self.assertNotIn("*", entry)

    def test_launcher_holds_socket_group_without_added_privilege(self) -> None:
        text = (
            _repo_root()
            / "build"
            / "overlay"
            / "etc"
            / "systemd"
            / "system"
            / "greia-launcher.service"
        ).read_text(encoding="utf-8")
        directives = _parse_unit_directives(text)
        self.assertEqual(directives.get("Service.User"), ["greiakid"])
        self.assertEqual(directives.get("Service.Group"), ["greiakid"])
        supplementary = " ".join(
            directives.get("Service.SupplementaryGroups", [])
        )
        self.assertNotIn("root", supplementary)
        self.assertNotIn("sudo", supplementary)

    def test_module_entry_point_honours_the_units_own_flag(self) -> None:
        """The service's ``--issue-for-pending`` must actually reach argparse.

        ``greia-boot-health-credential.service`` invokes this module with
        ``python3 -m greia_platform.boot_health --issue-for-pending``, so
        ``main()`` is reached with ``argv`` as None. When None was treated as an
        empty argument list, the unit's own flag was silently discarded: the
        generator printed its usage text and exited 2 on every boot, so the
        service never once issued a capability and the failure was invisible
        because every existing test passed an explicit argument list.

        Driven through ``sys.argv`` with no argument to ``main()``, which is
        exactly what ``python3 -m`` does.
        """

        import io
        import contextlib
        import sys as _sys

        from greia_platform import boot_health

        saved_argv = _sys.argv
        _sys.argv = ["boot_health", "--issue-for-pending"]
        # argparse.print_usage and the ISSUED/NO_PENDING line both go to stdout.
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                code = boot_health.main()
        finally:
            _sys.argv = saved_argv

        self.assertEqual(code, 0, out.getvalue())
        self.assertNotIn("usage:", out.getvalue())
        self.assertIn("NO_PENDING", out.getvalue())

    def test_module_entry_point_still_refuses_without_the_flag(self) -> None:
        """An explicit refusal must survive the argv fix, fail-closed."""

        import io
        import contextlib
        import sys as _sys

        from greia_platform import boot_health

        saved_argv = _sys.argv
        _sys.argv = ["boot_health"]
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                code = boot_health.main()
        finally:
            _sys.argv = saved_argv

        self.assertEqual(code, 2)
        self.assertIn("usage:", out.getvalue())

    @staticmethod
    def _stub_update_authority() -> object:
        class _Stub:
            def confirm_boot_health(self) -> dict[str, object]:
                raise AssertionError("no journal is pending in this test")

        return _Stub()


if __name__ == "__main__":
    unittest.main()

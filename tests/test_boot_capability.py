"""P4.6 focused proof: the shipped production capability verifier.

``greia_platform.boot_capability.build_production_verifier`` (behind
``load_production_capability_verifier``) adapts the token-only root
service seam to the binding-ful root authority:

- the single pending transaction, the current boot attempt and the
  trusted launcher path resolve from Greia-owned state, never request
  bytes; the presented token is the only request-derived input;
- the authority's ``verify_and_consume`` is called exactly once per
  presentation; absent/ambiguous/unknown/replayed capabilities fail
  closed with zero mutation;
- no launcher-writable vault substitute exists in the module.

Disposable tmpdirs only; the kernel boot ID and peer identity are
fixture-driven through explicit constructor bindings (the same values
the production defaults resolve from Greia-owned state on device).
"""

from __future__ import annotations

import inspect
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher.boot_health import TRUSTED_BOOTSTRAP_PATH
from greia_platform.boot_capability import build_production_verifier
from greia_platform.boot_health import (
    BootHealthError,
    default_capability_authority,
    maybe_issue_boot_capability,
)
from greia_platform.boot_transaction import BootTransactionJournal


_BOOT_ID_1 = "aaaaaaaa-1111-2222-3333-444444444444"
_BOOT_ID_2 = "bbbbbbbb-5555-6666-7777-888888888888"

_RELEASE = "greia-0.15.0"
_RELEASE_SEQ = 11
_LAYOUT_ID = "modern-gpt-ab-v1"
_BACKEND_ID = "grub-ab-v1"

_PEER_UID = 1001


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            snapshot[str(path.relative_to(root))] = path.read_bytes()
    return snapshot


def _stage_pending_update(root: Path) -> tuple[Path, Path]:
    """Stage a non-terminal update journal; return (journal_dir, state_dir)."""
    journal_dir = root / "update-state" / "system-updates" / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    (root / "boot-journal").mkdir(parents=True, exist_ok=True)
    BootTransactionJournal.begin_update(
        journal_dir,
        layout_id=_LAYOUT_ID,
        boot_backend=_BACKEND_ID,
        release_id=_RELEASE,
        release_sequence=_RELEASE_SEQ,
        candidate_slot="B",
        accepted_slot="A",
    )
    return journal_dir, root / "update-state"


def _stage_pending_first_install(root: Path) -> tuple[Path, Path]:
    journal_dir = root / "boot-journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    (root / "update-state").mkdir(parents=True, exist_ok=True)
    BootTransactionJournal.begin_first_install(
        journal_dir,
        layout_id=_LAYOUT_ID,
        boot_backend=_BACKEND_ID,
        release_id=_RELEASE,
        release_sequence=_RELEASE_SEQ,
    )
    return journal_dir, root / "update-state"


def _issue(root: Path, journal_dir: Path, state_dir: Path, *, boot_id: str = _BOOT_ID_1):
    owner = default_capability_authority(
        authority_dir=root / "authority",
        delivery_dir=root / "delivery",
    )
    issued = maybe_issue_boot_capability(
        authority=owner,
        boot_journal_dir=root / "boot-journal",
        update_state_dir=state_dir,
        boot_id=boot_id,
        peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
        peer_uid=_PEER_UID,
    )
    assert issued is not None
    return issued, owner


def _verifier(root: Path, owner, state_dir: Path, **overrides):
    params: dict[str, object] = {
        "authority": owner,
        "boot_journal_dir": root / "boot-journal",
        "update_state_dir": state_dir,
        "boot_id": _BOOT_ID_1,
        "peer_bootstrap_path": TRUSTED_BOOTSTRAP_PATH,
    }
    params.update(overrides)
    return build_production_verifier(**params)  # type: ignore[arg-type]


class ProductionVerifierConsumeTests(unittest.TestCase):
    def test_unknown_then_issued_then_replay(self) -> None:
        """RED (live) → GREEN (consumed once) → RED (replay)."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir, state_dir = _stage_pending_update(root)
            issued, owner = _issue(root, journal_dir, state_dir)
            journal = BootTransactionJournal.load(journal_dir)
            verifier = _verifier(root, owner, state_dir)
            before = _snapshot_tree(root)
            # Unknown token: refused, zero mutation, capability still live.
            with self.assertRaises(BootHealthError):
                verifier.verify_and_consume(token="f" * 64)
            self.assertTrue(owner.capability_live())
            self.assertEqual(_snapshot_tree(root), before)
            # Issued token: exactly one authority call, consumed.
            with mock.patch.object(
                owner, "verify_and_consume", wraps=owner.verify_and_consume
            ) as wrapped:
                record = verifier.verify_and_consume(token=issued.token)
            self.assertEqual(wrapped.call_count, 1)
            _, kwargs = wrapped.call_args
            self.assertEqual(
                sorted(kwargs),
                ["boot_attempt", "peer_bootstrap_path", "token", "transaction_id"],
            )
            self.assertEqual(kwargs["transaction_id"], journal.transaction_id)
            self.assertEqual(kwargs["boot_attempt"], _BOOT_ID_1)
            self.assertEqual(kwargs["peer_bootstrap_path"], TRUSTED_BOOTSTRAP_PATH)
            self.assertEqual(record["transaction_id"], journal.transaction_id)
            self.assertFalse(owner.capability_live())
            # Replay: the consumed capability never verifies twice.
            with self.assertRaises(BootHealthError):
                verifier.verify_and_consume(token=issued.token)

    def test_first_install_pending_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir, state_dir = _stage_pending_first_install(root)
            issued, owner = _issue(root, journal_dir, state_dir)
            verifier = _verifier(root, owner, state_dir)
            record = verifier.verify_and_consume(token=issued.token)
            journal = BootTransactionJournal.load(journal_dir)
            self.assertEqual(record["transaction_id"], journal.transaction_id)
            self.assertFalse(owner.capability_live())

    def test_absent_pending_fails_closed_with_no_writes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "update-state").mkdir(parents=True)
            (root / "boot-journal").mkdir(parents=True)
            owner = default_capability_authority(
                authority_dir=root / "authority",
                delivery_dir=root / "delivery",
            )
            verifier = _verifier(root, owner, root / "update-state")
            before = _snapshot_tree(root)
            with self.assertRaisesRegex(BootHealthError, "no pending"):
                verifier.verify_and_consume(token="e" * 64)
            self.assertEqual(_snapshot_tree(root), before)

    def test_ambiguous_pending_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _stage_pending_update(root)
            _stage_pending_first_install(root)
            owner = default_capability_authority(
                authority_dir=root / "authority",
                delivery_dir=root / "delivery",
            )
            verifier = _verifier(root, owner, root / "update-state")
            with self.assertRaisesRegex(BootHealthError, "mbiguous"):
                verifier.verify_and_consume(token="e" * 64)
            self.assertFalse(owner.capability_live())

    def test_stale_boot_id_fails_closed_and_keeps_capability_live(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir, state_dir = _stage_pending_update(root)
            issued, owner = _issue(root, journal_dir, state_dir, boot_id=_BOOT_ID_1)
            stale = _verifier(root, owner, state_dir, boot_id=_BOOT_ID_2)
            before = _snapshot_tree(root)
            with self.assertRaises(BootHealthError):
                stale.verify_and_consume(token=issued.token)
            self.assertTrue(owner.capability_live())
            self.assertEqual(_snapshot_tree(root), before)
            # The live boot attempt still verifies afterwards.
            fresh = _verifier(root, owner, state_dir)
            fresh.verify_and_consume(token=issued.token)
            self.assertFalse(owner.capability_live())

    def test_wrong_presenter_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir, state_dir = _stage_pending_update(root)
            issued, owner = _issue(root, journal_dir, state_dir)
            impostor = _verifier(
                root, owner, state_dir,
                peer_bootstrap_path="greia_parent.panel:ParentPanel",
            )
            with self.assertRaises(BootHealthError):
                impostor.verify_and_consume(token=issued.token)
            self.assertTrue(owner.capability_live())


class ProductionVerifierShapeTests(unittest.TestCase):
    def test_token_only_signature(self) -> None:
        verifier = build_production_verifier()
        self.assertEqual(
            [name for name in inspect.signature(verifier.verify_and_consume).parameters],
            ["token"],
        )

    def test_no_vault_substitute_in_module(self) -> None:
        import greia_platform.boot_capability as module

        source = inspect.getsource(module)
        for forbidden in (
            "default_vault",
            "provision_for_boot_attempt",
            "atomic_write",
            "O_WRONLY",
            "O_RDWR",
            "os.replace",
            "CAPABILITY_AUTHORITY",
        ):
            self.assertNotIn(forbidden, source)
        # Exactly one authority consume call site: one use per presentation.
        self.assertEqual(source.count("authority.verify_and_consume"), 1)
        # Bindings resolve from Greia-owned state, never request bytes.
        self.assertIn("load_pending_boot_journal", source)
        self.assertIn("read_boot_id", source)
        self.assertIn("capability_peer_bootstrap_path", source)

    def test_env_resolved_authority_binds(self) -> None:
        """Default authority/env binds reach the same one-use lifecycle."""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            journal_dir, state_dir = _stage_pending_update(root)
            saved = {
                name: os.environ.get(name)
                for name in (
                    "GREIA_BOOT_HEALTH_AUTHORITY_DIR",
                    "GREIA_BOOT_HEALTH_DELIVERY_DIR",
                )
            }
            try:
                os.environ["GREIA_BOOT_HEALTH_AUTHORITY_DIR"] = str(root / "authority")
                os.environ["GREIA_BOOT_HEALTH_DELIVERY_DIR"] = str(root / "delivery")
                owner = default_capability_authority()
                issued = maybe_issue_boot_capability(
                    authority=owner,
                    boot_journal_dir=root / "boot-journal",
                    update_state_dir=state_dir,
                    boot_id=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                    peer_uid=_PEER_UID,
                )
                assert issued is not None
                verifier = build_production_verifier(
                    boot_journal_dir=root / "boot-journal",
                    update_state_dir=state_dir,
                    boot_id=_BOOT_ID_1,
                    peer_bootstrap_path=TRUSTED_BOOTSTRAP_PATH,
                )
                verifier.verify_and_consume(token=issued.token)
                self.assertFalse(owner.capability_live())
            finally:
                for name, old in saved.items():
                    if old is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = old


if __name__ == "__main__":
    unittest.main()

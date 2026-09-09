"""T5-EVID: bounded reboot-surviving boot/lifecycle record.

Preregistered predicates (frozen before observation):
  P1: after a failed candidate and reboot, the accepted system reports the
      attempted slot/release, last durable milestone and recovery reason
      using only the PERSIST record (no /run, no previous journal).
  P2: total stored bytes never exceed 64 KiB; over-budget writes fail closed
      and rotate within budget, never growing unboundedly.
  P3: journald stays volatile in both installed overlays.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from greia_platform import boot_transaction as boot_module
from greia_platform.boot_transaction import (
    BOOT_HISTORY_FILE_MODE,
    BOOT_HISTORY_FILE_NAME,
    BOOT_HISTORY_RUNTIME_PATH,
    MAX_BOOT_HISTORY_BYTES,
    MAX_BOOT_HISTORY_ENTRIES,
    BootHistory,
    BootTransactionError,
    describe_previous_boot,
)
from greia_platform import persistent_layout as persist_module
from greia_platform.persistent_layout import (
    Durability,
    MountKind,
    find_audit_entry,
    persist_boot_history_path,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _boot_kwargs(*, slot: str, release: str, seq: int, txn: str,
                 txn_type: str, default: str, one_shot: str | None = None,
                 boot_id: str | None = None, started: int = 1757000000):
    return {
        "boot_id": boot_id or str(uuid.uuid4()),
        "started_at_unix": started,
        "slot": slot,
        "release_id": release,
        "release_sequence": seq,
        "transaction_id": txn,
        "transaction_type": txn_type,
        "backend_default": default,
        "backend_one_shot": one_shot,
    }


class JournaldVolatileTests(unittest.TestCase):
    def test_both_overlays_keep_journald_volatile(self) -> None:
        # P3: T5 must not make the whole journal persistent to debug boot.
        for relative in (
            "build/overlay/etc/systemd/journald.conf.d/10-greia-bounds.conf",
            "build/installer-overlay/etc/systemd/journald.conf.d/10-greia-bounds.conf",
        ):
            with self.subTest(overlay=relative):
                path = REPO_ROOT / relative
                self.assertTrue(path.is_file(), f"missing journald bound: {relative}")
                text = path.read_text(encoding="utf-8")
                self.assertIn("Storage=volatile", text)
                self.assertNotIn("Storage=persistent", text)


class BootHistoryRingTests(unittest.TestCase):
    def test_cap_is_64kib_and_shared_between_owners(self) -> None:
        # P2: source-enforced hard cap, one value on both sides of the seam.
        self.assertEqual(MAX_BOOT_HISTORY_BYTES, 64 * 1024)
        self.assertEqual(persist_module.MAX_BOOT_HISTORY_BYTES, MAX_BOOT_HISTORY_BYTES)
        self.assertEqual(
            persist_module.PERSIST_BOOT_HISTORY_NAME, BOOT_HISTORY_FILE_NAME
        )
        self.assertEqual(
            persist_module.BOOT_HISTORY_RUNTIME_PATH, BOOT_HISTORY_RUNTIME_PATH
        )
        self.assertEqual(BOOT_HISTORY_RUNTIME_PATH,
                         "/var/lib/greia-os/diagnostics/boot-history.json")

    def test_audit_classifies_boot_history_as_bounded_logs(self) -> None:
        entry = find_audit_entry(BOOT_HISTORY_RUNTIME_PATH)
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.durability, Durability.PERSISTENT_SHARED)
        self.assertEqual(entry.namespace, "bounded-logs")
        self.assertEqual(entry.mount, MountKind.INHERIT)

    def test_persist_path_helper_matches_boot_transaction_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            persist_root = Path(tmp)
            expected = persist_root / "greia" / BOOT_HISTORY_FILE_NAME
            self.assertEqual(persist_boot_history_path(persist_root), expected)
            self.assertEqual(
                boot_module.boot_history_path(persist_root), expected
            )

    def test_rotation_and_milestone_updates_stay_canonical_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            history_dir = Path(tmp) / "persist" / "greia"
            history_dir.mkdir(parents=True)
            history = BootHistory.empty(history_dir)
            history.begin_boot(**_boot_kwargs(
                slot="A", release="greia-0.14.0", seq=7,
                txn="txn-first", txn_type="first-install", default="A",
            ))
            history.record_milestone("slot-observed")
            history.record_milestone("launcher-started")
            history.record_milestone(
                "interactive-ready", launcher_result="ok",
            )
            history.record_milestone(
                "committed", health_result="confirmed", terminal_state="accepted",
            )
            raw = history.history_path.read_bytes()
            self.assertLessEqual(len(raw), MAX_BOOT_HISTORY_BYTES)
            # Canonical JSON: reload is byte-identical.
            reloaded = BootHistory.load(history_dir)
            self.assertEqual(reloaded.canonical_bytes(), raw)
            self.assertEqual(reloaded.current.milestone, "committed")
            self.assertEqual(reloaded.current.launcher_result, "ok")

    def test_failed_candidate_previous_boot_report_uses_persist_only(self) -> None:
        # P1: full production-path proof. Volatile /run and the previous
        # journal are unavailable; only the PERSIST file crosses the reboot.
        with tempfile.TemporaryDirectory() as tmp:
            persist_mount = Path(tmp) / "persist"
            history_dir = persist_mount / "greia"
            history_dir.mkdir(parents=True)
            volatile_run = Path(tmp) / "run" / "greia-os"
            volatile_run.mkdir(parents=True)
            (volatile_run / "active-profile.json").write_text("{}\n")

            history = BootHistory.empty(history_dir)
            history.begin_boot(**_boot_kwargs(
                slot="A", release="greia-0.14.0", seq=7,
                txn="txn-a", txn_type="first-install", default="A",
            ))
            history.record_milestone("interactive-ready", launcher_result="ok")
            history.record_milestone(
                "committed", health_result="confirmed", terminal_state="accepted",
            )
            # Failed candidate B boots, reaches launcher, then fails health.
            history.begin_boot(**_boot_kwargs(
                slot="B", release="greia-0.15.0", seq=11,
                txn="txn-b", txn_type="update", default="A", one_shot="B",
                started=1757000600,
            ))
            history.record_milestone("launcher-started")
            history.record_milestone(
                "failed", launcher_result="failed", health_result="failed",
                recovery_reason="candidate-failed",
                terminal_state="failed",
            )

            # --- reboot: volatile state and journals are gone ---
            # Simulate the guest-disk read by copying only the PERSIST file.
            guest_copy = Path(tmp) / "guest-disk" / "greia"
            guest_copy.mkdir(parents=True)
            (guest_copy / BOOT_HISTORY_FILE_NAME).write_bytes(
                history.history_path.read_bytes()
            )
            os.chmod(guest_copy / BOOT_HISTORY_FILE_NAME, BOOT_HISTORY_FILE_MODE)
            # Prove volatile is not consulted: delete it.
            (volatile_run / "active-profile.json").unlink()

            rebooted = BootHistory.load(guest_copy)
            summary = describe_previous_boot(rebooted)
            # The rebooted head is the accepted system's new boot only after
            # it rotates; here the ring head is still the failed candidate,
            # so emulate the accepted reboot rotation first.
            rebooted.begin_boot(**_boot_kwargs(
                slot="A", release="greia-0.14.0", seq=7,
                txn="txn-a2", txn_type="update", default="A",
                started=1757001200,
            ))
            summary = describe_previous_boot(rebooted)
            self.assertIsNotNone(summary)
            assert summary is not None
            self.assertEqual(summary["attempted_slot"], "B")
            self.assertEqual(summary["attempted_release_id"], "greia-0.15.0")
            self.assertEqual(summary["attempted_release_sequence"], 11)
            self.assertEqual(summary["last_milestone"], "failed")
            self.assertEqual(summary["recovery_reason"], "candidate-failed")
            self.assertEqual(summary["terminal_state"], "failed")
            self.assertEqual(summary["transaction_type"], "update")

    def test_coarse_boundaries_only_reject_verbose_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            history_dir = Path(tmp)
            history = BootHistory.empty(history_dir)
            history.begin_boot(**_boot_kwargs(
                slot="A", release="greia-0.14.0", seq=7,
                txn="txn-a", txn_type="first-install", default="A",
            ))
            for verbose in (
                "animation-frame-12",
                "input-event",
                "journal-line",
                "pointer-move",
            ):
                with self.subTest(verbose=verbose), self.assertRaises(
                    BootTransactionError
                ):
                    history.record_milestone(verbose)

    def test_over_budget_write_fails_closed_and_file_untouched(self) -> None:
        # P2 negative control: with no budget left, rotation must raise and
        # the existing file must keep its exact bytes (never grow).
        with tempfile.TemporaryDirectory() as tmp:
            history_dir = Path(tmp)
            history = BootHistory.empty(history_dir)
            history.begin_boot(**_boot_kwargs(
                slot="A", release="greia-0.14.0", seq=7,
                txn="txn-a", txn_type="first-install", default="A",
            ))
            before = history.history_path.read_bytes()
            original_max = boot_module.MAX_BOOT_HISTORY_BYTES
            try:
                boot_module.MAX_BOOT_HISTORY_BYTES = 10  # type: ignore[assignment]
                with self.assertRaises(BootTransactionError):
                    history.begin_boot(**_boot_kwargs(
                        slot="B", release="greia-0.15.0", seq=11,
                        txn="txn-b", txn_type="update", default="A",
                        one_shot="B",
                    ))
                self.assertEqual(history.history_path.read_bytes(), before)
                self.assertEqual(len(history.entries), 1)
            finally:
                boot_module.MAX_BOOT_HISTORY_BYTES = original_max

    def test_ring_truncates_oldest_within_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            history_dir = Path(tmp)
            history = BootHistory.empty(history_dir)
            for index in range(MAX_BOOT_HISTORY_ENTRIES + 3):
                history.begin_boot(**_boot_kwargs(
                    slot="A" if index % 2 == 0 else "B",
                    release="greia-0.14.0", seq=index,
                    txn=f"txn-{index}", txn_type="update",
                    default="A", started=1757000000 + index,
                ))
            self.assertEqual(len(history.entries), MAX_BOOT_HISTORY_ENTRIES)
            self.assertLessEqual(
                len(history.history_path.read_bytes()), MAX_BOOT_HISTORY_BYTES
            )
            # Oldest entries rotated away; newest retained.
            self.assertEqual(history.entries[-1].transaction_id,
                             f"txn-{MAX_BOOT_HISTORY_ENTRIES + 2}")

    def test_corrupt_history_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            history_dir = Path(tmp)
            history = BootHistory.empty(history_dir)
            history.begin_boot(**_boot_kwargs(
                slot="A", release="greia-0.14.0", seq=7,
                txn="txn-a", txn_type="first-install", default="A",
            ))
            history.history_path.write_bytes(b"{not json")
            os.chmod(history.history_path, BOOT_HISTORY_FILE_MODE)
            with self.assertRaises(BootTransactionError):
                BootHistory.load(history_dir)

    def test_symlink_history_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            history_dir = Path(tmp) / "h"
            history_dir.mkdir()
            target = Path(tmp) / "real.json"
            target.write_text("{}\n")
            link = history_dir / BOOT_HISTORY_FILE_NAME
            link.symlink_to(target)
            with self.assertRaises(BootTransactionError):
                BootHistory.load(history_dir)


if __name__ == "__main__":
    unittest.main()

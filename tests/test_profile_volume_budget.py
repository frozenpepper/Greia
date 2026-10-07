"""Shared profile-volume headroom contracts; no Pygame or hardware required."""
from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from greia_platform.creation_capacity import (
    VolumeBudget,
    VolumeCapacityPolicy,
    VolumeSpaceError,
    VolumeUsage,
)
from greia_platform.history import (
    HistoryError,
    HistoryPolicy,
    ProfileHistoryStore,
)
from greia_platform.storage import (
    ActivityStorageService,
    StoragePolicy,
    StorageQuotaExceeded,
)


_GIB = 1024 ** 3
_MIB = 1024 ** 2


class _MutableProbe:
    def __init__(self) -> None:
        self.usage = VolumeUsage(8 * _GIB, 2 * _GIB, 6 * _GIB)

    def __call__(self, _root: Path) -> VolumeUsage:
        return self.usage


class _Profile:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.storage_dir = root / "storage"
        self.progress_dir = root / "progress"

    def activity_storage_dir(self, activity_id: str) -> Path:
        target = self.storage_dir / activity_id
        target.mkdir(parents=True, exist_ok=True)
        return target


def _storage_policy() -> StoragePolicy:
    return StoragePolicy(
        policy_schema_version=1,
        namespace_quota_bytes=4 * _MIB,
        max_kv_bytes=256 * 1024,
        max_kv_value_bytes=64 * 1024,
        max_key_bytes=128,
        max_file_bytes=2 * _MIB,
        max_files=64,
        max_path_bytes=512,
        protected_free_bytes=64 * _MIB,
        max_rollback_snapshots=2,
    )


def _history_policy() -> HistoryPolicy:
    return HistoryPolicy(
        schema_version=1,
        max_sessions_per_profile=20,
        max_events_per_session=16,
        max_event_payload_bytes=8192,
        max_idempotency_key_bytes=64,
        max_reward_ledger_entries=100,
        max_recent_sessions_summary=10,
        max_score_absolute=1_000_000,
        sqlite_busy_timeout_ms=500,
    )


class VolumeBudgetTests(unittest.TestCase):
    def test_non_growing_repair_can_use_reserve_but_positive_growth_cannot(self):
        policy = VolumeCapacityPolicy(
            maximum_used_fraction=0.75,
            minimum_free_bytes=200,
        )
        usage = VolumeUsage(total_bytes=1000, used_bytes=750, free_bytes=250)
        policy.require_write(
            usage,
            final_growth_bytes=0,
            peak_additional_bytes=100,
        )
        with self.assertRaises(VolumeSpaceError):
            policy.require_write(
                usage,
                final_growth_bytes=1,
                peak_additional_bytes=1,
            )
        with self.assertRaises(VolumeSpaceError):
            policy.require_write(
                usage,
                final_growth_bytes=0,
                peak_additional_bytes=251,
            )

    def test_reservation_serializes_measure_then_write_across_writers(self):
        state = {"usage": VolumeUsage(1000, 600, 400)}
        budget = VolumeBudget(
            VolumeCapacityPolicy(
                maximum_used_fraction=0.75,
                minimum_free_bytes=0,
            ),
            probe=lambda _root: state["usage"],
        )
        root = Path("/")
        first_entered = threading.Event()
        release_first = threading.Event()
        second_done = threading.Event()
        outcome: list[str] = []

        def first_writer() -> None:
            with budget.write_reservation(
                root,
                final_growth_bytes=100,
                peak_additional_bytes=100,
            ):
                state["usage"] = VolumeUsage(1000, 700, 300)
                first_entered.set()
                release_first.wait(timeout=2)

        def second_writer() -> None:
            first_entered.wait(timeout=2)
            try:
                with budget.write_reservation(
                    root,
                    final_growth_bytes=100,
                    peak_additional_bytes=100,
                ):
                    outcome.append("allowed")
            except VolumeSpaceError:
                outcome.append("denied")
            finally:
                second_done.set()

        first = threading.Thread(target=first_writer)
        second = threading.Thread(target=second_writer)
        first.start()
        second.start()
        self.assertTrue(first_entered.wait(timeout=2))
        self.assertFalse(second_done.wait(timeout=0.05))
        release_first.set()
        first.join(timeout=2)
        second.join(timeout=2)
        self.assertEqual(outcome, ["denied"])


class ActivityStorageVolumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = _Profile(Path(self.temp.name) / "profile")
        self.profile.root.mkdir(parents=True)
        self.probe = _MutableProbe()
        self.budget = VolumeBudget(probe=self.probe)
        self.service = ActivityStorageService(
            _storage_policy(),
            volume_budget=self.budget,
        )
        self.storage = self.service.open(
            self.profile,
            "org.greia.test",
            schema_version=1,
            package_version="1.0.0",
        )

    def test_same_size_replace_allowed_at_ceiling_but_new_growth_denied(self):
        self.storage.file_write_atomic("state.bin", b"abc")
        self.probe.usage = VolumeUsage(
            8 * _GIB,
            6 * _GIB,
            2 * _GIB,
        )
        self.storage.file_write_atomic("state.bin", b"xyz")
        self.assertEqual(self.storage.file_read("state.bin"), b"xyz")

        with self.assertRaises(StorageQuotaExceeded):
            self.storage.file_write_atomic("new.bin", b"x")
        with self.assertRaisesRegex(Exception, "does not exist"):
            self.storage.file_read("new.bin")

    def test_migration_working_copy_uses_same_volume_guard(self):
        self.storage.file_write_atomic("state.bin", b"payload")
        self.probe.usage = VolumeUsage(
            8 * _GIB,
            6 * _GIB,
            2 * _GIB,
        )
        with self.assertRaises(StorageQuotaExceeded):
            self.service.begin_migration(
                self.profile,
                "org.greia.test",
                target_schema_version=2,
                package_version="2.0.0",
            )


class HistoryVolumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = _Profile(Path(self.temp.name) / "profile")
        self.profile.root.mkdir(parents=True)
        self.probe = _MutableProbe()
        self.budget = VolumeBudget(probe=self.probe)
        self.store = ProfileHistoryStore(
            self.profile,
            _history_policy(),
            volume_budget=self.budget,
        )
        self.manifest = SimpleNamespace(
            activity_id="org.greia.test",
            version="1.0.0",
            runtime_type="python",
        )

    def test_existing_session_update_survives_ceiling_new_session_does_not(self):
        self.store.start_session(
            self.manifest,
            session_id="session-one",
            package_digest="a" * 64,
        )
        self.probe.usage = VolumeUsage(
            8 * _GIB,
            6 * _GIB,
            2 * _GIB,
        )

        # Update-only SQLite work may use bounded scratch inside the reserve.
        self.store.mark_ready("session-one")

        with self.assertRaises(HistoryError):
            self.store.start_session(
                self.manifest,
                session_id="session-two",
                package_digest="b" * 64,
            )
        self.assertEqual(len(self.store.summary().recent_sessions), 1)


if __name__ == "__main__":
    unittest.main()

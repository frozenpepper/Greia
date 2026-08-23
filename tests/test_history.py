from __future__ import annotations

import json
import math
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from greia_platform.activities import (
    ActivityEventDefinition,
    ActivityRegistry,
    RuntimeCatalogue,
)
from greia_platform.history import (
    EventIdempotencyConflict,
    EventValidationError,
    HistoryError,
    HistoryPolicy,
    ProfileHistoryStore,
    ProgressionPolicy,
)
from greia_platform.profiles import ProfileStore
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _Clock:
    def __init__(self, value: float = 1000.0):
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class HistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        runtime = RuntimeCatalogue.load(PROJECT_ROOT / "runtime" / "child-runtime.toml")
        source = ActivitySource(
            PROJECT_ROOT / "activities",
            PackageTrust.BUILT_IN,
            "greia-system",
        )
        cls.activities = ActivityRegistry([source], runtime).discover()
        cls.shape = next(
            item for item in cls.activities if item.activity_id == "org.greia.shape-garden"
        )
        cls.history_policy = HistoryPolicy.load(
            PROJECT_ROOT / "runtime" / "history-policy.toml"
        )
        cls.progression = ProgressionPolicy.load(
            PROJECT_ROOT / "runtime" / "progression-policy.toml",
            cls.activities,
        )

    def _context(self, root: Path):
        profiles = ProfileStore.load(
            PROJECT_ROOT / "runtime" / "profile-defaults.toml",
            root / "profiles",
        )
        profile = profiles.ensure_initialized()[0]
        return profiles.context(profile.profile_id)

    def _store(
        self,
        root: Path,
        *,
        clock: _Clock | None = None,
        policy: HistoryPolicy | None = None,
    ) -> ProfileHistoryStore:
        return ProfileHistoryStore(
            self._context(root),
            policy or self.history_policy,
            clock=clock or _Clock(),
        )

    def _start(
        self,
        store: ProfileHistoryStore,
        session_id: str,
        *,
        manifest=None,
    ) -> None:
        manifest = manifest or self.shape
        store.start_session(
            manifest,
            session_id=session_id,
            package_digest="a" * 64,
        )

    def test_policy_loads_against_canonical_activity_catalogue(self) -> None:
        self.assertEqual(self.history_policy.max_sessions_per_profile, 2000)
        self.assertEqual(len(self.progression.rules), 4)
        rule_map = {rule.rule_id: rule for rule in self.progression.rules}
        self.assertIn("shape-garden-creation-star", rule_map)
        rule = rule_map["shape-garden-creation-star"]
        self.assertEqual(rule.activity_id, "org.greia.shape-garden")
        self.assertEqual(rule.event_id, "creation.completed")
        self.assertEqual((rule.reward_id, rule.reward_delta), ("star", 1))

    def test_authoritative_session_ready_finish_and_restart_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clock = _Clock(100.0)
            store = self._store(Path(temporary), clock=clock)
            self._start(store, "session-one")
            clock.advance(2.0)
            store.mark_ready("session-one")
            clock.advance(3.0)
            store.finish_session("session-one", "normal")

            self._start(store, "session-two")
            clock.advance(7.0)
            self.assertEqual(store.recover_unfinished_sessions(), 1)
            summary = store.summary()

        self.assertEqual(len(summary.recent_sessions), 2)
        restarted, normal = summary.recent_sessions
        self.assertEqual(restarted.exit_reason, "platform_restart")
        self.assertFalse(restarted.ready)
        self.assertEqual(restarted.active_duration_seconds, 7.0)
        self.assertEqual(normal.exit_reason, "normal")
        self.assertTrue(normal.ready)
        self.assertEqual(normal.active_duration_seconds, 5.0)

    def test_identical_idempotent_event_does_not_duplicate_progression(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            self._start(store, "session-one")
            payload = {"reward_id": "diamonds", "reward_delta": 999999}
            first = store.emit_event(
                self.shape,
                self.progression,
                session_id="session-one",
                event_id="creation.completed",
                idempotency_key="create-1",
                payload=payload,
            )
            duplicate = store.emit_event(
                self.shape,
                self.progression,
                session_id="session-one",
                event_id="creation.completed",
                idempotency_key="create-1",
                payload=payload,
            )
            summary = store.summary()

        self.assertFalse(first.duplicate)
        self.assertEqual(first.reward_deltas, (("star", 1),))
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(duplicate.event_record_id, first.event_record_id)
        self.assertEqual(duplicate.reward_deltas, ())
        self.assertEqual(dict(summary.reward_balances), {"star": 1})
        self.assertEqual(
            dict(summary.event_counts),
            {"org.greia.shape-garden:creation.completed": 1},
        )
        self.assertNotIn("diamonds", dict(summary.reward_balances))

    def test_conflicting_idempotency_reuse_is_transactional(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            self._start(store, "session-one")
            store.emit_event(
                self.shape,
                self.progression,
                session_id="session-one",
                event_id="creation.completed",
                idempotency_key="same-key",
                payload={"value": 1},
            )
            with self.assertRaises(EventIdempotencyConflict):
                store.emit_event(
                    self.shape,
                    self.progression,
                    session_id="session-one",
                    event_id="creation.completed",
                    idempotency_key="same-key",
                    payload={"value": 2},
                )
            summary = store.summary()

        self.assertEqual(dict(summary.reward_balances), {"star": 1})
        self.assertEqual(
            dict(summary.event_counts)["org.greia.shape-garden:creation.completed"],
            1,
        )

    def test_only_declared_events_on_open_matching_session_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            self._start(store, "session-one")
            with self.assertRaises(EventValidationError):
                store.emit_event(
                    self.shape,
                    self.progression,
                    session_id="session-one",
                    event_id="not.declared",
                    idempotency_key="bad-event",
                )
            store.finish_session("session-one", "normal")
            with self.assertRaises(EventValidationError):
                store.emit_event(
                    self.shape,
                    self.progression,
                    session_id="session-one",
                    event_id="creation.completed",
                    idempotency_key="after-close",
                )

    def test_score_order_is_manifest_owned_and_bounded(self) -> None:
        score_manifest = replace(
            self.shape,
            events=(ActivityEventDefinition("score.points", "score", "higher_better"),),
        )
        no_rewards = ProgressionPolicy(1, ())
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            self._start(store, "score-session", manifest=score_manifest)
            for key, score in (("one", 10), ("two", 5), ("three", 12)):
                store.emit_event(
                    score_manifest,
                    no_rewards,
                    session_id="score-session",
                    event_id="score.points",
                    idempotency_key=key,
                    score=score,
                )
            with self.assertRaises(EventValidationError):
                store.emit_event(
                    score_manifest,
                    no_rewards,
                    session_id="score-session",
                    event_id="score.points",
                    idempotency_key="nan",
                    score=math.nan,
                )
            summary = store.summary()

        self.assertEqual(
            dict(summary.best_scores)["org.greia.shape-garden:score.points"],
            12.0,
        )

    def test_non_score_event_rejects_score_and_bounds_payload_and_key(self) -> None:
        policy = replace(
            self.history_policy,
            max_event_payload_bytes=16,
            max_idempotency_key_bytes=8,
        )
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary), policy=policy)
            self._start(store, "session-one")
            with self.assertRaises(EventValidationError):
                store.emit_event(
                    self.shape,
                    self.progression,
                    session_id="session-one",
                    event_id="creation.completed",
                    idempotency_key="score",
                    score=1,
                )
            with self.assertRaises(EventValidationError):
                store.emit_event(
                    self.shape,
                    self.progression,
                    session_id="session-one",
                    event_id="creation.completed",
                    idempotency_key="123456789",
                )
            with self.assertRaises(EventValidationError):
                store.emit_event(
                    self.shape,
                    self.progression,
                    session_id="session-one",
                    event_id="creation.completed",
                    idempotency_key="payload",
                    payload={"too_long": "0123456789"},
                )

    def test_once_per_session_reward_applies_again_only_in_new_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            self._start(store, "session-one")
            first = store.emit_event(
                self.shape,
                self.progression,
                session_id="session-one",
                event_id="creation.completed",
                idempotency_key="first",
            )
            second = store.emit_event(
                self.shape,
                self.progression,
                session_id="session-one",
                event_id="creation.completed",
                idempotency_key="second",
            )
            store.finish_session("session-one", "normal")
            self._start(store, "session-two")
            third = store.emit_event(
                self.shape,
                self.progression,
                session_id="session-two",
                event_id="creation.completed",
                idempotency_key="third",
            )
            summary = store.summary()

        self.assertEqual(first.reward_deltas, (("star", 1),))
        self.assertEqual(second.reward_deltas, ())
        self.assertEqual(third.reward_deltas, (("star", 1),))
        self.assertEqual(dict(summary.reward_balances), {"star": 2})
        self.assertEqual(
            dict(summary.event_counts)["org.greia.shape-garden:creation.completed"],
            3,
        )

    def test_retention_prunes_detail_without_losing_progression_aggregates(self) -> None:
        policy = replace(
            self.history_policy,
            max_sessions_per_profile=2,
            max_recent_sessions_summary=2,
            max_reward_ledger_entries=1,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self._store(root, policy=policy)
            for index in range(3):
                session_id = f"session-{index}"
                self._start(store, session_id)
                store.emit_event(
                    self.shape,
                    self.progression,
                    session_id=session_id,
                    event_id="creation.completed",
                    idempotency_key=f"event-{index}",
                )
                store.finish_session(session_id, "normal")
            summary = store.summary()
            exported = store.export_state()

        self.assertEqual(len(summary.recent_sessions), 2)
        self.assertEqual(dict(summary.reward_balances), {"star": 3})
        self.assertEqual(
            dict(summary.event_counts)["org.greia.shape-garden:creation.completed"],
            3,
        )
        self.assertLessEqual(len(exported["reward_ledger"]), 1)
        self.assertEqual(len(exported["sessions"]), 2)

    def test_export_is_logical_json_state_not_database_bytes_or_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            self._start(store, "session-one")
            store.emit_event(
                self.shape,
                self.progression,
                session_id="session-one",
                event_id="creation.completed",
                idempotency_key="event-one",
                payload={"shape": "circle"},
            )
            exported = store.export_state()
            encoded = json.dumps(exported, sort_keys=True)

        self.assertEqual(exported["schema_version"], 1)
        self.assertIn("creation.completed", encoded)
        self.assertNotIn("history.sqlite3", encoded)
        self.assertNotIn(str(store.database_path), encoded)

    def test_corrupt_database_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = self._context(root)
            store = ProfileHistoryStore(context, self.history_policy)
            database_path = store.database_path
            database_path.write_bytes(b"not a sqlite database")
            with self.assertRaises(HistoryError):
                ProfileHistoryStore(context, self.history_policy)

    def test_progress_path_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = self._context(root)
            outside = root / "outside"
            outside.mkdir()
            context.progress_dir.rmdir()
            try:
                context.progress_dir.symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaisesRegex(HistoryError, "symbolic link"):
                ProfileHistoryStore(context, self.history_policy)


if __name__ == "__main__":
    unittest.main()

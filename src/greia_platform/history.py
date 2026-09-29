from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import sqlite3
import time
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Mapping

from .activities import ActivityEventDefinition, ActivityManifest
from .profiles import ProfileContext


logger = logging.getLogger(__name__)


_HISTORY_SCHEMA_VERSION = 1
_MAX_SIGNED_64 = (1 << 63) - 1
_ALLOWED_EXIT_REASONS = frozenset(
    {
        "normal",
        "crash",
        "launch_failure",
        "ready_timeout",
        "graceful_stop",
        "forced_stop",
        "system_shutdown",
        "platform_failure",
        "platform_restart",
    }
)


class HistoryError(RuntimeError):
    """Platform history/progression state could not be safely read or changed."""


class HistoryPolicyError(HistoryError):
    """History or progression policy is invalid."""


class EventValidationError(HistoryError):
    """An Activity event violates the live manifest/history contract."""


class EventIdempotencyConflict(EventValidationError):
    """An idempotency key was reused for different normalized event content."""


@dataclass(frozen=True, slots=True)
class HistoryPolicy:
    schema_version: int
    max_sessions_per_profile: int
    max_events_per_session: int
    max_event_payload_bytes: int
    max_idempotency_key_bytes: int
    max_reward_ledger_entries: int
    max_recent_sessions_summary: int
    max_score_absolute: int
    sqlite_busy_timeout_ms: int

    @classmethod
    def load(cls, path: Path) -> "HistoryPolicy":
        raw = _load_toml(path, "history policy")
        policy = cls(
            schema_version=_integer(raw, "schema_version", 1, 1),
            max_sessions_per_profile=_integer(
                raw, "max_sessions_per_profile", 1, 100_000
            ),
            max_events_per_session=_integer(raw, "max_events_per_session", 1, 100_000),
            max_event_payload_bytes=_integer(
                raw, "max_event_payload_bytes", 1, 64 * 1024
            ),
            max_idempotency_key_bytes=_integer(
                raw, "max_idempotency_key_bytes", 1, 4096
            ),
            max_reward_ledger_entries=_integer(
                raw, "max_reward_ledger_entries", 1, 1_000_000
            ),
            max_recent_sessions_summary=_integer(
                raw, "max_recent_sessions_summary", 1, 10_000
            ),
            max_score_absolute=_integer(raw, "max_score_absolute", 1, _MAX_SIGNED_64),
            sqlite_busy_timeout_ms=_integer(raw, "sqlite_busy_timeout_ms", 1, 60_000),
        )
        if policy.max_recent_sessions_summary > policy.max_sessions_per_profile:
            raise HistoryPolicyError(
                "max_recent_sessions_summary cannot exceed max_sessions_per_profile"
            )
        return policy


@dataclass(frozen=True, slots=True)
class ProgressionRule:
    rule_id: str
    activity_id: str
    event_id: str
    once_per_session: bool
    reward_id: str
    reward_delta: int


@dataclass(frozen=True, slots=True)
class ProgressionPolicy:
    schema_version: int
    rules: tuple[ProgressionRule, ...]

    @classmethod
    def load(
        cls, path: Path, activities: Iterable[ActivityManifest]
    ) -> "ProgressionPolicy":
        raw = _load_toml(path, "progression policy")
        schema_version = _integer(raw, "schema_version", 1, 1)
        raw_rules = raw.get("rules", [])
        if not isinstance(raw_rules, list) or not all(
            isinstance(item, dict) for item in raw_rules
        ):
            raise HistoryPolicyError("progression rules must be an array of tables")

        activity_tuple = tuple(activities)
        manifests = {activity.activity_id: activity for activity in activity_tuple}
        if len(manifests) != len(activity_tuple):
            raise HistoryPolicyError("progression Activity catalogue contains duplicates")

        rules: list[ProgressionRule] = []
        seen_rule_ids: set[str] = set()
        for raw_rule in raw_rules:
            assert isinstance(raw_rule, dict)
            rule_id = _bounded_identifier(raw_rule, "id")
            activity_id = _bounded_identifier(raw_rule, "activity_id")
            event_id = _bounded_identifier(raw_rule, "event_id")
            reward_id = _bounded_identifier(raw_rule, "reward_id")
            once_per_session = _boolean(raw_rule, "once_per_session")
            reward_delta = _signed_integer(raw_rule, "reward_delta")
            if reward_delta == 0:
                raise HistoryPolicyError("progression reward_delta must not be zero")
            if rule_id in seen_rule_ids:
                raise HistoryPolicyError(f"duplicate progression rule id: {rule_id}")
            seen_rule_ids.add(rule_id)

            manifest = manifests.get(activity_id)
            if manifest is None:
                # A progression rule may reference an Activity that is not
                # available on this system because it failed registered-input
                # validation (broken/not loaded) or was retired. A single such
                # rule must not take the whole launcher down: drop the rule so
                # the broken Activity stays an island while progression for all
                # remaining Activities keeps working.
                logger.warning(
                    "Dropping progression rule %r: Activity %r is not loaded",
                    rule_id,
                    activity_id,
                )
                continue
            if event_id not in {event.event_id for event in manifest.events}:
                raise HistoryPolicyError(
                    f"progression rule {rule_id!r} references undeclared event {event_id!r}"
                )
            rules.append(
                ProgressionRule(
                    rule_id,
                    activity_id,
                    event_id,
                    once_per_session,
                    reward_id,
                    reward_delta,
                )
            )
        return cls(schema_version, tuple(rules))

    def matching_rules(
        self, activity_id: str, event_id: str
    ) -> tuple[ProgressionRule, ...]:
        return tuple(
            rule
            for rule in self.rules
            if rule.activity_id == activity_id and rule.event_id == event_id
        )


@dataclass(frozen=True, slots=True)
class EventReceipt:
    event_record_id: int
    duplicate: bool
    reward_deltas: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class RecentSessionSummary:
    activity_id: str
    package_version: str
    runtime_type: str
    started_at: float
    ended_at: float | None
    active_duration_seconds: float | None
    exit_reason: str | None
    ready: bool


@dataclass(frozen=True, slots=True)
class HistorySummary:
    reward_balances: tuple[tuple[str, int], ...]
    event_counts: tuple[tuple[str, int], ...]
    best_scores: tuple[tuple[str, float], ...]
    recent_sessions: tuple[RecentSessionSummary, ...]


@dataclass(frozen=True, slots=True)
class PlatformHistoryService:
    """Shared R5 policy/configuration that opens one private store per profile."""

    history_policy: HistoryPolicy
    progression_policy: ProgressionPolicy

    @classmethod
    def load(
        cls,
        history_policy_path: Path,
        progression_policy_path: Path,
        activities: Iterable[ActivityManifest],
    ) -> "PlatformHistoryService":
        activity_tuple = tuple(activities)
        return cls(
            HistoryPolicy.load(history_policy_path),
            ProgressionPolicy.load(progression_policy_path, activity_tuple),
        )

    def open(self, profile: ProfileContext) -> "ProfileHistoryStore":
        return ProfileHistoryStore(profile, self.history_policy)

    def recover_unfinished(self, profile: ProfileContext) -> int:
        return self.open(profile).recover_unfinished_sessions()


class ProfileHistoryStore:
    """Profile-owned authoritative local session/event/progression database.

    SQLite is deliberately private implementation detail. Activity processes receive
    neither this path nor SQL access. All writes occur through the platform-owned
    lifecycle/event boundaries defined by ADR 0017.
    """

    DB_NAME = "history.sqlite3"

    def __init__(
        self,
        profile: ProfileContext,
        policy: HistoryPolicy,
        *,
        clock: Callable[[], float] = time.time,
    ):
        self.profile = profile
        self.policy = policy
        self._clock = clock
        self._root = profile.progress_dir
        self._db_path = self._root / self.DB_NAME
        self._prepare_root()
        self._initialize_schema()

    def start_session(
        self,
        manifest: ActivityManifest,
        *,
        session_id: str,
        package_digest: str,
        started_at: float | None = None,
    ) -> None:
        _validate_identifier(session_id, "session_id", maximum=160)
        _validate_digest(package_digest)
        timestamp = _timestamp(self._clock() if started_at is None else started_at)
        with self._transaction() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO sessions(
                        session_id, activity_id, package_version, package_digest,
                        runtime_type, started_at, ready
                    ) VALUES(?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        session_id,
                        manifest.activity_id,
                        manifest.version,
                        package_digest,
                        manifest.runtime_type,
                        timestamp,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise HistoryError("session identity already exists") from exc
            self._prune_sessions(connection)

    def recover_unfinished_sessions(self, *, ended_at: float | None = None) -> int:
        timestamp = _timestamp(self._clock() if ended_at is None else ended_at)
        with self._transaction() as connection:
            rows = connection.execute(
                "SELECT session_id, started_at FROM sessions WHERE ended_at IS NULL"
            ).fetchall()
            for row in rows:
                duration = max(0.0, timestamp - float(row["started_at"]))
                connection.execute(
                    """
                    UPDATE sessions
                       SET ended_at = ?, active_duration_seconds = ?,
                           exit_reason = 'platform_restart'
                     WHERE session_id = ? AND ended_at IS NULL
                    """,
                    (timestamp, duration, str(row["session_id"])),
                )
            self._prune_sessions(connection)
            return len(rows)

    def mark_ready(self, session_id: str, *, ready_at: float | None = None) -> None:
        timestamp = _timestamp(self._clock() if ready_at is None else ready_at)
        with self._transaction() as connection:
            row = self._session_row(connection, session_id)
            if row["ended_at"] is not None:
                raise HistoryError("cannot mark a closed session ready")
            connection.execute(
                """
                UPDATE sessions
                   SET ready = 1, ready_at = COALESCE(ready_at, ?)
                 WHERE session_id = ?
                """,
                (timestamp, session_id),
            )

    def finish_session(
        self,
        session_id: str,
        exit_reason: object,
        *,
        ended_at: float | None = None,
        active_duration_seconds: float | None = None,
    ) -> None:
        reason = str(exit_reason)
        if reason not in _ALLOWED_EXIT_REASONS:
            raise HistoryError(f"unsupported session exit reason: {reason}")
        timestamp = _timestamp(self._clock() if ended_at is None else ended_at)
        with self._transaction() as connection:
            row = self._session_row(connection, session_id)
            if row["ended_at"] is not None:
                raise HistoryError("session is already closed")
            duration = (
                max(0.0, timestamp - float(row["started_at"]))
                if active_duration_seconds is None
                else _duration(active_duration_seconds)
            )
            connection.execute(
                """
                UPDATE sessions
                   SET ended_at = ?, active_duration_seconds = ?, exit_reason = ?
                 WHERE session_id = ? AND ended_at IS NULL
                """,
                (timestamp, duration, reason, session_id),
            )
            self._prune_sessions(connection)

    def emit_event(
        self,
        manifest: ActivityManifest,
        progression: ProgressionPolicy,
        *,
        session_id: str,
        event_id: str,
        idempotency_key: str,
        score: object = None,
        payload: object = None,
    ) -> EventReceipt:
        event = _declared_event(manifest, event_id)
        normalized_score = self._validate_score(event, score)
        normalized_payload, payload_json = self._validate_payload(payload)
        key = self._validate_idempotency_key(idempotency_key)
        normalized = {
            "activity_id": manifest.activity_id,
            "event_id": event.event_id,
            "score": normalized_score,
            "payload": normalized_payload,
        }
        content_json = _portable_json(normalized)
        content_digest = hashlib.sha256(content_json.encode("utf-8")).hexdigest()
        timestamp = _timestamp(self._clock())

        with self._transaction() as connection:
            session = self._session_row(connection, session_id)
            if session["ended_at"] is not None:
                raise EventValidationError("event session is closed")
            if session["activity_id"] != manifest.activity_id:
                raise EventValidationError("event Activity does not match live session")

            existing = connection.execute(
                """
                SELECT record_id, content_digest
                  FROM events
                 WHERE session_id = ? AND idempotency_key = ?
                """,
                (session_id, key),
            ).fetchone()
            if existing is not None:
                if existing["content_digest"] != content_digest:
                    raise EventIdempotencyConflict(
                        "idempotency key was reused for different event content"
                    )
                return EventReceipt(int(existing["record_id"]), True, ())

            event_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM events WHERE session_id = ?", (session_id,)
                ).fetchone()[0]
            )
            if event_count >= self.policy.max_events_per_session:
                raise EventValidationError("session event limit has been reached")

            cursor = connection.execute(
                """
                INSERT INTO events(
                    session_id, activity_id, event_id, idempotency_key,
                    content_digest, score, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    manifest.activity_id,
                    event.event_id,
                    key,
                    content_digest,
                    normalized_score,
                    payload_json,
                    timestamp,
                ),
            )
            record_id = int(cursor.lastrowid)

            connection.execute(
                """
                INSERT INTO event_counts(activity_id, event_id, count)
                VALUES(?, ?, 1)
                ON CONFLICT(activity_id, event_id)
                DO UPDATE SET count = count + 1
                """,
                (manifest.activity_id, event.event_id),
            )
            if event.kind == "score":
                assert normalized_score is not None and event.score_order is not None
                self._update_best_score(
                    connection, manifest.activity_id, event, normalized_score
                )

            rewards = self._apply_progression(
                connection,
                progression,
                session_id=session_id,
                event_record_id=record_id,
                activity_id=manifest.activity_id,
                event_id=event.event_id,
                created_at=timestamp,
            )
            self._prune_reward_ledger(connection)
            return EventReceipt(record_id, False, tuple(rewards))

    def summary(self) -> HistorySummary:
        with self._connect() as connection:
            reward_balances = tuple(
                (str(row["reward_id"]), int(row["balance"]))
                for row in connection.execute(
                    "SELECT reward_id, balance FROM reward_balances ORDER BY reward_id"
                )
            )
            event_counts = tuple(
                (
                    _aggregate_key(str(row["activity_id"]), str(row["event_id"])),
                    int(row["count"]),
                )
                for row in connection.execute(
                    """
                    SELECT activity_id, event_id, count
                      FROM event_counts
                     ORDER BY activity_id, event_id
                    """
                )
            )
            best_scores = tuple(
                (
                    _aggregate_key(str(row["activity_id"]), str(row["event_id"])),
                    float(row["best_score"]),
                )
                for row in connection.execute(
                    """
                    SELECT activity_id, event_id, best_score
                      FROM best_scores
                     ORDER BY activity_id, event_id
                    """
                )
            )
            recent_sessions = tuple(
                RecentSessionSummary(
                    activity_id=str(row["activity_id"]),
                    package_version=str(row["package_version"]),
                    runtime_type=str(row["runtime_type"]),
                    started_at=float(row["started_at"]),
                    ended_at=(
                        None if row["ended_at"] is None else float(row["ended_at"])
                    ),
                    active_duration_seconds=(
                        None
                        if row["active_duration_seconds"] is None
                        else float(row["active_duration_seconds"])
                    ),
                    exit_reason=(
                        None if row["exit_reason"] is None else str(row["exit_reason"])
                    ),
                    ready=bool(row["ready"]),
                )
                for row in connection.execute(
                    """
                    SELECT activity_id, package_version, runtime_type, started_at,
                           ended_at, active_duration_seconds, exit_reason, ready
                      FROM sessions
                     ORDER BY started_at DESC, rowid DESC
                     LIMIT ?
                    """,
                    (self.policy.max_recent_sessions_summary,),
                )
            )
        return HistorySummary(
            reward_balances=reward_balances,
            event_counts=event_counts,
            best_scores=best_scores,
            recent_sessions=recent_sessions,
        )

    def export_state(self) -> dict[str, object]:
        """Return a logical, architecture-neutral history/progression snapshot."""

        with self._connect() as connection:
            sessions = [
                {
                    "session_id": str(row["session_id"]),
                    "activity_id": str(row["activity_id"]),
                    "package_version": str(row["package_version"]),
                    "package_digest": str(row["package_digest"]),
                    "runtime_type": str(row["runtime_type"]),
                    "started_at": float(row["started_at"]),
                    "ready_at": None if row["ready_at"] is None else float(row["ready_at"]),
                    "ended_at": None if row["ended_at"] is None else float(row["ended_at"]),
                    "active_duration_seconds": (
                        None
                        if row["active_duration_seconds"] is None
                        else float(row["active_duration_seconds"])
                    ),
                    "exit_reason": None if row["exit_reason"] is None else str(row["exit_reason"]),
                    "ready": bool(row["ready"]),
                }
                for row in connection.execute(
                    "SELECT * FROM sessions ORDER BY started_at, rowid"
                )
            ]
            events = [
                {
                    "record_id": int(row["record_id"]),
                    "session_id": str(row["session_id"]),
                    "activity_id": str(row["activity_id"]),
                    "event_id": str(row["event_id"]),
                    "idempotency_key": str(row["idempotency_key"]),
                    "score": None if row["score"] is None else float(row["score"]),
                    "payload": json.loads(str(row["payload_json"])),
                    "created_at": float(row["created_at"]),
                }
                for row in connection.execute(
                    "SELECT * FROM events ORDER BY record_id"
                )
            ]
            event_counts = [
                dict(row)
                for row in connection.execute(
                    "SELECT activity_id, event_id, count FROM event_counts ORDER BY activity_id, event_id"
                )
            ]
            best_scores = [
                dict(row)
                for row in connection.execute(
                    "SELECT activity_id, event_id, score_order, best_score FROM best_scores ORDER BY activity_id, event_id"
                )
            ]
            balances = [
                dict(row)
                for row in connection.execute(
                    "SELECT reward_id, balance FROM reward_balances ORDER BY reward_id"
                )
            ]
            ledger = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT ledger_id, session_id, event_record_id, rule_id,
                           reward_id, delta, resulting_balance, created_at
                      FROM reward_ledger ORDER BY ledger_id
                    """
                )
            ]
        return {
            "schema_version": _HISTORY_SCHEMA_VERSION,
            "sessions": sessions,
            "events": events,
            "event_counts": event_counts,
            "best_scores": best_scores,
            "reward_balances": balances,
            "reward_ledger": ledger,
        }

    @property
    def database_path(self) -> Path:
        """Internal-only path used by platform code/tests, never an Activity API."""

        return self._db_path

    def _prepare_root(self) -> None:
        try:
            relative = self._root.relative_to(self.profile.root)
        except ValueError as exc:
            raise HistoryError("profile progress directory escaped profile root") from exc
        if not relative.parts:
            raise HistoryError("profile progress directory must be below profile root")
        current = self.profile.root
        if current.is_symlink():
            raise HistoryError("profile root may not be a symbolic link")
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise HistoryError("profile progress path contains a symbolic link")
        self._root.mkdir(parents=True, exist_ok=True)
        if not self._root.is_dir():
            raise HistoryError("profile progress path is not a directory")
        # Not best-effort, unlike the parent-side normaliser in profiles.py: the
        # child identity must be able to write its own progress, and a silently
        # retained wrong mode turns this boot crash into a later write failure.
        # Setting setgid additionally requires the caller to own the directory
        # (inode_owner_or_capable), so a parent-owned progress root fails here
        # even when the shared profile group would permit the mode. Name the
        # ownership and mode in the error, because a bare EPERM is what made this
        # cost four blind appliance cycles to diagnose.
        try:
            os.chmod(self._root, 0o2770)
        except PermissionError as exc:
            try:
                owner = self._root.stat()
                actual = f"{owner.st_uid}:{owner.st_gid} mode {owner.st_mode & 0o7777:04o}"
            except OSError:  # pragma: no cover - stat is only for diagnostics
                actual = "unreadable"
            raise HistoryError(
                "profile progress directory must be owned by the child identity "
                f"and mode 2770 for the history store to open it; {self._root} is "
                f"{actual} ({exc.strerror})"
            ) from exc

    def _initialize_schema(self) -> None:
        try:
            with self._connect() as connection:
                user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if user_version not in {0, _HISTORY_SCHEMA_VERSION}:
                    raise HistoryError(
                        f"unsupported history database schema version: {user_version}"
                    )
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS sessions(
                        session_id TEXT PRIMARY KEY,
                        activity_id TEXT NOT NULL,
                        package_version TEXT NOT NULL,
                        package_digest TEXT NOT NULL,
                        runtime_type TEXT NOT NULL,
                        started_at REAL NOT NULL,
                        ready_at REAL,
                        ended_at REAL,
                        active_duration_seconds REAL,
                        exit_reason TEXT,
                        ready INTEGER NOT NULL DEFAULT 0 CHECK(ready IN (0, 1))
                    );
                    CREATE INDEX IF NOT EXISTS sessions_started_idx
                        ON sessions(started_at DESC);

                    CREATE TABLE IF NOT EXISTS events(
                        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                        activity_id TEXT NOT NULL,
                        event_id TEXT NOT NULL,
                        idempotency_key TEXT NOT NULL,
                        content_digest TEXT NOT NULL,
                        score REAL,
                        payload_json TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        UNIQUE(session_id, idempotency_key)
                    );
                    CREATE INDEX IF NOT EXISTS events_session_idx
                        ON events(session_id, record_id);

                    CREATE TABLE IF NOT EXISTS event_counts(
                        activity_id TEXT NOT NULL,
                        event_id TEXT NOT NULL,
                        count INTEGER NOT NULL CHECK(count >= 0),
                        PRIMARY KEY(activity_id, event_id)
                    );

                    CREATE TABLE IF NOT EXISTS best_scores(
                        activity_id TEXT NOT NULL,
                        event_id TEXT NOT NULL,
                        score_order TEXT NOT NULL CHECK(score_order IN ('higher_better', 'lower_better')),
                        best_score REAL NOT NULL,
                        PRIMARY KEY(activity_id, event_id)
                    );

                    CREATE TABLE IF NOT EXISTS reward_balances(
                        reward_id TEXT PRIMARY KEY,
                        balance INTEGER NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS reward_ledger(
                        ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                        event_record_id INTEGER NOT NULL REFERENCES events(record_id) ON DELETE CASCADE,
                        rule_id TEXT NOT NULL,
                        reward_id TEXT NOT NULL,
                        delta INTEGER NOT NULL,
                        resulting_balance INTEGER NOT NULL,
                        created_at REAL NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS reward_ledger_session_idx
                        ON reward_ledger(session_id, ledger_id);

                    CREATE TABLE IF NOT EXISTS rule_applications(
                        session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
                        rule_id TEXT NOT NULL,
                        event_record_id INTEGER NOT NULL REFERENCES events(record_id) ON DELETE CASCADE,
                        PRIMARY KEY(session_id, rule_id)
                    );
                    """
                )
                if user_version == 0:
                    connection.execute(f"PRAGMA user_version = {_HISTORY_SCHEMA_VERSION}")
                connection.commit()
            if self._db_path.exists():
                os.chmod(self._db_path, 0o660)
        except sqlite3.DatabaseError as exc:
            raise HistoryError("history database is unavailable or corrupt") from exc

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            connection = sqlite3.connect(
                self._db_path,
                timeout=self.policy.sqlite_busy_timeout_ms / 1000.0,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute(
                f"PRAGMA busy_timeout = {int(self.policy.sqlite_busy_timeout_ms)}"
            )
        except sqlite3.DatabaseError as exc:
            raise HistoryError("cannot open history database") from exc
        try:
            yield connection
        except sqlite3.DatabaseError as exc:
            raise HistoryError("history database operation failed") from exc
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def _session_row(self, connection: sqlite3.Connection, session_id: str) -> sqlite3.Row:
        _validate_identifier(session_id, "session_id", maximum=160)
        row = connection.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise EventValidationError("event session is unknown")
        return row

    def _validate_idempotency_key(self, value: object) -> str:
        if not isinstance(value, str) or not value:
            raise EventValidationError("idempotency_key must be non-empty text")
        if any(character in "\r\n\x00" for character in value):
            raise EventValidationError("idempotency_key contains unsupported characters")
        if len(value.encode("utf-8")) > self.policy.max_idempotency_key_bytes:
            raise EventValidationError("idempotency_key exceeds configured byte limit")
        return value

    def _validate_score(
        self, event: ActivityEventDefinition, score: object
    ) -> float | None:
        if event.kind != "score":
            if score is not None:
                raise EventValidationError("non-score event cannot include a score")
            return None
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise EventValidationError("score event requires a numeric score")
        normalized = float(score)
        if not math.isfinite(normalized):
            raise EventValidationError("score must be finite")
        if abs(normalized) > self.policy.max_score_absolute:
            raise EventValidationError("score exceeds configured magnitude")
        return normalized

    def _validate_payload(self, payload: object) -> tuple[object, str]:
        normalized = {} if payload is None else payload
        try:
            encoded = _portable_json(normalized)
        except (TypeError, ValueError) as exc:
            raise EventValidationError("event payload must be portable JSON") from exc
        if len(encoded.encode("utf-8")) > self.policy.max_event_payload_bytes:
            raise EventValidationError("event payload exceeds configured byte limit")
        return normalized, encoded

    def _update_best_score(
        self,
        connection: sqlite3.Connection,
        activity_id: str,
        event: ActivityEventDefinition,
        score: float,
    ) -> None:
        assert event.score_order is not None
        existing = connection.execute(
            """
            SELECT score_order, best_score FROM best_scores
             WHERE activity_id = ? AND event_id = ?
            """,
            (activity_id, event.event_id),
        ).fetchone()
        if existing is None:
            connection.execute(
                """
                INSERT INTO best_scores(activity_id, event_id, score_order, best_score)
                VALUES(?, ?, ?, ?)
                """,
                (activity_id, event.event_id, event.score_order, score),
            )
            return
        if existing["score_order"] != event.score_order:
            raise HistoryError("stored score ordering disagrees with Activity manifest")
        previous = float(existing["best_score"])
        better = score > previous if event.score_order == "higher_better" else score < previous
        if better:
            connection.execute(
                """
                UPDATE best_scores SET best_score = ?
                 WHERE activity_id = ? AND event_id = ?
                """,
                (score, activity_id, event.event_id),
            )

    def _apply_progression(
        self,
        connection: sqlite3.Connection,
        progression: ProgressionPolicy,
        *,
        session_id: str,
        event_record_id: int,
        activity_id: str,
        event_id: str,
        created_at: float,
    ) -> list[tuple[str, int]]:
        deltas: list[tuple[str, int]] = []
        for rule in progression.matching_rules(activity_id, event_id):
            if rule.once_per_session:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO rule_applications(session_id, rule_id, event_record_id)
                    VALUES(?, ?, ?)
                    """,
                    (session_id, rule.rule_id, event_record_id),
                )
                if cursor.rowcount == 0:
                    continue
            current_row = connection.execute(
                "SELECT balance FROM reward_balances WHERE reward_id = ?",
                (rule.reward_id,),
            ).fetchone()
            current = 0 if current_row is None else int(current_row["balance"])
            resulting = current + rule.reward_delta
            if abs(resulting) > _MAX_SIGNED_64:
                raise HistoryError("reward balance exceeds signed 64-bit range")
            connection.execute(
                """
                INSERT INTO reward_balances(reward_id, balance) VALUES(?, ?)
                ON CONFLICT(reward_id) DO UPDATE SET balance = excluded.balance
                """,
                (rule.reward_id, resulting),
            )
            connection.execute(
                """
                INSERT INTO reward_ledger(
                    session_id, event_record_id, rule_id, reward_id,
                    delta, resulting_balance, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    event_record_id,
                    rule.rule_id,
                    rule.reward_id,
                    rule.reward_delta,
                    resulting,
                    created_at,
                ),
            )
            deltas.append((rule.reward_id, rule.reward_delta))
        return deltas

    def _prune_sessions(self, connection: sqlite3.Connection) -> None:
        total = int(connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0])
        excess = total - self.policy.max_sessions_per_profile
        if excess <= 0:
            return
        rows = connection.execute(
            """
            SELECT session_id FROM sessions
             WHERE ended_at IS NOT NULL
             ORDER BY started_at ASC, rowid ASC
             LIMIT ?
            """,
            (excess,),
        ).fetchall()
        for row in rows:
            connection.execute(
                "DELETE FROM sessions WHERE session_id = ?", (str(row["session_id"]),)
            )

    def _prune_reward_ledger(self, connection: sqlite3.Connection) -> None:
        total = int(connection.execute("SELECT COUNT(*) FROM reward_ledger").fetchone()[0])
        excess = total - self.policy.max_reward_ledger_entries
        if excess <= 0:
            return
        connection.execute(
            """
            DELETE FROM reward_ledger WHERE ledger_id IN (
                SELECT ledger_id FROM reward_ledger ORDER BY ledger_id ASC LIMIT ?
            )
            """,
            (excess,),
        )


def _load_toml(path: Path, label: str) -> Mapping[str, object]:
    try:
        with path.resolve(strict=True).open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise HistoryPolicyError(f"invalid {label} {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise HistoryPolicyError(f"{label} must be a TOML table")
    return raw


def _integer(
    container: Mapping[str, object], key: str, minimum: int, maximum: int
) -> int:
    value = container.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise HistoryPolicyError(f"{key} must be an integer")
    if value < minimum or value > maximum:
        raise HistoryPolicyError(f"{key} is outside its allowed range")
    return value


def _signed_integer(container: Mapping[str, object], key: str) -> int:
    value = container.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise HistoryPolicyError(f"{key} must be an integer")
    if abs(value) > _MAX_SIGNED_64:
        raise HistoryPolicyError(f"{key} exceeds signed 64-bit range")
    return value


def _boolean(container: Mapping[str, object], key: str) -> bool:
    value = container.get(key)
    if not isinstance(value, bool):
        raise HistoryPolicyError(f"{key} must be a boolean")
    return value


def _bounded_identifier(container: Mapping[str, object], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str):
        raise HistoryPolicyError(f"{key} must be text")
    try:
        _validate_identifier(value, key, maximum=160)
    except HistoryError as exc:
        raise HistoryPolicyError(str(exc)) from exc
    return value


def _validate_identifier(value: object, label: str, *, maximum: int) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or not value[0].isalnum()
        or not value[-1].isalnum()
        or any(character not in allowed for character in value)
    ):
        raise HistoryError(f"{label} is not a bounded lower-case identifier")
    return value


def _validate_digest(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise HistoryError("package digest must be a lower-case SHA-256 hex digest")
    return value


def _declared_event(manifest: ActivityManifest, event_id: object) -> ActivityEventDefinition:
    if not isinstance(event_id, str):
        raise EventValidationError("event_id must be text")
    for event in manifest.events:
        if event.event_id == event_id:
            return event
    raise EventValidationError("event is not declared by the live Activity manifest")


def _portable_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _timestamp(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HistoryError("timestamp must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise HistoryError("timestamp must be finite and non-negative")
    return result


def _duration(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise HistoryError("active duration must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise HistoryError("active duration must be finite and non-negative")
    return result


def _aggregate_key(activity_id: str, event_id: str) -> str:
    return f"{activity_id}:{event_id}"

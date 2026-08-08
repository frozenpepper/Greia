from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from greia_platform.history import HistoryError, HistoryPolicy, ProfileHistoryStore
from greia_platform.profiles import ProfileStore


@dataclass(frozen=True, slots=True)
class ParentProgressReader:
    """Bounded, read-only logical progress view for authenticated parent UI.

    This adapter deliberately exposes neither SQLite paths nor raw event payloads
    nor session identifiers. Parent-management integration consumes platform
    summaries, while the history database remains an internal implementation.
    """

    profile_store: ProfileStore
    history_policy: HistoryPolicy

    @classmethod
    def load(cls, root: Path, profile_store: ProfileStore) -> "ParentProgressReader":
        return cls(
            profile_store=profile_store,
            history_policy=HistoryPolicy.load(root / "runtime" / "history-policy.toml"),
        )

    def payload(self, profile_id: str) -> dict[str, object]:
        try:
            context = self.profile_store.context(profile_id)
            summary = ProfileHistoryStore(context, self.history_policy).summary()
        except HistoryError:
            return self.unavailable_payload()
        return {
            "available": True,
            "reward_balances": dict(summary.reward_balances),
            "event_counts": dict(summary.event_counts),
            "best_scores": dict(summary.best_scores),
            "recent_sessions": [
                {
                    "activity_id": session.activity_id,
                    "package_version": session.package_version,
                    "runtime_type": session.runtime_type,
                    "started_at": session.started_at,
                    "ended_at": session.ended_at,
                    "active_duration_seconds": session.active_duration_seconds,
                    "exit_reason": session.exit_reason,
                    "ready": session.ready,
                }
                for session in summary.recent_sessions
            ],
        }

    @staticmethod
    def unavailable_payload() -> dict[str, object]:
        return {
            "available": False,
            "reward_balances": {},
            "event_counts": {},
            "best_scores": {},
            "recent_sessions": [],
        }

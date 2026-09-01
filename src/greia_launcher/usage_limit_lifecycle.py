from __future__ import annotations

from dataclasses import dataclass

from greia_platform.usage_limits import (
    UsageLimitError,
    UsageLimitService,
    UsageLimitStatus,
)


DEFAULT_CHECKPOINT_SECONDS = 15


class ActivityUsageLimitError(RuntimeError):
    """Raised when runtime usage-limit authority cannot be evaluated safely."""


class ActivityUsageLimitReached(ActivityUsageLimitError):
    """Raised when an Activity may not start because today's budget is exhausted."""

    def __init__(self, status: UsageLimitStatus):
        super().__init__("daily Activity time limit reached")
        self.status = status


@dataclass(slots=True)
class _RuntimeUsageSession:
    profile_id: str
    last_accounted_at: float
    status: UsageLimitStatus


class ActivityUsageLimitGuard:
    """Translate monotonic Activity runtime into usage-limit accounting.

    This class intentionally has no process, display or shell authority. The
    Activity supervisor owns lifecycle decisions and supplies monotonic
    timestamps. The guard only performs preflight policy checks, bounded
    checkpoint accounting and final tail accounting through UsageLimitService.

    Keeping the concerns separate prevents the policy store from becoming a
    second process supervisor and makes the same accounting reusable for Python
    and trusted-Chrome Activity runtimes.
    """

    def __init__(
        self,
        service: UsageLimitService,
        *,
        checkpoint_seconds: int = DEFAULT_CHECKPOINT_SECONDS,
    ) -> None:
        if (
            not isinstance(checkpoint_seconds, int)
            or isinstance(checkpoint_seconds, bool)
            or checkpoint_seconds <= 0
        ):
            raise ValueError("checkpoint_seconds must be a positive integer")
        self._service = service
        self._checkpoint_seconds = checkpoint_seconds
        self._sessions: dict[str, _RuntimeUsageSession] = {}

    def preflight(self, profile_id: str) -> UsageLimitStatus:
        """Return current authority or reject an already-exhausted launch."""
        try:
            status = self._service.status(profile_id)
        except (UsageLimitError, OSError, TypeError, ValueError) as exc:
            raise ActivityUsageLimitError("cannot read Activity usage limits") from exc
        if status.exhausted:
            raise ActivityUsageLimitReached(status)
        return status

    def begin(
        self,
        session_id: str,
        profile_id: str,
        started_at: float,
        *,
        initial_status: UsageLimitStatus | None = None,
    ) -> UsageLimitStatus:
        """Begin accounting after a process has successfully launched."""
        if not session_id:
            raise ValueError("session_id must not be empty")
        if session_id in self._sessions:
            raise ActivityUsageLimitError("usage accounting session already exists")
        if started_at < 0:
            raise ValueError("started_at must be non-negative")
        status = initial_status if initial_status is not None else self.preflight(profile_id)
        if status.profile_id != profile_id:
            raise ActivityUsageLimitError("usage status profile does not match Activity profile")
        if status.exhausted:
            raise ActivityUsageLimitReached(status)
        self._sessions[session_id] = _RuntimeUsageSession(
            profile_id=profile_id,
            last_accounted_at=started_at,
            status=status,
        )
        return status

    def checkpoint(
        self,
        session_id: str,
        now: float,
        *,
        force: bool = False,
    ) -> UsageLimitStatus:
        """Account whole elapsed seconds when due and return effective status.

        Fractional seconds deliberately remain in the monotonic residual. This
        avoids double-counting across frequent polls while keeping the durable
        ledger integer-sized and deterministic.
        """
        state = self._session(session_id)
        elapsed = now - state.last_accounted_at
        if elapsed < 0:
            raise ActivityUsageLimitError("monotonic Activity time moved backwards")

        remaining = state.status.effective_remaining_seconds
        due_after = self._checkpoint_seconds
        if remaining is not None:
            # Near exhaustion, check at the remaining whole-second boundary
            # rather than waiting for the normal 15-second checkpoint.
            due_after = min(due_after, max(1, remaining))
        if not force and elapsed < due_after:
            return state.status

        whole_seconds = int(elapsed)
        if whole_seconds <= 0:
            return state.status
        try:
            status = self._service.record_activity_time(
                state.profile_id, whole_seconds
            )
        except (UsageLimitError, OSError, TypeError, ValueError) as exc:
            raise ActivityUsageLimitError("cannot record Activity usage time") from exc
        state.last_accounted_at += whole_seconds
        state.status = status
        return status

    def finish(self, session_id: str, ended_at: float) -> UsageLimitStatus:
        """Account the terminal whole-second tail exactly once and retire state."""
        status = self.checkpoint(session_id, ended_at, force=True)
        self._sessions.pop(session_id, None)
        return status

    def discard(self, session_id: str) -> None:
        """Retire a guard session when lifecycle cleanup cannot finish normally."""
        self._sessions.pop(session_id, None)

    def status(self, session_id: str) -> UsageLimitStatus:
        """Return the last authoritative status without touching persistent state."""
        return self._session(session_id).status

    def _session(self, session_id: str) -> _RuntimeUsageSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise ActivityUsageLimitError("usage accounting session is not active") from exc


__all__ = [
    "ActivityUsageLimitError",
    "ActivityUsageLimitGuard",
    "ActivityUsageLimitReached",
    "DEFAULT_CHECKPOINT_SECONDS",
]

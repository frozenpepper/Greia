from __future__ import annotations

from greia_platform.activities import ActivityManifest
from greia_platform.permissions import ActivityAuthority
from greia_platform.profiles import ProfileContext

from .lifecycle import (
    ActivityExitReason,
    ActivityResult,
    ActivitySession,
    monotonic_now,
    new_activity_session_id,
)
from .runtime_adapter import RuntimeExit
from .supervisor import ActivitySupervisor
from .usage_limit_lifecycle import (
    ActivityUsageLimitError,
    ActivityUsageLimitGuard,
    ActivityUsageLimitReached,
)


class UsageLimitedActivitySupervisor(ActivitySupervisor):
    """Apply daily Activity-time policy at the authoritative lifecycle seam.

    ``ActivitySupervisor`` continues to own processes, display/session cleanup,
    history and graceful/forced termination. This specialization adds only the
    policy decisions that require those lifecycle facts:

    * reject a launch before creating a child process when today's budget is
      already exhausted;
    * begin monotonic accounting only after a process has actually launched;
    * checkpoint bounded elapsed time while the Activity owns the session;
    * request the normal graceful stop path when the budget reaches zero;
    * preserve ``time_limit_reached`` as the semantic exit reason even when an
      uncooperative Activity later requires the existing forced-stop fallback;
    * fail closed as ``platform_failure`` if the authoritative ledger cannot be
      read or updated.

    The usage-limit guard itself intentionally has no process or display
    authority. Keeping that separation prevents screen-time policy from growing
    a second lifecycle implementation and lets trusted-chrome supervisors reuse
    the same behavior through ordinary inheritance.
    """

    def __init__(
        self,
        *args: object,
        usage_limit_guard: ActivityUsageLimitGuard | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._usage_limit_guard = usage_limit_guard
        self._usage_limit_sessions: set[str] = set()
        self._time_limit_stop_sessions: set[str] = set()

    def start(
        self,
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
    ) -> ActivitySession:
        guard = self._usage_limit_guard
        profile_id = profile.profile.profile_id
        if guard is not None:
            try:
                guard.preflight(profile_id)
            except ActivityUsageLimitReached:
                return self._failed_launch_session(
                    manifest,
                    profile,
                    authority,
                    session_id=new_activity_session_id(),
                    reason=ActivityExitReason.TIME_LIMIT_REACHED,
                )
            except ActivityUsageLimitError:
                return self._failed_launch_session(
                    manifest,
                    profile,
                    authority,
                    session_id=new_activity_session_id(),
                    reason=ActivityExitReason.PLATFORM_FAILURE,
                )

        session = super().start(manifest, profile, authority)
        if guard is None or session.result is not None:
            return session

        # Read authority again after process creation. Parent policy may have
        # changed while runtime/display preparation was in progress, and a
        # stale preflight must not grant an extra Activity session.
        try:
            guard.begin(session.session_id, profile_id, session.started_at)
        except ActivityUsageLimitReached:
            self._time_limit_stop_sessions.add(session.session_id)
            return self._stop_for_time_limit(session)
        except ActivityUsageLimitError:
            guard.discard(session.session_id)
            result = super().force_stop(session, ActivityExitReason.PLATFORM_FAILURE)
            if result is not None:
                session.result = result
            return session

        self._usage_limit_sessions.add(session.session_id)
        return session

    def poll(self, session: ActivitySession) -> ActivityResult | None:
        if session.result is not None:
            return session.result

        guard = self._usage_limit_guard
        if guard is not None and session.session_id in self._usage_limit_sessions:
            try:
                status = guard.checkpoint(session.session_id, monotonic_now())
            except ActivityUsageLimitError:
                self._usage_limit_sessions.discard(session.session_id)
                guard.discard(session.session_id)
                self._time_limit_stop_sessions.discard(session.session_id)
                return super().force_stop(session, ActivityExitReason.PLATFORM_FAILURE)
            if (
                status.exhausted
                and session.session_id not in self._time_limit_stop_sessions
            ):
                self._time_limit_stop_sessions.add(session.session_id)
                return self._stop_for_time_limit(session)

        return super().poll(session)

    def _stop_for_time_limit(self, session: ActivitySession) -> ActivityResult | None:
        """Use the normal stop marker/grace period, never a policy-side kill."""
        return super().request_stop(session)

    def _finish_session(
        self,
        session: ActivitySession,
        runtime_exit: RuntimeExit,
        ended_at: float,
    ) -> ActivityResult:
        guard = self._usage_limit_guard
        accounting_failed = False
        if guard is not None and session.session_id in self._usage_limit_sessions:
            try:
                guard.finish(session.session_id, ended_at)
            except ActivityUsageLimitError:
                accounting_failed = True
                guard.discard(session.session_id)
            finally:
                self._usage_limit_sessions.discard(session.session_id)

        if accounting_failed:
            session.forced_reason = ActivityExitReason.PLATFORM_FAILURE
        elif session.session_id in self._time_limit_stop_sessions:
            # The base supervisor may have temporarily marked FORCED_STOP after
            # the grace period. Preserve the parent-facing semantic cause while
            # still using that existing kill/cleanup mechanism underneath.
            session.forced_reason = ActivityExitReason.TIME_LIMIT_REACHED

        try:
            return super()._finish_session(session, runtime_exit, ended_at)
        finally:
            self._time_limit_stop_sessions.discard(session.session_id)


__all__ = ["UsageLimitedActivitySupervisor"]

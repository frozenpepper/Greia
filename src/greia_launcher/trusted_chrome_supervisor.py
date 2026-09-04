from __future__ import annotations

from greia_platform.activities import ActivityManifest
from greia_platform.permissions import ActivityAuthority
from greia_platform.profiles import ProfileContext

from .lifecycle import ActivityExitReason, ActivityResult, ActivitySession, ActivitySessionState
from .system_chrome import (
    SystemChromeCoordinator,
    SystemChromeError,
    SystemChromeLease,
    SystemChromeNavigationBridge,
    SystemChromePhase,
)
from .usage_limited_supervisor import UsageLimitedActivitySupervisor


class TrustedChromeActivitySupervisor(UsageLimitedActivitySupervisor):
    """Bind mandatory Greia Home chrome to the authoritative Activity lifecycle.

    The usage-limited base supervisor remains the owner of process/runtime/
    display/history semantics and daily Activity-time enforcement. This narrow
    specialization adds the trusted system-chrome lease beside the display
    lease:

    * prepare after the Activity session identity exists but before READY;
    * show only after the display session has successfully presented READY;
    * poll protected navigation outside Activity input authority;
    * route Home and time-limit expiry through the same graceful/forced stop
      lifecycle;
    * hide/abort on every normal, crash and failed-launch cleanup path.

    No Activity pixels or high-rate ordinary input pass through this class.
    """

    def __init__(
        self,
        *args: object,
        system_chrome_coordinator: SystemChromeCoordinator | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._system_chrome_coordinator = system_chrome_coordinator
        self._system_chrome_leases: dict[str, SystemChromeLease] = {}
        self._system_navigation_bridge = (
            None
            if system_chrome_coordinator is None
            else SystemChromeNavigationBridge(system_chrome_coordinator, self)
        )

    def start(
        self,
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
    ) -> ActivitySession:
        session = super().start(manifest, profile, authority)
        coordinator = self._system_chrome_coordinator
        if coordinator is None or session.result is not None:
            return session
        try:
            # Mandatory Home is always enabled. Back is enabled when the activity
            # supports/requires back navigation (e.g. hierarchical browsing).
            back_needed = manifest.activity_id in {
                "org.greia.enciclopedia",
            }
            lease = coordinator.prepare(session.session_id, back_available=back_needed)
        except SystemChromeError:
            result = self.force_stop(session, ActivityExitReason.PLATFORM_FAILURE)
            if result is not None:
                session.result = result
            return session
        self._system_chrome_leases[session.session_id] = lease
        return session

    def poll(self, session: ActivitySession) -> ActivityResult | None:
        result = super().poll(session)
        if result is not None:
            return result
        if session.state not in {ActivitySessionState.RUNNING, ActivitySessionState.STOPPING}:
            return None
        lease = self._system_chrome_leases.get(session.session_id)
        bridge = self._system_navigation_bridge
        if lease is None or bridge is None:
            return None
        try:
            bridge.poll(lease, session)
        except SystemChromeError:
            forced = self.force_stop(session, ActivityExitReason.PLATFORM_FAILURE)
            return forced if forced is not None else session.result
        # request_stop() may have completed the process during the nested poll
        # initiated by SystemChromeNavigationBridge.
        return session.result

    def _record_ready(self, session: ActivitySession, *, present_display: bool) -> bool:
        if not super()._record_ready(session, present_display=present_display):
            return False
        if not present_display:
            return True
        lease = self._system_chrome_leases.get(session.session_id)
        coordinator = self._system_chrome_coordinator
        if lease is None or coordinator is None:
            return coordinator is None
        try:
            coordinator.activity_ready(lease)
        except SystemChromeError:
            return False
        return True

    def _cleanup_display_session(self, session_id: str) -> bool:
        chrome_clean = self._cleanup_system_chrome(session_id)
        display_clean = super()._cleanup_display_session(session_id)
        return chrome_clean and display_clean

    def _cleanup_system_chrome(self, session_id: str) -> bool:
        lease = self._system_chrome_leases.pop(session_id, None)
        if lease is None:
            return True
        coordinator = self._system_chrome_coordinator
        bridge = self._system_navigation_bridge
        if bridge is not None:
            bridge.clear(lease)
        if coordinator is None:
            return False
        try:
            if coordinator.snapshot.phase in {
                SystemChromePhase.PREPARED,
                SystemChromePhase.VISIBLE,
            }:
                coordinator.activity_ended(lease)
            elif coordinator.snapshot.phase is SystemChromePhase.FAILED:
                coordinator.abort(lease)
        except (SystemChromeError, TypeError):
            return False
        return coordinator.snapshot.phase is SystemChromePhase.HIDDEN


__all__ = ["TrustedChromeActivitySupervisor"]

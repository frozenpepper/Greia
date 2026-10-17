from typing import Protocol

from greia_platform.activities import ActivityManifest
from greia_platform.permissions import ActivityAuthority
from greia_platform.profiles import ProfileContext


class ControllerGuideSource(Protocol):
    def poll_guide_button(self) -> bool: ...


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

    * prepare and show as soon as the Activity session identity exists, so
      Home is present from the launch card onward (ADR 0019 "always present
      while the Activity is visible"); restack it above the Activity surface
      when that surface maps and again at READY;
    * poll protected navigation outside Activity input authority, also while
      STARTING: Home before READY cancels the launch (bounded forced stop of
      a process that has presented nothing of its own);
    * route Home and time-limit expiry through the same graceful/forced stop
      lifecycle;
    * hide/abort on every normal, crash and failed-launch cleanup path.

    No Activity pixels or high-rate ordinary input pass through this class.
    """

    def __init__(
        self,
        *args: object,
        system_chrome_coordinator: SystemChromeCoordinator | None = None,
        controller_set: ControllerGuideSource | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._system_chrome_coordinator = system_chrome_coordinator
        self._controller_set = controller_set
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
        try:
            coordinator.launch_started(lease)
        except SystemChromeError:
            # Fail closed: never run an Activity whose Home cannot be shown.
            result = self.force_stop(session, ActivityExitReason.PLATFORM_FAILURE)
            if result is not None:
                session.result = result
        return session

    def paint_launch_home(self, surface: object, pygame: object) -> object | None:
        """Paint Home on the Shell's launch screen; return its hit box or None."""

        coordinator = self._system_chrome_coordinator
        if coordinator is None:
            return None
        return coordinator.paint_launch_picture(surface, pygame)

    def cancel_launch(self, session: ActivitySession) -> ActivityResult | None:
        """Home before READY: end the launch now through lifecycle authority.

        The Activity has not presented a frame of its own, so there is no
        child work to save and it may not be polling the graceful stop marker
        yet. A READY session (or one already past READY) keeps the normal
        graceful stop; the forced path is the same bounded one Home always
        falls back to.
        """

        if session.result is not None:
            return session.result
        if session.ready_at is not None or session.state is not ActivitySessionState.STARTING:
            return self.request_stop(session)
        return self.force_stop(session, ActivityExitReason.FORCED_STOP)

    def poll(self, session: ActivitySession) -> ActivityResult | None:
        result = super().poll(session)
        if result is not None:
            return result
        if session.state not in {
            ActivitySessionState.STARTING,
            ActivitySessionState.RUNNING,
            ActivitySessionState.STOPPING,
        }:
            return None
        controller_set = self._controller_set
        if (
            controller_set is not None
            and session.state is not ActivitySessionState.STOPPING
            and controller_set.poll_guide_button()
        ):
            self.cancel_launch(session)
            return session.result
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

    def ensure_system_chrome_visible(self, session: ActivitySession) -> bool:
        """Restack mandatory Home/Back above a newly raised surface.

        Used after a trusted Shell modal is raised and, while STARTING, once
        the Activity's window has mapped over the chrome shown at launch.
        """
        if self.active_session is not session or session.state not in {
            ActivitySessionState.STARTING,
            ActivitySessionState.RUNNING,
        }:
            return False
        lease = self._system_chrome_leases.get(session.session_id)
        coordinator = self._system_chrome_coordinator
        if lease is None or coordinator is None:
            return coordinator is None
        try:
            coordinator.ensure_visible(lease)
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

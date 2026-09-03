from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from greia_platform.display_metrics import DisplayMetrics, PhysicalUiPolicy
from greia_platform.responsive_layout import AdaptiveGridPolicy
from greia_platform.system_chrome import SystemNavigationAction

from .lifecycle import ActivityResult, ActivitySession


TRUSTED_ACTION_MINIMUM_MM = 10.0
"""One shared physical-size floor for semantic action targets (millimetres).

Trusted Home/Back geometry, launcher/profile essential controls, shared
collection minimums — and later the installer (T07) and on-device Parent (T08)
seams — all convert this single value through
: meth:`PhysicalUiPolicy.minimum_pixels`. T07/T08 must import this constant and
:func:`resolve_trusted_action_minimum_px` unchanged; do not fork a second floor
helper. The value is a physical minimum only: it never scales a layout
globally and never moves Home/Back by itself.
"""


def resolve_trusted_action_minimum_px(
    metrics: Any,
    *,
    fallback_px: Any,
) -> int:
    """Return the pixel minimum for one semantic action target.

    ``fallback_px`` is the existing conservative pixel size for the target; it
    is returned unchanged when ``metrics`` is missing, unknown, or malformed.
    Trustworthy high-density metrics raise the result via the shared
    :data:`TRUSTED_ACTION_MINIMUM_MM` floor; trustworthy low-density metrics
    never shrink it below ``fallback_px``. The result is always a bounded
    integer, so malformed input fails soft instead of producing absurd
    geometry. ``metrics`` is injected by the composition owner; this helper
    never probes hardware and never parses configuration.
    """
    try:
        sanitized_fallback = PhysicalUiPolicy.minimum_pixels(
            TRUSTED_ACTION_MINIMUM_MM,
            fallback_px=fallback_px,
            metrics=None,
        )
    except Exception:
        sanitized_fallback = 8
    if not isinstance(metrics, DisplayMetrics):
        return sanitized_fallback
    try:
        physical = PhysicalUiPolicy.minimum_pixels(
            TRUSTED_ACTION_MINIMUM_MM,
            fallback_px=sanitized_fallback,
            metrics=metrics,
        )
    except Exception:
        return sanitized_fallback
    return max(sanitized_fallback, physical)


def collection_policy_for_metrics(
    metrics: Any,
    *,
    minimum_item_px: int = 72,
    preferred_item_px: int = 160,
    maximum_item_px: int = 220,
    minimum_gap_px: int = 6,
    maximum_gap_px: int = 24,
    maximum_columns: int = 6,
    maximum_rows: int = 3,
) -> AdaptiveGridPolicy:
    """Build a collection grid policy with the shared physical floor applied.

    This is the ``DisplayMetrics → PhysicalUiPolicy → pixel minimum →
    AdaptiveGridPolicy(...)`` composition seam: only ``minimum_item_px`` is
    raised by :func:`resolve_trusted_action_minimum_px`. Preferred/maximum
    sizes, gap bounds, and grid bounds pass through untouched, so decoration
    and layout structure are never globally scaled. When the physical floor
    would exceed ``preferred_item_px`` it is capped there to keep the policy
    valid; the grid's own constrained-degradation path then handles the rest.
    Malformed ``metrics`` yields the base policy unchanged.
    """
    floored = resolve_trusted_action_minimum_px(
        metrics, fallback_px=minimum_item_px
    )
    try:
        preferred = int(preferred_item_px)
    except (TypeError, ValueError):
        preferred = 160
    minimum = min(floored, max(1, preferred))
    return AdaptiveGridPolicy(
        minimum_item_px=minimum,
        preferred_item_px=preferred_item_px,
        maximum_item_px=maximum_item_px,
        minimum_gap_px=minimum_gap_px,
        maximum_gap_px=maximum_gap_px,
        maximum_columns=maximum_columns,
        maximum_rows=maximum_rows,
    )


class SystemChromeError(RuntimeError):
    """Raised when Greia cannot preserve trusted Activity navigation chrome."""


class SystemChromePhase(StrEnum):
    HIDDEN = "hidden"
    PREPARED = "prepared"
    VISIBLE = "visible"
    FAILED = "failed"


class SystemChromeBackend(Protocol):
    """Backend-specific trusted overlay/input implementation.

    Implementations sit outside Activity authority. They must render the
    canonical Home control, optionally Back, and consume input in the protected
    chrome region before Activity input dispatch.
    """

    @property
    def backend_id(self) -> str: ...

    def prepare(self, session_id: str, *, back_available: bool) -> None: ...

    def show(self, session_id: str) -> None: ...

    def poll_action(self, session_id: str) -> SystemNavigationAction | None: ...

    def hide(self, session_id: str) -> None: ...


class ActivityStopController(Protocol):
    """Narrow lifecycle authority required by trusted system navigation."""

    def request_stop(self, session: ActivitySession) -> ActivityResult | None: ...


@dataclass(frozen=True, slots=True)
class SystemChromeLease:
    """Exact-object ownership token for one Activity chrome generation."""

    session_id: str
    generation: int
    back_available: bool


@dataclass(frozen=True, slots=True)
class SystemChromeSnapshot:
    phase: SystemChromePhase
    session_id: str | None
    generation: int
    back_available: bool
    failure: str | None = None


@dataclass(frozen=True, slots=True)
class SystemNavigationRequest:
    """One Greia-owned request to end an Activity and choose a Shell destination."""

    session_id: str
    action: SystemNavigationAction


class SystemChromeCoordinator:
    """Own trusted Home/Back chrome independently of Activity runtimes.

    The coordinator deliberately knows nothing about Python, HTML, browser
    history or Activity-defined controls. Its only job is to preserve one
    platform-owned chrome instance around the active Activity surface and to
    return validated Greia navigation actions to the launcher.
    """

    def __init__(self, backend: SystemChromeBackend):
        backend_id = backend.backend_id
        if not isinstance(backend_id, str) or not backend_id.strip():
            raise TypeError("system chrome backend_id must be non-empty text")
        self._backend = backend
        self._backend_id = backend_id.strip()
        self._phase = SystemChromePhase.HIDDEN
        self._session_id: str | None = None
        self._generation = 0
        self._lease: SystemChromeLease | None = None
        self._back_available = False
        self._failure: str | None = None

    @property
    def backend_id(self) -> str:
        return self._backend_id

    @property
    def snapshot(self) -> SystemChromeSnapshot:
        return SystemChromeSnapshot(
            phase=self._phase,
            session_id=self._session_id,
            generation=self._generation,
            back_available=self._back_available,
            failure=self._failure,
        )

    def prepare(self, session_id: str, *, back_available: bool) -> SystemChromeLease:
        session_id = _session_id(session_id)
        if self._phase is not SystemChromePhase.HIDDEN:
            raise SystemChromeError(
                f"cannot prepare system chrome while phase is {self._phase.value}"
            )
        self._session_id = session_id
        self._back_available = bool(back_available)
        self._failure = None
        try:
            self._backend.prepare(session_id, back_available=self._back_available)
        except Exception as exc:
            failure = f"prepare: {exc}"
            # No lease has been issued yet, so there is no later caller that can
            # safely recover this generation through abort(). Give the backend
            # one bounded rollback attempt now. A successfully cleaned failed
            # launch must not poison every later Activity until Shell restart.
            self._phase = SystemChromePhase.FAILED
            self._failure = failure
            if self._attempt_hide(session_id):
                self._reset_hidden()
            raise SystemChromeError("system chrome backend could not prepare") from exc

        self._generation += 1
        lease = SystemChromeLease(session_id, self._generation, self._back_available)
        self._lease = lease
        self._phase = SystemChromePhase.PREPARED
        return lease

    def activity_ready(self, lease: SystemChromeLease) -> None:
        self._require_lease(lease)
        if self._phase is not SystemChromePhase.PREPARED:
            raise SystemChromeError(
                f"cannot show system chrome while phase is {self._phase.value}"
            )
        try:
            self._backend.show(lease.session_id)
        except Exception as exc:
            self._phase = SystemChromePhase.FAILED
            self._failure = f"show: {exc}"
            self._attempt_hide(lease.session_id)
            raise SystemChromeError("system chrome backend could not show") from exc
        self._phase = SystemChromePhase.VISIBLE

    def poll_action(self, lease: SystemChromeLease) -> SystemNavigationAction | None:
        self._require_lease(lease)
        if self._phase is not SystemChromePhase.VISIBLE:
            return None
        try:
            action = self._backend.poll_action(lease.session_id)
        except Exception as exc:
            self._phase = SystemChromePhase.FAILED
            self._failure = f"poll: {exc}"
            raise SystemChromeError("system chrome backend input failed") from exc
        if action is None:
            return None
        if not isinstance(action, SystemNavigationAction):
            self._phase = SystemChromePhase.FAILED
            self._failure = "poll: invalid action"
            raise SystemChromeError("system chrome backend returned an invalid action")
        if action is SystemNavigationAction.BACK and not lease.back_available:
            self._phase = SystemChromePhase.FAILED
            self._failure = "poll: unavailable back action"
            raise SystemChromeError("system chrome backend emitted unavailable Back")
        return action

    def activity_ended(self, lease: SystemChromeLease) -> None:
        self._require_lease(lease)
        if self._phase not in {SystemChromePhase.PREPARED, SystemChromePhase.VISIBLE}:
            raise SystemChromeError(
                f"cannot hide system chrome while phase is {self._phase.value}"
            )
        try:
            self._backend.hide(lease.session_id)
        except Exception as exc:
            self._phase = SystemChromePhase.FAILED
            self._failure = f"hide: {exc}"
            raise SystemChromeError("system chrome backend could not hide") from exc
        self._reset_hidden()

    def abort(self, lease: SystemChromeLease) -> None:
        self._require_lease(lease)
        if self._phase is SystemChromePhase.HIDDEN:
            return
        if not self._attempt_hide(lease.session_id):
            raise SystemChromeError("system chrome backend could not recover")
        self._reset_hidden()

    def _attempt_hide(self, session_id: str) -> bool:
        try:
            self._backend.hide(session_id)
        except Exception:
            return False
        return True

    def _reset_hidden(self) -> None:
        self._phase = SystemChromePhase.HIDDEN
        self._session_id = None
        self._lease = None
        self._back_available = False
        self._failure = None

    def _require_lease(self, lease: SystemChromeLease) -> None:
        if lease is not self._lease:
            raise SystemChromeError("stale or foreign system chrome lease")
        if lease.session_id != self._session_id or lease.generation != self._generation:
            raise SystemChromeError("system chrome lease does not match active generation")


class SystemChromeNavigationBridge:
    """Translate trusted chrome input into Greia's existing stop lifecycle.

    Home and Back both end the current Activity through the same authoritative
    lifecycle. Exactly one navigation request can be retained because Greia
    permits one active Activity; this keeps the bridge naturally hard-bounded.
    The Activity never receives or vetoes the navigation intent.
    """

    def __init__(
        self,
        coordinator: SystemChromeCoordinator,
        stop_controller: ActivityStopController,
    ) -> None:
        self._coordinator = coordinator
        self._stop_controller = stop_controller
        self._request: tuple[int, SystemNavigationRequest] | None = None

    def poll(
        self,
        lease: SystemChromeLease,
        session: ActivitySession,
    ) -> SystemNavigationRequest | None:
        if session.session_id != lease.session_id:
            raise SystemChromeError("system chrome lease/session identity mismatch")
        if self._request is not None:
            generation, existing = self._request
            if generation == lease.generation:
                return existing
            raise SystemChromeError("uncleared system navigation request from older generation")
        action = self._coordinator.poll_action(lease)
        if action is None:
            return None
        request = SystemNavigationRequest(session.session_id, action)
        self._request = (lease.generation, request)
        self._stop_controller.request_stop(session)
        return request

    def clear(self, lease: SystemChromeLease) -> None:
        """Retire the remembered navigation request after Activity cleanup."""

        if self._request is not None and self._request[0] == lease.generation:
            self._request = None


def _session_id(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("system chrome session_id must be text")
    value = value.strip()
    if not value or len(value) > 128 or any(ch.isspace() or ch == "\x00" for ch in value):
        raise ValueError("invalid system chrome session_id")
    return value

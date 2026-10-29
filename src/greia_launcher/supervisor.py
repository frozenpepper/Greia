from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path
from typing import Callable, Mapping, Protocol

from greia_platform.activities import ActivityManifest
from greia_platform.creation_access import CreationSessionAccess
from greia_platform.creation_capacity import VolumeBudget
from greia_platform.creations import CreationLibrary, CreationLibraryError
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.history import (
    HistoryCapacityError,
    HistoryError,
    PlatformHistoryService,
    SessionHistoryRecorder,
    UnrecordedSessionHistory,
)
from greia_platform.permissions import ActivityAuthority
from greia_platform.profiles import ProfileContext, ProfileError
from greia_platform.storage import ActivityStorageService, StorageError
from greia_platform.system_language import resolve_child_locale, resolve_device_locale

from .creation_selection import SelectionRequest
from .display_session import (
    DisplaySessionCoordinator,
    DisplaySessionError,
    DisplaySessionLease,
)
from .event_broker import (
    SANDBOX_EVENT_ROOT,
    ActivityEventBroker,
)
from .lifecycle import (
    ActivityLifecycleControl,
    ActivityExitReason,
    ActivityResult,
    ActivitySession,
    ActivitySessionState,
    monotonic_now,
    new_activity_session_id,
)
from .runtime_adapter import (
    PythonRuntimeAdapter,
    RuntimeAdapterError,
    RuntimeCommand,
    RuntimeExit,
    RuntimeExitKind,
    RuntimeInvocation,
    RuntimeLaunchAdapter,
    RuntimeLaunchPreparation,
    RuntimeManager,
)
from .storage_broker import (
    SANDBOX_STORAGE_ROOT,
    ActivityStorageBroker,
)


SANDBOX_ACTIVITY_ROOT = Path("/run/greia-activity-data")
SANDBOX_CUSTOMIZATION_ROOT = Path("/run/greia-customization")
logger = logging.getLogger(__name__)

PRODUCTION_ROOT = Path("/opt/greia-os")
PRODUCTION_BWRAP = Path("/usr/bin/bwrap")
_DEVELOPMENT_CAPABILITIES = frozenset(
    {
        "audio.basic",
        "display",
        "keyboard",
        "network",
        "pointer",
        "power.controlled_shutdown",
        "removable_media",
        "touch",
    }
)
_DISPLAY_TRANSPORT_ENVIRONMENT = frozenset(
    {
        "DISPLAY",
        "SDL_VIDEODRIVER",
        "WAYLAND_DISPLAY",
        "XAUTHORITY",
        "XDG_RUNTIME_DIR",
    }
)


class ActivityLifecycleError(RuntimeError):
    """Raised when the platform cannot preserve the one-Activity lifecycle."""


StorageBrokerFactory = Callable[..., ActivityStorageBroker]
EventBrokerFactory = Callable[..., ActivityEventBroker]


class SessionResource(Protocol):
    def stop(self) -> None: ...


class ActivitySupervisor:
    """Own one Activity process from launch through cleanup.

    Runtime selection and runtime/device compatibility are delegated to one
    RuntimeManager. This supervisor remains the runtime-neutral lifecycle and
    sandbox owner: it consumes platform-issued ActivityAuthority rather than
    trusting Activity environment or manifest claims as grants.

    When a DisplaySessionCoordinator is injected, the supervisor composes its
    lifecycle observations with the display-side ownership state machine. The
    coordinator still owns display mechanics; the supervisor only ensures that
    prepare/present/restore occur at the same authoritative platform session
    boundaries as READY, process exit and normalized history.
    """

    def __init__(
        self,
        python_executable: Path | None = None,
        *,
        sandbox_executable: Path | None = None,
        require_sandbox: bool | None = None,
        ready_timeout_seconds: float = 15.0,
        graceful_stop_seconds: float = 2.0,
        runtime_manager: RuntimeManager | None = None,
        runtime_adapters: Mapping[str, RuntimeLaunchAdapter] | None = None,
        storage_service: ActivityStorageService | None = None,
        storage_broker_factory: StorageBrokerFactory = ActivityStorageBroker.start,
        history_service: PlatformHistoryService | None = None,
        event_broker_factory: EventBrokerFactory = ActivityEventBroker.start,
        display_coordinator: DisplaySessionCoordinator | None = None,
    ):
        if ready_timeout_seconds <= 0:
            raise ValueError("ready_timeout_seconds must be positive")
        if graceful_stop_seconds <= 0:
            raise ValueError("graceful_stop_seconds must be positive")
        if runtime_manager is not None and runtime_adapters is not None:
            raise ValueError("provide runtime_manager or runtime_adapters, not both")

        self._sandbox_executable = sandbox_executable
        self._require_sandbox_override = require_sandbox
        if runtime_manager is None:
            if self._sandbox_required():
                raise ActivityLifecycleError(
                    "installed ActivitySupervisor requires an injected HAL-backed RuntimeManager"
                )
            adapters = dict(runtime_adapters or {})
            adapters.setdefault("python", PythonRuntimeAdapter(python_executable))
            runtime_manager = RuntimeManager(
                adapters,
                DeviceCapabilityService.static(
                    _DEVELOPMENT_CAPABILITIES,
                    source_id="supervisor-development-static",
                ),
            )
        if self._sandbox_required() and storage_service is None:
            raise ActivityLifecycleError(
                "installed ActivitySupervisor requires an injected ActivityStorageService"
            )
        if self._sandbox_required() and history_service is None:
            raise ActivityLifecycleError(
                "installed ActivitySupervisor requires an injected PlatformHistoryService"
            )
        self._runtime_manager = runtime_manager
        self._storage_service = storage_service
        self._volume_budget = (
            storage_service.volume_budget
            if storage_service is not None
            else VolumeBudget()
        )
        self._storage_broker_factory = storage_broker_factory
        self._history_service = history_service
        self._event_broker_factory = event_broker_factory
        self._display_coordinator = display_coordinator
        self._history_stores: dict[str, SessionHistoryRecorder] = {}
        self._session_resources: dict[str, tuple[SessionResource, ...]] = {}
        self._runtime_preparations: dict[str, RuntimeLaunchPreparation] = {}
        self._display_leases: dict[str, DisplaySessionLease] = {}
        self._ready_timeout_seconds = ready_timeout_seconds
        self._graceful_stop_seconds = graceful_stop_seconds
        self._active_session: ActivitySession | None = None

    @property
    def active_session(self) -> ActivitySession | None:
        session = self._active_session
        if session is not None and not session.terminal:
            return session
        return None

    def _active_creation_broker(self, session: ActivitySession) -> ActivityStorageBroker | None:
        """Only a currently-running trusted Activity session may own a picker."""
        if self.active_session is not session or session.state is not ActivitySessionState.RUNNING:
            return None
        return next(
            (resource for resource in self._session_resources.get(session.session_id, ())
             if isinstance(resource, ActivityStorageBroker)),
            None,
        )

    def pending_creation_selection(self, session: ActivitySession) -> SelectionRequest | None:
        """Shell-only inspection, not an Activity-visible enumeration operation."""
        broker = self._active_creation_broker(session)
        return None if broker is None else broker.pending_creation_selection()

    def enable_creation_picker(self, session: ActivitySession) -> None:
        """Enable requests only after the trusted display host has a real lease."""
        broker = self._active_creation_broker(session)
        if broker is None:
            raise ActivityLifecycleError("no live creation-picker session")
        broker.enable_creation_picker()

    def disable_creation_picker(self, session: ActivitySession) -> None:
        broker = self._active_creation_broker(session)
        if broker is not None:
            broker.disable_creation_picker()

    def complete_creation_selection(
        self, session: ActivitySession, request_id: str, creation_id: str
    ) -> str:
        """Shell-only completion after a trusted UI confirmed child intent."""
        broker = self._active_creation_broker(session)
        if broker is None:
            raise ActivityLifecycleError("no live creation-picker session")
        return broker.complete_creation_selection(request_id, creation_id)

    def cancel_creation_selection(self, session: ActivitySession, request_id: str) -> None:
        """Shell-owned cancellation on Back/Home/display failure."""
        broker = self._active_creation_broker(session)
        if broker is None:
            raise ActivityLifecycleError("no live creation-picker session")
        broker.cancel_creation_selection(request_id)

    def start(
        self,
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
    ) -> ActivitySession:
        if self.active_session is not None:
            raise ActivityLifecycleError("only one Activity may run at a time")
        if authority.activity_id != manifest.activity_id:
            raise ActivityLifecycleError("Activity authority identity does not match manifest")
        session_id = new_activity_session_id()
        history_store: SessionHistoryRecorder | None = None
        if self._history_service is not None:
            try:
                history_store = self._history_service.open(profile)
                history_store.start_session(
                    manifest,
                    session_id=session_id,
                    package_digest=authority.package_digest,
                )
            except HistoryCapacityError as exc:
                # The volume is past its growth headroom: keep the child able
                # to play, but record nothing (fail-soft, never fail-open).
                logger.warning(
                    "Launching %s as an unrecorded session; progression and "
                    "history are paused until space is freed: %s",
                    manifest.activity_id,
                    exc,
                )
                history_store = UnrecordedSessionHistory(
                    profile, self._history_service.history_policy
                )
            except HistoryError:
                return self._failed_launch_session(
                    manifest,
                    profile,
                    authority,
                    session_id=session_id,
                    reason=ActivityExitReason.PLATFORM_FAILURE,
                )
        if not frozenset(manifest.required_capabilities).issubset(
            authority.effective_capabilities
        ):
            return self._failed_launch_session(
                manifest, profile, authority, session_id=session_id, history_store=history_store
            )

        try:
            preparation = self._runtime_manager.prepare_launch(
                manifest,
                expected_device_snapshot_token=authority.device_snapshot_token,
                package_trust=authority.package_trust,
            )
        except RuntimeAdapterError:
            return self._failed_launch_session(
                manifest, profile, authority, session_id=session_id, history_store=history_store
            )
        runtime_command = preparation.command

        sandboxed = self._sandbox_required()
        try:
            host_activity_data = profile.activity_data_dir(manifest.activity_id)
        except (ProfileError, OSError) as exc:
            # A profile-tree contract violation fails this one launch (and
            # closes its history row), never the child Shell.
            logger.error(
                "Activity %s data directory is unusable; launch refused: %s",
                manifest.activity_id,
                str(exc)[:400],
            )
            return self._failed_launch_session(
                manifest,
                profile,
                authority,
                session_id=session_id,
                history_store=history_store,
                reason=ActivityExitReason.PLATFORM_FAILURE,
            )
        child_activity_data = SANDBOX_ACTIVITY_ROOT if sandboxed else host_activity_data

        sandbox: Path | None = None
        if sandboxed:
            sandbox = self._resolve_sandbox()
            if not sandbox.is_file() or not os.access(sandbox, os.X_OK):
                return self._failed_launch_session(
                    manifest,
                    profile,
                    authority,
                    session_id=session_id,
                    history_store=history_store,
                )

        try:
            lifecycle_binding = self._runtime_manager.create_lifecycle_binding(
                preparation,
                session_id,
                host_activity_data,
                child_activity_data,
            )
        except (RuntimeAdapterError, OSError):
            return self._failed_launch_session(
                manifest, profile, authority, session_id=session_id, history_store=history_store
            )
        control = lifecycle_binding.control

        resources: tuple[SessionResource, ...] = ()
        storage_broker: ActivityStorageBroker | None = None
        if self._storage_service is not None:
            try:
                storage = self._storage_service.open(
                    profile,
                    manifest.activity_id,
                    schema_version=manifest.storage_schema_version,
                    package_version=manifest.version,
                )
                storage_broker = self._storage_broker_factory(
                    storage, session_id, sandboxed=sandboxed
                )
                if manifest.creations_produces or manifest.creations_consumes:
                    if not isinstance(storage_broker, ActivityStorageBroker):
                        raise ActivityLifecycleError(
                            "creation-aware Activity requires the trusted storage broker"
                        )
                    access = CreationSessionAccess(
                        library=CreationLibrary(
                            profile.creations_dir,
                            volume_budget=self._volume_budget,
                        ),
                        storage=storage,
                        manifest=manifest,
                        authority=authority,
                        session_id=session_id,
                    )
                    storage_broker.bind_creations(access)
            except (StorageError, OSError, ProfileError, CreationLibraryError, ActivityLifecycleError, ValueError, sqlite3.Error):
                # Broker was started before the optional creations repository.
                # It is not yet in session resources; own its cleanup here.
                if storage_broker is not None:
                    storage_broker.stop()
                return self._failed_launch_session(
                    manifest,
                    profile,
                    authority,
                    session_id=session_id,
                    control=control,
                    history_store=history_store,
                    reason=ActivityExitReason.PLATFORM_FAILURE,
                )
            resources = (storage_broker,)

        event_broker: ActivityEventBroker | None = None
        if history_store is not None and self._history_service is not None:
            try:
                event_broker = self._event_broker_factory(
                    history_store,
                    manifest,
                    self._history_service.progression_policy,
                    session_id,
                    sandboxed=sandboxed,
                )
            except (HistoryError, OSError):
                return self._failed_launch_session(
                    manifest,
                    profile,
                    authority,
                    session_id=session_id,
                    control=control,
                    history_store=history_store,
                    resources=resources,
                    reason=ActivityExitReason.PLATFORM_FAILURE,
                )
            resources = (*resources, event_broker)

        display_lease: DisplaySessionLease | None = None
        if self._display_coordinator is not None:
            try:
                display_lease = self._display_coordinator.prepare_activity(session_id)
            except DisplaySessionError:
                return self._failed_launch_session(
                    manifest,
                    profile,
                    authority,
                    session_id=session_id,
                    control=control,
                    history_store=history_store,
                    resources=resources,
                    reason=ActivityExitReason.PLATFORM_FAILURE,
                )
            self._display_leases[session_id] = display_lease

        try:
            environment = self._sanitized_environment(
                manifest,
                profile,
                authority,
                session_id,
                sandboxed=sandboxed,
                storage_broker=storage_broker,
                event_broker=event_broker,
                runtime_environment=runtime_command.environment,
                lifecycle_environment=lifecycle_binding.environment,
                display_environment=(
                    None
                    if display_lease is None
                    else display_lease.transport.environment()
                ),
            )
        except (ActivityLifecycleError, OSError, TypeError, ValueError):
            return self._failed_launch_session(
                manifest,
                profile,
                authority,
                session_id=session_id,
                control=control,
                history_store=history_store,
                resources=resources,
                reason=ActivityExitReason.PLATFORM_FAILURE,
            )

        if sandboxed:
            assert sandbox is not None
            try:
                command = self._sandbox_command(
                    sandbox,
                    runtime_command,
                    manifest,
                    profile,
                    authority,
                    storage_broker=storage_broker,
                    event_broker=event_broker,
                )
            except (ActivityLifecycleError, ProfileError, OSError):
                return self._failed_launch_session(
                    manifest,
                    profile,
                    authority,
                    session_id=session_id,
                    control=control,
                    history_store=history_store,
                    resources=resources,
                    reason=ActivityExitReason.PLATFORM_FAILURE,
                )
            cwd: Path | None = None
        else:
            command = list(runtime_command.command)
            cwd = runtime_command.cwd

        invocation = RuntimeInvocation(
            command=tuple(command),
            cwd=cwd,
            environment=tuple(sorted(environment.items())),
        )
        started = monotonic_now()
        try:
            process = self._runtime_manager.launch(preparation, invocation)
        except RuntimeAdapterError:
            return self._failed_launch_session(
                manifest,
                profile,
                authority,
                session_id=session_id,
                control=control,
                started_at=started,
                resources=resources,
                history_store=history_store,
            )

        session = ActivitySession(
            activity_id=manifest.activity_id,
            package_digest=authority.package_digest,
            session_id=session_id,
            control=control,
            process=process,
            state=ActivitySessionState.STARTING,
            started_at=started,
            ready_deadline=started + self._ready_timeout_seconds,
            graceful_stop_seconds=self._graceful_stop_seconds,
        )
        self._session_resources[session.session_id] = resources
        if history_store is not None:
            self._history_stores[session.session_id] = history_store
        self._runtime_preparations[session.session_id] = preparation
        self._active_session = session
        return session

    def poll(self, session: ActivitySession) -> ActivityResult | None:
        if session.result is not None:
            return session.result
        if self._active_session is not session:
            raise ActivityLifecycleError("session is not owned by this supervisor")
        process = session.process
        if process is None:
            raise ActivityLifecycleError("non-terminal session has no process")

        preparation = self._runtime_preparations.get(session.session_id)
        if preparation is None:
            raise ActivityLifecycleError("session has no runtime preparation")
        control = session.control
        if control is None:
            raise ActivityLifecycleError("active session has no lifecycle control")

        now = monotonic_now()
        runtime_exit = self._runtime_manager.collect_exit(preparation, process)
        if runtime_exit is not None:
            # READY is a per-launch marker, so consume it even when the child
            # exits between polling ticks. The process is already terminal, so
            # record READY in history but do not present a now-dead surface.
            if session.ready_at is None and control.ready():
                if self._record_ready(session, present_display=False):
                    session.ready_at = now
                else:
                    session.forced_reason = ActivityExitReason.PLATFORM_FAILURE
            return self._finish_session(session, runtime_exit, now)

        if session.state is ActivitySessionState.STARTING:
            if control.ready():
                if self._record_ready(session, present_display=True):
                    session.ready_at = now
                    session.state = ActivitySessionState.RUNNING
                else:
                    return self.force_stop(session, ActivityExitReason.PLATFORM_FAILURE)
            elif now >= session.ready_deadline:
                self.force_stop(session, ActivityExitReason.READY_TIMEOUT)

        if session.state is ActivitySessionState.STOPPING:
            requested_at = session.stop_requested_at
            if (
                requested_at is not None
                and session.forced_reason is None
                and now - requested_at >= session.graceful_stop_seconds
            ):
                result = self.force_stop(session, ActivityExitReason.FORCED_STOP)
                if result is not None:
                    return result

        runtime_exit = self._runtime_manager.collect_exit(preparation, process)
        if runtime_exit is not None:
            return self._finish_session(session, runtime_exit, monotonic_now())
        return None

    def request_stop(self, session: ActivitySession) -> ActivityResult | None:
        if session.result is not None:
            return session.result
        if self._active_session is not session:
            raise ActivityLifecycleError("session is not owned by this supervisor")
        control = session.control
        if control is None:
            raise ActivityLifecycleError("active session has no lifecycle control")
        if session.state is not ActivitySessionState.STOPPING:
            control.request_stop()
            session.stop_requested_at = monotonic_now()
            session.state = ActivitySessionState.STOPPING
        return self.poll(session)

    def force_stop(
        self,
        session: ActivitySession,
        reason: ActivityExitReason = ActivityExitReason.FORCED_STOP,
    ) -> ActivityResult | None:
        if session.result is not None:
            return session.result
        if self._active_session is not session:
            raise ActivityLifecycleError("session is not owned by this supervisor")
        if reason not in {
            ActivityExitReason.FORCED_STOP,
            ActivityExitReason.READY_TIMEOUT,
            ActivityExitReason.SYSTEM_SHUTDOWN,
            ActivityExitReason.PLATFORM_FAILURE,
        }:
            raise ValueError("force_stop requires a forced terminal reason")
        session.forced_reason = reason
        session.state = ActivitySessionState.STOPPING
        process = session.process
        preparation = self._runtime_preparations.get(session.session_id)
        if process is not None and preparation is not None:
            self._runtime_manager.force_stop(preparation, process)
            runtime_exit = self._runtime_manager.collect_exit(preparation, process)
            if runtime_exit is not None:
                return self._finish_session(session, runtime_exit, monotonic_now())
        return None

    def shutdown_active(self) -> ActivityResult | None:
        session = self.active_session
        if session is None:
            return None
        return self.force_stop(session, ActivityExitReason.SYSTEM_SHUTDOWN)

    def _finish_session(
        self,
        session: ActivitySession,
        runtime_exit: RuntimeExit,
        ended_at: float,
    ) -> ActivityResult:
        if session.forced_reason is not None:
            reason = session.forced_reason
        elif (
            session.stop_requested_at is not None
            and runtime_exit.kind is RuntimeExitKind.NORMAL
        ):
            reason = ActivityExitReason.GRACEFUL_STOP
        elif runtime_exit.kind is RuntimeExitKind.NORMAL:
            reason = ActivityExitReason.NORMAL
        else:
            reason = ActivityExitReason.CRASH

        runtime_clean = self._cleanup_runtime_session(session)
        display_clean = self._cleanup_display_session(session.session_id)
        resources_clean = self._cleanup_session_resources(session.session_id)
        control_clean = True
        if session.control is not None:
            try:
                session.control.cleanup()
            except Exception:
                control_clean = False
        if not runtime_clean or not display_clean or not resources_clean or not control_clean:
            reason = ActivityExitReason.PLATFORM_FAILURE

        history_store = self._history_stores.pop(session.session_id, None)
        if history_store is not None:
            try:
                history_store.finish_session(
                    session.session_id,
                    reason.value,
                    active_duration_seconds=max(0.0, ended_at - session.started_at),
                )
            except HistoryCapacityError as exc:
                self._warn_history_paused(session.activity_id, exc)
            except HistoryError:
                reason = ActivityExitReason.PLATFORM_FAILURE

        state = (
            ActivitySessionState.EXITED
            if reason in {ActivityExitReason.NORMAL, ActivityExitReason.GRACEFUL_STOP}
            else ActivitySessionState.FAILED
        )
        result = ActivityResult(
            activity_id=session.activity_id,
            session_id=session.session_id,
            return_code=runtime_exit.return_code,
            exit_reason=reason,
            ready=session.ready_at is not None,
            started_at=session.started_at,
            ready_at=session.ready_at,
            ended_at=ended_at,
        )
        session.state = state
        session.result = result
        if self._active_session is session:
            self._active_session = None
        return result

    def _failed_launch_session(
        self,
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
        *,
        session_id: str,
        control: ActivityLifecycleControl | None = None,
        started_at: float | None = None,
        resources: tuple[SessionResource, ...] = (),
        history_store: SessionHistoryRecorder | None = None,
        reason: ActivityExitReason = ActivityExitReason.LAUNCH_FAILURE,
    ) -> ActivitySession:
        started = monotonic_now() if started_at is None else started_at
        ended = monotonic_now()
        if not self._cleanup_display_session(session_id):
            reason = ActivityExitReason.PLATFORM_FAILURE
        for resource in reversed(resources):
            try:
                resource.stop()
            except Exception:
                reason = ActivityExitReason.PLATFORM_FAILURE
        if control is not None:
            try:
                control.cleanup()
            except Exception:
                reason = ActivityExitReason.PLATFORM_FAILURE
        if history_store is not None:
            try:
                history_store.finish_session(
                    session_id,
                    reason.value,
                    active_duration_seconds=max(0.0, ended - started),
                )
            except HistoryError:
                reason = ActivityExitReason.PLATFORM_FAILURE
        result = ActivityResult(
            activity_id=manifest.activity_id,
            session_id=session_id,
            return_code=126,
            exit_reason=reason,
            ready=False,
            started_at=started,
            ready_at=None,
            ended_at=ended,
        )
        session = ActivitySession(
            activity_id=manifest.activity_id,
            package_digest=authority.package_digest,
            session_id=session_id,
            control=control,
            process=None,
            state=ActivitySessionState.FAILED,
            started_at=started,
            ready_deadline=started,
            graceful_stop_seconds=self._graceful_stop_seconds,
            result=result,
        )
        return session

    def _record_ready(self, session: ActivitySession, *, present_display: bool) -> bool:
        if present_display and not self._present_display_session(session.session_id):
            return False
        history_store = self._history_stores.get(session.session_id)
        if history_store is None:
            return True
        try:
            history_store.mark_ready(session.session_id)
        except HistoryCapacityError as exc:
            # A healthy running Activity is not failed because history is full.
            self._warn_history_paused(session.activity_id, exc)
            return True
        except HistoryError:
            return False
        return True

    @staticmethod
    def _warn_history_paused(activity_id: str, exc: Exception) -> None:
        logger.warning(
            "History write skipped for %s because child-data headroom is "
            "exhausted: %s",
            activity_id,
            exc,
        )

    def _present_display_session(self, session_id: str) -> bool:
        lease = self._display_leases.get(session_id)
        if lease is None:
            return True
        coordinator = self._display_coordinator
        if coordinator is None:
            self._display_leases.pop(session_id, None)
            return False
        try:
            coordinator.activity_ready(lease)
        except DisplaySessionError:
            # activity_ready() already attempts shell recovery. Retire this lease
            # either way; a FAILED coordinator remains fail-closed for later
            # prepare attempts while the current Activity is force-stopped.
            self._display_leases.pop(session_id, None)
            return False
        return True

    def _cleanup_display_session(self, session_id: str) -> bool:
        lease = self._display_leases.pop(session_id, None)
        if lease is None:
            return True
        coordinator = self._display_coordinator
        if coordinator is None:
            return False
        if coordinator.snapshot.shell_available:
            return True
        try:
            coordinator.activity_ended(lease)
        except (DisplaySessionError, TypeError):
            return False
        return coordinator.snapshot.shell_available

    def _cleanup_runtime_session(self, session: ActivitySession) -> bool:
        preparation = self._runtime_preparations.pop(session.session_id, None)
        process = session.process
        if preparation is None or process is None:
            return preparation is None and process is None
        try:
            self._runtime_manager.cleanup(preparation, process)
        except Exception:
            return False
        return True

    def _cleanup_session_resources(self, session_id: str) -> bool:
        resources = self._session_resources.pop(session_id, ())
        clean = True
        for resource in reversed(resources):
            try:
                resource.stop()
            except Exception:
                clean = False
        return clean

    def _sandbox_required(self) -> bool:
        if self._require_sandbox_override is not None:
            return self._require_sandbox_override
        installed_root = Path(os.environ.get("GREIA_OS_ROOT", str(PRODUCTION_ROOT)))
        from .installed_root import is_installed_root

        return is_installed_root(installed_root)

    def _resolve_sandbox(self) -> Path:
        if self._sandbox_executable is not None:
            return self._sandbox_executable
        configured = os.environ.get("GREIA_ACTIVITY_SANDBOX")
        return Path(configured) if configured else PRODUCTION_BWRAP

    @staticmethod
    def _sandbox_command(
        sandbox: Path,
        runtime_command: RuntimeCommand,
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
        *,
        storage_broker: ActivityStorageBroker | None = None,
        event_broker: ActivityEventBroker | None = None,
    ) -> list[str]:
        command = [
            str(sandbox),
            "--die-with-parent",
            "--new-session",
            "--unshare-pid",
            "--unshare-net",
            "--unshare-uts",
            "--ro-bind",
            "/",
            "/",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            # /run is read-only under --ro-bind / /, which would prevent bwrap
            # from creating the mount points for the per-session storage/event
            # sockets and activity data. A private tmpfs keeps those writable.
            "--tmpfs",
            "/run",
        ]
        if authority.has_capability("audio.basic"):
            command.extend(["--dev-bind-try", "/dev/snd", "/dev/snd"])
        activity_data = profile.activity_data_dir(manifest.activity_id)
        command.extend(
            [
                "--dir",
                str(SANDBOX_ACTIVITY_ROOT),
                "--bind",
                str(activity_data),
                str(SANDBOX_ACTIVITY_ROOT),
                "--tmpfs",
                "/var/lib/greia-profiles",
                "--tmpfs",
                "/var/lib/greia-os",
                "--tmpfs",
                "/run/greia-os",
            ]
        )
        if storage_broker is not None:
            command.extend(
                [
                    "--dir",
                    str(SANDBOX_STORAGE_ROOT),
                    "--ro-bind",
                    str(storage_broker.host_root),
                    str(SANDBOX_STORAGE_ROOT),
                ]
            )
        if event_broker is not None:
            command.extend(
                [
                    "--dir",
                    str(SANDBOX_EVENT_ROOT),
                    "--ro-bind",
                    str(event_broker.host_root),
                    str(SANDBOX_EVENT_ROOT),
                ]
            )
        if authority.has_permission("customization.manage"):
            command.extend(
                [
                    "--bind",
                    str(profile.customization_dir),
                    str(SANDBOX_CUSTOMIZATION_ROOT),
                ]
            )
        if not authority.has_permission("removable_media.read"):
            command.extend(["--tmpfs", "/media/greia"])
        command.extend(
            ["--chdir", str(runtime_command.cwd), *runtime_command.command]
        )
        return command

    @staticmethod
    def _sanitized_environment(
        manifest: ActivityManifest,
        profile: ProfileContext,
        authority: ActivityAuthority,
        session_id: str,
        *,
        sandboxed: bool = False,
        storage_broker: ActivityStorageBroker | None = None,
        event_broker: ActivityEventBroker | None = None,
        runtime_environment: tuple[tuple[str, str], ...] = (),
        lifecycle_environment: tuple[tuple[str, str], ...] = (),
        display_environment: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        allowed_names = {
            "DISPLAY",
            "LANG",
            "LC_ALL",
            "PULSE_SERVER",
            "SDL_AUDIODRIVER",
            "SDL_VIDEODRIVER",
            "WAYLAND_DISPLAY",
            "XAUTHORITY",
            "XDG_RUNTIME_DIR",
        }
        environment = {
            name: value for name, value in os.environ.items() if name in allowed_names
        }
        activity_data = profile.activity_data_dir(manifest.activity_id)
        cache_dir = activity_data / "cache"
        config_dir = activity_data / "config"
        data_dir = activity_data / "data"
        for path in (cache_dir, config_dir, data_dir):
            path.mkdir(parents=True, exist_ok=True)
            os.chmod(path, 0o770)

        avatar_request = activity_data / ".greia" / "requests" / "avatar.json"
        if authority.has_permission("profile.manage_own"):
            avatar_request.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(avatar_request.parent, 0o770)

        if sandboxed:
            env_activity_data = SANDBOX_ACTIVITY_ROOT
            env_cache = SANDBOX_ACTIVITY_ROOT / "cache"
            env_config = SANDBOX_ACTIVITY_ROOT / "config"
            env_data = SANDBOX_ACTIVITY_ROOT / "data"
            env_customization = SANDBOX_CUSTOMIZATION_ROOT
            env_avatar_request = SANDBOX_ACTIVITY_ROOT / ".greia" / "requests" / "avatar.json"
        else:
            env_activity_data = activity_data
            env_cache = cache_dir
            env_config = config_dir
            env_data = data_dir
            env_customization = profile.customization_dir
            env_avatar_request = avatar_request

        root_path = Path(os.environ.get("GREIA_OS_ROOT", str(PRODUCTION_ROOT))).resolve()
        python_path = os.environ.get("PYTHONPATH") or str(root_path / "src")
        environment.update(
            {
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "PYTHONPATH": python_path,
                "HOME": str(env_activity_data),
                "XDG_CACHE_HOME": str(env_cache),
                "XDG_CONFIG_HOME": str(env_config),
                "XDG_DATA_HOME": str(env_data),
                "GREIA_OS_ROOT": str(root_path),
                "GREIA_ACTIVITY_ID": manifest.activity_id,
                "GREIA_ACTIVITY_ROOT": str(manifest.root),
                "GREIA_ACTIVITY_DATA_DIR": str(env_activity_data),
                "GREIA_ACTIVITY_INPUT_PROFILE": manifest.input_profile,
                "GREIA_RUNTIME_API": manifest.api_version,
                "GREIA_ACTIVITY_CAPABILITIES": ",".join(sorted(authority.sdk_features)),
                "GREIA_PACKAGE_TRUST": authority.package_trust.value,
                "GREIA_PROFILE_ID": profile.profile.profile_id,
                "GREIA_PROFILE_NAME": profile.profile.display_name,
                "GREIA_PROFILE_AVATAR": profile.profile.avatar_id,
                "GREIA_PROFILE_LOCALE": resolve_child_locale(getattr(profile.profile, "locale", None)),
                "GREIA_DEVICE_LOCALE": resolve_device_locale(),
                "GREIA_PROFILE_UPPERCASE": (
                    "uppercase"
                    if getattr(profile.profile, "uppercase_text", True)
                    else "normal"
                ),
                "GREIA_MEDIA_ROOT": os.environ.get("GREIA_MEDIA_ROOT", "/media/greia"),
                "GREIA_ACTIVITY_SESSION_ID": session_id,
                # The platform-owned Activity entry normalizes the Activity's
                # own set_mode size to this exact Shell surface. Empty means
                # "use the real desktop size" (fullscreen child sessions).
                "GREIA_ACTIVITY_VIEWPORT": os.environ.get(
                    "GREIA_ACTIVITY_VIEWPORT", ""
                ),
            }
        )
        ActivitySupervisor._apply_display_environment(environment, display_environment)
        environment.update(dict(runtime_environment))
        for name, value in lifecycle_environment:
            if name in environment:
                raise ActivityLifecycleError(
                    f"runtime lifecycle environment collides with platform name {name!r}"
                )
            environment[name] = value
        if storage_broker is not None:
            environment["GREIA_STORAGE_SOCKET"] = str(storage_broker.child_socket)
            environment["GREIA_STORAGE_TOKEN"] = storage_broker.session_token
        if event_broker is not None:
            environment["GREIA_EVENT_SOCKET"] = str(event_broker.child_socket)
            environment["GREIA_EVENT_TOKEN"] = event_broker.session_token
        if authority.has_permission("customization.manage"):
            environment["GREIA_CUSTOMIZATION_DIR"] = str(env_customization)
        if authority.has_permission("profile.manage_own"):
            environment["GREIA_AVATAR_REQUEST_PATH"] = str(env_avatar_request)
        return environment

    @staticmethod
    def _apply_display_environment(
        environment: dict[str, str],
        display_environment: Mapping[str, str] | None,
    ) -> None:
        if display_environment is None:
            return
        unknown = set(display_environment) - _DISPLAY_TRANSPORT_ENVIRONMENT
        if unknown:
            raise ActivityLifecycleError(
                "display transport contains unsupported environment names: "
                + ", ".join(sorted(unknown))
            )
        for name, value in display_environment.items():
            if not isinstance(name, str) or not isinstance(value, str):
                raise ActivityLifecycleError(
                    "display transport environment entries must be text"
                )
            if "\x00" in value or len(value) > 8192:
                raise ActivityLifecycleError(
                    f"display transport environment value is invalid for {name!r}"
                )

        # These names select mutually exclusive display transports. Remove
        # inherited values first so a typed Wayland/KMSDRM lease cannot carry a
        # stale X11 endpoint (or vice versa). XDG_RUNTIME_DIR is also used by
        # non-display services, so preserve it unless the selected transport
        # explicitly supplies its own runtime directory.
        for name in ("DISPLAY", "XAUTHORITY", "WAYLAND_DISPLAY", "SDL_VIDEODRIVER"):
            environment.pop(name, None)
        if "XDG_RUNTIME_DIR" in display_environment:
            environment.pop("XDG_RUNTIME_DIR", None)
        environment.update(display_environment)

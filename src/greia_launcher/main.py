from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from greia_platform.boot_logo import canonical_boot_logo as _canonical_boot_logo
from greia_platform.boot_markers import emit_boot_marker
from greia_platform.activity_display import remember_viewport
from greia_platform.activities import (
    ActivityManifest,
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
)
from greia_platform.assets import AssetCatalogue, AssetCatalogueError
from greia_platform.creation_capacity import VolumeBudget
from greia_platform.pygame_visual_assets import (
    PygameVisualSurfaceCache,
    VisualSurfaceCacheError,
    pygame_display_converter,
)
from greia_platform.customization import ThemeStore
from greia_platform.typography import FontRole, GreiaTypography
from greia_platform.hal import (
    AudioState,
    DisplayState,
    GreiaHAL,
    InputState,
    NetworkState,
    PowerState,
    RemovableMediaState,
    StaticAudioHAL,
    StaticDisplayHAL,
    StaticInputHAL,
    StaticNetworkHAL,
    StaticPowerHAL,
    StaticRemovableMediaHAL,
)
from greia_platform.permissions import PermissionDecisionError
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.profiles import (
    ChildProfile,
    ProfileContext,
    ProfileError,
)

from greia_platform.history import HistoryError
from greia_platform.activity_launch_cover import LaunchCard, LaunchCardPublisher
from greia_platform.input_core import SemanticAction
from greia_platform.storage import StorageError
from .bootstrap import (
    BootLifecycleError,
    BootLifecycleGuard,
    BootLifecycleState,
    LauncherBootstrap,
    PreparedLauncherState,
)
from .composition import (
    build_launcher_runtime_services,
    provisional_installed_display_session,
)
from .display_session import DisplaySessionError
from .launch_feedback import launch_feedback
from .foreground_cadence import ActivityForegroundCadence
from .return_tap_guard import ReturnTapGuard
from .launch_timing import ready_timeout_for
from .key_chord import KeyChordTracker
from .lifecycle import ActivityExitReason, ActivityResult, ActivitySessionState
from .parent_credential_client import ParentCredentialClient
from .parent_panel import ParentSettingsOverlay
from .shell_input import ShellControllerCommand, ShellInputAction, ShellInputController
from .runtime_adapter import RuntimeAdapterError
from .supervisor import ActivityLifecycleError, ActivitySupervisor
from .theme import LauncherThemeController


logger = logging.getLogger(__name__)

#: Launch-preparation failures that are expected operational faults (bad
#: profile tree, full/unwritable storage, history, runtime validation, display
#: lease, IO or a subprocess timeout). They fail one launch with one bounded
#: journal line. Anything else is a programming error: still contained so
#: the child Shell survives, but logged with its full traceback.
EXPECTED_LAUNCH_START_ERRORS: tuple[type[Exception], ...] = (
    ProfileError,
    StorageError,
    HistoryError,
    RuntimeAdapterError,
    ActivityLifecycleError,
    DisplaySessionError,
    OSError,
    subprocess.SubprocessError,
)
_LAUNCH_ERROR_TEXT_LIMIT = 400
# Shared-visual surface budget for the child Shell: 4 Mpx (about 16 MiB at
# 32 bpp). A full catalogue walk at 1024x600 measured about 2.9 Mpx, so this
# bounds the long-session plateau without evicting the normal working set.
SHELL_VISUAL_CACHE_MAX_PIXELS = 4 * 1024 * 1024


def configure_launcher_logging(
    *,
    syslog_address: str = "/dev/log",
    stream: Any = None,
) -> None:
    """Route WARNING+ records (tracebacks included) to the journal. Idempotent.

    ``greia-x-session`` runs the Shell under xinit, whose stdio forwarding
    provably loses ExecStart output, so a traceback written only to stderr
    never reached the journal. journald owns ``/dev/log``; when it exists a
    syslog handler delivers each record (with any traceback) as one journal
    entry tagged ``greia-launcher``. stderr is kept for development runs.
    Uncaught exceptions are routed through the same handlers before the
    interpreter's default hook runs.
    """

    root = logging.getLogger()
    if getattr(root, "_greia_launcher_logging", False):
        return
    formatter = logging.Formatter("%(levelname)s %(name)s: %(message)s")
    stderr_handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)
    if syslog_address and os.path.exists(syslog_address):
        try:
            syslog_handler = logging.handlers.SysLogHandler(address=syslog_address)
        except OSError:
            syslog_handler = None
        if syslog_handler is not None:
            syslog_handler.ident = "greia-launcher: "
            syslog_handler.setLevel(logging.WARNING)
            syslog_handler.setFormatter(formatter)
            root.addHandler(syslog_handler)
    if root.level == logging.NOTSET or root.level > logging.WARNING:
        root.setLevel(logging.WARNING)
    previous_hook = sys.excepthook

    def _log_uncaught(exc_type: Any, exc: Any, tb: Any) -> None:
        if not issubclass(exc_type, KeyboardInterrupt):
            logging.getLogger("greia_launcher").critical(
                "child Shell crashed", exc_info=(exc_type, exc, tb)
            )
        previous_hook(exc_type, exc, tb)

    sys.excepthook = _log_uncaught
    root._greia_launcher_logging = True  # type: ignore[attr-defined]


@dataclass(frozen=True, slots=True)
class LauncherPaths:
    root: Path
    activities: Path
    developer_activities: Path | None
    runtime_catalogue: Path
    asset_catalogue: Path
    shared_visual_catalogue: Path
    theme_defaults: Path
    profile_defaults: Path
    permission_policy: Path
    storage_policy: Path
    history_policy: Path
    progression_policy: Path
    profiles_dir: Path
    active_profile_status: Path

    @classmethod
    def from_environment(cls) -> "LauncherPaths":
        root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")).resolve()
        return cls(
            root=root,
            activities=root / "activities",
            developer_activities=_optional_absolute_path_from_environment(
                "GREIA_DEVELOPER_ACTIVITY_ROOT"
            ),
            runtime_catalogue=root / "runtime" / "child-runtime.toml",
            asset_catalogue=root / "assets" / "catalog" / "core_icons_v1.toml",
            shared_visual_catalogue=root / "assets" / "catalog" / "shared_visuals_v1.toml",
            theme_defaults=root / "runtime" / "theme-defaults.toml",
            profile_defaults=root / "runtime" / "profile-defaults.toml",
            permission_policy=root / "runtime" / "permission-policy.toml",
            storage_policy=root / "runtime" / "storage-policy.toml",
            history_policy=root / "runtime" / "history-policy.toml",
            progression_policy=root / "runtime" / "progression-policy.toml",
            profiles_dir=Path(
                os.environ.get("GREIA_PROFILES_DIR", "/var/lib/greia-profiles")
            ).resolve(),
            active_profile_status=Path(
                os.environ.get(
                    "GREIA_ACTIVE_PROFILE_STATUS", "/run/greia-os/active-profile.json"
                )
            ).resolve(),
        )


@dataclass(frozen=True, slots=True)
class HitTarget:
    action: str
    value: object
    rect: Any


@dataclass(frozen=True, slots=True)
class GridPage:
    start: int
    stop: int
    columns: int
    rows: int
    page_size: int
    page_index: int
    page_count: int


def calculate_grid_page(
    total: int,
    selected: int,
    *,
    columns: int,
    max_rows: int,
) -> GridPage:
    """Return a bounded page containing the selected index."""

    columns = max(1, columns)
    max_rows = max(1, max_rows)
    page_size = columns * max_rows
    if total <= 0:
        return GridPage(0, 0, columns, 0, page_size, 0, 1)
    selected = min(max(0, selected), total - 1)
    page_count = (total + page_size - 1) // page_size
    page_index = selected // page_size
    start = page_index * page_size
    stop = min(total, start + page_size)
    visible = stop - start
    rows = (visible + columns - 1) // columns
    return GridPage(start, stop, columns, rows, page_size, page_index, page_count)


def create_preparation_worker():  # type: ignore[no-untyped-def]
    """Return the single bounded post-frame preparation worker.

    Phase 4 owns exactly one preparation worker: remaining work is small
    after Phase 3 and a single worker avoids Atom-class contention and init
    race sprawl. The literal ``max_workers=1`` below is the source assertion
    point; do not add a second executor.
    """

    from concurrent.futures import ThreadPoolExecutor

    return ThreadPoolExecutor(max_workers=1)


class LauncherApplication:
    ERROR = (177, 44, 44)
    RESCAN_SECONDS = 2.0
    #: State-dependent service cadence while an Activity owns the foreground.
    FOREGROUND_CADENCE = ActivityForegroundCadence()
    #: Stateless, fail-soft owner of the per-launch card file (launch hand-off).
    _launch_card_publisher = LaunchCardPublisher()

    def __init__(
        self,
        *,
        windowed: bool = False,
        allow_exit: bool = False,
        shell_input: ShellInputController | None = None,
        bootstrap: bool = True,
    ):
        # Lightweight construction only: no Activity discovery, no registry
        # composition, no runtime build, no history recovery. The explicit
        # bootstrap step (see bootstrap()/bootstrap_launcher()) owns the
        # one-pass composition. The base constructor never calls the
        # overridable _rebuild_runtime_services(); subclasses bootstrap
        # explicitly after this constructor has fully returned.
        self._shell_input = shell_input or ShellInputController()
        self.paths = LauncherPaths.from_environment()
        self.windowed = windowed
        self.allow_exit = allow_exit
        self._bootstrapped = False
        self._boot_lifecycle = BootLifecycleGuard()
        # Bootstrap-owned state starts as explicit placeholders so an
        # unbootstrapped instance is observable but performs no discovery.
        self.runtime: RuntimeCatalogue | None = None
        self.registry: ActivityRegistry | None = None
        self._activities: tuple[ActivityManifest, ...] = ()
        self._asset_set: Any = None
        self.assets: Any = None
        self.shared_visuals_available = False
        self._visual_cache: Any = None
        self.profile_store: Any = None
        self.profiles: tuple[ChildProfile, ...] = ()
        self.session: Any = None
        self.selector_theme: Any = None
        self.theme_controller: Any = None
        self._activity_discovery_token: Any = ()
        self.runtime_services: Any = None
        self.supervisor: Any = None
        self._history_recovery_failures: set[str] = set()
        self._shell_window_backend: Any = None
        self._selected = 0
        self._profile_selected = 0
        self._active_profile: ProfileContext | None = None
        self._pending_profile: ChildProfile | None = None
        self._mode = "profiles"
        self._secret_text = ""
        self._secret_error_until = 0.0
        self._last_result: ActivityResult | None = None
        self._first_frame_released = False
        self._next_boot_handoff_attempt = 0.0
        self._icon_cache: dict[tuple[str, int], Any] = {}
        self._font_cache: dict[int, Any] = {}
        self._profile_name_cache: dict[tuple[str, int, int, tuple[int, int, int]], Any] = {}
        self._typography = GreiaTypography(
            self.paths.root / "assets" / "fonts" / "nunito-sans"
        )
        self._next_rescan = 0.0
        self._catalogue_error = False
        self._targets: list[HitTarget] = []
        self._cached_profiles_surface: Any = None
        self._cached_profiles_key: Any = None
        self._cached_profiles_targets: list[HitTarget] = []
        self._parent_chord = KeyChordTracker({ord("s"), ord("t")}, hold_duration_seconds=5.0)
        # The Parent password belongs to the Parent service identity; the
        # panel asks that service to verify it rather than reading its 0600
        # digest as the child identity, which could never succeed.
        self._parent_panel = ParentSettingsOverlay(ParentCredentialClient())
        self._dimmed_underlay: Any = None
        self._dimmed_underlay_key: Any = None
        self._parent_panel_opened_monotonic = 0.0
        self._page_content_rect: Any = None
        # Post-intro wait: seconds the main thread blocked on the single
        # preparation worker after the intro ended (near zero by design).
        self._post_intro_wait_seconds = 0.0
        # Production post-intro health acceptance (T3-UPDATE2): outcome of
        # the single INTERACTIVE_READY seam call, or None on plain boots;
        # bounded error text when health infra refused on a pending boot.
        self._post_intro_health_outcome: Any = None
        self._post_intro_health_error: str | None = None
        # Auto-bootstrap only the exact base type. Subclass instances must
        # let their own explicit bootstrap run after this constructor has
        # returned, so the base constructor never dispatches to a subclass
        # override while state is half-initialized.
        if bootstrap and type(self) is LauncherApplication:
            self.bootstrap()

    @classmethod
    def create_bootstrapped(
        cls,
        *,
        windowed: bool = False,
        allow_exit: bool = False,
        shell_input: ShellInputController | None = None,
    ) -> "LauncherApplication":
        """Construct and explicitly bootstrap one launcher in boot order."""

        app = cls(
            windowed=windowed,
            allow_exit=allow_exit,
            shell_input=shell_input,
            bootstrap=False,
        )
        return app.bootstrap()

    def bootstrap(self) -> "LauncherApplication":
        """Run the explicit one-pass boot composition exactly once.

        Preparation is delegated to :class:`LauncherBootstrap`, which seals
        the composed set into one immutable :class:`PreparedLauncherState`;
        publication happens atomically in :meth:`apply_prepared_state`.
        A present-but-corrupt built-in index raises its controlled failure
        (never a silent full rescan); a damaged Parent set degrades to the
        displayable catalogue-error state instead of taking the Shell down.
        The polymorphic runtime build runs here, never in the constructor.
        A failed bootstrap publishes nothing and resets the lifecycle guard
        so a later retry on a fresh composition may run.
        """

        if self._bootstrapped:
            return self
        emit_boot_marker("launcher_construct_begin")
        try:
            self._boot_lifecycle.begin_preparing_runtime()
            coordinator = LauncherBootstrap(self.paths)
            try:
                state = coordinator.prepare_runtime(
                    build_services=self._build_bootstrap_services,
                    build_supervisor=self._build_bootstrap_supervisor,
                    build_catalogue=self._bootstrap_catalogue_builder(),
                )
            except Exception:
                self._boot_lifecycle.reset_to_created()
                raise
            try:
                self.apply_prepared_state(state)
            except Exception:
                self._boot_lifecycle.reset_to_created()
                raise
            return self
        finally:
            emit_boot_marker("launcher_construct_end")

    def apply_prepared_state(self, state: PreparedLauncherState) -> "LauncherApplication":
        """Publish one prepared state exactly once into ``INTERACTIVE_READY``.

        The main thread calls this at intro completion ( now: directly from
        :meth:`bootstrap`). All fields are assigned together only after the
        display-bound visual cache is built; any failure restores the
        pre-apply placeholders so no half-populated launcher is observable.
        Consuming a second state, or applying while not preparing, raises
        :class:`BootLifecycleError`.
        """

        if self._bootstrapped:
            raise BootLifecycleError(
                "prepared launcher state was already consumed; "
                "exactly one apply per launcher instance"
            )
        if not isinstance(state, PreparedLauncherState):
            raise BootLifecycleError(
                f"apply requires a PreparedLauncherState, not {type(state).__name__}"
            )
        if self._boot_lifecycle.state is BootLifecycleState.FIRST_FRAME_VISIBLE:
            # Async post-frame path (P4-FIRSTFRAME): preparation ran after
            # the first flip; record the preparation edge before publishing.
            self._boot_lifecycle.begin_preparing_runtime()
        if self._boot_lifecycle.state is not BootLifecycleState.PREPARING_RUNTIME:
            raise BootLifecycleError(
                "apply_prepared_state requires the preparing_runtime state, "
                f"not {self._boot_lifecycle.state.value}"
            )
        # Display-bound construction happens before any publication, so its
        # failure leaves the launcher untouched.
        visual_cache = (
            PygameVisualSurfaceCache.for_pygame(
                state.asset_set.catalogue,
                max_entries=96,
                # Entry count alone allowed up to 96 display-sized renditions;
                # the pixel budget makes the Shell's shared-art plateau a
                # known byte cost on the 1 GB reference floor.
                max_total_pixels=SHELL_VISUAL_CACHE_MAX_PIXELS,
                # Convert decoded PNG renditions to display-native surfaces once
                # so every later frame blit uses pygame's fast paths instead of
                # the generic per-pixel fallback on low-resource devices.
                display_converter=pygame_display_converter(),
            )
            if state.asset_set.shared_visuals_available
            else None
        )
        snapshot = {
            "runtime": self.runtime,
            "registry": self.registry,
            "_asset_set": self._asset_set,
            "assets": self.assets,
            "shared_visuals_available": self.shared_visuals_available,
            "_visual_cache": self._visual_cache,
            "profile_store": self.profile_store,
            "profiles": self.profiles,
            "session": self.session,
            "selector_theme": self.selector_theme,
            "theme_controller": self.theme_controller,
            "_activities": self._activities,
            "_activity_discovery_token": self._activity_discovery_token,
            "runtime_services": self.runtime_services,
            "supervisor": self.supervisor,
            "_history_recovery_failures": self._history_recovery_failures,
            "_shell_window_backend": self._shell_window_backend,
            "_catalogue_error": self._catalogue_error,
            "_selected": self._selected,
        }
        try:
            self.runtime = state.runtime
            self.registry = state.registry
            self._asset_set = state.asset_set
            self.assets = state.asset_set.catalogue
            self.shared_visuals_available = state.asset_set.shared_visuals_available
            self._visual_cache = visual_cache
            self.profile_store = state.profile_store
            self.profiles = state.profiles
            self.session = state.session
            self.selector_theme = state.selector_theme
            self.theme_controller = state.selector_theme
            self._activities = state.activities
            self._activity_discovery_token = state.activity_discovery_token
            self.runtime_services = state.runtime_services
            self.supervisor = state.supervisor
            self._history_recovery_failures = set(state.history_recovery_failures)
            self._shell_window_backend = state.shell_window_backend
            self._selected = 0
            self._catalogue_error = state.parent_degraded
            self._bootstrapped = True
        except Exception:
            self.runtime = snapshot["runtime"]
            self.registry = snapshot["registry"]
            self._asset_set = snapshot["_asset_set"]
            self.assets = snapshot["assets"]
            self.shared_visuals_available = snapshot["shared_visuals_available"]
            self._visual_cache = snapshot["_visual_cache"]
            self.profile_store = snapshot["profile_store"]
            self.profiles = snapshot["profiles"]
            self.session = snapshot["session"]
            self.selector_theme = snapshot["selector_theme"]
            self.theme_controller = snapshot["theme_controller"]
            self._activities = snapshot["_activities"]
            self._activity_discovery_token = snapshot["_activity_discovery_token"]
            self.runtime_services = snapshot["runtime_services"]
            self.supervisor = snapshot["supervisor"]
            self._history_recovery_failures = snapshot["_history_recovery_failures"]
            self._shell_window_backend = snapshot["_shell_window_backend"]
            self._catalogue_error = snapshot["_catalogue_error"]
            self._selected = snapshot["_selected"]
            self._bootstrapped = False
            raise
        # FIX-COMPOSE-WINDOW interactive handoff: promote deferred developer
        # sources into the registry without validating them. The discovery
        # token above was snapshotted before this promotion, so the first
        # post-interactive rescan observes the delta and performs the deferred
        # live validation through the unchanged trust-aware degrade path.
        # Deferred content stays unserved (never issued) until that rescan
        # validates it; the promotion itself walks no tree and computes no
        # digest. ``getattr`` duck-typing keeps synthetic/test states working.
        attach_deferred = getattr(self.registry, "attach_deferred_sources", None)
        if callable(attach_deferred):
            attach_deferred()
        self._boot_lifecycle.mark_interactive_ready()
        # POSTR1-P3-PREINTRO-TIMING-INSTRUMENT: canonical observable for the
        # real INTERACTIVE_READY transition. Single owner of the
        # ``launcher_interactive_ready`` GREIA_BOOT event (emitted only via
        # emit_boot_marker, never a second printer); consumed by
        # tools/boot/analyze_boot_markers.py and
        # tools/x8_qemu/preintro_timing.py P3.
        emit_boot_marker("launcher_interactive_ready")
        # T3-UPDATE2 production call graph: exactly one BOOT_HEALTHY
        # acceptance at the real INTERACTIVE_READY transition. Outside
        # candidate/first-install boots it is a bounded no-op (plain boots
        # mutate no journal or health state); first-frame systemd READY=1
        # stays owned by boot_intro and never implies update health.
        self._run_post_intro_health()
        return self

    def _run_post_intro_health(self) -> None:
        """Invoke the production post-intro health seam exactly once.

        The default implementation calls the production seam
        (:func:`greia_launcher.boot_health.maybe_accept_production_boot`)
        with the live lifecycle guard. Health-infra failures are recorded
        in bounded attributes and never take the Shell down: the journal
        stays pending for the privileged service to reconcile. Tests may
        count invocations by wrapping this method; the default stays the
        production path, never a stub.
        """

        from . import boot_health as _launcher_boot_health

        try:
            outcome = _launcher_boot_health.maybe_accept_production_boot(
                self._boot_lifecycle
            )
        except Exception as exc:
            self._post_intro_health_outcome = None
            self._post_intro_health_error = str(exc)[:256]
            return
        self._post_intro_health_outcome = outcome
        self._post_intro_health_error = None

    def _bootstrap_catalogue_builder(self) -> Any:
        """Return the presentation-catalogue factory for prepare, if any.

        The base launcher owns no presentation catalogue; the presentation
        subclass overrides this to build exactly one catalogue inside the
        one-pass preparation.
        """

        return None

    def _prepare_runtime_state(self) -> Any:
        """Compose the one-pass boot set on the single preparation worker.

        Worker-thread entry: runs :meth:`LauncherBootstrap.prepare_runtime`
        with this shell's injected builders. Performs only non-Pygame work
        (Activity index reads/deserialization, history file reads/recovery,
        pure-Python catalogue construction, filesystem reads). Developer-source
        live validation is deferred past the interactive handoff (see
        :func:`is_developer_boot_validation_deferred`), so the worker holds
        the GIL over structurally less work before interactive readiness.
        Never imports
        Pygame, never touches a surface, never mutates live launcher state;
        publication happens on the main thread in
        :meth:`apply_prepared_state`.
        """

        from .bootstrap import LauncherBootstrap

        coordinator = LauncherBootstrap(self.paths)
        return coordinator.prepare_runtime(
            build_services=self._build_bootstrap_services,
            build_supervisor=self._build_bootstrap_supervisor,
            build_catalogue=self._bootstrap_catalogue_builder(),
        )

    def _begin_post_frame_preparation(self, executor: Any) -> Any:
        """First-frame callback: enter preparing state and submit the worker.

        Runs on the display thread immediately after the first successful
        flip (and its ``intro_first_frame_flipped`` marker). Advances the
        guard ``FIRST_FRAME_VISIBLE → PREPARING_RUNTIME`` then submits
        :meth:`_prepare_runtime_state` onto the single bounded worker. The
        worker thread never calls Pygame; the display thread continues the
        existing intro animation without pause.
        """

        self._boot_lifecycle.mark_first_frame_visible()
        self._boot_lifecycle.begin_preparing_runtime()
        return executor.submit(self._prepare_runtime_state)

    def _await_and_apply_preparation(self, future: Any) -> Any:
        """Intro-end boundary: wait for the worker, then apply exactly once.

        Blocks only if the worker is still running (post-intro by design,
        expected near zero after Phase 3) and records that wait in
        ``_post_intro_wait_seconds``. Applies the one
        :class:`PreparedLauncherState` in a single deterministic transition
        into ``INTERACTIVE_READY``. Worker failure resets the guard to
        ``CREATED`` and re-raises through the existing controlled Greia
        error path: nothing half-populated is published and no hidden
        rescan runs.
        """

        wait_start = time.monotonic()
        try:
            state = future.result()
            self._post_intro_wait_seconds = time.monotonic() - wait_start
            self.apply_prepared_state(state)
        except Exception:
            try:
                self._boot_lifecycle.reset_to_created()
            except BootLifecycleError:
                pass
            raise
        return state

    def _chrome_metrics(self) -> Any:
        """Return injected display metrics, or ``None`` when unknown."""
        return getattr(self, "_display_metrics", None)

    def _runtime_hal(self) -> GreiaHAL | None:
        """Return the device HAL for runtime services."""
        return None if self._installed_root() else _development_hal()

    def _runtime_volume_budget(self) -> VolumeBudget | None:
        """Return an injected child-data volume budget, or ``None`` for production.

        ``None`` keeps the production default: measure the real filesystem that
        holds durable profile data. Only host-variation shells (the developer
        Simulator) override this to model a synthetic device volume.
        """
        return None

    def _runtime_adapters(
        self,
    ) -> Sequence[Any] | Mapping[str, Any] | None:
        """Return custom runtime launch adapters, if any."""
        return None

    def _build_bootstrap_services(self, runtime: RuntimeCatalogue, activities: Any) -> Any:
        """Build the shared device/runtime/permission/history authorities.

        Pure construction for the bootstrap coordinator: no Pygame, no live
        launcher mutation. The supervisor is built separately in
        :meth:`_build_bootstrap_supervisor` so subclasses keep their own
        supervisor type without a second service build.
        """

        return build_launcher_runtime_services(
            runtime,
            activities,
            runtime_policy_path=self.paths.runtime_catalogue,
            permission_policy_path=self.paths.permission_policy,
            storage_policy_path=self.paths.storage_policy,
            history_policy_path=self.paths.history_policy,
            progression_policy_path=self.paths.progression_policy,
            hal=self._runtime_hal(),
            volume_budget=self._runtime_volume_budget(),
            runtime_adapters=self._runtime_adapters(),
        )

    def _build_bootstrap_supervisor(self, runtime_services: Any) -> Any:
        """Build the Activity supervisor bound to prepared services.

        Pure construction for the bootstrap coordinator: no Pygame, no live
        launcher mutation. Richer shells override this to build their own
        supervisor type the first time.
        """

        display_coordinator = (
            provisional_installed_display_session() if self._installed_root() else None
        )
        return ActivitySupervisor(
            runtime_manager=runtime_services.runtime_manager,
            storage_service=runtime_services.storage_service,
            history_service=runtime_services.history_service,
            display_coordinator=display_coordinator,
            ready_timeout_seconds=ready_timeout_for(runtime_services),
        )

    def _enter_running_state(self) -> None:
        """Record the interactive loop entry in the boot lifecycle guard."""

        self._boot_lifecycle.mark_running()

    def _rebuild_runtime_services(self) -> None:
        """Bind runtime/permission/history authority to the composed set.

        This is the single boot construction point for the shared services
        and the supervisor. Richer launcher subclasses override it to build
        their own supervisor type the first time, so boot never constructs
        one supervisor only to replace it afterwards.
        """

        runtime_services = self._build_bootstrap_services(self.runtime, self._activities)
        supervisor = self._build_bootstrap_supervisor(runtime_services)
        # Publish the pair only after both objects are completely built. The
        # launch path therefore never observes a supervisor/runtime mismatch.
        self.runtime_services = runtime_services
        self.supervisor = supervisor

    def _enter_parent_panel(self, pygame: Any) -> None:
        """Open the hidden Parent Settings overlay with active text input.

        SDL delivers ``TEXTINPUT`` events only while text input is active.
        Without starting it here the Parent password field can never receive
        typed characters (the profile secret screen is the only other consumer
        of text input and stops it on exit).
        """

        self._mode = "parent_panel"
        self._parent_panel.open()
        self._parent_panel_opened_monotonic = time.monotonic()
        pygame.event.clear(pygame.TEXTINPUT)
        pygame.event.clear(pygame.KEYDOWN)
        pygame.key.start_text_input()

    def _parent_panel_accepts_text(self, now: float) -> bool:
        """Whether typed characters may reach the Parent password field now.

        While the opening chord is still physically held (or within a short
        settle window after open), SDL keeps delivering auto-repeat text from
        the held S/T keys; those characters must never leak into the field.
        """

        if self._parent_chord.is_holding:
            return False
        return now - self._parent_panel_opened_monotonic >= 0.35

    def _exit_parent_panel(self, pygame: Any) -> None:
        """Close the overlay and restore the profile picker input state."""

        self._parent_panel.close()
        pygame.key.stop_text_input()
        self._mode = "profiles"

    def _draw_dimmed_parent_underlay(self, screen: Any, pygame: Any) -> None:
        """Present the profile picker dimmed through one opaque composite.

        Blending a full-screen translucent dim onto the visible surface costs
        more than the rest of the frame combined on Atom-class devices. The
        dimmed copy is therefore rebuilt only when the underlying picker state
        changes and is presented with a fast opaque blit otherwise.
        """

        size = screen.get_size()
        key = (self._cached_profiles_key, size)
        if (
            self._dimmed_underlay is not None
            and self._dimmed_underlay_key == key
            and self._dimmed_underlay.get_size() == size
        ):
            screen.blit(self._dimmed_underlay, (0, 0))
            return
        dimmed = screen.copy()
        dimmed.blit(self._parent_panel.dim_surface(size, pygame), (0, 0))
        self._dimmed_underlay = dimmed.convert()
        self._dimmed_underlay_key = key
        screen.blit(self._dimmed_underlay, (0, 0))

    def run(self) -> int:
        import pygame

        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        emit_boot_marker("pygame_display_init_begin")
        try:
            # Display-only pre-frame init: the handoff/intro needs the
            # display + event/image/transform surface work only. Font
            # rendering is lazily owned by greia_platform.typography
            # (_ensure_pygame) and the mixer stays uninitialized until
            # spoken-label audio first needs it; controller handles open
            # lazily at interactive readiness via _shell_input.start().
            pygame.display.init()
        finally:
            emit_boot_marker("pygame_display_init_end")
        display_flags = pygame.RESIZABLE if self.windowed else pygame.FULLSCREEN
        default_size = (960, 540) if self.windowed else (0, 0)
        emit_boot_marker("display_set_mode_begin")
        try:
            screen = pygame.display.set_mode(default_size, display_flags)
        finally:
            emit_boot_marker("display_set_mode_end")
        remember_viewport(screen.get_size())
        pygame.display.set_caption("Greia OS")
        pygame.mouse.set_visible(False)
        if self._bootstrapped:
            self._enter_running_state()
            self._shell_window_backend.after_window_created(pygame)
        else:
            # Phase 4 order: first flip before runtime preparation. The
            # handoff frame is drawn and flipped first, then the single
            # bounded worker prepares the runtime while the display thread
            # stays responsive. The intro-end boundary below waits (near
            # zero) and applies exactly once.
            self._boot_lifecycle.mark_display_ready()
            executor = create_preparation_worker()
            try:
                from .boot_intro import (
                    _emit_first_frame_flipped_once,
                    draw_boot_handoff_frame,
                )

                draw_boot_handoff_frame(screen, pygame, progress=92)
                pygame.display.flip()
                _emit_first_frame_flipped_once()
                future = self._begin_post_frame_preparation(executor)
                if not self._first_frame_released:
                    self._release_boot_cover()
                try:
                    self._await_and_apply_preparation(future)
                finally:
                    executor.shutdown(wait=False)
            except Exception:
                executor.shutdown(wait=False)
                raise
            self._shell_window_backend.after_window_created(pygame)
            self._enter_running_state()
        clock = pygame.time.Clock()
        running = True
        last_display_size = screen.get_size()

        self._shell_input.start()
        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT and self.allow_exit:
                        running = False
                    elif event.type == pygame.TEXTINPUT:
                        if self._mode == "parent_panel":
                            if self._parent_panel_accepts_text(time.monotonic()):
                                self._parent_panel.handle_text_input(event.text)
                        elif self._mode == "secret":
                            self._handle_secret_text(event.text)
                    elif event.type == pygame.KEYDOWN:
                        if self._mode == "profiles" and self._parent_chord.handle_key_down(
                            event.key, time.monotonic()
                        ):
                            self._enter_parent_panel(pygame)
                        else:
                            running = self._handle_key(event.key, pygame)
                    elif event.type == pygame.KEYUP:
                        self._parent_chord.handle_key_up(event.key)
                    elif event.type == pygame.MOUSEMOTION:
                        self._synthetic_pointer_active = True
                        if hasattr(event, "pos"):
                            pygame.mouse.set_pos(event.pos)
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        if not self._return_tap_swallowed(event.pos):
                            self._handle_click(event.pos, pygame)
                    elif event.type == pygame.VIDEORESIZE and self.windowed:
                        screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                        remember_viewport(screen.get_size())
                    else:
                        action = self._shell_input.translate_event(event)
                        if action is not None:
                            running = self._handle_semantic_action(action, pygame)

                current_surface = pygame.display.get_surface()
                if current_surface is not None:
                    screen = current_surface
                if screen.get_size() != last_display_size:
                    last_display_size = screen.get_size()
                    self._icon_cache.clear()
                    self._font_cache.clear()
                    self._profile_name_cache.clear()
                    self._dimmed_underlay = None
                    self._dimmed_underlay_key = None
                    if self._visual_cache is not None:
                        self._visual_cache.clear()
                if self._mode == "profiles":
                    if self._parent_chord.poll(time.monotonic()):
                        self._enter_parent_panel(pygame)
                elif self._mode == "parent_panel":
                    if self._parent_chord.is_holding:
                        # Drain chord auto-repeat while the keys are down.
                        pygame.event.clear(pygame.TEXTINPUT)
                    self._parent_panel.drain()
                if running:
                    stick_action = self._shell_input.poll_analog(time.monotonic())
                    if stick_action is not None:
                        running = self._handle_semantic_action(stick_action, pygame)
                self._rescan_if_due()
                self._draw(screen, pygame)
                pygame.display.flip()
                if not self._first_frame_released:
                    self._release_boot_cover()
                clock.tick(60)
        finally:
            self._shell_input.close()
            if self.session is not None:
                self.session.clear()
            pygame.key.stop_text_input()
            pygame.quit()
        return 0

    _CONTROLLER_KEY_NAMES = {
        SemanticAction.NAV_LEFT: "K_LEFT",
        SemanticAction.NAV_RIGHT: "K_RIGHT",
        SemanticAction.NAV_UP: "K_UP",
        SemanticAction.NAV_DOWN: "K_DOWN",
        SemanticAction.ACTIVATE: "K_RETURN",
        SemanticAction.CANCEL: "K_ESCAPE",
    }

    def _handle_semantic_action(self, action: ShellInputAction, pygame: Any) -> bool:
        """Deliver one normalized controller action to the active Shell surface.

        Controller input joins the keyboard path at the single ``_handle_key``
        seam (every Shell surface already interprets arrows/Return/Escape
        there), so Home, Collections, the first-boot wizard, the badge shelf,
        the gallery and the Parent panel need no controller-specific code and
        keyboard behavior cannot diverge from it. Section/page and Home are the
        only controller-specific intents; each surface answers them through the
        ``_controller_section`` / ``_controller_go_home`` hooks. Returns the
        loop's ``running`` flag.
        """

        if isinstance(action, ShellControllerCommand):
            if self._controller_text_owned():
                return True
            if action is ShellControllerCommand.HOME:
                self._controller_go_home(pygame)
            else:
                self._controller_section(
                    -1 if action is ShellControllerCommand.SECTION_PREVIOUS else 1,
                    pygame,
                )
            return True
        key_name = self._CONTROLLER_KEY_NAMES.get(action)
        if key_name is None:
            return True
        # A typed secret (profile secret, Parent password) is keyboard-owned: a
        # stray button must not submit an empty one. Cancel still backs out.
        if self._controller_text_owned() and action is not SemanticAction.CANCEL:
            return True
        return self._handle_key(getattr(pygame, key_name), pygame)

    def _controller_text_owned(self) -> bool:
        """True while a surface is collecting a secret from the physical keyboard."""

        if self._mode == "secret":
            return True
        return self._mode == "parent_panel" and self._parent_panel.accepts_typed_text_only

    def _controller_section(self, direction: int, pygame: Any) -> None:
        """Previous (``-1``) / next (``+1``) section or page of the active surface."""

        if self._mode == "parent_panel":
            self._parent_panel.step_section(direction)

    def _controller_go_home(self, pygame: Any) -> None:
        """Reserved Greia Home control: return toward Home, never log out.

        The base Shell has no surface deeper than Home, so this is a no-op;
        richer presentations override it for Collections, galleries and shelves.
        """

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self._mode == "parent_panel":
            running = self._parent_panel.handle_key(key, pygame)
            if not self._parent_panel.is_open:
                self._exit_parent_panel(pygame)
            return running

        if self._mode == "profiles":
            if key in {pygame.K_LEFT, pygame.K_UP} and self.profiles:
                self._profile_selected = (self._profile_selected - 1) % len(self.profiles)
            elif key in {pygame.K_RIGHT, pygame.K_DOWN, pygame.K_TAB} and self.profiles:
                self._profile_selected = (self._profile_selected + 1) % len(self.profiles)
            elif key in {pygame.K_RETURN, pygame.K_SPACE} and self.profiles:
                self._select_profile(self.profiles[self._profile_selected], pygame)
            elif self.allow_exit and key in {pygame.K_ESCAPE, pygame.K_q}:
                return False
            return True

        if self._mode == "secret":
            if key == pygame.K_BACKSPACE:
                self._secret_text = self._secret_text[:-1]
            elif key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                self._attempt_unlock(pygame)
            elif key == pygame.K_ESCAPE:
                self._cancel_unlock(pygame)
            return True

        if key in {pygame.K_LEFT, pygame.K_UP} and self._activities:
            self._selected = (self._selected - 1) % len(self._activities)
        elif key in {pygame.K_RIGHT, pygame.K_DOWN, pygame.K_TAB} and self._activities:
            self._selected = (self._selected + 1) % len(self._activities)
        elif key in {pygame.K_RETURN, pygame.K_SPACE}:
            self._launch_selected(pygame)
        elif key == pygame.K_ESCAPE:
            self._logout(pygame)
        elif self.allow_exit and key == pygame.K_q:
            return False
        return True

    def _handle_secret_text(self, text: str) -> None:
        if time.monotonic() < self._secret_error_until or not text:
            return
        remaining = self.profile_store.policy.max_secret_characters - len(self._secret_text)
        if remaining <= 0:
            return
        accepted = "".join(
            character
            for character in text
            if character not in "\r\n\x00" and character.isprintable()
        )
        self._secret_text += accepted[:remaining]

    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        if self._mode == "parent_panel":
            if not self._parent_panel.handle_click(position, pygame):
                self._exit_parent_panel(pygame)
            return
        for target in reversed(self._targets):
            if not target.rect.collidepoint(position):
                continue
            if target.action == "error_badge_dismiss":
                self._last_result = None
                self._catalogue_error = False
            elif target.action == "profile":
                self._select_profile(target.value, pygame)  # type: ignore[arg-type]
            elif target.action == "unlock":
                self._attempt_unlock(pygame)
            elif target.action == "cancel_unlock":
                self._cancel_unlock(pygame)
            elif target.action == "backspace":
                self._secret_text = self._secret_text[:-1]
            elif target.action == "switch_profile":
                self._logout(pygame)
            elif target.action == "profile_page":
                self._profile_selected = int(target.value)
            elif target.action == "activity_page":
                self._selected = int(target.value)
            elif target.action == "activity":
                self._selected = int(target.value)
                self._launch_selected(pygame)
            return

    def _select_profile(self, profile: ChildProfile, pygame: Any) -> None:
        if profile.has_secret:
            self._pending_profile = profile
            self._secret_text = ""
            self._secret_error_until = 0.0
            self._mode = "secret"
            pygame.key.start_text_input()
            return
        self._activate_profile(profile, pygame)

    def _attempt_unlock(self, pygame: Any) -> None:
        if time.monotonic() < self._secret_error_until:
            return
        profile = self._pending_profile
        if profile is None:
            self._cancel_unlock(pygame)
            return
        try:
            accepted = self.profile_store.verify_secret(profile.profile_id, self._secret_text)
        except ProfileError:
            accepted = False
        if accepted:
            self._activate_profile(profile, pygame)
            return
        self._secret_text = ""
        self._secret_error_until = time.monotonic() + 1.2

    def _cancel_unlock(self, pygame: Any) -> None:
        pygame.key.stop_text_input()
        self._pending_profile = None
        self._secret_text = ""
        self._mode = "profiles"

    def _activate_profile(self, profile: ChildProfile, pygame: Any) -> None:
        try:
            spoken = getattr(self, "_spoken_labels", None)
            if spoken is not None:
                spoken.stop()
        except Exception:
            pass
        pygame.key.stop_text_input()
        context = self.session.activate(self.profile_store, profile.profile_id)
        self._active_profile = context
        self.theme_controller = LauncherThemeController(
            ThemeStore.load(self.paths.theme_defaults, context.customization_dir)
        )
        self._pending_profile = None
        self._secret_text = ""
        self._last_result = None
        self._selected = 0
        self._mode = "activities"
        # The picker's full-screen composition is invisible for the whole
        # profile session; rebuild it on the next logout instead of holding a
        # display-sized surface behind Home and every Activity.
        self._cached_profiles_surface = None
        self._cached_profiles_key = None
        self._cached_profiles_targets = []

    def _logout(self, pygame: Any) -> None:
        try:
            spoken = getattr(self, "_spoken_labels", None)
            if spoken is not None:
                spoken.stop()
        except Exception:
            pass
        pygame.key.stop_text_input()
        self.session.clear()
        self._active_profile = None
        self._pending_profile = None
        self._secret_text = ""
        self._mode = "profiles"
        self.theme_controller = self.selector_theme

    def _launch_selected(self, pygame: Any) -> None:
        try:
            spoken = getattr(self, "_spoken_labels", None)
            if spoken is not None:
                # The Activity (its own process and mixer) takes the
                # foreground: close the Shell mixer so its audio thread does
                # not run for the whole session.
                release = getattr(spoken, "release_audio", None)
                if callable(release):
                    release(pygame)
                else:
                    spoken.stop()
        except Exception:
            pass
        if not self._activities or self._active_profile is None:
            return
        manifest = self._activities[self._selected]
        pygame.event.clear()
        profile_id = self._active_profile.profile.profile_id
        try:
            registration = self.registry.registration_for(manifest)
            authority = self.runtime_services.permission_broker.issue(registration)
        except (ActivityValidationError, PermissionDecisionError):
            self._last_result = None
            self._catalogue_error = True
            return

        # Launch hand-off (see greia_platform.activity_launch_cover): present
        # the launch screen *before* the start work (package validation,
        # brokers, sandbox), then hand its exact pixels to the Activity, whose
        # entry presents them in its new window at once instead of black.
        self._draw_launch_overlay(pygame, text=launch_feedback(getattr(self, "_active_locale", "en")).overlay)
        self._paint_launch_home(pygame, pygame.display.get_surface())
        pygame.display.flip()
        self._on_frame_presented(pygame.display.get_surface(), pygame)
        _launch_feedback = time.monotonic()
        launch_card_dir = self._publish_launch_card(manifest, pygame)
        try:
            self._run_launched_activity(
                pygame, manifest, profile_id, authority, launch_card_dir, _launch_feedback
            )
        finally:
            if launch_card_dir is not None:
                self._launch_card_publisher.discard(launch_card_dir)
            self._arm_return_tap_guard(pygame)

    def _publish_launch_card(self, manifest: ActivityManifest, pygame: Any) -> Path | None:
        """Publish the presented launch screen as this launch's card.

        Returns the Activity data directory holding the card, or ``None``
        (the Activity then covers its window with the theme colour). A stale
        card left by an interrupted earlier launch is removed on failure.
        """

        profile = self._active_profile
        screen = pygame.display.get_surface()
        if profile is None or screen is None:
            return None
        try:
            data_dir = profile.activity_data_dir(manifest.activity_id)
        except (ProfileError, OSError):
            return None
        try:
            card = LaunchCard.from_surface(screen, pygame)
        except Exception:  # fail-soft: no card only means a theme-colour cover
            card = None
        if card is not None and self._launch_card_publisher.publish(data_dir, card):
            return data_dir
        self._launch_card_publisher.discard(data_dir)
        return None

    def _run_launched_activity(
        self,
        pygame: Any,
        manifest: ActivityManifest,
        profile_id: str,
        authority: Any,
        launch_card_dir: Path | None,
        _launch_feedback: float,
    ) -> None:
        try:
            activity_session = self.supervisor.start(
                manifest, self._active_profile, authority
            )
        except Exception as exc:  # containment boundary; logged below
            self._contain_launch_start_failure(manifest, exc)
            return
        self._last_result = activity_session.result
        picker_host = None
        picker_prepare_deadline = 0.0
        picker_next_prepare = 0.0
        # True once the Activity entry painted the card in its own window and
        # removed it: the Shell's wait screen is then hidden behind that
        # window, so repainting it would only steal CPU from the start-up.
        launch_covered = launch_card_dir is None

        try:
            while self._last_result is None:
                # Before READY, Shell events are deliberately discarded. Once a
                # trusted Creations modal is actually visible, only that shared
                # Shell Screen receives Shell-window input; the Activity remains
                # alive behind it and never receives picker-native handles.
                #
                # Simulator remote input normally belongs to its Activity transport.
                # While the trusted modal owns that transport, pull those queued
                # events into the Shell process before draining pygame's queue.
                if picker_host is not None and picker_host.visible:
                    poll_hooks = getattr(self, "_poll_input_hooks", None)
                    if callable(poll_hooks):
                        poll_hooks(pygame)
                events = tuple(pygame.event.get())
                if (
                    not launch_covered
                    and activity_session.state == ActivitySessionState.STARTING
                    and self._launch_home_tapped(pygame, events)
                ):
                    # Home on the Shell's own launch screen (tapped while the
                    # Shell was busy starting the Activity): cancel through the
                    # same lifecycle authority as the trusted chrome.
                    cancel = getattr(self.supervisor, "cancel_launch", None)
                    if callable(cancel):
                        cancel(activity_session)
                self._last_result = self.supervisor.poll(activity_session)
                if self._last_result is not None:
                    break
    
                is_running = activity_session.state == ActivitySessionState.RUNNING
                is_ready = (
                    activity_session.control.ready()
                    if activity_session.control is not None
                    else False
                )
                now = time.monotonic()
    
                if is_running and manifest.creations_consumes:
                    if picker_host is None:
                        from .creation_picker_host import (
                            ActivityCreationPickerHost,
                            CreationPickerHostError,
                        )
    
                        picker_host = ActivityCreationPickerHost(
                            supervisor=self.supervisor,
                            shell_window_backend=self._shell_window_backend,
                            session=activity_session,
                            profile=self._active_profile,
                            typography=self._typography,
                            locale=getattr(self, "_active_locale", "en"),
                            volume_budget=getattr(
                                getattr(self, "runtime_services", None),
                                "volume_budget",
                                None,
                            ),
                            visual_cache=getattr(self, "_visual_cache", None),
                        )
                        # Allow a bounded focus-settling interval after the child
                        # window reports READY; never poll X11 indefinitely.
                        picker_prepare_deadline = now + 1.5
                        picker_next_prepare = now
    
                    if (
                        not picker_host.prepared
                        and now <= picker_prepare_deadline
                        and now >= picker_next_prepare
                    ):
                        picker_next_prepare = now + 0.10
                        try:
                            picker_host.prepare(pygame)
                        except CreationPickerHostError:
                            self._catalogue_error = True
                            self._last_result = self.supervisor.force_stop(
                                activity_session,
                                ActivityExitReason.PLATFORM_FAILURE,
                            )
                            continue
    
                    if picker_host.prepared:
                        try:
                            drew_picker = picker_host.service(pygame, events)
                        except CreationPickerHostError:
                            self._catalogue_error = True
                            try:
                                picker_host.shutdown(
                                    pygame,
                                    activity_alive=activity_session.state
                                    is ActivitySessionState.RUNNING,
                                )
                            finally:
                                self._last_result = self.supervisor.force_stop(
                                    activity_session,
                                    ActivityExitReason.PLATFORM_FAILURE,
                                )
                            continue
                        if drew_picker:
                            pygame.display.flip()
                            self._on_frame_presented(
                                pygame.display.get_surface(), pygame
                            )
                # While no trusted modal is visible the child owns the foreground;
                # never repaint the hidden Shell except for pre-READY feedback
                # that is still visible (not yet covered by the launch card).
                if not launch_covered and not is_running:
                    launch_covered = self._launch_card_publisher.consumed(
                        launch_card_dir
                    )
                    if launch_covered:
                        # The Activity window has just mapped over the trusted
                        # Home shown at launch: raise Home again now (the card
                        # carries Home's picture for these few milliseconds).
                        restack = getattr(
                            self.supervisor, "ensure_system_chrome_visible", None
                        )
                        if callable(restack):
                            restack(activity_session)
                if (
                    not is_running
                    and not is_ready
                    and not launch_covered
                    and self.FOREGROUND_CADENCE.wait_screen_due(now, _launch_feedback)
                ):
                    self._draw_launch_overlay(pygame, text=launch_feedback(getattr(self, "_active_locale", "en")).overlay)
                    self._paint_launch_home(pygame, pygame.display.get_surface())
                    pygame.display.flip()
                    self._on_frame_presented(
                        pygame.display.get_surface(), pygame
                    )
                    _launch_feedback = now
                modal_active = picker_host is not None and (
                    picker_host.visible
                    or (not picker_host.prepared and now <= picker_prepare_deadline)
                )
                time.sleep(
                    self.FOREGROUND_CADENCE.poll_interval(
                        activity_session.state, modal_active=modal_active
                    )
                )
    
        finally:
            if picker_host is not None:
                alive = activity_session.state in {
                    ActivitySessionState.RUNNING,
                    ActivitySessionState.STOPPING,
                }
                if not picker_host.shutdown(
                    pygame, activity_alive=alive
                ):
                    self._catalogue_error = True

        pygame.mouse.set_visible(False)
        pygame.event.clear()
        self._shell_input.start()
        try:
            self.profile_store.consume_avatar_request(profile_id)
            refreshed = self.session.activate(self.profile_store, profile_id)
        except ProfileError:
            self._logout(pygame)
            return
        self._active_profile = refreshed
        self.theme_controller.invalidate()
        self.theme_controller.theme

    def _contain_launch_start_failure(
        self, manifest: ActivityManifest, exc: Exception
    ) -> None:
        """Fail one launch without taking the child Shell down.

        Only the launch screen has been presented; the next Shell frame
        repaints the Collection page with the existing launch-error badge.
        Expected faults log one bounded line; unexpected ones keep their
        traceback.
        """

        detail = str(exc)[:_LAUNCH_ERROR_TEXT_LIMIT]
        if isinstance(exc, EXPECTED_LAUNCH_START_ERRORS):
            logger.error(
                "Activity %s failed to start (%s): %s",
                manifest.activity_id,
                type(exc).__name__,
                detail,
            )
        else:
            logger.exception(
                "Activity %s failed to start with an unexpected %s: %s",
                manifest.activity_id,
                type(exc).__name__,
                detail,
            )
        self._last_result = None
        self._catalogue_error = True

    def _draw_launch_overlay(self, pygame: Any, *, text: str) -> None:
        """Full-screen launch overlay that visibly blocks interaction."""
        screen = pygame.display.get_surface()
        if screen is None:
            return
        width, height = screen.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((255, 250, 240, 245))
        screen.blit(overlay, (0, 0))
        center = screen.get_rect().center
        # Panel
        panel = pygame.Rect(0, 0, min(360, width - 60), 170)
        panel.center = center
        pygame.draw.rect(screen, (247, 235, 203), panel, border_radius=24)
        pygame.draw.rect(screen, (61, 44, 31), panel, width=2, border_radius=24)
        # Pulsing dots
        now = time.monotonic()
        for index in range(3):
            phase = (now * 2.0 + index * 0.8) % 2.0
            radius = int(5 + 5 * (1.0 - abs(phase - 1.0)))
            dot_center = (center[0] - 30 + index * 30, center[1] - 40)
            pygame.draw.circle(screen, (255, 194, 52), dot_center, radius)
        # Message
        font = self._typography.font(FontRole.CONTROL, 32)
        label = font.render(text, True, (61, 44, 31))
        screen.blit(label, label.get_rect(center=(center[0], center[1] + 25)))
        hint = self._typography.font(FontRole.BODY, 20)
        hint_label = hint.render(launch_feedback(getattr(self, "_active_locale", "en")).wait, True, (130, 120, 100))
        screen.blit(hint_label, hint_label.get_rect(center=(center[0], center[1] + 65)))

    def _paint_launch_home(self, pygame: Any, screen: Any) -> None:
        """Protected Home on the launch screen (ADR 0019), drawn by the Shell.

        The trusted chrome backend paints its own Home picture at the
        protected location, so Home is visible from the first launch frame,
        while the Shell is still starting the Activity, and the launch card
        the Activity repaints carries it too. Taps on it are answered by
        :meth:`_launch_home_tapped` while the Shell window is on top; the
        trusted chrome window takes over the region once it is shown.
        """

        paint = getattr(self.supervisor, "paint_launch_home", None)
        self._launch_home_box = (
            paint(screen, pygame) if callable(paint) and screen is not None else None
        )

    def _arm_return_tap_guard(self, pygame: Any) -> None:
        """The Shell is back in front: ignore a stray Home/Back tap for a moment.

        See :mod:`greia_launcher.return_tap_guard`: a repeated Activity Home
        tap must not land on the active-profile switcher drawn underneath it.
        """

        screen = pygame.display.get_surface()
        if screen is None:
            self._return_tap_guard = ReturnTapGuard()
            return
        width, height = screen.get_size()
        self._return_tap_guard = ReturnTapGuard.after_activity(
            width,
            height,
            time.monotonic(),
            home_box=getattr(self, "_launch_home_box", None),
        )

    def _return_tap_swallowed(self, position: tuple[int, int]) -> bool:
        """Whether a primary release is a stray tap aimed at an ended Activity's chrome."""

        guard = getattr(self, "_return_tap_guard", None)
        return guard is not None and guard.swallows(position, time.monotonic())

    def _launch_home_tapped(self, pygame: Any, events: tuple[Any, ...]) -> bool:
        """Whether a primary release landed on the launch screen's Home."""

        box = getattr(self, "_launch_home_box", None)
        if box is None:
            return False
        for event in events:
            if getattr(event, "type", None) == pygame.MOUSEBUTTONUP and getattr(event, "button", 0) == 1:
                x, y = event.pos
                if box.x <= x < box.x + box.width and box.y <= y < box.y + box.height:
                    return True
        return False

    def _installed_root(self) -> bool:
        from .installed_root import is_installed_root

        return is_installed_root(self.paths.root)

    def _rescan_if_due(self) -> bool:
        now = time.monotonic()
        if now < self._next_rescan:
            return False
        self._next_rescan = now + self.RESCAN_SECONDS
        changed_act = self._rescan_activities()
        changed_prof = self._rescan_profiles()
        return bool(changed_act or changed_prof)

    def _on_frame_presented(self, screen: Any, pygame: Any) -> None:
        """Hook called immediately after a frame is presented."""

    def _rescan_activities(self) -> bool:
        token = self.registry.discovery_token()
        if token == self._activity_discovery_token:
            return False
        # Remember even a broken/incomplete package state so the Acer does not
        # reparse the same invalid tree every two seconds. A later file/directory
        # change produces another token and retries validation.
        self._activity_discovery_token = token
        selected_id = (
            self._activities[self._selected].activity_id
            if self._activities and self._selected < len(self._activities)
            else None
        )
        try:
            discovered = self.registry.discover()
        except ActivityValidationError:
            changed = not self._catalogue_error
            self._catalogue_error = True
            return changed
        self._catalogue_error = False
        previous = self._activities
        self._activities = discovered
        self._selected = 0
        if selected_id:
            for index, activity in enumerate(discovered):
                if activity.activity_id == selected_id:
                    self._selected = index
                    break
        return previous != discovered

    def _rescan_profiles(self) -> bool:
        try:
            profiles = self.profile_store.list_profiles()
        except ProfileError:
            return False
        previous = self.profiles
        if profiles == previous:
            return False
        selected_id = (
            self.profiles[self._profile_selected].profile_id
            if self.profiles and self._profile_selected < len(self.profiles)
            else None
        )
        self.profiles = profiles
        self._profile_selected = 0
        if selected_id:
            for index, profile in enumerate(profiles):
                if profile.profile_id == selected_id:
                    self._profile_selected = index
                    break
        if self._pending_profile and not any(
            profile.profile_id == self._pending_profile.profile_id for profile in profiles
        ):
            self._pending_profile = None
            self._secret_text = ""
            self._mode = "profiles"
        if self._active_profile is not None:
            matching = next(
                (
                    profile
                    for profile in profiles
                    if profile.profile_id == self._active_profile.profile.profile_id
                ),
                None,
            )
            if matching is None:
                self.session.clear()
                self._active_profile = None
                self._mode = "profiles"
                self.theme_controller = self.selector_theme
            elif matching != self._active_profile.profile:
                try:
                    self._active_profile = self.session.activate(
                        self.profile_store, matching.profile_id
                    )
                except ProfileError:
                    self.session.clear()
                    self._active_profile = None
                    self._mode = "profiles"
                    self.theme_controller = self.selector_theme
        return True

    def _draw(self, screen: Any, pygame: Any) -> None:
        self._targets.clear()
        theme = self.theme_controller.draw_background(screen, pygame)
        if self._mode == "parent_panel":
            self._draw_profile_picker(screen, theme, pygame)
            self._draw_dimmed_parent_underlay(screen, pygame)
            self._parent_panel.draw(
                screen,
                theme,
                self._typography,
                pygame,
                self._load_icon,
                draw_backdrop=False,
                base_surface=self._dimmed_underlay,
                base_key=self._dimmed_underlay_key,
            )
        elif self._mode == "profiles":
            self._draw_profile_picker(screen, theme, pygame)
        elif self._mode == "secret":
            self._draw_secret_entry(screen, theme, pygame)
        else:
            self._draw_activities(screen, theme, pygame)
        self._draw_pointer(screen, pygame)

    def _draw_profile_picker(self, screen: Any, theme: Any, pygame: Any) -> None:
        width, height = screen.get_size()
        if not self.profiles:
            self._draw_empty(screen, pygame)
            return

        pointer = pygame.mouse.get_pos()
        pointer_active = pygame.mouse.get_focused()

        hovered_target = None
        if (
            self._mode != "parent_panel"
            and pointer_active
            and self._cached_profiles_targets
        ):
            # While the Parent Settings modal is open its dim layer covers the
            # picker: hover there is invisible and clicks go to the overlay.
            # Computing it anyway changed the cache key whenever the pointer
            # crossed a hidden tile (e.g. beneath the password field) and
            # forced a full picker rebuild plus a full-screen dim recomposite
            # on an Atom-class CPU.
            for target in self._cached_profiles_targets:
                if target.rect.collidepoint(pointer):
                    hovered_target = (target.action, target.value)
                    break

        cache_key = (
            self._profile_selected,
            tuple(p.profile_id for p in self.profiles),
            hovered_target,
            getattr(self, "_active_locale", "en"),
            theme.background,
            theme.panel,
            theme.accent,
            theme.text,
            (width, height),
        )

        if self._cached_profiles_key == cache_key and self._cached_profiles_surface is not None:
            screen.blit(self._cached_profiles_surface, (0, 0))
            self._targets.extend(self._cached_profiles_targets)
            return

        if (
            self._cached_profiles_surface is None
            or self._cached_profiles_surface.get_size() != (width, height)
        ):
            self._cached_profiles_surface = pygame.Surface((width, height)).convert()

        self._cached_profiles_surface.fill(theme.background)
        saved_targets = self._targets
        self._targets = []

        self._render_profile_picker_content(self._cached_profiles_surface, theme, pygame)

        self._cached_profiles_key = cache_key
        self._cached_profiles_targets = list(self._targets)
        saved_targets.extend(self._targets)
        self._targets = saved_targets
        screen.blit(self._cached_profiles_surface, (0, 0))

    def _render_profile_picker_content(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        width, height = screen.get_size()
        header_size = max(70, min(100, height // 6))
        header_icon = self._load_icon("rainbow", header_size, pygame)
        screen.blit(header_icon, header_icon.get_rect(center=(width // 2, header_size // 2 + 8)))
        if not self.profiles:
            self._draw_empty(screen, pygame)
            return

        if height <= 400 and width >= 480:
            # Short landscape screens: one wide row keeps each card finger-sized.
            columns = min(4, len(self.profiles))
        else:
            columns = min(4 if width >= 900 else 3 if width >= 700 else 2, len(self.profiles))
        page = calculate_grid_page(
            len(self.profiles), self._profile_selected, columns=columns, max_rows=2
        )
        gap = max(12, min(22, width // 48))
        inner_panel = (
            getattr(self, "_shared_panel_inner_rect", None)
            if not getattr(self, "_shared_panel_disabled", False)
            else None
        )
        from .navigation_layout import (
            compute_navigation_safe_content_bounds,
            resolve_page_button_size,
        )
        from greia_platform.responsive_layout import UiRect, Viewport

        viewport = Viewport(width, height)
        panel_layout = getattr(self, "_shell_panel_layout", None)
        panel_outer = (
            panel_layout.outer_rect
            if panel_layout is not None
            else (UiRect(inner_panel.x, inner_panel.y, inner_panel.width, inner_panel.height) if inner_panel is not None else None)
        )
        nav_button_size = resolve_page_button_size(
            viewport,
            self._chrome_metrics(),
            panel_outer_rect=panel_outer if inner_panel is not None else None,
        )
        pagination_reserve = 38 if page.page_count > 1 else 0
        if inner_panel is not None:
            pad_x = max(14, inner_panel.width // 45)
            pad_y = max(8, inner_panel.height // 40)
            avail_w = max(240, inner_panel.width - pad_x * 2)
            avail_h = max(180, inner_panel.height - pad_y * 2 - pagination_reserve)
            if page.page_count > 1:
                safe_rect = compute_navigation_safe_content_bounds(
                    viewport,
                    panel_outer_rect=panel_outer,
                    available_content_rect=UiRect(inner_panel.x + pad_x, inner_panel.y + pad_y, avail_w, avail_h),
                    button_size=nav_button_size,
                )
                avail_w = safe_rect.width
                safe_origin_x = safe_rect.x
            else:
                safe_origin_x = inner_panel.x + pad_x

            max_tile_w = max(1, (avail_w - gap * (page.columns - 1)) // page.columns)
            max_tile_h = max(1, (avail_h - gap * max(0, page.rows - 1)) // max(1, page.rows))
            tile_w = min(224, max_tile_w)
            tile_h = min(236, max_tile_h)
            tile_w = max(1, min(max_tile_w, max(110, tile_w)))
            tile_h = max(1, min(max_tile_h, max(120, tile_h)))
            total_w = page.columns * tile_w + (page.columns - 1) * gap
            total_h = page.rows * tile_h + max(0, page.rows - 1) * gap
            origin_x = safe_origin_x + (avail_w - total_w) // 2
            origin_y = inner_panel.top + pad_y + max(0, (avail_h - total_h) // 2)
        else:
            top = header_size + 12
            available_h = height - top - 18 - pagination_reserve
            raw_content = UiRect(0, top, width, available_h)
            if page.page_count > 1:
                safe_rect = compute_navigation_safe_content_bounds(
                    viewport,
                    available_content_rect=raw_content,
                    button_size=nav_button_size,
                )
                usable_w = safe_rect.width
                safe_origin_x = safe_rect.x
            else:
                side_reserve = 30
                usable_w = max(240, width - side_reserve)
                safe_origin_x = (width - usable_w) // 2

            max_tile_w = max(1, (usable_w - gap * (page.columns - 1)) // page.columns)
            max_tile_h = max(1, (available_h - gap * max(0, page.rows - 1)) // max(1, page.rows))
            tile_w = min(224, max_tile_w)
            tile_h = min(236, max_tile_h)
            tile_w = max(1, min(max_tile_w, max(110, tile_w)))
            tile_h = max(1, min(max_tile_h, max(120, tile_h)))
            total_w = page.columns * tile_w + (page.columns - 1) * gap
            total_h = page.rows * tile_h + max(0, page.rows - 1) * gap
            origin_x = safe_origin_x + max(0, (usable_w - total_w) // 2)
            origin_y = top + max(0, (available_h - total_h) // 2)
        self._page_content_rect = UiRect(origin_x, origin_y, total_w, total_h)

        pointer = pygame.mouse.get_pos()
        pointer_active = pygame.mouse.get_focused()

        for local_index, global_index in enumerate(range(page.start, page.stop)):
            profile = self.profiles[global_index]
            column = local_index % page.columns
            row = local_index // page.columns
            rect = pygame.Rect(
                origin_x + column * (tile_w + gap),
                origin_y + row * (tile_h + gap),
                tile_w,
                tile_h,
            )
            selected = global_index == self._profile_selected
            hovered = pointer_active and rect.collidepoint(pointer)
            self._draw_profile_card(screen, rect, profile, selected, hovered, theme, pygame)
            self._targets.append(HitTarget("profile", profile, rect))

        self._draw_page_controls(
            screen,
            theme,
            pygame,
            page,
            previous_action="profile_page",
            next_action="profile_page",
            total=len(self.profiles),
        )
        self._draw_parent_hold_hint(screen, theme, pygame, width, height)

    def _draw_parent_hold_hint(
        self, screen: Any, theme: Any, pygame: Any, width: int, height: int
    ) -> None:
        """Small adult-facing S + T hint required on the profile picker.

        It is not a control and owns no hit target. The hint is deliberately
        word-light and localized through the same device-language catalog as
        the rest of the Shell.
        """
        from greia_platform.system_language import language_ui

        text = language_ui(
            getattr(self, "_active_locale", "en"), "shell"
        ).get("parent_hold_hint", "").strip()
        if not text:
            text = "For parents: hold S + T for 5 seconds"
        font_size = max(10, min(14, height // 40))
        font = self._font(font_size, pygame)
        label = font.render(text, True, theme.text)
        padding_x = max(8, font_size // 2)
        padding_y = max(4, font_size // 3)
        pill = pygame.Rect(
            10,
            10,
            min(width - 20, label.get_width() + padding_x * 2),
            label.get_height() + padding_y * 2,
        )
        pygame.draw.rect(screen, theme.panel, pill, border_radius=max(8, height // 60))
        pygame.draw.rect(
            screen,
            _mix(theme.text, theme.panel, 0.72),
            pill,
            width=1,
            border_radius=max(8, height // 60),
        )
        screen.blit(label, label.get_rect(center=pill.center))

    def _draw_profile_card(
        self,
        screen: Any,
        rect: Any,
        profile: Any,
        selected: bool,
        hovered: bool,
        theme: Any,
        pygame: Any,
    ) -> None:
        """Primitive / fallback profile card presentation."""
        is_highlighted = selected or hovered
        drawn = rect.move(0, -2 if is_highlighted else 0)

        # Grounding drop shadow
        shadow_rect = drawn.move(0, 4 if is_highlighted else 2)
        shadow_color = _mix(theme.background, (0, 0, 0), 0.14 if is_highlighted else 0.08)
        pygame.draw.rect(screen, shadow_color, shadow_rect, border_radius=26)

        # Card fill
        card_bg = _mix(theme.panel, (255, 255, 255), 0.35) if is_highlighted else theme.panel
        pygame.draw.rect(screen, card_bg, drawn, border_radius=26)

        # Subtle top sheen highlight line
        sheen_color = _mix(card_bg, (255, 255, 255), 0.60)
        pygame.draw.line(
            screen,
            sheen_color,
            (drawn.left + 24, drawn.top + 2),
            (drawn.right - 24, drawn.top + 2),
            width=1,
        )

        # Outline
        outline_color = theme.accent if is_highlighted else _mix(theme.text, theme.panel, 0.72)
        outline_width = 6 if selected else (3 if hovered else 2)
        pygame.draw.rect(
            screen,
            outline_color,
            drawn,
            width=outline_width,
            border_radius=26,
        )
        icon_size = min(int(drawn.width * 0.58), int(drawn.height * 0.58))
        icon = self._load_icon(profile.avatar_id, icon_size, pygame)
        screen.blit(icon, icon.get_rect(center=(drawn.centerx, drawn.top + drawn.height * 0.40)))
        font_size = max(23, min(38, drawn.height // 6))
        max_name_width = drawn.width - 18
        name = self._profile_name_surface(
            self._child_display_text(profile.display_name),
            font_size,
            max_name_width,
            theme.text,
            pygame,
        )
        screen.blit(name, name.get_rect(center=(drawn.centerx, drawn.bottom - drawn.height * 0.15)))
        if profile.has_secret:
            lock = self._load_icon("yellow_star", max(26, drawn.width // 7), pygame)
            screen.blit(lock, lock.get_rect(topright=(drawn.right - 8, drawn.top + 8)))

    def _draw_secret_entry(self, screen: Any, theme: Any, pygame: Any) -> None:
        width, height = screen.get_size()
        profile = self._pending_profile
        if profile is None:
            return
        avatar_size = max(110, min(190, height // 3))
        avatar = self._load_icon(profile.avatar_id, avatar_size, pygame)
        screen.blit(avatar, avatar.get_rect(center=(width // 2, height // 4)))
        name = self._font(max(30, min(48, height // 11)), pygame).render(
            profile.display_name, True, theme.text
        )
        screen.blit(name, name.get_rect(center=(width // 2, height // 2 - 54)))
        entry = pygame.Rect(width // 2 - min(300, width // 3), height // 2, min(600, width * 2 // 3), max(74, height // 8))
        pygame.draw.rect(screen, theme.panel, entry, border_radius=20)
        border = self.ERROR if time.monotonic() < self._secret_error_until else theme.accent
        pygame.draw.rect(screen, border, entry, width=7, border_radius=20)
        visible = "•" * len(self._secret_text) if profile.mask_secret else self._secret_text
        text_surface = self._font(max(32, min(50, entry.height // 2)), pygame).render(
            visible or "…", True, theme.text
        )
        if text_surface.get_width() > entry.width - 28:
            text_surface = text_surface.subsurface(
                (text_surface.get_width() - entry.width + 28, 0, entry.width - 28, text_surface.get_height())
            ).copy()
        screen.blit(text_surface, text_surface.get_rect(midleft=(entry.left + 18, entry.centery)))
        button_size = max(68, min(92, height // 7))
        gap = 24
        total_buttons_w = 3 * button_size + 2 * gap
        buttons_start_x = width // 2 - total_buttons_w // 2
        cancel = pygame.Rect(buttons_start_x, entry.bottom + 22, button_size, button_size)
        erase = pygame.Rect(buttons_start_x + button_size + gap, entry.bottom + 22, button_size, button_size)
        accept = pygame.Rect(buttons_start_x + 2 * (button_size + gap), entry.bottom + 22, button_size, button_size)
        for rect, icon_id, action in (
            (cancel, "close_button", "cancel_unlock"),
            (erase, "abc_board", "backspace"),
            (accept, "check", "unlock"),
        ):
            pygame.draw.rect(screen, theme.panel, rect, border_radius=20)
            pygame.draw.rect(screen, theme.accent, rect, width=5, border_radius=20)
            icon = self._load_icon(icon_id, rect.width - 14, pygame)
            screen.blit(icon, icon.get_rect(center=rect.center))
            self._targets.append(HitTarget(action, None, rect))

    def _draw_activities(self, screen: Any, theme: Any, pygame: Any) -> None:
        width, height = screen.get_size()
        if self._active_profile is not None:
            badge_size = max(62, min(86, height // 7))
            badge = pygame.Rect(14, 10, badge_size, badge_size)
            pygame.draw.rect(screen, theme.panel, badge, border_radius=22)
            pygame.draw.rect(screen, theme.accent, badge, width=5, border_radius=22)
            avatar = self._load_icon(self._active_profile.profile.avatar_id, badge_size - 12, pygame)
            screen.blit(avatar, avatar.get_rect(center=badge.center))
            self._targets.append(HitTarget("switch_profile", None, badge))
        if not self._activities:
            self._draw_empty(screen, pygame)
            return

        columns = min(3 if width >= 760 else 2, len(self._activities))
        page = calculate_grid_page(
            len(self._activities), self._selected, columns=columns, max_rows=2
        )
        top = max(92, height // 7)
        available_h = height - top - 24
        side_reserve = 150 if page.page_count > 1 else 30
        gap = max(16, min(26, width // 42))
        usable_w = max(240, width - side_reserve)
        tile_size = min(
            218,
            (usable_w - gap * (page.columns - 1)) // page.columns,
            (available_h - gap * max(0, page.rows - 1)) // max(1, page.rows),
        )
        tile_size = max(115, tile_size)
        total_width = page.columns * tile_size + (page.columns - 1) * gap
        total_height = page.rows * tile_size + max(0, page.rows - 1) * gap
        origin_x = (width - total_width) // 2
        origin_y = top + max(0, (available_h - total_height) // 2)
        for local_index, global_index in enumerate(range(page.start, page.stop)):
            activity = self._activities[global_index]
            column = local_index % page.columns
            row = local_index // page.columns
            rect = pygame.Rect(
                origin_x + column * (tile_size + gap),
                origin_y + row * (tile_size + gap),
                tile_size,
                tile_size,
            )
            selected = global_index == self._selected
            self._draw_activity_tile(screen, rect, activity, selected, theme, pygame)
            self._targets.append(HitTarget("activity", global_index, rect))

        self._draw_page_controls(
            screen,
            theme,
            pygame,
            page,
            previous_action="activity_page",
            next_action="activity_page",
            total=len(self._activities),
        )
        if (self._last_result and not self._last_result.succeeded) or self._catalogue_error:
            self._draw_error_badge(screen, pygame)

    def _draw_page_controls(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        page: Any,
        *,
        previous_action: str = "",
        next_action: str = "",
        total: int = 0,
    ) -> None:
        from .navigation_layout import (
            PageControlsState,
            resolve_page_button_size,
            resolve_page_controls_layout,
        )
        from greia_platform.responsive_layout import Viewport

        if isinstance(page, PageControlsState):
            page_state = page
        else:
            page_state = PageControlsState.from_grid_page(
                page,
                total=total,
                previous_action=previous_action,
                next_action=next_action,
            )

        if page_state.page_count <= 1:
            return
        viewport = Viewport(screen.get_width(), screen.get_height())
        panel_layout = getattr(self, "_shell_panel_layout", None)
        panel_outer = panel_layout.outer_rect if panel_layout else None
        size = resolve_page_button_size(
            viewport,
            self._chrome_metrics(),
            panel_outer_rect=panel_outer,
        )
        layout = resolve_page_controls_layout(
            viewport,
            page_state,
            panel_outer_rect=panel_outer,
            panel_content_rect=getattr(self, "_page_content_rect", None),
            button_size=size,
        )
        pointer = pygame.mouse.get_pos()
        pointer_active = pygame.mouse.get_focused()
        controls = (
            (
                "previous",
                pygame.Rect(
                    layout.previous_rect.x,
                    layout.previous_rect.y,
                    layout.previous_rect.width,
                    layout.previous_rect.height,
                ),
                page_state.previous_action or previous_action,
                page_state.previous_value,
                page_state.can_go_previous,
            ),
            (
                "next",
                pygame.Rect(
                    layout.next_rect.x,
                    layout.next_rect.y,
                    layout.next_rect.width,
                    layout.next_rect.height,
                ),
                page_state.next_action or next_action,
                page_state.next_value,
                page_state.can_go_next,
            ),
        )
        for direction, rect, action, target_val, enabled in controls:
            if not enabled:
                continue
            hovered = pointer_active and rect.collidepoint(pointer)
            self._draw_page_arrow_button(
                screen, theme, pygame, direction, rect, hovered
            )
            if action:
                self._targets.append(HitTarget(action, target_val, rect))

    def _draw_arrow_glyph(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        direction: str,
        drawn: Any,
        hovered: bool,
    ) -> None:
        """Draw a chunky directional arrow glyph centered within a button."""
        cx, cy = drawn.center
        scale = drawn.width / 52.0
        optical_shift = max(1, int(round(1.5 * scale)))
        if direction == "previous":
            cx += optical_shift
        else:
            cx -= optical_shift
        shaft_len = max(8, int(15 * scale))
        shaft_h = max(6, int(10 * scale))
        head_len = max(8, int(13 * scale))
        head_half_h = max(7, int(13 * scale))
        corner_r = max(2, int(2.5 * scale))

        glyph_color = (
            _mix(theme.accent, (40, 20, 10), 0.30) if hovered else theme.text
        )

        if direction == "previous":
            tip_x = cx - int(13 * scale)
            base_x = tip_x + head_len
            shaft_x = base_x - int(2 * scale)
            shaft_rect = pygame.Rect(shaft_x, cy - shaft_h // 2, shaft_len, shaft_h)
            head_pts = ((tip_x, cy), (base_x, cy - head_half_h), (base_x, cy + head_half_h))
        else:
            tip_x = cx + int(13 * scale)
            base_x = tip_x - head_len
            shaft_x = base_x - shaft_len + int(2 * scale)
            shaft_rect = pygame.Rect(shaft_x, cy - shaft_h // 2, shaft_len, shaft_h)
            head_pts = ((tip_x, cy), (base_x, cy - head_half_h), (base_x, cy + head_half_h))

        # Soft optical drop shadow
        shadow_shaft = shaft_rect.move(0, 1)
        shadow_pts = tuple((p[0], p[1] + 1) for p in head_pts)
        shadow_color = _mix(theme.background, (0, 0, 0), 0.16)
        pygame.draw.rect(screen, shadow_color, shadow_shaft, border_radius=corner_r)
        pygame.draw.polygon(screen, shadow_color, shadow_pts)
        for p in shadow_pts:
            pygame.draw.circle(screen, shadow_color, p, corner_r)

        # Foreground glyph
        pygame.draw.rect(screen, glyph_color, shaft_rect, border_radius=corner_r)
        pygame.draw.polygon(screen, glyph_color, head_pts)
        for p in head_pts:
            pygame.draw.circle(screen, glyph_color, p, corner_r)

    def _draw_page_arrow_button(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        direction: str,
        rect: Any,
        hovered: bool,
    ) -> None:
        """Procedural tactile circular navigation button with chunky arrow glyph."""
        drawn = rect.move(0, -2 if hovered else 0)

        # Procedural circular tactile button
        cx, cy = drawn.center
        radius = drawn.width // 2
        shadow_cy = cy + 3
        pygame.draw.circle(screen, (61, 44, 31, 40), (cx, shadow_cy), radius)
        fill = (255, 255, 255) if hovered else (255, 253, 248)
        pygame.draw.circle(screen, fill, (cx, cy), radius)
        ring_color = (255, 214, 110) if hovered else (242, 230, 212)
        pygame.draw.circle(screen, ring_color, (cx, cy), radius - 3, width=2)
        border_color = (
            theme.accent if hovered else _mix(theme.text, theme.panel, 0.72)
        )
        pygame.draw.circle(
            screen,
            border_color,
            (cx, cy),
            radius,
            width=3 if hovered else 2,
        )
        sheen = (255, 255, 255)
        pygame.draw.line(
            screen,
            sheen,
            (cx - int(radius * 0.55), cy - radius + 4),
            (cx + int(radius * 0.55), cy - radius + 4),
            width=2,
        )

        self._draw_arrow_glyph(screen, theme, pygame, direction, drawn, hovered)

    def _draw_activity_tile(
        self,
        screen: Any,
        rect: Any,
        activity: ActivityManifest,
        selected: bool,
        theme: Any,
        pygame: Any,
    ) -> None:
        border = 8 if selected else 3
        border_color = theme.accent if selected else _mix(theme.text, theme.panel, 0.72)
        pygame.draw.rect(screen, theme.panel, rect, border_radius=24)
        pygame.draw.rect(screen, border_color, rect, width=border, border_radius=24)
        icon_size = int(rect.width * 0.62)
        icon = self._load_icon(activity.icon_id, icon_size, pygame)
        screen.blit(icon, icon.get_rect(center=(rect.centerx, rect.centery - rect.height * 0.06)))

    def _load_icon(self, icon_id: str, size: int, pygame: Any) -> Any:
        cache_key = (icon_id, size)
        cached = self._icon_cache.get(cache_key)
        if cached is not None:
            return cached
        asset = self.assets.get(icon_id)
        path = asset.path_256 if size > 128 else asset.path_128
        image = pygame.image.load(str(path)).convert_alpha()
        image = pygame.transform.smoothscale(image, (size, size))
        self._icon_cache[cache_key] = image
        return image

    def _font(self, size: int, pygame: Any) -> Any:
        size = max(10, size)
        font = self._font_cache.get(size)
        if font is None:
            font = self._typography.font(FontRole.TITLE, size)
            self._font_cache[size] = font
        return font

    def _profile_name_surface(
        self,
        name: str,
        font_size: int,
        max_width: int,
        color: tuple[int, int, int],
        pygame: Any,
    ) -> Any:
        key = (name, font_size, max_width, color)
        cached = self._profile_name_cache.get(key)
        if cached is not None:
            return cached
        rendered = self._font(font_size, pygame).render(name, True, color)
        if rendered.get_width() > max_width:
            scaled = pygame.transform.smoothscale(
                rendered,
                (
                    max_width,
                    max(1, round(rendered.get_height() * max_width / rendered.get_width())),
                ),
            )
        else:
            scaled = rendered
        self._profile_name_cache[key] = scaled
        return scaled

    def _draw_pointer(self, screen: Any, pygame: Any) -> None:
        if not pygame.mouse.get_focused():
            return
        from greia_platform.activity_ui import draw_activity_pointer

        pos = pygame.mouse.get_pos()
        draw_activity_pointer(screen, pos)

    def _draw_empty(self, screen: Any, pygame: Any) -> None:
        self._boot_logo(screen, pygame, screen.get_rect().center)

    def _boot_logo(self, screen: Any, pygame: Any, center: tuple[int, int]) -> None:
        cache_key = ("boot-logo", self.paths.root)
        image = self._icon_cache.get(cache_key)
        if image is None:
            frame_path = _canonical_boot_logo(self.paths.root)
            source = frame_path if frame_path is not None else None
            if source is None:
                fallback = self.assets.get("robot")
                image = pygame.image.load(str(fallback.path_256)).convert_alpha()
            else:
                image = pygame.image.load(str(source)).convert_alpha()
            max_height = max(120, min(300, screen.get_height() // 3))
            if image.get_width() > image.get_height():
                width = max_height
                height = int(image.get_height() * width / image.get_width())
            else:
                height = max_height
                width = int(image.get_width() * height / image.get_height())
            image = pygame.transform.smoothscale(image, (width, height)).convert_alpha()
            self._icon_cache[cache_key] = image
        screen.blit(image, image.get_rect(center=center))

    def _draw_error_badge(self, screen: Any, pygame: Any) -> None:
        size = max(44, min(64, screen.get_height() // 10))
        icon = self._load_icon("close_button", size, pygame)
        badge_rect = icon.get_rect(topright=(screen.get_width() - 14, 14))
        screen.blit(icon, badge_rect)
        self._targets.append(HitTarget("error_badge_dismiss", 0, badge_rect))

    def _release_boot_cover(self) -> None:
        if self.windowed or os.environ.get("GREIA_SKIP_BOOT_HANDOFF") == "1":
            self._first_frame_released = True
            return
        now = time.monotonic()
        if now < self._next_boot_handoff_attempt:
            return
        self._next_boot_handoff_attempt = now + 0.5
        handoff = Path("/usr/local/lib/greia-os/release-boot-cover")
        if handoff.exists():
            completed = subprocess.run([str(handoff)], check=False, shell=False)
            self._first_frame_released = completed.returncode == 0


DEVELOPER_SOURCE_ID = "greia-developer-remote"
BUILT_IN_SOURCE_ID = "greia-system"
DEVELOPER_MARKER_PATH = Path("/etc/greia-os/developer-remote")
DEVELOPER_MARKER_ENV_VAR = "GREIA_DEVELOPER_REMOTE_MARKER"


def developer_marker_path() -> Path:
    """Return the explicit developer-image marker path (env-overridable for tests).

    The default matches the platform developer-remote contract
    (``/etc/greia-os/developer-remote``); ``GREIA_DEVELOPER_REMOTE_MARKER``
    overrides it the same way the Parent package API already does.
    """

    override = os.environ.get(DEVELOPER_MARKER_ENV_VAR)
    if override is not None and override.strip():
        return Path(override.strip())
    return DEVELOPER_MARKER_PATH


def is_developer_mode() -> bool:
    """Whether the explicit developer-mode path is enabled on this machine.

    Developer mode requires the developer-image marker file. The mere
    presence of ``GREIA_DEVELOPER_ACTIVITY_ROOT`` is not sufficient: production
    child boot must not pay developer-mode discovery cost because an
    environment variable happens to be set.
    """

    try:
        return developer_marker_path().is_file()
    except (OSError, ValueError):
        return False


def developer_activity_source(
    developer_root: Path | None,
) -> ActivitySource | None:
    """Return the explicit live-discovery developer source, or ``None``.

    Returns ``None`` when developer mode is off or no developer root is
    configured. The returned source always carries
    ``DEVELOPER_UNSIGNED``/``greia-developer-remote`` trust: developer packages
    are validated live by ``ActivityRegistry`` on this path and are never
    promoted to built-in trust, nor is any developer index consumed as a
    built-in index (the launcher consumes no index on this path).
    """

    if developer_root is None:
        return None
    if not is_developer_mode():
        return None
    return ActivitySource(
        developer_root,
        trust=PackageTrust.DEVELOPER_UNSIGNED,
        source_id=DEVELOPER_SOURCE_ID,
    )


def _optional_absolute_path_from_environment(name: str) -> Path | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    path = Path(value.strip())
    if not path.is_absolute():
        raise ActivityValidationError(f"{name} must be an absolute path")
    return path.resolve()


def _activity_sources(paths: LauncherPaths) -> tuple[ActivitySource, ...]:
    """Compose the configured sources including the developer root when set.

    This helper preserves the historical environment-gated composition and its
    trust/overlap rules. Production child boot must not call it directly;
    use :func:`boot_activity_sources`, which suppresses the developer source
    unless explicit developer mode is enabled.
    """

    sources = [
        ActivitySource(
            paths.activities,
            trust=PackageTrust.BUILT_IN,
            source_id="greia-system",
        )
    ]
    developer = paths.developer_activities
    if developer is not None:
        if (
            developer == paths.activities
            or developer in paths.activities.parents
            or paths.activities in developer.parents
        ):
            raise ActivityValidationError(
                "developer Activity root must be separate from the built-in Activity root"
            )
        sources.append(
            ActivitySource(
                developer,
                trust=PackageTrust.DEVELOPER_UNSIGNED,
                source_id="greia-developer-remote",
            )
        )
    return tuple(sources)


def is_developer_boot_validation_deferred() -> bool:
    """Whether boot compose defers developer live validation past interactive.

    FIX-COMPOSE-WINDOW worker-side contract: the boot worker holds the GIL
    while running pure-Python compose/validation as the main thread must
    poll/drain/flip, so developer-tree live validation (per-package tree
    validation plus digest recomputation) is deferred past the interactive
    handoff on developer images. Deferred developer content is absent from
    the first interactive frame and arrives on the first post-interactive
    rescan through the unchanged trust-aware degrade path (never served
    unvalidated). Catalogue-staleness vs contention trade-off: developer
    tiles appear ~one rescan interval later; the boot worker performs
    structurally less GIL-bound work before interactive readiness. Owned by
    ``greia_launcher.composition``; this helper only exposes the same switch
    for boot-order documentation and tests.
    """

    raw = os.environ.get(
        "GREIA_DEFER_DEVELOPER_UNTIL_INTERACTIVE",
        "1",
    )
    if not raw.strip():
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off")


def boot_activity_sources(paths: LauncherPaths) -> tuple[ActivitySource, ...]:
    """Compose the production boot source set with explicit developer gating.

    Developer mode off: returns only the built-in source and performs no
    developer-root filesystem scan (the registry built from this set never
    observes the developer root, so ``discover()``/``discovery_token()`` touch
    only the built-in tree). Developer mode on: delegates to
    :func:`_activity_sources` so the developer tree keeps live
    ``ActivityRegistry`` validation semantics with ``DEVELOPER_UNSIGNED`` trust
    that is never promoted to built-in trust.

    FIX-COMPOSE-WINDOW: the returned developer source is still the complete
    authoritative set, but boot composition (``composition.compose_boot_content``)
    skips its live validation while :func:`is_developer_boot_validation_deferred`
    holds. The interactive handoff promotes the deferred source into the
    registry without validation and the first post-interactive rescan
    validates it; developer content is therefore never served unvalidated,
    only later.
    """

    builtin = ActivitySource(
        paths.activities,
        trust=PackageTrust.BUILT_IN,
        source_id=BUILT_IN_SOURCE_ID,
    )
    developer_root = getattr(paths, "developer_activities", None)
    developer = developer_activity_source(developer_root)
    if developer is None:
        return (builtin,)
    return _activity_sources(paths)


def _development_hal() -> GreiaHAL:
    """Deterministic non-installed HAL for windowed/source development only."""

    return GreiaHAL(
        display=StaticDisplayHAL(DisplayState(True, backend="development-static")),
        input=StaticInputHAL(
            InputState(True, True, True, backend="development-static")
        ),
        audio=StaticAudioHAL(AudioState(True, backend="development-static")),
        removable_media=StaticRemovableMediaHAL(
            RemovableMediaState(True, backend="development-static")
        ),
        network=StaticNetworkHAL(NetworkState(True, backend="development-static")),
        power=StaticPowerHAL(PowerState(True, backend="development-static")),
    )


def _mix(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
    right_weight: float,
) -> tuple[int, int, int]:
    return tuple(
        round(a * (1.0 - right_weight) + b * right_weight)
        for a, b in zip(left, right)
    )  # type: ignore[return-value]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windowed", action="store_true")
    parser.add_argument("--allow-exit", action="store_true")
    return parser.parse_args()


def bootstrap_launcher(app: LauncherApplication) -> LauncherApplication:
    """Run the explicit one-pass boot composition for an unbootstrapped app.

    Module-level owner of the T37 bootstrap step so production entry points
    never rely on constructor side effects: construct with
    ``bootstrap=False``, then pass the instance through here.
    """

    return app.bootstrap()


def main() -> int:
    emit_boot_marker("launcher_python_enter")
    configure_launcher_logging()
    args = parse_args()
    # Phase 4 order: construct the minimal shell here; display init, first
    # flip, single-worker preparation and intro-end apply all happen inside
    # run(). Do not pre-bootstrap before display.
    app = LauncherApplication(
        windowed=args.windowed, allow_exit=args.allow_exit, bootstrap=False
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())

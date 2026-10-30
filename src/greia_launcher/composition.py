from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from greia_platform.activities import (
    ActivityCollisionConflict,
    ActivityCollisionResolution,
    ActivityManifest,
    ActivityRegistration,
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
    resolve_activity_collisions,
)
from greia_platform.activity_index import ActivityIndexLoader
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.achievements import ProfileAchievementService
from greia_platform.creation_capacity import VolumeBudget
from greia_platform.device_capabilities import (
    DeviceCapabilityService,
    HALDeviceCapabilityProbe,
)
from greia_platform.hal import (
    GreiaHAL,
    LinuxAudioHAL,
    LinuxNetworkHAL,
    LinuxRemovableMediaHAL,
    SystemdPowerHAL,
)
from greia_platform.hal_legacy_x import (
    LegacyXDisplayHAL,
    LegacyXHardwareSessionController,
    LegacyXInputHAL,
)
from greia_platform.history import (
    HistoryPolicy,
    HistoryPolicyError,
    PlatformHistoryService,
    ProgressionPolicy,
)
from greia_platform.permissions import PermissionBroker
from greia_platform.storage import ActivityStorageService, StoragePolicy

from .display_session import DisplaySessionCoordinator
from .display_session_legacy_x import LegacyXDisplaySessionBackend
from .launch_timing import (
    DEFAULT_READY_TIMEOUT_SECONDS,
    POLICY_FILE_NAME as LAUNCH_TIMING_POLICY_FILE_NAME,
    resolve_ready_timeout_seconds,
)
from .runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeLaunchAdapter,
    RuntimeManager,
    WebRuntimeAdapter,
)
from .shell_window import NoopShellWindowController, ShellWindowController
from .shell_window_legacy_x import LegacyXShellWindowController
from .system_chrome import SystemChromeCoordinator
from .system_chrome_legacy_x import LegacyXSystemChromeBackend

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LauncherRuntimeServices:
    """Trusted shared dependencies for Activity launch decisions."""

    device_capabilities: DeviceCapabilityService
    permission_broker: PermissionBroker
    runtime_manager: RuntimeManager
    storage_service: ActivityStorageService
    history_service: PlatformHistoryService
    volume_budget: VolumeBudget = field(default_factory=VolumeBudget)
    achievement_service: ProfileAchievementService | None = None
    #: READY liveness bound for this device class (see launch_timing).
    activity_ready_timeout_seconds: float = DEFAULT_READY_TIMEOUT_SECONDS


def provisional_installed_hal() -> GreiaHAL:
    """Compose the current installed R6 HAL without blessing legacy X as final.

    R7 replaces the display/input implementations below this semantic boundary.
    Keeping composition here prevents PermissionBroker or runtime code from
    probing hardware independently.
    """

    x_controller = LegacyXHardwareSessionController()
    return GreiaHAL(
        display=LegacyXDisplayHAL(x_controller),
        input=LegacyXInputHAL(x_controller),
        audio=LinuxAudioHAL(),
        removable_media=LinuxRemovableMediaHAL(),
        network=LinuxNetworkHAL(),
        power=SystemdPowerHAL(),
    )


def provisional_installed_display_session() -> DisplaySessionCoordinator:
    """Compose the current X11 compatibility session behind the R7 contract.

    This deliberately preserves the existing production Xorg/xinit mechanism.
    Replacing this factory with a measured direct/compositor backend must not
    require changes to ActivitySupervisor or Activity runtime APIs.
    """

    return DisplaySessionCoordinator(LegacyXDisplaySessionBackend())


def provisional_installed_system_chrome() -> SystemChromeCoordinator:
    """Compose trusted Home/Back above the provisional Legacy-X Activity surface.

    The concrete backend owns one tiny launcher-process X11 window covering only
    Greia's protected navigation region. It is a migration adapter for R7.3,
    not an acceptance of shared X11 as the target architecture.
    """

    return SystemChromeCoordinator(LegacyXSystemChromeBackend())


def provisional_installed_shell_window_backend() -> ShellWindowController:
    """Return the installed shell's current Legacy-X native window controller.

    The launcher does not inspect SDL backend environment or call Xlib itself.
    R7 backend selection belongs to trusted platform composition. Replacing the
    installed display/session architecture therefore swaps this collaborator at
    the same composition boundary without changing launcher rendering code.
    """

    return LegacyXShellWindowController()


def development_shell_window_backend() -> ShellWindowController:
    """Return the backend-neutral shell hook for host development windows."""

    return NoopShellWindowController()


def default_runtime_adapters(
    runtime_policy_path: Path,
    *,
    python_executable: Path | None = None,
    browser_executable: Path | None = None,
) -> tuple[RuntimeLaunchAdapter, ...]:
    """Return the canonical runtime-adapter set for ordinary Greia composition.

    Synthetic/development compositions may inject another adapter set into
    ``build_launcher_runtime_services``. Permission, storage, history and
    device-authority composition stay here regardless of that variation.
    """

    return (
        PythonRuntimeAdapter(
            python_executable,
            policy=PythonRuntimePolicy.load(runtime_policy_path),
        ),
        WebRuntimeAdapter(browser_executable),
    )


def load_runtime_progression_policy(
    progression_policy_path: Path,
    activities: tuple[ActivityManifest, ...],
) -> ProgressionPolicy:
    """Load optional progression enrichment without making it boot authority.

    Source/build validation should continue to call ``ProgressionPolicy.load``
    directly and fail loudly on malformed policy or undeclared events. The
    installed launcher has a different availability requirement: if progression
    policy is stale/corrupt, child Activity launch and history must remain
    available. In that case progression is disabled for this launcher instance
    and the defect is left visible in the journal.
    """

    try:
        return ProgressionPolicy.load(progression_policy_path, activities)
    except HistoryPolicyError as exc:
        logger.error(
            "Progression policy is invalid at runtime; disabling progression "
            "for this launcher instance: %s",
            exc,
        )
        return ProgressionPolicy(schema_version=1, rules=())


def build_launcher_runtime_services(
    runtime: RuntimeCatalogue,
    activities: tuple[ActivityManifest, ...],
    *,
    runtime_policy_path: Path,
    permission_policy_path: Path,
    storage_policy_path: Path,
    history_policy_path: Path,
    progression_policy_path: Path,
    achievement_policy_path: Path | None = None,
    hal: GreiaHAL | None = None,
    volume_budget: VolumeBudget | None = None,
    python_executable: Path | None = None,
    browser_executable: Path | None = None,
    runtime_adapters: (
        Sequence[RuntimeLaunchAdapter] | Mapping[str, RuntimeLaunchAdapter] | None
    ) = None,
) -> LauncherRuntimeServices:
    """Build the shared device/runtime/permission/history/achievement authorities.

    ``hal``, ``volume_budget`` and ``runtime_adapters`` are deliberate
    variation seams (``volume_budget`` lets a developer simulator model its
    synthetic device volume instead of the host disk; the production default
    measures the real child-data filesystem). Callers
    must inject only those missing-machine/runtime facts; they must not rebuild
    PermissionBroker, storage, history or achievement composition in parallel.

    History storage bounds remain startup/safety authority and fail closed.
    Progression and achievements are child-facing enrichment: malformed or stale
    enrichment is disabled with diagnostics rather than taking down Greia Shell.
    """

    device_capabilities = DeviceCapabilityService(
        HALDeviceCapabilityProbe(hal or provisional_installed_hal())
    )
    permission_broker = PermissionBroker.phase0(
        runtime,
        permission_policy_path,
        device_capabilities=device_capabilities,
    )
    adapters = (
        runtime_adapters
        if runtime_adapters is not None
        else default_runtime_adapters(
            runtime_policy_path,
            python_executable=python_executable,
            browser_executable=browser_executable,
        )
    )
    runtime_manager = RuntimeManager(adapters, device_capabilities)
    volume_budget = volume_budget if volume_budget is not None else VolumeBudget()
    storage_service = ActivityStorageService(
        StoragePolicy.load(storage_policy_path),
        volume_budget=volume_budget,
    )
    history_service = PlatformHistoryService(
        HistoryPolicy.load(history_policy_path),
        load_runtime_progression_policy(progression_policy_path, activities),
        volume_budget=volume_budget,
    )

    resolved_achievement_policy = (
        achievement_policy_path
        if achievement_policy_path is not None
        else history_policy_path.parent / "achievement-policy.toml"
    )
    achievement_service: ProfileAchievementService | None = None
    try:
        achievement_service = ProfileAchievementService.load(
            resolved_achievement_policy,
            activities,
            history_service,
        )
    except (OSError, RuntimeError, ValueError):
        # Achievements are child-facing enrichment, not a launch/safety authority.
        # Disable badge presentation without taking down the launcher.
        achievement_service = None

    return LauncherRuntimeServices(
        device_capabilities=device_capabilities,
        permission_broker=permission_broker,
        runtime_manager=runtime_manager,
        volume_budget=volume_budget,
        storage_service=storage_service,
        history_service=history_service,
        achievement_service=achievement_service,
        activity_ready_timeout_seconds=resolve_ready_timeout_seconds(
            runtime_policy_path.parent / LAUNCH_TIMING_POLICY_FILE_NAME
        ),
    )


# -- T36 one-pass Activity source composition (B04 trust-aware degrade) ---
#
# Boot composes Activity sources exactly once. The seam is explicit:
#
#   1. index loading ends here: each source's trusted index is read without
#      re-running package-tree validation or digest recomputation
#      (``load_built_in_registrations`` / ``load_parent_registrations``), the
#      developer source keeps its explicit live-validation path, and the
#      complete set is resolved once through the shared pure resolver
#      (``resolve_activity_collisions`` in ``greia_platform.activities``);
#   2. runtime construction begins in the caller: one seeded
#      ``ComposedActivityRegistry`` (activation-time proof reused, never
#      recomputed, seeded with the same accepted/rejected/conflict evidence
#      so cold boot and later rescans cannot diverge), one
#      ``build_launcher_runtime_services`` set, and one presentation
#      ``ActivityCatalogue``.
#
# Result shape handed to runtime/catalogue construction
# (``ComposedLauncherContent``): ``registrations``/``activities`` are the
# accepted authoritative set; ``rejected`` holds every degraded claimant
# (never issuable via ``registration_for`` nor launchable); ``conflicts``
# holds one structured record per rejected claimant per colliding identity
# (identity/alias string, source ID, platform-assigned trust, package root,
# validation-time digest); ``degraded`` is true when any conflict exists
# (parent omission OR collision) and boot continues degraded;
# ``parent_degraded``/``parent_error`` remain the parent-specific omission
# signal consumed by the existing catalogue-error display. Collision
# conflicts are logged once at composition (bounded); rescan logging only
# reports newly appearing conflicts, never per-frame/per-rescan spam.
#
# Callers must not rebuild the registry or runtime services per source
# afterwards. The "built-ins first, Parent later, rebuild" two-pass flow is
# gone: ``compose_boot_content`` already contains the Parent set.

BUILT_IN_INDEX_ENV_VAR = "GREIA_BUILT_IN_ACTIVITY_INDEX"
BUILT_IN_INDEX_PATH = Path("/usr/share/greia/activity-index-v1.json")
PARENT_ACTIVITY_ROOT_ENV_VAR = "GREIA_PARENT_ACTIVITY_ROOT"
PARENT_ACTIVITY_ROOT_DEFAULT = Path("/var/lib/greia-os/activity-packages/active")

# -- FIX-COMPOSE-WINDOW: deferred developer validation (boot GIL-window shrink) --
#
# Catalogue-staleness vs contention trade-off (stated explicitly, per brief):
# the boot worker holds the GIL while running pure-Python compose/validation
# and the main thread must poll/drain/flip concurrently, so every package the
# worker validates before interactive readiness stretches the contention
# window. Developer-source live validation (per-package tree validation plus
# digest recomputation over the developer tree) is the deferrable share:
# developer content is absent from the first interactive frame and arrives on
# the first post-interactive rescan (~one rescan interval later) through the
# unchanged trust-aware degrade path. Built-in/Parent content is unaffected:
# it is served from the deterministic image indexes without revalidation.
# Cheap-but-weak mitigations (nice levels, yield points) are not used here;
# the window shrinks because the worker performs structurally less work
# before the interactive handoff, not because it is scheduled differently.
DEFER_DEVELOPER_UNTIL_INTERACTIVE_ENV_VAR = (
    "GREIA_DEFER_DEVELOPER_UNTIL_INTERACTIVE"
)


def developer_boot_validation_deferred(
    *,
    include_developer: bool | None = None,
) -> bool:
    """Whether boot compose must skip developer live validation.

    An explicit ``include_developer`` wins over the environment. Otherwise
    deferral defaults to ON: ``GREIA_DEFER_DEVELOPER_UNTIL_INTERACTIVE``
    disables it only on explicit ``0``/``false``/``no``/``off``. The default
    keeps the developer-image boot worker cheap; cold-boot trust tests opt
    out explicitly to keep asserting the undeferred resolution.
    """

    if include_developer is not None:
        return not include_developer
    raw = os.environ.get(DEFER_DEVELOPER_UNTIL_INTERACTIVE_ENV_VAR, "1")
    if not raw.strip():
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off")


def built_in_index_path() -> Path:
    """Return the built-in Activity index file path (env-overridable).

    The default is the image path shipped by the T33 build transaction
    (``build/build-image.sh`` writes ``/usr/share/greia/activity-index-v1.json``
    from the same source tree installed under ``/opt/greia-os/activities``).
    ``GREIA_BUILT_IN_ACTIVITY_INDEX`` overrides it the same way other Greia
    paths are overridable, which is also how tests pin a fixture index.
    """

    override = os.environ.get(BUILT_IN_INDEX_ENV_VAR)
    if override is not None and override.strip():
        return Path(override.strip())
    return BUILT_IN_INDEX_PATH


@dataclass(frozen=True, slots=True)
class ParentActiveSet:
    """Parent package source bound to its T34 active-set location."""

    source: ActivitySource
    index_path: Path | None


def resolve_parent_active_set() -> ParentActiveSet:
    """Resolve the Parent package source against the T34 active generation.

    An explicit ``GREIA_PARENT_ACTIVITY_ROOT`` keeps its historical meaning
    (a directly scanned package directory with no versioned index). Otherwise
    the source binds to the atomic active generation exposed by
    ``ActivityPackageService`` (``generations/<gen>/activities`` plus its
    ``index.json``), so boot observes exactly the published Parent set.
    """

    explicit = os.environ.get(PARENT_ACTIVITY_ROOT_ENV_VAR)
    if explicit is not None and explicit.strip():
        root = Path(explicit.strip()).resolve()
        return ParentActiveSet(
            source=_parent_source_for_root(root),
            index_path=None,
        )
    try:
        from greia_platform.activity_packages import (
            ActivityPackageError,
            ActivityPackageService,
        )

        service = ActivityPackageService.from_environment()
        root = service.active_source().root.resolve()
        index_path = service.active_index_path()
        return ParentActiveSet(
            source=_parent_source_for_root(root),
            index_path=index_path if index_path is not None else None,
        )
    except (ActivityPackageError, OSError, ValueError, RuntimeError):
        root = PARENT_ACTIVITY_ROOT_DEFAULT
        return ParentActiveSet(
            source=_parent_source_for_root(root),
            index_path=None,
        )


def _parent_source_for_root(root: Path) -> ActivitySource:
    from greia_platform.activity_packages import ActivityPackageService

    return ActivitySource(
        root,
        PackageTrust.PARENT_TRUSTED_UNSIGNED,
        ActivityPackageService.SOURCE_ID,
    )


def load_built_in_registrations(
    source: ActivitySource,
    runtime: RuntimeCatalogue,
) -> tuple[ActivityRegistration, ...]:
    """Load built-in image content from its trusted index without re-validation.

    When the image index is present the loader reconstructs the already
    validated registrations: no package tree is re-read and no digest is
    recomputed. A missing index (source checkout or legacy image) falls back
    to one validated scan. A present-but-corrupt index raises instead of
    serving an unvalidated set.
    """

    index = built_in_index_path()
    if index.is_file():
        return ActivityIndexLoader.from_runtime(source, runtime).load_file(index)
    # Fallback live scan collects every validated registration without
    # resolving collisions here; the composed resolver owns the single
    # cross-source decision so degraded evidence is never lost per-source.
    return _collect_live_registrations(source, runtime)


def load_parent_registrations(
    parent: ParentActiveSet,
    runtime: RuntimeCatalogue,
) -> tuple[ActivityRegistration, ...]:
    """Load the T34 atomic active Parent set without re-validation when indexed.

    A missing Parent root contributes no registrations and is not an error
    (Parent content is optional catalogue input). A missing versioned index
    falls back to one strict validated scan; any other load failure raises so
    the caller can omit the Parent set explicitly instead of serving a mix.
    """

    if not parent.source.root.exists():
        return ()
    if parent.index_path is not None and parent.index_path.is_file():
        loader = ActivityIndexLoader.from_runtime(parent.source, runtime)
        return loader.load_file(parent.index_path)
    strict = ActivityRegistry((parent.source,), runtime)
    return strict.discover_registrations()


def load_developer_registrations(
    source: ActivitySource | None,
    runtime: RuntimeCatalogue,
) -> tuple[ActivityRegistration, ...]:
    """Load developer content through the explicit live-validation path.

    Developer packages keep ``DEVELOPER_UNSIGNED`` trust and are validated
    live by ``ActivityRegistry``; no developer index is ever consumed.
    Collisions are not resolved here; every validated claimant is returned
    so the composed resolver makes the single trust-aware degrade decision.
    """

    if source is None:
        return ()
    return _collect_live_registrations(source, runtime)


def _collect_live_registrations(
    source: ActivitySource,
    runtime: RuntimeCatalogue,
) -> tuple[ActivityRegistration, ...]:
    """Validate every package of one source without resolving collisions."""

    live = ActivityRegistry((source,), runtime, fail_closed=False)
    root = source.root
    if not root.exists():
        return ()
    collected: list[ActivityRegistration] = []
    for path in sorted(root.glob("*/activity.toml")):
        try:
            collected.append(live.validate_registration(path.parent, source))
        except Exception as exc:
            logger.warning(
                "Skipping invalid/corrupted activity package at %s: %s",
                path.parent,
                exc,
            )
            continue
    return tuple(collected)


def enforce_composed_collision(
    registrations: Sequence[ActivityRegistration],
) -> None:
    """Legacy fail-closed cross-source identity/alias gate (superseded by B04).

    Preserved for direct callers that still require exception semantics.
    Boot composition (``compose_boot_content``) no longer uses this gate;
    it resolves through the shared trust-aware degrade resolver
    (``resolve_activity_collisions``) so one developer duplicate can never
    brick the child shell.
    """

    identities: dict[str, str] = {}
    for registration in registrations:
        manifest = registration.manifest
        for identity in (manifest.activity_id, *manifest.legacy_ids):
            if identity in identities:
                raise ActivityValidationError(
                    f"Activity identity/alias collision {identity!r}: "
                    f"{identities[identity]} and {manifest.activity_id}"
                )
            identities[identity] = manifest.activity_id


def _log_collision_conflicts(
    conflicts: Sequence[ActivityCollisionConflict],
) -> None:
    """Emit one bounded journal warning per rejected collision claimant."""

    for conflict in conflicts:
        logger.warning(
            "Composed Activity collision degraded: identity %r rejected "
            "activity %r source %r trust %r root %s digest %s",
            conflict.identity,
            conflict.activity_id,
            conflict.source_id,
            conflict.package_trust.value,
            str(conflict.package_root),
            conflict.package_digest[:16],
        )


class ComposedActivityRegistry(ActivityRegistry):
    """Registry pre-seeded with the one-pass composed registration set.

    The boot path never calls ``discover`` on this registry: activation-time
    ``registration_for`` reuses the index-loaded proof carried in each
    ``ActivityRegistration`` instead of recomputing digests or revalidating
    trees. ``discovery_token`` stays filesystem-based so later change detection
    keeps working; a later rescan revalidates live by design through the same
    shared degrade resolver, so cold boot and rescan cannot diverge on
    collisions. Rejected registrations are never issuable. Rescan logging
    reports only newly appearing conflicts (bounded, no per-rescan spam).
    """

    def __init__(
        self,
        sources: Sequence[ActivitySource],
        runtime: RuntimeCatalogue,
        registrations: Sequence[ActivityRegistration],
        *,
        rejected: Sequence[ActivityRegistration] = (),
        conflicts: Sequence[ActivityCollisionConflict] = (),
        degraded: bool = False,
        deferred_sources: Sequence[ActivitySource] = (),
    ) -> None:
        super().__init__(sources, runtime, fail_closed=False)
        self._issued.update(
            {id(registration.manifest): registration for registration in registrations}
        )
        self._rejected_registrations = tuple(rejected)
        self._collision_conflicts = tuple(conflicts)
        self._collision_degraded = bool(degraded or conflicts)
        # FIX-COMPOSE-WINDOW: developer sources whose live validation was
        # deferred past the interactive handoff. They are not scanned,
        # validated, or issuable until attached; see
        # :meth:`attach_deferred_sources`.
        self._deferred_sources = tuple(deferred_sources)
        self._parent_pointer_stamp: object = object()
        self.parent_source_needs_rescan = False

    @property
    def deferred_sources(self) -> tuple[ActivitySource, ...]:
        """Developer sources still awaiting post-interactive validation."""

        return self._deferred_sources

    def attach_deferred_sources(self) -> tuple[ActivitySource, ...]:
        """Promote deferred boot sources without validating them.

        Called once on the main thread at the interactive handoff (see
        ``LauncherApplication.apply_prepared_state``). This is a cheap tuple
        update: no tree is walked, no package is validated, no digest is
        recomputed, and no registration is issued, so the trust boundary is
        unchanged (deferred content stays unserved until the first
        post-interactive rescan validates it live through the shared
        trust-aware degrade resolver). The boot discovery token was
        snapshotted before this promotion, so the next rescan observes the
        token delta and runs that validation exactly once.
        """

        if not self._deferred_sources:
            return ()
        pending = self._deferred_sources
        self._deferred_sources = ()
        self._sources = (*self._sources, *pending)
        self._roots = tuple(source.root for source in self._sources)
        return pending

    def discovery_token(self) -> tuple[tuple[str, int, int, int], ...]:
        """Follow the atomic Parent generation before observing package changes.

        The active pointer names a generation; it is not itself a directory.
        Keeping the boot-time resolved path would miss subsequent installs.
        """
        pointer = Path(os.environ.get(
            "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT", "/var/lib/greia-os/activity-packages"
        )) / "active"
        try:
            info = pointer.stat()
            stamp: object = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        except OSError:
            stamp = None
        if stamp == self._parent_pointer_stamp:
            return super().discovery_token()
        parent = resolve_parent_active_set().source
        sources = list(self._sources)
        for index, source in enumerate(sources):
            if source.source_id != parent.source_id or source.trust != PackageTrust.PARENT_TRUSTED_UNSIGNED:
                continue
            built_in = sources[0].root.resolve()
            candidate = parent.root.resolve()
            if candidate == built_in or candidate in built_in.parents or built_in in candidate.parents:
                raise ActivityValidationError("parent Activity root must be separate from the built-in Activity root")
            if source.root != parent.root:
                sources[index] = parent
                self._sources = tuple(sources)
                self._roots = tuple(item.root for item in sources)
                self.parent_source_needs_rescan = True
            break
        self._parent_pointer_stamp = stamp
        return super().discovery_token()

    def discover_registrations(
        self, *, fail_closed: bool | None = None
    ) -> tuple[ActivityRegistration, ...]:
        previous = {
            (item.identity, item.activity_id, item.source_id)
            for item in self._collision_conflicts
        }
        result = super().discover_registrations(fail_closed=fail_closed)
        self.parent_source_needs_rescan = False
        fresh = [
            item
            for item in self._collision_conflicts
            if (item.identity, item.activity_id, item.source_id) not in previous
        ]
        if fresh:
            _log_collision_conflicts(fresh)
        return result


@dataclass(frozen=True, slots=True)
class ComposedLauncherContent:
    """Single composed Activity set plus its seeded registry.

    Handoff contract for runtime/catalogue construction and B04-PROOF
    diagnostics: ``registrations``/``activities`` are the accepted set;
    ``rejected`` are degraded claimants (never issuable/launchable);
    ``conflicts`` are structured per-claimant records (identity, source ID,
    trust, package root, validation-time digest); ``degraded`` marks any
    catalogue degrade (parent omission or collision) while boot continues.
    """

    sources: tuple[ActivitySource, ...]
    registrations: tuple[ActivityRegistration, ...]
    activities: tuple[ActivityManifest, ...]
    registry: ComposedActivityRegistry
    parent_degraded: bool = False
    parent_error: str | None = None
    rejected: tuple[ActivityRegistration, ...] = ()
    conflicts: tuple[ActivityCollisionConflict, ...] = ()
    degraded: bool = False
    # FIX-COMPOSE-WINDOW: developer sources deferred past interactive need
    # (validated on the first post-interactive rescan, not by the boot
    # worker). ``developer_deferred`` marks the staleness side of the
    # trade-off: the interactive set served at the handoff excludes these
    # sources until that rescan completes.
    deferred_sources: tuple[ActivitySource, ...] = ()
    developer_deferred: bool = False


def compose_boot_content(
    runtime: RuntimeCatalogue,
    boot_sources: Sequence[ActivitySource],
    *,
    include_developer: bool | None = None,
) -> ComposedLauncherContent:
    """Compose the boot Activity set exactly once.

    FIX-COMPOSE-WINDOW: on developer images the boot worker skips
    developer-source live validation by default (see
    :func:`developer_boot_validation_deferred`) and serves the indexed
    built-in set (+ the Parent active set) at the interactive handoff. The
    deferred developer sources stay listed in ``sources``/``deferred_sources``
    and are promoted into the registry at the handoff without validation, so
    the first post-interactive rescan validates them through the unchanged
    trust-aware degrade path. Pass ``include_developer=True`` to keep the
    historical cold-boot validation (trust tests do this explicitly).

    ``boot_sources`` is the T35-gated built-in/developer set (see
    ``boot_activity_sources``); the Parent active set is resolved here, so
    callers receive built-in plus Parent plus developer registrations with one
    trust-aware degrade resolution and one seeded registry. A damaged Parent
    set is omitted with ``parent_degraded`` set instead of taking the Shell
    down. A built-in/developer identity collision degrades (accept built-in,
    reject developer claimants, record structured conflicts, mark degraded)
    and boot continues; any other ambiguous identity group rejects every
    member and boot continues with the remainder. The following still raise
    hard controlled failure (never degrade): built-in index
    corruption/incompatibility, forged source/trust metadata, source-root
    escape, and failure to construct mandatory runtime/sandbox/system-chrome
    authority. The Parent root must stay separate from the built-in root.
    """

    sources = tuple(boot_sources)
    if not sources or sources[0].trust is not PackageTrust.BUILT_IN:
        raise ActivityValidationError(
            "composed boot sources must start with the built-in source"
        )
    built_in_source = sources[0]
    developer_sources = tuple(sources[1:])
    parent_set = resolve_parent_active_set()
    built_in_root = built_in_source.root.resolve()
    parent_root = parent_set.source.root.resolve()
    if (
        parent_root == built_in_root
        or parent_root in built_in_root.parents
        or built_in_root in parent_root.parents
    ):
        raise ActivityValidationError(
            "parent Activity root must be separate from the built-in Activity root"
        )
    built_in = load_built_in_registrations(built_in_source, runtime)
    # FIX-COMPOSE-WINDOW: the boot worker skips the developer tree walk
    # (glob + per-package validation + digest recomputation) while deferred.
    # The deferred sources stay in the authoritative ``ordered_sources`` set
    # but outside the registry until the interactive handoff promotes them
    # without validation; the first post-interactive rescan then performs the
    # deferred live validation through the same trust-aware degrade resolver.
    # Deferral is never a trust promotion: deferred content is simply absent
    # (never served unvalidated) until that rescan validates it.
    developer_deferred = bool(developer_sources) and developer_boot_validation_deferred(
        include_developer=include_developer
    )
    developer: list[ActivityRegistration] = []
    if not developer_deferred:
        for source in developer_sources:
            developer.extend(load_developer_registrations(source, runtime))
    deferred_sources = tuple(developer_sources) if developer_deferred else ()
    parent_degraded = False
    parent_error: str | None = None
    try:
        parent = load_parent_registrations(parent_set, runtime)
    except (ActivityValidationError, ValueError, OSError, RuntimeError) as exc:
        parent = ()
        parent_degraded = True
        parent_error = str(exc)
    combined = (*built_in, *parent, *developer)
    resolution: ActivityCollisionResolution = resolve_activity_collisions(combined)
    if resolution.degraded:
        _log_collision_conflicts(resolution.conflicts)
    accepted = resolution.accepted
    ordered_sources = (
        built_in_source,
        parent_set.source,
        *developer_sources,
    )
    registry = ComposedActivityRegistry(
        (
            (built_in_source, parent_set.source)
            if developer_deferred
            else ordered_sources
        ),
        runtime,
        accepted,
        rejected=resolution.rejected,
        conflicts=resolution.conflicts,
        degraded=resolution.degraded,
        deferred_sources=deferred_sources,
    )
    degraded = bool(parent_degraded or resolution.degraded)
    return ComposedLauncherContent(
        sources=ordered_sources,
        registrations=tuple(accepted),
        activities=tuple(item.manifest for item in accepted),
        registry=registry,
        parent_degraded=parent_degraded,
        parent_error=parent_error,
        rejected=tuple(resolution.rejected),
        conflicts=tuple(resolution.conflicts),
        degraded=degraded,
        deferred_sources=deferred_sources,
        developer_deferred=developer_deferred,
    )

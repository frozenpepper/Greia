"""Explicit launcher bootstrap coordinator and boot lifecycle guard.

Phase 4 owns the first-frame budget: the interactive launcher must be able to
show its first intro frame before Activity catalogue/history/runtime
construction completes. This module provides the two seams that make that
possible without changing the intro itself:

- :class:`BootLifecycleGuard`: the guarded boot state model
  (``CREATED → DISPLAY_READY → FIRST_FRAME_VISIBLE → PREPARING_RUNTIME →
  INTERACTIVE_READY → RUNNING``). Every later boot change must pass through
  these transitions; illegal transitions fail loudly.
- :class:`LauncherBootstrap`: the narrowly-scoped coordinator that performs
  the one-pass boot composition and returns it as an immutable
  :class:`PreparedLauncherState`. ``prepare_runtime()`` is the single contract
  the future post-frame worker will call; the main thread publishes the result
  exactly once through ``LauncherApplication.apply_prepared_state()``.

Worker boundary: ``prepare_runtime()`` performs only non-Pygame work
(Activity source resolution/index loading, catalogue construction, profile
and history file IO, runtime service construction). It never imports Pygame,
never touches a Pygame surface, and never mutates live launcher state — all
publication happens in the main-thread apply step, which additionally builds
the display-bound visual cache. ``bootstrap.py`` therefore has no Pygame or
threading dependency by design.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

from greia_platform.activities import (
    ActivityManifest,
    ActivityRegistration,
    RuntimeCatalogue,
)
from greia_platform.boot_markers import emit_boot_marker
from greia_platform.history import HistoryError
from greia_platform.profiles import ActiveProfileSession, ChildProfile, ProfileStore
from greia_platform.customization import ThemeStore
from greia_platform.trust import ActivitySource

from .composition import (
    ComposedActivityRegistry,
    LauncherRuntimeServices,
    compose_boot_content,
    development_shell_window_backend,
    provisional_installed_shell_window_backend,
)
from .theme import LauncherThemeController
from .installed_root import is_installed_root
from .visual_assets import LauncherAssetSet, load_launcher_assets

if False:  # pragma: no cover - typing only, avoids a main/bootstrap cycle.
    from .main import LauncherPaths


class BootLifecycleState(StrEnum):
    """Guarded boot states for the launcher first-frame sequence."""

    CREATED = "created"
    DISPLAY_READY = "display_ready"
    FIRST_FRAME_VISIBLE = "first_frame_visible"
    PREPARING_RUNTIME = "preparing_runtime"
    INTERACTIVE_READY = "interactive_ready"
    RUNNING = "running"


class BootLifecycleError(ValueError):
    """Raised when boot state is advanced illegally or consumed twice."""


_ALLOWED_BOOT_TRANSITIONS: dict[BootLifecycleState, tuple[BootLifecycleState, ...]] = {
    # CREATED → PREPARING_RUNTIME is the transitional synchronous path used by
    # P4-BOOTSTRAP (preparation still runs before display, exactly as before).
    # P4-FIRSTFRAME routes preparation after the first frame instead
    # (CREATED → DISPLAY_READY → FIRST_FRAME_VISIBLE → PREPARING_RUNTIME) and
    # may deprecate the direct edge once the reorder lands.
    BootLifecycleState.CREATED: (
        BootLifecycleState.DISPLAY_READY,
        BootLifecycleState.PREPARING_RUNTIME,
    ),
    BootLifecycleState.DISPLAY_READY: (BootLifecycleState.FIRST_FRAME_VISIBLE,),
    BootLifecycleState.FIRST_FRAME_VISIBLE: (BootLifecycleState.PREPARING_RUNTIME,),
    BootLifecycleState.PREPARING_RUNTIME: (BootLifecycleState.INTERACTIVE_READY,),
    BootLifecycleState.INTERACTIVE_READY: (BootLifecycleState.RUNNING,),
    BootLifecycleState.RUNNING: (),
}


class BootLifecycleGuard:
    """Own the launcher boot state and fail loudly on illegal transitions."""

    def __init__(
        self, initial: BootLifecycleState = BootLifecycleState.CREATED
    ) -> None:
        self._state = BootLifecycleState(initial)

    @property
    def state(self) -> BootLifecycleState:
        return self._state

    def transition(self, target: BootLifecycleState) -> BootLifecycleState:
        """Advance to ``target`` or raise :class:`BootLifecycleError`."""

        wanted = BootLifecycleState(target)
        allowed = _ALLOWED_BOOT_TRANSITIONS[self._state]
        if wanted not in allowed:
            raise BootLifecycleError(
                f"illegal boot transition {self._state.value} -> {wanted.value}; "
                f"allowed next: {[item.value for item in allowed] or ['<terminal>']}"
            )
        self._state = wanted
        return self._state

    def mark_display_ready(self) -> BootLifecycleState:
        return self.transition(BootLifecycleState.DISPLAY_READY)

    def mark_first_frame_visible(self) -> BootLifecycleState:
        return self.transition(BootLifecycleState.FIRST_FRAME_VISIBLE)

    def begin_preparing_runtime(self) -> BootLifecycleState:
        return self.transition(BootLifecycleState.PREPARING_RUNTIME)

    def mark_interactive_ready(self) -> BootLifecycleState:
        return self.transition(BootLifecycleState.INTERACTIVE_READY)

    def mark_running(self) -> BootLifecycleState:
        return self.transition(BootLifecycleState.RUNNING)

    def reset_to_created(self) -> BootLifecycleState:
        """Return a failed preparation to ``CREATED`` so a retry may run.

        Valid only from ``PREPARING_RUNTIME`` after a failed bootstrap that
        published nothing (the apply step restores placeholders before
        raising). This is the single sanctioned backward edge; every other
        backward or skip-ahead transition raises.
        """

        if self._state is not BootLifecycleState.PREPARING_RUNTIME:
            raise BootLifecycleError(
                f"boot reset to created is only valid from preparing_runtime, "
                f"not {self._state.value}"
            )
        self._state = BootLifecycleState.CREATED
        return self._state


@dataclass(frozen=True, slots=True)
class PreparedLauncherState:
    """Immutable one-pass boot composition result.

    The coordinator resolves configured sources, loads registrations from each
    source, resolves identity/alias collisions across the complete set once,
    and builds one runtime service set, one supervisor, and (for presentation
    shells) one presentation catalogue. Consumers publish this atomically;
    the instance itself is never mutated after creation.
    """

    runtime: RuntimeCatalogue
    sources: tuple[ActivitySource, ...]
    registrations: tuple[ActivityRegistration, ...]
    activities: tuple[ActivityManifest, ...]
    registry: ComposedActivityRegistry
    asset_set: LauncherAssetSet
    profile_store: ProfileStore
    profiles: tuple[ChildProfile, ...]
    session: ActiveProfileSession
    selector_theme: LauncherThemeController
    runtime_services: LauncherRuntimeServices
    supervisor: Any
    catalogue: Any | None
    history_recovery_failures: frozenset[str]
    parent_degraded: bool
    parent_error: str | None
    rejected: tuple[ActivityRegistration, ...]
    conflicts: tuple[Any, ...]
    degraded: bool
    activity_discovery_token: Any
    shell_window_backend: Any
    installed: bool


# Builders injected by the owning shell so polymorphic construction stays
# with the shell subclasses while the coordinator owns the one-pass order.
ServicesBuilder = Callable[
    [RuntimeCatalogue, tuple[ActivityManifest, ...]], LauncherRuntimeServices
]
SupervisorBuilder = Callable[[LauncherRuntimeServices], Any]
CatalogueBuilder = Callable[[tuple[ActivityManifest, ...]], Any]


class LauncherBootstrap:
    """Perform the one-pass boot composition without touching live UI state.

    The coordinator holds only the resolved paths; every build step returns
    fresh objects that are sealed into the resulting
    :class:`PreparedLauncherState`. Builders are injected by the owning shell
    so subclass construction policy (supervisor type, presentation catalogue)
    is preserved without the base coordinator dispatching to overrides.
    """

    def __init__(self, paths: LauncherPaths) -> None:
        self._paths = paths

    @property
    def paths(self) -> LauncherPaths:
        return self._paths

    def prepare_runtime(
        self,
        *,
        build_services: ServicesBuilder,
        build_supervisor: SupervisorBuilder,
        build_catalogue: CatalogueBuilder | None = None,
    ) -> PreparedLauncherState:
        """Compose the complete boot set exactly once and seal it immutably.

        Emits the established boot markers in their historical order. A
        present-but-corrupt built-in index raises its controlled failure
        (never a silent full rescan); a damaged Parent set degrades inside
        composition instead of taking the Shell down. No Pygame import, no
        surface mutation, no live launcher mutation happens here.
        """

        from .main import boot_activity_sources

        paths = self._paths
        # 2A: no in-process Activity-tree scrub on the boot path. Built-in
        # hygiene is owned by the image build and parent/developer hygiene
        # by their activation transactions.
        runtime = RuntimeCatalogue.load(paths.runtime_catalogue)
        emit_boot_marker("activity_sources_begin")
        try:
            # One-pass composition: the gated boot set plus the Parent
            # active set are resolved and loaded exactly once here.
            composed = compose_boot_content(
                runtime,
                boot_activity_sources(paths),
            )
        finally:
            emit_boot_marker("activity_sources_end")
        asset_set = load_launcher_assets(
            paths.asset_catalogue,
            paths.shared_visual_catalogue,
        )
        profile_store = ProfileStore.load(
            paths.profile_defaults, paths.profiles_dir
        )
        profiles = profile_store.ensure_initialized()
        session = ActiveProfileSession(paths.active_profile_status)
        session.clear()
        selector_theme = LauncherThemeController(
            ThemeStore.load(
                paths.theme_defaults,
                paths.profiles_dir / ".selector-theme",
            )
        )
        emit_boot_marker("activity_discover_begin")
        try:
            activities = composed.activities
        finally:
            emit_boot_marker("activity_discover_end")
        activity_discovery_token = composed.registry.discovery_token()
        # If a Parent generation changed while boot was loading its index,
        # force one live rescan after handoff instead of sealing a new token
        # beside registrations from the old generation.
        if composed.registry.parent_source_needs_rescan:
            activity_discovery_token = None
        installed = is_installed_root(paths.root)
        emit_boot_marker("activity_runtime_build_begin")
        try:
            runtime_services = build_services(runtime, activities)
            supervisor = build_supervisor(runtime_services)
        finally:
            emit_boot_marker("activity_runtime_build_end")
        history_recovery_failures: set[str] = set()
        emit_boot_marker("history_prepare_begin")
        try:
            for child in profiles:
                try:
                    runtime_services.history_service.recover_unfinished(
                        profile_store.context(child.profile_id)
                    )
                except HistoryError:
                    history_recovery_failures.add(child.profile_id)
        finally:
            emit_boot_marker("history_prepare_end")
        catalogue = build_catalogue(activities) if build_catalogue is not None else None
        shell_window_backend = (
            provisional_installed_shell_window_backend()
            if installed
            else development_shell_window_backend()
        )
        return PreparedLauncherState(
            runtime=runtime,
            sources=composed.sources,
            registrations=composed.registrations,
            activities=activities,
            registry=composed.registry,
            asset_set=asset_set,
            profile_store=profile_store,
            profiles=profiles,
            session=session,
            selector_theme=selector_theme,
            runtime_services=runtime_services,
            supervisor=supervisor,
            catalogue=catalogue,
            history_recovery_failures=frozenset(history_recovery_failures),
            parent_degraded=composed.parent_degraded,
            parent_error=composed.parent_error,
            rejected=composed.rejected,
            conflicts=composed.conflicts,
            degraded=composed.degraded,
            activity_discovery_token=activity_discovery_token,
            shell_window_backend=shell_window_backend,
            installed=installed,
        )

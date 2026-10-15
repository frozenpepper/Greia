from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path
from typing import Any

from greia_platform.activities import (
    ActivityManifest,
    ActivityRegistry,
    ActivityValidationError,
)
from greia_platform.assets import AssetCatalogueError
from greia_platform.boot_markers import emit_boot_marker
from greia_platform.child_text import ChildTextCase, child_text_case_from_environment
from greia_platform.pygame_effects import (
    PygameDepthStyle,
    draw_raised_panel,
    draw_soft_shadow,
    make_rounded_shadow,
    make_shadowed_icon,
    transformed_rect,
)
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.ui_core import BoundedCache
from greia_platform.ui_motion import HoverMotion, InteractionVisualState, LaunchMotion
from greia_platform.ui_scroll import ScrollModel

from .launch_feedback import launch_feedback
from .activity_icon import ActivityIconError, package_icon_path
from .spoken_labels import SpokenLabelController
from .catalogue_view import (
    ALL_ACTIVITIES_ID,
    ActivityCatalogue,
    ActivityFolder,
    _category_title,
)
from .title_presentation import (
    contain_fit_icon_surface,
    render_activity_card_label,
)
from .main import (
    HitTarget,
    LauncherApplication,
    _activity_sources,  # noqa: F401 -- legacy reconfiguration seam (see below).
    _development_hal,
    boot_activity_sources,
)
from .bootstrap import BootLifecycleError
from .supervisor import ActivitySupervisor


PARENT_ACTIVITY_SOURCE_ID = "greia-parent-package-service"

_IDLE_ACTIVE_SLEEP_SECONDS = 0.008
_IDLE_RELAXED_SLEEP_SECONDS = 0.04


def idle_sleep_seconds(idle_seconds: float) -> float:
    """Return the idle-loop sleep for how long no input has been observed.

    The launcher is input-driven: frames render only when something changes.
    Immediately after interaction the loop polls quickly so added input latency
    stays imperceptible; after a short quiet period it relaxes to a slower wake
    cadence that keeps idle CPU low on Atom-class reference devices.
    """

    if idle_seconds < 1.0:
        return _IDLE_ACTIVE_SLEEP_SECONDS
    return _IDLE_RELAXED_SLEEP_SECONDS


class GreiaLauncherPresentation(LauncherApplication):
    """Child-facing presentation specialization for the launcher core.

    Lifecycle, permissions, profile ownership, Activity supervision and boot
    handoff remain in ``LauncherApplication``. This class owns richer
    presentation/navigation plus the additional typed discovery source for
    parent-installed packages. It never bypasses the registry or supervisor.
    """

    _DEPTH = PygameDepthStyle(shadow_offset=5, shadow_alpha=45, radius=24)
    _HOVER = HoverMotion(scale=1.025, lift_pixels=3.0)
    _LAUNCH = LaunchMotion(duration_seconds=0.42, wiggle_pixels=7, bounce_pixels=10)
    # Inflation (width, height) of a card hit rect restored from the backdrop
    # before a hover/launch-tick repair redraws that card.
    _TILE_REPAIR_PAD = (34, 40)

    def __init__(
        self,
        *,
        windowed: bool = False,
        allow_exit: bool = False,
        bootstrap: bool = True,
        **kwargs: object,
    ):
        # Lightweight construction: the base constructor is always invoked
        # with bootstrap=False so it never dispatches to this subclass's
        # runtime override while base state is half-initialized. The explicit
        # bootstrap below runs after both base and presentation placeholders
        # are fully assigned.
        super().__init__(
            windowed=windowed, allow_exit=allow_exit, bootstrap=False, **kwargs
        )
        # Replace the old unbounded presentation dictionaries with explicit LRU
        # bounds while preserving the mapping surface used by the base class.
        self._icon_cache = BoundedCache(96)
        self._font_cache = BoundedCache(24)
        self._shadow_cache: BoundedCache[tuple[int, int, int], Any] = BoundedCache(16)
        self._decorated_icon_cache: BoundedCache[tuple[str, str, int], Any] = BoundedCache(64)
        self._label_surface_cache: BoundedCache[
            tuple[str, int, int, tuple[int, int, int], int], Any
        ] = BoundedCache(128)
        self._category_label_cache: BoundedCache[
            tuple[str, int, tuple[int, int, int]], Any
        ] = BoundedCache(32)
        self._category_icon_cache: BoundedCache[
            tuple[str, int, int, int], Any
        ] = BoundedCache(32)
        self._catalogue: ActivityCatalogue | None = None
        self._category_id = ALL_ACTIVITIES_ID
        self._activity_scroll_start = 0
        self._launching_activity_id: str | None = None
        self._launch_animation_started = 0.0
        self._last_input_monotonic = 0.0
        # Last settled hover target for coalesced MOUSEMOTION handling.
        # Raw hit-target identity is paired with a stable semantic identity so
        # a category/catalogue change cannot disguise a different Activity as
        # the same ("presented_activity", index) tuple.
        self._coalesced_hover_target: tuple[str, Any] | None = None
        self._coalesced_hover_identity: tuple[Any, ...] | None = None
        self._cached_activities_surface: Any = None
        self._cached_activities_key: Any = None
        self._cached_activities_targets: list[HitTarget] = []
        # Dynamic per-frame aspects of the activities scene (pointer hover and
        # launch-animation tick) are tracked separately from the static cache
        # key so hover transitions repair only the affected tiles instead of
        # rebuilding the whole 1024x600 surface on an Atom-class CPU.
        self._activities_hover_signature: tuple[str, Any] | None = None
        self._activities_launch_tick: int | None = None
        self._tile_surface_cache: BoundedCache[Any, Any] = BoundedCache(64)
        self._backdrop_cache: BoundedCache[Any, Any] = BoundedCache(16)
        self._disclosure_cache: BoundedCache[Any, Any] = BoundedCache(32)
        try:
            env_root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")).resolve()
            if (env_root / "assets/audio/system/launcher-labels").exists():
                spoken_root = env_root
            else:
                spoken_root = Path(__file__).resolve().parents[2]
        except Exception:
            spoken_root = Path(__file__).resolve().parents[2]
        self._spoken_labels = SpokenLabelController(spoken_root)
        if bootstrap:
            self.bootstrap()

    def bootstrap(self) -> "GreiaLauncherPresentation":
        """Explicitly bootstrap base composition plus the presentation catalogue.

        One-pass boot: the base bootstrap composes the complete built-in
        plus Parent plus developer set exactly once (see
        composition.compose_boot_content) through the coordinator, and the
        apply step publishes the single presentation catalogue built inside
        that same preparation; it never rebuilds the registry or runtime
        services per source here.
        """

        if getattr(self, "_bootstrapped", False) and self._catalogue is not None:
            return self
        super().bootstrap()
        return self

    def apply_prepared_state(self, state: Any) -> "GreiaLauncherPresentation":
        """Publish the prepared base state plus the one presentation catalogue."""

        super().apply_prepared_state(state)
        try:
            self._catalogue = state.catalogue
        except Exception:
            self._catalogue = None
            self._bootstrapped = False
            raise
        return self

    def _bootstrap_catalogue_builder(self) -> Any:
        """Build the single presentation catalogue inside preparation."""

        return ActivityCatalogue.from_activities

    def _spoken_locale(self) -> str:
        try:
            return str(self._active_locale)  # type: ignore[attr-defined]
        except Exception:
            return "it"

    def _speakable_for_target(
        self, target: tuple[str, Any] | None, locale: str | None = None
    ) -> tuple[str, Any] | None:
        if target is None:
            return None
        action, value = target
        loc = locale or self._spoken_locale()
        try:
            if action == "presented_activity" or action == "presented_activity_select":
                idx = int(value)
                acts = self._presented_activities  # type: ignore[attr-defined]
                if not (0 <= idx < len(acts)):
                    return None
                manifest = acts[idx]
                if isinstance(manifest, ActivityFolder):
                    return self._spoken_labels.collection_focus(manifest.folder_id, loc)
                return self._spoken_labels.activity_focus(manifest, loc)
            if action == "home_collection":
                cid = str(value)
                return self._spoken_labels.collection_focus(cid, loc)
            if action == "activity_subcollection":
                cid = str(value)
                return self._spoken_labels.collection_focus(cid, loc)
            if action == "activity_category":
                cid = str(value)
                return self._spoken_labels.collection_focus(cid, loc)
        except (ValueError, TypeError, AttributeError, KeyError):
            return None
        return None

    def _announce_selected_activity(self, pygame: Any) -> bool:
        try:
            acts = self._presented_activities  # type: ignore[attr-defined]
            if not acts or not (0 <= self._selected < len(acts)):  # type: ignore[attr-defined]
                return False
            manifest = acts[self._selected]  # type: ignore[attr-defined]
            if isinstance(manifest, ActivityFolder):
                return self._spoken_labels.announce_collection(
                    manifest.folder_id, self._spoken_locale(), pygame
                )
            return self._spoken_labels.announce_activity(
                manifest, self._spoken_locale(), pygame
            )
        except Exception:
            return False

    def _announce_selected_home_collection(self, pygame: Any) -> bool:
        try:
            cols = getattr(self, "_home_collections", lambda: ())()
            if not cols:
                return False
            idx = getattr(self, "_home_collection_selected", 0)
            if not (0 <= idx < len(cols)):
                return False
            cid = cols[idx].collection_id
            return self._spoken_labels.announce_collection(cid, self._spoken_locale(), pygame)
        except Exception:
            return False

    def _announce_selected_subcollection(self, pygame: Any) -> bool:
        try:
            groups = getattr(self, "_adaptive_groups", lambda: ())()
            if not groups:
                return False
            idx = getattr(self, "_subcollection_selected", 0)
            if not (0 <= idx < len(groups)):
                return False
            cid = groups[idx].collection_id
            return self._spoken_labels.announce_collection(cid, self._spoken_locale(), pygame)
        except Exception:
            return False

    def _poll_spoken_labels(self, pygame: Any, now: float) -> None:
        try:
            self._spoken_labels.poll_pending_pointer_focus(now, pygame)
        except Exception:
            pass

    def _clear_spoken_pointer(self) -> None:
        self._coalesced_hover_target = None
        self._coalesced_hover_identity = None
        try:
            self._spoken_labels.clear_pointer_focus()
        except Exception:
            pass

    def _stop_spoken_labels(self) -> None:
        try:
            self._spoken_labels.stop()
        except Exception:
            pass

    def _configure_parent_package_source(self) -> None:
        """Compose parent-installed packages into the same launch authority path.

        Boot no longer routes through here: the base constructor composes all
        sources exactly once via ``composition.compose_boot_content``. This
        method remains for explicit reconfiguration only. It still routes the
        developer content through the gated boot set, so developer mode off
        never scans the developer root here either.
        """

        package_root = Path(
            os.environ.get(
                "GREIA_PARENT_ACTIVITY_ROOT",
                "/var/lib/greia-os/activity-packages/active",
            )
        ).resolve()
        if (
            package_root == self.paths.activities
            or package_root in self.paths.activities.parents
            or self.paths.activities in package_root.parents
        ):
            raise ActivityValidationError(
                "parent Activity root must be separate from the built-in Activity root"
            )
        sources = (
            *boot_activity_sources(self.paths),
            ActivitySource(
                package_root,
                trust=PackageTrust.PARENT_TRUSTED_UNSIGNED,
                source_id=PARENT_ACTIVITY_SOURCE_ID,
            ),
        )
        registry = ActivityRegistry(sources, self.runtime)
        try:
            discovered = registry.discover()
        except ActivityValidationError:
            # Parent package storage is optional catalogue input. A damaged
            # package may be omitted without taking the child Shell down, but it
            # must never leave this presentation subclass using the plain
            # ActivitySupervisor created by LauncherApplication.__init__.
            #
            # Rebuild against the already validated built-in/developer registry
            # so dynamic dispatch restores the complete installed lifecycle
            # composition (trusted Home/Back, usage limits and profile-aware
            # launch services). If that mandatory rebuild itself fails, let the
            # initialization fail closed rather than launching an unprotected
            # Activity.
            self._catalogue_error = True
            self._rebuild_runtime_services()
            return

        self.registry = registry
        self._activities = discovered
        self._activity_discovery_token = registry.discovery_token()
        self._rebuild_runtime_services()

    def _rebuild_runtime_services(self) -> None:
        """Rebind runtime/permission/history authority to the validated registry set.

        Parent installation can change the registry while the launcher is
        already running. Merely redrawing the new manifest would be unsafe: the
        runtime manager and permission/history services must be rebuilt from the
        exact same validated Activity set before that new tile becomes launchable.
        """

        super()._rebuild_runtime_services()

    def _initial_display_request(self, pygame: Any) -> tuple[tuple[int, int], int]:
        """Return the platform-selected initial shell surface request."""

        return (
            ((960, 540), pygame.RESIZABLE)
            if self.windowed
            else ((0, 0), pygame.FULLSCREEN)
        )

    def _resize_display_request(
        self, event: Any, pygame: Any
    ) -> tuple[tuple[int, int], int] | None:
        """Translate one host resize event into the authoritative shell request."""

        if not self.windowed:
            return None
        return (tuple(event.size), pygame.RESIZABLE)

    def _display_caption(self) -> str:
        return "Greia OS"

    def run(self) -> int:
        import pygame

        from .main import create_preparation_worker
        from .input_semantics import discard_preinteractive_input

        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        emit_boot_marker("pygame_display_init_begin")
        try:
            # Display-only pre-frame init: same contract as
            # LauncherApplication.run — the first frame needs the display
            # surface only. Fonts init lazily via greia_platform.typography,
            # the mixer on first spoken-label audio, controllers at
            # interactive readiness. No mixer/joystick init before first flip.
            pygame.display.init()
        finally:
            emit_boot_marker("pygame_display_init_end")
        default_size, display_flags = self._initial_display_request(pygame)
        emit_boot_marker("display_set_mode_begin")
        try:
            screen = pygame.display.set_mode(default_size, display_flags)
        finally:
            emit_boot_marker("display_set_mode_end")
        pygame.display.set_caption(self._display_caption())
        pygame.mouse.set_visible(False)
        if self._bootstrapped:
            self._enter_running_state()
            self._shell_window_backend.after_window_created(pygame)
        else:
            # Phase 4 order: minimal shell → display → first intro flip →
            # single-worker preparation → intro-end apply. The first-frame
            # callback below owns the display-thread → worker handoff; the
            # 7-second intro clock is anchored to the first flip and never
            # shortened by preparation.
            self._boot_lifecycle.mark_display_ready()
            executor = create_preparation_worker()
            pending: dict[str, Any] = {}

            def _on_first_frame() -> None:
                pending["future"] = self._begin_post_frame_preparation(executor)
                if not self._first_frame_released:
                    self._release_boot_cover()

            try:
                if not self.windowed:
                    try:
                        from .boot_chime import play_boot_chime
                        from .boot_intro import run_intro

                        # The first draw/flip, its intro_first_frame_flipped
                        # marker and the worker submission all happen inside
                        # run_intro; the existing 5 s animation + 2 s hold
                        # run unchanged while the worker prepares off-thread.
                        run_intro(screen, pygame, on_first_frame=_on_first_frame)
                        play_boot_chime()
                    except Exception:  # noqa: BLE001 - presentation must never fail boot
                        # If the first frame never fired, preparation was not submitted
                        # and boot cannot proceed. But if the first frame flipped, any
                        # subsequent animation or chime failure is non-fatal polish.
                        if "future" not in pending:
                            raise
                else:
                    from .boot_intro import (
                        _emit_first_frame_flipped_once,
                        draw_boot_handoff_frame,
                    )

                    # Windowed/dev path has no 7 s animation: publish the
                    # same handoff first frame, then submit the worker.
                    draw_boot_handoff_frame(screen, pygame, progress=92)
                    pygame.display.flip()
                    _emit_first_frame_flipped_once()
                    _on_first_frame()
                if "future" not in pending:
                    raise BootLifecycleError(
                        "first-frame callback never fired; "
                        "preparation was not submitted"
                    )
                try:
                    self._await_and_apply_preparation(pending["future"])
                finally:
                    executor.shutdown(wait=False)
            except Exception:
                executor.shutdown(wait=False)
                raise
            self._shell_window_backend.after_window_created(pygame)
            self._enter_running_state()

        # The handoff/intro/preparation phase is deliberately non-interactive.
        # Drop every queued user action immediately before the first interactive
        # poll so a boot-time click/key cannot activate whatever Home control
        # happens to appear underneath it later. System/lifecycle events remain.
        discard_preinteractive_input(pygame)

        clock = pygame.time.Clock()
        running = True
        last_display_size = screen.get_size()

        _needs_redraw = True
        try:
            while running:
                frame_start = time.monotonic()
                self._poll_input_hooks(pygame)
                events = pygame.event.get()
                if events:
                    self._last_input_monotonic = frame_start
                    if any(event.type != pygame.MOUSEMOTION for event in events):
                        _needs_redraw = True
                # Live overlay content changes with no event behind it. Without
                # this the microphone meter only advanced when something moved the
                # pointer. This is the loop that actually runs, so it is the only
                # place a repaint request has to be honoured; the request itself
                # is false whenever nothing is live, so idle frames are untouched.
                parent_panel = getattr(self, "_parent_panel", None)
                if parent_panel is not None and parent_panel.needs_frame():
                    _needs_redraw = True
                # Platform-owned gallery is static except during explicit WAV
                # preview; update its progress bar and settled Play state only
                # while that preview is actually active.
                if self._mode == "creations":
                    creations_view = getattr(self, "_creations_screen", None)
                    if creations_view is not None and creations_view.needs_frame():
                        _needs_redraw = True
                _pending_motion_pos: tuple[int, int] | None = None
                _motion_seen = False
                for event in events:
                    if event.type == pygame.QUIT and self.allow_exit:
                        running = False
                    elif event.type == pygame.TEXTINPUT:
                        if self._mode == "parent_panel":
                            if self._parent_panel_accepts_text(time.monotonic()):
                                self._parent_panel.handle_text_input(event.text)
                                _needs_redraw = True
                        elif self._mode == "secret":
                            self._handle_secret_text(event.text)
                            _needs_redraw = True
                    elif event.type == pygame.KEYDOWN:
                        if self._mode == "parent_panel":
                            _needs_redraw = True
                            if not self._parent_panel.handle_key(event.key, pygame):
                                self._exit_parent_panel(pygame)
                        elif self._mode == "profiles" and self._parent_chord.handle_key_down(
                            event.key, time.monotonic()
                        ):
                            self._enter_parent_panel(pygame)
                            _needs_redraw = True
                        else:
                            running = self._handle_key(event.key, pygame)
                            _needs_redraw = True
                    elif event.type == pygame.KEYUP:
                        self._parent_chord.handle_key_up(event.key)
                    elif event.type == pygame.MOUSEMOTION:
                        # Coalesce: record only the last position. The single
                        # hit-test + gated speakable update happens once per
                        # frame after the event loop via _apply_coalesced_motion.
                        self._synthetic_pointer_active = True
                        if hasattr(event, "pos"):
                            _pending_motion_pos = event.pos
                            _motion_seen = True
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        _needs_redraw = True
                        if self._mode == "parent_panel":
                            if not self._parent_panel.handle_click(event.pos):
                                self._exit_parent_panel(pygame)
                        else:
                            self._handle_click(event.pos, pygame)
                    elif event.type == pygame.MOUSEWHEEL and self._mode == "activities":
                        self._scroll_activity_rows(-event.y, pygame)
                        _needs_redraw = True
                    elif event.type == pygame.VIDEORESIZE:
                        request = self._resize_display_request(event, pygame)
                        if request is not None:
                            screen = pygame.display.set_mode(*request)
                            _needs_redraw = True

                if _motion_seen and _pending_motion_pos is not None:
                    if self._apply_coalesced_motion(_pending_motion_pos):
                        _needs_redraw = True

                current_surface = pygame.display.get_surface()
                if current_surface is not None:
                    screen = current_surface
                if screen.get_size() != last_display_size:
                    last_display_size = screen.get_size()
                    self._icon_cache.clear()
                    self._font_cache.clear()
                    self._shadow_cache.clear()
                    self._decorated_icon_cache.clear()
                    self._label_surface_cache.clear()
                    self._category_label_cache.clear()
                    self._category_icon_cache.clear()
                    self._cached_activities_key = None
                    self._cached_activities_surface = None
                    self._cached_activities_targets.clear()
                    self._tile_surface_cache.clear()
                    self._backdrop_cache.clear()
                    self._dimmed_underlay = None
                    self._dimmed_underlay_key = None
                    self._activity_scroll_start = 0
                    self._clear_spoken_pointer()
                    if self._visual_cache is not None:
                        self._visual_cache.clear()
                    _needs_redraw = True
                if self._mode == "profiles":
                    if self._parent_chord.poll(time.monotonic()):
                        self._enter_parent_panel(pygame)
                        _needs_redraw = True
                elif self._mode == "parent_panel":
                    if self._parent_chord.is_holding:
                        # Drain chord auto-repeat while the keys are down.
                        pygame.event.clear(pygame.TEXTINPUT)
                    if self._parent_panel.drain():
                        _needs_redraw = True
                if self._rescan_if_due():
                    _needs_redraw = True
                try:
                    self._poll_spoken_labels(pygame, time.monotonic())
                except Exception:
                    pass

                is_animating = bool(self._launching_activity_id is not None)
                if _needs_redraw or is_animating or not self._first_frame_released:
                    self._draw(screen, pygame)
                    pygame.display.flip()
                    self._on_frame_presented(screen, pygame)
                    if not self._first_frame_released:
                        self._release_boot_cover()
                    _needs_redraw = False
                    clock.tick(60)
                else:
                    # Adaptive idle pacing: poll quickly right after interaction
                    # so input latency stays imperceptible, then relax the wake
                    # cadence to keep idle CPU low on Atom-class devices.
                    time.sleep(
                        idle_sleep_seconds(frame_start - self._last_input_monotonic)
                    )
        finally:
            if self.session is not None:
                self.session.clear()
            pygame.key.stop_text_input()
            pygame.quit()
        return 0

    def _poll_input_hooks(self, pygame: Any) -> None:
        """Optional hook called before polling pygame events each frame."""

    def _on_frame_presented(self, screen: Any, pygame: Any) -> None:
        """Optional presentation hook called immediately after each frame is flipped."""

    @property
    def _presented_activities(self) -> tuple[ActivityManifest, ...]:
        self._category_id = self._catalogue.nearest_category(self._category_id)
        return self._catalogue.collection(self._category_id).items

    def _columns(self, pygame: Any) -> int:
        surface = pygame.display.get_surface()
        width = surface.get_width() if surface is not None else 1024
        return 3 if width >= 760 else 2

    def _rows(self, pygame: Any) -> int:
        """Rows of Activity cards per page (presentation layers may refine)."""

        return 2

    def _page_capacity(self, pygame: Any) -> int:
        return max(1, self._columns(pygame) * self._rows(pygame))

    def _scroll_model(self, pygame: Any) -> ScrollModel:
        page_capacity = self._page_capacity(pygame)
        return ScrollModel(capacity=page_capacity, step=page_capacity)

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self._mode != "activities":
            return super()._handle_key(key, pygame)
        old_selected = getattr(self, "_selected", 0)
        old_category = getattr(self, "_category_id", None)
        old_scroll = getattr(self, "_activity_scroll_start", 0)
        was_launching = key in {pygame.K_RETURN, pygame.K_SPACE}
        if was_launching:
            try:
                self._stop_spoken_labels()  # type: ignore[attr-defined]
            except Exception:
                pass
        self._last_result = None
        self._catalogue_error = False
        activities = self._presented_activities
        if key == pygame.K_TAB:
            self._cycle_category(1)
        elif activities and key in {
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_UP,
            pygame.K_DOWN,
        }:
            columns = self._columns(pygame)
            if key == pygame.K_LEFT:
                delta = -1
            elif key == pygame.K_RIGHT:
                delta = 1
            elif key == pygame.K_UP:
                delta = -columns
            else:
                delta = columns
            self._selected = min(max(0, self._selected + delta), len(activities) - 1)
            self._ensure_selected_visible(pygame)
        elif activities and key == pygame.K_PAGEUP:
            self._scroll_activity_rows(-1, pygame)
        elif activities and key == pygame.K_PAGEDOWN:
            self._scroll_activity_rows(1, pygame)
        elif key in {pygame.K_RETURN, pygame.K_SPACE}:
            self._launch_selected(pygame)
            return True
        elif key == pygame.K_BACKSPACE and self._category_id != ALL_ACTIVITIES_ID:
            self._set_category(ALL_ACTIVITIES_ID)
        elif key == pygame.K_ESCAPE:
            if self._category_id != ALL_ACTIVITIES_ID:
                self._set_category(ALL_ACTIVITIES_ID)
            else:
                self._logout(pygame)
                try:
                    self._stop_spoken_labels()  # type: ignore[attr-defined]
                except Exception:
                    pass
                return True
        elif self.allow_exit and key == pygame.K_q:
            try:
                self._stop_spoken_labels()  # type: ignore[attr-defined]
            except Exception:
                pass
            return False
        # Spoken labels – immediate for real semantic changes
        try:
            if getattr(self, "_category_id", None) != old_category:
                if self._category_id == ALL_ACTIVITIES_ID:
                    pass
                else:
                    self._spoken_labels.announce_collection(  # type: ignore[attr-defined]
                        self._category_id, self._spoken_locale(), pygame  # type: ignore[attr-defined]
                    )
            elif was_launching:
                pass
            elif getattr(self, "_selected", 0) != old_selected or getattr(
                self, "_activity_scroll_start", 0
            ) != old_scroll:
                self._announce_selected_activity(pygame)  # type: ignore[attr-defined]
        except Exception:
            pass
        return True

    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        for target in reversed(self._targets):
            if not target.rect.collidepoint(position):
                continue
            if target.action == "error_badge_dismiss":
                self._last_result = None
                self._catalogue_error = False
                return
            if target.action == "activity_category":
                self._last_result = None
                self._catalogue_error = False
                self._set_category(str(target.value))
                try:
                    self._spoken_labels.announce_collection(  # type: ignore[attr-defined]
                        str(target.value), self._spoken_locale(), pygame  # type: ignore[attr-defined]
                    )
                except Exception:
                    pass
                return
            if target.action == "activity_category_back":
                self._last_result = None
                self._catalogue_error = False
                self._set_category(ALL_ACTIVITIES_ID)
                return
            if target.action == "presented_activity_page_prev":
                self._last_result = None
                self._catalogue_error = False
                old = getattr(self, "_selected", 0)
                self._scroll_activity_rows(-1, pygame)
                if getattr(self, "_selected", 0) != old:
                    try:
                        self._announce_selected_activity(pygame)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                return
            if target.action == "presented_activity_page_next":
                self._last_result = None
                self._catalogue_error = False
                old = getattr(self, "_selected", 0)
                self._scroll_activity_rows(1, pygame)
                if getattr(self, "_selected", 0) != old:
                    try:
                        self._announce_selected_activity(pygame)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                return
            if target.action == "presented_activity_page":
                self._last_result = None
                self._catalogue_error = False
                old = getattr(self, "_selected", 0)
                page_idx = int(target.value)
                page_cap = self._page_capacity(pygame)
                self._selected = min(page_idx * page_cap, len(self._presented_activities) - 1)
                self._ensure_selected_visible(pygame)
                if getattr(self, "_selected", 0) != old:
                    try:
                        self._announce_selected_activity(pygame)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                return
            if target.action == "presented_activity_select":
                self._last_result = None
                self._catalogue_error = False
                old = getattr(self, "_selected", 0)
                self._selected = int(target.value)
                self._ensure_selected_visible(pygame)
                if getattr(self, "_selected", 0) != old:
                    try:
                        self._announce_selected_activity(pygame)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                return
            if target.action == "presented_activity":
                self._last_result = None
                self._catalogue_error = False
                self._selected = int(target.value)
                self._ensure_selected_visible(pygame)
                try:
                    self._stop_spoken_labels()  # type: ignore[attr-defined]
                except Exception:
                    pass
                self._launch_selected(pygame)
                return
        super()._handle_click(position, pygame)

    def _scroll_activity_rows(self, direction: int, pygame: Any) -> None:
        activities = self._presented_activities
        if not activities or direction == 0:
            return
        page_capacity = self._page_capacity(pygame)
        delta = page_capacity * (-1 if direction < 0 else 1)
        self._selected = min(max(0, self._selected + delta), len(activities) - 1)
        self._ensure_selected_visible(pygame)

    def _ensure_selected_visible(self, pygame: Any) -> None:
        activities = self._presented_activities
        window = self._scroll_model(pygame).window(
            len(activities), self._selected, self._activity_scroll_start
        )
        self._activity_scroll_start = window.start

    def _cycle_category(self, delta: int) -> None:
        ids = self._catalogue.category_ids
        if not ids:
            return
        try:
            current = ids.index(self._category_id)
        except ValueError:
            current = 0
        self._set_category(ids[(current + delta) % len(ids)])

    def _set_category(self, category_id: str) -> None:
        resolved = self._catalogue.nearest_category(category_id)
        if resolved != self._category_id:
            self._clear_spoken_pointer()
        self._category_id = resolved
        self._selected = 0
        self._activity_scroll_start = 0

    def _rescan_activities(self) -> bool:
        token = self.registry.discovery_token()
        if token == self._activity_discovery_token:
            return False
        self._activity_discovery_token = token
        current = self._presented_activities
        selected_id = (
            current[self._selected].activity_id
            if current and self._selected < len(current)
            else None
        )
        try:
            discovered = self.registry.discover()
        except ActivityValidationError:
            changed = not self._catalogue_error
            self._catalogue_error = True
            return changed
        # Runtime authority must be rebuilt before the newly discovered manifest
        # is published into the child-facing catalogue. If that construction
        # fails, the last known-good service/catalogue pair remains authoritative.
        previous_activities = self._activities
        self._activities = discovered
        try:
            self._rebuild_runtime_services()
        except (ActivityValidationError, OSError, ValueError):
            self._activities = previous_activities
            changed = not self._catalogue_error
            self._catalogue_error = True
            return changed
        new_catalogue = ActivityCatalogue.from_activities(discovered)
        self._clear_spoken_pointer()
        self._catalogue_error = False
        self._catalogue = new_catalogue
        self._category_id = self._catalogue.nearest_category(self._category_id)
        presented = self._presented_activities
        self._selected = 0
        if selected_id:
            for index, activity in enumerate(presented):
                if activity.activity_id == selected_id:
                    self._selected = index
                    break
        self._activity_scroll_start = 0
        self._tile_surface_cache.clear()
        self._backdrop_cache.clear()
        self._cached_activities_key = None
        return True

    def _is_pointer_active(self, pygame: Any) -> bool:
        return bool(pygame.mouse.get_focused() or getattr(self, "_synthetic_pointer_active", False))

    def _pointer_pos(self, pygame: Any) -> tuple[int, int]:
        pos = getattr(self, "_pointer_position", None)
        return pos if pos is not None else pygame.mouse.get_pos()

    def _draw_pointer(self, screen: Any, pygame: Any) -> None:
        if not self._is_pointer_active(pygame):
            return
        from greia_platform.activity_ui import draw_activity_pointer

        pos = self._pointer_pos(pygame)
        draw_activity_pointer(screen, pos)

    def _target_at(self, pos: tuple[int, int] | None) -> tuple[str, Any] | None:
        if pos is None:
            return None
        for target in reversed(self._targets):
            if target.rect.collidepoint(pos):
                return (target.action, target.value)
        return None

    def _hover_semantic_identity(
        self, target: tuple[str, Any] | None
    ) -> tuple[Any, ...] | None:
        """Return stable hover identity independent of page/category index reuse."""

        if target is None:
            return None
        action, value = target
        locale = self._spoken_locale()
        try:
            if action in {"presented_activity", "presented_activity_select"}:
                index = int(value)
                activities = self._presented_activities
                if 0 <= index < len(activities):
                    return ("activity", activities[index].activity_id, locale)
            if action in {
                "home_collection",
                "activity_subcollection",
                "activity_category",
            }:
                return ("collection", str(value), locale)
        except (ValueError, TypeError, AttributeError, KeyError):
            pass
        return ("target", action, value)

    def _apply_coalesced_motion(self, position: tuple[int, int] | None) -> bool:
        """Apply one coalesced pointer position for the frame.

        Single ``_pointer_position`` update and one ``_target_at`` hit-test are
        performed for the settled position. Spoken focus is gated by stable
        semantic identity rather than raw (action, index), so catalogue/category
        mutations cannot silently reuse an index for a different Activity.
        Returns True when the once-per-frame redraw flag must be set. This method
        never draws or flips; the run loop's single present path stays authoritative.
        """

        if position is None:
            return False
        prev_pos = getattr(self, "_pointer_position", None)
        pointer_moved = prev_pos != position
        self._pointer_position = position
        prev_hover = getattr(self, "_coalesced_hover_target", None)
        prev_identity = getattr(self, "_coalesced_hover_identity", None)
        new_target = self._target_at(position)
        new_identity = self._hover_semantic_identity(new_target)

        # Compatibility with pre-existing state/tests that seeded only the raw
        # hover target: adopt the semantic key lazily without triggering speech.
        if new_target == prev_hover and prev_identity is None:
            self._coalesced_hover_identity = new_identity
            return pointer_moved
        if new_target == prev_hover and new_identity == prev_identity:
            return pointer_moved

        self._coalesced_hover_target = new_target
        self._coalesced_hover_identity = new_identity
        if new_identity == prev_identity:
            return True

        try:
            now = time.monotonic()
            new_sp = self._speakable_for_target(new_target)
            if new_sp is None:
                self._spoken_labels.pointer_focus_changed(None, None, now)
                self._spoken_labels.clear_pointer_focus()
            else:
                self._spoken_labels.pointer_focus_changed(new_sp[0], new_sp[1], now)
        except Exception:
            pass
        return True

    def _draw_activities(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
    ) -> None:
        width, height = screen.get_size()
        activities = self._presented_activities
        if not activities and self._category_id == ALL_ACTIVITIES_ID:
            self._draw_empty(screen, pygame)
            return
        # Inside a Collection an empty projection (an adaptive group chooser,
        # or every Activity hidden by Parent policy) still renders the page so
        # its header and local Back stay reachable; the content renderer owns
        # the empty state.

        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)

        hovered_target = None
        if pointer_active and self._cached_activities_targets:
            for target in self._cached_activities_targets:
                if target.rect.collidepoint(pointer):
                    hovered_target = (target.action, target.value)
                    break

        launch_elapsed = (
            time.monotonic() - self._launch_animation_started
            if self._launching_activity_id
            else None
        )
        launch_tick = (
            int(launch_elapsed * 60) if launch_elapsed is not None else None
        )

        static_key = (
            self._active_profile.profile.profile_id if self._active_profile else None,
            self._category_id,
            self._activity_scroll_start,
            self._selected,
            self._launching_activity_id,
            theme.background,
            theme.panel,
            theme.accent,
            theme.text,
            (width, height),
            self._active_locale,
            bool((self._last_result and not self._last_result.succeeded) or self._catalogue_error),
        )

        surface_ready = (
            self._cached_activities_surface is not None
            and self._cached_activities_surface.get_size() == (width, height)
        )
        if self._cached_activities_key == static_key and surface_ready:
            prev_hover = self._activities_hover_signature
            prev_tick = self._activities_launch_tick
            if hovered_target == prev_hover and launch_tick == prev_tick:
                self._present_cached_activities(screen, theme, pygame)
                return
            if self._repair_dynamic_activities(
                screen,
                theme,
                pygame,
                activities,
                prev_hover=prev_hover,
                new_hover=hovered_target,
                prev_tick=prev_tick,
                new_tick=launch_tick,
                pointer=pointer,
                pointer_active=pointer_active,
            ):
                self._activities_hover_signature = hovered_target
                self._activities_launch_tick = launch_tick
                self._present_cached_activities(screen, theme, pygame)
                return

        if (
            self._cached_activities_surface is None
            or self._cached_activities_surface.get_size() != (width, height)
        ):
            self._cached_activities_surface = pygame.Surface((width, height)).convert()

        self._cached_activities_surface.fill(theme.background)
        saved_targets = self._targets
        self._targets = []

        self._render_activities_content(self._cached_activities_surface, theme, pygame)

        self._cached_activities_key = static_key
        self._activities_hover_signature = hovered_target
        self._activities_launch_tick = launch_tick
        self._cached_activities_targets = list(self._targets)
        saved_targets.extend(self._targets)
        self._targets = saved_targets
        screen.blit(self._cached_activities_surface, (0, 0))
        self._draw_activity_title_disclosure(screen, theme, pygame)

    def _present_cached_activities(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        """Present the cached activities scene and refresh frame hit targets."""

        screen.blit(self._cached_activities_surface, (0, 0))
        self._targets.extend(self._cached_activities_targets)
        self._draw_activity_title_disclosure(screen, theme, pygame)

    def _repair_dynamic_activities(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        activities: tuple[ActivityManifest, ...],
        *,
        prev_hover: tuple[str, Any] | None,
        new_hover: tuple[str, Any] | None,
        prev_tick: int | None,
        new_tick: int | None,
        pointer: tuple[int, int],
        pointer_active: bool,
    ) -> bool:
        """Repair only hover/launch-affected activity tiles inside the cache.

        The cached scene surface is an opaque copy of the composed backdrop plus
        every card. When only pointer-hover or the launch-animation tick
        changes, restoring those tiles' padded regions from the pre-composited
        backdrop and re-blitting just those cards avoids a full-scene rebuild.
        Returns False whenever any aspect exceeds tile-level dynamics so the
        caller falls back to the proven full rebuild.
        """

        backdrop = getattr(self, "_last_scene_backdrop", None)
        cached_surface = self._cached_activities_surface
        if backdrop is None or cached_surface is None:
            return False

        SUPPORTED_ACTIONS = {
            "presented_activity",
            "presented_activity_page_prev",
            "presented_activity_page_next",
            "activity_category",
            "activity_category_back",
        }

        def _is_supported(signature: tuple[str, Any] | None) -> bool:
            return signature is None or signature[0] in SUPPORTED_ACTIONS

        if not _is_supported(prev_hover) or not _is_supported(new_hover):
            return False

        rects_by_index = {
            target.value: target.rect.copy()
            for target in self._cached_activities_targets
            if target.action == "presented_activity"
        }

        damage_tiles: dict[int, Any] = {}
        for signature in (prev_hover, new_hover):
            if signature is not None and signature[0] == "presented_activity":
                rect = rects_by_index.get(signature[1])
                if rect is None:
                    return False
                damage_tiles[int(signature[1])] = rect

        launching_changed = new_tick != prev_tick and self._launching_activity_id
        if launching_changed:
            for target in self._cached_activities_targets:
                if target.action != "presented_activity":
                    continue
                index = int(target.value)
                if 0 <= index < len(activities) and (
                    activities[index].activity_id == self._launching_activity_id
                ):
                    damage_tiles[index] = target.rect.copy()
                    break

        arrow_targets = {
            target.action: target
            for target in self._cached_activities_targets
            if target.action in ("presented_activity_page_prev", "presented_activity_page_next")
        }
        damage_arrows: dict[str, Any] = {}
        for signature in (prev_hover, new_hover):
            if signature is not None and signature[0] in (
                "presented_activity_page_prev",
                "presented_activity_page_next",
            ):
                target = arrow_targets.get(signature[0])
                if target is None:
                    return False
                damage_arrows[signature[0]] = target

        damage_header = False
        for signature in (prev_hover, new_hover):
            if signature is not None and signature[0] in (
                "activity_category",
                "activity_category_back",
            ):
                damage_header = True
                break

        if not damage_tiles and not damage_arrows and not damage_header:
            return False

        backdrop_rect = backdrop.get_rect()

        # 1. Repair cards
        if damage_tiles:
            for index, rect in sorted(damage_tiles.items()):
                if not 0 <= index < len(activities):
                    return False
                restore = rect.inflate(*self._TILE_REPAIR_PAD).clip(backdrop_rect)
                cached_surface.blit(backdrop, restore.topleft, restore)

            for index, rect in sorted(damage_tiles.items()):
                activity = activities[index]
                state = InteractionVisualState(
                    hovered=pointer_active and rect.collidepoint(pointer),
                    selected=index == self._selected,
                    launching=activity.activity_id == self._launching_activity_id,
                )
                self._draw_activity_tile(
                    cached_surface, rect, activity, state, theme, pygame
                )

        # 2. Repair navigation arrows
        if damage_arrows:
            for action, target in damage_arrows.items():
                rect = target.rect
                restore = rect.inflate(24, 24).clip(backdrop_rect)
                cached_surface.blit(backdrop, restore.topleft, restore)
                hovered = pointer_active and rect.collidepoint(pointer)
                direction = (
                    "previous" if action == "presented_activity_page_prev" else "next"
                )
                if hasattr(self, "_draw_page_arrow_button"):
                    self._draw_page_arrow_button(
                        cached_surface, theme, pygame, direction, rect, hovered
                    )
                else:
                    return False

        # 3. Repair category bar (semantic region owner)
        if damage_header:
            header_rect = self._activities_header_repair_rect(screen, pygame).clip(
                backdrop_rect
            )
            cached_surface.blit(backdrop, header_rect.topleft, header_rect)
            saved_targets = self._targets
            self._targets = []
            try:
                self._draw_category_bar(cached_surface, theme, pygame)
            finally:
                self._targets = saved_targets

        return True

    def _activities_header_repair_rect(self, screen: Any, pygame: Any) -> Any:
        """Return the header region restored before the category bar is redrawn.

        It must cover every pixel the category bar/header may draw and nothing
        drawn by other owners (profile badge, cards, top-right badges).
        """

        left = 112 if self._active_profile is not None else 20
        error_active = (
            (self._last_result and not self._last_result.succeeded)
            or self._catalogue_error
        )
        has_topright_badge = (
            error_active
            or getattr(self, "_achievement_service", None) is not None
            or getattr(self, "_achievement_snapshot", None) is not None
        )
        right = screen.get_width() - (96 if has_topright_badge else 20)
        return pygame.Rect(left - 4, 0, max(0, right - left + 8), 84)

    def _draw_activity_title_disclosure(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        try:
            activities = self._presented_activities
            if not activities:
                return
            pointer = self._pointer_pos(pygame)
            pointer_active = self._is_pointer_active(pygame)

            target_activity = None
            target_rect = None

            if pointer_active and self._cached_activities_targets:
                for target in self._cached_activities_targets:
                    if target.action == "presented_activity" and target.rect.collidepoint(pointer):
                        if 0 <= target.value < len(activities):
                            target_activity = activities[target.value]
                            target_rect = target.rect
                            break

            if target_activity is None or target_rect is None:
                return
            if isinstance(target_activity, ActivityFolder):
                return

            full_title = self._child_display_text(
                _activity_title(target_activity, self._active_locale)
            )
            if not full_title:
                return

            font = self._font(15, pygame)
            width, height = screen.get_size()
            max_w = min(320, width - 40)

            # Word wrap for tooltip if title is very long
            words = full_title.strip().split()
            lines: list[str] = []
            current_line = ""
            usable_w = max(60, max_w - 24)

            for word in words:
                test = f"{current_line} {word}".strip() if current_line else word
                if font.size(test)[0] <= usable_w:
                    current_line = test
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            if not lines:
                lines = [full_title]

            line_h = font.get_linesize()
            text_surfaces = [font.render(line, True, theme.text) for line in lines]
            text_w = max(s.get_width() for s in text_surfaces)
            text_h = len(text_surfaces) * line_h

            pad_x = 12
            pad_y = 7
            pw = text_w + pad_x * 2
            ph = text_h + pad_y * 2

            px = target_rect.centerx - pw // 2
            px = max(16, min(width - pw - 16, px))

            # Smart placement: above the card if possible, otherwise below
            py = target_rect.top - ph - 6
            if py < 65:
                py = target_rect.bottom + 6

            # 1. Tactile shadow
            shadow_rect = pygame.Rect(px + 2, py + 3, pw, ph)
            pygame.draw.rect(
                screen, _mix(theme.background, (0, 0, 0), 0.16), shadow_rect, border_radius=12
            )

            # 2. Pill background
            pill_rect = pygame.Rect(px, py, pw, ph)
            bg_color = (
                min(255, getattr(theme, "panel", (255, 255, 255))[0] + 12),
                min(255, getattr(theme, "panel", (255, 255, 255))[1] + 12),
                min(255, getattr(theme, "panel", (255, 255, 255))[2] + 12),
            )
            pygame.draw.rect(screen, bg_color, pill_rect, border_radius=12)
            pygame.draw.rect(screen, theme.accent, pill_rect, width=2, border_radius=12)

            # 3. Text lines
            for i, ts in enumerate(text_surfaces):
                tx = px + (pw - ts.get_width()) // 2
                ty = py + pad_y + i * line_h
                screen.blit(ts, (tx, ty))
        except Exception:
            pass

    def _render_activities_content(self, screen: Any, theme: Any, pygame: Any) -> None:
        width, height = screen.get_size()
        if self._active_profile is not None:
            badge_size = max(62, min(86, height // 7))
            badge = pygame.Rect(14, 10, badge_size, badge_size)
            shadow = self._shadow_for(badge.size, pygame)
            draw_raised_panel(
                screen,
                badge,
                pygame,
                fill=theme.panel,
                outline=theme.accent,
                state=InteractionVisualState(
                    hovered=badge.collidepoint(self._pointer_pos(pygame)) and self._is_pointer_active(pygame)
                ),
                style=self._DEPTH,
                cached_shadow=shadow,
                selected_width=5,
            )
            avatar = self._load_icon(
                self._active_profile.profile.avatar_id, badge_size - 14, pygame
            )
            screen.blit(avatar, avatar.get_rect(center=badge.center))
            self._targets.append(HitTarget("switch_profile", None, badge))

        self._draw_category_bar(screen, theme, pygame)
        activities = self._presented_activities
        if not activities:
            self._draw_empty(screen, pygame)
            return

        columns = self._columns(pygame)
        rows = self._rows(pygame)
        page_capacity = max(1, columns * rows)
        self._selected = max(0, min(self._selected, max(0, len(activities) - 1)))
        self._activity_scroll_start = max(0, min(self._activity_scroll_start, max(0, len(activities) - 1)))
        scroll = ScrollModel(capacity=page_capacity, step=page_capacity)
        window = scroll.window(
            len(activities), self._selected, self._activity_scroll_start
        )
        self._activity_scroll_start = window.start
        gap = max(14, min(22, width // 48))

        inner_panel = (
            getattr(self, "_shared_panel_inner_rect", None)
            if not getattr(self, "_shared_panel_disabled", False)
            else None
        )

        has_pagination = (len(activities) > page_capacity)

        from .navigation_layout import (
            compute_navigation_safe_content_bounds,
            resolve_constrained_square_tile_size,
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

        if inner_panel is not None:
            pad_x = max(14, inner_panel.width // 45)
            pad_y = max(8, inner_panel.height // 40)
            pagination_reserve = 38 if has_pagination else 0
            avail_w = max(240, inner_panel.width - pad_x * 2)
            avail_h = max(180, inner_panel.height - pad_y * 2 - pagination_reserve)
            if has_pagination:
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

            # 218 = 210 reference tile +4%: larger cards give two-line labels
            # breathing room while label font sizes stay unchanged.
            tile_size = max(
                1,
                resolve_constrained_square_tile_size(
                    avail_w,
                    avail_h,
                    columns=columns,
                    rows=rows,
                    gap=gap,
                    preferred_max=218,
                    preferred_min=120,
                ),
            )
            total_width = columns * tile_size + (columns - 1) * gap
            total_height = rows * tile_size + (rows - 1) * gap
            origin_x = safe_origin_x + (avail_w - total_width) // 2
            origin_y = inner_panel.top + pad_y + max(0, (avail_h - total_height) // 2)
        else:
            top = max(116, height // 5)
            pagination_reserve = 38 if has_pagination else 0
            available_h = height - top - 28 - pagination_reserve
            raw_content = UiRect(0, top, width, available_h)
            if has_pagination:
                safe_rect = compute_navigation_safe_content_bounds(
                    viewport,
                    available_content_rect=raw_content,
                    button_size=nav_button_size,
                )
                usable_w = safe_rect.width
                safe_origin_x = safe_rect.x
            else:
                side_reserve = 86
                usable_w = max(240, width - side_reserve)
                safe_origin_x = (width - usable_w) // 2

            tile_size = max(
                1,
                resolve_constrained_square_tile_size(
                    usable_w,
                    available_h,
                    columns=columns,
                    rows=rows,
                    gap=gap,
                    preferred_max=218,
                    preferred_min=120,
                ),
            )
            total_width = columns * tile_size + (columns - 1) * gap
            total_height = rows * tile_size + (rows - 1) * gap
            origin_x = safe_origin_x + max(0, (usable_w - total_width) // 2)
            origin_y = top + max(0, (available_h - total_height) // 2)

        self._page_content_rect = UiRect(origin_x, origin_y, total_width, total_height)

        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)
        for local_index, presented_index in enumerate(
            range(window.start, window.stop)
        ):
            activity = activities[presented_index]
            column = local_index % columns
            row = local_index // columns
            rect = pygame.Rect(
                origin_x + column * (tile_size + gap),
                origin_y + row * (tile_size + gap),
                tile_size,
                tile_size,
            )
            state = InteractionVisualState(
                hovered=pointer_active and rect.collidepoint(pointer),
                selected=presented_index == self._selected,
                launching=activity.activity_id == self._launching_activity_id,
            )
            self._draw_activity_tile(screen, rect, activity, state, theme, pygame)
            self._targets.append(
                HitTarget("presented_activity", presented_index, rect)
            )
        self._draw_pagination_and_overflow(screen, theme, pygame, window, columns, inner_panel)
        if (self._last_result and not self._last_result.succeeded) or self._catalogue_error:
            self._draw_error_badge(screen, pygame)

    def _draw_error_badge(self, screen: Any, pygame: Any) -> None:
        size = max(42, min(56, screen.get_height() // 10))
        icon = self._load_icon("close_button", size, pygame)
        rect = pygame.Rect(screen.get_width() - size - 14, 14, size, size)
        screen.blit(icon, icon.get_rect(center=rect.center))
        self._targets.append(HitTarget("error_badge_dismiss", None, rect))

    @property
    def _active_locale(self) -> str:
        if self._active_profile is not None and getattr(self._active_profile.profile, "locale", None):
            return self._active_profile.profile.locale
        return os.environ.get("GREIA_PROFILE_LOCALE") or os.environ.get("GREIA_DEVICE_LOCALE") or "it"

    def _draw_category_bar(self, screen: Any, theme: Any, pygame: Any) -> None:
        if not self._catalogue.category_ids:
            return
        if self._category_id != ALL_ACTIVITIES_ID:
            self._draw_category_header(screen, theme, pygame)
            return

        collections = tuple(
            item
            for item in self._catalogue.collections
            if item.collection_id != ALL_ACTIVITIES_ID
        )
        if not collections:
            return
        left = 112 if self._active_profile is not None else 20
        error_active = (self._last_result and not self._last_result.succeeded) or self._catalogue_error
        right = screen.get_width() - (76 if error_active else 20)
        gap = 9
        height = max(42, min(52, screen.get_height() // 11))
        available = max(0, right - left)
        show_labels = available >= len(collections) * 112
        x = left
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)
        for collection in collections:
            label_text = _category_title(collection.collection_id, self._active_locale)
            font_size = max(18, min(22, height // 2))
            label = self._category_label_surface(label_text, font_size, theme.text, pygame)
            icon_size = max(26, height - 14)
            if show_labels:
                width = min(174, max(88, label.get_width() + icon_size + 32))
            else:
                width = height
            if x + width > right:
                break
            rect = pygame.Rect(x, 18, width, height)
            hovered = pointer_active and rect.collidepoint(pointer)
            drawn = rect.move(0, -1 if hovered else 0)

            # Grounding drop shadow
            shadow_rect = drawn.move(0, 2 if hovered else 1)
            shadow_color = _mix(theme.background, (0, 0, 0), 0.10 if hovered else 0.06)
            pygame.draw.rect(screen, shadow_color, shadow_rect, border_radius=height // 2)

            # Pill background fill
            bg_color = _mix(theme.panel, (255, 255, 255), 0.35) if hovered else theme.panel
            pygame.draw.rect(screen, bg_color, drawn, border_radius=height // 2)

            # Subtle top sheen highlight line
            sheen_color = _mix(bg_color, (255, 255, 255), 0.55)
            pygame.draw.line(
                screen,
                sheen_color,
                (drawn.left + height // 3, drawn.top + 1),
                (drawn.right - height // 3, drawn.top + 1),
                width=1,
            )

            outline = (
                theme.accent if hovered else _mix(theme.text, theme.panel, 0.72)
            )
            pygame.draw.rect(
                screen,
                outline,
                drawn,
                width=3 if hovered else 2,
                border_radius=height // 2,
            )
            category_icon = self._category_shadowed_icon(
                collection.icon_id or "backpack",
                icon_size,
                shadow_alpha=40,
                shadow_offset=2,
                pygame=pygame,
            )
            if show_labels:
                icon_center = (drawn.left + 12 + icon_size // 2, drawn.centery)
                screen.blit(
                    category_icon,
                    category_icon.get_rect(center=icon_center),
                )
                label_rect = label.get_rect(
                    midleft=(drawn.left + 20 + icon_size, drawn.centery)
                )
                screen.blit(label, label_rect)
            else:
                screen.blit(
                    category_icon,
                    category_icon.get_rect(center=drawn.center),
                )
            self._targets.append(
                HitTarget("activity_category", collection.collection_id, rect)
            )
            x += width + gap

    def _draw_category_header(self, screen: Any, theme: Any, pygame: Any) -> None:
        """Draw persistent in-category identity and a local return-to-All control."""

        collections = tuple(
            item
            for item in self._catalogue.collections
            if item.collection_id != ALL_ACTIVITIES_ID
        )
        left = 112 if self._active_profile is not None else 20
        height = max(46, min(56, screen.get_height() // 10))
        back_rect = pygame.Rect(left, 16, height, height)
        hovered = back_rect.collidepoint(self._pointer_pos(pygame)) and self._is_pointer_active(pygame)
        drawn = back_rect.move(0, -2 if hovered else 0)

        icon_btn_fn = getattr(self, "_icon_button_surface", None)
        frame = icon_btn_fn(height, pygame, variant="hover" if hovered else "default") if icon_btn_fn else None

        if frame is not None:
            screen.blit(frame, drawn)
        else:
            # Circular tactile button fallback
            shadow_rect = drawn.move(0, 3)
            pygame.draw.circle(
                screen, (0, 0, 0, 35), shadow_rect.center, drawn.width // 2
            )
            pygame.draw.circle(screen, theme.panel, drawn.center, drawn.width // 2)
            border_color = (
                theme.accent if hovered else _mix(theme.text, theme.panel, 0.72)
            )
            pygame.draw.circle(
                screen,
                border_color,
                drawn.center,
                drawn.width // 2,
                width=3 if hovered else 2,
            )

        from greia_platform.activity_ui import draw_back_symbol

        arrow_color = (
            _mix(theme.accent, (40, 20, 10), 0.30) if hovered else theme.text
        )
        symbol_rect = drawn.move(0, -2 if frame is not None else 0)
        draw_back_symbol(screen, symbol_rect, arrow_color)
        self._targets.append(
            HitTarget("activity_category_back", ALL_ACTIVITIES_ID, back_rect)
        )

        # Category Switcher Strip
        x = back_rect.right + 14
        error_active = (self._last_result and not self._last_result.succeeded) or self._catalogue_error
        has_topright_badge = (
            error_active
            or getattr(self, "_achievement_service", None) is not None
            or getattr(self, "_achievement_snapshot", None) is not None
        )
        right = screen.get_width() - (96 if has_topright_badge else 20)
        gap = 8
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)

        for col in collections:
            is_active = (col.collection_id == self._category_id)
            label_text = _category_title(col.collection_id, self._active_locale)
            count = len(col.items)
            display_text = f"{label_text} ({count})" if is_active else label_text
            font_size = max(15, min(19, height // 2))
            label = self._category_label_surface(display_text, font_size, theme.text, pygame)
            icon_size = max(24, height - 16)

            if is_active:
                chip_width = min(220, max(110, label.get_width() + icon_size + 28))
            else:
                chip_width = min(150, max(46, label.get_width() + icon_size + 24)) if (right - x > len(collections) * 80) else height

            if x + chip_width > right:
                break

            chip_rect = pygame.Rect(x, 16, chip_width, height)
            h_chip = pointer_active and chip_rect.collidepoint(pointer)
            is_highlighted = is_active or h_chip
            drawn_chip = chip_rect.move(0, -1 if is_highlighted else 0)

            # Grounding drop shadow
            shadow_rect = drawn_chip.move(0, 2 if is_highlighted else 1)
            shadow_color = _mix(theme.background, (0, 0, 0), 0.12 if is_active else 0.07)
            pygame.draw.rect(screen, shadow_color, shadow_rect, border_radius=height // 2)

            # Pill background fill
            if is_active:
                bg_color = _mix(theme.panel, theme.accent, 0.15)
            elif h_chip:
                bg_color = _mix(theme.panel, (255, 255, 255), 0.35)
            else:
                bg_color = theme.panel
            pygame.draw.rect(screen, bg_color, drawn_chip, border_radius=height // 2)

            # Subtle top sheen highlight line
            sheen_color = _mix(bg_color, (255, 255, 255), 0.55)
            pygame.draw.line(
                screen,
                sheen_color,
                (drawn_chip.left + height // 3, drawn_chip.top + 1),
                (drawn_chip.right - height // 3, drawn_chip.top + 1),
                width=1,
            )

            # Outline
            outline_color = theme.accent if (is_active or h_chip) else _mix(theme.text, theme.panel, 0.75)
            outline_width = 3 if is_active else (2 if h_chip else 1)
            pygame.draw.rect(screen, outline_color, drawn_chip, width=outline_width, border_radius=height // 2)

            cat_icon = self._category_shadowed_icon(
                col.icon_id or "backpack",
                icon_size,
                shadow_alpha=48 if is_active else 30,
                shadow_offset=2,
                pygame=pygame,
            )

            if chip_width > height:
                icon_center = (drawn_chip.left + 12 + icon_size // 2, drawn_chip.centery)
                screen.blit(cat_icon, cat_icon.get_rect(center=icon_center))
                label_rect = label.get_rect(midleft=(drawn_chip.left + 16 + icon_size, drawn_chip.centery))
                screen.blit(label, label_rect)
            else:
                screen.blit(cat_icon, cat_icon.get_rect(center=drawn_chip.center))

            if not is_active:
                self._targets.append(
                    HitTarget("activity_category", col.collection_id, chip_rect)
                )

            x += chip_width + gap

    def _category_label_surface(
        self, text: str, size: int, color: tuple[int, int, int], pygame: Any
    ) -> Any:
        # Single child-facing case chokepoint for every Collection/Category/
        # discovery-group label rendered by the Shell and its mixins.
        text = self._child_display_text(text)
        key = (text, size, color)
        cached = self._category_label_cache.get(key)
        if cached is not None:
            return cached
        rendered = self._font(size, pygame).render(text, True, color)
        self._category_label_cache[key] = rendered
        return rendered

    def _category_shadowed_icon(
        self,
        icon_id: str,
        size: int,
        shadow_alpha: int,
        shadow_offset: int,
        pygame: Any,
    ) -> Any:
        key = (icon_id, size, shadow_alpha, shadow_offset)
        cached = self._category_icon_cache.get(key)
        if cached is not None:
            return cached
        base = self._load_icon(icon_id, size, pygame)
        shadowed = make_shadowed_icon(
            base,
            pygame,
            shadow_alpha=shadow_alpha,
            shadow_offset=shadow_offset,
        )
        self._category_icon_cache[key] = shadowed
        return shadowed

    def _draw_pagination_and_overflow(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        window: Any,
        columns: int,
        inner_panel: Any = None,
    ) -> None:
        activities = self._presented_activities
        if not activities:
            return
        page_capacity = self._page_capacity(pygame)
        from .navigation_layout import PageControlsState

        page_state = PageControlsState.from_scroll_window(
            window,
            page_capacity=page_capacity,
            total_items=len(activities),
        )
        self._draw_page_controls(
            screen,
            theme,
            pygame,
            page_state,
            previous_action="presented_activity_page_prev",
            next_action="presented_activity_page_next",
            total=len(activities),
        )

    def _draw_scroll_controls(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        window: Any,
        columns: int,
    ) -> None:
        self._draw_pagination_and_overflow(screen, theme, pygame, window, columns)

    def _draw_activity_tile(
        self,
        screen: Any,
        rect: Any,
        activity: ActivityManifest,
        state: InteractionVisualState,
        theme: Any,
        pygame: Any,
    ) -> None:
        if not state.launching:
            key = (
                activity.activity_id,
                activity.version,
                rect.width,
                rect.height,
                state.hovered,
                state.selected,
                theme.panel,
                theme.accent,
                theme.text,
                theme.background,
                self._active_locale,
                self._activity_tile_style_token(),
            )
            cached = self._tile_surface_cache.get(key)
            if cached is None:
                pad_x = 8
                pad_y = 12
                w = rect.width + pad_x * 2
                h = rect.height + pad_y * 2
                surf = pygame.Surface((w, h), pygame.SRCALPHA)
                local_rect = pygame.Rect(pad_x, pad_y, rect.width, rect.height)
                self._draw_activity_tile_content(
                    surf, local_rect, activity, state, theme, pygame
                )
                self._tile_surface_cache[key] = (surf, pad_x, pad_y)
                cached = (surf, pad_x, pad_y)
            surf, pad_x, pad_y = cached
            screen.blit(surf, (rect.left - pad_x, rect.top - pad_y))
            return

        self._draw_activity_tile_content(screen, rect, activity, state, theme, pygame)

    def _activity_tile_style_token(self) -> Any:
        """Extra tile-cache identity for presentation layers (e.g. a Collection hue)."""

        return None

    def _draw_activity_tile_content(
        self,
        screen: Any,
        rect: Any,
        activity: ActivityManifest,
        state: InteractionVisualState,
        theme: Any,
        pygame: Any,
    ) -> None:
        if isinstance(activity, ActivityFolder):
            self._draw_folder_tile_fallback(screen, rect, activity, state, theme, pygame)
            return
        motion = (
            self._LAUNCH.sample(time.monotonic() - self._launch_animation_started)
            if state.launching
            else self._HOVER.sample(state)
        )
        outline = (
            theme.accent
            if state.emphasized
            else _mix(theme.text, theme.panel, 0.72)
        )
        target = transformed_rect(rect, motion, pygame)
        shared_shadow_drawn = False
        if self._visual_cache is not None:
            try:
                shadow_w = max(32, int(round(target.width * 1.06)))
                shadow_h = max(12, min(64, int(round(shadow_w * 150 / 520))))
                shadow_surf = self._visual_cache.get(
                    "ui.shadow.soft",
                    variant="default",
                    size=(shadow_w, shadow_h),
                )
                shadow_y = (
                    target.bottom
                    - max(2, int(round(shadow_h * 0.20)))
                    + int(round(motion.shadow_lift * 2.0))
                )
                shadow_rect = shadow_surf.get_rect(center=(target.centerx, shadow_y))
                screen.blit(shadow_surf, shadow_rect)
                shared_shadow_drawn = True
            except (
                VisualSurfaceCacheError,
                AssetCatalogueError,
                KeyError,
                FileNotFoundError,
                OSError,
                ValueError,
                pygame.error,
            ):
                shared_shadow_drawn = False

        if not shared_shadow_drawn:
            usable_shadow = (
                self._shadow_for(rect.size, pygame)
                if target.size == rect.size
                else None
            )
            draw_soft_shadow(
                screen,
                target,
                pygame,
                style=self._DEPTH,
                lift=motion.shadow_lift,
                cached_shadow=usable_shadow,
            )

        radius = min(self._DEPTH.radius, target.width // 2, target.height // 2)
        pygame.draw.rect(screen, theme.panel, target, border_radius=radius)
        width = 8 if state.emphasized else 3
        pygame.draw.rect(screen, outline, target, width=max(1, width), border_radius=radius)
        tile = target

        # Reserve a real label band instead of treating the Activity name as an
        # incidental caption. This keeps names legible across icon aspect ratios
        # and makes every Activity identifiable even when its artwork is novel.
        label_height = max(38, min(56, int(tile.height * 0.28)))
        label_rect = pygame.Rect(
            tile.left + 8,
            tile.bottom - label_height - 6,
            tile.width - 16,
            label_height,
        )
        # Icons read slightly larger while labels render a step smaller: the
        # artwork is the child's primary identifier, the name is support.
        icon_room = max(48, label_rect.top - tile.top - 10)
        icon_size = max(56, min(int(tile.width * 0.82), icon_room))
        icon = self._activity_icon(activity, icon_size, pygame)
        icon_center_y = tile.top + max(10, (label_rect.top - tile.top) // 2)
        screen.blit(
            icon,
            icon.get_rect(center=(tile.centerx, icon_center_y)),
        )
        title = self._render_activity_label(
            self._child_display_text(_activity_title(activity, self._active_locale)),
            max_width=label_rect.width - 10,
            max_height=label_rect.height - 4,
            pygame=pygame,
            color=theme.text,
            preferred_size=max(14, min(22, tile.height // 9)),
        )
        screen.blit(title, title.get_rect(center=label_rect.center))

        if state.selected:
            star_size = max(20, min(28, tile.width // 6))
            star_rect = pygame.Rect(tile.right - star_size - 6, tile.top + 6, star_size, star_size)
            cx, cy = star_rect.center
            r_out = star_size // 2
            r_in = r_out * 0.45
            star_pts = []
            for i in range(10):
                angle = i * math.pi / 5 - math.pi / 2
                r = r_out if i % 2 == 0 else r_in
                star_pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            pygame.draw.polygon(screen, (255, 193, 7), star_pts)
            pygame.draw.polygon(screen, (255, 160, 0), star_pts, width=2)

        if state.launching:
            badge_h = max(26, min(34, tile.height // 7))
            badge_w = min(tile.width - 16, 140)
            badge_rect = pygame.Rect(0, 0, badge_w, badge_h)
            badge_rect.center = (tile.centerx, icon_center_y)
            pygame.draw.rect(screen, (239, 77, 83), badge_rect, border_radius=badge_h // 2)
            pygame.draw.rect(screen, (255, 255, 255), badge_rect, width=2, border_radius=badge_h // 2)
            font_launch = self._font(max(13, min(17, badge_h // 2)), pygame)
            launch_text = font_launch.render(
                self._child_display_text(_launch_status_label(self._active_locale)), True, (255, 255, 255)
            )
            screen.blit(launch_text, launch_text.get_rect(center=badge_rect.center))

    def _draw_folder_tile_fallback(
        self,
        screen: Any,
        rect: Any,
        folder: ActivityFolder,
        state: InteractionVisualState,
        theme: Any,
        pygame: Any,
    ) -> None:
        """Primitive theme-folder tile used when shared artwork is unavailable."""

        target = transformed_rect(rect, self._HOVER.sample(state), pygame)
        tab = pygame.Rect(target.x, target.y, target.width * 2 // 5, max(10, target.height // 8))
        body = pygame.Rect(target.x, tab.bottom - 4, target.width, target.bottom - tab.bottom + 4)
        fill = _mix(theme.panel, (243, 154, 56), 0.35)
        outline = theme.accent if state.emphasized else _mix(theme.text, theme.panel, 0.5)
        for part in (tab, body):
            pygame.draw.rect(screen, fill, part, border_radius=12)
            pygame.draw.rect(screen, outline, part, width=4 if state.emphasized else 2, border_radius=12)
        label_h = max(30, body.height // 4)
        icon_size = max(24, min(body.width - 20, body.height - label_h - 12))
        icon = self._category_shadowed_icon(
            folder.group.icon_id or "backpack", icon_size, shadow_alpha=40,
            shadow_offset=2, pygame=pygame,
        )
        screen.blit(icon, icon.get_rect(center=(body.centerx, body.top + 6 + icon_size // 2)))
        title = self._category_label_surface(
            f"{folder.group.title or folder.folder_id} ({len(folder.items)})",
            max(14, min(20, label_h // 2)), theme.text, pygame,
        )
        if title.get_width() > body.width - 8:
            scale = (body.width - 8) / title.get_width()
            title = pygame.transform.smoothscale(
                title, (body.width - 8, max(1, round(title.get_height() * scale)))
            )
        screen.blit(title, title.get_rect(center=(body.centerx, body.bottom - label_h // 2)))

    def _render_activity_label(
        self,
        text: str,
        *,
        max_width: int,
        max_height: int,
        pygame: Any,
        color: tuple[int, int, int],
        preferred_size: int,
    ) -> Any:
        """Fit one Activity name without geometrically distorting glyphs using at most two lines."""

        cache_key = (text, max_width, max_height, color, preferred_size)
        cached = self._label_surface_cache.get(cache_key)
        if cached is not None:
            return cached

        # The child Shell's font provider multiplies requested sizes by the
        # profile interface scale, while card geometry stays in layout pixels.
        # Divide the requested range by the scale so the *effective* font is
        # what competes against the label band; otherwise large profiles push
        # every candidate past the band and the fallback clips glyphs.
        scale = getattr(self.theme_controller, "interface_scale", 1.0) or 1.0
        effective_preferred = max(11, int(round(preferred_size / scale)))
        effective_min = max(9, int(round(12 / scale)))

        result = render_activity_card_label(
            text,
            max_width=max_width,
            max_height=max_height,
            font_provider=lambda sz: self._font(sz, pygame),
            color=color,
            preferred_size=effective_preferred,
            pygame=pygame,
            min_size=effective_min,
        )
        self._label_surface_cache[cache_key] = result
        return result

    def _child_display_text(self, text: str) -> str:
        """Present child-facing Shell text under the active profile's case policy.

        Greia's youngest children learn CAPITAL letters first, so the platform
        default upper-cases child-facing words. When no child is active the
        launch environment policy applies (uppercase unless disabled). Parent
        surfaces are adult-facing and deliberately bypass this helper.
        """

        active = getattr(self, "_active_profile", None)
        if active is not None:
            return text.upper() if active.profile.uppercase_text else text
        if child_text_case_from_environment() is ChildTextCase.UPPERCASE:
            return text.upper()
        return text

    def _activity_icon(
        self, activity: ActivityManifest, size: int, pygame: Any
    ) -> Any:
        key = (activity.activity_id, activity.version, size)
        cached = self._decorated_icon_cache.get(key)
        if cached is not None:
            return cached

        raw_source = self._activity_raw_icon(activity, size, pygame)
        source = contain_fit_icon_surface(raw_source, size, pygame, safe_padding_ratio=0.03)
        decorated = make_shadowed_icon(
            source,
            pygame,
            shadow_alpha=54,
            shadow_offset=max(2, size // 28),
        )
        self._decorated_icon_cache[key] = decorated
        return decorated

    def _activity_raw_icon(
        self, activity: ActivityManifest, size: int, pygame: Any
    ) -> Any:
        """Return the decoded package icon once per Activity version (bounded cache)."""

        raw_key = ("raw_icon", activity.activity_id, activity.version)
        raw_source = self._icon_cache.get(raw_key)
        if raw_source is None:
            try:
                package_path = package_icon_path(activity)
                if package_path is not None:
                    raw_source = pygame.image.load(str(package_path)).convert_alpha()
                else:
                    raw_source = self._load_icon(activity.icon_id, size, pygame)
            except (ActivityIconError, OSError, ValueError, pygame.error):
                self._catalogue_error = True
                raw_source = self._load_icon("robot", size, pygame)
            self._icon_cache[raw_key] = raw_source
        return raw_source

    def _shadow_for(self, size: tuple[int, int], pygame: Any) -> Any:
        key = (size[0], size[1], self._DEPTH.shadow_alpha)
        cached = self._shadow_cache.get(key)
        if cached is None:
            cached = make_rounded_shadow(size, pygame, style=self._DEPTH)
            self._shadow_cache[key] = cached
        return cached

    def _launch_selected(self, pygame: Any) -> None:
        activities = self._presented_activities
        if not activities or self._active_profile is None:
            return
        self._selected = min(max(0, self._selected), len(activities) - 1)
        manifest = activities[self._selected]
        self._launching_activity_id = manifest.activity_id
        self._launch_animation_started = time.monotonic()
        end = self._launch_animation_started + self._LAUNCH.duration_seconds
        while time.monotonic() < end:
            for event in pygame.event.get():
                if event.type == pygame.QUIT and self.allow_exit:
                    self._launching_activity_id = None
                    return
            screen = pygame.display.get_surface()
            if screen is None:
                break
            self._draw(screen, pygame)
            pygame.display.flip()
            pygame.time.delay(16)
        self._launching_activity_id = None

        # Reuse the authoritative base launch path by temporarily translating
        # the selected item back to its registry index. No package/lifecycle
        # authority is duplicated in this presentation class.
        global_index = next(
            (
                index
                for index, item in enumerate(self._activities)
                if item.activity_id == manifest.activity_id
            ),
            None,
        )
        if global_index is None:
            self._catalogue_error = True
            return
        presented_index = self._selected
        self._selected = global_index
        try:
            super()._launch_selected(pygame)
        finally:
            self._selected = min(
                presented_index,
                max(0, len(self._presented_activities) - 1),
            )
            self._ensure_selected_visible(pygame)


def _launch_status_label(locale: str) -> str:
    """Short launcher-owned feedback in the child's selected UI language."""
    return launch_feedback(locale).badge


_ACTIVITY_TITLE_CACHE: dict[tuple[str, str, str], str] = {}


def _activity_title(activity: ActivityManifest, locale: str = "it") -> str:
    lang = locale.split("-")[0].lower() if locale else "it"
    root = getattr(activity, "root", None)
    cache_key = (activity.activity_id, str(root) if root is not None else "", lang)
    cached = _ACTIVITY_TITLE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    result: str | None = None
    if root is not None:
        try:
            loc_dir = Path(root) / "locales"
            target_file = loc_dir / f"{lang}.json"
            if not target_file.exists():
                target_file = loc_dir / "en.json"
            if target_file.exists():
                with open(target_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    title = (
                        data.get("strings", {}).get("activity.title")
                        or data.get("strings", {}).get(activity.title_key)
                    )
                    if title:
                        result = str(title)
        except Exception:
            pass
    if result is None:
        candidate = activity.title_key.strip()
        if candidate and "." not in candidate:
            result = candidate
        else:
            tail = activity.activity_id.rsplit(".", 1)[-1]
            result = tail.replace("-", " ").replace("_", " ").title()

    _ACTIVITY_TITLE_CACHE[cache_key] = result
    return result


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


def main() -> int:
    args = parse_args()
    # Phase 4 order: minimal shell here; run() owns display, first flip,
    # single-worker preparation and intro-end apply.
    app = GreiaLauncherPresentation(
        windowed=args.windowed,
        allow_exit=args.allow_exit,
        bootstrap=False,
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
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

from .activity_icon import ActivityIconError, package_icon_path
from .spoken_labels import SpokenLabelController
from .catalogue_view import ALL_ACTIVITIES_ID, ActivityCatalogue, _category_title
from .composition import build_launcher_runtime_services, provisional_installed_display_session
from .title_presentation import (
    contain_fit_icon_surface,
    render_activity_card_label,
)
from .main import (
    HitTarget,
    LauncherApplication,
    _activity_sources,
    _development_hal,
)
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

    def __init__(self, *, windowed: bool = False, allow_exit: bool = False):
        super().__init__(windowed=windowed, allow_exit=allow_exit)
        self._configure_parent_package_source()
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
        self._catalogue = ActivityCatalogue.from_activities(self._activities)
        self._category_id = ALL_ACTIVITIES_ID
        self._activity_scroll_start = 0
        self._launching_activity_id: str | None = None
        self._launch_animation_started = 0.0
        self._last_input_monotonic = 0.0
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
        """Compose parent-installed packages into the same launch authority path."""

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
            *_activity_sources(self.paths),
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

        development_hal = None if self._installed_root() else _development_hal()
        runtime_services = build_launcher_runtime_services(
            self.runtime,
            self._activities,
            runtime_policy_path=self.paths.runtime_catalogue,
            permission_policy_path=self.paths.permission_policy,
            storage_policy_path=self.paths.storage_policy,
            history_policy_path=self.paths.history_policy,
            progression_policy_path=self.paths.progression_policy,
            hal=development_hal,
        )
        display_coordinator = (
            provisional_installed_display_session() if self._installed_root() else None
        )
        supervisor = ActivitySupervisor(
            runtime_manager=runtime_services.runtime_manager,
            storage_service=runtime_services.storage_service,
            history_service=runtime_services.history_service,
            display_coordinator=display_coordinator,
        )
        # Publish the pair only after both objects are completely built. The
        # launch path therefore never observes a supervisor/runtime mismatch.
        self.runtime_services = runtime_services
        self.supervisor = supervisor

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

        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        pygame.init()
        pygame.font.init()
        default_size, display_flags = self._initial_display_request(pygame)
        screen = pygame.display.set_mode(default_size, display_flags)
        pygame.display.set_caption(self._display_caption())
        pygame.mouse.set_visible(False)
        self._shell_window_backend.after_window_created(pygame)
        clock = pygame.time.Clock()
        running = True
        last_display_size = screen.get_size()

        # Present the static white Greia frame immediately, then the short
        # one-shot intro and the boot chime (which may only start after the
        # first real frame is on screen). The intro is monotonic-time driven
        # and bounded to <=1.0 s; the chime is fail-silent and asynchronous.
        if not self.windowed:
            try:
                from .boot_chime import play_boot_chime
                from .boot_intro import run_intro

                pygame.display.flip()
                if not self._first_frame_released:
                    self._release_boot_cover()
                run_intro(screen, pygame)
                play_boot_chime()
            except Exception:  # noqa: BLE001 - never fail boot for presentation
                pass

        _needs_redraw = True
        try:
            while running:
                frame_start = time.monotonic()
                self._poll_input_hooks(pygame)
                events = pygame.event.get()
                if events:
                    _needs_redraw = True
                    self._last_input_monotonic = frame_start
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
                        self._synthetic_pointer_active = True
                        _needs_redraw = True
                        if hasattr(event, "pos"):
                            prev_pos = getattr(self, "_pointer_position", None)
                            self._pointer_position = event.pos
                            prev_target = self._target_at(prev_pos) if prev_pos else None
                            new_target = self._target_at(event.pos)
                            if prev_target != new_target:
                                _needs_redraw = True
                            try:
                                now = time.monotonic()
                                prev_sp = self._speakable_for_target(prev_target)
                                new_sp = self._speakable_for_target(new_target)
                                if new_sp is None:
                                    self._spoken_labels.pointer_focus_changed(None, None, now)
                                    self._spoken_labels.clear_pointer_focus()
                                elif prev_sp is None or new_sp[0] != prev_sp[0]:
                                    self._spoken_labels.pointer_focus_changed(
                                        new_sp[0], new_sp[1], now
                                    )
                            except Exception:
                                pass
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

    def _scroll_model(self, pygame: Any) -> ScrollModel:
        columns = self._columns(pygame)
        page_capacity = columns * 2
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
                columns = self._columns(pygame)
                page_cap = columns * 2
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
        columns = self._columns(pygame)
        page_capacity = columns * 2
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
        self._category_id = self._catalogue.nearest_category(category_id)
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
        self._catalogue_error = False
        self._catalogue = ActivityCatalogue.from_activities(discovered)
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

    def _draw_activities(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
    ) -> None:
        width, height = screen.get_size()
        activities = self._presented_activities
        if not activities:
            self._draw_empty(screen, pygame)
            return

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

        def _is_tile(signature: tuple[str, Any] | None) -> bool:
            return signature is not None and signature[0] == "presented_activity"

        # Chrome controls (chips, arrows, badge) own their own hover artwork;
        # repairing only tiles would leave them stale, so defer to full render.
        if not (prev_hover is None or _is_tile(prev_hover)):
            return False
        if not (new_hover is None or _is_tile(new_hover)):
            return False

        rects_by_index = {
            target.value: target.rect.copy()
            for target in self._cached_activities_targets
            if target.action == "presented_activity"
        }

        damage: dict[int, Any] = {}
        for signature in (prev_hover, new_hover):
            if not _is_tile(signature):
                continue
            rect = rects_by_index.get(signature[1])
            if rect is None:
                return False
            damage[int(signature[1])] = rect

        launching_changed = new_tick != prev_tick and self._launching_activity_id
        if launching_changed:
            for target in self._cached_activities_targets:
                if target.action != "presented_activity":
                    continue
                index = int(target.value)
                if 0 <= index < len(activities) and (
                    activities[index].activity_id == self._launching_activity_id
                ):
                    damage[index] = target.rect.copy()
                    break

        if not damage:
            return False

        backdrop_rect = backdrop.get_rect()
        for index, rect in sorted(damage.items()):
            if not 0 <= index < len(activities):
                return False
            # Cover every extent the dynamic states can reach: the tile-surface
            # padding plus hover lift/scale and the bounded launch wiggle/bounce
            # amplitudes. The extra margin stays within inter-tile transparent
            # padding, so neighbours' visible pixels are never touched.
            restore = rect.inflate(34, 40).clip(backdrop_rect)
            cached_surface.blit(backdrop, restore.topleft, restore)

        for index, rect in sorted(damage.items()):
            activity = activities[index]
            state = InteractionVisualState(
                hovered=pointer_active and rect.collidepoint(pointer),
                selected=index == self._selected,
                launching=activity.activity_id == self._launching_activity_id,
            )
            self._draw_activity_tile(cached_surface, rect, activity, state, theme, pygame)
        return True

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
            pygame.draw.rect(screen, (203, 213, 225), shadow_rect, border_radius=12)

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
        rows = 2
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

        if inner_panel is not None:
            pad_x = max(14, inner_panel.width // 45)
            pad_y = max(8, inner_panel.height // 40)
            pagination_reserve = 38 if has_pagination else 0
            avail_w = max(240, inner_panel.width - pad_x * 2)
            avail_h = max(180, inner_panel.height - pad_y * 2 - pagination_reserve)
            # 218 = 210 reference tile +4%: larger cards give two-line labels
            # breathing room while label font sizes stay unchanged.
            tile_size = min(
                218,
                (avail_w - gap * (columns - 1)) // columns,
                (avail_h - gap * (rows - 1)) // rows,
            )
            tile_size = max(120, tile_size)
            total_width = columns * tile_size + (columns - 1) * gap
            total_height = rows * tile_size + (rows - 1) * gap
            origin_x = inner_panel.centerx - total_width // 2
            origin_y = inner_panel.top + pad_y + max(0, (avail_h - total_height) // 2)
        else:
            top = max(116, height // 5)
            pagination_reserve = 38 if has_pagination else 0
            available_h = height - top - 28 - pagination_reserve
            side_reserve = 86
            usable_w = max(240, width - side_reserve)
            tile_size = min(
                218,
                (usable_w - gap * (columns - 1)) // columns,
                (available_h - gap * (rows - 1)) // rows,
            )
            tile_size = max(120, tile_size)
            total_width = columns * tile_size + (columns - 1) * gap
            total_height = rows * tile_size + (rows - 1) * gap
            origin_x = (width - total_width) // 2
            origin_y = top + max(0, (available_h - total_height) // 2)

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
            outline = (
                theme.accent if hovered else _mix(theme.text, theme.panel, 0.72)
            )
            pygame.draw.rect(screen, theme.panel, rect, border_radius=height // 2)
            pygame.draw.rect(
                screen,
                outline,
                rect,
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
                icon_center = (rect.left + 12 + icon_size // 2, rect.centery)
                screen.blit(
                    category_icon,
                    category_icon.get_rect(center=icon_center),
                )
                label_rect = label.get_rect(
                    midleft=(rect.left + 20 + icon_size, rect.centery)
                )
                screen.blit(label, label_rect)
            else:
                screen.blit(
                    category_icon,
                    category_icon.get_rect(center=rect.center),
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
        back_state = InteractionVisualState(hovered=hovered)
        draw_raised_panel(
            screen,
            back_rect,
            pygame,
            fill=theme.panel,
            outline=theme.accent if hovered else _mix(theme.text, theme.panel, 0.72),
            state=back_state,
            style=self._DEPTH,
            cached_shadow=self._shadow_for(back_rect.size, pygame),
        )
        from greia_platform.activity_ui import draw_back_symbol

        arrow_color = theme.accent if hovered else theme.text
        draw_back_symbol(screen, back_rect, arrow_color)
        self._targets.append(
            HitTarget("activity_category_back", ALL_ACTIVITIES_ID, back_rect)
        )

        # Category Switcher Strip
        x = back_rect.right + 14
        error_active = (self._last_result and not self._last_result.succeeded) or self._catalogue_error
        right = screen.get_width() - (76 if error_active else 20)
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

            bg_color = _mix(theme.panel, theme.accent, 0.12) if is_active else theme.panel
            outline_color = theme.accent if (is_active or h_chip) else _mix(theme.text, theme.panel, 0.75)
            outline_width = 3 if is_active else (2 if h_chip else 1)

            pygame.draw.rect(screen, bg_color, chip_rect, border_radius=height // 2)
            pygame.draw.rect(screen, outline_color, chip_rect, width=outline_width, border_radius=height // 2)

            cat_icon = self._category_shadowed_icon(
                col.icon_id or "backpack",
                icon_size,
                shadow_alpha=48 if is_active else 30,
                shadow_offset=2,
                pygame=pygame,
            )

            if chip_width > height:
                icon_center = (chip_rect.left + 12 + icon_size // 2, chip_rect.centery)
                screen.blit(cat_icon, cat_icon.get_rect(center=icon_center))
                label_rect = label.get_rect(midleft=(chip_rect.left + 16 + icon_size, chip_rect.centery))
                screen.blit(label, label_rect)
            else:
                screen.blit(cat_icon, cat_icon.get_rect(center=chip_rect.center))

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
        page_capacity = columns * 2
        total_items = len(activities)
        total_pages = (total_items + page_capacity - 1) // page_capacity
        if total_pages <= 1:
            return

        current_page = window.start // page_capacity
        width, height = screen.get_size()
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)

        # 1. Floating side arrows on left and right edges
        arrow_size = max(44, min(54, height // 11))
        center_y = inner_panel.centery if inner_panel else height // 2 + 20

        if inner_panel:
            left_arrow_rect = pygame.Rect(
                inner_panel.left - arrow_size // 2 - 4,
                center_y - arrow_size // 2,
                arrow_size,
                arrow_size,
            )
            right_arrow_rect = pygame.Rect(
                inner_panel.right - arrow_size // 2 + 4,
                center_y - arrow_size // 2,
                arrow_size,
                arrow_size,
            )
        else:
            left_arrow_rect = pygame.Rect(16, center_y - arrow_size // 2, arrow_size, arrow_size)
            right_arrow_rect = pygame.Rect(width - arrow_size - 16, center_y - arrow_size // 2, arrow_size, arrow_size)

        # Left arrow button
        if window.can_scroll_backward:
            h_left = pointer_active and left_arrow_rect.collidepoint(pointer)
            pygame.draw.rect(screen, theme.panel, left_arrow_rect, border_radius=arrow_size // 2)
            pygame.draw.rect(
                screen,
                theme.accent if h_left else _mix(theme.text, theme.panel, 0.7),
                left_arrow_rect,
                width=3 if h_left else 2,
                border_radius=arrow_size // 2,
            )
            inset = arrow_size // 3
            pts = (
                (left_arrow_rect.right - inset, left_arrow_rect.top + inset - 2),
                (left_arrow_rect.left + inset, left_arrow_rect.centery),
                (left_arrow_rect.right - inset, left_arrow_rect.bottom - inset + 2),
            )
            pygame.draw.lines(
                screen,
                theme.accent if h_left else theme.text,
                False,
                pts,
                width=max(3, arrow_size // 12),
            )
            self._targets.append(
                HitTarget("presented_activity_page_prev", -1, left_arrow_rect)
            )

        # Right arrow button
        if window.can_scroll_forward:
            h_right = pointer_active and right_arrow_rect.collidepoint(pointer)
            pygame.draw.rect(screen, theme.panel, right_arrow_rect, border_radius=arrow_size // 2)
            pygame.draw.rect(
                screen,
                theme.accent if h_right else _mix(theme.text, theme.panel, 0.7),
                right_arrow_rect,
                width=3 if h_right else 2,
                border_radius=arrow_size // 2,
            )
            inset = arrow_size // 3
            pts = (
                (right_arrow_rect.left + inset, right_arrow_rect.top + inset - 2),
                (right_arrow_rect.right - inset, right_arrow_rect.centery),
                (right_arrow_rect.left + inset, right_arrow_rect.bottom - inset + 2),
            )
            pygame.draw.lines(
                screen,
                theme.accent if h_right else theme.text,
                False,
                pts,
                width=max(3, arrow_size // 12),
            )
            self._targets.append(
                HitTarget("presented_activity_page_next", 1, right_arrow_rect)
            )

        # 2. Bottom Pagination Capsule Pill (Page Dots + Counter)
        pill_h = 30
        dot_spacing = 14
        dots_w = (total_pages - 1) * dot_spacing + 24
        label_text = f"{current_page + 1} / {total_pages}"
        font = self._font(14, pygame)
        label_surf = font.render(label_text, True, _mix(theme.text, theme.panel, 0.4))
        pill_w = dots_w + label_surf.get_width() + 28
        pill_x = (inner_panel.centerx if inner_panel else width // 2) - pill_w // 2
        pill_y = (inner_panel.bottom - pill_h - 4) if inner_panel else height - pill_h - 10
        pill_rect = pygame.Rect(pill_x, pill_y, pill_w, pill_h)

        pygame.draw.rect(
            screen,
            _mix(theme.panel, theme.accent, 0.08),
            pill_rect,
            border_radius=pill_h // 2,
        )
        pygame.draw.rect(
            screen,
            _mix(theme.text, theme.panel, 0.8),
            pill_rect,
            width=1,
            border_radius=pill_h // 2,
        )

        dots_start_x = pill_rect.left + 14
        for p in range(total_pages):
            dot_cx = dots_start_x + p * dot_spacing
            dot_cy = pill_rect.centery
            is_active = (p == current_page)
            if is_active:
                dot_r = pygame.Rect(dot_cx - 8, dot_cy - 4, 16, 8)
                pygame.draw.rect(screen, theme.accent, dot_r, border_radius=4)
            else:
                pygame.draw.circle(
                    screen,
                    _mix(theme.text, theme.panel, 0.5),
                    (dot_cx, dot_cy),
                    4,
                )
            dot_hit = pygame.Rect(dot_cx - 8, dot_cy - 12, 16, 24)
            self._targets.append(HitTarget("presented_activity_page", p, dot_hit))

        screen.blit(
            label_surf,
            label_surf.get_rect(
                midleft=(dots_start_x + total_pages * dot_spacing + 6, pill_rect.centery)
            ),
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

    def _draw_activity_tile_content(
        self,
        screen: Any,
        rect: Any,
        activity: ActivityManifest,
        state: InteractionVisualState,
        theme: Any,
        pygame: Any,
    ) -> None:
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
                self._child_display_text("Avvio..."), True, (255, 255, 255)
            )
            screen.blit(launch_text, launch_text.get_rect(center=badge_rect.center))

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

        source = contain_fit_icon_surface(raw_source, size, pygame, safe_padding_ratio=0.03)
        decorated = make_shadowed_icon(
            source,
            pygame,
            shadow_alpha=54,
            shadow_offset=max(2, size // 28),
        )
        self._decorated_icon_cache[key] = decorated
        return decorated

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
    return GreiaLauncherPresentation(
        windowed=args.windowed,
        allow_exit=args.allow_exit,
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
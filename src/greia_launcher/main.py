from __future__ import annotations

import argparse
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from greia_platform.boot_logo import canonical_boot_logo as _canonical_boot_logo
from greia_platform.activities import (
    ActivityManifest,
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
)
from greia_platform.assets import AssetCatalogue, AssetCatalogueError
from greia_platform.pygame_visual_assets import (
    PygameVisualSurfaceCache,
    VisualSurfaceCacheError,
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
from greia_platform.history import HistoryError
from greia_platform.permissions import PermissionDecisionError
from greia_platform.main_credential import MainCredentialStore
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.profiles import (
    ActiveProfileSession,
    ChildProfile,
    ProfileContext,
    ProfileError,
    ProfileStore,
)

from .composition import (
    build_launcher_runtime_services,
    provisional_installed_display_session,
)
from .key_chord import KeyChordTracker
from .lifecycle import ActivityResult
from .parent_panel import ParentSettingsOverlay
from .supervisor import ActivitySupervisor
from .theme import LauncherThemeController
from .visual_assets import load_launcher_assets


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


class LauncherApplication:
    ERROR = (177, 44, 44)
    RESCAN_SECONDS = 2.0

    def __init__(self, *, windowed: bool = False, allow_exit: bool = False):
        self.paths = LauncherPaths.from_environment()
        self.runtime = RuntimeCatalogue.load(self.paths.runtime_catalogue)
        self.registry = ActivityRegistry(
            _activity_sources(self.paths), self.runtime, fail_closed=False
        )
        self._asset_set = load_launcher_assets(
            self.paths.asset_catalogue,
            self.paths.shared_visual_catalogue,
        )
        self.assets = self._asset_set.catalogue
        self.shared_visuals_available = self._asset_set.shared_visuals_available
        self._visual_cache = (
            PygameVisualSurfaceCache.for_pygame(self.assets)
            if self._asset_set.shared_visuals_available
            else None
        )
        self.profile_store = ProfileStore.load(
            self.paths.profile_defaults, self.paths.profiles_dir
        )
        self.profiles = self.profile_store.ensure_initialized()
        self.session = ActiveProfileSession(self.paths.active_profile_status)
        self.session.clear()
        self.selector_theme = LauncherThemeController(
            ThemeStore.load(
                self.paths.theme_defaults,
                self.paths.profiles_dir / ".selector-theme",
            )
        )
        self.theme_controller = self.selector_theme
        self.windowed = windowed
        self._activities = self.registry.discover()
        self._activity_discovery_token = self.registry.discovery_token()
        development_hal = None if self._installed_root() else _development_hal()
        self.runtime_services = build_launcher_runtime_services(
            self.runtime,
            self._activities,
            runtime_policy_path=self.paths.runtime_catalogue,
            permission_policy_path=self.paths.permission_policy,
            storage_policy_path=self.paths.storage_policy,
            history_policy_path=self.paths.history_policy,
            progression_policy_path=self.paths.progression_policy,
            hal=development_hal,
        )
        self._history_recovery_failures: set[str] = set()
        for child in self.profiles:
            try:
                self.runtime_services.history_service.recover_unfinished(
                    self.profile_store.context(child.profile_id)
                )
            except HistoryError:
                self._history_recovery_failures.add(child.profile_id)
        display_coordinator = (
            provisional_installed_display_session() if self._installed_root() else None
        )
        self.supervisor = ActivitySupervisor(
            runtime_manager=self.runtime_services.runtime_manager,
            storage_service=self.runtime_services.storage_service,
            history_service=self.runtime_services.history_service,
            display_coordinator=display_coordinator,
        )
        self.allow_exit = allow_exit
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
        self._parent_panel = ParentSettingsOverlay(MainCredentialStore.from_environment())

    def run(self) -> int:
        import pygame

        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        pygame.init()
        pygame.font.init()
        display_flags = pygame.RESIZABLE if self.windowed else pygame.FULLSCREEN
        default_size = (960, 540) if self.windowed else (0, 0)
        screen = pygame.display.set_mode(default_size, display_flags)
        pygame.display.set_caption("Greia OS")
        pygame.mouse.set_visible(False)
        _set_x11_input_focus(screen, pygame)
        clock = pygame.time.Clock()
        running = True
        last_display_size = screen.get_size()

        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT and self.allow_exit:
                        running = False
                    elif event.type == pygame.TEXTINPUT:
                        if self._mode == "parent_panel":
                            if not self._parent_chord.is_holding:
                                self._parent_panel.handle_text_input(event.text)
                        elif self._mode == "secret":
                            self._handle_secret_text(event.text)
                    elif event.type == pygame.KEYDOWN:
                        if self._mode == "profiles" and self._parent_chord.handle_key_down(
                            event.key, time.monotonic()
                        ):
                            self._mode = "parent_panel"
                            self._parent_panel.open()
                            pygame.event.clear(pygame.TEXTINPUT)
                            pygame.event.clear(pygame.KEYDOWN)
                        else:
                            running = self._handle_key(event.key, pygame)
                    elif event.type == pygame.KEYUP:
                        self._parent_chord.handle_key_up(event.key)
                    elif event.type == pygame.MOUSEMOTION:
                        self._synthetic_pointer_active = True
                        if hasattr(event, "pos"):
                            pygame.mouse.set_pos(event.pos)
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        self._handle_click(event.pos, pygame)
                    elif event.type == pygame.VIDEORESIZE and self.windowed:
                        screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

                current_surface = pygame.display.get_surface()
                if current_surface is not None:
                    screen = current_surface
                if screen.get_size() != last_display_size:
                    last_display_size = screen.get_size()
                    self._icon_cache.clear()
                    self._font_cache.clear()
                    self._profile_name_cache.clear()
                    if self._visual_cache is not None:
                        self._visual_cache.clear()
                if self._mode == "profiles":
                    if self._parent_chord.poll(time.monotonic()):
                        self._mode = "parent_panel"
                        self._parent_panel.open()
                        pygame.event.clear(pygame.TEXTINPUT)
                        pygame.event.clear(pygame.KEYDOWN)
                elif self._mode == "parent_panel":
                    self._parent_panel.drain()
                self._rescan_if_due()
                self._draw(screen, pygame)
                pygame.display.flip()
                if not self._first_frame_released:
                    self._release_boot_cover()
                clock.tick(30)
        finally:
            self.session.clear()
            pygame.key.stop_text_input()
            pygame.quit()
        return 0

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self._mode == "parent_panel":
            running = self._parent_panel.handle_key(key, pygame)
            if not self._parent_panel.is_open:
                self._mode = "profiles"
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
                self._mode = "profiles"
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

    def _logout(self, pygame: Any) -> None:
        pygame.key.stop_text_input()
        self.session.clear()
        self._active_profile = None
        self._pending_profile = None
        self._secret_text = ""
        self._mode = "profiles"
        self.theme_controller = self.selector_theme

    def _launch_selected(self, pygame: Any) -> None:
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
        activity_session = self.supervisor.start(
            manifest, self._active_profile, authority
        )
        self._last_result = activity_session.result
        self._draw_launch_overlay(pygame, text="Starting…")
        pygame.display.flip()
        self._on_frame_presented(pygame.display.get_surface(), pygame)
        _launch_feedback = time.monotonic()
        while self._last_result is None:
            # The child Activity owns the visible surface while running. Keep
            # SDL responsive and show an immediate full-screen launch overlay
            # that visibly blocks any further clicks or keys until ready.
            for event in pygame.event.get():
                pass
            self._last_result = self.supervisor.poll(activity_session)
            if self._last_result is None:
                is_ready = (
                    activity_session.control.ready()
                    if activity_session.control is not None
                    else False
                )
                if not is_ready and time.monotonic() - _launch_feedback > 0.1:
                    self._draw_launch_overlay(pygame, text="Starting…")
                    pygame.display.flip()
                    self._on_frame_presented(pygame.display.get_surface(), pygame)
                    _launch_feedback = time.monotonic()
                time.sleep(0.02)
        pygame.mouse.set_visible(False)
        pygame.event.clear()
        try:
            self.profile_store.consume_avatar_request(profile_id)
            refreshed = self.session.activate(self.profile_store, profile_id)
        except ProfileError:
            self._logout(pygame)
            return
        self._active_profile = refreshed
        self.theme_controller.invalidate()
        self.theme_controller.theme

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
        hint_label = hint.render("Please wait…", True, (130, 120, 100))
        screen.blit(hint_label, hint_label.get_rect(center=(center[0], center[1] + 65)))

    def _installed_root(self) -> bool:
        return self.paths.root == Path("/opt/greia-os")

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
            self._parent_panel.draw(screen, theme, self._typography, pygame, self._load_icon)
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
        if pointer_active and self._cached_profiles_targets:
            for target in self._cached_profiles_targets:
                if target.rect.collidepoint(pointer):
                    hovered_target = (target.action, target.value)
                    break

        cache_key = (
            self._profile_selected,
            tuple(p.profile_id for p in self.profiles),
            hovered_target,
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

        columns = min(4 if width >= 900 else 3 if width >= 700 else 2, len(self.profiles))
        page = calculate_grid_page(
            len(self.profiles), self._profile_selected, columns=columns, max_rows=2
        )
        top = header_size + 12
        available_h = height - top - 18
        side_reserve = 150 if page.page_count > 1 else 30
        gap = max(12, min(22, width // 48))
        usable_w = max(240, width - side_reserve)
        tile_w = min(205, (usable_w - gap * (page.columns - 1)) // page.columns)
        tile_h = min(205, (available_h - gap * max(0, page.rows - 1)) // max(1, page.rows))
        tile_w = max(110, tile_w)
        tile_h = max(120, tile_h)
        total_w = page.columns * tile_w + (page.columns - 1) * gap
        total_h = page.rows * tile_h + max(0, page.rows - 1) * gap
        origin_x = (width - total_w) // 2
        origin_y = top + max(0, (available_h - total_h) // 2)

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
            pygame.draw.rect(screen, theme.panel, rect, border_radius=26)
            pygame.draw.rect(
                screen,
                theme.accent if selected else _mix(theme.text, theme.panel, 0.72),
                rect,
                width=8 if selected else 3,
                border_radius=26,
            )
            icon_size = min(int(rect.width * 0.58), int(rect.height * 0.58))
            icon = self._load_icon(profile.avatar_id, icon_size, pygame)
            screen.blit(icon, icon.get_rect(center=(rect.centerx, rect.top + rect.height * 0.40)))
            font_size = max(23, min(38, rect.height // 6))
            max_name_width = rect.width - 18
            name = self._profile_name_surface(
                profile.display_name, font_size, max_name_width, theme.text, pygame
            )
            screen.blit(name, name.get_rect(center=(rect.centerx, rect.bottom - rect.height * 0.15)))
            if profile.has_secret:
                lock = self._load_icon("yellow_star", max(26, rect.width // 7), pygame)
                screen.blit(lock, lock.get_rect(topright=(rect.right - 8, rect.top + 8)))
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
        cancel = pygame.Rect(width // 2 - button_size - gap, entry.bottom + 22, button_size, button_size)
        erase = pygame.Rect(width // 2 - button_size // 2, entry.bottom + 22, button_size, button_size)
        accept = pygame.Rect(width // 2 + gap, entry.bottom + 22, button_size, button_size)
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
            210,
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
        page: GridPage,
        *,
        previous_action: str,
        next_action: str,
        total: int,
    ) -> None:
        if page.page_count <= 1:
            return
        size = max(54, min(72, screen.get_height() // 8))
        center_y = screen.get_height() // 2 + 24
        controls = (
            ("previous", pygame.Rect(14, center_y - size // 2, size, size), previous_action),
            ("next", pygame.Rect(screen.get_width() - size - 14, center_y - size // 2, size, size), next_action),
        )
        for direction, rect, action in controls:
            enabled = page.page_index > 0 if direction == "previous" else page.page_index + 1 < page.page_count
            if not enabled:
                continue
            pygame.draw.rect(screen, theme.panel, rect, border_radius=20)
            pygame.draw.rect(screen, theme.accent, rect, width=5, border_radius=20)
            inset = max(13, rect.width // 4)
            if direction == "previous":
                points = ((rect.right - inset, rect.top + inset), (rect.left + inset, rect.centery), (rect.right - inset, rect.bottom - inset))
                target_index = max(0, page.start - page.page_size)
            else:
                points = ((rect.left + inset, rect.top + inset), (rect.right - inset, rect.centery), (rect.left + inset, rect.bottom - inset))
                target_index = min(total - 1, page.stop)
            pygame.draw.polygon(screen, theme.text, points)
            self._targets.append(HitTarget(action, target_index, rect))

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
        size = max(34, min(54, screen.get_height() // 12))
        icon = self._load_icon("yellow_star", size, pygame)
        x, y = pygame.mouse.get_pos()
        screen.blit(icon, icon.get_rect(center=(x, y)))

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


def _optional_absolute_path_from_environment(name: str) -> Path | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    path = Path(value.strip())
    if not path.is_absolute():
        raise ActivityValidationError(f"{name} must be an absolute path")
    return path.resolve()


def _activity_sources(paths: LauncherPaths) -> tuple[ActivitySource, ...]:
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


def _set_x11_input_focus(screen: Any, pygame: Any) -> None:
    """Give the fullscreen window X input focus when no window manager runs.

    Greia boots Xorg directly with no WM, so keyboard events go nowhere unless
    the launcher window is focused. This sets X input focus to the SDL window.
    """
    import ctypes
    import ctypes.util

    try:
        if os.environ.get("SDL_VIDEODRIVER", "x11") != "x11":
            return
        info = pygame.display.get_wm_info()
        raw_window = info.get("window", 0)
        if not isinstance(raw_window, int) or not raw_window:
            return
        x11_lib = ctypes.util.find_library("X11")
        if not x11_lib:
            return
        x11 = ctypes.CDLL(x11_lib)
        display = x11.XOpenDisplay(None)
        if not display:
            return
        revert_to = 1  # RevertToParent
        current = ctypes.c_ulong()
        revert = ctypes.c_int()
        x11.XGetInputFocus(display, ctypes.byref(current), ctypes.byref(revert))
        if current.value != raw_window:
            x11.XSetInputFocus(display, raw_window, revert_to, 0)
        x11.XCloseDisplay(display)
    except Exception:
        return


def main() -> int:
    args = parse_args()
    return LauncherApplication(windowed=args.windowed, allow_exit=args.allow_exit).run()


if __name__ == "__main__":
    raise SystemExit(main())

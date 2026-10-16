"""Installed Greia child shell composition.

This layer keeps presentation policy out of the lifecycle core: the richer
launcher still owns catalogue rendering, while this installed composition adds
profile visual preferences to launcher typography and to the read-only launch
context supplied to Activities.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from functools import partial
from pathlib import Path
import time
from typing import Any

from greia_platform.achievements import ProfileAchievementService
from greia_platform.audio import AudioService, MicrophoneProcessingMode
from greia_platform.boot_markers import emit_boot_marker
from greia_platform.customization import CustomizationError, ThemeStore
from greia_platform.hal import GreiaHAL
from greia_platform.profile_presentation import ProfilePresentationStore
from greia_platform.theme_snapshot import ThemeSnapshotError, encode_theme_snapshot
from greia_platform.ui_preferences import UiPreferencesStore
from greia_platform.usage_limits import UsageLimitError, UsageLimitService, UsageLimitStore

from .activity_policy_presentation import PolicyEnforcedAdaptiveActivityDiscoveryMixin
from .achievement_presentation import AchievementLibraryMixin
from .catalogue_view import ALL_ACTIVITIES_ID
from .collection_home_presentation import CollectionFirstHomeMixin
from .collection_page_presentation import CollectionPageMixin
from .composition import (
    build_launcher_runtime_services,
    provisional_installed_display_session,
    provisional_installed_system_chrome,
)
from .display_session import DisplaySessionCoordinator
from .event_broker import ActivityEventBroker
from .feedback_presentation import SharedUiFeedbackMixin
from .launch_timing import ready_timeout_for
from .main import _development_hal, configure_launcher_logging
from .navigation_chrome_presentation import SharedUiNavigationChromeMixin
from .presentation import GreiaLauncherPresentation, parse_args
from .profile_chrome_presentation import SharedUiProfileChromeMixin
from .runtime_adapter import RuntimeLaunchAdapter
from .shared_ui_presentation import (
    SharedUiActivityCardMixin,
    SharedUiCategoryButtonMixin,
    SharedUiShellPanelMixin,
)
from .supervisor import ActivitySupervisor
from .system_chrome import SystemChromeCoordinator
from .trusted_chrome_supervisor import TrustedChromeActivitySupervisor
from .usage_limit_lifecycle import ActivityUsageLimitGuard
from .usage_limit_presentation import home_usage_limit_presentation


class ProfileVisualActivitySupervisor(TrustedChromeActivitySupervisor):
    """Add profile visuals/audio on top of trusted Activity lifecycle chrome."""

    def __init__(
        self,
        *args: object,
        audio_service: AudioService | None = None,
        achievement_service: ProfileAchievementService | None = None,
        **kwargs: object,
    ) -> None:
        if achievement_service is not None and "event_broker_factory" not in kwargs:
            kwargs["event_broker_factory"] = partial(
                ActivityEventBroker.start,
                achievement_service=achievement_service,
            )
        super().__init__(*args, **kwargs)
        self._audio_service = audio_service

    def _sanitized_environment(
        self,
        manifest,
        profile,
        authority,
        session_id: str,
        *,
        sandboxed: bool = False,
        storage_broker=None,
        event_broker=None,
        runtime_environment: tuple[tuple[str, str], ...] = (),
        lifecycle_environment: tuple[tuple[str, str], ...] = (),
        display_environment: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        environment = ActivitySupervisor._sanitized_environment(
            manifest,
            profile,
            authority,
            session_id,
            sandboxed=sandboxed,
            storage_broker=storage_broker,
            event_broker=event_broker,
            runtime_environment=runtime_environment,
            lifecycle_environment=lifecycle_environment,
            display_environment=display_environment,
        )

        preferences = UiPreferencesStore(profile.customization_dir).read()
        environment["GREIA_INTERFACE_SIZE"] = preferences.interface_size.value

        presentation = ProfilePresentationStore(profile.customization_dir).read()
        environment["GREIA_PROFILE_PRESENTATION"] = presentation.presentation.value
        environment["GREIA_PROFILE_GRAMMATICAL_GENDER"] = (
            presentation.grammatical_gender.value
        )

        root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")).resolve()
        defaults = root / "runtime" / "theme-defaults.toml"
        try:
            theme = ThemeStore.load(defaults, profile.customization_dir).resolve()
            environment["GREIA_THEME_SNAPSHOT"] = encode_theme_snapshot(theme)
        except (OSError, ValueError, CustomizationError, ThemeSnapshotError):
            environment.pop("GREIA_THEME_SNAPSHOT", None)

        if self._audio_service is not None and authority.has_capability("audio.basic"):
            for name, value in self._audio_service.session_environment():
                if name in environment:
                    raise ValueError(f"audio session environment collides with {name!r}")
                environment[name] = value
            route = self._audio_service.route()
            if route.mode is not MicrophoneProcessingMode.OFF:
                # SDL/pygame cannot open arbitrary ALSA PCM names, so routed
                # launches also receive a Greia-composed ALSA view in which
                # the SDL-enumerated capture device carries the selected
                # route (ADR 0031). Processing-off launches stay raw.
                environment["ALSA_CONFIG_PATH"] = str(
                    root / "runtime" / "alsa" / "greia-activity-capture.conf"
                )
        return environment


class GreiaChildShell(
    PolicyEnforcedAdaptiveActivityDiscoveryMixin,
    AchievementLibraryMixin,
    CollectionFirstHomeMixin,
    CollectionPageMixin,
    SharedUiNavigationChromeMixin,
    SharedUiFeedbackMixin,
    SharedUiProfileChromeMixin,
    SharedUiCategoryButtonMixin,
    SharedUiShellPanelMixin,
    SharedUiActivityCardMixin,
    GreiaLauncherPresentation,
):
    """Production child shell with profile-aware visual presentation context.

    Synthetic/development variants override only the typed variation hooks
    below. The authoritative service/supervisor rebuild sequence remains here.
    Shared visual artwork is presentation-only and preserves the base launcher
    as a fail-soft fallback.
    """

    # My Creations is a trusted Shell destination, not a package/Activity.
    # The existing Collection Home renders semantic destinations without
    # requiring an ActivityManifest or a parallel launcher hierarchy.
    CREATIONS_COLLECTION_ID = "my_creations"

    def _home_collections(self) -> tuple[Any, ...]:
        from greia_platform.ui_core import Collection

        collections = super()._home_collections()
        if getattr(self, "_active_profile", None) is None:
            return collections
        # A child sees Create and the place to find their saved work together.
        # Use a different canonical picture from Create's palette so a
        # prereader can recognize making versus keeping without text.
        creations = Collection(
            self.CREATIONS_COLLECTION_ID, (), icon_id="backpack",
        )
        create_index = next(
            (index for index, collection in enumerate(collections)
             if collection.collection_id == "create"),
            None,
        )
        position = create_index + 1 if create_index is not None else 0
        return (*collections[:position], creations, *collections[position:])

    def _set_category(self, category_id: str) -> None:
        if category_id == self.CREATIONS_COLLECTION_ID:
            self._open_creations()
            return
        super()._set_category(category_id)

    def _open_creations(self) -> None:
        """Open active profile's trusted library after selecting Home portal."""
        if self._active_profile is None:
            return
        import sqlite3

        from greia_platform.creation_audio_pygame import PygameRecordingPreview
        from greia_platform.creation_gallery import CreationsGalleryController
        from greia_platform.creation_gallery_screen import CreationsGalleryScreen
        from greia_platform.creations import CreationLibrary, CreationLibraryError
        from greia_platform.profiles import ProfileError

        try:
            library = CreationLibrary(
                self._active_profile.creations_dir,
                volume_budget=getattr(
                    getattr(self, "runtime_services", None), "volume_budget", None
                ),
            )
            controller = CreationsGalleryController(
                library, audio_player=PygameRecordingPreview(),
            )
            from .profile_chrome_presentation import greeter_character_for

            self._creations_screen = CreationsGalleryScreen(
                controller, typography=self._typography, locale=self._active_locale,
                visual_cache=getattr(self, "_visual_cache", None),
                backdrop=self._creations_backdrop,
                greeter=greeter_character_for(self._active_profile.profile.avatar_id),
                text_transform=self._child_display_text,
            )
        except (OSError, ValueError, ProfileError, CreationLibraryError, sqlite3.Error):
            self._catalogue_error = True
            return
        self._mode = "creations"
        self._targets.clear()

    def _creations_backdrop(self, size: tuple[int, int]) -> Any | None:
        """Opaque storybook scene for My Creations (the Shell's cached backdrop)."""

        import pygame

        cached = getattr(self, "_creations_backdrop_surface", None)
        if cached is not None and cached.get_size() == size:
            return cached
        if getattr(self, "_visual_cache", None) is None:
            return None
        surface = pygame.Surface(size).convert()
        theme = self.theme_controller.theme
        surface.fill(theme.background)
        self._draw_shell_scene_backdrop(surface, pygame, theme=theme)
        if getattr(self, "_shared_scene_disabled", False):
            return None
        # One retained surface, replaced only when the display size changes.
        self._creations_backdrop_surface = surface
        return surface

    def _close_creations(self) -> None:
        screen = getattr(self, "_creations_screen", None)
        if screen is not None:
            screen.on_exit()
        self._creations_screen = None
        self._creations_backdrop_surface = None
        if self._mode == "creations":
            self._mode = "activities"
            super()._set_category(ALL_ACTIVITIES_ID)
            self._cached_activities_key = None

    def _draw(self, screen: Any, pygame: Any) -> None:
        if self._mode != "creations":
            super()._draw(screen, pygame)
            return
        self._targets.clear()
        viewer = getattr(self, "_creations_screen", None)
        if viewer is None:
            self._close_creations()
            return
        viewer.draw(screen)
        self._draw_pointer(screen, pygame)

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self._mode != "creations":
            return super()._handle_key(key, pygame)
        from greia_platform.ui_core import UiEventResult

        viewer = getattr(self, "_creations_screen", None)
        if viewer is None:
            self._close_creations()
            return True
        result = viewer.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))
        if result is UiEventResult.REQUEST_CLOSE:
            self._close_creations()
        return True

    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        if self._mode != "creations":
            super()._handle_click(position, pygame)
            return
        from greia_platform.ui_core import UiEventResult

        viewer = getattr(self, "_creations_screen", None)
        if viewer is None:
            self._close_creations()
            return
        result = viewer.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=position)
        )
        if result is UiEventResult.REQUEST_CLOSE:
            self._close_creations()

    def _rescan_profiles(self) -> bool:
        """Revoke a gallery if Parent removes/changes its active child profile."""
        was_viewing = self._mode == "creations"
        changed = super()._rescan_profiles()
        if was_viewing and self._mode != "creations":
            self._close_creations()
        return changed

    def _logout(self, pygame: Any) -> None:
        # Profile exit must release every preview channel and old gallery view.
        self._close_creations()
        super()._logout(pygame)

    def _runtime_hal(self) -> GreiaHAL | None:
        return None if self._installed_root() else _development_hal()

    def _runtime_adapters(
        self,
    ) -> Sequence[RuntimeLaunchAdapter] | Mapping[str, RuntimeLaunchAdapter] | None:
        return None

    def _display_session_coordinator(self) -> DisplaySessionCoordinator | None:
        return provisional_installed_display_session() if self._installed_root() else None

    def _system_chrome_coordinator(self) -> SystemChromeCoordinator | None:
        return provisional_installed_system_chrome() if self._installed_root() else None

    def _build_usage_limit_service(self) -> UsageLimitService:
        """Construct a usage limit service without mutating live shell state."""
        return UsageLimitService(
            UsageLimitStore(self.paths.profiles_dir / "usage-limits.json")
        )

    def _usage_limit_service(self) -> UsageLimitService:
        service = getattr(self, "_usage_limits", None)
        if service is None:
            # Parent API and Shell deliberately open the same inter-process-safe
            # ledger below the managed profile root. There is no second cache or
            # launcher-private screen-time authority.
            service = self._build_usage_limit_service()
            self._usage_limits = service
        return service

    def _build_bootstrap_supervisor(self, runtime_services: Any) -> Any:
        """Build the profile-visual supervisor bound to prepared services.

        Pure construction for the bootstrap coordinator: file-backed Audio
        settings and usage-limit ledger reads only, no Pygame, no live
        launcher mutation. The controller set is read by reference and never
        mutated here.
        """

        root = Path(os.environ.get("GREIA_OS_ROOT", "/opt/greia-os")).resolve()
        audio_service = AudioService.load(
            root / "runtime" / "audio-settings.toml",
            Path(
                os.environ.get(
                    "GREIA_SYSTEM_SETTINGS_DIR",
                    "/var/lib/greia-system-settings",
                )
            ),
        )
        return ProfileVisualActivitySupervisor(
            runtime_manager=runtime_services.runtime_manager,
            storage_service=runtime_services.storage_service,
            history_service=runtime_services.history_service,
            achievement_service=runtime_services.achievement_service,
            display_coordinator=self._display_session_coordinator(),
            system_chrome_coordinator=self._system_chrome_coordinator(),
            audio_service=audio_service,
            usage_limit_guard=ActivityUsageLimitGuard(self._build_usage_limit_service()),
            ready_timeout_seconds=ready_timeout_for(runtime_services),
            controller_set=(
                self._shell_input.controllers
                if getattr(self, "_shell_input", None) is not None
                else None
            ),
        )

    def _rebuild_runtime_services(self) -> None:
        super()._rebuild_runtime_services()

    def _launch_selected(self, pygame: Any) -> None:
        """Run one Activity lifecycle, with a friendly exhausted-budget pre-check.

        The usage-limit supervisor remains the authoritative enforcement point:
        it accounts real Activity time and closes races where the budget changes
        between this presentation check and process creation. This early read is
        only child-facing UX. If the already-authoritative ledger says the day is
        exhausted, stay on Greia Home rather than flashing ``Starting…`` and a
        generic launch error. If the read itself fails, delegate to the normal
        launch path so presentation code never becomes a fail-open authority.
        """

        profile_context = getattr(self, "_active_profile", None)
        if profile_context is not None:
            try:
                status = self._usage_limit_service().status(
                    profile_context.profile.profile_id
                )
            except (UsageLimitError, OSError, TypeError, ValueError):
                status = None
            if status is not None and status.exhausted:
                self._last_result = None
                self._catalogue_error = False
                self._home_collection_selected = 0
                self._set_category(ALL_ACTIVITIES_ID)
                self._cached_activities_key = None
                return

        super()._launch_selected(pygame)
        # Returning from an Activity changes today's usage status. Rebuild Home
        # once on return rather than turning the passive readout into a ticking
        # idle timer.
        self._cached_activities_key = None
        # The no-window-manager Legacy-X session can leave focus on the child
        # window that just disappeared. Keep the backend-specific repair behind
        # the trusted Shell-window seam and invoke it once per completed return.
        self._shell_window_backend.after_activity_return(pygame)

    def _render_collection_home(self, screen: Any, theme: Any, pygame: Any) -> None:
        super()._render_collection_home(screen, theme, pygame)
        self._draw_home_usage_limit(screen, theme, pygame)

    def _draw_home_usage_limit(self, screen: Any, theme: Any, pygame: Any) -> None:
        profile_context = getattr(self, "_active_profile", None)
        if profile_context is None:
            return
        try:
            status = self._usage_limit_service().status(
                profile_context.profile.profile_id
            )
        except (UsageLimitError, OSError, TypeError, ValueError):
            # Enforcement remains fail-closed at launch. A readout failure must
            # not crash or continuously redraw the otherwise usable Home.
            return
        presentation = home_usage_limit_presentation(
            status,
            locale=getattr(self, "_active_locale", "en"),
            uppercase=profile_context.profile.uppercase_text,
        )
        if not presentation.visible:
            return

        from greia_platform.typography import FontRole

        width, height = screen.get_size()
        font_size = max(15, min(21, height // 30))
        label = self._typography.font(FontRole.CONTROL, font_size).render(
            presentation.text,
            True,
            theme.text,
        )
        clock_diameter = max(24, min(32, height // 18))
        horizontal_padding = 12
        gap = 8
        pill_width = min(
            max(120, width - 120),
            clock_diameter + gap + label.get_width() + horizontal_padding * 2,
        )
        pill_height = max(clock_diameter + 10, label.get_height() + 14)
        pill = pygame.Rect(
            max(8, width - pill_width - 14),
            12,
            pill_width,
            pill_height,
        )
        pygame.draw.rect(screen, theme.panel, pill, border_radius=pill_height // 2)
        pygame.draw.rect(
            screen,
            theme.accent if presentation.exhausted else theme.text,
            pill,
            width=2,
            border_radius=pill_height // 2,
        )

        clock_center = (
            pill.left + horizontal_padding + clock_diameter // 2,
            pill.centery,
        )
        radius = clock_diameter // 2
        pygame.draw.circle(screen, theme.text, clock_center, radius, width=2)
        pygame.draw.line(
            screen,
            theme.text,
            clock_center,
            (clock_center[0], clock_center[1] - max(4, radius // 2)),
            width=2,
        )
        pygame.draw.line(
            screen,
            theme.text,
            clock_center,
            (clock_center[0] + max(4, radius // 2), clock_center[1]),
            width=2,
        )
        text_left = clock_center[0] + radius + gap
        available_width = max(1, pill.right - horizontal_padding - text_left)
        if label.get_width() > available_width:
            label = pygame.transform.smoothscale(
                label,
                (
                    available_width,
                    max(
                        1,
                        round(
                            label.get_height()
                            * available_width
                            / label.get_width()
                        ),
                    ),
                ),
            )
        screen.blit(label, label.get_rect(midleft=(text_left, pill.centery)))

    def _font(self, size: int, pygame: Any) -> Any:
        effective = max(
            12,
            min(160, int(round(size * self.theme_controller.interface_scale))),
        )
        cached = self._font_cache.get(effective)
        if cached is None:
            from greia_platform.typography import FontRole

            cached = self._typography.font(FontRole.BODY, effective)
            self._font_cache[effective] = cached
        return cached

    def _draw_launch_overlay(self, pygame: Any, *, text: str) -> None:
        if self._draw_shared_launch_overlay(pygame, text=text):
            return

        from greia_platform.typography import FontRole

        screen = pygame.display.get_surface()
        if screen is None:
            return
        width, height = screen.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((255, 250, 240, 245))
        screen.blit(overlay, (0, 0))
        center = screen.get_rect().center
        panel = pygame.Rect(
            0,
            0,
            min(360, max(180, width - 60)),
            min(170, max(120, height - 40)),
        )
        panel.center = center
        pygame.draw.rect(screen, (247, 235, 203), panel, border_radius=24)
        pygame.draw.rect(screen, (61, 44, 31), panel, width=2, border_radius=24)
        now = time.monotonic()
        for index in range(3):
            phase = (now * 2.0 + index * 0.8) % 2.0
            radius = int(5 + 5 * (1.0 - abs(phase - 1.0)))
            dot_center = (center[0] - 30 + index * 30, center[1] - 40)
            pygame.draw.circle(screen, (255, 194, 52), dot_center, radius)

        scale = self.theme_controller.interface_scale
        control_size = max(18, min(160, int(round(32 * scale))))
        body_size = max(18, min(160, int(round(20 * scale))))
        label = self._typography.font(FontRole.CONTROL, control_size).render(
            self._child_display_text(text), True, (61, 44, 31)
        )
        screen.blit(label, label.get_rect(center=(center[0], center[1] + 25)))
        from .launch_feedback import launch_feedback

        hint_label = self._typography.font(FontRole.BODY, body_size).render(
            self._child_display_text(launch_feedback(self._active_locale).wait),
            True,
            (130, 120, 100),
        )
        screen.blit(hint_label, hint_label.get_rect(center=(center[0], center[1] + 65)))


def main() -> int:
    emit_boot_marker("launcher_python_enter")
    configure_launcher_logging()
    args = parse_args()
    # Phase 4 order: minimal shell here; run() owns display, first flip,
    # single-worker preparation and intro-end apply.
    return GreiaChildShell(
        windowed=args.windowed,
        allow_exit=args.allow_exit,
        bootstrap=False,
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())

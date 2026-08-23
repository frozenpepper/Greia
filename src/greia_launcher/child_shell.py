"""Installed Greia child shell composition.

This layer keeps presentation policy out of the lifecycle core: the richer
launcher still owns catalogue rendering, while this installed composition adds
profile visual preferences to launcher typography and to the read-only launch
context supplied to Activities.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
import time
from typing import Any

from greia_platform.audio import AudioService
from greia_platform.customization import CustomizationError, ThemeStore
from greia_platform.hal import GreiaHAL
from greia_platform.profile_presentation import ProfilePresentationStore
from greia_platform.theme_snapshot import ThemeSnapshotError, encode_theme_snapshot
from greia_platform.ui_preferences import UiPreferencesStore

from .adaptive_discovery_presentation import AdaptiveActivityDiscoveryMixin
from .achievement_presentation import AchievementLibraryMixin
from .collection_home_presentation import CollectionFirstHomeMixin
from .composition import build_launcher_runtime_services, provisional_installed_display_session
from .display_session import DisplaySessionCoordinator
from .feedback_presentation import SharedUiFeedbackMixin
from .main import _development_hal
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


class ProfileVisualActivitySupervisor(ActivitySupervisor):
    """Add safe profile presentation and platform-selected microphone routing."""

    def __init__(
        self,
        *args: object,
        audio_service: AudioService | None = None,
        **kwargs: object,
    ) -> None:
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
        return environment


class GreiaChildShell(
    AdaptiveActivityDiscoveryMixin,
    AchievementLibraryMixin,
    CollectionFirstHomeMixin,
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

    def _runtime_hal(self) -> GreiaHAL | None:
        return None if self._installed_root() else _development_hal()

    def _runtime_adapters(
        self,
    ) -> Sequence[RuntimeLaunchAdapter] | Mapping[str, RuntimeLaunchAdapter] | None:
        return None

    def _display_session_coordinator(self) -> DisplaySessionCoordinator | None:
        return provisional_installed_display_session() if self._installed_root() else None

    def _rebuild_runtime_services(self) -> None:
        runtime_services = build_launcher_runtime_services(
            self.runtime,
            self._activities,
            runtime_policy_path=self.paths.runtime_catalogue,
            permission_policy_path=self.paths.permission_policy,
            storage_policy_path=self.paths.storage_policy,
            history_policy_path=self.paths.history_policy,
            progression_policy_path=self.paths.progression_policy,
            hal=self._runtime_hal(),
            runtime_adapters=self._runtime_adapters(),
        )
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
        supervisor = ProfileVisualActivitySupervisor(
            runtime_manager=runtime_services.runtime_manager,
            storage_service=runtime_services.storage_service,
            history_service=runtime_services.history_service,
            display_coordinator=self._display_session_coordinator(),
            audio_service=audio_service,
        )
        self.runtime_services = runtime_services
        self.supervisor = supervisor

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
            text, True, (61, 44, 31)
        )
        screen.blit(label, label.get_rect(center=(center[0], center[1] + 25)))
        hint_label = self._typography.font(FontRole.BODY, body_size).render(
            "Please wait…", True, (130, 120, 100)
        )
        screen.blit(hint_label, hint_label.get_rect(center=(center[0], center[1] + 65)))


def main() -> int:
    args = parse_args()
    return GreiaChildShell(
        windowed=args.windowed,
        allow_exit=args.allow_exit,
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())

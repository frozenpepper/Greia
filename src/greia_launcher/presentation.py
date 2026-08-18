from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Any

from greia_platform.activities import (
    ActivityManifest,
    ActivityRegistry,
    ActivityValidationError,
)
from greia_platform.pygame_effects import (
    PygameDepthStyle,
    draw_raised_panel,
    make_rounded_shadow,
    make_shadowed_icon,
)
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.ui_core import BoundedCache
from greia_platform.ui_motion import HoverMotion, InteractionVisualState, LaunchMotion
from greia_platform.ui_scroll import ScrollModel

from .activity_icon import ActivityIconError, package_icon_path
from .catalogue_view import ALL_ACTIVITIES_ID, ActivityCatalogue
from .composition import build_launcher_runtime_services, provisional_installed_display_session
from .main import (
    HitTarget,
    LauncherApplication,
    _activity_sources,
    _development_hal,
    _set_x11_input_focus,
)
from .supervisor import ActivitySupervisor


PARENT_ACTIVITY_SOURCE_ID = "greia-parent-package-service"


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
        self._catalogue = ActivityCatalogue.from_activities(self._activities)
        self._category_id = ALL_ACTIVITIES_ID
        self._activity_scroll_start = 0
        self._launching_activity_id: str | None = None
        self._launch_animation_started = 0.0

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
            # The immutable package service should make this rare, but boot must
            # stay fail-soft if package storage is externally damaged. Keep the
            # already validated built-in/developer registry from the base class.
            self._catalogue_error = True
            return

        self.registry = registry
        self._activities = discovered
        self._activity_discovery_token = registry.discovery_token()
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
        display_coordinator = (
            provisional_installed_display_session() if self._installed_root() else None
        )
        self.supervisor = ActivitySupervisor(
            runtime_manager=self.runtime_services.runtime_manager,
            storage_service=self.runtime_services.storage_service,
            history_service=self.runtime_services.history_service,
            display_coordinator=display_coordinator,
        )

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
                    elif event.type == pygame.TEXTINPUT and self._mode == "secret":
                        self._handle_secret_text(event.text)
                    elif event.type == pygame.KEYDOWN:
                        running = self._handle_key(event.key, pygame)
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        self._handle_click(event.pos, pygame)
                    elif event.type == pygame.MOUSEWHEEL and self._mode == "activities":
                        self._scroll_activity_rows(-event.y, pygame)
                    elif event.type == pygame.VIDEORESIZE and self.windowed:
                        screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

                current_surface = pygame.display.get_surface()
                if current_surface is not None:
                    screen = current_surface
                if screen.get_size() != last_display_size:
                    last_display_size = screen.get_size()
                    self._icon_cache.clear()
                    self._font_cache.clear()
                    self._shadow_cache.clear()
                    self._decorated_icon_cache.clear()
                    self._activity_scroll_start = 0
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
        return ScrollModel(capacity=columns * 2, step=columns)

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self._mode != "activities":
            return super()._handle_key(key, pygame)
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
        elif key in {pygame.K_RETURN, pygame.K_SPACE}:
            self._launch_selected(pygame)
        elif key == pygame.K_ESCAPE:
            self._logout(pygame)
        elif self.allow_exit and key == pygame.K_q:
            return False
        return True

    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        for target in reversed(self._targets):
            if not target.rect.collidepoint(position):
                continue
            if target.action == "activity_category":
                self._set_category(str(target.value))
                return
            if target.action == "presented_activity_select":
                self._selected = int(target.value)
                self._ensure_selected_visible(pygame)
                return
            if target.action == "presented_activity":
                self._selected = int(target.value)
                self._ensure_selected_visible(pygame)
                self._launch_selected(pygame)
                return
        super()._handle_click(position, pygame)

    def _scroll_activity_rows(self, direction: int, pygame: Any) -> None:
        activities = self._presented_activities
        if not activities or direction == 0:
            return
        columns = self._columns(pygame)
        delta = columns * (-1 if direction < 0 else 1)
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

    def _rescan_activities(self) -> None:
        token = self.registry.discovery_token()
        if token == self._activity_discovery_token:
            return
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
            self._catalogue_error = True
            return
        self._catalogue_error = False
        self._activities = discovered
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

    def _draw_activities(self, screen: Any, theme: Any, pygame: Any) -> None:
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
                    hovered=badge.collidepoint(pygame.mouse.get_pos())
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
        scroll = ScrollModel(capacity=columns * 2, step=columns)
        window = scroll.window(
            len(activities), self._selected, self._activity_scroll_start
        )
        self._activity_scroll_start = window.start
        visible_count = window.stop - window.start
        rows = max(1, (visible_count + columns - 1) // columns)
        top = max(116, height // 5)
        available_h = height - top - 28
        side_reserve = (
            86 if window.can_scroll_backward or window.can_scroll_forward else 30
        )
        gap = max(16, min(25, width // 42))
        usable_w = max(240, width - side_reserve)
        tile_size = min(
            205,
            (usable_w - gap * (columns - 1)) // columns,
            (available_h - gap * max(0, rows - 1)) // rows,
        )
        tile_size = max(115, tile_size)
        total_width = columns * tile_size + (columns - 1) * gap
        total_height = rows * tile_size + max(0, rows - 1) * gap
        origin_x = (width - total_width) // 2
        origin_y = top + max(0, (available_h - total_height) // 2)

        pointer = pygame.mouse.get_pos()
        pointer_active = pygame.mouse.get_focused()
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

        self._draw_scroll_controls(screen, theme, pygame, window, columns)
        if (self._last_result and not self._last_result.succeeded) or self._catalogue_error:
            self._draw_error_badge(screen, pygame)

    def _draw_category_bar(self, screen: Any, theme: Any, pygame: Any) -> None:
        if not self._catalogue.category_ids:
            return
        left = 112 if self._active_profile is not None else 20
        right = screen.get_width() - 20
        gap = 9
        height = max(42, min(52, screen.get_height() // 11))
        x = left
        pointer = pygame.mouse.get_pos()
        for collection in self._catalogue.collections:
            label_text = collection.title or collection.collection_id
            font = self._font(max(18, min(22, height // 2)), pygame)
            label = font.render(label_text, True, theme.text)
            width = min(170, max(72, label.get_width() + 28))
            if x + width > right:
                break
            rect = pygame.Rect(x, 18, width, height)
            selected = collection.collection_id == self._category_id
            hovered = rect.collidepoint(pointer) and pygame.mouse.get_focused()
            fill = (
                theme.panel
                if not selected
                else _mix(theme.panel, theme.accent, 0.16)
            )
            outline = (
                theme.accent
                if selected or hovered
                else _mix(theme.text, theme.panel, 0.72)
            )
            pygame.draw.rect(screen, fill, rect, border_radius=height // 2)
            pygame.draw.rect(
                screen,
                outline,
                rect,
                width=4 if selected else 2,
                border_radius=height // 2,
            )
            screen.blit(label, label.get_rect(center=rect.center))
            self._targets.append(
                HitTarget("activity_category", collection.collection_id, rect)
            )
            x += width + gap

    def _draw_scroll_controls(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        window: Any,
        columns: int,
    ) -> None:
        if not window.can_scroll_backward and not window.can_scroll_forward:
            return
        size = max(48, min(62, screen.get_height() // 9))
        x = screen.get_width() - size - 12
        center_y = screen.get_height() // 2 + 36
        controls = (
            (
                -1,
                pygame.Rect(x, center_y - size - 8, size, size),
                window.can_scroll_backward,
            ),
            (
                1,
                pygame.Rect(x, center_y + 8, size, size),
                window.can_scroll_forward,
            ),
        )
        for direction, rect, enabled in controls:
            if not enabled:
                continue
            pygame.draw.rect(screen, theme.panel, rect, border_radius=18)
            pygame.draw.rect(screen, theme.accent, rect, width=4, border_radius=18)
            inset = max(12, rect.width // 4)
            if direction < 0:
                points = (
                    (rect.left + inset, rect.bottom - inset),
                    (rect.centerx, rect.top + inset),
                    (rect.right - inset, rect.bottom - inset),
                )
            else:
                points = (
                    (rect.left + inset, rect.top + inset),
                    (rect.centerx, rect.bottom - inset),
                    (rect.right - inset, rect.top + inset),
                )
            pygame.draw.polygon(screen, theme.text, points)
            target = min(
                max(0, self._selected + direction * columns),
                len(self._presented_activities) - 1,
            )
            self._targets.append(
                HitTarget("presented_activity_select", target, rect)
            )

    def _draw_activity_tile(
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
        shadow = self._shadow_for(rect.size, pygame)
        tile = draw_raised_panel(
            screen,
            rect,
            pygame,
            fill=theme.panel,
            outline=outline,
            state=state,
            motion=motion,
            style=self._DEPTH,
            cached_shadow=shadow,
        )
        icon_size = max(58, int(tile.width * 0.54))
        icon = self._activity_icon(activity, icon_size, pygame)
        screen.blit(
            icon,
            icon.get_rect(center=(tile.centerx, tile.centery - tile.height * 0.10)),
        )
        title = self._font(max(18, min(25, tile.height // 8)), pygame).render(
            _activity_title(activity), True, theme.text
        )
        if title.get_width() > tile.width - 18:
            target_width = tile.width - 18
            title = pygame.transform.smoothscale(
                title,
                (
                    target_width,
                    max(
                        1,
                        round(
                            title.get_height()
                            * target_width
                            / title.get_width()
                        ),
                    ),
                ),
            )
        screen.blit(
            title,
            title.get_rect(center=(tile.centerx, tile.bottom - tile.height * 0.12)),
        )

    def _activity_icon(
        self, activity: ActivityManifest, size: int, pygame: Any
    ) -> Any:
        key = (activity.activity_id, activity.version, size)
        cached = self._decorated_icon_cache.get(key)
        if cached is not None:
            return cached
        try:
            package_path = package_icon_path(activity)
            if package_path is not None:
                source = pygame.image.load(str(package_path)).convert_alpha()
                source = pygame.transform.smoothscale(source, (size, size))
            else:
                source = self._load_icon(activity.icon_id, size, pygame)
        except (ActivityIconError, OSError, ValueError, pygame.error):
            self._catalogue_error = True
            source = self._load_icon("robot", size, pygame)
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
                if item is manifest
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


def _activity_title(activity: ActivityManifest) -> str:
    candidate = activity.title_key.strip()
    if candidate and "." not in candidate:
        return candidate
    tail = activity.activity_id.rsplit(".", 1)[-1]
    return tail.replace("-", " ").replace("_", " ").title()


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

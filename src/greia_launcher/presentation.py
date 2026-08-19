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
        _set_x11_input_focus(screen, pygame)
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
                    elif event.type == pygame.VIDEORESIZE:
                        request = self._resize_display_request(event, pygame)
                        if request is not None:
                            screen = pygame.display.set_mode(*request)

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
        elif key == pygame.K_BACKSPACE and self._category_id != ALL_ACTIVITIES_ID:
            self._set_category(ALL_ACTIVITIES_ID)
        elif key == pygame.K_ESCAPE:
            if self._category_id != ALL_ACTIVITIES_ID:
                self._set_category(ALL_ACTIVITIES_ID)
            else:
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
            if target.action == "activity_category_back":
                self._set_category(ALL_ACTIVITIES_ID)
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
        # Runtime authority must be rebuilt before the newly discovered manifest
        # is published into the child-facing catalogue. If that construction
        # fails, the last known-good service/catalogue pair remains authoritative.
        previous_activities = self._activities
        self._activities = discovered
        try:
            self._rebuild_runtime_services()
        except (ActivityValidationError, OSError, ValueError):
            self._activities = previous_activities
            self._catalogue_error = True
            return
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
        right = screen.get_width() - 20
        gap = 9
        height = max(42, min(52, screen.get_height() // 11))
        available = max(0, right - left)
        show_labels = available >= len(collections) * 112
        x = left
        pointer = pygame.mouse.get_pos()
        pointer_active = pygame.mouse.get_focused()
        for collection in collections:
            label_text = collection.title or collection.collection_id
            font = self._font(max(18, min(22, height // 2)), pygame)
            label = font.render(label_text, True, theme.text)
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
            category_icon = self._load_icon(
                collection.icon_id or "backpack", icon_size, pygame
            )
            category_icon = make_shadowed_icon(
                category_icon,
                pygame,
                shadow_alpha=40,
                shadow_offset=2,
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

        collection = self._catalogue.collection(self._category_id)
        left = 112 if self._active_profile is not None else 20
        height = max(46, min(58, screen.get_height() // 10))
        back_rect = pygame.Rect(left, 16, height, height)
        hovered = back_rect.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_focused()
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
        arrow_inset = max(12, height // 4)
        arrow_x = back_rect.left + arrow_inset
        arrow_tip_x = back_rect.left + height // 3
        arrow_right = back_rect.right - arrow_inset
        pygame.draw.line(
            screen,
            theme.text,
            (arrow_tip_x, back_rect.centery),
            (arrow_right, back_rect.centery),
            width=max(3, height // 12),
        )
        pygame.draw.lines(
            screen,
            theme.text,
            False,
            (
                (arrow_x + height // 8, back_rect.centery - height // 6),
                (arrow_tip_x, back_rect.centery),
                (arrow_x + height // 8, back_rect.centery + height // 6),
            ),
            width=max(3, height // 12),
        )
        self._targets.append(
            HitTarget("activity_category_back", ALL_ACTIVITIES_ID, back_rect)
        )

        icon_size = max(38, height - 2)
        category_icon = self._load_icon(
            collection.icon_id or "backpack", icon_size, pygame
        )
        category_icon = make_shadowed_icon(
            category_icon,
            pygame,
            shadow_alpha=48,
            shadow_offset=max(2, icon_size // 24),
        )
        icon_center = (back_rect.right + 14 + icon_size // 2, back_rect.centery)
        screen.blit(category_icon, category_icon.get_rect(center=icon_center))

        label_text = collection.title or collection.collection_id
        label = self._font(max(22, min(30, height // 2)), pygame).render(
            label_text, True, theme.text
        )
        screen.blit(
            label,
            label.get_rect(midleft=(icon_center[0] + icon_size // 2 + 12, back_rect.centery)),
        )

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

        # Reserve a real label band instead of treating the Activity name as an
        # incidental caption. This keeps names legible across icon aspect ratios
        # and makes every Activity identifiable even when its artwork is novel.
        label_height = max(32, min(48, int(tile.height * 0.24)))
        label_rect = pygame.Rect(
            tile.left + 8,
            tile.bottom - label_height - 7,
            tile.width - 16,
            label_height,
        )
        pygame.draw.rect(
            screen,
            _mix(theme.panel, theme.accent, 0.07),
            label_rect,
            border_radius=max(12, label_height // 3),
        )
        icon_room = max(54, label_rect.top - tile.top - 20)
        icon_size = max(52, min(int(tile.width * 0.54), icon_room))
        icon = self._activity_icon(activity, icon_size, pygame)
        icon_center_y = tile.top + max(12, (label_rect.top - tile.top) // 2)
        screen.blit(
            icon,
            icon.get_rect(center=(tile.centerx, icon_center_y)),
        )
        title = self._render_activity_label(
            _activity_title(activity),
            max_width=label_rect.width - 14,
            max_height=label_rect.height - 8,
            pygame=pygame,
            color=theme.text,
            preferred_size=max(18, min(25, tile.height // 8)),
        )
        screen.blit(title, title.get_rect(center=label_rect.center))

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
        """Fit one Activity name without geometrically distorting glyphs."""

        for size in range(preferred_size, 15, -1):
            rendered = self._font(size, pygame).render(text, True, color)
            if rendered.get_width() <= max_width and rendered.get_height() <= max_height:
                return rendered
        shortened = text.strip()
        font = self._font(16, pygame)
        while len(shortened) > 3:
            shortened = shortened[:-2].rstrip()
            rendered = font.render(shortened + "…", True, color)
            if rendered.get_width() <= max_width:
                return rendered
        return font.render(shortened or "Activity", True, color)

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
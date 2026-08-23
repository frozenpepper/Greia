from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from typing import Any

from greia_platform.achievements import (
    AchievementEntry,
    AchievementError,
    AchievementSnapshot,
)
from greia_platform.pygame_achievements import PygameAchievementBadgeRenderer
from greia_platform.system_language import SystemLanguageStore
from greia_platform.typography import FontRole

from .main import HitTarget


@dataclass(slots=True)
class _AchievementCelebration:
    entry: AchievementEntry
    intro_started: float


class AchievementLibraryMixin:
    """Profile-owned achievement library and post-Activity badge celebration.

    This presentation layer never decides whether an achievement is earned. It
    reads only ``ProfileAchievementService`` snapshots composed by the trusted
    launcher. Activity processes cannot invoke this UI or mutate its state.

    Historical/reconstructed unlocks appear as NEW in the library but are not
    replayed as a popup queue on profile activation. Celebration popups are for
    achievements earned during the Activity session that just returned control
    to the Shell.
    """

    _ACHIEVEMENTS_PER_PAGE = 6
    _CELEBRATION_INTRO_SECONDS = 0.34

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._achievement_snapshot: AchievementSnapshot | None = None
        self._achievement_selected = 0
        self._achievement_library_seen_ids: tuple[str, ...] = ()
        self._achievement_queue: list[AchievementEntry] = []
        self._achievement_celebration: _AchievementCelebration | None = None
        self._achievement_badges = PygameAchievementBadgeRenderer(self._load_icon)
        try:
            self._achievement_locale = (
                SystemLanguageStore.from_environment().read().locale
            )
        except Exception:
            self._achievement_locale = os.environ.get("GREIA_DEVICE_LOCALE", "en") or "en"

    @property
    def _achievement_service(self) -> Any | None:
        services = getattr(self, "runtime_services", None)
        return None if services is None else getattr(services, "achievement_service", None)

    def _activate_profile(self, profile: Any, pygame: Any) -> None:
        super()._activate_profile(profile, pygame)
        self._achievement_selected = 0
        # Do not replay historical/reconstructed achievements as a popup storm.
        self._refresh_achievements()

    def _logout(self, pygame: Any) -> None:
        self._achievement_snapshot = None
        self._achievement_queue.clear()
        self._achievement_celebration = None
        self._achievement_library_seen_ids = ()
        self._achievement_badges.clear()
        super()._logout(pygame)

    def _launch_selected(self, pygame: Any) -> None:
        before = {
            entry.definition.achievement_id
            for entry in (
                self._achievement_snapshot.entries
                if self._achievement_snapshot is not None
                else ()
            )
            if entry.unlocked
        }
        super()._launch_selected(pygame)
        if self._active_profile is None:
            return
        snapshot = self._refresh_achievements()
        if snapshot is None:
            return
        new_entries = [
            entry
            for entry in snapshot.entries
            if entry.unlocked
            and entry.definition.achievement_id not in before
            and entry.announced_at is None
        ]
        self._queue_achievement_announcements(new_entries, pygame)

    def _refresh_achievements(self) -> AchievementSnapshot | None:
        service = self._achievement_service
        profile = self._active_profile
        if service is None or profile is None:
            self._achievement_snapshot = None
            return None
        try:
            snapshot = service.refresh(profile)
        except (AchievementError, OSError, ValueError):
            self._achievement_snapshot = None
            return None
        self._achievement_snapshot = snapshot
        return snapshot

    def _queue_achievement_announcements(
        self,
        entries: list[AchievementEntry],
        pygame: Any,
    ) -> None:
        known = {item.definition.achievement_id for item in self._achievement_queue}
        if self._achievement_celebration is not None:
            known.add(self._achievement_celebration.entry.definition.achievement_id)
        for entry in entries:
            if entry.definition.achievement_id not in known:
                self._achievement_queue.append(entry)
                known.add(entry.definition.achievement_id)
        if self._achievement_celebration is None and self._achievement_queue:
            entry = self._achievement_queue.pop(0)
            self._achievement_celebration = _AchievementCelebration(
                entry=entry,
                intro_started=time.monotonic(),
            )
            self._run_achievement_intro(pygame)

    def _run_achievement_intro(self, pygame: Any) -> None:
        """Play one short bounded geometry-only pop after Activity handoff."""

        celebration = self._achievement_celebration
        screen = pygame.display.get_surface()
        if celebration is None or screen is None:
            return
        started = time.monotonic()
        while time.monotonic() - started < self._CELEBRATION_INTRO_SECONDS:
            # Restore the Shell through its already cached/dirty paths, then draw
            # only the small opaque achievement card. No full-screen alpha layer.
            super()._draw(screen, pygame)
            self._draw_achievement_celebration(screen, pygame, animated=True)
            self._draw_pointer(screen, pygame)
            pygame.display.flip()
            time.sleep(1.0 / 30.0)

    def _dismiss_achievement_celebration(self, pygame: Any) -> None:
        celebration = self._achievement_celebration
        profile = self._active_profile
        service = self._achievement_service
        if celebration is not None and profile is not None and service is not None:
            try:
                service.mark_announced(
                    profile,
                    celebration.entry.definition.achievement_id,
                )
            except (AchievementError, OSError, ValueError):
                pass
        self._achievement_celebration = None
        if self._achievement_queue:
            entry = self._achievement_queue.pop(0)
            self._achievement_celebration = _AchievementCelebration(
                entry=entry,
                intro_started=time.monotonic(),
            )
            self._run_achievement_intro(pygame)
        self._refresh_achievements()

    def _open_achievement_library(self) -> None:
        snapshot = self._refresh_achievements()
        if snapshot is None:
            return
        self._achievement_selected = 0
        self._achievement_library_seen_ids = tuple(
            entry.definition.achievement_id
            for entry in snapshot.entries
            if entry.unlocked
        )
        self._mode = "achievements"

    def _close_achievement_library(self) -> None:
        service = self._achievement_service
        profile = self._active_profile
        if service is not None and profile is not None:
            try:
                service.mark_seen(profile, self._achievement_library_seen_ids)
            except (AchievementError, OSError, ValueError):
                pass
        self._achievement_library_seen_ids = ()
        self._refresh_achievements()
        self._mode = "activities"

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self._achievement_celebration is not None:
            if key in {
                pygame.K_RETURN,
                pygame.K_SPACE,
                pygame.K_ESCAPE,
                pygame.K_BACKSPACE,
            }:
                self._dismiss_achievement_celebration(pygame)
            return True
        if self._mode != "achievements":
            return super()._handle_key(key, pygame)

        entries = self._achievement_visible_entries()
        if key in {pygame.K_ESCAPE, pygame.K_BACKSPACE}:
            self._close_achievement_library()
        elif entries and key in {pygame.K_LEFT, pygame.K_UP}:
            delta = -1 if key == pygame.K_LEFT else -3
            self._achievement_selected = min(
                max(0, self._achievement_selected + delta), len(entries) - 1
            )
        elif entries and key in {pygame.K_RIGHT, pygame.K_DOWN, pygame.K_TAB}:
            delta = 1 if key in {pygame.K_RIGHT, pygame.K_TAB} else 3
            self._achievement_selected = min(
                max(0, self._achievement_selected + delta), len(entries) - 1
            )
        return True

    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        if self._achievement_celebration is not None:
            self._dismiss_achievement_celebration(pygame)
            return
        if self._mode == "achievements":
            for target in reversed(self._targets):
                if not target.rect.collidepoint(position):
                    continue
                if target.action == "achievement_back":
                    self._close_achievement_library()
                    return
                if target.action == "achievement_entry":
                    self._achievement_selected = int(target.value)
                    return
                if target.action == "achievement_page_prev":
                    self._achievement_selected = max(
                        0,
                        self._achievement_selected - self._ACHIEVEMENTS_PER_PAGE,
                    )
                    return
                if target.action == "achievement_page_next":
                    entries = self._achievement_visible_entries()
                    self._achievement_selected = min(
                        max(0, len(entries) - 1),
                        self._achievement_selected + self._ACHIEVEMENTS_PER_PAGE,
                    )
                    return
            return

        for target in reversed(self._targets):
            if (
                target.rect.collidepoint(position)
                and target.action == "achievement_library"
            ):
                self._open_achievement_library()
                return
        super()._handle_click(position, pygame)

    def _draw(self, screen: Any, pygame: Any) -> None:
        if self._mode == "achievements":
            self._targets.clear()
            theme = self.theme_controller.draw_background(screen, pygame)
            self._draw_achievement_library(screen, theme, pygame)
            self._draw_pointer(screen, pygame)
            return
        super()._draw(screen, pygame)
        if self._achievement_celebration is not None:
            self._draw_achievement_celebration(screen, pygame, animated=False)
            # Base Shell draws its pointer before this mixin; redraw it last so
            # the child cursor never disappears behind the celebration card.
            self._draw_pointer(screen, pygame)

    def _draw_activities(self, screen: Any, theme: Any, pygame: Any) -> None:
        """Add the profile badge-library route after any Activity/Home projection.

        Hooking the complete activities surface, rather than only
        ``_render_activities_content``, keeps the route present even when an
        earlier adaptive-discovery mixin intentionally renders a sub-Collection
        chooser without delegating farther down the content chain.
        """

        super()._draw_activities(screen, theme, pygame)
        if self._achievement_service is None or self._active_profile is None:
            return
        if (
            (getattr(self, "_last_result", None) and not self._last_result.succeeded)
            or getattr(self, "_catalogue_error", False)
        ):
            return
        self._draw_achievement_library_button(screen, theme, pygame)

    def _draw_achievement_library_button(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        snapshot = self._achievement_snapshot or self._refresh_achievements()
        if snapshot is None:
            return
        size = max(58, min(76, screen.get_height() // 8))
        rect = pygame.Rect(screen.get_width() - size - 14, 10, size, size)
        pygame.draw.rect(screen, theme.panel, rect, border_radius=20)
        pygame.draw.rect(screen, theme.accent, rect, width=4, border_radius=20)
        icon = self._load_icon("yellow_star", max(30, size - 24), pygame)
        screen.blit(icon, icon.get_rect(center=(rect.centerx, rect.centery - 4)))
        count = self._typography.font(FontRole.CONTROL, max(12, size // 5)).render(
            str(snapshot.unlocked_count), True, theme.text
        )
        pill = pygame.Rect(
            0,
            0,
            max(22, count.get_width() + 10),
            max(20, count.get_height() + 4),
        )
        pill.bottomright = (rect.right + 2, rect.bottom + 2)
        pygame.draw.rect(screen, theme.accent, pill, border_radius=pill.height // 2)
        screen.blit(count, count.get_rect(center=pill.center))
        self._targets.append(
            HitTarget("achievement_library", None, rect.inflate(8, 8))
        )

    def _achievement_visible_entries(self) -> tuple[AchievementEntry, ...]:
        snapshot = self._achievement_snapshot
        return () if snapshot is None else snapshot.visible_entries

    def _draw_achievement_library(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        snapshot = self._refresh_achievements()
        entries = () if snapshot is None else snapshot.visible_entries
        width, height = screen.get_size()

        back_size = max(54, min(68, height // 9))
        back = pygame.Rect(14, 12, back_size, back_size)
        pygame.draw.rect(screen, theme.panel, back, border_radius=18)
        pygame.draw.rect(screen, theme.accent, back, width=4, border_radius=18)
        points = (
            (back.centerx + 10, back.top + 14),
            (back.centerx - 10, back.centery),
            (back.centerx + 10, back.bottom - 14),
        )
        pygame.draw.lines(screen, theme.text, False, points, width=6)
        self._targets.append(HitTarget("achievement_back", None, back))

        italian = self._achievement_locale.casefold().startswith("it")
        title_text = "I MIEI DISTINTIVI" if italian else "MY BADGES"
        title = self._typography.font(
            FontRole.TITLE, max(26, min(38, height // 15))
        ).render(title_text, True, theme.text)
        screen.blit(title, title.get_rect(center=(width // 2, back.centery)))

        if snapshot is not None:
            # Secret locked achievements are absent from visible_entries and must
            # not leak through the denominator.
            counter_text = f"{snapshot.unlocked_count}/{len(entries)}"
            counter = self._typography.font(
                FontRole.CONTROL, max(18, height // 30)
            ).render(counter_text, True, theme.text)
            screen.blit(counter, counter.get_rect(midright=(width - 18, back.centery)))

        if not entries:
            empty_text = (
                "I distintivi arriveranno esplorando Greia."
                if italian
                else "Badges will appear as you explore Greia."
            )
            empty = self._typography.font(
                FontRole.BODY, max(20, height // 24)
            ).render(empty_text, True, theme.text)
            screen.blit(empty, empty.get_rect(center=screen.get_rect().center))
            return

        self._achievement_selected = min(self._achievement_selected, len(entries) - 1)
        page_index = self._achievement_selected // self._ACHIEVEMENTS_PER_PAGE
        page_start = page_index * self._ACHIEVEMENTS_PER_PAGE
        page_entries = entries[page_start : page_start + self._ACHIEVEMENTS_PER_PAGE]

        grid_top = back.bottom + 12
        detail_h = max(118, min(142, height // 4))
        grid_bottom = height - detail_h - 10
        columns = 3
        rows = 2
        gap_x = max(12, width // 60)
        gap_y = 10
        side = 54
        cell_w = (width - side * 2 - gap_x * (columns - 1)) // columns
        cell_h = max(100, (grid_bottom - grid_top - gap_y) // rows)

        for local_index, entry in enumerate(page_entries):
            global_index = page_start + local_index
            row = local_index // columns
            column = local_index % columns
            rect = pygame.Rect(
                side + column * (cell_w + gap_x),
                grid_top + row * (cell_h + gap_y),
                cell_w,
                cell_h,
            )
            selected = global_index == self._achievement_selected
            pygame.draw.rect(screen, theme.panel, rect, border_radius=20)
            pygame.draw.rect(
                screen,
                theme.accent
                if selected
                else self._mix_color(theme.text, theme.panel, 0.78),
                rect,
                width=5 if selected else 2,
                border_radius=20,
            )
            badge_size = max(66, min(92, rect.height - 38))
            badge = self._achievement_badges.render(entry, badge_size, pygame)
            screen.blit(
                badge,
                badge.get_rect(
                    center=(rect.centerx, rect.top + badge_size // 2 + 4)
                ),
            )

            label_text = entry.definition.title.resolve(self._achievement_locale)
            label = self._fit_text(
                label_text,
                max_width=rect.width - 16,
                size=max(14, min(18, rect.height // 8)),
                color=theme.text,
            )
            screen.blit(
                label,
                label.get_rect(center=(rect.centerx, rect.bottom - 18)),
            )
            if entry.is_new:
                new_text = "NUOVO" if italian else "NEW"
                new = self._typography.font(FontRole.CONTROL, 12).render(
                    new_text, True, theme.accent_text
                )
                new_rect = pygame.Rect(
                    0,
                    0,
                    new.get_width() + 12,
                    new.get_height() + 5,
                )
                new_rect.topright = (rect.right - 6, rect.top + 6)
                pygame.draw.rect(
                    screen, theme.accent, new_rect, border_radius=8
                )
                screen.blit(new, new.get_rect(center=new_rect.center))
            self._targets.append(
                HitTarget("achievement_entry", global_index, rect)
            )

        detail = pygame.Rect(36, grid_bottom + 8, width - 72, detail_h - 16)
        pygame.draw.rect(screen, theme.panel, detail, border_radius=20)
        pygame.draw.rect(screen, theme.accent, detail, width=3, border_radius=20)
        selected_entry = entries[self._achievement_selected]
        heading = selected_entry.definition.title.resolve(self._achievement_locale)
        heading_surface = self._fit_text(
            heading,
            max_width=detail.width - 36,
            size=max(18, min(24, detail.height // 4)),
            color=theme.text,
        )
        screen.blit(heading_surface, (detail.left + 18, detail.top + 12))
        description = (
            selected_entry.definition.description.resolve(self._achievement_locale)
            if selected_entry.unlocked
            else selected_entry.definition.locked_hint.resolve(
                self._achievement_locale
            )
        )
        detail_size = max(15, min(19, detail.height // 6))
        lines = self._wrap_text(
            description,
            max_width=detail.width - 36,
            size=detail_size,
        )
        y = detail.top + 48
        for line in lines[:2]:
            rendered = self._typography.font(FontRole.BODY, detail_size).render(
                line, True, theme.text
            )
            screen.blit(rendered, (detail.left + 18, y))
            y += rendered.get_height() + 3

        total_pages = (
            len(entries) + self._ACHIEVEMENTS_PER_PAGE - 1
        ) // self._ACHIEVEMENTS_PER_PAGE
        if page_index > 0:
            self._draw_page_arrow(
                screen,
                theme,
                pygame,
                left=True,
                action="achievement_page_prev",
            )
        if page_index + 1 < total_pages:
            self._draw_page_arrow(
                screen,
                theme,
                pygame,
                left=False,
                action="achievement_page_next",
            )

    def _draw_page_arrow(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        *,
        left: bool,
        action: str,
    ) -> None:
        size = max(42, min(54, screen.get_height() // 11))
        rect = pygame.Rect(
            8 if left else screen.get_width() - size - 8,
            screen.get_height() // 2 - size // 2,
            size,
            size,
        )
        pygame.draw.rect(screen, theme.panel, rect, border_radius=16)
        pygame.draw.rect(screen, theme.accent, rect, width=3, border_radius=16)
        inset = 13
        points = (
            (
                (rect.right - inset, rect.top + inset),
                (rect.left + inset, rect.centery),
                (rect.right - inset, rect.bottom - inset),
            )
            if left
            else (
                (rect.left + inset, rect.top + inset),
                (rect.right - inset, rect.centery),
                (rect.left + inset, rect.bottom - inset),
            )
        )
        pygame.draw.lines(screen, theme.text, False, points, width=5)
        self._targets.append(HitTarget(action, None, rect))

    def _draw_achievement_celebration(
        self,
        screen: Any,
        pygame: Any,
        *,
        animated: bool,
    ) -> None:
        celebration = self._achievement_celebration
        if celebration is None:
            return
        theme = self.theme_controller.theme
        entry = celebration.entry
        width, height = screen.get_size()
        panel_w = min(520, width - 70)
        panel_h = min(310, height - 70)
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = screen.get_rect().center

        # Static opaque card; no full-screen alpha blend over the launcher.
        pygame.draw.rect(screen, theme.panel, panel, border_radius=28)
        pygame.draw.rect(screen, theme.accent, panel, width=6, border_radius=28)

        elapsed = max(0.0, time.monotonic() - celebration.intro_started)
        pulse = (
            min(1.0, elapsed / self._CELEBRATION_INTRO_SECONDS)
            if animated
            else 1.0
        )
        ray_len = int(16 + 14 * math.sin(pulse * math.pi / 2.0))
        cx, cy = panel.centerx, panel.top + 104
        for index in range(10):
            angle = index * math.tau / 10.0
            inner = 64
            outer = inner + ray_len
            pygame.draw.line(
                screen,
                theme.accent,
                (
                    cx + int(math.cos(angle) * inner),
                    cy + int(math.sin(angle) * inner),
                ),
                (
                    cx + int(math.cos(angle) * outer),
                    cy + int(math.sin(angle) * outer),
                ),
                width=4,
            )

        badge = self._achievement_badges.render(entry, 126, pygame)
        screen.blit(badge, badge.get_rect(center=(cx, cy)))
        italian = self._achievement_locale.casefold().startswith("it")
        eyebrow_text = "NUOVO DISTINTIVO!" if italian else "NEW BADGE!"
        eyebrow = self._typography.font(FontRole.CONTROL, 19).render(
            eyebrow_text, True, theme.accent
        )
        screen.blit(
            eyebrow,
            eyebrow.get_rect(center=(panel.centerx, panel.top + 28)),
        )

        title_text = entry.definition.title.resolve(self._achievement_locale)
        title = self._fit_text(
            title_text,
            max_width=panel.width - 50,
            size=28,
            color=theme.text,
        )
        screen.blit(
            title,
            title.get_rect(center=(panel.centerx, panel.top + 190)),
        )
        description = entry.definition.description.resolve(self._achievement_locale)
        lines = self._wrap_text(
            description,
            max_width=panel.width - 60,
            size=18,
        )
        y = panel.top + 220
        for line in lines[:2]:
            rendered = self._typography.font(FontRole.BODY, 18).render(
                line, True, theme.text
            )
            screen.blit(rendered, rendered.get_rect(center=(panel.centerx, y)))
            y += rendered.get_height() + 3
        self._targets.append(
            HitTarget("achievement_dismiss", None, panel.inflate(30, 30))
        )

    def _fit_text(
        self,
        text: str,
        *,
        max_width: int,
        size: int,
        color: tuple[int, int, int],
    ) -> Any:
        current = max(11, size)
        while current > 11:
            rendered = self._typography.font(FontRole.CONTROL, current).render(
                text, True, color
            )
            if rendered.get_width() <= max_width:
                return rendered
            current -= 1
        return self._typography.font(FontRole.CONTROL, 11).render(
            text, True, color
        )

    def _wrap_text(
        self, text: str, *, max_width: int, size: int
    ) -> tuple[str, ...]:
        font = self._typography.font(FontRole.BODY, size)
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if current and font.size(candidate)[0] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return tuple(lines)

    @staticmethod
    def _mix_color(
        first: tuple[int, int, int],
        second: tuple[int, int, int],
        weight_first: float,
    ) -> tuple[int, int, int]:
        return tuple(
            int(a * weight_first + b * (1.0 - weight_first))
            for a, b in zip(first[:3], second[:3])
        )

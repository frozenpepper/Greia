from __future__ import annotations

from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError

from .catalogue_view import ALL_ACTIVITIES_ID
from .main import HitTarget
from .portal_geometry import portal_icon_center, portal_icon_size


_ADAPTIVE_VISUAL_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)


class AdaptiveActivityDiscoveryMixin:
    """Render one optional adaptive sub-Collection presentation layer.

    This mixin owns child-facing grouping/navigation only. It deliberately has
    no Parent discovery-policy store, filtering service, reload token, or policy
    write path. Installed child compositions that expose Activities must project
    Parent visibility/age/difficulty authority before this presentation layer;
    ``PolicyEnforcedAdaptiveActivityDiscoveryMixin`` provides that composition.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._subcollection_id: str | None = None
        self._subcollection_selected = 0

    @property
    def _presented_activities(self):
        self._category_id = self._catalogue.nearest_category(self._category_id)
        if self._subcollection_id is not None:
            group = self._catalogue.subcollection(
                self._category_id, self._subcollection_id
            )
            if group is not None:
                return group.items
            self._subcollection_id = None
        if self._catalogue.subcollections_for(self._category_id):
            return ()
        return self._catalogue.collection(self._category_id).items

    def _activate_profile(self, profile: Any, pygame: Any) -> None:
        super()._activate_profile(profile, pygame)
        self._subcollection_id = None
        self._subcollection_selected = 0

    def _logout(self, pygame: Any) -> None:
        self._subcollection_id = None
        self._subcollection_selected = 0
        super()._logout(pygame)

    def _set_category(self, category_id: str) -> None:
        self._subcollection_id = None
        self._subcollection_selected = 0
        super()._set_category(category_id)

    def _adaptive_groups(self):
        if self._category_id == ALL_ACTIVITIES_ID:
            return ()
        return self._catalogue.subcollections_for(self._category_id)

    def _group_chooser_active(self) -> bool:
        return bool(self._adaptive_groups()) and self._subcollection_id is None

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self._mode == "activities" and self._subcollection_id is not None:
            if key in {pygame.K_BACKSPACE, pygame.K_ESCAPE}:
                self._subcollection_id = None
                self._subcollection_selected = 0
                self._selected = 0
                self._activity_scroll_start = 0
                self._cached_activities_key = None
                try:
                    self._stop_spoken_labels()  # type: ignore[attr-defined]
                except Exception:
                    pass
                return True

        if self._mode == "activities" and self._group_chooser_active():
            groups = self._adaptive_groups()
            if not groups:
                return super()._handle_key(key, pygame)
            old_sel = getattr(self, "_subcollection_selected", 0)
            was_open = key in {pygame.K_RETURN, pygame.K_SPACE}
            if was_open:
                try:
                    self._stop_spoken_labels()  # type: ignore[attr-defined]
                except Exception:
                    pass
            self._last_result = None
            self._catalogue_error = False
            columns = self._subcollection_columns(pygame)
            if key == pygame.K_TAB:
                self._subcollection_selected = (
                    self._subcollection_selected + 1
                ) % len(groups)
            elif key in {pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN}:
                delta = {
                    pygame.K_LEFT: -1,
                    pygame.K_RIGHT: 1,
                    pygame.K_UP: -columns,
                    pygame.K_DOWN: columns,
                }[key]
                self._subcollection_selected = min(
                    max(0, self._subcollection_selected + delta), len(groups) - 1
                )
            elif key in {pygame.K_RETURN, pygame.K_SPACE}:
                cid = groups[self._subcollection_selected].collection_id
                self._open_subcollection(cid)
                try:
                    self._spoken_labels.announce_collection(cid, self._spoken_locale(), pygame)  # type: ignore[attr-defined]
                except Exception:
                    pass
                return True
            elif key in {pygame.K_BACKSPACE, pygame.K_ESCAPE}:
                self._set_category(ALL_ACTIVITIES_ID)
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
            self._cached_activities_key = None
            try:
                if getattr(self, "_subcollection_selected", 0) != old_sel:
                    cid = groups[self._subcollection_selected].collection_id
                    self._spoken_labels.announce_collection(cid, self._spoken_locale(), pygame)  # type: ignore[attr-defined]
            except Exception:
                pass
            return True
        return super()._handle_key(key, pygame)

    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        for target in reversed(self._targets):
            if not target.rect.collidepoint(position):
                continue
            if target.action == "activity_subcollection":
                cid = str(target.value)
                try:
                    self._stop_spoken_labels()  # type: ignore[attr-defined]
                except Exception:
                    pass
                self._open_subcollection(cid)
                try:
                    self._spoken_labels.announce_collection(cid, self._spoken_locale(), pygame)  # type: ignore[attr-defined]
                except Exception:
                    pass
                return
            if (
                target.action == "activity_category_back"
                and self._subcollection_id is not None
            ):
                self._subcollection_id = None
                self._subcollection_selected = 0
                self._selected = 0
                self._activity_scroll_start = 0
                self._cached_activities_key = None
                try:
                    self._stop_spoken_labels()  # type: ignore[attr-defined]
                except Exception:
                    pass
                return
        super()._handle_click(position, pygame)

    def _open_subcollection(self, group_id: str) -> None:
        group = self._catalogue.subcollection(self._category_id, group_id)
        if group is None:
            return
        self._subcollection_id = group.collection_id
        self._selected = 0
        self._activity_scroll_start = 0
        self._cached_activities_key = None

    def _draw_activities(self, screen: Any, theme: Any, pygame: Any) -> None:
        super()._draw_activities(screen, theme, pygame)

    def _render_activities_content(self, screen: Any, theme: Any, pygame: Any) -> None:
        if self._group_chooser_active():
            self._render_subcollection_chooser(screen, theme, pygame)
            return
        super()._render_activities_content(screen, theme, pygame)
        if self._subcollection_id is not None:
            self._draw_subcollection_identity(screen, theme, pygame)

    def _subcollection_columns(self, pygame: Any) -> int:
        surface = pygame.display.get_surface()
        width = surface.get_width() if surface is not None else 1024
        return 3 if width >= 820 else 2 if width >= 560 else 1

    def _render_subcollection_chooser(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        width, height = screen.get_size()
        panel_top = max(52, min(62, height // 10))
        draw_panel = getattr(self, "_draw_shared_shell_panel", None)
        if draw_panel is not None:
            draw_panel(
                screen,
                pygame,
                top=panel_top,
                bottom_margin=4,
                max_width=width - 24,
                theme=theme,
            )
        self._draw_active_profile_badge(screen, theme, pygame)
        self._draw_category_header(screen, theme, pygame)

        groups = self._adaptive_groups()
        if not groups:
            self._draw_empty(screen, pygame)
            return
        self._subcollection_selected = min(
            self._subcollection_selected, len(groups) - 1
        )
        inner = getattr(self, "_shared_panel_inner_rect", None)
        if inner is None:
            inner = pygame.Rect(28, panel_top + 32, width - 56, height - panel_top - 52)
        else:
            inner = inner.copy()
            inner.top += max(22, height // 24)
            inner.height = max(1, inner.height - max(22, height // 24))

        columns = min(self._subcollection_columns(pygame), len(groups))
        rows = (len(groups) + columns - 1) // columns
        gap_x = max(18, min(32, inner.width // 24))
        gap_y = max(12, min(24, inner.height // 22))
        label_height = max(30, min(42, inner.height // 9))
        cell_w = max(1, (inner.width - gap_x * (columns - 1)) // columns)
        cell_h = max(1, (inner.height - gap_y * (rows - 1)) // rows)
        # 177 = 170 reference portal +4% for consistent card/button scale.
        portal_size = max(
            84,
            min(177, cell_w - 8, cell_h - label_height - 4),
        )
        item_h = portal_size + label_height
        total_h = rows * item_h + gap_y * (rows - 1)
        origin_y = inner.top + max(0, (inner.height - total_h) // 2)
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)
        visual_cache = getattr(self, "_visual_cache", None)

        for index, group in enumerate(groups):
            row = index // columns
            column = index % columns
            row_start = row * columns
            row_count = min(columns, len(groups) - row_start)
            row_width = row_count * portal_size + max(0, row_count - 1) * gap_x
            x0 = inner.centerx - row_width // 2
            x = x0 + column * (portal_size + gap_x)
            y = origin_y + row * (item_h + gap_y)
            portal = pygame.Rect(x, y, portal_size, portal_size)
            hit = pygame.Rect(x, y, portal_size, item_h)
            hovered = pointer_active and hit.collidepoint(pointer)
            selected = index == self._subcollection_selected
            drawn = portal.move(0, -3 if hovered or selected else 0)

            surface = None
            if visual_cache is not None:
                try:
                    surface = visual_cache.get(
                        "ui.portal.frame", variant="default", size=drawn.size
                    )
                except (_ADAPTIVE_VISUAL_ERRORS + (pygame.error,)):
                    surface = None
            if surface is not None:
                screen.blit(surface, drawn)
            else:
                radius = max(20, min(drawn.width, drawn.height) // 2 - 3)
                pygame.draw.circle(screen, theme.panel, drawn.center, radius)
                pygame.draw.circle(
                    screen,
                    theme.accent if hovered or selected else theme.text,
                    drawn.center,
                    radius,
                    width=5 if selected else 3,
                )
            icon = self._category_shadowed_icon(
                group.icon_id or "backpack",
                portal_icon_size(portal.width),
                shadow_alpha=42,
                shadow_offset=2,
                pygame=pygame,
            )
            screen.blit(
                icon,
                icon.get_rect(center=portal_icon_center(drawn.center, drawn.height)),
            )
            label = self._category_label_surface(
                group.title or group.collection_id,
                max(18, min(26, label_height * 2 // 3)),
                theme.text,
                pygame,
            )
            if label.get_width() > portal_size + 8:
                scale = (portal_size + 8) / label.get_width()
                label = pygame.transform.smoothscale(
                    label,
                    (portal_size + 8, max(1, round(label.get_height() * scale))),
                )
            screen.blit(
                label,
                label.get_rect(
                    center=(portal.centerx, y + portal_size + label_height // 2)
                ),
            )
            self._targets.append(
                HitTarget("activity_subcollection", group.collection_id, hit)
            )

    def _draw_active_profile_badge(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        if self._active_profile is None:
            return
        height = screen.get_height()
        badge_size = max(62, min(86, height // 7))
        badge = pygame.Rect(14, 10, badge_size, badge_size)
        pygame.draw.rect(screen, theme.panel, badge, border_radius=22)
        pygame.draw.rect(screen, theme.accent, badge, width=5, border_radius=22)
        avatar = self._load_icon(
            self._active_profile.profile.avatar_id, badge_size - 12, pygame
        )
        screen.blit(avatar, avatar.get_rect(center=badge.center))
        self._targets.append(HitTarget("switch_profile", None, badge))
        overlay = getattr(self, "_overlay_active_profile_frame", None)
        if overlay is not None:
            overlay(
                screen,
                badge,
                self._active_profile.profile,
                theme,
                pygame,
            )

    def _draw_subcollection_identity(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        if self._subcollection_id is None:
            return
        group = self._catalogue.subcollection(
            self._category_id, self._subcollection_id
        )
        if group is None:
            return
        label = self._category_label_surface(
            group.title or group.collection_id,
            max(16, min(20, screen.get_height() // 30)),
            theme.text,
            pygame,
        )
        icon_size = max(22, min(30, screen.get_height() // 20))
        icon = self._category_shadowed_icon(
            group.icon_id or "backpack",
            icon_size,
            shadow_alpha=30,
            shadow_offset=2,
            pygame=pygame,
        )
        pill_w = min(
            screen.get_width() - 40,
            label.get_width() + icon_size + 34,
        )
        pill_h = max(32, icon_size + 8)
        pill = pygame.Rect(0, 0, pill_w, pill_h)
        pill.midtop = (screen.get_width() // 2, 76)
        pygame.draw.rect(screen, theme.panel, pill, border_radius=pill_h // 2)
        pygame.draw.rect(screen, theme.accent, pill, width=2, border_radius=pill_h // 2)
        screen.blit(
            icon,
            icon.get_rect(midleft=(pill.left + 10, pill.centery)),
        )
        screen.blit(
            label,
            label.get_rect(midleft=(pill.left + icon_size + 18, pill.centery)),
        )
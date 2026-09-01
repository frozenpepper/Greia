"""Collection-first Greia Home presentation for the child Shell.

The normal child Home is a bounded set of semantic Collection destinations,
not an ``All Activities`` wall with filter tabs. This mixin changes only the
launcher presentation/navigation projection. Activity identity, registry,
permissions, lifecycle and storage remain owned by the existing launcher core.
"""

from __future__ import annotations

from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_effects import transformed_rect
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError
from greia_platform.ui_motion import InteractionVisualState

from .catalogue_view import ALL_ACTIVITIES_ID, _category_title
from .main import HitTarget


_COLLECTION_VISUAL_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)


class CollectionFirstHomeMixin:
    """Present primary Collections as the child-facing Greia Home.

    ``ALL_ACTIVITIES_ID`` remains an internal catalogue projection, but when it
    is the current launcher location this mixin renders available primary
    Collections as large portal destinations. Entering a Collection reuses the
    already-proven Activity catalogue/card path. Local Back returns here.

    The reviewed ``ui.portal.frame`` asset is optional and fail-soft. If its
    generated rendition is missing or corrupt, Collection Home remains usable
    with a primitive circular fallback while the rest of the shared UI stays
    enabled.
    """

    _PORTAL_SOURCE_SIZE = 520

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._home_collection_selected = 0
        self._shared_collection_portal_disabled = False

    def _home_collections(self) -> tuple[Any, ...]:
        return tuple(
            collection
            for collection in self._catalogue.collections
            if collection.collection_id != ALL_ACTIVITIES_ID and collection.items
        )

    def _home_columns(self, pygame: Any) -> int:
        surface = pygame.display.get_surface()
        width = surface.get_width() if surface is not None else 1024
        if width >= 900:
            return 3
        if width >= 620:
            return 2
        return 1

    def _set_home_collection_selected(self, index: int) -> None:
        collections = self._home_collections()
        if not collections:
            self._home_collection_selected = 0
        else:
            self._home_collection_selected = min(max(0, index), len(collections) - 1)
        # The existing activities surface cache predates Collection-first Home;
        # explicitly invalidate it when keyboard/controller focus changes.
        self._cached_activities_key = None

    def _activate_profile(self, profile: Any, pygame: Any) -> None:
        """Every profile activation starts at Greia Home, never a stale Collection."""

        super()._activate_profile(profile, pygame)
        self._home_collection_selected = 0
        self._set_category(ALL_ACTIVITIES_ID)

    def _handle_key(self, key: int, pygame: Any) -> bool:
        if self._mode != "activities" or self._category_id != ALL_ACTIVITIES_ID:
            return super()._handle_key(key, pygame)

        old_idx = getattr(self, "_home_collection_selected", 0)
        was_launch = key in {pygame.K_RETURN, pygame.K_SPACE}
        if was_launch:
            try:
                self._stop_spoken_labels()  # type: ignore[attr-defined]
            except Exception:
                pass
        self._last_result = None
        self._catalogue_error = False
        collections = self._home_collections()
        if collections:
            self._home_collection_selected = min(
                self._home_collection_selected, len(collections) - 1
            )

        if key == pygame.K_TAB and collections:
            self._set_home_collection_selected(
                (self._home_collection_selected + 1) % len(collections)
            )
        elif collections and key in {
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_UP,
            pygame.K_DOWN,
        }:
            columns = self._home_columns(pygame)
            if key == pygame.K_LEFT:
                delta = -1
            elif key == pygame.K_RIGHT:
                delta = 1
            elif key == pygame.K_UP:
                delta = -columns
            else:
                delta = columns
            self._set_home_collection_selected(self._home_collection_selected + delta)
        elif key in {pygame.K_RETURN, pygame.K_SPACE} and collections:
            cid = collections[self._home_collection_selected].collection_id
            self._set_category(cid)
            try:
                self._spoken_labels.announce_collection(cid, self._spoken_locale(), pygame)  # type: ignore[attr-defined]
            except Exception:
                pass
            return True
        elif key in {pygame.K_BACKSPACE, pygame.K_ESCAPE}:
            # At launcher root, Back returns to profile choice rather than
            # manufacturing an additional hidden hierarchy level.
            try:
                self._stop_spoken_labels()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._logout(pygame)
            return True
        elif self.allow_exit and key == pygame.K_q:
            try:
                self._stop_spoken_labels()  # type: ignore[attr-defined]
            except Exception:
                pass
            return False
        # Announce home collection selection changes
        try:
            if getattr(self, "_home_collection_selected", 0) != old_idx:
                cols = self._home_collections()
                if 0 <= self._home_collection_selected < len(cols):
                    cid = cols[self._home_collection_selected].collection_id
                    self._spoken_labels.announce_collection(cid, self._spoken_locale(), pygame)  # type: ignore[attr-defined]
        except Exception:
            pass
        return True

    def _handle_click(self, position: tuple[int, int], pygame: Any) -> None:
        if self._mode == "activities" and self._category_id == ALL_ACTIVITIES_ID:
            for target in reversed(self._targets):
                if not target.rect.collidepoint(position):
                    continue
                if target.action == "home_collection":
                    self._last_result = None
                    self._catalogue_error = False
                    collection_id = str(target.value)
                    for index, collection in enumerate(self._home_collections()):
                        if collection.collection_id == collection_id:
                            self._home_collection_selected = index
                            break
                    try:
                        self._stop_spoken_labels()  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    self._set_category(collection_id)
                    try:
                        self._spoken_labels.announce_collection(collection_id, self._spoken_locale(), pygame)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    return
        super()._handle_click(position, pygame)

    def _scroll_activity_rows(self, direction: int, pygame: Any) -> None:
        if self._category_id == ALL_ACTIVITIES_ID:
            return
        super()._scroll_activity_rows(direction, pygame)

    def _render_activities_content(self, screen: Any, theme: Any, pygame: Any) -> None:
        if self._category_id != ALL_ACTIVITIES_ID:
            super()._render_activities_content(screen, theme, pygame)
            return
        self._render_collection_home(screen, theme, pygame)

    def _render_collection_home(self, screen: Any, theme: Any, pygame: Any) -> None:
        width, height = screen.get_size()

        # Reuse the accepted large Shell tray as framing, but Home content is
        # Collections rather than Activity cards plus filter controls. Draw it
        # before profile chrome so the panel can never cover the switcher.
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

        inner = getattr(self, "_shared_panel_inner_rect", None)
        if inner is None:
            inner = pygame.Rect(24, panel_top + 18, width - 48, height - panel_top - 42)

        # Keep the same active-profile route available on top of Home framing.
        if self._active_profile is not None:
            badge_size = max(62, min(86, height // 7))
            badge = pygame.Rect(14, 10, badge_size, badge_size)
            pygame.draw.rect(screen, theme.panel, badge, border_radius=22)
            pygame.draw.rect(screen, theme.accent, badge, width=5, border_radius=22)
            avatar = self._load_icon(
                self._active_profile.profile.avatar_id,
                badge_size - 12,
                pygame,
            )
            screen.blit(avatar, avatar.get_rect(center=badge.center))
            self._targets.append(HitTarget("switch_profile", None, badge))
            overlay_profile = getattr(self, "_overlay_active_profile_frame", None)
            if overlay_profile is not None:
                overlay_profile(
                    screen,
                    badge,
                    self._active_profile.profile,
                    theme,
                    pygame,
                )

        collections = self._home_collections()
        if not collections:
            self._draw_empty(screen, pygame)
            return
        self._home_collection_selected = min(
            self._home_collection_selected, len(collections) - 1
        )

        columns = min(self._home_columns(pygame), len(collections))
        rows = (len(collections) + columns - 1) // columns
        gap_x = max(20, min(44, inner.width // 20))
        gap_y = max(14, min(24, inner.height // 20))
        label_size = max(17, min(23, inner.height // 18))
        label_gap = max(4, min(8, inner.height // 60))
        label_approx_h = label_size + 4

        avail_cell_w = max(1, (inner.width - gap_x * (columns - 1)) // columns)
        avail_cell_h = max(1, (inner.height - gap_y * (rows - 1)) // rows)
        # 141 = 136 reference portal +4% so Collection buttons match the
        # larger Activity-card scale; label font size stays unchanged.
        portal_size = max(
            76,
            min(
                141,
                avail_cell_w - 12,
                avail_cell_h - label_gap - label_approx_h - 12,
            ),
        )
        item_height = portal_size + label_gap + label_approx_h
        total_height = rows * item_height + gap_y * (rows - 1)
        origin_y = inner.top + max(0, (inner.height - total_height) // 2)

        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)
        visual_cache = getattr(self, "_visual_cache", None)

        for index, collection in enumerate(collections):
            row = index // columns
            column = index % columns
            row_start = row * columns
            row_count = min(columns, len(collections) - row_start)
            row_width = row_count * portal_size + max(0, row_count - 1) * gap_x
            row_origin_x = inner.centerx - row_width // 2
            x = row_origin_x + column * (portal_size + gap_x)
            y = origin_y + row * (item_height + gap_y)

            portal_rect = pygame.Rect(x, y, portal_size, portal_size)
            hit_rect = pygame.Rect(x, y, portal_size, item_height)
            hovered = pointer_active and hit_rect.collidepoint(pointer)
            selected = index == self._home_collection_selected
            state = InteractionVisualState(hovered=hovered, selected=selected)
            target = transformed_rect(portal_rect, self._HOVER.sample(state), pygame)

            portal_surface = None
            if (
                not self._shared_collection_portal_disabled
                and visual_cache is not None
            ):
                try:
                    portal_surface = visual_cache.get(
                        "ui.portal.frame",
                        variant="default",
                        size=target.size,
                    )
                except _COLLECTION_VISUAL_ERRORS:
                    self._shared_collection_portal_disabled = True
                except pygame.error:
                    self._shared_collection_portal_disabled = True

            if portal_surface is not None:
                screen.blit(portal_surface, target)
            else:
                # Narrow fallback: preserve Collection-first information
                # architecture even when only this optional artwork is broken.
                radius = max(20, min(target.width, target.height) // 2 - 3)
                pygame.draw.circle(screen, theme.panel, target.center, radius)
                pygame.draw.circle(
                    screen,
                    theme.accent if state.emphasized else theme.text,
                    target.center,
                    radius,
                    width=5 if state.emphasized else 3,
                )

            if state.emphasized:
                pygame.draw.circle(
                    screen,
                    theme.accent,
                    target.center,
                    max(18, min(target.width, target.height) // 2 - 9),
                    width=max(3, portal_size // 44),
                )

            icon_size = max(42, min(96, int(round(target.width * 0.42))))
            icon = self._category_shadowed_icon(
                collection.icon_id or "backpack",
                icon_size,
                shadow_alpha=44,
                shadow_offset=max(2, icon_size // 28),
                pygame=pygame,
            )
            screen.blit(icon, icon.get_rect(center=(target.centerx, target.centery - 2)))

            label_text = _category_title(collection.collection_id, self._active_locale)
            label = self._category_label_surface(
                label_text,
                label_size,
                theme.text,
                pygame,
            )
            max_label_width = max(40, portal_size + gap_x - 4)
            if label.get_width() > max_label_width:
                label = pygame.transform.smoothscale(
                    label,
                    (
                        max_label_width,
                        max(1, round(label.get_height() * max_label_width / label.get_width())),
                    ),
                )
            label_y = y + portal_size + label_gap + label.get_height() // 2
            screen.blit(
                label,
                label.get_rect(center=(portal_rect.centerx, label_y)),
            )
            self._targets.append(
                HitTarget("home_collection", collection.collection_id, hit_rect)
            )

        if (self._last_result and not self._last_result.succeeded) or self._catalogue_error:
            self._draw_error_badge(screen, pygame)

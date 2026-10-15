"""Storybook Collection pages for the child Shell (Activity browsing).

A Collection page stands on the same cached meadow scene as Home. Its header
shows the local Back control, the current Collection as a small hue portal
with its name, and the other Collections as tappable mini portals. Activities
are large hue-coded cards (``ui.card.activity_tile``) with the Activity icon
filling the card's cream face and the title on a caption pill; two big round
arrows turn pages and a row of dots shows where the child is.

Presentation only: catalogue projection, Parent filtering, selection, paging,
spoken labels and launch lifecycle stay owned by the existing launcher chain.
Geometry comes from :mod:`greia_launcher.collection_page_layout`. Every
artwork is optional: if a rendition is missing or corrupt the page disables
itself and the proven tray/card presentation below it in the MRO takes over.
"""

from __future__ import annotations

import time
from typing import Any

from greia_platform.assets import AssetCatalogueError
from greia_platform.pygame_effects import transformed_rect
from greia_platform.pygame_visual_assets import VisualSurfaceCacheError
from greia_platform.responsive_layout import UiRect
from greia_platform.ui_core import BoundedCache
from greia_platform.ui_motion import InteractionVisualState
from greia_platform.ui_scroll import ScrollModel

from .catalogue_view import ALL_ACTIVITIES_ID, ActivityFolder, _category_title
from .collection_hues import collection_hue, hue_rgb
from .collection_page_layout import (
    CARD_FACE_RADIUS_FRACTION,
    CARD_REPAIR_PAD,
    CollectionPageLayout,
    card_art_height,
    card_face_rect,
    collection_grid_shape,
    page_dot_positions,
)
from .home_layout import PORTAL_ART_HEIGHT, PORTAL_ART_WIDTH, portal_icon_rect
from .main import HitTarget
from .shared_ui_presentation import (
    CAPTION_CREAM,
    CAPTION_FOCUS,
    CAPTION_INK,
    draw_caption_pill,
    draw_title_pill,
)
from .system_chrome import resolve_trusted_action_minimum_px
from .title_presentation import contain_fit_icon_surface


_PAGE_VISUAL_ERRORS = (
    VisualSurfaceCacheError,
    AssetCatalogueError,
    KeyError,
    FileNotFoundError,
    OSError,
    ValueError,
)

CARD_ASSET_ID = "ui.card.activity_tile"
FOLDER_ASSET_ID = "ui.card.folder"
FOCUS_ASSET_ID = "ui.portal.collection_focus"
PORTAL_ASSET_ID = "ui.portal.collection"
ROUND_BUTTON_ASSET_ID = "ui.button.round"


def round_button_variant(kind: str) -> str:
    """Map a control kind to its ``ui.button.round`` variant (Back is the default)."""

    return "default" if kind == "back" else kind


class _PageArtUnavailable(Exception):
    """Raised inside one page render when optional artwork cannot be used."""


class CollectionPageMixin:
    """Render in-Collection Activity pages as big hue-coded storybook cards.

    Sits in the Shell MRO directly after ``CollectionFirstHomeMixin`` (which
    owns Home) and before the shared tray/card/navigation mixins, which remain
    the fail-soft fallback. It refines the launcher seams ``_columns``,
    ``_rows``, ``_draw_category_header``, ``_draw_activity_tile_content``,
    ``_draw_pagination_and_overflow``, ``_draw_page_arrow_button``,
    ``_activities_header_repair_rect`` and ``_activity_tile_style_token``;
    it never adds hit-target actions of its own.
    """

    _TILE_REPAIR_PAD = CARD_REPAIR_PAD

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._collection_page_disabled = False
        self._collection_page_layout: CollectionPageLayout | None = None
        self._collection_layout_cache: BoundedCache[Any, CollectionPageLayout] = BoundedCache(4)
        self._card_mask_cache: BoundedCache[tuple[int, int], Any] = BoundedCache(4)

    # -- activation -----------------------------------------------------

    def _collection_page_active(self) -> bool:
        return (
            getattr(self, "_category_id", ALL_ACTIVITIES_ID) != ALL_ACTIVITIES_ID
            and getattr(self, "_visual_cache", None) is not None
            and not getattr(self, "_collection_page_disabled", False)
        )

    def _disable_collection_page(self) -> None:
        self._collection_page_disabled = True
        self._tile_surface_cache.clear()
        self._cached_activities_key = None

    def _collection_page_hue(self) -> str:
        return collection_hue(
            getattr(self, "_category_id", None),
            group_id=getattr(self, "_subcollection_id", None),
        )

    def _activity_tile_style_token(self) -> Any:
        if not self._collection_page_active():
            return super()._activity_tile_style_token()
        return ("collection_page", self._collection_page_hue())

    # -- geometry -------------------------------------------------------

    def _collection_profile_badge(self, height: int) -> UiRect | None:
        if getattr(self, "_active_profile", None) is None:
            return None
        size = max(62, min(86, height // 7))
        return UiRect(14, 10, size, size)

    def _collection_layout(self, width: int, height: int) -> CollectionPageLayout:
        badge = self._collection_profile_badge(height)
        star = max(58, min(76, height // 8))
        minimum = resolve_trusted_action_minimum_px(
            getattr(self, "_display_metrics", None), fallback_px=44
        )
        key = (width, height, badge, star, minimum)
        layout = self._collection_layout_cache.get(key)
        if layout is None:
            layout = CollectionPageLayout.compute(
                width,
                height,
                profile_badge=badge,
                right_reserve=star + 28,
                minimum_target_px=minimum,
            )
            self._collection_layout_cache[key] = layout
        return layout

    def _display_size(self, pygame: Any) -> tuple[int, int]:
        surface = pygame.display.get_surface()
        if surface is None:
            return 1024, 600
        return surface.get_size()

    def _columns(self, pygame: Any) -> int:
        if not self._collection_page_active():
            return super()._columns(pygame)
        return collection_grid_shape(*self._display_size(pygame))[0]

    def _rows(self, pygame: Any) -> int:
        if not self._collection_page_active():
            return super()._rows(pygame)
        return collection_grid_shape(*self._display_size(pygame))[1]

    # -- page -----------------------------------------------------------

    def _render_activities_content(self, screen: Any, theme: Any, pygame: Any) -> None:
        if not self._collection_page_active():
            super()._render_activities_content(screen, theme, pygame)
            return
        first_target = len(self._targets)
        try:
            self._render_collection_page(screen, theme, pygame)
        except _PageArtUnavailable:
            # Optional art broke mid-frame: drop this partial page and let the
            # proven tray/card presentation draw the same semantics.
            del self._targets[first_target:]
            self._disable_collection_page()
            screen.fill(theme.background)
            super()._render_activities_content(screen, theme, pygame)

    def _render_collection_page(self, screen: Any, theme: Any, pygame: Any) -> None:
        width, height = screen.get_size()
        layout = self._collection_layout(width, height)
        self._collection_page_layout = layout
        self._draw_shell_scene_backdrop(screen, pygame, theme=theme)
        self._draw_active_profile_badge(screen, theme, pygame)
        self._draw_category_bar(screen, theme, pygame)

        activities = self._presented_activities
        error = bool(
            (self._last_result and not self._last_result.succeeded)
            or self._catalogue_error
        )
        if not activities:
            self._draw_empty(screen, pygame)
            if error:
                self._draw_error_badge(screen, pygame)
            return

        capacity = layout.capacity
        self._selected = max(0, min(self._selected, len(activities) - 1))
        self._activity_scroll_start = max(
            0, min(self._activity_scroll_start, len(activities) - 1)
        )
        window = ScrollModel(capacity=capacity, step=capacity).window(
            len(activities), self._selected, self._activity_scroll_start
        )
        self._activity_scroll_start = window.start
        self._page_content_rect = layout.grid_bounds

        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)
        for local_index, presented_index in enumerate(range(window.start, window.stop)):
            activity = activities[presented_index]
            hit = layout.hits[local_index]
            rect = pygame.Rect(hit.x, hit.y, hit.width, hit.height)
            state = InteractionVisualState(
                hovered=pointer_active and rect.collidepoint(pointer),
                selected=presented_index == self._selected,
                launching=activity.activity_id == self._launching_activity_id,
            )
            self._draw_activity_tile(screen, rect, activity, state, theme, pygame)
            self._targets.append(HitTarget("presented_activity", presented_index, rect))
        self._draw_pagination_and_overflow(screen, theme, pygame, window, layout.columns)
        if error:
            self._draw_error_badge(screen, pygame)

    def _repair_dynamic_activities(self, *args: Any, **kwargs: Any) -> bool:
        try:
            return super()._repair_dynamic_activities(*args, **kwargs)
        except _PageArtUnavailable:
            # Fall back to one full rebuild with the proven presentation.
            self._disable_collection_page()
            return False

    # -- sub-Collection chooser ---------------------------------------

    def _render_storybook_subcollection_chooser(
        self, screen: Any, theme: Any, pygame: Any
    ) -> bool:
        """Draw the adaptive group chooser as hue portals on the scene.

        Returns False (nothing consumed) when the storybook page is disabled
        so ``AdaptiveActivityDiscoveryMixin`` keeps its proven tray chooser.
        Groups, selection and the ``activity_subcollection`` targets keep the
        adaptive mixin's semantics.
        """

        if not self._collection_page_active():
            return False
        first_target = len(self._targets)
        try:
            self._draw_storybook_subcollection_chooser(screen, theme, pygame)
        except _PageArtUnavailable:
            del self._targets[first_target:]
            self._disable_collection_page()
            screen.fill(theme.background)
            return False
        return True

    def _draw_storybook_subcollection_chooser(
        self, screen: Any, theme: Any, pygame: Any
    ) -> None:
        from .home_layout import CollectionHomeLayout

        width, height = screen.get_size()
        page = self._collection_layout(width, height)
        self._collection_page_layout = page
        self._draw_shell_scene_backdrop(screen, pygame, theme=theme)
        self._draw_active_profile_badge(screen, theme, pygame)
        self._draw_category_header(screen, theme, pygame)
        groups = self._adaptive_groups()
        if not groups:
            self._draw_empty(screen, pygame)
            return
        self._subcollection_selected = min(self._subcollection_selected, len(groups) - 1)
        header = UiRect(0, 0, width, page.header_bottom + 6)
        layout = CollectionHomeLayout.compute(
            width,
            height,
            len(groups),
            self._subcollection_columns(pygame),
            reserved=(header,),
        )
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)
        visual_cache = self._visual_cache
        for index, group in enumerate(groups):
            portal = layout.portals[index]
            hit = layout.hits[index]
            hit_rect = pygame.Rect(hit.x, hit.y, hit.width, hit.height)
            focused = index == self._subcollection_selected
            hovered = pointer_active and hit_rect.collidepoint(pointer)
            rect = pygame.Rect(portal.x, portal.y, portal.width, portal.height)
            drawn = transformed_rect(
                rect, self._HOVER.sample(InteractionVisualState(hovered=hovered or focused)), pygame
            )
            hue = collection_hue(self._category_id, group_id=group.collection_id)
            try:
                art = visual_cache.get(PORTAL_ASSET_ID, variant=hue, size=drawn.size)
                ring = (
                    visual_cache.get(FOCUS_ASSET_ID, variant="default", size=drawn.size)
                    if focused
                    else None
                )
            except (_PAGE_VISUAL_ERRORS + (pygame.error,)) as exc:
                raise _PageArtUnavailable() from exc
            screen.blit(art, drawn)
            if ring is not None:
                screen.blit(ring, drawn)
            box = portal_icon_rect(UiRect(drawn.x, drawn.y, drawn.width, drawn.height))
            icon = self._category_shadowed_icon(
                group.icon_id or "backpack",
                portal_icon_rect(portal).width,
                shadow_alpha=40,
                shadow_offset=max(2, box.width // 28),
                pygame=pygame,
            )
            screen.blit(icon, icon.get_rect(center=(box.x + box.width // 2, box.y + box.height // 2)))
            slot = layout.labels[index]
            label = self._category_label_surface(
                group.title or group.collection_id, layout.label_font_px, CAPTION_INK, pygame
            )
            if label.get_width() > slot.width - slot.height:
                label = self._fit_label(label, slot.width - slot.height, pygame)
            draw_caption_pill(
                screen,
                pygame,
                pygame.Rect(slot.x, slot.y, slot.width, slot.height),
                label,
                focused=focused,
            )
            self._targets.append(HitTarget("activity_subcollection", group.collection_id, hit_rect))

    # -- header ---------------------------------------------------------

    def _activities_header_repair_rect(self, screen: Any, pygame: Any) -> Any:
        if not self._collection_page_active():
            return super()._activities_header_repair_rect(screen, pygame)
        band = self._collection_layout(*screen.get_size()).header_band
        return pygame.Rect(band.x, band.y, band.width, band.height)

    def _draw_category_header(self, screen: Any, theme: Any, pygame: Any) -> None:
        if not self._collection_page_active():
            super()._draw_category_header(screen, theme, pygame)
            return
        layout = self._collection_layout(*screen.get_size())
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)

        back = pygame.Rect(layout.back.x, layout.back.y, layout.back.width, layout.back.height)
        self._blit_round_button(
            screen, "back", back, pointer_active and back.collidepoint(pointer), pygame
        )
        self._targets.append(HitTarget("activity_category_back", ALL_ACTIVITIES_ID, back))

        # Current place: the Collection's own mini portal plus its name.
        group = None
        if getattr(self, "_subcollection_id", None) is not None:
            group = self._catalogue.subcollection(self._category_id, self._subcollection_id)
        current = self._catalogue.collection(self._category_id)
        icon_id = (group.icon_id if group is not None else None) or current.icon_id or "backpack"
        title = (
            (group.title or group.collection_id)
            if group is not None
            else _category_title(self._category_id, self._active_locale)
        )
        portal_h = layout.header_height + 4
        portal_w = int(round(portal_h * PORTAL_ART_WIDTH / PORTAL_ART_HEIGHT))
        x = layout.identity.x
        portal = pygame.Rect(x, layout.back.y - 2, portal_w, portal_h)
        self._blit_mini_portal(screen, portal, self._collection_page_hue(), icon_id, pygame)
        font_px = max(15, min(26, int(round(layout.header_height * 0.4))))
        label = self._category_label_surface(title, font_px, CAPTION_INK, pygame)
        pill_h = max(28, font_px + 14)
        max_label_w = max(60, min(320, layout.header_right - portal.right - 8))
        if label.get_width() > max_label_w - pill_h:
            label = self._fit_label(label, max_label_w - pill_h, pygame)
        slot = pygame.Rect(
            portal.right + 4,
            portal.top + (layout.header_height - pill_h) // 2,
            label.get_width() + pill_h,
            pill_h,
        )
        draw_caption_pill(screen, pygame, slot, label, focused=False)
        x = slot.right + max(12, layout.header_height // 3)

        # Other Collections: small tappable portals in their own hue.
        chip_h = max(36, int(round(layout.header_height * 0.92)))
        chip_w = int(round(chip_h * PORTAL_ART_WIDTH / PORTAL_ART_HEIGHT))
        gap = max(4, chip_w // 8)
        for collection in self._catalogue.collections:
            cid = collection.collection_id
            if cid in (ALL_ACTIVITIES_ID, self._category_id):
                continue
            if x + chip_w > layout.header_right:
                break
            chip = pygame.Rect(x, layout.back.y + (layout.back.height - chip_h) // 2, chip_w, chip_h)
            hovered = pointer_active and chip.collidepoint(pointer)
            drawn = chip.move(0, -3 if hovered else 0)
            self._blit_mini_portal(
                screen, drawn, collection_hue(cid), collection.icon_id or "backpack", pygame
            )
            self._targets.append(HitTarget("activity_category", cid, chip))
            x += chip_w + gap

    def _fit_label(self, label: Any, max_width: int, pygame: Any) -> Any:
        max_width = max(24, max_width)
        return pygame.transform.smoothscale(
            label,
            (max_width, max(1, round(label.get_height() * max_width / label.get_width()))),
        )

    # -- cards ----------------------------------------------------------

    def _draw_activity_tile_content(
        self,
        screen: Any,
        rect: Any,
        activity: Any,
        state: Any,
        theme: Any,
        pygame: Any,
    ) -> None:
        layout = getattr(self, "_collection_page_layout", None)
        if not self._collection_page_active() or layout is None:
            super()._draw_activity_tile_content(screen, rect, activity, state, theme, pygame)
            return
        motion = (
            self._LAUNCH.sample(time.monotonic() - self._launch_animation_started)
            if state.launching
            else self._HOVER.sample(InteractionVisualState(hovered=state.hovered))
        )
        art = pygame.Rect(rect.x, rect.y, rect.width, card_art_height(rect.width))
        target = transformed_rect(art, motion, pygame)
        if isinstance(activity, ActivityFolder):
            self._draw_folder_card(screen, rect, art, target, activity, state, layout, pygame)
            return
        visual_cache = self._visual_cache
        try:
            card = visual_cache.get(
                CARD_ASSET_ID, variant=self._collection_page_hue(), size=target.size
            )
            ring = (
                visual_cache.get(FOCUS_ASSET_ID, variant="default", size=target.size)
                if state.selected or state.launching
                else None
            )
        except (_PAGE_VISUAL_ERRORS + (pygame.error,)) as exc:
            raise _PageArtUnavailable() from exc
        screen.blit(card, target)

        # Size the icon from the untransformed card so hover reuses the cache.
        face = card_face_rect(UiRect(art.x, art.y, art.width, art.height))
        drawn_face = card_face_rect(UiRect(target.x, target.y, target.width, target.height))
        icon = self._card_face_icon(activity, face.width, pygame)
        screen.blit(
            icon,
            icon.get_rect(
                center=(drawn_face.x + drawn_face.width // 2, drawn_face.y + drawn_face.height // 2)
            ),
        )
        if ring is not None:
            screen.blit(ring, target)

        self._draw_card_title(
            screen,
            rect,
            art,
            self._activity_title_for_shared_card(activity),
            state.selected,
            layout,
            pygame,
        )

        if state.launching:
            from .presentation import _launch_status_label

            text = self._child_display_text(_launch_status_label(self._active_locale))
            badge_font = self._font(max(12, min(18, drawn_face.height // 7)), pygame)
            surface = badge_font.render(text, True, CAPTION_INK)
            badge = pygame.Rect(0, 0, min(target.width, surface.get_width() + 22), surface.get_height() + 10)
            badge.center = (target.centerx, drawn_face.bottom - badge.height // 2)
            pygame.draw.rect(screen, CAPTION_FOCUS, badge, border_radius=badge.height // 2)
            pygame.draw.rect(screen, CAPTION_INK, badge, width=2, border_radius=badge.height // 2)
            screen.blit(surface, surface.get_rect(center=badge.center))

    def _draw_card_title(
        self,
        screen: Any,
        rect: Any,
        art: Any,
        text: str,
        focused: bool,
        layout: CollectionPageLayout,
        pygame: Any,
    ) -> None:
        overhang = layout.labels[0].width - layout.cards[0].width if layout.labels else 0
        slot_top = art.bottom + layout.label_gap
        slot = pygame.Rect(
            rect.x - overhang // 2,
            slot_top,
            rect.width + overhang,
            max(1, rect.bottom - slot_top),
        )
        min_pill = max(22, int(round(layout.label_font_px * 1.25)) + 8)
        title = self._render_activity_label(
            self._child_display_text(text),
            max_width=max(28, slot.width - min_pill // 2 - 10),
            max_height=max(16, slot.height - 4),
            pygame=pygame,
            color=CAPTION_INK,
            preferred_size=layout.label_font_px,
        )
        draw_title_pill(screen, pygame, slot, title, focused=focused, min_height=min_pill)

    def _draw_folder_card(
        self,
        screen: Any,
        rect: Any,
        art: Any,
        target: Any,
        folder: ActivityFolder,
        state: Any,
        layout: CollectionPageLayout,
        pygame: Any,
    ) -> None:
        """Draw a theme folder: manila folder, member icons peeking out, theme
        icon on the flap and a count badge, so it never reads as an Activity."""

        visual_cache = self._visual_cache
        try:
            back = visual_cache.get(FOLDER_ASSET_ID, variant="default", size=target.size)
            front = visual_cache.get(FOLDER_ASSET_ID, variant="front", size=target.size)
            ring = (
                visual_cache.get(FOCUS_ASSET_ID, variant="default", size=target.size)
                if state.selected
                else None
            )
        except (_PAGE_VISUAL_ERRORS + (pygame.error,)) as exc:
            raise _PageArtUnavailable() from exc
        screen.blit(back, target)
        # Up to three members peek out of the folder (sized from the
        # untransformed card so hover reuses the cached icons).
        peek = max(16, int(round(art.width * 0.36)))
        members = folder.items[:3]
        slots = {1: ((0.5, 0.0),), 2: ((0.37, -8.0), (0.63, 8.0))}.get(
            len(members), ((0.29, -10.0), (0.71, 10.0), (0.5, 0.0))
        )
        order = list(zip(members, slots))
        if len(order) == 3:
            # Middle member last so it overlaps its neighbours.
            order = [order[0], order[2], order[1]]
        for member, (fx, angle) in order:
            icon = self._card_face_icon(member, peek, pygame)
            if angle:
                icon = pygame.transform.rotozoom(icon, angle, 1.0)
            lift = 0.05 if fx == 0.5 else 0.0
            center = (
                target.x + int(round(target.width * fx)),
                target.y + int(round(target.height * (0.23 - lift))),
            )
            screen.blit(icon, icon.get_rect(center=center))
        screen.blit(front, target)
        window = int(round(target.width * 102 / 288))
        theme_icon = self._category_shadowed_icon(
            folder.group.icon_id or "backpack",
            max(16, int(round(art.width * 0.31))),
            shadow_alpha=36,
            shadow_offset=max(1, art.width // 90),
            pygame=pygame,
        )
        screen.blit(
            theme_icon,
            theme_icon.get_rect(
                center=(target.centerx, target.y + int(round(target.height * 186 / 304)))
            ),
        )
        if ring is not None:
            screen.blit(ring, target)
        # How many Activities are inside: a sunshine badge on the flap's corner.
        radius = max(10, int(round(window * 0.22)))
        badge_center = (
            target.x + int(round(target.width * 226 / 288)),
            target.y + int(round(target.height * 230 / 304)),
        )
        from pygame import gfxdraw

        gfxdraw.aacircle(screen, badge_center[0], badge_center[1], radius + 3, CAPTION_INK)
        pygame.draw.circle(screen, CAPTION_INK, badge_center, radius + 3)
        pygame.draw.circle(screen, CAPTION_FOCUS, badge_center, radius)
        count = self._category_label_surface(
            str(len(folder.items)), max(12, int(radius * 1.3)), CAPTION_INK, pygame
        )
        screen.blit(count, count.get_rect(center=badge_center))
        self._draw_card_title(
            screen,
            rect,
            art,
            folder.group.title or folder.folder_id,
            state.selected,
            layout,
            pygame,
        )

    def _card_face_icon(self, activity: Any, face_size: int, pygame: Any) -> Any:
        """Return the Activity icon fitted to a card face with its rounded corners.

        Built once per Activity version and size: package icons are either
        rounded tiles or floating objects, and a few are full-bleed squares;
        clipping all of them to the face's rounded square keeps every card
        reading as one family.
        """

        pad = max(2, face_size // 36)
        size = max(16, face_size - 2 * pad)
        key = ("card_face", activity.activity_id, activity.version, size)
        cached = self._decorated_icon_cache.get(key)
        if cached is not None:
            return cached
        raw = self._activity_raw_icon(activity, size, pygame)
        icon = contain_fit_icon_surface(raw, size, pygame, safe_padding_ratio=0.0)
        radius = max(4, int(round(size * CARD_FACE_RADIUS_FRACTION)))
        icon.blit(self._rounded_mask(size, radius, pygame), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self._decorated_icon_cache[key] = icon
        return icon

    def _rounded_mask(self, size: int, radius: int, pygame: Any) -> Any:
        """Anti-aliased rounded-square alpha mask (drawn 4x, scaled down once)."""

        key = (size, radius)
        mask = self._card_mask_cache.get(key)
        if mask is None:
            big = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            pygame.draw.rect(
                big, (255, 255, 255, 255), big.get_rect(), border_radius=radius * 4
            )
            mask = pygame.transform.smoothscale(big, (size, size))
            self._card_mask_cache[key] = mask
        return mask

    # -- paging ---------------------------------------------------------

    def _draw_pagination_and_overflow(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        window: Any,
        columns: int,
        inner_panel: Any = None,
    ) -> None:
        layout = getattr(self, "_collection_page_layout", None)
        if not self._collection_page_active() or layout is None:
            super()._draw_pagination_and_overflow(
                screen, theme, pygame, window, columns, inner_panel
            )
            return
        total = len(self._presented_activities)
        capacity = layout.capacity
        page_count = (total + capacity - 1) // capacity
        if page_count <= 1:
            return
        pointer = self._pointer_pos(pygame)
        pointer_active = self._is_pointer_active(pygame)
        for direction, area, action, enabled in (
            ("previous", layout.previous, "presented_activity_page_prev", window.start > 0),
            ("next", layout.next, "presented_activity_page_next", window.stop < total),
        ):
            if not enabled:
                continue
            rect = pygame.Rect(area.x, area.y, area.width, area.height)
            self._draw_page_arrow_button(
                screen, theme, pygame, direction, rect,
                pointer_active and rect.collidepoint(pointer),
            )
            self._targets.append(HitTarget(action, None, rect))
        self._draw_page_dots(screen, layout, page_count, window.start // capacity, pygame)

    def _draw_page_dots(
        self, screen: Any, layout: CollectionPageLayout, page_count: int, page_index: int, pygame: Any
    ) -> None:
        """Pure visual position: one dot per page, the current one big and in hue."""

        count, active = page_dot_positions(page_count, page_index)
        if count <= 1:
            return
        from pygame import gfxdraw

        radius = layout.dot_radius
        step = radius * 3
        cx0 = layout.dots.x + layout.dots.width // 2 - (count - 1) * step // 2
        cy = layout.dots.y + layout.dots.height // 2
        hue = hue_rgb(self._collection_page_hue())
        for index in range(count):
            cx = cx0 + index * step
            r = int(round(radius * 1.35)) if index == active else radius - 1
            fill = hue if index == active else CAPTION_CREAM
            gfxdraw.filled_circle(screen, cx, cy + 2, r, (205, 186, 150))
            gfxdraw.filled_circle(screen, cx, cy, r, CAPTION_INK)
            gfxdraw.aacircle(screen, cx, cy, r, CAPTION_INK)
            gfxdraw.filled_circle(screen, cx, cy, max(1, r - 2), fill)
            gfxdraw.aacircle(screen, cx, cy, max(1, r - 2), fill)

    def _draw_page_arrow_button(
        self,
        screen: Any,
        theme: Any,
        pygame: Any,
        direction: str,
        rect: Any,
        hovered: bool,
    ) -> None:
        if not self._collection_page_active():
            super()._draw_page_arrow_button(screen, theme, pygame, direction, rect, hovered)
            return
        self._blit_round_button(screen, direction, rect, hovered, pygame)

    # -- shared art helpers ---------------------------------------------

    def _blit_round_button(self, screen: Any, variant: str, rect: Any, hovered: bool, pygame: Any) -> None:
        try:
            art = self._visual_cache.get(
                ROUND_BUTTON_ASSET_ID, variant=round_button_variant(variant), size=rect.size
            )
        except (_PAGE_VISUAL_ERRORS + (pygame.error,)) as exc:
            raise _PageArtUnavailable() from exc
        screen.blit(art, rect.move(0, -3 if hovered else 0))

    def _blit_mini_portal(self, screen: Any, rect: Any, hue: str, icon_id: str, pygame: Any) -> None:
        try:
            art = self._visual_cache.get(PORTAL_ASSET_ID, variant=hue, size=rect.size)
        except (_PAGE_VISUAL_ERRORS + (pygame.error,)) as exc:
            raise _PageArtUnavailable() from exc
        screen.blit(art, rect)
        box = portal_icon_rect(UiRect(rect.x, rect.y, rect.width, rect.height))
        icon = self._category_shadowed_icon(
            icon_id, box.width, shadow_alpha=36, shadow_offset=max(1, box.width // 28), pygame=pygame
        )
        screen.blit(icon, icon.get_rect(center=(box.x + box.width // 2, box.y + box.height // 2)))

"""Presentation renderer for Morbidi Mostriciattoli."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.child_text import display_text
from greia_platform.localization import LocalizedResources
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .monster_art import MonsterArt
    from .monster_content import (
        ACCESSORY_OPTIONS,
        BODY_COLORS,
        BODY_SHAPES,
        EYE_OPTIONS,
        MOUTH_OPTIONS,
        TUFT_OPTIONS,
        Category,
    )
    from .monster_model import (
        MAX_SAVED_PORTRAITS,
        MonsterEditor,
        MonsterGallery,
        MonsterRecipe,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
else:
    from monster_art import MonsterArt
    from monster_content import (
        ACCESSORY_OPTIONS,
        BODY_COLORS,
        BODY_SHAPES,
        EYE_OPTIONS,
        MOUTH_OPTIONS,
        TUFT_OPTIONS,
        Category,
    )
    from monster_model import (
        MAX_SAVED_PORTRAITS,
        MonsterEditor,
        MonsterGallery,
        MonsterRecipe,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )


# Gallery grid: every one of the MAX_SAVED_PORTRAITS (24) saved monsters has a
# visible, hit-testable card (6 columns x 4 rows).
GALLERY_COLUMNS: Final = 6
GALLERY_CARD_SIZE: Final = (150, 108)
GALLERY_ORIGIN: Final = (34, 96)
GALLERY_STRIDE: Final = (162, 118)
GALLERY_THUMB_SIZE: Final = (72, 86)


def gallery_card_rect(index: int) -> pygame.Rect:
    """Screen rectangle of the gallery card for saved-monster ``index``."""
    col, row = index % GALLERY_COLUMNS, index // GALLERY_COLUMNS
    return pygame.Rect(
        GALLERY_ORIGIN[0] + col * GALLERY_STRIDE[0],
        GALLERY_ORIGIN[1] + row * GALLERY_STRIDE[1],
        *GALLERY_CARD_SIZE,
    )


PORTRAIT_CANVAS_RECT: Final[pygame.Rect] = pygame.Rect(70, 96, 460, 400)

SURPRISE_BTN_RECT: Final[pygame.Rect] = pygame.Rect(70, 520, 150, 56)
UNDO_BTN_RECT: Final[pygame.Rect] = pygame.Rect(235, 520, 120, 56)
NAME_BTN_RECT: Final[pygame.Rect] = pygame.Rect(370, 520, 150, 56)
SAVE_BTN_RECT: Final[pygame.Rect] = pygame.Rect(540, 520, 160, 56)
GALLERY_BTN_RECT: Final[pygame.Rect] = pygame.Rect(720, 520, 234, 56)

# Everything in the top row starts clear of the trusted Home/Back region, which
# the platform reserves in full (both slots) so layout never jumps with context.
_TOP_ROW_LEFT: Final[int] = (
    ActivitySystemChromeLayout.for_surface(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    .protected_region.right
    + 8
)
BACK_TO_STUDIO_RECT: Final[pygame.Rect] = pygame.Rect(_TOP_ROW_LEFT, 24, 230, 52)
TAB_START_X: Final[int] = _TOP_ROW_LEFT
TAB_SPACING: Final[int] = 136
TAB_WIDTH: Final[int] = 128
TAB_Y: Final[int] = 20


class MonsterRenderer:
    """Render the studio creator, category tabs, option cards, and saved portrait gallery."""

    def __init__(
        self,
        art: MonsterArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources
        self._thumb_cache: dict[str, pygame.Surface] = {}
        # Localized default names resolve once; a missing resource shows nothing.
        self._default_name = self._resolve("gallery.default_name")
        self._default_name_long = self._resolve("gallery.default_name_long")

    def _fit_render(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: tuple[int, int, int],
        max_width: int,
    ) -> pygame.Surface:
        """Render one line, shrinking (to a floor) so capitals never overflow."""
        while size > 12 and self._typography.measure(text, role, size).width > max_width:
            size -= 1
        return self._typography.render(text, role, size, color)

    def _resolve(self, key: str) -> str:
        try:
            return self._resources.text(key)
        except Exception:
            return ""

    def draw_editor(
        self,
        target: pygame.Surface,
        editor: MonsterEditor,
        *,
        hovered_tab: Category | None = None,
        hovered_option_idx: int | None = None,
        hovered_btn: str | None = None,
        squash_progress: float = 0.0,
    ) -> None:
        target.blit(self._art.background, (0, 0))

        # 1. Top Category Tabs
        self._draw_category_tabs(target, editor.active_category, hovered_tab=hovered_tab)

        # 2. Main Monster Portrait Canvas
        self._draw_monster_canvas(target, editor.recipe, squash_progress=squash_progress)

        # 3. Right Option Cards
        self._draw_option_cards(
            target,
            editor,
            hovered_option_idx=hovered_option_idx,
        )

        # 4. Bottom Toolbar
        self._draw_toolbar(target, editor, hovered_btn=hovered_btn)

    def draw_gallery(
        self,
        target: pygame.Surface,
        gallery: MonsterGallery,
        *,
        hovered_idx: int | None = None,
        selected_portrait_id: str | None = None,
        confirm_delete: bool = False,
        hovered_btn: str | None = None,
    ) -> None:
        target.blit(self._art.background, (0, 0))

        # Top Return Button
        b_draw = BACK_TO_STUDIO_RECT.move(0, -4) if (hovered_btn == "back") else BACK_TO_STUDIO_RECT
        pygame.draw.rect(target, (10, 14, 28), BACK_TO_STUDIO_RECT.move(0, 6), border_radius=22)
        pygame.draw.rect(target, (2, 132, 199), b_draw, border_radius=22)
        b_border = (56, 189, 248) if (hovered_btn == "back") else (255, 255, 255)
        pygame.draw.rect(target, b_border, b_draw, width=3, border_radius=22)

        b_txt = self._fit_render(
            self._resources.text("button.back"),
            FontRole.TITLE,
            20,
            (255, 255, 255),
            BACK_TO_STUDIO_RECT.width - 28,
        )
        target.blit(
            b_txt,
            (
                b_draw.centerx - b_txt.get_width() // 2,
                b_draw.centery - b_txt.get_height() // 2,
            ),
        )

        # Gallery Title Badge
        header = f"{self._resources.text('button.gallery')} ({gallery.count}/{MAX_SAVED_PORTRAITS})"
        h_surf = self._typography.render(header, FontRole.TITLE, 24, (254, 240, 138))
        header_x = max(
            REFERENCE_WIDTH // 2 - h_surf.get_width() // 2,
            BACK_TO_STUDIO_RECT.right + 16,
        )
        target.blit(h_surf, (header_x, 34))

        if gallery.count == 0:
            empty_txt = self._typography.render(self._resources.text("gallery.empty"), FontRole.BODY, 24, (148, 163, 184))
            target.blit(empty_txt, (REFERENCE_WIDTH // 2 - empty_txt.get_width() // 2, 280))
            return

        # Grid of saved monsters (6 columns x 4 rows = all 24 slots)
        for i, recipe in enumerate(gallery.recipes[:MAX_SAVED_PORTRAITS]):
            card_rect = gallery_card_rect(i)
            is_hovered = (i == hovered_idx)

            # Drop shadow
            pygame.draw.rect(target, (10, 14, 28, 90), card_rect.move(0, 6), border_radius=18)
            pygame.draw.rect(target, (15, 23, 42), card_rect, border_radius=18)
            border_c = (56, 189, 248) if is_hovered else (51, 65, 85)
            pygame.draw.rect(target, border_c, card_rect, width=3, border_radius=18)

            # Thumbnail
            thumb = self._get_thumbnail(recipe)
            target.blit(thumb, (card_rect.left + 6, card_rect.top + (card_rect.height - thumb.get_height()) // 2))

            # Name / Label
            name_str = display_text(recipe.name if recipe.name else self._default_name)
            name_surf = self._fit_render(
                name_str[:12], FontRole.TITLE, 15, (254, 240, 138),
                card_rect.right - (card_rect.left + 6 + GALLERY_THUMB_SIZE[0] + 6) - 8,
            )
            target.blit(
                name_surf,
                (card_rect.left + 6 + GALLERY_THUMB_SIZE[0] + 6, card_rect.centery - name_surf.get_height() // 2),
            )

        # Modal preview if selected
        if selected_portrait_id is not None:
            sel = gallery.get(selected_portrait_id)
            if sel is not None:
                self._draw_modal_preview(target, sel, confirm_delete=confirm_delete, hovered_btn=hovered_btn)

    def clear_thumbnail_cache(self) -> None:
        self._thumb_cache.clear()

    def _get_thumbnail(self, recipe: MonsterRecipe) -> pygame.Surface:
        if recipe.portrait_id not in self._thumb_cache:
            if len(self._thumb_cache) >= MAX_SAVED_PORTRAITS:
                # Evict oldest
                self._thumb_cache.pop(next(iter(self._thumb_cache)))
            full = pygame.Surface((100, 120), pygame.SRCALPHA)
            self._art.draw_monster(full, pygame.Rect(0, 0, 100, 120), recipe)
            # Rendered once and cached at the card's size (no per-frame scaling).
            surf = pygame.transform.smoothscale(full, GALLERY_THUMB_SIZE)
            self._thumb_cache[recipe.portrait_id] = surf
        return self._thumb_cache[recipe.portrait_id]

    def _draw_category_tabs(
        self,
        target: pygame.Surface,
        active_cat: Category,
        *,
        hovered_tab: Category | None = None,
    ) -> None:
        categories = list(Category)
        for i, cat in enumerate(categories):
            tab_rect = pygame.Rect(TAB_START_X + i * TAB_SPACING, TAB_Y, TAB_WIDTH, 56)
            is_active = (cat == active_cat)
            is_hovered = (cat == hovered_tab)

            t_draw = tab_rect.move(0, -4) if (is_hovered or is_active) else tab_rect
            pygame.draw.rect(target, (10, 14, 28), tab_rect.move(0, 6), border_radius=18)

            bg_col = (147, 51, 234) if is_active else (30, 41, 59)
            border_col = (254, 240, 138) if is_active else ((56, 189, 248) if is_hovered else (71, 85, 105))
            pygame.draw.rect(target, bg_col, t_draw, border_radius=18)
            pygame.draw.rect(target, border_col, t_draw, width=3, border_radius=18)

            cat_symbols = {
                Category.BODY_SHAPE: "⚪",
                Category.BODY_COLOR: "🎨",
                Category.EYES: "👀",
                Category.MOUTH: "👄",
                Category.TUFT: "🦄",
                Category.ACCESSORY: "🎀",
            }
            sym = cat_symbols.get(cat, "✨")
            txt_surf = self._typography.render(sym, FontRole.DISPLAY, 32, (255, 255, 255))
            target.blit(
                txt_surf,
                (
                    t_draw.centerx - txt_surf.get_width() // 2,
                    t_draw.centery - txt_surf.get_height() // 2,
                ),
            )

    def _draw_monster_canvas(
        self,
        target: pygame.Surface,
        recipe: MonsterRecipe,
        *,
        squash_progress: float = 0.0,
    ) -> None:
        # Easel photo frame
        pygame.draw.rect(target, (10, 14, 28, 90), PORTRAIT_CANVAS_RECT.move(0, 8), border_radius=28)
        pygame.draw.rect(target, (15, 23, 42, 220), PORTRAIT_CANVAS_RECT, border_radius=28)
        pygame.draw.rect(target, (217, 119, 6), PORTRAIT_CANVAS_RECT, width=4, border_radius=28)
        pygame.draw.rect(target, (254, 240, 138), PORTRAIT_CANVAS_RECT.inflate(-8, -8), width=1, border_radius=24)

        # Name banner at top of canvas if named
        if recipe.name:
            n_surf = self._typography.render(display_text(recipe.name), FontRole.TITLE, 22, (254, 240, 138))
            n_rect = pygame.Rect(PORTRAIT_CANVAS_RECT.centerx - n_surf.get_width() // 2 - 16, PORTRAIT_CANVAS_RECT.top + 14, n_surf.get_width() + 32, 34)
            pygame.draw.rect(target, (30, 41, 59), n_rect, border_radius=14)
            pygame.draw.rect(target, (217, 119, 6), n_rect, width=2, border_radius=14)
            target.blit(n_surf, (PORTRAIT_CANVAS_RECT.centerx - n_surf.get_width() // 2, PORTRAIT_CANVAS_RECT.top + 18))

        # Monster
        monster_area = pygame.Rect(PORTRAIT_CANVAS_RECT.left + 30, PORTRAIT_CANVAS_RECT.top + 40, PORTRAIT_CANVAS_RECT.width - 60, PORTRAIT_CANVAS_RECT.height - 60)
        self._art.draw_monster(target, monster_area, recipe, squash_progress=squash_progress)

    def _draw_option_cards(
        self,
        target: pygame.Surface,
        editor: MonsterEditor,
        *,
        hovered_option_idx: int | None = None,
    ) -> None:
        cat = editor.active_category
        options = self._get_options_for_category(cat)

        for i, opt in enumerate(options[:8]):
            row = i // 3
            col = i % 3
            card_rect = pygame.Rect(560 + col * 132, 96 + row * 132, 116, 116)
            is_hovered = (i == hovered_option_idx)
            is_selected = self._is_option_selected(editor.recipe, cat, opt)

            draw_rect = card_rect.move(0, -6) if (is_hovered or is_selected) else card_rect

            # Drop shadow
            pygame.draw.rect(target, (10, 14, 28, 80), card_rect.move(0, 6), border_radius=22)

            bg_col = (255, 251, 235) if cat != Category.BODY_COLOR else opt.primary_color
            border_col = (56, 189, 248) if is_selected else ((251, 191, 36) if is_hovered else (71, 85, 105))
            border_w = 4 if (is_selected or is_hovered) else 2

            pygame.draw.rect(target, bg_col, draw_rect, border_radius=22)
            pygame.draw.rect(target, border_col, draw_rect, width=border_w, border_radius=22)

            # Option symbol
            sym_surf = self._typography.render(opt.symbol, FontRole.DISPLAY, 48, (255, 255, 255))
            target.blit(
                sym_surf,
                (
                    draw_rect.centerx - sym_surf.get_width() // 2,
                    draw_rect.centery - sym_surf.get_height() // 2,
                ),
            )

    def _draw_toolbar(
        self,
        target: pygame.Surface,
        editor: MonsterEditor,
        *,
        hovered_btn: str | None = None,
    ) -> None:
        # 1. Surprise
        self._draw_btn(target, SURPRISE_BTN_RECT, self._resources.text("button.surprise"), (234, 88, 12), is_hovered=(hovered_btn == "surprise"))
        # 2. Undo
        can_undo = editor.can_undo()
        self._draw_btn(target, UNDO_BTN_RECT, self._resources.text("button.undo"), (100, 116, 139) if not can_undo else (71, 85, 105), is_hovered=(hovered_btn == "undo" and can_undo), enabled=can_undo)
        # 3. Name
        self._draw_btn(target, NAME_BTN_RECT, self._resources.text("button.name"), (147, 51, 234), is_hovered=(hovered_btn == "name"))
        # 4. Save
        self._draw_btn(target, SAVE_BTN_RECT, self._resources.text("button.save"), (22, 163, 74), is_hovered=(hovered_btn == "save"))
        # 5. Gallery
        self._draw_btn(target, GALLERY_BTN_RECT, self._resources.text("button.gallery"), (2, 132, 199), is_hovered=(hovered_btn == "gallery"))

    def _draw_btn(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        bg_col: tuple[int, int, int],
        *,
        is_hovered: bool = False,
        enabled: bool = True,
    ) -> None:
        draw_rect = rect.move(0, -4) if (is_hovered and enabled) else rect
        pygame.draw.rect(target, (10, 14, 28), rect.move(0, 6), border_radius=20)
        pygame.draw.rect(target, bg_col, draw_rect, border_radius=20)
        border_c = (56, 189, 248) if (is_hovered and enabled) else (255, 255, 255)
        pygame.draw.rect(target, border_c, draw_rect, width=3, border_radius=20)

        # Highlight line
        if enabled:
            hl = draw_rect.inflate(-16, -draw_rect.height + 8).move(0, -draw_rect.height // 2 + 8)
            pygame.draw.rect(target, (255, 255, 255, 90), hl, border_radius=4)

        txt_surf = self._fit_render(
            label, FontRole.TITLE, 18, (255, 255, 255), rect.width - 24
        )
        target.blit(
            txt_surf,
            (
                draw_rect.centerx - txt_surf.get_width() // 2,
                draw_rect.centery - txt_surf.get_height() // 2,
            ),
        )

    def _draw_modal_preview(
        self,
        target: pygame.Surface,
        recipe: MonsterRecipe,
        *,
        confirm_delete: bool = False,
        hovered_btn: str | None = None,
    ) -> None:
        overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 28, 200))
        target.blit(overlay, (0, 0))

        modal_rect = pygame.Rect(260, 60, 504, 480)
        pygame.draw.rect(target, (15, 23, 42), modal_rect, border_radius=28)
        pygame.draw.rect(target, (217, 119, 6), modal_rect, width=4, border_radius=28)

        # Monster drawing
        m_area = pygame.Rect(modal_rect.left + 50, modal_rect.top + 30, modal_rect.width - 100, 300)
        self._art.draw_monster(target, m_area, recipe)

        # Name
        name_str = display_text(recipe.name if recipe.name else self._default_name_long)
        n_surf = self._typography.render(name_str, FontRole.TITLE, 24, (254, 240, 138))
        target.blit(n_surf, (modal_rect.centerx - n_surf.get_width() // 2, modal_rect.top + 340))

        # Action buttons
        del_rect = pygame.Rect(modal_rect.centerx - 110, modal_rect.bottom - 70, 220, 50)
        self._draw_btn(target, del_rect, self._resources.text("button.delete"), (225, 29, 72), is_hovered=(hovered_btn == "delete"))

    def tab_at(self, point: tuple[int, int]) -> Category | None:
        categories = list(Category)
        for i, cat in enumerate(categories):
            tab_rect = pygame.Rect(TAB_START_X + i * TAB_SPACING, TAB_Y, TAB_WIDTH, 56)
            if tab_rect.collidepoint(point):
                return cat
        return None

    def option_at(self, point: tuple[int, int], category: Category) -> int | None:
        options = self._get_options_for_category(category)
        for i in range(len(options)):
            row = i // 3
            col = i % 3
            card_rect = pygame.Rect(560 + col * 132, 96 + row * 132, 116, 116)
            if card_rect.collidepoint(point):
                return i
        return None

    def button_at(self, point: tuple[int, int]) -> str | None:
        if SURPRISE_BTN_RECT.collidepoint(point):
            return "surprise"
        if UNDO_BTN_RECT.collidepoint(point):
            return "undo"
        if NAME_BTN_RECT.collidepoint(point):
            return "name"
        if SAVE_BTN_RECT.collidepoint(point):
            return "save"
        if GALLERY_BTN_RECT.collidepoint(point):
            return "gallery"
        return None

    def gallery_card_at(self, point: tuple[int, int], count: int) -> int | None:
        for i in range(min(MAX_SAVED_PORTRAITS, count)):
            if gallery_card_rect(i).collidepoint(point):
                return i
        return None

    def back_to_studio_contains(self, point: tuple[int, int]) -> bool:
        return BACK_TO_STUDIO_RECT.collidepoint(point)

    def modal_delete_contains(self, point: tuple[int, int]) -> bool:
        del_rect = pygame.Rect(512 - 110, 470, 220, 50)
        return del_rect.collidepoint(point)

    def _get_options_for_category(self, category: Category):
        if category == Category.BODY_SHAPE:
            return BODY_SHAPES
        if category == Category.BODY_COLOR:
            return BODY_COLORS
        if category == Category.EYES:
            return EYE_OPTIONS
        if category == Category.MOUTH:
            return MOUTH_OPTIONS
        if category == Category.TUFT:
            return TUFT_OPTIONS
        return ACCESSORY_OPTIONS

    def _is_option_selected(self, recipe: MonsterRecipe, category: Category, option) -> bool:
        if category == Category.BODY_SHAPE:
            return recipe.body_shape == option.option_id
        if category == Category.BODY_COLOR:
            return recipe.body_color == option.option_id
        if category == Category.EYES:
            return recipe.eyes == option.option_id
        if category == Category.MOUTH:
            return recipe.mouth == option.option_id
        if category == Category.TUFT:
            return recipe.tuft == option.option_id
        return recipe.accessory == option.option_id

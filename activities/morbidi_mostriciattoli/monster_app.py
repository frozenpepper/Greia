"""Interactive application loop for Morbidi Mostriciattoli."""

from __future__ import annotations

from enum import StrEnum
import random
import time
from typing import Final

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import GreiaTypography

if __package__:
    from .monster_audio import MonsterAudio
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
        MonsterEditor,
        MonsterGallery,
        MonsterRecipe,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
    from .monster_renderer import MonsterRenderer
    from .monster_services import GreiaMonsterEvents, GreiaMonsterStorage
else:
    from monster_audio import MonsterAudio
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
        MonsterEditor,
        MonsterGallery,
        MonsterRecipe,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
    from monster_renderer import MonsterRenderer
    from monster_services import GreiaMonsterEvents, GreiaMonsterStorage


class ViewMode(StrEnum):
    STUDIO = "studio"
    GALLERY = "gallery"
    NAME_DIALOG = "name_dialog"


def _is_safe_point(screen: pygame.Surface, pos: tuple[int, int]) -> bool:
    """Platform Home/Back belongs to trusted chrome; the Activity must not exit for it."""
    viewport = activity_viewport_for_surface(screen)
    x, y = pos
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    return not any(
        r.x <= x < r.right and r.y <= y < r.bottom
        for r in viewport.protected_regions
    )


class MonsterActivity:
    """Cute soft monster creator application."""

    def __init__(
        self,
        screen: pygame.Surface,
        renderer: MonsterRenderer,
        audio: MonsterAudio,
        events: GreiaMonsterEvents,
        storage: GreiaMonsterStorage,
        *,
        rng: random.Random | None = None,
        clock=time.monotonic,
    ) -> None:
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        self.renderer = renderer
        self.audio = audio
        self.events = events
        self.storage = storage
        self.rng = rng or random.Random()
        self.clock = clock

        self.editor = MonsterEditor()
        self.gallery = storage.load_gallery()
        self.view_mode = ViewMode.STUDIO
        self.selected_portrait_id: str | None = None

        self._running = True
        self._ready_published = False
        self._dirty = True

        self._hovered_tab: Category | None = None
        self._hovered_option: int | None = None
        self._hovered_btn: str | None = None
        self._hovered_gallery_card: int | None = None

        self._squash_start: float | None = None
        self._name_input: str = ""

    def run(self) -> int:
        ticker = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            for event in pygame.event.get():
                self._handle_event(event)

            if self._advance_animation():
                self._dirty = True

            if self._dirty:
                self._render()
                self.canvas.present()
                pygame.display.flip()
                self._dirty = False
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True

            ticker.tick(30)
        return 0

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.selected_portrait_id is not None:
                self.selected_portrait_id = None
                self._dirty = True
            elif self.view_mode == ViewMode.GALLERY:
                self.view_mode = ViewMode.STUDIO
                self.renderer.clear_thumbnail_cache()
                self._dirty = True
            else:
                self._running = False
            return

        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.canvas = PygameReferenceCanvas(self.screen)
            self._dirty = True
            return

        if event.type == pygame.MOUSEMOTION:
            if not _is_safe_point(self.screen, event.pos):
                return
            logical = self.canvas.pointer(event.pos)
            if logical is not None:
                point = (int(logical[0]), int(logical[1]))
                if self.view_mode == ViewMode.STUDIO:
                    new_tab = self.renderer.tab_at(point)
                    new_opt = self.renderer.option_at(point, self.editor.active_category)
                    new_btn = self.renderer.button_at(point)
                    if new_tab != self._hovered_tab or new_opt != self._hovered_option or new_btn != self._hovered_btn:
                        self._hovered_tab = new_tab
                        self._hovered_option = new_opt
                        self._hovered_btn = new_btn
                        self._dirty = True
                elif self.view_mode == ViewMode.GALLERY:
                    new_card = self.renderer.gallery_card_at(point, self.gallery.count)
                    new_back = "back" if self.renderer.back_to_studio_contains(point) else (
                        "delete" if (self.selected_portrait_id and self.renderer.modal_delete_contains(point)) else None
                    )
                    if new_card != self._hovered_gallery_card or new_back != self._hovered_btn:
                        self._hovered_gallery_card = new_card
                        self._hovered_btn = new_back
                        self._dirty = True
            return

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button != 1:
                return
            position = getattr(event, "pos", None)
            if position is None:
                width, height = self.screen.get_size()
                position = (int(event.x * width), int(event.y * height))
            if not _is_safe_point(self.screen, position):
                return
            logical = self.canvas.pointer(position)
            if logical is not None:
                point = (int(logical[0]), int(logical[1]))
                if self._handle_pointer(point):
                    self._dirty = True

    def _handle_pointer(self, point: tuple[int, int]) -> bool:
        if self.view_mode == ViewMode.STUDIO:
            # 1. Category Tab
            tab = self.renderer.tab_at(point)
            if tab is not None:
                self.editor.select_category(tab)
                self.audio.play("tap")
                return True

            # 2. Option Card
            opt_idx = self.renderer.option_at(point, self.editor.active_category)
            if opt_idx is not None:
                options = self.renderer._get_options_for_category(self.editor.active_category)
                if opt_idx < len(options):
                    opt = options[opt_idx]
                    if self.editor.apply_option(opt.option_id):
                        self._squash_start = self.clock()
                        self.audio.play("squash" if self.editor.active_category in {Category.BODY_SHAPE, Category.BODY_COLOR} else "pop")
                        return True

            # 3. Toolbar Buttons
            btn = self.renderer.button_at(point)
            if btn == "surprise":
                if self.editor.surprise_me(self.rng):
                    self._squash_start = self.clock()
                    self.audio.play("surprise")
                    return True
            elif btn == "undo":
                if self.editor.undo():
                    self._squash_start = self.clock()
                    self.audio.play("pop")
                    return True
            elif btn == "name":
                # Preset name cycle for toddler accessibility
                names = ["Bubu", "Puffo", "Zuzu", "Mimi", "Pippo", "Lulù", "Totò", "Kiki", ""]
                curr_idx = names.index(self.editor.recipe.name) if self.editor.recipe.name in names else -1
                next_name = names[(curr_idx + 1) % len(names)]
                self.editor.set_name(next_name)
                self.audio.play("tap")
                return True
            elif btn == "save":
                # Save portrait
                if not self.gallery.is_full:
                    recipe_to_save = self.editor.recipe
                    candidate = MonsterGallery(self.gallery.recipes)
                    if not candidate.add(recipe_to_save):
                        return False
                    # Commit storage first. A failed save must leave the
                    # editor/visible gallery unchanged and must not award a creation.
                    if not self.storage.save_gallery(candidate):
                        return False
                    self.gallery = candidate
                    self.events.portrait_created(recipe_to_save.portrait_id, recipe_to_save)
                    self.audio.play("save")
                    self.editor = MonsterEditor()
                    return True
            elif btn == "gallery":
                self.view_mode = ViewMode.GALLERY
                self.selected_portrait_id = None
                self.audio.play("tap")
                return True

        elif self.view_mode == ViewMode.GALLERY:
            if self.selected_portrait_id is not None:
                if self.renderer.modal_delete_contains(point):
                    candidate = MonsterGallery(self.gallery.recipes)
                    if not candidate.delete(self.selected_portrait_id):
                        return False
                    # Only remove the selected portrait from the visible gallery
                    # after its new durable catalogue has committed.
                    if not self.storage.save_gallery(candidate):
                        return False
                    self.gallery = candidate
                    self.selected_portrait_id = None
                    self.renderer.clear_thumbnail_cache()
                    self.audio.play("pop")
                    return True
                else:
                    # Dismiss modal
                    self.selected_portrait_id = None
                    return True

            if self.renderer.back_to_studio_contains(point):
                self.view_mode = ViewMode.STUDIO
                self.renderer.clear_thumbnail_cache()
                self.audio.play("tap")
                return True

            card_idx = self.renderer.gallery_card_at(point, self.gallery.count)
            if card_idx is not None and card_idx < self.gallery.count:
                self.selected_portrait_id = self.gallery.recipes[card_idx].portrait_id
                self.audio.play("tap")
                return True

        return False

    def _advance_animation(self) -> bool:
        if self._squash_start is not None:
            if (self.clock() - self._squash_start) >= 0.25:
                self._squash_start = None
                return True
            return True
        return False

    def _render(self) -> None:
        squash_prog = 0.0
        if self._squash_start is not None:
            squash_prog = min(1.0, (self.clock() - self._squash_start) / 0.25)

        if self.view_mode == ViewMode.STUDIO:
            self.renderer.draw_editor(
                self.canvas.surface,
                self.editor,
                hovered_tab=self._hovered_tab,
                hovered_option_idx=self._hovered_option,
                hovered_btn=self._hovered_btn,
                squash_progress=squash_prog,
            )
        elif self.view_mode == ViewMode.GALLERY:
            self.renderer.draw_gallery(
                self.canvas.surface,
                self.gallery,
                hovered_idx=self._hovered_gallery_card,
                selected_portrait_id=self.selected_portrait_id,
                hovered_btn=self._hovered_btn,
            )

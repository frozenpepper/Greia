"""App lifecycle and interaction orchestration for Tre Carte Una Storia."""

from __future__ import annotations

from enum import StrEnum
import random
import time
from typing import Callable

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.activity_ui import is_home_clicked
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.typography import GreiaTypography

if __package__:
    from .story_cards_audio import StoryAudio
    from .story_cards_content import STORY_SEEDS, StorySeed
    from .story_cards_model import (
        SavedStory,
        StoryLibrary,
        StoryRound,
        StoryStage,
        create_shuffled_round,
    )
    from .story_cards_renderer import StoryRenderer
    from .story_cards_services import EventPort, StoragePort
else:
    from story_cards_audio import StoryAudio
    from story_cards_content import STORY_SEEDS, StorySeed
    from story_cards_model import (
        SavedStory,
        StoryLibrary,
        StoryRound,
        StoryStage,
        create_shuffled_round,
    )
    from story_cards_renderer import StoryRenderer
    from story_cards_services import EventPort, StoragePort


class ViewMode(StrEnum):
    PUZZLE = "puzzle"
    GALLERY = "gallery"
    FULL_DIALOG = "full_dialog"


class StoryActivity:
    """Coordinate story ordering puzzle, caption composition, storage, and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        round_state: StoryRound,
        library: StoryLibrary,
        renderer: StoryRenderer,
        typography: GreiaTypography,
        resources,
        storage: StoragePort,
        events: EventPort,
        audio: StoryAudio,
        rng: random.Random,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.round_state = round_state
        self.library = library
        self.renderer = renderer
        self.typography = typography
        self.resources = resources
        self.storage = storage
        self.events = events
        self.audio = audio
        self.rng = rng
        self.session_id = session_id
        self.clock = clock

        self.view_mode = ViewMode.PUZZLE
        self.selected_gallery_story_id: str | None = None
        self.confirm_delete = False
        self._seed_index = 0
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._last_blink = clock()
        self._cursor_visible = True
        self._focused_slot = 0

    def run(self) -> int:
        ticker = pygame.time.Clock()
        pygame.key.start_text_input()

        while self._running and not activity_stop_requested():
            now = self.clock()
            if now - self._last_blink >= 0.5:
                self._cursor_visible = not self._cursor_visible
                self._last_blink = now
                if self.view_mode == ViewMode.PUZZLE and self.round_state.stage == StoryStage.CAPTION:
                    self._dirty = True

            for event in pygame.event.get():
                self._handle_event(event)

            if self._dirty:
                self._render()
                self.canvas.present()
                pygame.display.flip()
                self._dirty = False
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
                    self.audio.play_welcome()

            ticker.tick(20)

        pygame.key.stop_text_input()
        return 0

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.view_mode == ViewMode.GALLERY:
                if self.selected_gallery_story_id is not None:
                    self.selected_gallery_story_id = None
                    self.confirm_delete = False
                else:
                    self.view_mode = ViewMode.PUZZLE
                self._dirty = True
                return
            elif self.view_mode == ViewMode.FULL_DIALOG:
                self.view_mode = ViewMode.PUZZLE
                self._dirty = True
                return
            else:
                self._running = False
                return

        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.canvas = PygameReferenceCanvas(self.screen)
            self._dirty = True
            return

        if self.view_mode == ViewMode.PUZZLE:
            if self.round_state.stage == StoryStage.SEQUENCE:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self._focused_slot = (self._focused_slot - 1) % 3
                        self.round_state.select_slot(self._focused_slot)
                        self.audio.play("select")
                        self._dirty = True
                    elif event.key == pygame.K_RIGHT:
                        self._focused_slot = (self._focused_slot + 1) % 3
                        self.round_state.select_slot(self._focused_slot)
                        self.audio.play("select")
                        self._dirty = True
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self._check_order()
                        self._dirty = True
                    elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                        slot_idx = event.key - pygame.K_1
                        self.round_state.select_slot(slot_idx)
                        self.audio.play("card_swap")
                        self._dirty = True
            else:  # CAPTION Stage
                if event.type == pygame.TEXTINPUT:
                    if self.round_state.insert_custom(event.text):
                        self.audio.play("select")
                        self._cursor_visible = True
                        self._last_blink = self.clock()
                        self._dirty = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        if self.round_state.backspace_custom():
                            self.audio.play("select")
                            self._cursor_visible = True
                            self._last_blink = self.clock()
                            self._dirty = True
                    elif event.key == pygame.K_DELETE:
                        if self.round_state.delete_custom_forward():
                            self.audio.play("select")
                            self._cursor_visible = True
                            self._last_blink = self.clock()
                            self._dirty = True
                    elif event.key == pygame.K_LEFT:
                        if self.round_state.move_cursor_left():
                            self._cursor_visible = True
                            self._last_blink = self.clock()
                            self._dirty = True
                    elif event.key == pygame.K_RIGHT:
                        if self.round_state.move_cursor_right():
                            self._cursor_visible = True
                            self._last_blink = self.clock()
                            self._dirty = True
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and (event.mod & pygame.KMOD_CTRL):
                        self._save_story()
                        self._dirty = True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._handle_pointer(event.pos):
                self._dirty = True

    def _handle_pointer(self, raw_pos: tuple[int, int]) -> bool:
        if is_home_clicked(self.screen, raw_pos):
            self._running = False
            return False
        if not _safe_point(self.screen, raw_pos):
            return False
        logical = self.canvas.pointer(raw_pos)
        if logical is None:
            return False
        point = (int(logical[0]), int(logical[1]))

        if self.view_mode == ViewMode.FULL_DIALOG:
            self.view_mode = ViewMode.PUZZLE
            return True

        if self.view_mode == ViewMode.GALLERY:
            return self._handle_gallery_pointer(point)

        # Puzzle mode pointer handling
        if self.round_state.stage == StoryStage.SEQUENCE:
            # Replay instructions / Mascot tap
            if self.renderer.listen_contains(point):
                self.audio.play_welcome()
                return True

            # Tap Card Slot
            slot_idx = self.renderer.slot_at(point)
            if slot_idx is not None:
                self.round_state.select_slot(slot_idx)
                self.audio.play("card_swap")
                self.audio.play_slot(slot_idx)
                return True

            # Check Order Button
            if self.renderer.check_contains(point):
                self._check_order()
                return True

            # Gallery Button
            if self.renderer.gallery_contains(point):
                self.view_mode = ViewMode.GALLERY
                self.selected_gallery_story_id = None
                self.confirm_delete = False
                self.audio.play("select")
                return True
        else:  # Caption Stage
            # Preset Caption tap (sets and reads aloud)
            p_idx = self.renderer.caption_preset_at(point)
            if p_idx is not None:
                self.round_state.set_preset_caption(p_idx)
                self.audio.play("select")
                self.audio.play_story_sentence(self.round_state.seed.seed_id, p_idx)
                return True

            # Custom Caption box tap
            if self.renderer.custom_caption_contains(point):
                self.round_state.set_custom_mode()
                self._cursor_visible = True
                self._last_blink = self.clock()
                self.audio.play("select")
                return True

            # Save Button
            if self.renderer.save_contains(point):
                self._save_story()
                return True

        return False

    def _handle_gallery_pointer(self, point: tuple[int, int]) -> bool:
        # Return to Game / New Story
        if self.renderer.back_to_game_contains(point):
            self.view_mode = ViewMode.PUZZLE
            self.selected_gallery_story_id = None
            self.confirm_delete = False
            self.audio.play("select")
            return True

        # Story Modal open
        if self.selected_gallery_story_id is not None:
            if self.confirm_delete:
                if self.renderer.delete_btn_rect().collidepoint(point):
                    self.library.delete(self.selected_gallery_story_id)
                    self.storage.save(self.library)
                    self.selected_gallery_story_id = None
                    self.confirm_delete = False
                    self.audio.play("delete")
                    return True
                elif self.renderer.cancel_btn_rect().collidepoint(point):
                    self.confirm_delete = False
                    self.audio.play("select")
                    return True
            else:
                if self.renderer.delete_btn_rect().collidepoint(point):
                    self.confirm_delete = True
                    self.audio.play("select")
                    return True
                elif self.renderer.cancel_btn_rect().collidepoint(point):
                    self.selected_gallery_story_id = None
                    self.confirm_delete = False
                    self.audio.play("select")
                    return True
            return True

        # Grid story item tap
        idx = self.renderer.gallery_item_at(point, self.library.count)
        if idx is not None:
            story = self.library.stories[idx]
            self.selected_gallery_story_id = story.story_id
            self.confirm_delete = False
            self.audio.play("select")
            return True

        return False

    def _check_order(self) -> None:
        if self.round_state.check_sequence():
            self.events.sequence_completed(self.round_state.seed)
            self.audio.play_feedback(True)
        else:
            self.audio.play_feedback(False)

    def _save_story(self) -> None:
        if self.library.is_full:
            self.audio.play("full")
            self.view_mode = ViewMode.FULL_DIALOG
            return

        story_id = f"story-{int(time.time())}-{self.rng.randrange(1_000_000):06d}"

        # Determine caption text
        if self.round_state.caption_mode == "custom":
            caption = self.round_state.custom_caption if self.round_state.custom_caption else self.resources.text(self.round_state.seed.caption_keys[0])
            mode = "custom"
        else:
            preset_idx = int(self.round_state.caption_mode.split("_")[-1])
            caption = self.resources.text(self.round_state.seed.caption_keys[preset_idx])
            mode = self.round_state.caption_mode

        saved_story = SavedStory(
            story_id=story_id,
            created_at=int(time.time()),
            seed_id=self.round_state.seed.seed_id,
            card_ids=tuple(c.card_id for c in self.round_state.current_order),  # type: ignore[arg-type]
            caption_mode=mode,
            caption_text=caption,
        )

        # 1. Add to in-memory library
        self.library.add(saved_story)

        # 2. Write to storage FIRST
        saved = self.storage.save(self.library)
        if not saved:
            self.library.delete(story_id)
            return

        # 3. Emit creation event ONLY after successful storage save
        self.events.story_created(saved_story)
        self.audio.play("save")

        # 4. Advance to next story seed
        self._seed_index = (self._seed_index + 1) % len(STORY_SEEDS)
        next_seed = STORY_SEEDS[self._seed_index]
        self.round_state = create_shuffled_round(next_seed, self.rng)

    def _render(self) -> None:
        if self.view_mode == ViewMode.FULL_DIALOG:
            self.renderer.draw_round(
                self.canvas.surface,
                self.round_state,
                self.library,
                cursor_visible=False,
            )
            self.renderer.draw_full_dialog(self.canvas.surface)
        elif self.view_mode == ViewMode.GALLERY:
            self.renderer.draw_gallery(
                self.canvas.surface,
                self.library,
                selected_story_id=self.selected_gallery_story_id,
                confirm_delete=self.confirm_delete,
            )
        else:
            self.renderer.draw_round(
                self.canvas.surface,
                self.round_state,
                self.library,
                cursor_visible=self._cursor_visible,
            )


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True

"""App lifecycle and interaction orchestration for Posta di Leo."""

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
    from .postcard_audio import PostcardAudio
    from .postcard_content import RECIPIENTS, STAMPS
    from .postcard_model import (
        MAX_SAVED_CARDS,
        PostcardDraft,
        PostcardLibrary,
        SavedPostcard,
    )
    from .postcard_renderer import PostcardRenderer
    from .postcard_services import EventPort, StoragePort
else:
    from postcard_audio import PostcardAudio
    from postcard_content import RECIPIENTS, STAMPS
    from postcard_model import (
        MAX_SAVED_CARDS,
        PostcardDraft,
        PostcardLibrary,
        SavedPostcard,
    )
    from postcard_renderer import PostcardRenderer
    from postcard_services import EventPort, StoragePort


class ViewMode(StrEnum):
    EDITOR = "editor"
    GALLERY = "gallery"
    FULL_DIALOG = "full_dialog"


class PostcardActivity:
    """Coordinate postcard composer, storage, events, and Greia lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        draft: PostcardDraft,
        library: PostcardLibrary,
        renderer: PostcardRenderer,
        typography: GreiaTypography,
        resources,
        storage: StoragePort,
        events: EventPort,
        audio: PostcardAudio,
        rng: random.Random,
        session_id: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.draft = draft
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

        self.view_mode = ViewMode.EDITOR
        self.selected_gallery_card_id: str | None = None
        self.confirm_delete = False
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._last_blink = clock()
        self._cursor_visible = True

    def run(self) -> int:
        ticker = pygame.time.Clock()
        pygame.key.start_text_input()

        while self._running and not activity_stop_requested():
            now = self.clock()
            if now - self._last_blink >= 0.5:
                self._cursor_visible = not self._cursor_visible
                self._last_blink = now
                if self.view_mode == ViewMode.EDITOR:
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

            ticker.tick(20)

        pygame.key.stop_text_input()
        return 0

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.view_mode == ViewMode.GALLERY:
                if self.selected_gallery_card_id is not None:
                    self.selected_gallery_card_id = None
                    self.confirm_delete = False
                else:
                    self.view_mode = ViewMode.EDITOR
                self._dirty = True
                return
            elif self.view_mode == ViewMode.FULL_DIALOG:
                self.view_mode = ViewMode.EDITOR
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

        if self.view_mode == ViewMode.EDITOR:
            if event.type == pygame.TEXTINPUT:
                if self.draft.insert(event.text):
                    self.audio.play("type")
                    self._cursor_visible = True
                    self._last_blink = self.clock()
                    self._dirty = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    if self.draft.backspace():
                        self.audio.play("type")
                        self._cursor_visible = True
                        self._last_blink = self.clock()
                        self._dirty = True
                elif event.key == pygame.K_DELETE:
                    if self.draft.delete_forward():
                        self.audio.play("type")
                        self._cursor_visible = True
                        self._last_blink = self.clock()
                        self._dirty = True
                elif event.key == pygame.K_LEFT:
                    if self.draft.move_left():
                        self._cursor_visible = True
                        self._last_blink = self.clock()
                        self._dirty = True
                elif event.key == pygame.K_RIGHT:
                    if self.draft.move_right():
                        self._cursor_visible = True
                        self._last_blink = self.clock()
                        self._dirty = True
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and (event.mod & pygame.KMOD_CTRL):
                    self._save_postcard()
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
            self.view_mode = ViewMode.EDITOR
            return True

        if self.view_mode == ViewMode.GALLERY:
            return self._handle_gallery_pointer(point)

        # Editor mode pointer handling
        # 1. Recipient tap
        rec_id = self.renderer.recipient_at(point)
        if rec_id is not None:
            self.draft.set_recipient(rec_id)
            self.audio.play("select")
            return True

        # 2. Stamp tap
        st_id = self.renderer.stamp_at(point)
        if st_id is not None:
            self.draft.set_stamp(st_id)
            self.audio.play("stamp")
            return True

        # 3. Send / Save Button
        if self.renderer.send_contains(point):
            self._save_postcard()
            return True

        # 4. Gallery Button
        if self.renderer.gallery_contains(point):
            self.view_mode = ViewMode.GALLERY
            self.selected_gallery_card_id = None
            self.confirm_delete = False
            self.audio.play("select")
            return True

        # 5. Clear Button
        if self.renderer.clear_contains(point):
            self.draft.clear()
            self.audio.play("delete")
            return True

        return False

    def _handle_gallery_pointer(self, point: tuple[int, int]) -> bool:
        # Return to Editor
        if self.renderer.back_to_editor_contains(point):
            self.view_mode = ViewMode.EDITOR
            self.selected_gallery_card_id = None
            self.confirm_delete = False
            self.audio.play("select")
            return True

        # Card Modal open
        if self.selected_gallery_card_id is not None:
            if self.confirm_delete:
                if self.renderer.delete_btn_rect().collidepoint(point):
                    # Confirm Delete
                    self.library.delete(self.selected_gallery_card_id)
                    self.storage.save(self.library)
                    self.selected_gallery_card_id = None
                    self.confirm_delete = False
                    self.audio.play("delete")
                    return True
                elif self.renderer.cancel_btn_rect().collidepoint(point):
                    # Cancel Delete
                    self.confirm_delete = False
                    self.audio.play("select")
                    return True
            else:
                if self.renderer.delete_btn_rect().collidepoint(point):
                    # Request Delete Confirmation
                    self.confirm_delete = True
                    self.audio.play("select")
                    return True
                elif self.renderer.cancel_btn_rect().collidepoint(point):
                    # Close Modal
                    self.selected_gallery_card_id = None
                    self.confirm_delete = False
                    self.audio.play("select")
                    return True
            return True

        # Grid card tap
        idx = self.renderer.gallery_card_at(point, self.library.count)
        if idx is not None:
            card = self.library.cards[idx]
            self.selected_gallery_card_id = card.card_id
            self.confirm_delete = False
            self.audio.play("select")
            return True

        return False

    def _save_postcard(self) -> None:
        if self.library.is_full:
            self.audio.play("full")
            self.view_mode = ViewMode.FULL_DIALOG
            return

        card_id = f"card-{int(time.time())}-{self.rng.randrange(1_000_000):06d}"
        saved_card = SavedPostcard(
            card_id=card_id,
            created_at=int(time.time()),
            recipient_id=self.draft.recipient_id,
            stamp_id=self.draft.stamp_id,
            text=self.draft.text,
        )

        # 1. Add to in-memory library
        self.library.add(saved_card)

        # 2. Write to storage FIRST
        saved = self.storage.save(self.library)
        if not saved:
            # Revert if write failed
            self.library.delete(card_id)
            return

        # 3. Emit creation event ONLY after successful storage save
        self.events.postcard_created(saved_card)
        self.audio.play("send")

        # 4. Reset draft for next postcard
        self.draft.clear()

    def _render(self) -> None:
        if self.view_mode == ViewMode.FULL_DIALOG:
            self.renderer.draw_editor(
                self.canvas.surface,
                self.draft,
                self.library,
                cursor_visible=False,
            )
            self.renderer.draw_full_dialog(self.canvas.surface)
        elif self.view_mode == ViewMode.GALLERY:
            self.renderer.draw_gallery(
                self.canvas.surface,
                self.library,
                selected_card_id=self.selected_gallery_card_id,
                confirm_delete=self.confirm_delete,
            )
        else:
            self.renderer.draw_editor(
                self.canvas.surface,
                self.draft,
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

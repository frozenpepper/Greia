"""Greia Screen/controller bridge for the shared child creations gallery.

Both full-screen My Creations and a trusted selection overlay use this
presentation owner. It never exposes library enumeration/delete through
an Activity broker, and no capture/playback occurs until requested.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from .creation_gallery import CreationsGalleryController, GalleryError, GalleryMode
from .creation_gallery_layout import CreationGalleryLayout
from .creation_gallery_painter import CreationsPygamePainter
from .creations import CreationLibraryError
from .typography import GreiaTypography
from .ui_core import Screen, UiEventResult


class CreationsGalleryScreen(Screen):
    """A single bounded child-facing view with trusted event dispatch."""

    def __init__(
        self,
        controller: CreationsGalleryController,
        *,
        typography: GreiaTypography,
        locale: str = "it",
    ):
        self.controller = controller
        self.painter = CreationsPygamePainter(
            controller, typography=typography, locale=locale
        )
        self._size: tuple[int, int] | None = None
        self._closed = False
        self.error = False
        self._delete_focus = "cancel_delete"

    @property
    def surface_id(self) -> str:
        return (
            "greia.creations.picker"
            if self.controller.mode == GalleryMode.PICKER
            else "greia.creations.library"
        )

    def on_exit(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.controller.close()
        self.painter.close()

    def needs_frame(self) -> bool:
        """Animate progress only during actual playback, never while idle."""
        if self._closed:
            return False
        active = self.controller.playing_id is not None and self.controller.paused_id is None
        self.controller.poll_playback()
        return active

    def draw(self, screen: Any) -> None:
        import pygame

        size = screen.get_size()
        try:
            layout = CreationGalleryLayout.for_surface(
                *size, tabs=len(self.controller.families)
            )
            if size != self._size:
                self._size = size
                self.controller.set_page_size(len(layout.cards))
                self.painter.close()
            self.painter.draw(screen, layout, pygame, delete_focus=self._delete_focus)
        except (GalleryError, CreationLibraryError, ValueError, OSError, sqlite3.Error, pygame.error):
            self.error = True
        if self.error:
            # A bounded illustrated failure is preferable to leaking paths or
            # crashing Greia Home when an artifact has become corrupt.
            pygame.draw.circle(
                screen, (249, 170, 112), (size[0] // 2, 98), 20
            )

    def handle_event(self, event: object) -> UiEventResult:
        import pygame

        if self._closed or self.controller.closed:
            return UiEventResult.REQUEST_CLOSE
        try:
            if getattr(event, "type", None) == pygame.MOUSEBUTTONUP and getattr(event, "button", 0) == 1:
                position = getattr(event, "pos", (-1, -1))
                for hit in reversed(self.painter.targets):
                    if hit.rect.collidepoint(position):
                        return self._activate(hit.action, hit.value)
            if getattr(event, "type", None) == pygame.KEYDOWN:
                key = getattr(event, "key", -1)
                page = self.controller.page
                if page.pending_delete_id is not None:
                    # Confirmation is a true modal: no background play/replay,
                    # navigation or second delete while the question is open.
                    if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        return self._activate("cancel_delete", None)
                    if key == pygame.K_LEFT:
                        self._delete_focus = "cancel_delete"
                    elif key == pygame.K_RIGHT:
                        self._delete_focus = "confirm_delete"
                    elif key in (pygame.K_RETURN, pygame.K_SPACE):
                        return self._activate(self._delete_focus, None)
                    return UiEventResult.HANDLED
                if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return self._activate("detail_back" if page.detail_id else "close", None)
                if key == pygame.K_TAB and not page.detail_id:
                    families = self.controller.families
                    index = families.index(page.family)
                    return self._activate("family", families[(index + 1) % len(families)])
                if key in (pygame.K_LEFT, pygame.K_RIGHT) and not page.detail_id:
                    direction = -1 if key == pygame.K_LEFT else 1
                    ids = tuple(item.creation_id for item in page.items)
                    if ids:
                        current = ids.index(page.focused_id) if page.focused_id in ids else 0
                        target = current + direction
                        if 0 <= target < len(ids):
                            self.controller.focus_item(ids[target])
                        else:
                            self.controller.previous_page() if direction < 0 else self.controller.next_page()
                    return UiEventResult.HANDLED
                if key in (pygame.K_RETURN, pygame.K_SPACE):
                    if page.detail_id is None and page.focused_id:
                        return self._activate("open", page.focused_id)
                    if page.detail_id and self.controller.mode == GalleryMode.PICKER:
                        return self._activate("choose", None)
                if key == pygame.K_p and page.detail_id is not None:
                    return self._activate("audio", page.detail_id)
                if key == pygame.K_r and page.detail_id is not None:
                    return self._activate("replay", page.detail_id)
                if key == pygame.K_DELETE and page.detail_id and self.controller.mode == GalleryMode.LIBRARY:
                    return self._activate("ask_delete", None)
                return UiEventResult.HANDLED
        except (GalleryError, CreationLibraryError, ValueError, OSError, sqlite3.Error, pygame.error):
            self.error = True
            return UiEventResult.HANDLED
        return UiEventResult.IGNORED

    def _activate(self, action: str, value: object | None) -> UiEventResult:
        try:
            if action in ("close", "back"):
                self.on_exit()
                return UiEventResult.REQUEST_CLOSE
            if action == "detail_back":
                self.controller.close_item()
            elif action == "family":
                self.controller.set_family(value)  # type: ignore[arg-type]
            elif action == "next":
                self.controller.next_page()
            elif action == "previous":
                self.controller.previous_page()
            elif action == "open":
                self.controller.open_item(value)  # type: ignore[arg-type]
            elif action == "audio":
                self.controller.toggle_audio(value)  # type: ignore[arg-type]
            elif action == "replay":
                self.controller.replay_audio(value)  # type: ignore[arg-type]
            elif action == "ask_delete":
                self._delete_focus = "cancel_delete"
                self.controller.ask_delete()
            elif action == "cancel_delete":
                self.controller.cancel_delete()
            elif action == "confirm_delete":
                self.controller.confirm_delete()
                self.painter.close()
            elif action == "choose":
                self.controller.choose()
                return UiEventResult.REQUEST_CLOSE
            return UiEventResult.HANDLED
        except (GalleryError, CreationLibraryError, ValueError, OSError, sqlite3.Error):
            self.error = True
            return UiEventResult.HANDLED

"""Real Pygame rendering and child-input checks for the shared Creations UI.

These are SDL-dummy source tests, not human-reviewed Simulator screenshots.
They exercise the actual Screen and Painter, including the empty first boot.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform.creation_gallery import CreationsGalleryController, GalleryMode
from greia_platform.creation_gallery_layout import CreationGalleryLayout
from greia_platform.creation_gallery_screen import CreationsGalleryScreen
from greia_platform.creations import CreationLibrary
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import UiEventResult


class CreationGalleryRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.addCleanup(pygame.quit)
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.library = CreationLibrary(Path(work.name) / "creations")
        self.typography = GreiaTypography()
        self.addCleanup(self.typography.clear)

    def _screen(
        self, *,
        mode: GalleryMode = GalleryMode.LIBRARY, locale: str = "it",
        on_pick=None,
    ) -> CreationsGalleryScreen:
        controller = CreationsGalleryController(
            self.library, mode=mode, on_pick=on_pick,
            media_types=frozenset({"audio/wav"}) if mode is GalleryMode.PICKER else None,
        )
        return CreationsGalleryScreen(
            controller, typography=self.typography, locale=locale,
        )

    def test_empty_library_first_frame_is_drawable_in_both_languages(self) -> None:
        for locale in ("it", "en"):
            for size in ((480, 320), (800, 480), (1024, 600)):
                with self.subTest(locale=locale, size=size):
                    screen = self._screen(locale=locale)
                    surface = pygame.display.set_mode(size)
                    screen.draw(surface)
                    self.assertFalse(screen.error)
                    self.assertEqual(screen.controller.page.items, ())
                    self.assertTrue(any(t.action == "back" for t in screen.painter.targets))
                    self.assertFalse(any(t.action == "open" for t in screen.painter.targets))
                    screen.on_exit()

    def test_empty_filtered_picker_can_cancel_without_minting_a_grant(self) -> None:
        granted: list[str] = []
        screen = self._screen(
            mode=GalleryMode.PICKER, locale="en",
            on_pick=lambda creation_id: granted.append(creation_id) or "token",
        )
        surface = pygame.display.set_mode((800, 480))
        names: list[str] = []
        icon = screen.painter._icon

        def observe_icon(target, name, box, pg, color=None):
            names.append(name)
            icon(target, name, box, pg, color)

        screen.painter._icon = observe_icon
        screen.draw(surface)
        self.assertFalse(screen.error)
        # One 'audio' icon is the tab, another is the large empty-state art.
        # An audio-only picker must not incorrectly present a picture icon.
        self.assertEqual(names.count("audio"), 2)
        self.assertNotIn("image", names)
        self.assertFalse(any(t.action == "choose" for t in screen.painter.targets))
        back = next(t.rect.center for t in screen.painter.targets if t.action == "back")
        result = screen.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONUP, {"button": 1, "pos": back},
        ))
        self.assertIs(result, UiEventResult.REQUEST_CLOSE)
        self.assertEqual(granted, [])

    def test_delete_dialog_blocks_background_keys_and_defaults_to_cancel(self) -> None:
        record = self.library.publish(
            b"Once upon a time", producer_id="org.greia.writing",
            media_type="text/plain", role="story",
        )
        screen = self._screen()
        surface = pygame.display.set_mode((800, 480))
        screen.draw(surface)
        screen.controller.open_item(record.creation_id)
        screen._activate("ask_delete", None)
        screen.draw(surface)
        self.assertFalse(screen.error)
        self.assertEqual(screen.controller.page.pending_delete_id, record.creation_id)
        self.assertEqual(
            {hit.action for hit in screen.painter.targets},
            {"confirm_delete", "cancel_delete"},
        )
        layout = CreationGalleryLayout.for_surface(800, 480)
        cancel_border = (layout.cancel.x + layout.cancel.width // 2, layout.cancel.y + 2)
        confirm_border = (layout.confirm.x + layout.confirm.width // 2, layout.confirm.y + 2)
        self.assertEqual(tuple(surface.get_at(cancel_border)[:3]), screen.painter.INK)

        # Background replay, Delete, TAB and arrow keys cannot escape the modal.
        for key in (pygame.K_p, pygame.K_r, pygame.K_TAB, pygame.K_DELETE):
            self.assertIs(
                screen.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": key})),
                UiEventResult.HANDLED,
            )
            self.assertEqual(screen.controller.page.pending_delete_id, record.creation_id)

        # Initial focus is the safe 'keep my creation' choice.
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
        self.assertIsNone(screen.controller.page.pending_delete_id)
        self.assertEqual(self.library.read(record.creation_id), b"Once upon a time")

        # A distinct RIGHT, then ENTER sequence must be required to delete.
        screen._activate("ask_delete", None)
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT}))
        self.assertEqual(screen._delete_focus, "confirm_delete")
        screen.draw(surface)
        self.assertEqual(
            {hit.action for hit in screen.painter.targets},
            {"confirm_delete", "cancel_delete"},
        )
        self.assertEqual(tuple(surface.get_at(confirm_border)[:3]), screen.painter.INK)
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
        self.assertEqual(self.library.list(), ())
        screen.draw(surface)  # deletion returns safely to empty-library state
        self.assertFalse(screen.error)
        screen.on_exit()


if __name__ == "__main__":
    unittest.main()

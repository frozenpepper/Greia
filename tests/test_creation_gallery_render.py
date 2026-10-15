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

import hermetic_volume


def setUpModule() -> None:
    hermetic_volume.install_for_module()


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

    def test_empty_library_caption_does_not_cover_footer_navigation(self) -> None:
        screen = self._screen(locale="en")
        size = (1024, 600)
        surface = pygame.display.set_mode(size)
        positions: list[int] = []
        real_text = screen.painter._text

        def observe_text(target, label, x, y, font_size, *, center=False):
            if "creations will appear" in label:
                positions.append(y)
            return real_text(target, label, x, y, font_size, center=center)

        screen.painter._text = observe_text
        screen.draw(surface)
        self.assertFalse(screen.error)
        self.assertEqual(len(positions), 1)
        layout = CreationGalleryLayout.for_surface(*size)
        self.assertLess(positions[0], layout.back.y - 8)
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



class StorybookCreationGalleryTests(unittest.TestCase):
    """Shared-art presentation: framed tiles, round controls, pictograms."""

    def setUp(self) -> None:
        from greia_platform.assets import AssetCatalogue
        from greia_platform.pygame_visual_assets import PygameVisualSurfaceCache

        pygame.init()
        self.addCleanup(pygame.quit)
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.library = CreationLibrary(Path(work.name) / "creations")
        self.typography = GreiaTypography()
        self.addCleanup(self.typography.clear)
        root = Path(__file__).resolve().parents[1]
        self.cache = PygameVisualSurfaceCache.for_pygame(
            AssetCatalogue.load(root / "assets" / "catalog" / "shared_visuals_v1.toml"),
            max_entries=32,
        )
        self.requested: list[str] = []
        real_get = self.cache.get

        def observed(asset_id, **kwargs):
            self.requested.append(asset_id)
            return real_get(asset_id, **kwargs)

        self.cache.get = observed

    def _screen(self, *, backdrop=None) -> CreationsGalleryScreen:
        controller = CreationsGalleryController(self.library)
        return CreationsGalleryScreen(
            controller, typography=self.typography, locale="en",
            visual_cache=self.cache, backdrop=backdrop, greeter="leo",
            text_transform=str.upper,
        )

    def test_empty_and_filled_gallery_use_shared_art_at_every_size(self) -> None:
        scene = {}

        def backdrop(size):
            return scene.setdefault(size, pygame.Surface(size))

        for size in ((480, 320), (800, 480), (1024, 600), (1280, 800)):
            with self.subTest(size=size, state="empty"):
                surface = pygame.display.set_mode(size)
                screen = self._screen(backdrop=backdrop)
                screen.draw(surface)
                self.assertFalse(screen.error)
                self.assertTrue(any(t.action == "back" for t in screen.painter.targets))
                screen.on_exit()
        self.assertIn("ui.pictogram.creation", self.requested)
        self.assertIn("character.leo", self.requested)
        self.library.publish(b"Once upon a time", producer_id="org.greia.writing",
                             media_type="text/plain", role="story", title="Tale")
        for size in ((480, 320), (1024, 600)):
            with self.subTest(size=size, state="filled"):
                surface = pygame.display.set_mode(size)
                screen = self._screen(backdrop=backdrop)
                screen.draw(surface)
                self.assertFalse(screen.error)
                self.assertTrue(any(t.action == "open" for t in screen.painter.targets))
                screen.on_exit()
        self.assertIn("ui.card.activity_tile", self.requested)
        self.assertIn("ui.button.round", self.requested)

    def test_storybook_delete_dialog_keeps_safe_default_and_visible_focus(self) -> None:
        record = self.library.publish(
            b"Keep me", producer_id="org.greia.writing", media_type="text/plain", role="story",
        )
        screen = self._screen()
        surface = pygame.display.set_mode((800, 480))
        screen.draw(surface)
        screen.controller.open_item(record.creation_id)
        screen._activate("ask_delete", None)
        screen.draw(surface)
        self.assertFalse(screen.error)
        self.assertEqual(
            {hit.action for hit in screen.painter.targets}, {"confirm_delete", "cancel_delete"}
        )
        layout = CreationGalleryLayout.for_surface(800, 480)
        border = (layout.cancel.x + layout.cancel.width // 2, layout.cancel.y + 2)
        self.assertEqual(tuple(surface.get_at(border)[:3]), screen.painter.INK)
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
        self.assertEqual(self.library.read(record.creation_id), b"Keep me")
        screen.on_exit()

    def test_broken_shared_art_falls_back_to_primitive_gallery(self) -> None:
        def broken(asset_id, **kwargs):
            raise FileNotFoundError(asset_id)

        self.cache.get = broken
        screen = self._screen()
        surface = pygame.display.set_mode((1024, 600))
        screen.draw(surface)
        self.assertFalse(screen.error)
        self.assertTrue(any(t.action == "back" for t in screen.painter.targets))
        screen.on_exit()


if __name__ == "__main__":
    unittest.main()

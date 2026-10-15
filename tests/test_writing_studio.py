"""Writing app-loop tests (ADR 0037 kit, emoji sheet, paper colours, delete).

These drive the real ``WritingApp`` through Pygame events on a dummy display:
typing (child text kept exactly as typed), the non-modal emoji sheet, paper
colours, undo, autosave, deliberate delete, keyboard toolbar focus,
controller focus, protected chrome and the My Creations celebration.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.activity_feedback import CastPose
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import GreiaTypography

from activities.writing.writing_app import WritingApp
from activities.writing.writing_content import (
    DEFAULT_TINT,
    GALLERY_PAGE_SIZE,
    INDEX_KEY,
    MAX_DOCUMENTS,
    TINT_IDS,
)
from activities.writing.writing_controls import WritingSheet
from activities.writing.writing_model import DocumentRepository, card_badge


class MemoryStorage:
    def __init__(self) -> None:
        self.kv: dict[str, object] = {}
        self.files: dict[str, bytes] = {}

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        self.kv[key] = value

    def file_write_atomic(self, name, data):
        self.files[name] = bytes(data)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class FakeCreations:
    def __init__(self) -> None:
        self.published: list[tuple] = []

    def publish_private_file(self, name, *, media_type, role, title=""):
        self.published.append((name, media_type, role, title))
        return {"ok": True}


def _key(key: int, mod: int = 0) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode="", scancode=0)


class WritingStudioTestCase(unittest.TestCase):
    size = (1024, 600)

    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.storage = MemoryStorage()
        self.clock = FakeClock()

    def make_app(self, creations=None) -> WritingApp:
        return WritingApp(
            self.screen, None, ChildUiMetrics.for_size(*self.size), GreiaTypography(), None,
            DocumentRepository(self.storage), creations, clock=self.clock,
        )

    def type_text(self, app: WritingApp, text: str) -> None:
        # SDL delivers one TEXTINPUT per committed character/cluster.
        for char in text:
            app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text=char))

    def tap(self, app: WritingApp, point) -> None:
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=point, button=1))
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=point, button=1))

    def frame(self, app: WritingApp, seconds: float = 0.0) -> None:
        self.clock.now += seconds
        app._step_frame()
        app._draw()

    def sheet(self, app: WritingApp) -> WritingSheet:
        overlays = app.surfaces.overlays
        self.assertTrue(overlays)
        return overlays[-1]


class WritingSessionTests(WritingStudioTestCase):
    def test_full_session_types_emoji_undoes_and_autosaves_exactly_as_typed(self) -> None:
        app = self.make_app()
        self.frame(app)
        self.assertEqual(self.storage.files, {})  # a blank page is never saved
        self.type_text(app, "Ciao Mamma, io sono Leo")
        app.handle_event(_key(pygame.K_RETURN))
        # Insert an emoji through the picker by pointer.
        self.tap(app, app.controls.emoji.rect.center)
        sheet = self.sheet(app)
        self.assertTrue(app.emoji_picker_open)
        first_emoji = sheet.layer.target("emoji.0")
        self.tap(app, first_emoji.rect.center)
        self.assertEqual(app.surfaces.overlays, (sheet,))  # stays open for more
        self.type_text(app, "!x")
        app.handle_event(_key(pygame.K_BACKSPACE))
        expected = "Ciao Mamma, io sono Leo\n" + app.emoji_palette.categories[0].emoji[0] + "!"
        self.assertEqual(app.buffer.text, expected)
        # Undo through the shared undo control restores the deleted "x".
        app.handle_event(_key(pygame.K_ESCAPE))
        self.assertFalse(app.emoji_picker_open)
        self.tap(app, app.controls.undo.rect.center)
        self.assertEqual(app.buffer.text, expected + "x")
        self.frame(app, 0.1)
        self.assertTrue(app.dirty)
        self.frame(app, 2.0)
        self.assertFalse(app.dirty)
        records = app.repository.list_records()
        self.assertEqual(len(records), 1)
        # ADR 0034: child-authored text is stored exactly as typed (no re-casing).
        self.assertEqual(app.repository.load_text(records[0].document_id), expected + "x")
        self.assertEqual(records[0].tint, DEFAULT_TINT)
        # Leaving with Escape saves and stops; the page reloads intact.
        self.assertFalse(app.handle_event(_key(pygame.K_ESCAPE)))
        again = self.make_app()
        self.assertEqual(again.buffer.text, expected + "x")

    def test_undo_control_uses_the_shared_library_glyph(self) -> None:
        app = self.make_app()
        self.assertTrue(get_shared_visual_path("icon.hud.undo").is_file())
        self.assertIsNotNone(app.controls.undo.icon)
        self.assertIs(app.controls.undo.icon, app.kit.glyph("undo", app.metrics.px(38)))
        self.assertFalse(app.controls.undo.enabled)
        self.type_text(app, "a")
        self.assertTrue(app.controls.undo.enabled)

    def test_mouse_wheel_scrolls_a_long_story_and_typing_brings_the_caret_back(self) -> None:
        app = self.make_app()
        for _ in range(30):
            self.type_text(app, "line")
            app.handle_event(_key(pygame.K_RETURN))
        bottom = app.scroll_line
        self.assertGreater(bottom, 0)
        for _ in range(40):
            app.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1))
        self.assertEqual(app.scroll_line, 0)
        self.type_text(app, "z")
        self.assertEqual(app.scroll_line, bottom)


class WritingEmojiSheetTests(WritingStudioTestCase):
    def test_emoji_grid_sits_right_under_the_category_row(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                screen = pygame.display.set_mode(size)
                app = WritingApp(
                    screen, None, ChildUiMetrics.for_size(*size), GreiaTypography(), None,
                    DocumentRepository(MemoryStorage()), None, clock=self.clock,
                )
                panel, categories, items = app.renderer.emoji_sheet_rects(app.editor_rect)
                gap = items[0].top - categories[0].bottom
                self.assertGreaterEqual(gap, 0)
                self.assertLessEqual(gap, app.metrics.px(20))  # no dead gap
                self.assertTrue(app.editor_rect.contains(panel))
                for rect in [*categories, *items]:
                    self.assertTrue(panel.contains(rect))
                self.assertGreaterEqual(len(items), max(len(c.emoji) for c in app.emoji_palette.categories))
                # Text above the sheet stays visible (at least one line).
                app._toggle_emoji()
                self.assertGreaterEqual(app.renderer.visible_line_count(app.view_rect), 1)
                self.assertLessEqual(app.view_rect.bottom, panel.top)
                app._draw()

    def test_category_keyboard_and_typing_while_the_sheet_is_open(self) -> None:
        app = self.make_app()
        app._toggle_emoji()
        sheet = self.sheet(app)
        self.tap(app, sheet.layer.target("category.animals").rect.center)
        sheet = self.sheet(app)
        self.assertEqual(app.emoji_palette.selected.category_id, "animals")
        # Arrows move over the emoji sheet; Enter inserts the focused emoji.
        app.handle_event(_key(pygame.K_DOWN))
        self.assertTrue(sheet.layer.focus_visible)
        focused = sheet.layer.focused_id
        self.assertTrue(focused.startswith("emoji."))
        app.handle_event(_key(pygame.K_RETURN))
        inserted = app.emoji_palette.selected.emoji[int(focused.split(".")[1])]
        self.assertEqual(app.buffer.text, inserted)
        # Space types a space (not an activation) and letters still type.
        app.handle_event(_key(pygame.K_SPACE))
        self.type_text(app, " ok")
        self.assertEqual(app.buffer.text, inserted + " ok")
        # Tapping the visible text places the caret and keeps the sheet.
        origin = app.renderer.text_origin(app.editor_rect)
        self.tap(app, (origin[0] + 1, origin[1] + 5))
        self.assertEqual(app.buffer.cursor, 0)
        self.assertTrue(app.emoji_picker_open)
        # The emoji toolbar button closes it again.
        self.tap(app, app.controls.emoji.rect.center)
        self.assertFalse(app.emoji_picker_open)
        self.assertEqual(app.surfaces.overlays, ())


class WritingPaperTests(WritingStudioTestCase):
    def test_new_offers_six_papers_and_the_tint_is_saved_as_metadata(self) -> None:
        app = self.make_app()
        self.type_text(app, "first page")
        self.tap(app, app.controls.new.rect.center)
        sheet = self.sheet(app)
        self.assertTrue(sheet.modal)
        self.assertEqual(len(sheet.layer.targets), len(TINT_IDS))
        self.tap(app, sheet.layer.target("paper.sky").rect.center)
        self.assertEqual(app.surfaces.overlays, ())
        self.assertIsNone(app.current)
        self.assertEqual(app.tint, "sky")
        self.assertEqual(len(app.repository.list_records()), 1)  # draft not saved yet
        self.type_text(app, "blue page")
        self.assertTrue(app._save())
        records = app.repository.list_records()
        self.assertEqual([r.tint for r in records], ["sky", DEFAULT_TINT])
        stored = self.storage.kv[INDEX_KEY]
        self.assertEqual(stored[0]["tint"], "sky")
        self.assertNotIn("tint", stored[1])
        # The body stays plain UTF-8 text.
        self.assertEqual(self.storage.files[f"documents/{records[0].document_id}.txt"], b"blue page")
        app._open(records[1])
        self.assertEqual(app.tint, DEFAULT_TINT)
        app._open(app.repository.list_records()[0])
        self.assertEqual(app.tint, "sky")

    def test_dismissing_the_paper_sheet_keeps_the_page_and_text_does_not_leak(self) -> None:
        app = self.make_app()
        self.type_text(app, "keep")
        app._press_new()
        app.handle_event(_key(pygame.K_RIGHT))
        app.handle_event(_key(pygame.K_SPACE))
        # Space chose a paper; its TEXTINPUT must not land on the new page.
        app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text=" "))
        self.assertEqual(app.buffer.text, "")
        self.assertEqual(app.tint, TINT_IDS[1])
        app._open(app.repository.list_records()[0])
        app._press_new()
        app.handle_event(_key(pygame.K_ESCAPE))
        self.assertEqual(app.buffer.text, "keep")
        self.assertTrue(app.running)

    def test_legacy_index_entries_load_on_cream_and_keep_their_text(self) -> None:
        self.storage.kv[INDEX_KEY] = [{"id": "a" * 32, "preview": "old"}, {"id": "b" * 32, "preview": "x", "tint": "neon"}]
        self.storage.files[f"documents/{'a' * 32}.txt"] = "Old Story 🐢".encode("utf-8")
        self.storage.files[f"documents/{'b' * 32}.txt"] = b"x"
        app = self.make_app()
        self.assertEqual([r.tint for r in app.records], [DEFAULT_TINT, DEFAULT_TINT])
        self.assertEqual(app.buffer.text, "Old Story 🐢")
        self.type_text(app, "!")
        self.assertTrue(app._save())
        self.assertEqual(app.repository.list_records()[0].tint, DEFAULT_TINT)


class WritingGalleryTests(WritingStudioTestCase):
    def seed(self, app: WritingApp, count: int) -> None:
        for index in range(count):
            app.repository.create_text(f"page {index}", tint=TINT_IDS[index % len(TINT_IDS)])
        app.records = app.repository.list_records()

    def test_badge_delete_needs_confirmation_and_cancel_keeps_the_page(self) -> None:
        app = self.make_app()
        self.seed(app, 3)
        app._enter_gallery()
        badge = app.controls.badges[1]
        target = app.records[1]
        self.tap(app, badge.rect.center)
        sheet = self.sheet(app)
        self.assertEqual(sheet.layer.focused_id, "delete.cancel")  # back is the default
        self.assertEqual(len(app.repository.list_records()), 3)
        app.handle_event(_key(pygame.K_RETURN))
        self.assertEqual(app.surfaces.overlays, ())
        self.assertEqual(len(app.repository.list_records()), 3)
        self.tap(app, badge.rect.center)
        self.tap(app, self.sheet(app).layer.target("delete.confirm").rect.center)
        remaining = app.repository.list_records()
        self.assertEqual(len(remaining), 2)
        self.assertNotIn(target.document_id, [r.document_id for r in remaining])
        self.assertNotIn(f"documents/{target.document_id}.txt", self.storage.files)

    def test_keyboard_delete_from_a_full_shelf_makes_room_for_a_new_page(self) -> None:
        app = self.make_app()
        self.seed(app, MAX_DOCUMENTS)
        app._open(app.records[0])
        app._press_new()
        self.assertEqual(app.mode, "gallery")  # full: never evict, show the shelf
        self.assertGreater(app.library_full_until, self.clock.now)
        app.handle_event(_key(pygame.K_RIGHT))
        app.handle_event(_key(pygame.K_DELETE))
        self.sheet(app)
        app.handle_event(_key(pygame.K_RIGHT))
        app.handle_event(_key(pygame.K_RETURN))
        self.assertEqual(len(app.repository.list_records()), MAX_DOCUMENTS - 1)
        app._toggle_gallery()
        app._press_new()
        self.assertTrue(self.sheet(app).modal)
        app.handle_event(_key(pygame.K_RETURN))
        self.type_text(app, "room!")
        self.assertTrue(app._save())
        self.assertEqual(len(app.repository.list_records()), MAX_DOCUMENTS)

    def test_deleting_the_open_page_starts_a_fresh_draft(self) -> None:
        app = self.make_app()
        self.type_text(app, "bye")
        self.assertTrue(app._save())
        app._enter_gallery()
        app._ask_delete_focused()
        app._confirm_delete()
        self.assertEqual(app.repository.list_records(), [])
        self.assertIsNone(app.current)
        app._toggle_gallery()
        self.assertEqual(app.buffer.text, "")

    def test_card_badges_identify_pages_for_pre_readers(self) -> None:
        self.assertEqual(card_badge("my 🦖 dino"), "🦖")
        self.assertEqual(card_badge("  ciao"), "c")
        self.assertEqual(card_badge("Ciao"), "C")  # never re-cased
        self.assertEqual(card_badge("👩🏽‍🔬 lab"), "👩🏽‍🔬")
        self.assertEqual(card_badge("..."), "")

    def test_gallery_cards_pages_and_controls_stay_clear_of_chrome(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                screen = pygame.display.set_mode(size)
                app = WritingApp(
                    screen, None, ChildUiMetrics.for_size(*size), GreiaTypography(), None,
                    DocumentRepository(MemoryStorage()), FakeCreations(), clock=self.clock,
                )
                self.seed(app, 2 * GALLERY_PAGE_SIZE + 1)
                app._enter_gallery()
                app._draw()
                chrome = ActivitySystemChromeLayout.for_surface(*size).protected_region
                protected = pygame.Rect(chrome.x, chrome.y, chrome.width, chrome.height)
                for target in app.controls.layer.targets:
                    self.assertFalse(target.rect.colliderect(protected), target.control_id)
                cards = [rect for rect, _ in app.renderer.gallery_cards(app.editor_rect, app.records, 0)]
                strip = app.renderer.gallery_strip(app.editor_rect)
                for rect in cards:
                    self.assertFalse(rect.colliderect(strip))
                app._toggle_gallery()
                for target in app.controls.layer.targets:
                    self.assertFalse(target.rect.colliderect(protected), target.control_id)


class WritingInputTests(WritingStudioTestCase):
    def test_tab_moves_keyboard_focus_into_the_toolbar_without_typing(self) -> None:
        app = self.make_app()
        self.type_text(app, "hi")
        layer = app.controls.layer
        app.handle_event(_key(pygame.K_TAB))
        self.assertTrue(app.toolbar_focus)
        self.assertTrue(layer.focus_visible)
        self.assertEqual(layer.focused_id, "tool.gallery")
        app.handle_event(_key(pygame.K_RIGHT))
        app.handle_event(_key(pygame.K_RIGHT))
        self.assertEqual(layer.focused_id, "tool.emoji")
        app.handle_event(_key(pygame.K_SPACE))
        app.handle_event(pygame.event.Event(pygame.TEXTINPUT, text=" "))
        self.assertTrue(app.emoji_picker_open)
        self.assertEqual(app.buffer.text, "hi")  # Space activated, did not type
        self.assertTrue(self.sheet(app).layer.focus_visible)
        app.handle_event(_key(pygame.K_ESCAPE))
        # Typing returns to the page from toolbar focus.
        app.handle_event(_key(pygame.K_TAB))
        self.assertTrue(app.toolbar_focus)
        self.type_text(app, "!")
        self.assertFalse(app.toolbar_focus)
        self.assertEqual(app.buffer.text, "hi!")
        # Arrows on the page move the caret (text profile keeps arrows).
        app.handle_event(_key(pygame.K_LEFT))
        self.assertEqual(app.buffer.cursor, 2)

    def test_controller_dpad_focuses_toolbar_and_south_presses(self) -> None:
        button_down = getattr(pygame, "CONTROLLERBUTTONDOWN", None)
        if button_down is None or not hasattr(pygame, "CONTROLLER_BUTTON_DPAD_RIGHT"):
            self.skipTest("SDL controller events unavailable")
        app = self.make_app()
        self.type_text(app, "x")

        def press(button: int) -> None:
            app.handle_event(pygame.event.Event(button_down, button=button, instance_id=0))
            app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONUP, button=button, instance_id=0))

        press(pygame.CONTROLLER_BUTTON_DPAD_RIGHT)
        self.assertTrue(app.toolbar_focus)
        press(pygame.CONTROLLER_BUTTON_DPAD_RIGHT)
        self.assertEqual(app.controls.layer.focused_id, "tool.undo")
        press(pygame.CONTROLLER_BUTTON_A)
        self.assertEqual(app.buffer.text, "")
        press(pygame.CONTROLLER_BUTTON_DPAD_LEFT)
        press(pygame.CONTROLLER_BUTTON_A)
        self.assertEqual(app.mode, "gallery")
        press(pygame.CONTROLLER_BUTTON_B)
        self.assertEqual(app.mode, "edit")

    def test_pointer_in_protected_chrome_never_presses_or_moves_the_caret(self) -> None:
        app = self.make_app()
        self.type_text(app, "abc")
        chrome = ActivitySystemChromeLayout.for_surface(*self.size).home_hitbox
        point = (chrome.x + chrome.width // 2, chrome.y + chrome.height // 2)
        self.tap(app, point)
        self.assertEqual(app.buffer.cursor, 3)
        self.assertEqual(app.mode, "edit")
        self.assertEqual(app.surfaces.overlays, ())


class WritingShareTests(WritingStudioTestCase):
    def test_share_is_deliberate_and_leo_cheers(self) -> None:
        creations = FakeCreations()
        app = self.make_app(creations)
        self.assertFalse(app.controls.share.enabled)  # nothing to share yet
        self.tap(app, app.controls.share.rect.center)
        self.assertEqual(creations.published, [])
        self.type_text(app, "Una storia 🌈")
        self.assertTrue(app.controls.share.enabled)
        self.tap(app, app.controls.share.rect.center)
        self.assertEqual(len(creations.published), 1)
        name, media_type, role, _title = creations.published[0]
        self.assertEqual((media_type, role), ("text/plain", "document"))
        self.assertEqual(self.storage.files[name].decode("utf-8"), "Una storia 🌈")
        if app.cast is not None and app.cast.available:
            self.assertIs(app.cast.pose, CastPose.CHEER)
        self.frame(app, 0.2)
        self.frame(app, 3.0)
        self.assertEqual(app.shared_state, "")


if __name__ == "__main__":
    unittest.main()

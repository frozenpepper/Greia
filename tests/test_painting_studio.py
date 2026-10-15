"""Painting studio app-loop tests (ADR 0037 kit, stamps, colouring, delete).

These drive the real ``PaintingApp`` through Pygame events on a dummy display:
pointer strokes, keyboard focus, controller virtual pointer, the stamp and
colouring sheets, the deliberate delete confirmation and save migration.
"""
from __future__ import annotations

import io
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
from PIL import Image

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.system_chrome import ActivitySystemChromeLayout

from activities.painting.painting_app import PaintingApp
from activities.painting.painting_content import (
    COLOURING_PAGES,
    GALLERY_PAGE_SIZE,
    INDEX_KEY,
    MAX_PAINTINGS,
    STAMP_IDS,
)
from activities.painting.painting_model import PaintingRecord, PaintingRepository, Stamp
from activities.painting.painting_renderer import _decode_png, _encode_png

ACTIVITY = ROOT / "activities" / "painting"


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


def _key(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0)


class PaintingStudioTestCase(unittest.TestCase):
    size = (1024, 600)

    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.storage = MemoryStorage()
        self.clock = FakeClock()

    def make_app(self, creations=None) -> PaintingApp:
        return PaintingApp(
            self.screen, ChildUiMetrics.for_size(*self.size), None,
            PaintingRepository(self.storage), creations, clock=self.clock,
        )

    def drag(self, app: PaintingApp, points) -> None:
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=points[0], button=1))
        for point in points[1:]:
            app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=point, rel=(0, 0), buttons=(1, 0, 0)))
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=points[-1], button=1))

    def tap(self, app: PaintingApp, point) -> None:
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=point, button=1))
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=point, button=1))

    def frame(self, app: PaintingApp, seconds: float = 0.0) -> None:
        self.clock.now += seconds
        app._step_frame()
        app._draw()


class PaintingSessionTests(PaintingStudioTestCase):
    def test_full_studio_session_paints_stamps_undoes_and_autosaves(self) -> None:
        app = self.make_app()
        self.frame(app)
        canvas = app.canvas_rect
        # Pick blue by tapping its swatch, then the large brush size.
        blue_rect = app.renderer._color_buttons()[5][0]
        self.tap(app, blue_rect.center)
        self.assertEqual(app.selected_color, 5)
        self.tap(app, app.renderer._size_buttons()[2][0].center)
        self.assertEqual(app.selected_size, 2)
        stroke = [(canvas.left + 40 + i * 12, canvas.centery) for i in range(20)]
        self.drag(app, stroke)
        self.assertEqual(app.canvas.get_at((stroke[5][0] - canvas.left, stroke[5][1] - canvas.top))[:3], (51, 163, 211))
        # Stamp: open the sheet from the tray tile, choose the cat, place one.
        self.tap(app, app.renderer.tool_buttons()[1].center)
        self.assertEqual(len(app.surfaces.overlays), 1)
        _panel, tiles = app.renderer.stamp_sheet_rects()
        cat = STAMP_IDS.index("prop.vocab.cat")
        self.tap(app, tiles[cat].center)
        self.assertEqual(app.surfaces.overlays, ())
        self.assertEqual((app.tool, app.stamp_id), ("stamp", "prop.vocab.cat"))
        self.tap(app, (canvas.right - 120, canvas.centery))
        self.assertIsInstance(app.history.items[-1], Stamp)
        self.assertEqual(len(app.history.items), 2)
        # Undo (top toolbar) removes only the stamp.
        self.tap(app, app.renderer.toolbar_rect("undo").center)
        self.assertEqual(len(app.history.items), 1)
        self.frame(app)
        self.assertEqual(app._status(), "saving")
        self.frame(app, 1.5)  # idle autosave
        self.assertFalse(app.dirty)
        self.assertEqual(len(PaintingRepository(self.storage).list_records()), 1)
        self.assertEqual(app._status(), "saved")

    def test_keyboard_reaches_swatches_tools_and_toolbar(self) -> None:
        app = self.make_app()
        self.frame(app)
        layer = app.controls.layer
        self.assertEqual(layer.focused_id, "color.1")  # starts on the chosen paint
        app.handle_event(_key(pygame.K_RIGHT))
        self.assertTrue(layer.focus_visible)
        self.assertEqual(layer.focused_id, "color.2")
        app.handle_event(_key(pygame.K_SPACE))
        self.assertEqual(app.selected_color, 2)
        for _ in range(12):
            app.handle_event(_key(pygame.K_RIGHT))
        self.assertEqual(layer.focused_id, "tool.stamp")
        app.handle_event(_key(pygame.K_LEFT))
        app.handle_event(_key(pygame.K_RETURN))
        self.assertEqual(app.tool, "eraser")
        app.handle_event(_key(pygame.K_UP))
        self.assertTrue(layer.focused_id.startswith("tool."))
        # The kit never focuses anything inside the protected Home/Back region.
        chrome = ActivitySystemChromeLayout.for_surface(*self.size).protected_region
        protected = pygame.Rect(chrome.x, chrome.y, chrome.width, chrome.height)
        for target in layer.targets:
            self.assertFalse(target.rect.colliderect(protected), target.control_id)

    def test_stamp_sheet_is_keyboard_operable_and_escape_closes_it(self) -> None:
        app = self.make_app()
        app._open_stamp_sheet()
        sheet = app.surfaces.overlays[-1]
        app.handle_event(_key(pygame.K_RIGHT))
        app.handle_event(_key(pygame.K_RIGHT))
        self.assertEqual(sheet.layer.focused_id, "stamp.2")
        app.handle_event(_key(pygame.K_SPACE))
        self.assertEqual(app.stamp_id, STAMP_IDS[2])
        self.assertEqual(app.surfaces.overlays, ())
        app._open_stamp_sheet()
        app.handle_event(_key(pygame.K_ESCAPE))
        self.assertEqual(app.surfaces.overlays, ())
        self.assertTrue(app.running)

    def test_pointer_in_protected_chrome_never_paints_or_presses(self) -> None:
        app = self.make_app()
        chrome = ActivitySystemChromeLayout.for_surface(*self.size).home_hitbox
        point = (chrome.x + chrome.width // 2, chrome.y + chrome.height // 2)
        self.tap(app, point)
        self.assertFalse(app.drawing)
        self.assertEqual(app.history.items, ())
        self.assertEqual(app.mode, "paint")

    def test_controller_stick_moves_virtual_pointer_and_south_paints(self) -> None:
        axis_event = getattr(pygame, "CONTROLLERAXISMOTION", None)
        button_down = getattr(pygame, "CONTROLLERBUTTONDOWN", None)
        if axis_event is None or button_down is None:
            self.skipTest("SDL controller events unavailable")
        app = self.make_app()
        app.handle_event(pygame.event.Event(axis_event, axis=pygame.CONTROLLER_AXIS_LEFTX, value=30000, instance_id=0))
        self.assertTrue(app.controller_pointer.active)
        start = app.controller_pointer.position
        self.frame(app, 0.1)
        moved = app.controller_pointer.position
        self.assertGreater(moved[0], start[0])
        app.handle_event(pygame.event.Event(button_down, button=pygame.CONTROLLER_BUTTON_A, instance_id=0))
        self.assertTrue(app.drawing)
        self.frame(app, 0.1)
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONUP, button=pygame.CONTROLLER_BUTTON_A, instance_id=0))
        self.assertFalse(app.drawing)
        self.assertEqual(len(app.history.items), 1)
        self.assertGreater(len(app.history.items[0].points), 1)


class PaintingColouringTests(PaintingStudioTestCase):
    def test_colouring_page_outline_stays_on_top_and_is_flattened_on_save(self) -> None:
        app = self.make_app()
        self.assertEqual(set(app.renderer.outlines.available()), set(COLOURING_PAGES))
        self.tap(app, app.renderer.toolbar_rect("colouring").center)
        self.assertEqual(app.surfaces.overlays[-1].surface_id, "painting.pages")
        _panel, cards = app.renderer.colouring_sheet_rects(len(COLOURING_PAGES))
        self.tap(app, cards[0].center)
        self.assertEqual(app.page, COLOURING_PAGES[0])
        self.assertIsNotNone(app.outline)
        # An untouched colouring page is still only a draft (no blank saves).
        self.assertTrue(app._save())
        self.assertEqual(PaintingRepository(self.storage).list_records(), [])
        # Paint a wide black band across the canvas: the outline still shows.
        canvas = app.canvas_rect
        app._choose_color(0)
        app._choose_size(2)
        for y in range(canvas.top + 10, canvas.bottom - 10, 20):
            self.drag(app, [(canvas.left + 5, y), (canvas.right - 5, y)])
        self.assertTrue(app._save())
        records = PaintingRepository(self.storage).list_records()
        self.assertEqual(records[0].page, COLOURING_PAGES[0])
        stored = Image.open(io.BytesIO(self.storage.files[f"paintings/{records[0].painting_id}.png"])).convert("RGB")
        ink = sum(1 for pixel in stored.getdata() if abs(pixel[0] - 75) < 12 and abs(pixel[1] - 55) < 12 and abs(pixel[2] - 47) < 12)
        self.assertGreater(ink, 500, "flattened PNG must contain the outline ink")
        # Eraser removes paint, never the outline overlay.
        app._toggle_eraser()
        self.drag(app, [(canvas.left + 5, canvas.centery), (canvas.right - 5, canvas.centery)])
        self.assertIsNotNone(app.outline)

    def test_reopened_colouring_painting_keeps_its_page_after_resize(self) -> None:
        app = self.make_app()
        app._start_colouring(COLOURING_PAGES[1])
        canvas = app.canvas_rect
        self.drag(app, [(canvas.left + 30, canvas.top + 30), (canvas.left + 90, canvas.top + 60)])
        self.assertTrue(app._save())
        record_id = app.current.painting_id
        self.screen = pygame.display.set_mode((800, 480))
        app.handle_resize(pygame.event.Event(pygame.VIDEORESIZE, size=(800, 480), w=800, h=480))
        self.assertEqual(app.current.painting_id, record_id)
        self.assertEqual(app.page, COLOURING_PAGES[1])
        self.assertEqual(app.outline.get_size(), app.canvas_rect.size)


class PaintingDeleteTests(PaintingStudioTestCase):
    def seed(self, app: PaintingApp, count: int) -> None:
        png = _encode_png(app._new_blank_surface())
        for _ in range(count):
            app.repository.create(png)
        app.records = app.repository.list_records()

    def test_badge_delete_needs_confirmation_and_cancel_keeps_the_painting(self) -> None:
        app = self.make_app()
        self.seed(app, 3)
        app._enter_gallery()
        target = app.records[1]
        badge = app.controls.badges[1].rect
        self.tap(app, badge.center)
        self.assertEqual(app.pending_delete, target)
        sheet = app.surfaces.overlays[-1]
        self.assertEqual(sheet.layer.focused_id, "delete.cancel")  # cancel is the default
        app.handle_event(_key(pygame.K_SPACE))  # activates cancel
        self.assertEqual(app.surfaces.overlays, ())
        self.assertEqual(len(app.repository.list_records()), 3)
        # Confirm deletes exactly that painting (index first, then bytes).
        self.tap(app, badge.center)
        _panel, _cancel, confirm = app.renderer.delete_dialog_rects()
        self.tap(app, confirm.center)
        ids = [record.painting_id for record in app.repository.list_records()]
        self.assertEqual(len(ids), 2)
        self.assertNotIn(target.painting_id, ids)
        self.assertNotIn(f"paintings/{target.painting_id}.png", self.storage.files)
        self.assertEqual(app.mode, "gallery")

    def test_keyboard_delete_from_full_shelf_makes_room_for_new_work(self) -> None:
        app = self.make_app()
        self.seed(app, MAX_PAINTINGS)
        app._open(app.records[0])
        canvas = app.canvas_rect
        self.drag(app, [(canvas.left + 40, canvas.top + 40), (canvas.left + 80, canvas.top + 50)])
        self.assertTrue(app._save())
        app._press_new()  # refused: the full shelf opens instead of evicting
        self.assertEqual(app.mode, "gallery")
        self.assertGreater(app.library_full_until, self.clock.now)
        self.assertEqual(len(app.repository.list_records()), MAX_PAINTINGS)
        # Keyboard: last card -> page strip -> delete tile -> confirm.
        app.handle_event(_key(pygame.K_RIGHT))
        app.handle_event(_key(pygame.K_DOWN))  # second row of the grid
        self.assertEqual(app.gallery_focus, 4)
        focused = app.gallery_focus
        app.handle_event(_key(pygame.K_DOWN))  # leaves the grid for the page strip
        layer = app.controls.layer
        self.assertFalse(layer.focused_id.startswith("card."))
        while layer.focused_id != "gallery.delete":
            app.handle_event(_key(pygame.K_RIGHT if layer.focused_id == "gallery.previous" else pygame.K_LEFT))
        app.handle_event(_key(pygame.K_RETURN))
        doomed = app.pending_delete
        self.assertEqual(doomed, app.records[focused])
        app.handle_event(_key(pygame.K_RIGHT))
        app.handle_event(_key(pygame.K_RETURN))
        self.assertEqual(len(app.repository.list_records()), MAX_PAINTINGS - 1)
        app._toggle_gallery()
        app._press_new()
        self.assertEqual(app.mode, "paint")
        self.assertIsNone(app.current)

    def _ids(self, app: PaintingApp) -> list[str]:
        return [record.painting_id for record in app.repository.list_records()]

    def _ring_on_card_via_new(self, app: PaintingApp, presses: list[int]) -> None:
        """Park the ring on New, then let the kit carry it onto a card."""
        app._enter_gallery()
        app.controls.layer.focus("tool.new", visible=True)
        for key in presses:
            app.handle_event(_key(key))

    def test_ring_and_selection_agree_after_kit_moves_focus_onto_a_card(self) -> None:
        app = self.make_app()
        self.seed(app, 6)
        app._enter_gallery()
        self.assertEqual(app.gallery_focus, 0)
        app.controls.layer.focus("tool.new", visible=True)
        app.handle_event(_key(pygame.K_DOWN))  # the kit, not the app, picks a card
        slot = app.controls.focused_card_slot()
        self.assertIsNotNone(slot)
        self.assertEqual(app.gallery_focus, slot)
        app.handle_event(_key(pygame.K_UP))  # back up the grid / toolbar, wherever the kit goes
        slot = app.controls.focused_card_slot()
        if slot is not None:
            self.assertEqual(app.gallery_focus, slot)

    def test_keyboard_delete_removes_exactly_the_card_the_ring_is_on(self) -> None:
        app = self.make_app()
        self.seed(app, 6)
        before = self._ids(app)
        self._ring_on_card_via_new(app, [pygame.K_DOWN])
        slot = app.controls.focused_card_slot()
        self.assertIsNotNone(slot)
        self.assertNotEqual(slot, 0)  # the kit landed away from the stale index
        layer = app.controls.layer
        selected = slot  # the card the ring stood on is the selection
        layer.focus("gallery.delete", visible=True)  # ring leaves the grid for the tile
        self.assertEqual(app.gallery_focus, selected)
        doomed = before[selected]
        app.handle_event(_key(pygame.K_RETURN))
        self.assertEqual(app.pending_delete.painting_id, doomed)
        app.handle_event(_key(pygame.K_RIGHT))  # cancel -> confirm
        app.handle_event(_key(pygame.K_RETURN))
        self.assertEqual(self._ids(app), [pid for pid in before if pid != doomed])

    def test_keyboard_delete_key_on_a_card_targets_that_card(self) -> None:
        app = self.make_app()
        self.seed(app, 6)
        before = self._ids(app)
        self._ring_on_card_via_new(app, [pygame.K_DOWN, pygame.K_RIGHT])
        slot = app.controls.focused_card_slot()
        app._ask_delete_focused()  # same action the delete tile runs
        self.assertEqual(app.pending_delete.painting_id, before[slot])

    def test_open_after_kit_focus_move_opens_the_ringed_painting(self) -> None:
        app = self.make_app()
        self.seed(app, 6)
        before = self._ids(app)
        self._ring_on_card_via_new(app, [pygame.K_DOWN])
        slot = app.controls.focused_card_slot()
        app.handle_event(_key(pygame.K_RETURN))
        self.assertEqual(app.mode, "paint")
        self.assertEqual(app.current.painting_id, before[slot])

    def test_page_step_keeps_ring_on_the_selected_card(self) -> None:
        app = self.make_app()
        self.seed(app, GALLERY_PAGE_SIZE + 3)
        before = self._ids(app)
        app._enter_gallery()
        app.controls.layer.focus("card.2", visible=True)
        app.gallery_focus = 2
        app.handle_event(_key(pygame.K_PAGEDOWN))
        self.assertEqual(app.gallery_focus, GALLERY_PAGE_SIZE)
        self.assertEqual(app.controls.focused_card_slot(), 0)
        app.handle_event(_key(pygame.K_RIGHT))  # sync must not drift to page_first + stale slot
        app._ask_delete_focused()
        self.assertEqual(app.pending_delete.painting_id, before[GALLERY_PAGE_SIZE + 1])

    def test_pointer_taps_still_target_the_tapped_card(self) -> None:
        app = self.make_app()
        self.seed(app, 6)
        before = self._ids(app)
        app._enter_gallery()
        app.controls.layer.focus("card.0", visible=False)  # stale hidden ring
        self.tap(app, app.controls.badges[4].rect.center)
        self.assertEqual(app.pending_delete.painting_id, before[4])
        app._close_sheet()
        # The delete tile after a tap acts on the card that was tapped.
        self.tap(app, app.controls.cards[3].rect.center)
        self.assertEqual(app.current.painting_id, before[3])
        app._enter_gallery()
        self.assertEqual(app.gallery_focus, 3)

    def test_gallery_cards_page_through_every_painting_after_delete(self) -> None:
        app = self.make_app()
        self.seed(app, GALLERY_PAGE_SIZE + 1)
        app._enter_gallery()
        app._gallery_page_step(1)
        self.assertEqual(len(app.controls.cards), 1)
        app._ask_delete_index(GALLERY_PAGE_SIZE)
        app._confirm_delete()
        self.assertEqual(len(app.records), GALLERY_PAGE_SIZE)
        self.assertEqual(app.gallery_focus, GALLERY_PAGE_SIZE - 1)
        self.frame(app)


class PaintingModelMigrationTests(unittest.TestCase):
    def test_existing_index_entries_load_and_keep_their_page(self) -> None:
        storage = MemoryStorage()
        legacy = "0123456789abcdef0123456789abcdef"
        storage.kv[INDEX_KEY] = [
            {"id": legacy},
            {"id": "f" * 32, "page": "unknown-page"},
            {"id": "e" * 32, "page": COLOURING_PAGES[0]},
        ]
        repository = PaintingRepository(storage)
        records = repository.list_records()
        self.assertEqual(records[0], PaintingRecord(legacy))
        self.assertIsNone(records[1].page)
        self.assertEqual(records[2].page, COLOURING_PAGES[0])
        repository.save_png("e" * 32, b"png")
        self.assertEqual(storage.kv[INDEX_KEY][0], {"id": "e" * 32, "page": COLOURING_PAGES[0]})
        self.assertIn({"id": legacy}, storage.kv[INDEX_KEY])

    def test_delete_rejects_unknown_ids_and_never_touches_others(self) -> None:
        storage = MemoryStorage()
        repository = PaintingRepository(storage)
        first = repository.create(b"one")
        second = repository.create(b"two")
        self.assertFalse(repository.delete("a" * 32))
        with self.assertRaises(ValueError):
            repository.delete("../escape")
        self.assertTrue(repository.delete(first.painting_id))
        self.assertEqual(repository.list_records(), [second])
        self.assertEqual(repository.load_png(second.painting_id), b"two")


class PaintingArtTests(unittest.TestCase):
    def test_stamps_resolve_through_the_shared_library(self) -> None:
        for asset_id in STAMP_IDS:
            with self.subTest(asset_id=asset_id):
                self.assertTrue(get_shared_visual_path(asset_id).is_file())

    def test_private_art_has_source_svg_and_runtime_png(self) -> None:
        for name in ("tool_gallery", "tool_colouring", *(f"colouring_{page}" for page in COLOURING_PAGES)):
            with self.subTest(name=name):
                source = ACTIVITY / "assets" / "source" / f"{name}.svg"
                self.assertTrue(source.is_file())
                text = source.read_text(encoding="utf-8")
                for forbidden in ("<image", "<text", "<filter", "<style", "<mask", "data:"):
                    self.assertNotIn(forbidden, text)
                self.assertTrue((ACTIVITY / "assets" / "runtime" / f"{name}.png").is_file())

    def test_resized_paintings_keep_their_aspect(self) -> None:
        pygame.init()
        pygame.display.set_mode((64, 64))
        square = pygame.Surface((100, 100))
        square.fill((239, 77, 83))
        decoded = _decode_png(_encode_png(square), (300, 100))
        self.assertEqual(decoded.get_size(), (300, 100))
        self.assertEqual(decoded.get_at((150, 50))[:3], (239, 77, 83))
        self.assertEqual(decoded.get_at((10, 50))[:3], (255, 255, 255))  # letterboxed, not stretched
        grown = _decode_png(_encode_png(square), (400, 400))
        self.assertEqual(grown.get_at((395, 395))[:3], (239, 77, 83))  # small art scales up too


if __name__ == "__main__":
    unittest.main()

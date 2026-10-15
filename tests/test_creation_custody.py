"""Child-work custody regressions for the creative Activities.

A child must never lose, silently evict, or be unable to reach their own work:

* Painting / Writing galleries page over *every* saved item;
* New does not persist blank/empty items;
* Teatrino refuses a 17th show instead of evicting the oldest;
* Teatrino / Storie never delete a show/story on a single tap;
* Momo's emotion quiz never speaks the answer;
* Shape Garden / Teatrino / Orchestra keep a visible Greia pointer.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform.activity_ui import ChildUiMetrics


class MemoryStorage:
    """Minimal profile-scoped Activity storage."""

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
        self.files.pop(name, None)
        return True

    def file_list(self, prefix=""):
        return [name for name in self.files if name.startswith(prefix)]


def _theme():
    return SimpleNamespace(
        background=(255, 250, 240), panel=(247, 235, 203), accent=(255, 194, 52),
        text=(61, 44, 31), accent_text=(255, 255, 255),
    )


def _screen(size=(1024, 600)) -> pygame.Surface:
    pygame.init()
    return pygame.display.set_mode(size)


# ---------------------------------------------------------------- Painting

from activities.painting.painting_app import PaintingApp
from activities.painting.painting_content import GALLERY_PAGE_SIZE as PAINT_PAGE, MAX_PAINTINGS
from activities.painting.painting_model import PaintingRepository


class PaintingCustodyTests(unittest.TestCase):
    def make_app(self, storage=None) -> PaintingApp:
        screen = _screen()
        storage = storage if storage is not None else MemoryStorage()
        return PaintingApp(
            screen, ChildUiMetrics.for_size(*screen.get_size()), _theme(),
            PaintingRepository(storage), None,
        )

    def draw_dot(self, app: PaintingApp, offset: int = 0) -> None:
        rect = app.canvas_rect
        pos = (rect.left + 80 + offset, rect.top + 80)
        app.handle_pointer_down(pos)
        app.handle_pointer_up(pos)

    def seed_records(self, app: PaintingApp, count: int) -> None:
        from activities.painting.painting_renderer import _encode_png

        png = _encode_png(app._new_blank_surface())
        for _ in range(count):
            app.repository.create(png)
        app.records = app.repository.list_records()

    def test_gallery_pages_cover_every_saved_painting(self) -> None:
        app = self.make_app()
        self.seed_records(app, MAX_PAINTINGS)
        records = app.records
        self.assertEqual(len(records), MAX_PAINTINGS)
        pages = app.renderer.gallery_page_count(len(records))
        self.assertEqual(pages, MAX_PAINTINGS // PAINT_PAGE)
        seen = []
        for page in range(pages):
            cards = app.renderer.gallery_cards(records, page)
            self.assertLessEqual(len(cards), PAINT_PAGE)
            seen.extend(record.painting_id for _, record in cards)
        self.assertEqual(seen, [record.painting_id for record in records])
        previous, following = app.renderer.gallery_nav_buttons()
        self.assertGreaterEqual(previous.height, 44)
        self.assertGreaterEqual(following.width, 64)
        self.assertFalse(previous.colliderect(following))

    def test_keyboard_and_arrow_buttons_reach_the_last_painting(self) -> None:
        app = self.make_app()
        self.seed_records(app, MAX_PAINTINGS)
        app._enter_gallery()
        self.assertEqual(app.mode, "gallery")
        self.assertEqual(app.gallery_focus, 0)
        # Page arrows (pointer / virtual pointer) walk every page.
        _, following = app.renderer.gallery_nav_buttons()
        pages = app.renderer.gallery_page_count(len(app.records))
        for _ in range(pages - 1):
            app._mouse_up(following.center)
        self.assertEqual(app.gallery_focus // PAINT_PAGE, pages - 1)
        # Keyboard / controller (arrows) reach the very last item as well.
        app.gallery_focus = 0
        for _ in range(len(app.records)):
            app.handle_key(SimpleNamespace(key=pygame.K_RIGHT))
        self.assertEqual(app.gallery_focus, len(app.records) - 1)
        app.handle_key(SimpleNamespace(key=pygame.K_PAGEUP))
        self.assertEqual(app.gallery_focus, (pages - 2) * PAINT_PAGE)

    def test_clicking_a_card_on_a_later_page_opens_that_painting(self) -> None:
        app = self.make_app()
        png = __import__("activities.painting.painting_renderer", fromlist=["_encode_png"])._encode_png(
            app._new_blank_surface()
        )
        for _ in range(8):
            app.repository.create(png)
        app.records = app.repository.list_records()
        app._enter_gallery()
        app._gallery_page_step(1)
        rect, record = app.renderer.gallery_cards(app.records, 1)[0]
        self.assertGreaterEqual(app.records.index(record), PAINT_PAGE)
        app._mouse_up(rect.center)
        self.assertEqual(app.mode, "paint")
        self.assertEqual(app.current.painting_id, record.painting_id)

    def test_new_never_persists_blank_paintings(self) -> None:
        storage = MemoryStorage()
        app = self.make_app(storage)
        self.assertEqual(storage.files, {})
        self.assertEqual(app.repository.list_records(), [])
        for _ in range(5):
            app._new()
        self.assertEqual(app.repository.list_records(), [])
        self.assertEqual(storage.files, {})
        # Draw: the first stroke creates exactly one record on save.
        self.draw_dot(app)
        self.assertTrue(app._save())
        self.assertEqual(len(app.repository.list_records()), 1)
        # New + New + New on the saved painting starts one blank draft only.
        for _ in range(3):
            app._new()
        self.assertIsNone(app.current)
        self.assertEqual(len(app.repository.list_records()), 1)
        # Drawing on the draft saves it as a second record.
        self.draw_dot(app, 40)
        self.assertTrue(app._save())
        self.assertEqual(len(app.repository.list_records()), 2)
        self.assertEqual(len([n for n in storage.files if n.endswith(".png")]), 2)

    def test_drawn_then_erased_draft_is_not_persisted(self) -> None:
        storage = MemoryStorage()
        app = self.make_app(storage)
        self.draw_dot(app)
        app._undo()
        self.assertTrue(app._save())
        self.assertEqual(app.repository.list_records(), [])

    def test_new_at_the_library_cap_keeps_work_and_opens_the_full_gallery(self) -> None:
        app = self.make_app()
        self.seed_records(app, MAX_PAINTINGS)
        app._open(app.records[0])
        self.draw_dot(app)
        self.assertTrue(app._save())
        count = len(app.repository.list_records())
        app._new()
        self.assertEqual(app.mode, "gallery")
        self.assertGreater(app.library_full_until, 0.0)
        self.assertEqual(len(app.repository.list_records()), count)
        self.assertIsNotNone(app.current)

    def test_resize_keeps_unsaved_draft_strokes(self) -> None:
        storage = MemoryStorage()
        app = self.make_app(storage)
        self.draw_dot(app)
        app.handle_resize(SimpleNamespace())
        self.assertEqual(len(app.repository.list_records()), 1)


# ----------------------------------------------------------------- Writing

from activities.writing.writing_app import WritingApp
from activities.writing.writing_content import GALLERY_PAGE_SIZE as WRITE_PAGE, MAX_DOCUMENTS
from activities.writing.writing_model import DocumentRepository
from greia_platform.typography import GreiaTypography


class WritingCustodyTests(unittest.TestCase):
    def make_app(self, storage=None) -> WritingApp:
        screen = _screen()
        storage = storage if storage is not None else MemoryStorage()
        return WritingApp(
            screen, None, ChildUiMetrics.for_size(*screen.get_size()), GreiaTypography(),
            _theme(), DocumentRepository(storage), None,
        )

    def seed(self, app: WritingApp, count: int) -> None:
        for index in range(count):
            app.repository.create_text(f"page {index}")
        app.records = app.repository.list_records()

    def test_gallery_pages_cover_every_saved_document(self) -> None:
        app = self.make_app()
        self.seed(app, MAX_DOCUMENTS)
        pages = app.renderer.gallery_page_count(len(app.records))
        self.assertEqual(pages, MAX_DOCUMENTS // WRITE_PAGE)
        seen = []
        for page in range(pages):
            cards = app.renderer.gallery_cards(app.editor_rect, app.records, page)
            self.assertLessEqual(len(cards), WRITE_PAGE)
            seen.extend(record.document_id for _, record in cards)
        self.assertEqual(seen, [record.document_id for record in app.records])
        previous, following = app.renderer.gallery_nav_buttons(app.editor_rect)
        self.assertFalse(previous.colliderect(following))
        for rect, _ in app.renderer.gallery_cards(app.editor_rect, app.records, 0):
            self.assertFalse(rect.colliderect(previous))
            self.assertFalse(rect.colliderect(following))

    def test_keyboard_and_arrows_reach_the_last_document(self) -> None:
        app = self.make_app()
        self.seed(app, MAX_DOCUMENTS)
        app._enter_gallery()
        for _ in range(len(app.records)):
            app.handle_key(SimpleNamespace(key=pygame.K_RIGHT, mod=0))
        self.assertEqual(app.gallery_focus, len(app.records) - 1)
        app.handle_key(SimpleNamespace(key=pygame.K_RETURN, mod=0))
        self.assertEqual(app.mode, "edit")
        self.assertEqual(app.current.document_id, app.records[-1].document_id)

    def test_pointer_arrows_page_through_the_library(self) -> None:
        app = self.make_app()
        self.seed(app, MAX_DOCUMENTS)
        app._enter_gallery()
        _, following = app.renderer.gallery_nav_buttons(app.editor_rect)
        pages = app.renderer.gallery_page_count(len(app.records))
        for _ in range(pages - 1):
            app.handle_pointer(following.center)
        self.assertEqual(app.gallery_focus // WRITE_PAGE, pages - 1)
        rect, record = app.renderer.gallery_cards(app.editor_rect, app.records, pages - 1)[0]
        app.handle_pointer(rect.center)
        self.assertEqual(app.current.document_id, record.document_id)

    def test_new_never_persists_blank_documents(self) -> None:
        storage = MemoryStorage()
        app = self.make_app(storage)
        self.assertEqual(storage.files, {})
        for _ in range(5):
            app._new()
        self.assertEqual(app.repository.list_records(), [])
        self.assertEqual(storage.files, {})
        app._apply_edit(lambda: app.buffer.insert("hello"))
        self.assertTrue(app._save())
        self.assertEqual(len(app.repository.list_records()), 1)
        for _ in range(3):
            app._new()
        self.assertIsNone(app.current)
        self.assertEqual(len(app.repository.list_records()), 1)
        app._apply_edit(lambda: app.buffer.insert("again"))
        self.assertTrue(app._save())
        self.assertEqual(len(app.repository.list_records()), 2)

    def test_typed_then_deleted_draft_is_not_persisted(self) -> None:
        storage = MemoryStorage()
        app = self.make_app(storage)
        app._apply_edit(lambda: app.buffer.insert("x"))
        app._apply_edit(app.buffer.backspace)
        self.assertTrue(app._save())
        self.assertEqual(app.repository.list_records(), [])

    def test_new_at_the_library_cap_keeps_work_and_opens_the_full_gallery(self) -> None:
        app = self.make_app()
        self.seed(app, MAX_DOCUMENTS)
        app._open(app.records[0])
        app._new()
        # The open document has text, so New must refuse rather than evict.
        self.assertEqual(app.mode, "gallery")
        self.assertEqual(len(app.repository.list_records()), MAX_DOCUMENTS)
        self.assertGreater(app.library_full_until, 0.0)


# ---------------------------------------------------------------- Teatrino

from activities.teatrino_fiabe.teatrino_content import MAX_SAVED_SHOWS
from activities.teatrino_fiabe.teatrino_model import (
    DeleteConfirmation as ShowDeleteConfirmation,
    ShowLibraryFullError,
    ShowRepository,
)
from teatrino_doubles import MemoryStorage as TeatrinoStorage
from teatrino_doubles import advance as teatrino_advance
from teatrino_doubles import make_app as make_teatrino_app


class TeatrinoCustodyTests(unittest.TestCase):
    def full_storage(self) -> TeatrinoStorage:
        storage = TeatrinoStorage()
        repo = ShowRepository(storage)
        for index in range(MAX_SAVED_SHOWS):
            repo.save_show("cottage", [{"id": "lilli"}], [], [], 1.0, b"RIFF" + bytes([index]))
        return storage

    def open_library(self, storage: TeatrinoStorage):
        app = make_teatrino_app(storage=storage)
        app.tap(app.layout.shows.center)
        self.assertEqual(app.top_sheet, "teatrino.library")
        return app

    def delete_badge(self, app):
        return app.library.controls.badges[0].rect.center

    def dialog_button(self, app, control_id: str):
        return app.surfaces.overlays[-1].layer.target(control_id).rect.center

    def test_full_shelf_never_silently_evicts(self) -> None:
        repo = ShowRepository(self.full_storage())
        ids = [item["id"] for item in repo.list_shows()]
        with self.assertRaises(ShowLibraryFullError):
            repo.save_show("forest", [], [], [], 1.0, b"RIFF-extra")
        self.assertEqual([item["id"] for item in repo.list_shows()], ids)

    def test_recording_is_refused_up_front_when_the_shelf_is_full(self) -> None:
        storage = self.full_storage()
        app = make_teatrino_app(storage=storage)
        app.tap(app.layout.rec.center)
        teatrino_advance(app, 3.0)
        self.assertEqual(app.mic_recorder.started, 0)
        self.assertFalse(app.is_recording)
        self.assertEqual(app.top_sheet, "teatrino.library", "the shows open, pictorially full")
        self.assertTrue(app.library.full)
        self.assertEqual(app.library.controls.shelf.current, MAX_SAVED_SHOWS)
        self.assertEqual(len(app.show_repo.list_shows()), MAX_SAVED_SHOWS)

    def test_every_saved_show_is_reachable_by_paging(self) -> None:
        app = self.open_library(self.full_storage())
        shown = 0
        for _page in range(app.library.pages):
            shown += sum(1 for card in app.library.controls.cards if card.icon is not None)
            app.tap(app.library.controls.following.rect.center)
        self.assertEqual(shown, MAX_SAVED_SHOWS)

    def test_single_tap_on_delete_does_not_delete(self) -> None:
        app = self.open_library(self.full_storage())
        app.tap(self.delete_badge(app))
        self.assertIsNotNone(app.delete_confirm)
        self.assertEqual(len(app.show_repo.list_shows()), MAX_SAVED_SHOWS)

    def test_dialog_defaults_to_keep_and_ignores_a_double_tap(self) -> None:
        app = self.open_library(self.full_storage())
        app.tap(self.delete_badge(app))
        self.assertEqual(app.delete_confirm.focus, ShowDeleteConfirmation.KEEP)
        app.press(pygame.K_RETURN)  # Space/Enter/south button on the default focus keeps
        self.assertIsNone(app.delete_confirm)
        self.assertEqual(len(app.show_repo.list_shows()), MAX_SAVED_SHOWS)
        app.tap(self.delete_badge(app))
        app.tap(self.dialog_button(app, "delete.confirm"))  # immediate second tap: not armed
        self.assertIsNotNone(app.delete_confirm)
        self.assertEqual(len(app.show_repo.list_shows()), MAX_SAVED_SHOWS)

    def test_deliberate_confirmation_deletes_exactly_that_show(self) -> None:
        storage = self.full_storage()
        app = self.open_library(storage)
        target = app.library_shows[0]["id"]
        app.tap(self.delete_badge(app))
        teatrino_advance(app, 1.0)  # the dialog arms
        app.tap(self.dialog_button(app, "delete.confirm"))
        self.assertIsNone(app.delete_confirm)
        remaining = [item["id"] for item in app.show_repo.list_shows()]
        self.assertEqual(len(remaining), MAX_SAVED_SHOWS - 1)
        self.assertNotIn(target, remaining)
        self.assertNotIn(ShowRepository._show_json_name(target), storage.files)
        self.assertEqual(app.top_sheet, "teatrino.library", "back on the shelf after deleting")

    def test_keyboard_confirm_path_and_cancel(self) -> None:
        app = self.open_library(self.full_storage())
        app.tap(self.delete_badge(app))
        app.press(pygame.K_RIGHT)  # the delete button is not armed yet: focus stays on keep
        self.assertEqual(app.delete_confirm.focus, ShowDeleteConfirmation.KEEP)
        teatrino_advance(app, 1.0)
        app.press(pygame.K_RIGHT)  # armed: focus -> delete
        self.assertEqual(app.delete_confirm.focus, ShowDeleteConfirmation.DELETE)
        app.press(pygame.K_ESCAPE)  # escape always keeps
        self.assertEqual(len(app.show_repo.list_shows()), MAX_SAVED_SHOWS)
        app.tap(self.delete_badge(app))
        teatrino_advance(app, 1.0)
        app.press(pygame.K_RIGHT)
        app.press(pygame.K_SPACE)
        self.assertEqual(len(app.show_repo.list_shows()), MAX_SAVED_SHOWS - 1)

    def test_tapping_outside_the_dialog_keeps_the_show(self) -> None:
        app = self.open_library(self.full_storage())
        app.tap(self.delete_badge(app))
        teatrino_advance(app, 1.0)
        app.tap((1020, 590))
        self.assertIsNone(app.delete_confirm)
        self.assertEqual(len(app.show_repo.list_shows()), MAX_SAVED_SHOWS)


# ------------------------------------------------------------------ Storie

_VOICE_DIR = ROOT / "activities" / "storie_della_mia_voce"
_VOICE_MODULES = (
    "voice_app", "voice_art", "voice_audio", "voice_content", "voice_controls", "voice_layout",
    "voice_microphone", "voice_model", "voice_renderer", "voice_services",
)


class _VoiceClock:
    now = 50.0

    def __call__(self) -> float:
        return self.now


class _SilentRecorder:
    available = True
    live_volume = 0.0

    def start(self) -> None:
        pass

    def stop(self, gain: float = 1.0):
        return None


class VoiceCustodyTests(unittest.TestCase):
    """Story shelf: deliberate delete (keep focused, arming delay), no eviction."""

    @classmethod
    def setUpClass(cls) -> None:
        # The Activity uses flat sibling imports (script style).
        sys.path.insert(0, str(_VOICE_DIR))
        cls._saved_modules = {name: sys.modules.pop(name) for name in list(sys.modules) if name in _VOICE_MODULES}
        import voice_app
        import voice_audio
        import voice_content
        import voice_services

        cls.voice_app = voice_app
        cls.voice_audio = voice_audio
        cls.voice_content = voice_content
        cls.voice_services = voice_services

    @classmethod
    def tearDownClass(cls) -> None:
        sys.path.remove(str(_VOICE_DIR))
        for name in _VOICE_MODULES:
            sys.modules.pop(name, None)
        sys.modules.update(cls._saved_modules)

    def make_app(self):
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography

        screen = _screen()
        store = MemoryStorage()
        services = self.voice_services
        repo = services.VoiceStorage.load(store)
        template = self.voice_content.STORIES[0]
        for index in range(3):
            repo.save_story(template.story_id, template.card_ids, {template.card_ids[0]: b"RIFF" + bytes([index])}, {})
        clock = _VoiceClock()
        app = self.voice_app.StoryApp(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            typography=GreiaTypography(),
            resources=None,
            audio=self.voice_audio.StoryAudio(),
            recorder=_SilentRecorder(),
            storage=repo,
            progress=services.StoryProgress.load(store),
            clock=clock,
        )
        app.open_shelf()
        return app, clock

    def badge(self, app, slot: int):
        return app.controls.badges[slot].rect.center

    def sheet_button(self, app, control_id: str):
        return app.sheet.layer.target(control_id).rect.center

    def test_single_tap_on_delete_does_not_delete(self) -> None:
        app, _ = self.make_app()
        app.tap(self.badge(app, 0))
        self.assertIsNotNone(app.delete_confirm)
        self.assertEqual(len(app.storage.stories), 3)

    def test_dialog_defaults_to_keep_and_ignores_a_double_tap(self) -> None:
        app, _ = self.make_app()
        app.tap(self.badge(app, 0))
        self.assertEqual(app.delete_confirm.focus, self.voice_services.DeleteConfirmation.KEEP)
        self.assertEqual(app.sheet.layer.focused_id, "delete.keep")
        app.press(pygame.K_SPACE)
        self.assertIsNone(app.delete_confirm)
        self.assertEqual(len(app.storage.stories), 3)
        app.tap(self.badge(app, 0))
        app.tap(self.sheet_button(app, "delete.confirm"))  # before the dialog armed
        self.assertIsNotNone(app.delete_confirm)
        self.assertEqual(len(app.storage.stories), 3)

    def test_deliberate_confirmation_deletes_exactly_that_story(self) -> None:
        app, clock = self.make_app()
        target = app.storage.stories[0].story_id
        app.tap(self.badge(app, 0))
        clock.now += 1.0
        app.tap(self.sheet_button(app, "delete.confirm"))
        self.assertIsNone(app.delete_confirm)
        remaining = [story.story_id for story in app.storage.stories]
        self.assertEqual(len(remaining), 2)
        self.assertNotIn(target, remaining)

    def test_keyboard_path_matches_teatrino(self) -> None:
        app, _ = self.make_app()
        app.controls.layer.focus("card.1", visible=True)
        app.controls.delete_focused.activate()
        self.assertEqual(app.delete_confirm.target_id, app.storage.stories[1].story_id)
        app.press(pygame.K_RIGHT)
        self.assertEqual(app.sheet.layer.focused_id, "delete.confirm")
        app.press(pygame.K_ESCAPE)
        self.assertEqual(len(app.storage.stories), 3)
        self.assertIsNone(app.delete_confirm)

    def test_tapping_outside_the_dialog_keeps_the_story(self) -> None:
        app, clock = self.make_app()
        app.tap(self.badge(app, 0))
        clock.now += 1.0
        app.tap((60, 300))
        self.assertIsNone(app.delete_confirm)
        self.assertEqual(len(app.storage.stories), 3)

    def test_both_activities_share_the_same_arming_delay_and_default(self) -> None:
        self.assertEqual(
            self.voice_services.DeleteConfirmation.ARM_SECONDS,
            ShowDeleteConfirmation.ARM_SECONDS,
        )
        self.assertEqual(
            self.voice_services.DeleteConfirmation("x", 0.0).focus,
            ShowDeleteConfirmation("x", 0.0).focus,
        )


# -------------------------------------------------------------------- Momo

from activities.faccine_momo.momo_app import MomoActivity
from activities.faccine_momo.momo_audio import MomoAudio
from activities.faccine_momo.momo_model import Emotion, GameMode, MomoModel
from activities.faccine_momo.momo_renderer import MomoRenderer


class MomoQuizDoesNotSpeakTheAnswerTests(unittest.TestCase):
    def make_app(self) -> MomoActivity:
        screen = _screen()
        audio = MomoAudio(ROOT / "activities" / "faccine_momo", locale="en")
        app = MomoActivity(screen, MomoRenderer(), audio, MomoModel())
        app.speech_queue._queue.clear()
        return app

    def queued(self, app: MomoActivity) -> list[str]:
        return [cue for cue, _ in app.speech_queue._queue]

    def test_entering_quiz_asks_but_never_names_the_target_emotion(self) -> None:
        app = self.make_app()
        app._handle_pointer_down(app.renderer.mode_button_rect.center)
        self.assertEqual(app.model.mode, GameMode.GUESS_EMOTION)
        cues = self.queued(app)
        self.assertIn("game_prompt", cues)
        emotion_names = {emotion.value for emotion in Emotion}
        self.assertFalse(emotion_names & set(cues), cues)

    def test_next_round_asks_but_never_names_the_target_emotion(self) -> None:
        app = self.make_app()
        app.model.mode = GameMode.GUESS_EMOTION
        app._quiz_advance_timer = 1e-9
        app.speech_queue.enqueue = mock.Mock()
        stop_after = {"n": 0}

        def stop_requested() -> bool:
            stop_after["n"] += 1
            return stop_after["n"] > 1

        with mock.patch("activities.faccine_momo.momo_app.activity_stop_requested", side_effect=stop_requested), \
                mock.patch("activities.faccine_momo.momo_app.mark_activity_ready"), \
                mock.patch("activities.faccine_momo.momo_app.pygame.quit"):
            app.run()
        cues = [call.args[0] for call in app.speech_queue.enqueue.call_args_list]
        self.assertEqual(cues, ["game_prompt"])


# -------------------------------------------------------- Greia pointer kept

class PointerStaysVisibleTests(unittest.TestCase):
    """Activities that hide the OS cursor must still present the Greia pointer."""

    def test_reference_canvas_default_present_draws_the_greia_pointer(self) -> None:
        from greia_platform.pygame_canvas import PygameReferenceCanvas

        screen = _screen()
        canvas = PygameReferenceCanvas(screen)
        target = canvas.target

        marker = (254, 202, 87)
        with mock.patch("pygame.mouse.get_focused", return_value=True), \
                mock.patch("pygame.mouse.get_pos", return_value=(500, 300)):
            canvas.present(clear=(0, 0, 0))
        hits = [
            target.get_at((500 + dx, 300 + dy))[:3] == marker
            for dx in range(-9, 10, 3) for dy in range(-9, 10, 3)
        ]
        self.assertTrue(any(hits))

    def test_pointer_hiding_activities_never_opt_out_of_the_default_pointer(self) -> None:
        for relative in (
            "shape_garden/garden_app.py",
            "teatrino_fiabe/teatrino_app.py",
            "orchestra_animali/orchestra_app.py",
        ):
            source = (ROOT / "activities" / relative).read_text(encoding="utf-8")
            self.assertIn("self.canvas.present(", source, relative)
            self.assertNotIn("pointer=False", source, relative)


class HeadlessCaptureStorageIsolationTests(unittest.TestCase):
    def test_headless_capture_never_defaults_to_the_developer_store(self) -> None:
        source = (ROOT / "tools" / "headless_greia_activity.py").read_text(encoding="utf-8")
        self.assertIn('"GREIA_STANDALONE_STORAGE_DIR"', source)
        self.assertIn('scratch / "standalone-storage"', source)
        self.assertIn("--storage-dir", source)


if __name__ == "__main__":
    unittest.main()

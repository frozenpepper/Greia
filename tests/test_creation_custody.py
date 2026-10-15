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

from activities.teatrino_fiabe.teatrino_app import TeatrinoApp
from activities.teatrino_fiabe.teatrino_content import MAX_SAVED_SHOWS
from activities.teatrino_fiabe.teatrino_model import (
    DeleteConfirmation as ShowDeleteConfirmation,
    ShowLibraryFullError,
    ShowRepository,
)
from activities.teatrino_fiabe.teatrino_renderer import (
    get_delete_dialog_layout,
    get_library_modal_layout,
)


class RecordingSound:
    def __init__(self) -> None:
        self.played: list[str] = []

    def play(self, sound_id: str) -> None:
        self.played.append(sound_id)


class TeatrinoCustodyTests(unittest.TestCase):
    def full_repo(self) -> tuple[ShowRepository, MemoryStorage]:
        storage = MemoryStorage()
        repo = ShowRepository(storage)
        for index in range(MAX_SAVED_SHOWS):
            repo.save_show("cottage", [{"id": "lilli", "name": "Lilli"}], [], [], 1.0, b"RIFF" + bytes([index]))
        return repo, storage

    def make_app(self, repo: ShowRepository) -> TeatrinoApp:
        app = object.__new__(TeatrinoApp)
        app.show_repo = repo
        app.library_shows = repo.list_shows()
        app.library_page = 0
        app.app_mode = "library"
        app.delete_confirm = None
        app.sound_mgr = RecordingSound()
        app.is_recording = False
        app.ui_strings = {}
        app.feedback_text = ""
        app.feedback_timer = 0.0
        return app

    def test_full_shelf_never_silently_evicts(self) -> None:
        repo, storage = self.full_repo()
        ids = [item["id"] for item in repo.list_shows()]
        with self.assertRaises(ShowLibraryFullError):
            repo.save_show("forest", [], [], [], 1.0, b"RIFF-extra")
        self.assertEqual([item["id"] for item in repo.list_shows()], ids)

    def test_recording_is_refused_up_front_when_the_shelf_is_full(self) -> None:
        repo, _ = self.full_repo()
        app = self.make_app(repo)
        app.app_mode = "stage"
        app.mic_recorder = SimpleNamespace(start_recording=mock.Mock())
        app.imported_narration = None
        self.assertFalse(app._start_recording())
        app.mic_recorder.start_recording.assert_not_called()
        self.assertFalse(app.is_recording)
        self.assertEqual(app.app_mode, "library")
        self.assertEqual(len(repo.list_shows()), MAX_SAVED_SHOWS)

    def test_persist_on_full_shelf_opens_the_library_and_keeps_shows(self) -> None:
        repo, _ = self.full_repo()
        app = self.make_app(repo)
        app.app_mode = "stage"
        app.puppets_on_stage = []
        app.recorded_frames = []
        app.recorded_sfx = []
        app.custom_backdrop_png = None
        self.assertIsNone(app._persist_recorded_show("cottage", 3.0, b"wav", feedback_seconds=2.0))
        self.assertEqual(app.app_mode, "library")
        self.assertEqual(len(repo.list_shows()), MAX_SAVED_SHOWS)

    def delete_button_pos(self, app: TeatrinoApp) -> tuple[int, int]:
        card = get_library_modal_layout(0, len(app.library_shows))["cards"][0]
        return card["del_btn"].center

    def test_single_tap_on_delete_does_not_delete(self) -> None:
        repo, _ = self.full_repo()
        app = self.make_app(repo)
        app._handle_mouse_down(*self.delete_button_pos(app))
        self.assertIsNotNone(app.delete_confirm)
        self.assertEqual(len(repo.list_shows()), MAX_SAVED_SHOWS)

    def test_dialog_defaults_to_keep_and_ignores_a_double_tap(self) -> None:
        repo, _ = self.full_repo()
        app = self.make_app(repo)
        app._handle_mouse_down(*self.delete_button_pos(app))
        self.assertEqual(app.delete_confirm.focus, ShowDeleteConfirmation.KEEP)
        # Space/Enter/south-button on the default focus keeps the show.
        app._handle_key_down(pygame.K_RETURN)
        self.assertIsNone(app.delete_confirm)
        self.assertEqual(len(repo.list_shows()), MAX_SAVED_SHOWS)
        # An immediate second tap on the delete button (before it is armed).
        app._handle_mouse_down(*self.delete_button_pos(app))
        app._handle_mouse_down(*get_delete_dialog_layout()["delete"].center)
        self.assertIsNotNone(app.delete_confirm)
        self.assertEqual(len(repo.list_shows()), MAX_SAVED_SHOWS)

    def test_deliberate_confirmation_deletes_exactly_that_show(self) -> None:
        repo, storage = self.full_repo()
        app = self.make_app(repo)
        target = app.library_shows[0]["id"]
        app._handle_mouse_down(*self.delete_button_pos(app))
        app.delete_confirm.opened_at -= 5.0  # dialog is armed
        app._handle_mouse_down(*get_delete_dialog_layout()["delete"].center)
        self.assertIsNone(app.delete_confirm)
        remaining = [item["id"] for item in repo.list_shows()]
        self.assertEqual(len(remaining), MAX_SAVED_SHOWS - 1)
        self.assertNotIn(target, remaining)
        self.assertNotIn(repo._show_json_name(target), storage.files)

    def test_keyboard_confirm_path_and_cancel(self) -> None:
        repo, _ = self.full_repo()
        app = self.make_app(repo)
        app._handle_mouse_down(*self.delete_button_pos(app))
        app._handle_key_down(pygame.K_RIGHT)  # focus -> delete
        self.assertEqual(app.delete_confirm.focus, ShowDeleteConfirmation.DELETE)
        app.delete_confirm.opened_at -= 5.0
        app._handle_key_down(pygame.K_ESCAPE)  # escape always keeps
        self.assertEqual(len(repo.list_shows()), MAX_SAVED_SHOWS)
        app._handle_mouse_down(*self.delete_button_pos(app))
        app._handle_key_down(pygame.K_RIGHT)
        app.delete_confirm.opened_at -= 5.0
        app._handle_key_down(pygame.K_SPACE)
        self.assertEqual(len(repo.list_shows()), MAX_SAVED_SHOWS - 1)

    def test_tapping_outside_the_dialog_keeps_the_show(self) -> None:
        repo, _ = self.full_repo()
        app = self.make_app(repo)
        app._handle_mouse_down(*self.delete_button_pos(app))
        app.delete_confirm.opened_at -= 5.0
        app._handle_mouse_down(5, 5)
        self.assertIsNone(app.delete_confirm)
        self.assertEqual(len(repo.list_shows()), MAX_SAVED_SHOWS)


# ------------------------------------------------------------------ Storie

_VOICE_DIR = ROOT / "activities" / "storie_della_mia_voce"


class VoiceCustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # The Activity uses flat sibling imports (script style).
        sys.path.insert(0, str(_VOICE_DIR))
        cls._saved_modules = {
            name: sys.modules.pop(name)
            for name in list(sys.modules)
            if name in {"voice_app", "voice_content", "voice_renderer", "voice_services", "voice_audio", "voice_microphone"}
        }
        import voice_app
        import voice_content
        import voice_renderer
        import voice_services

        cls.voice_app = voice_app
        cls.voice_content = voice_content
        cls.voice_renderer = voice_renderer
        cls.voice_services = voice_services

    @classmethod
    def tearDownClass(cls) -> None:
        sys.path.remove(str(_VOICE_DIR))
        for name in ("voice_app", "voice_content", "voice_renderer", "voice_services", "voice_audio", "voice_microphone"):
            sys.modules.pop(name, None)
        sys.modules.update(cls._saved_modules)

    def make_app(self):
        screen = _screen()
        storage = self.voice_services.VoiceStorage.load(MemoryStorage())
        scene_ids = [scene.scene_id for scene in self.voice_content.SCENES]
        for index in range(3):
            storage.save_story({scene_ids[0]: b"RIFF" + bytes([index])}, {scene_ids[0]: 1.0})
        app = object.__new__(self.voice_app.VoiceApp)
        app.screen = screen
        app.storage = storage
        app.renderer = self.voice_renderer.VoiceRenderer.build(screen)
        app.phase = self.voice_app.Phase.LIBRARY
        app.library_page = 0
        app.creations = None
        app.shared_scene_keys = set()
        app.delete_confirm = None
        app.current_channel = None
        app.current_sound = None
        return app

    def test_single_tap_on_delete_does_not_delete(self) -> None:
        app = self.make_app()
        app._handle_click(app.renderer.library_delete_rect(0).center)
        self.assertIsNotNone(app.delete_confirm)
        self.assertEqual(app.storage._library.count, 3)

    def test_dialog_defaults_to_keep_and_ignores_a_double_tap(self) -> None:
        app = self.make_app()
        app._handle_click(app.renderer.library_delete_rect(0).center)
        self.assertEqual(app.delete_confirm.focus, self.voice_services.DeleteConfirmation.KEEP)
        app._handle_delete_key(pygame.K_SPACE)
        self.assertIsNone(app.delete_confirm)
        self.assertEqual(app.storage._library.count, 3)
        app._handle_click(app.renderer.library_delete_rect(0).center)
        app._handle_click(app.renderer.delete_dialog_layout()["delete"].center)
        self.assertIsNotNone(app.delete_confirm)
        self.assertEqual(app.storage._library.count, 3)

    def test_deliberate_confirmation_deletes_exactly_that_story(self) -> None:
        app = self.make_app()
        target = app.storage._library.stories[0].story_id
        app._handle_click(app.renderer.library_delete_rect(0).center)
        app.delete_confirm.opened_at -= 5.0
        app._handle_click(app.renderer.delete_dialog_layout()["delete"].center)
        self.assertIsNone(app.delete_confirm)
        remaining = [story.story_id for story in app.storage._library.stories]
        self.assertEqual(len(remaining), 2)
        self.assertNotIn(target, remaining)

    def test_keyboard_path_matches_teatrino(self) -> None:
        app = self.make_app()
        app._handle_click(app.renderer.library_delete_rect(1).center)
        app._handle_delete_key(pygame.K_RIGHT)
        self.assertEqual(app.delete_confirm.focus, self.voice_services.DeleteConfirmation.DELETE)
        app._handle_delete_key(pygame.K_ESCAPE)
        self.assertEqual(app.storage._library.count, 3)
        self.assertIsNone(app.delete_confirm)

    def test_tapping_outside_the_dialog_keeps_the_story(self) -> None:
        app = self.make_app()
        app._handle_click(app.renderer.library_delete_rect(0).center)
        app.delete_confirm.opened_at -= 5.0
        app._handle_click((5, 5))
        self.assertIsNone(app.delete_confirm)
        self.assertEqual(app.storage._library.count, 3)

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

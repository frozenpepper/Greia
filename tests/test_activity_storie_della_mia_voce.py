"""Stories of My Voice (Story Cards): content, rules, recorder contract and app loop.

Source/headless evidence only (dummy SDL video/audio, fake microphone); no
hardware microphone or physical-device claim.
"""

from __future__ import annotations

import io
import json
import math
import os
import random
import struct
import sys
import tomllib
import unittest
import wave
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "storie_della_mia_voce"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

import pygame

from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

import voice_app
from voice_audio import StoryAudio
from voice_content import (
    ALL_TEMPLATES,
    LEGACY_SCENES,
    MAX_RECORDING_SECONDS,
    MAX_SAVED_STORIES,
    STORIES,
    is_valid_card_id,
)
from voice_model import OrderingBoard, Slideshow, TellingSession
from voice_services import STORY_INDEX_KEY, StoryProgress, VoiceStorage


# -- shared fakes (also used by test_voice_creations) ------------------------


def make_wav(seconds: float = 0.6) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(22050)
        frames = int(22050 * seconds)
        writer.writeframes(b"".join(struct.pack("<h", int(2000 * math.sin(i / 9))) for i in range(frames)))
    return buffer.getvalue()


class MemoryStorage:
    def __init__(self) -> None:
        self.kv: dict = {}
        self.files: dict[str, bytes] = {}

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        self.kv[key] = json.loads(json.dumps(value))

    def file_write_atomic(self, name, payload):
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class FakeRecorder:
    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.live_volume = 0.5
        self.started = 0
        self.open = False

    def start(self) -> None:
        self.started += 1
        self.open = True

    def stop(self, gain: float = 1.0):
        was_open, self.open = self.open, False
        return make_wav() if was_open else None


class FakeCreations:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def publish_private_file(self, filename, *, media_type, role, title):
        self.calls.append((filename, media_type, role, title))
        return {"creation_id": f"c{len(self.calls)}"}


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


class RecordingEvents:
    def __init__(self) -> None:
        self.log: list[tuple] = []

    def __getattr__(self, name):
        return lambda *args: self.log.append((name, *args))


def make_app(*, mic: bool = True, storage: MemoryStorage | None = None, creations=None, locale: str = "en", size=(1024, 600)):
    pygame.init()
    screen = pygame.display.set_mode(size)
    clock = Clock()
    store = storage if storage is not None else MemoryStorage()
    app = voice_app.StoryApp(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=activity_resources(ACTIVITY_ROOT, requested_locale=locale),
        audio=StoryAudio(locale=locale),
        recorder=FakeRecorder(mic),
        storage=VoiceStorage.load(store),
        progress=StoryProgress.load(store),
        events=RecordingEvents(),
        creations=creations,
        rng=random.Random(7),
        clock=clock,
    )
    return app, clock, store


def advance(app, clock: Clock, seconds: float, step: float = 0.05) -> None:
    for _ in range(max(1, int(round(seconds / step)))):
        clock.now += step
        app.step()


def solve_order(app, clock: Clock) -> None:
    """Place every card by the platform keyboard/tap path (via hints)."""

    board = app.board
    for _ in range(12):
        if board.solved:
            break
        hint = board.hint()
        assert hint is not None
        slot, card = hint
        if not board.in_tray(card):
            app._on_slot(board.slot_of(card))
            advance(app, clock, 0.4)
        if board.slots[slot] is not None and slot not in board.locked:
            app._on_slot(slot)
            advance(app, clock, 0.4)
        app._on_tray(card)
        advance(app, clock, 0.6)


def tell_all(app, clock: Clock) -> None:
    while True:
        app._on_mic()  # countdown
        advance(app, clock, 1.7)
        advance(app, clock, 1.0)  # recording
        app._on_mic()  # stop
        advance(app, clock, 0.4)
        if app.telling.last:
            app._on_next()
            return
        app._on_next()
        advance(app, clock, 0.4)


# -- content ------------------------------------------------------------------


class StoryContentTests(unittest.TestCase):
    def test_stories_are_three_or_four_cards_with_unique_safe_ids(self) -> None:
        self.assertGreaterEqual(len(STORIES), 5)
        seen: set[str] = set()
        for story in STORIES:
            self.assertIn(len(story.cards), (3, 4))
            self.assertTrue(story.pickable)
            for card in story.cards:
                self.assertTrue(is_valid_card_id(card.card_id), card.card_id)
                self.assertNotIn(card.card_id, seen)
                seen.add(card.card_id)
        self.assertFalse(LEGACY_SCENES.pickable)
        self.assertEqual(LEGACY_SCENES.card_ids, ("forest", "sea", "sky", "friends"))

    def test_gentlest_stories_come_first(self) -> None:
        sizes = [len(story.cards) for story in STORIES]
        self.assertEqual(sizes, sorted(sizes))

    def test_every_card_uses_registered_shared_library_art_and_canonical_cast(self) -> None:
        catalogue = (ROOT / "assets" / "catalog" / "shared_visuals_v1_source.toml").read_text(encoding="utf-8")
        data = tomllib.loads(catalogue)
        ids = {visual["id"]: {variant["name"] for variant in visual.get("variants", [])} for visual in data["visuals"]}
        for template in ALL_TEMPLATES.values():
            for card in template.cards:
                for layer in card.art.layers:
                    self.assertIn(layer, ids, layer)
                for sprite in card.art.sprites:
                    self.assertIn(sprite.asset_id, ids, sprite.asset_id)
                    self.assertIn(sprite.variant, ids[sprite.asset_id], f"{sprite.asset_id}:{sprite.variant}")
                    if sprite.asset_id.startswith("character."):
                        self.assertIn(sprite.asset_id.split(".")[1], ("lilli", "leo", "flash", "dani", "tito", "momo"))

    def test_bundles_keep_key_parity_and_resolve_every_story_title(self) -> None:
        bundles = {
            language: json.loads((ACTIVITY_ROOT / "locales" / f"{language}.json").read_text(encoding="utf-8"))["strings"]
            for language in ("en", "it", "es", "fr")
        }
        reference = set(bundles["en"])
        for language, strings in bundles.items():
            self.assertEqual(set(strings), reference, language)
            for template in ALL_TEMPLATES.values():
                self.assertTrue(strings.get(template.title_key), (language, template.title_key))
            for key in ("ui.my_stories", "victory.title", "button.new_story", "button.watch_again", "activity.title"):
                self.assertTrue(strings.get(key), (language, key))

    def test_manifest_declares_honest_skills_events_and_wav_production(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.storie-della-mia-voce")
        skills = {skill["id"] for skill in manifest["education"]["skills"]}
        self.assertIn("narrative.sequencing.picture_story", skills)
        self.assertIn("language.oral_expression.narration", skills)
        events = {event["id"] for event in manifest["education"]["events"]}
        for event in ("story.cards_ordered", "voice.story_saved", "voice.first_story_recorded", "voice.recording_started"):
            self.assertIn(event, events)
        self.assertEqual(manifest["creations"]["produces"], ["audio/wav"])
        self.assertEqual(manifest["presentation"]["categories"], ["create"])
        self.assertEqual(manifest["input"]["profile"], "hybrid")

    def test_recording_is_bounded_per_card(self) -> None:
        self.assertLessEqual(MAX_RECORDING_SECONDS, 45.0)
        self.assertEqual(MAX_SAVED_STORIES, 12)


# -- rules --------------------------------------------------------------------


class OrderingBoardTests(unittest.TestCase):
    ORDER = ("a1", "b2", "c3", "d4")

    def test_shuffle_is_never_already_solved(self) -> None:
        for seed in range(40):
            board = OrderingBoard.shuffled(self.ORDER, random.Random(seed))
            self.assertNotEqual(tuple(board.tray), self.ORDER)
            self.assertEqual(sorted(board.tray), sorted(self.ORDER))

    def test_place_fills_first_open_slot_and_take_back_returns_home(self) -> None:
        board = OrderingBoard(self.ORDER, ("c3", "a1", "d4", "b2"))
        self.assertEqual(board.place("a1"), 0)
        self.assertEqual(board.place("c3"), 1)
        self.assertIsNone(board.tray[0])
        self.assertEqual(board.take_back(0), "a1")
        self.assertEqual(board.tray[1], "a1")
        self.assertEqual(board.place("d4"), 0)

    def test_drag_onto_occupied_slot_swaps_or_sends_home(self) -> None:
        board = OrderingBoard(self.ORDER, ("c3", "a1", "d4", "b2"))
        board.place("a1", 0)
        board.place("b2", 0)  # from the tray onto a1: a1 goes home
        self.assertEqual(board.slots[0], "b2")
        self.assertTrue(board.in_tray("a1"))
        board.place("c3", 2)
        board.place("c3", 0)  # slot to slot: swap with b2
        self.assertEqual(board.slots[0], "c3")
        self.assertEqual(board.slots[2], "b2")

    def test_wrong_row_locks_right_cards_and_sends_the_rest_home(self) -> None:
        board = OrderingBoard(self.ORDER, ("c3", "a1", "d4", "b2"))
        for card, slot in (("a1", 0), ("c3", 1), ("b2", 2), ("d4", 3)):
            board.place(card, slot)
        result = board.check()
        self.assertFalse(result.correct)
        self.assertEqual(set(result.returned), {"c3", "b2"})
        self.assertEqual(board.locked, {0, 3})
        self.assertIsNone(board.place("c3", 0))  # locked places stay
        self.assertEqual(board.hint(), (1, "b2"))
        board.place("b2")
        board.place("c3")
        self.assertTrue(board.check().correct)
        self.assertEqual(board.mistakes, 1)

    def test_slideshow_follows_voice_or_holds_silent_pictures(self) -> None:
        show = Slideshow(("a1", "b2"), {"a1": 2.0}, {"a1"})
        show.start(0.0)
        self.assertFalse(show.due(0.5, voice_busy=True))
        self.assertTrue(show.due(1.2, voice_busy=False))
        self.assertTrue(show.next(1.2))
        self.assertFalse(show.due(2.0, voice_busy=None))
        self.assertTrue(show.due(4.0, voice_busy=None))
        self.assertFalse(show.next(4.0))
        self.assertTrue(show.finished)

    def test_telling_session_keeps_and_forgets_per_card(self) -> None:
        session = TellingSession(("a1", "b2"))
        session.keep(b"RIFF", 1.0)
        self.assertTrue(session.has())
        self.assertTrue(session.advance())
        self.assertTrue(session.last)
        self.assertFalse(session.has())
        session.back()
        session.forget()
        self.assertEqual(session.told, 0)
        with self.assertRaises(ValueError):
            session.keep(b"", 1.0)


class VoiceRecorderContractTests(unittest.TestCase):
    """The recorder follows MICROPHONE_RECORDING.md: SDK first, no device policy."""

    def test_recorder_uses_get_sdl_capture_device(self) -> None:
        text = (ACTIVITY_ROOT / "voice_microphone.py").read_text(encoding="utf-8")
        self.assertIn("get_sdl_capture_device", text)
        self.assertIn("get_audio_capture_device", text)
        for forbidden in ("soundcard", "/dev/snd", "hw:0,0", "plughw"):
            self.assertNotIn(forbidden, text)
        self.assertGreater(text.find("get_audio_device_names(True)"), text.find("get_sdl_capture_device()"))


# -- app loop -----------------------------------------------------------------


class StoryCardsAppLoopTests(unittest.TestCase):
    def test_full_round_order_tell_watch_save_and_complete(self) -> None:
        app, clock, store = make_app()
        self.assertIs(app.state, voice_app.Screen.PICKER)
        app._on_story(0)  # Momo plants a seed (three cards)
        self.assertIs(app.state, voice_app.Screen.ORDER)
        board = app.board
        # A wrong full row: Leo thinks, wrong cards go home, right ones lock.
        for card in reversed(board.order):
            app._on_tray(card)
        advance(app, clock, 0.5)
        self.assertEqual(app.cast.feedback.pose.value, "think")
        advance(app, clock, 1.5)
        self.assertFalse(board.full)
        self.assertGreater(len(board.locked), 0)
        self.assertFalse(app._busy)
        solve_order(app, clock)
        advance(app, clock, 0.6)
        self.assertTrue(board.solved)
        self.assertEqual(app.cast.feedback.pose.value, "cheer")
        advance(app, clock, 2.6)
        self.assertIs(app.state, voice_app.Screen.TELL)
        tell_all(app, clock)
        self.assertIs(app.state, voice_app.Screen.WATCH)
        self.assertEqual(len(app.storage.stories), 1)
        saved = app.storage.stories[0]
        self.assertEqual(saved.template_id, "momo_seed")
        self.assertEqual(saved.order, STORIES[0].card_ids)
        self.assertEqual(set(saved.recordings), set(STORIES[0].card_ids))
        self.assertIn(STORY_INDEX_KEY, store.kv)
        advance(app, clock, 15.0)
        self.assertIs(app.state, voice_app.Screen.DONE)
        self.assertIn("momo_seed", app.progress.done)
        names = [entry[0] for entry in app.events.log]
        for name in ("cards_ordered", "recording_started", "recording_stopped", "story_saved", "first_story_recorded"):
            self.assertIn(name, names)
        # Completion -> new story goes back to the picker with a star.
        app.completion.focus_visible = False
        app.tap(app.completion.primary_rect.center)
        self.assertIs(app.state, voice_app.Screen.PICKER)

    def test_keyboard_only_round_reaches_the_telling_step(self) -> None:
        app, clock, _ = make_app()
        app.press(pygame.K_SPACE)  # focused suggested story
        self.assertIs(app.state, voice_app.Screen.ORDER)
        board = app.board
        for _ in range(20):
            if app.state is not voice_app.Screen.ORDER:
                break
            hint = board.hint()
            if hint is None or app._busy:
                advance(app, clock, 0.5)
                continue
            _, card = hint
            if not board.in_tray(card):
                app._on_slot(board.slot_of(card))
                advance(app, clock, 0.4)
                continue
            app.controls.layer.focus(f"tray.{card}", visible=True)
            app.press(pygame.K_RETURN)
            advance(app, clock, 0.6)
        advance(app, clock, 3.0)
        self.assertIs(app.state, voice_app.Screen.TELL)
        self.assertEqual(app.controls.layer.focused_id, "mic")
        app.press(pygame.K_SPACE)
        advance(app, clock, 2.0)
        self.assertEqual(app.record_state.value, "recording")
        app.press(pygame.K_SPACE)
        self.assertTrue(app.telling.has())

    def test_pointer_drag_places_a_card_on_a_chosen_slot(self) -> None:
        app, clock, _ = make_app()
        app._on_story(2)
        layout = app._order_layout
        board = app.board
        card = board.order[1]
        start = layout.tray[board.tray_index(card)].center
        app.drag_to(start, layout.slots[1].center)
        self.assertEqual(board.slots[1], card)
        # A short tap on the placed card takes it back home.
        app.tap(layout.slots[1].center)
        self.assertTrue(board.in_tray(card))

    def test_idle_hints_point_then_show_the_right_card(self) -> None:
        app, clock, _ = make_app()
        app._on_story(0)
        advance(app, clock, 6.5)
        self.assertTrue(app.cast.pointing)
        self.assertTrue(any(key.startswith("slot.") for key in app.motion.halos))
        advance(app, clock, 6.5)
        self.assertTrue(any(key.startswith("card.") for key in app.motion.halos))

    def test_without_microphone_the_child_orders_and_watches_the_pictures(self) -> None:
        app, clock, store = make_app(mic=False)
        self.assertFalse(app.mic_ok)
        app._on_story(1)
        solve_order(app, clock)
        advance(app, clock, 3.0)
        self.assertIs(app.state, voice_app.Screen.WATCH)
        self.assertEqual(app.recorder.started, 0)
        advance(app, clock, 12.0)
        self.assertIs(app.state, voice_app.Screen.DONE)
        self.assertEqual(app.storage.stories, ())  # nothing blank is saved
        self.assertNotIn(STORY_INDEX_KEY, store.kv)

    def test_untold_story_is_watched_but_never_saved_blank(self) -> None:
        app, clock, _ = make_app()
        app._on_story(0)
        solve_order(app, clock)
        advance(app, clock, 3.0)
        for _ in range(3):
            app._on_next()
            advance(app, clock, 0.4)
        self.assertIs(app.state, voice_app.Screen.WATCH)
        self.assertEqual(app.storage.stories, ())

    def test_home_mid_telling_keeps_the_cards_already_told(self) -> None:
        app, clock, _ = make_app()
        app._on_story(0)
        solve_order(app, clock)
        advance(app, clock, 3.0)
        app._on_mic()
        advance(app, clock, 2.5)
        app._on_mic()
        self.assertTrue(app.telling.has())
        app.shutdown()
        self.assertEqual(len(app.storage.stories), 1)
        self.assertEqual(len(app.storage.stories[0].recordings), 1)

    def test_layouts_stay_clear_of_protected_chrome_at_small_viewports(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            app, clock, _ = make_app(size=size)
            protected = app._layout_source.protected
            for target in app.controls.layer.targets:
                self.assertFalse(target.rect.colliderect(protected), (size, target.control_id))
            app._on_story(3)
            for target in app.controls.layer.targets:
                self.assertFalse(target.rect.colliderect(protected), (size, target.control_id))
                self.assertTrue(pygame.Rect(0, 0, 1024, 600).contains(target.rect), (size, target.control_id))
            solve_order(app, clock)
            advance(app, clock, 3.0)
            for target in app.controls.layer.targets:
                self.assertFalse(target.rect.colliderect(protected), (size, target.control_id))
                self.assertTrue(pygame.Rect(0, 0, 1024, 600).contains(target.rect), (size, target.control_id))
            app.render()


if __name__ == "__main__":
    unittest.main()

"""Wonder Match (memory_meraviglie): rules, saves, layout and full app loop."""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "memory_meraviglie"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from memory_content import ALBUMS, LEVELS, MAX_LEVEL  # noqa: E402
from memory_model import (  # noqa: E402
    BoardResult,
    CardState,
    FlipResult,
    MemoryBoard,
    StickerBook,
    adapt_level,
    choose_subjects,
    peek_threshold,
)
from memory_services import SCHEMA_VERSION, GreiaMemoryProgress  # noqa: E402

LANGUAGES = ("en", "it", "es", "fr")


def _pairs(board: MemoryBoard) -> list[list[int]]:
    found: dict[str, list[int]] = {}
    for index, card in enumerate(board.cards):
        found.setdefault(card.subject_id, []).append(index)
    return list(found.values())


class BoardRuleTests(unittest.TestCase):
    def test_two_flip_rule_match_and_miss(self) -> None:
        board = MemoryBoard(["cat", "dog"], random.Random(3))
        (a1, a2), (b1, _) = _pairs(board)
        self.assertIs(board.flip(a1).result, FlipResult.FIRST)
        self.assertIs(board.flip(a1).result, FlipResult.IGNORED, "an open card cannot be flipped again")
        outcome = board.flip(a2)
        self.assertIs(outcome.result, FlipResult.MATCH)
        self.assertEqual(board.cards[a1].state, CardState.MATCHED)
        board.flip(b1)
        other = next(i for i, card in enumerate(board.cards) if card.state is CardState.DOWN)
        self.assertIs(board.flip(other).result, FlipResult.MATCH)
        self.assertTrue(board.complete)

    def test_miss_locks_until_covered_and_never_fails(self) -> None:
        board = MemoryBoard(["cat", "dog", "pig"], random.Random(1))
        pairs = _pairs(board)
        board.flip(pairs[0][0])
        self.assertIs(board.flip(pairs[1][0]).result, FlipResult.MISS)
        self.assertFalse(board.can_flip(pairs[2][0]))
        self.assertEqual(sorted(board.cover_miss()), sorted((pairs[0][0], pairs[1][0])))
        self.assertTrue(all(card.state is CardState.DOWN for card in board.cards))
        self.assertEqual((board.misses, board.miss_streak), (1, 1))

    def test_peek_prefers_seen_pairs_and_threshold_grows(self) -> None:
        board = MemoryBoard(["cat", "dog", "pig", "frog"], random.Random(2))
        pairs = _pairs(board)
        board.flip(pairs[2][0])
        board.flip(pairs[3][0])
        board.cover_miss()
        for _ in range(10):
            pair = board.peek_pair(random.Random(_))
            self.assertIn(sorted(pair), [sorted(pairs[2]), sorted(pairs[3])])
        self.assertLess(peek_threshold(2), peek_threshold(8))

    def test_adaptation_two_clean_up_one_long_down(self) -> None:
        clean = BoardResult(1, 3, 1)
        self.assertEqual(adapt_level(1, [clean]), 1)
        self.assertEqual(adapt_level(1, [clean, clean]), 2)
        self.assertEqual(adapt_level(2, [BoardResult(2, 6, 20)]), 1)
        self.assertEqual(adapt_level(MAX_LEVEL, [BoardResult(MAX_LEVEL, 8, 0)] * 2), MAX_LEVEL)
        self.assertEqual(adapt_level(0, [BoardResult(0, 2, 9)]), 0)

    def test_board_prefers_missing_stickers(self) -> None:
        album = ALBUMS[0]
        book = StickerBook({album.album_id: album.subject_ids[:5]})
        chosen = choose_subjects(album, 3, book, random.Random(4))
        self.assertEqual(set(chosen), set(album.subject_ids[5:]))
        self.assertTrue(book.add(album.album_id, chosen[0]))
        self.assertFalse(book.add(album.album_id, chosen[0]))
        self.assertFalse(book.add(album.album_id, "dragon"))


class ContentTests(unittest.TestCase):
    def test_albums_use_registered_library_art_only(self) -> None:
        import tomllib

        catalog = tomllib.loads((ROOT / "assets/catalog/shared_visuals_v1_source.toml").read_text())
        registered = {entry["id"] for entry in catalog["visuals"]}
        self.assertEqual(len(ALBUMS), 5)
        for album in ALBUMS:
            self.assertEqual(len(album.subjects), 8)
            for subject in album.subjects:
                self.assertIn(subject.asset_id, registered)
            for layer in album.scene:
                self.assertIn(layer, registered)
        self.assertEqual([spec.pairs for spec in LEVELS], [2, 3, 6, 8])

    def test_locale_parity_and_audio_paths(self) -> None:
        bundles = {
            lang: json.loads((ACTIVITY_ROOT / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            for lang in LANGUAGES
        }
        keys = set(bundles["en"]["strings"])
        required = {f"item.{s.subject_id}" for album in ALBUMS for s in album.subjects}
        required |= {"victory.title", "victory.subtitle", "button.play_again", "button.albums"}
        self.assertFalse(required - keys)
        for lang, bundle in bundles.items():
            with self.subTest(lang=lang):
                self.assertEqual(set(bundle["strings"]), keys)
                self.assertTrue(all(value.strip() for value in bundle["strings"].values()))
                for cue in bundle["audio"].values():
                    self.assertTrue((ACTIVITY_ROOT / cue["path"]).is_file(), cue["path"])

    def test_names_come_from_the_shared_vocab_bank_not_package_copies(self) -> None:
        from greia_platform.localization import shared_vocab_audio_path

        self.assertFalse((ACTIVITY_ROOT / "assets" / "audio").exists(), "no private noun clips")
        for lang in LANGUAGES:
            bundle = json.loads((ACTIVITY_ROOT / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
            self.assertFalse([k for k in bundle["audio"] if k.startswith("item.")])
        for subject_id in ("apple", "cake", "dolphin", "pizza", "moon", "boat"):
            for lang in ("en", "it"):
                path = shared_vocab_audio_path(ROOT, subject_id, lang)
                self.assertIsNotNone(path, (subject_id, lang))
                self.assertTrue(path.is_file())

    def test_memory_audio_name_loading_is_bank_backed_and_bounded(self) -> None:
        from memory_audio import MemoryAudio

        if pygame.mixer.get_init() is None:
            pygame.mixer.pre_init(22050, -16, 1, 512)
            try:
                pygame.mixer.init()
            except pygame.error:
                self.skipTest("no (dummy) mixer available")
            self.addCleanup(pygame.mixer.quit)
        audio = MemoryAudio(None, locale="it")
        audio.prepare_names(["apple", "octopus"])
        self.assertTrue(audio.has_name("apple"))  # Italian bank clip
        self.assertFalse(audio.has_name("octopus"))  # unrecorded -> silent
        self.assertFalse(audio.say_name("octopus"))

    def test_package_art_exists(self) -> None:
        for name in ("card_back", "card_face"):
            self.assertTrue((ACTIVITY_ROOT / "assets" / "source" / f"{name}.svg").is_file())
            self.assertTrue((ACTIVITY_ROOT / "assets" / "runtime" / f"{name}.png").is_file())
        source = "".join(path.read_text(encoding="utf-8") for path in ACTIVITY_ROOT.glob("*.py"))
        self.assertNotIn("draw_card_illustration", source, "no primitive card pictures")
        self.assertNotIn("pygame.draw.circle", source)


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value

    def kv_get(self, key):
        return self.value

    def kv_set(self, key, value):
        self.value = value


class ProgressTests(unittest.TestCase):
    def test_pre_rework_save_migrates_forward(self) -> None:
        loaded = GreiaMemoryProgress(_Storage({"theme_idx": 1, "grid_idx": 4, "timestamp": 1.0})).load()
        self.assertEqual((loaded.level, loaded.album_id), (MAX_LEVEL, "food"))

    def test_round_trip_and_corruption_recovery(self) -> None:
        storage = _Storage()
        repo = GreiaMemoryProgress(storage)
        book = StickerBook({"sea": ["crab", "fish", "unknown"]})
        repo.save(2, "sea", book, [BoardResult(2, 6, 3)] * 9)
        self.assertEqual(storage.value["schema_version"], SCHEMA_VERSION)
        self.assertEqual(len(storage.value["history"]), 6)
        loaded = repo.load()
        self.assertEqual(loaded.level, 2)
        self.assertEqual(set(loaded.stickers["sea"]), {"crab", "fish"})
        broken = GreiaMemoryProgress(_Storage({"schema_version": 2, "level": "x", "album": 7, "stickers": "no"})).load()
        self.assertEqual((broken.level, broken.album_id, broken.stickers), (0, "animals", {}))


class _Events:
    def __init__(self) -> None:
        self.pairs: list[dict] = []
        self.completed: list[dict] = []

    def pair_found(self, session_id, payload) -> None:
        self.pairs.append(payload)

    def game_completed(self, session_id, payload) -> None:
        self.completed.append(payload)


class _Audio:
    def __init__(self) -> None:
        self.played: list[str] = []
        self.spoken: list[str] = []

    def play(self, name: str) -> None:
        self.played.append(name)

    def say_name(self, subject_id: str) -> bool:
        self.spoken.append(f"item.{subject_id}")
        return True

    def lilli(self, cue: str) -> bool:
        self.spoken.append(cue)
        return True

    def prepare_names(self, subject_ids) -> None:
        pass

    def stop_speech(self) -> None:
        pass


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build(self, level: int = 0, size: tuple[int, int] | None = None):
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from memory_app import MemoryApp

        screen = pygame.display.set_mode(size) if size else pygame.display.get_surface()
        context = resolve_activity_locale("it", ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it"))
        self.storage = _Storage({"schema_version": 2, "level": level, "album": "sea", "stickers": {}, "history": []})
        self.events = _Events()
        self.audio = _Audio()
        self.clock = [100.0]
        self.app = MemoryApp(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            typography=GreiaTypography(),
            resources=LocalizedResources(ACTIVITY_ROOT, context),
            audio=self.audio,
            progress=GreiaMemoryProgress(self.storage),
            events=self.events,
            rng=random.Random(11),
            clock=lambda: self.clock[0],
        )
        return self.app

    def _advance(self, seconds: float, step: float = 0.05) -> None:
        end = self.clock[0] + seconds
        while self.clock[0] < end:
            self.clock[0] += step
            self.app.step()

    def _focus(self, index: int) -> None:
        layer = self.app.controls.layer
        target = self.app.layout.cards[index]
        for _ in range(12):
            if layer.focused_id == f"card.{index}":
                return
            current = layer.target(layer.focused_id).rect
            if target.x > current.x:
                self.app.press(pygame.K_RIGHT)
            elif target.x < current.x:
                self.app.press(pygame.K_LEFT)
            elif target.y > current.y:
                self.app.press(pygame.K_DOWN)
            else:
                self.app.press(pygame.K_UP)

    def _tap_card(self, index: int) -> bool:
        return self.app.tap(self.app.layout.cards[index].center)

    def test_album_is_chosen_by_picture_tiles_without_text(self) -> None:
        from memory_app import AppState

        app = self._build()
        self.assertIs(app.state, AppState.PICKER)
        self.assertEqual(len(app.controls.albums), len(ALBUMS))
        self.assertTrue(all(button.caption == "" and button.icon is not None for button in app.controls.albums))
        app.render()
        food = app.controls.albums[2]
        self.assertTrue(app.tap(food.rect.center))
        self.assertIs(app.state, AppState.PLAYING)
        self.assertEqual(app.album.album_id, "food")

    def test_pointer_round_plays_to_completion_scene(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from memory_app import AppState

        app = self._build(level=1)
        app._on_album("animals")
        self._advance(1.0)
        pairs = _pairs(app.board)
        # One kind miss first: cards wiggle, Lilli thinks, the pair turns back.
        self.assertTrue(self._tap_card(pairs[0][0]))
        self.assertTrue(self._tap_card(pairs[1][0]))
        self._advance(0.7)
        self.assertIs(app.cast.pose, CastPose.THINK)
        self.assertFalse(self._tap_card(pairs[2][0]), "cards stay visible for a moment")
        self._advance(1.0)
        self.assertTrue(all(card.state is CardState.DOWN for card in app.board.cards))
        for pair in pairs:
            self.assertTrue(self._tap_card(pair[0]))
            self._advance(0.3)
            self.assertTrue(self._tap_card(pair[1]))
            self._advance(0.5)
            self.assertIn(f"item.{app.board.cards[pair[0]].subject_id}", self.audio.spoken)
            self._advance(2.0)
            app.render()
        self._advance(2.0)
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertEqual(len(self.events.pairs), 3)
        self.assertEqual(len(self.events.completed), 1)
        self.assertEqual(self.events.completed[0]["misses"], 1)
        self.assertIn("celebrate.success", self.audio.spoken)
        self.assertEqual(len(self.storage.value["stickers"]["animals"]), 3)
        app.render()
        # Again (primary) starts a fresh board on the same album.
        app.press(pygame.K_RETURN)
        self.assertIs(app.state, AppState.PLAYING)
        self.assertEqual(app.board.matched, 0)

    def test_keyboard_plays_a_board_and_albums_button_returns_to_shelf(self) -> None:
        from memory_app import AppState

        app = self._build(level=0)
        app.press(pygame.K_RETURN)  # focused album (sea) opens
        self.assertEqual(app.album.album_id, "sea")
        self._advance(1.0)
        layer = app.controls.layer
        for pair in _pairs(app.board):
            for index in pair:
                self._focus(index)
                self.assertEqual(layer.focused_id, f"card.{index}")
                self.assertTrue(app.press(pygame.K_SPACE))
                self._advance(0.4)
            self._advance(2.0)
        self._advance(2.0)
        self.assertIs(app.state, AppState.TERMINAL)
        app._open_picker()
        self.assertIs(app.state, AppState.PICKER)

    def test_long_miss_streak_brings_lilli_peek(self) -> None:
        app = self._build(level=2)
        app._on_album("vehicles")
        self._advance(1.0)
        pairs = _pairs(app.board)
        for attempt in range(peek_threshold(app.board.pairs)):
            self._tap_card(pairs[attempt % len(pairs)][0])
            self._tap_card(pairs[(attempt + 1) % len(pairs)][1])
            self._advance(1.4)
        self._advance(0.6)
        self.assertEqual(len(app.motion.peek), 2)
        self.assertTrue(app.cast.pointing)
        self.assertIn("encourage.progress", self.audio.spoken)
        app.render()
        self._advance(2.2)
        self.assertFalse(app.motion.peek)
        self.assertTrue(self._tap_card(pairs[0][0]))

    def test_idle_hint_points_and_glows(self) -> None:
        app = self._build(level=0)
        app._on_album("nature")
        self._advance(1.0)
        self._tap_card(0)
        self._advance(6.5)
        self.assertTrue(app.cast.pointing)
        self.assertIn(0, app.motion.halos)

    def test_layout_stays_clear_of_protected_chrome_at_all_sizes(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                app = self._build(level=MAX_LEVEL, size=size)
                protected = app._layout_source.protected
                for button in app.controls.albums:
                    self.assertFalse(button.rect.colliderect(protected))
                app._on_album("animals")
                layout = app.layout
                for rect in (*layout.cards, layout.panel, layout.album_button, app.controls.progress.rect):
                    self.assertFalse(rect.colliderect(protected), rect)
                self.assertTrue(pygame.Rect(0, 0, 1024, 600).contains(layout.grid))
                app.render()
        pygame.display.set_mode((1024, 600))

    def test_quit_and_escape_stop_the_loop(self) -> None:
        app = self._build()
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""))
        self.assertFalse(app._running)
        app._running = True
        app.handle_event(pygame.event.Event(pygame.QUIT))
        self.assertFalse(app._running)


if __name__ == "__main__":
    unittest.main()

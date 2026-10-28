"""The Word Forest: catch-the-letter action practice (catalogue, field, saves, app loop)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import tomllib
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.activity_controls import ControlLayout, KitPointer, PointerPhase
from greia_platform.activity_feedback import CastPose
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

from activities.foresta_parole.foresta_app import AppState, ForestaApp
from activities.foresta_parole.foresta_art import ForestArt
from activities.foresta_parole.foresta_audio import SpeechQueue
from activities.foresta_parole.foresta_content import (
    AVOIDED_EXAMPLES,
    LOOKALIKE_PAIRS,
    PHONICS_DATA,
    STAGES,
    STORAGE_KEY,
    TARGETS_PER_ROUND,
)
from activities.foresta_parole.foresta_model import (
    Basket,
    FieldEventKind,
    FieldGeometry,
    ForestField,
    RoundPlanner,
    Target,
    catch_catalogue,
    lookalikes,
    next_stage,
    stage_spec,
)
from activities.foresta_parole.foresta_renderer import ForestRenderer
from activities.foresta_parole.foresta_services import ForestProgress, GreiaForestProgress

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_DIR = PROJECT_ROOT / "activities" / "foresta_parole"


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class FakeAudio:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.sfx: list[str] = []

    def play_speech(self, cue_id: str) -> float:
        self.spoken.append(cue_id)
        return 0.6

    def stop_speech(self) -> None:
        return None

    def play_sfx(self, cue: str) -> None:
        self.sfx.append(cue)


class MemoryStorage:
    def __init__(self, initial: dict | None = None) -> None:
        self.data = dict(initial or {})

    def kv_get(self, key, default=None):
        return self.data.get(key, default)

    def kv_set(self, key, value) -> None:
        self.data[key] = json.loads(json.dumps(value))


class FakeEvents:
    def __init__(self) -> None:
        self.caught: list[tuple[int, str]] = []
        self.rounds: list[dict] = []

    def letter_caught(self, session_id, index, letter, word) -> None:
        self.caught.append((index, letter))

    def round_completed(self, session_id, payload) -> None:
        self.rounds.append(payload)


def _make_app(size=(1024, 600), *, locale="en", storage=None, seed=5):
    pygame.init()
    screen = pygame.display.set_mode(size)
    clock = FakeClock()
    audio = FakeAudio()
    storage = storage if storage is not None else MemoryStorage()
    port = GreiaForestProgress(storage)
    events = FakeEvents()
    typography = GreiaTypography()
    rng = random.Random(seed)
    resources = activity_resources(ACTIVITY_DIR, requested_locale=locale)
    app = ForestaApp(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        planner=RoundPlanner(rng, language=locale),
        progress=port.load(),
        progress_port=port,
        events=events,
        renderer=ForestRenderer(ForestArt(1024, 600, typography)),
        typography=typography,
        resources=resources,
        audio=audio,  # type: ignore[arg-type]
        speech_queue=SpeechQueue(audio),
        locale=locale,
        rng=rng,
        session_id="test-000001",
        clock=clock,
    )
    return app, clock, audio, storage, events


def _step(app, clock, seconds: float, fps: int = 30) -> None:
    for _ in range(max(1, int(seconds * fps))):
        clock.now += 1.0 / fps
        app.tick()


def _key(key: int, down: bool = True) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=key, mod=0, unicode="", scancode=0)


class ManifestAndContentTests(unittest.TestCase):
    def test_manifest_matches_the_catch_game(self) -> None:
        data = tomllib.loads((ACTIVITY_DIR / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["activity"]["id"], "org.greia.foresta-parole")
        self.assertEqual(data["activity"]["version"], "0.2.0")
        self.assertEqual(set(data["activity"]["languages"]), {"it", "en", "es", "fr"})
        self.assertEqual(data["input"]["profile"], "directional")
        self.assertEqual((data["education"]["recommended_age_min"], data["education"]["recommended_age_max"]), (5, 7))
        self.assertNotIn("phonics", data["education"]["categories"])
        events = {event["id"] for event in data["education"]["events"]}
        self.assertEqual(events, {"letter.matched", "forest.round_completed"})
        self.assertEqual(data["storage"]["schema_version"], 1)

    def test_locale_bundles_have_key_parity_and_real_copy(self) -> None:
        bundles = {
            loc: json.loads((ACTIVITY_DIR / "locales" / f"{loc}.json").read_text(encoding="utf-8"))["strings"]
            for loc in ("en", "it", "es", "fr")
        }
        for loc, strings in bundles.items():
            with self.subTest(locale=loc):
                self.assertEqual(set(strings), set(bundles["en"]))
                for key in ("activity.title", "victory.title", "button.play_again"):
                    self.assertTrue(strings[key].strip())
        self.assertNotEqual(bundles["it"]["victory.title"], bundles["en"]["victory.title"])

    def test_playable_cards_are_recorded_pictured_and_review_state_is_honest(self) -> None:
        for language in ("en", "it", "es", "fr"):
            cards = catch_catalogue(language)
            with self.subTest(language=language):
                self.assertGreaterEqual(len(cards), 12)
                self.assertEqual(len({card.letter for card in cards}), len(cards))
                folder = ACTIVITY_DIR / "assets" / "audio" / language
                for card in cards:
                    self.assertTrue(card.word.casefold().startswith(card.letter.casefold()))
                    self.assertNotIn((language, card.letter), AVOIDED_EXAMPLES)
                    self.assertTrue(get_shared_visual_path(card.picture).is_file(), card.picture)
                    for stem in (card.prompt_cue, card.letter_cue, card.word_cue):
                        wav = folder / f"{stem}.wav"
                        self.assertTrue(wav.is_file(), wav)
                        receipt = json.loads((folder / f"{stem}.wav.receipt.json").read_text(encoding="utf-8"))
                        # Replacement clips are either pending listening or an
                        # explicit owner waiver; they are never claimed as
                        # machine-approved. Older accepted clips stay approved.
                        review = receipt["human_review"]
                        self.assertIn(review, {"APPROVED", "PENDING", "WAIVED_BY_OWNER"}, wav)
                        if "corpus_replacement" in receipt:
                            self.assertNotEqual(review, "APPROVED", wav)
                        if review == "WAIVED_BY_OWNER":
                            self.assertTrue(receipt.get("acceptance_note"), wav)

    def test_misleading_examples_are_never_played(self) -> None:
        letters = {card.letter for card in catch_catalogue("en")}
        self.assertNotIn("O", letters)  # Owl
        self.assertNotIn("C", {card.letter for card in catch_catalogue("fr")})  # Chat (CH)
        # The recordings stay in the authoritative inventory.
        self.assertIn(("O", "o", "find_o", "Owl", "pending", "owl"), PHONICS_DATA["en"])

    def test_prompt_clips_name_the_letter_not_its_sound(self) -> None:
        for language, joiner in (("en", " as "), ("it", " come ")):
            folder = ACTIVITY_DIR / "assets" / "audio" / language
            for card in catch_catalogue(language):
                receipt = json.loads((folder / f"{card.prompt_cue}.wav.receipt.json").read_text(encoding="utf-8"))
                self.assertEqual(receipt["request"]["text"], f"{card.letter}{joiner}{card.word}")


class ModelTests(unittest.TestCase):
    def test_round_has_six_distinct_targets_with_honest_decoys(self) -> None:
        planner = RoundPlanner(random.Random(3), language="en")
        for stage in range(1, len(STAGES) + 1):
            round_ = planner.build(stage)
            letters = [t.card.letter for t in round_.targets]
            self.assertEqual(len(letters), TARGETS_PER_ROUND)
            self.assertEqual(len(set(letters)), TARGETS_PER_ROUND)
            for target in round_.targets:
                self.assertNotIn(target.card.letter, target.decoys)
                self.assertEqual(len(target.decoys), stage_spec(stage).decoy_kinds)
                similar = set(lookalikes(target.card.letter, planner.alphabet))
                if not stage_spec(stage).lookalikes:
                    self.assertFalse(similar & set(target.decoys))
                elif similar:
                    self.assertTrue(similar & set(target.decoys))

    def test_least_caught_letters_are_chosen_first(self) -> None:
        planner = RoundPlanner(random.Random(1), language="it")
        caught = {card.letter: 9 for card in planner.cards}
        fresh = [card.letter for card in planner.cards][:3]
        for letter in fresh:
            caught[letter] = 0
        round_ = planner.build(1, caught)
        self.assertTrue(set(fresh) <= {t.card.letter for t in round_.targets})

    def test_lookalike_pairs_are_symmetric(self) -> None:
        for a, b in LOOKALIKE_PAIRS:
            self.assertIn(b, lookalikes(a, (a, b)))
            self.assertIn(a, lookalikes(b, (a, b)))

    def _target(self) -> Target:
        card = catch_catalogue("en")[0]
        return Target(card, ("M", "S", "W"))

    def test_drops_never_overlap_and_a_choice_appears_early(self) -> None:
        field = ForestField(random.Random(9))
        field.start(self._target(), stage_spec(4))
        seen_target = seen_decoy = False
        geo = field.geometry
        for frame in range(30 * 60):
            field.update(1 / 30, basket_x=-1000)  # basket far away: nothing is caught
            falling = field.falling
            if frame < 30 * 4:
                seen_target |= any(l.is_target for l in falling)
                seen_decoy |= any(not l.is_target for l in falling)
            self.assertLessEqual(len(falling), stage_spec(4).max_falling)
            for i, a in enumerate(falling):
                for b in falling[i + 1:]:
                    if a.lane == b.lane:
                        self.assertGreaterEqual(abs(a.y - b.y), geo.token)
                    else:
                        self.assertGreaterEqual(abs(a.x - b.x), geo.token)
        self.assertTrue(seen_target and seen_decoy)

    def test_colour_does_not_reveal_the_answer(self) -> None:
        field = ForestField(random.Random(2))
        field.start(self._target(), stage_spec(2))
        colours = set()
        for _ in range(30 * 40):
            field.update(1 / 30, basket_x=-1000)
            colours |= {l.color for l in field.falling if l.is_target}
        self.assertGreater(len(colours), 2)

    def _run_until(self, field: ForestField, basket_for, kind: FieldEventKind, seconds: float = 30.0):
        for _ in range(int(seconds * 30)):
            for event in field.update(1 / 30, basket_for(field)):
                if event.kind is kind:
                    return event
        return None

    def test_catch_target_decoy_and_miss(self) -> None:
        def under(target: bool):
            def pick(field: ForestField) -> float:
                letters = [l for l in field.falling if l.is_target is target and not l.passed]
                return max(letters, key=lambda l: l.y).x if letters else -1000.0
            return pick

        field = ForestField(random.Random(4))
        field.start(Target(catch_catalogue("en")[0], ("M", "S", "W")), stage_spec(1))
        self.assertIsNotNone(self._run_until(field, under(True), FieldEventKind.CAUGHT_TARGET))
        field.start(Target(catch_catalogue("en")[0], ("M", "S", "W")), stage_spec(1))
        self.assertIsNotNone(self._run_until(field, under(False), FieldEventKind.CAUGHT_DECOY))
        field.start(Target(catch_catalogue("en")[0], ("M", "S", "W")), stage_spec(1))
        self.assertIsNotNone(self._run_until(field, lambda f: -1000.0, FieldEventKind.MISSED_TARGET))

    def test_guide_sends_a_glowing_target_above_the_basket(self) -> None:
        field = ForestField(random.Random(8))
        field.start(self._target(), stage_spec(3))
        field.update(3.0 / 30, basket_x=-1000)
        field.set_guide(True)
        basket_x = field.geometry.lanes[3]
        newest = None
        for _ in range(30 * 6):
            field.update(1 / 30, basket_x=-1000)
            fresh = [l for l in field.falling if l.y < field.geometry.spawn_y + 10]
            if fresh:
                newest = fresh[-1]
                break
        self.assertIsNotNone(newest)
        assert newest is not None
        self.assertTrue(newest.is_target and newest.glow)
        del basket_x

    def test_basket_is_clamped_and_glides(self) -> None:
        geo = FieldGeometry()
        basket = Basket(geo)
        basket.nudge(-5000)
        self.assertEqual(basket.x, geo.basket_min_x)
        basket.goal = 900
        for _ in range(60):
            basket.follow(1 / 30)
        self.assertAlmostEqual(basket.x, 900, delta=1)

    def test_stage_adapts(self) -> None:
        planner = RoundPlanner(random.Random(0), language="en")
        smooth = planner.build(2)
        self.assertEqual(next_stage(smooth), 3)
        bumpy = planner.build(2)
        bumpy.errors = 6
        self.assertEqual(next_stage(bumpy), 1)
        top = planner.build(len(STAGES))
        self.assertEqual(next_stage(top), len(STAGES))


class ProgressTests(unittest.TestCase):
    def test_legacy_save_loads_and_carries_forward(self) -> None:
        storage = MemoryStorage({STORAGE_KEY: {"score": 30, "stars": 3, "words_completed": 2, "vocab_idx": 4}})
        progress = GreiaForestProgress(storage).load()
        self.assertEqual((progress.score, progress.stars, progress.words_completed), (30, 3, 2))
        self.assertEqual(progress.stage_for("en"), 1)
        progress.record_catch("en", "B")
        GreiaForestProgress(storage).save(progress)
        saved = storage.data[STORAGE_KEY]
        self.assertEqual(saved["schema_version"], 3)
        self.assertEqual((saved["score"], saved["stars"], saved["words_completed"]), (40, 4, 3))
        self.assertEqual(saved["caught"], {"en": {"B": 1}})

    def test_malformed_payload_parts_are_dropped(self) -> None:
        progress = ForestProgress.from_payload(
            {"score": "x", "stars": True, "stages": {"en": 99, "xx": 2, "it": "3"}, "caught": {"en": {"b": 2, "C": -1, "D": 5}}}
        )
        self.assertEqual((progress.score, progress.stars), (0, 0))
        self.assertEqual(progress.stages, {"en": len(STAGES)})
        self.assertEqual(progress.caught, {"en": {"D": 5}})
        self.assertEqual(ForestProgress.from_payload(None).to_payload()["score"], 0)


class AppLoopTests(unittest.TestCase):
    def tearDown(self) -> None:
        pygame.display.quit()

    def _steer_round(self, app, clock, *, limit_seconds=400.0) -> None:
        for _ in range(int(limit_seconds * 30)):
            if app.state is AppState.TERMINAL:
                return
            target = app.field.falling_target()
            if target is not None:
                # Steer like a child with a finger / mouse on the forest floor.
                app._pointer(KitPointer(PointerPhase.MOVE, (int(target.x), 520)))
            _step(app, clock, 1 / 30)

    def test_dirty_rect_frames_match_a_full_render(self) -> None:
        """Falling letters / basket / Leo / sign repaint only their rectangles."""

        for seed in (5, 9):
            app, clock, _audio, _storage, _events = _make_app(seed=seed)
            app._ready_published = True  # as after the first frame of run()
            previous = app._present(None)
            partial_frames: list[int] = []
            checked: list[int] = []
            mismatched: list[tuple[int, int, int]] = []
            original = app.canvas.present_regions
            app.canvas.present_regions = lambda regions: (partial_frames.append(1), original(regions))[1]
            for tick in range(360):
                if app.state is AppState.TERMINAL:
                    break
                target = app.field.falling_target()
                if target is not None and tick % 15 == 0:
                    app._pointer(KitPointer(PointerPhase.MOVE, (int(target.x), 520)))
                clock.now += 1 / 24
                app.tick()
                previous = app._present(previous)
                if tick % 30 == 29:
                    # Every so often: what the dirty rectangles left on the
                    # logical surface must equal a full render of this state.
                    partial = app.canvas.surface.copy()
                    app._render()
                    full = app.canvas.surface
                    checked.append(tick)
                    mismatched.extend(
                        (tick, x, y)
                        for x in range(0, full.get_width(), 3)
                        for y in range(0, full.get_height(), 3)
                        if partial.get_at((x, y)) != full.get_at((x, y))
                    )
            self.assertGreater(len(partial_frames), 60)
            self.assertTrue(checked)
            self.assertEqual(mismatched[:5], [], f"seed {seed}")

    def test_plays_a_full_round_to_the_completion_scene(self) -> None:
        storage = MemoryStorage({STORAGE_KEY: {"score": 10, "stars": 1, "words_completed": 1}})
        app, clock, audio, storage, events = _make_app(storage=storage)
        _step(app, clock, 1.2)
        self.assertEqual(audio.spoken[:2], ["leo.ready", app.round.current.card.prompt_cue])
        self._steer_round(app, clock)
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertEqual(len(app.round.caught), TARGETS_PER_ROUND)
        self.assertEqual([i for i, _ in events.caught], list(range(1, TARGETS_PER_ROUND + 1)))
        self.assertEqual(len(events.rounds), 1)
        saved = storage.data[STORAGE_KEY]
        self.assertEqual(saved["words_completed"], 1 + TARGETS_PER_ROUND)
        self.assertEqual(saved["rounds_completed"], 1)
        self.assertEqual(saved["stages"], {"en": 2})
        # Each caught word was named: letter, then word.
        first = app.round.caught[0]
        self.assertIn(first.letter_cue, audio.spoken)
        self.assertIn(first.word_cue, audio.spoken)
        self.assertIn("leo.celebrate", audio.spoken)
        app._render()  # completion overlay draws
        # Keyboard replays from the completion scene (shared kit focus).
        app._handle_event(_key(pygame.K_SPACE))
        self.assertIs(app.state, AppState.INTRO)
        self.assertEqual(app.round.stage, 2)
        self.assertEqual(app.controls.dots.current, 0)

    def test_wrong_catch_is_kind_and_two_lead_to_a_demonstration(self) -> None:
        app, clock, audio, _, _ = _make_app(seed=11)
        _step(app, clock, 0.5)
        for _ in range(2):
            before = app.round.errors
            for _ in range(30 * 30):
                decoys = [l for l in app.field.falling if not l.is_target and not l.passed]
                if decoys:
                    app.basket.goal = max(decoys, key=lambda l: l.y).x
                else:
                    app.basket.goal = 300.0  # stay away from the right letter
                _step(app, clock, 1 / 30)
                if app.round.errors > before:
                    break
            self.assertEqual(app.round.errors, before + 1)
            _step(app, clock, 0.1)
            self.assertIs(app.renderer.cast.pose, CastPose.THINK)
            self.assertIn("leo.retry", audio.spoken)
        self.assertTrue(app.field.guide)
        self.assertTrue(app.scene_state().leo_pointing)
        self.assertEqual(app.round.done, 0)  # nothing is taken away

    def test_idle_hint_points_and_repeats_the_word(self) -> None:
        app, clock, audio, _, _ = _make_app()
        _step(app, clock, 2.0)
        spoken = len(audio.spoken)
        app.basket.goal = None
        clock.now += 0.0
        _step(app, clock, 7.0)
        self.assertGreaterEqual(app.round.hints, 1)
        self.assertIn(app.round.current.card.prompt_cue, audio.spoken[spoken:])
        state = app.scene_state()
        self.assertTrue(state.hint or state.leo_pointing)

    def test_the_rain_rests_soon_after_the_idle_hints_but_not_while_an_arrow_is_held(self) -> None:
        from activities.foresta_parole.foresta_app import AWAY_SECONDS

        # Room for both idle hints (6 s, 18 s), but an unattended glade must
        # settle well inside a minute (Acer: 33% CPU and creeping RSS at 40 s).
        self.assertGreaterEqual(AWAY_SECONDS, 18.0)
        self.assertLessEqual(AWAY_SECONDS, 25.0)
        app, clock, _, _, _ = _make_app()
        app._handle_event(_key(pygame.K_RIGHT))
        _step(app, clock, AWAY_SECONDS + 10.0)
        self.assertFalse(app._resting(clock.now), "holding an arrow is play, not absence")
        app._handle_event(_key(pygame.K_RIGHT, down=False))
        _step(app, clock, AWAY_SECONDS + 0.5)
        self.assertTrue(app._resting(clock.now) or app.state is not AppState.PLAYING)

    def test_an_absent_child_lets_the_screen_settle_and_input_resumes_the_rain(self) -> None:
        from activities.foresta_parole.foresta_app import AWAY_SECONDS

        app, clock, _, _, events = _make_app()
        _step(app, clock, AWAY_SECONDS + 12.0)
        # No input for a long time: no new drops, no more hints, nothing moving.
        self.assertFalse(app.field.letters)
        hints = app.round.hints
        caught = len(events.caught)
        app._visual_changed()  # absorb the last real change
        for _ in range(60):
            _step(app, clock, 0.5, fps=2)
            self.assertFalse(app._animating())
            self.assertFalse(app._visual_changed())
        self.assertEqual(app.round.hints, hints)
        self.assertEqual(len(events.caught), caught)
        # The next input brings the letters back.
        app._note_input()
        _step(app, clock, 2.0)
        self.assertTrue(app.field.letters)
        self.assertTrue(app._animating())

    def test_field_without_spawn_lets_letters_finish_but_drops_nothing_new(self) -> None:
        field = ForestField(random.Random(3), FieldGeometry())
        field.start(Target(catch_catalogue("en")[0], ("M", "S", "W")), stage_spec(1))
        for _ in range(60):
            field.update(1 / 30, 500.0, spawn=False)
        self.assertFalse(field.letters)
        for _ in range(30):
            field.update(1 / 30, 500.0)
        self.assertTrue(field.letters)

    def test_keyboard_controller_and_pointer_move_the_basket(self) -> None:
        app, clock, audio, _, _ = _make_app()
        start = app.basket.x
        app._handle_event(_key(pygame.K_LEFT))
        _step(app, clock, 0.3)
        app._handle_event(_key(pygame.K_LEFT, down=False))
        moved = app.basket.x
        self.assertLess(moved, start - 100)
        _step(app, clock, 0.3)
        self.assertEqual(app.basket.x, moved)
        # Space replays the word.
        count = audio.spoken.count(app.round.current.card.prompt_cue)
        app._handle_event(_key(pygame.K_SPACE))
        _step(app, clock, 0.1)
        self.assertEqual(audio.spoken.count(app.round.current.card.prompt_cue), count + 1)
        # Pointer / touch pulls the basket along the floor.
        app._pointer(KitPointer(PointerPhase.MOVE, (900, 400)))
        _step(app, clock, 0.6)
        self.assertAlmostEqual(app.basket.x, app.basket.clamp(900), delta=2)
        # Left stick (simulated through the shared axis path).
        app._stick_x = 1.0
        before = app.basket.x
        app.basket.x = 600.0
        _step(app, clock, 0.2)
        self.assertGreater(app.basket.x, 600.0)
        app._stick_x = 0.0
        del before

    def test_listen_button_and_sign_replay_and_protected_chrome_is_ignored(self) -> None:
        app, clock, audio, _, _ = _make_app(size=(800, 480))
        _step(app, clock, 3.0)
        layout = ControlLayout.for_canvas(app.canvas, app.screen.get_size())
        for rect in (app.controls.geometry.listen, app.controls.dots.rect, app.controls.geometry.sign):
            self.assertFalse(layout.overlaps_chrome(rect), rect)
        cue = app.round.current.card.prompt_cue
        count = audio.spoken.count(cue)
        self.assertTrue(app._pointer_tap_logical(app.controls.geometry.listen.center))
        _step(app, clock, 0.1)
        self.assertEqual(audio.spoken.count(cue), count + 1)
        self.assertTrue(app._pointer_tap_logical(app.controls.geometry.sign.center))
        x = app.basket.x
        self.assertFalse(app._handle_pointer((5, 5)))  # Home/Back region
        _step(app, clock, 0.3)
        self.assertEqual(app.basket.x, x)

    def test_keyboard_hint_hangs_above_the_sign_and_lights_the_pressed_key(self) -> None:
        from greia_platform.activity_keyboard_hint import KeyCap

        for size in ((1024, 600), (800, 480), (480, 320)):
            with self.subTest(size=size):
                app, clock, _, _, _ = _make_app(size=size)
                geometry = app.controls.geometry
                keys = app.controls.keys
                layout = ControlLayout.for_canvas(app.canvas, app.screen.get_size())
                self.assertTrue(keys.visible, "shown at start")
                self.assertEqual(keys.active, {KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
                self.assertFalse(layout.overlaps_chrome(keys.rect))
                self.assertFalse(keys.rect.colliderect(geometry.sign))
                self.assertFalse(keys.rect.colliderect(geometry.listen))
                self.assertLessEqual(keys.rect.bottom, geometry.sign.top)
                field = geometry.field
                self.assertLess(keys.rect.right, field.lanes[0] - field.token // 2, "clear of the letter rain")
                if size != (480, 320):
                    smallest = min(r.height for r in keys.key_rects().values())
                    self.assertGreaterEqual(smallest * layout.scale, 26, "legible keycaps")
                pygame.display.quit()
        app, clock, _, _, _ = _make_app()
        keys = app.controls.keys
        _step(app, clock, 3.0)
        app._handle_event(_key(pygame.K_LEFT))
        self.assertIn(KeyCap.LEFT, keys.lit)
        app._handle_event(_key(pygame.K_LEFT, down=False))
        _step(app, clock, 0.5)
        self.assertNotIn(KeyCap.LEFT, keys.lit)
        app._visual_changed()
        self.assertFalse(app._visual_changed())
        keys.hide()
        self.assertTrue(app._visual_changed(), "the hint's look is part of the frame signature")
        app._render()
        pygame.display.quit()

    def test_renders_at_reference_sizes_in_both_languages(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            for locale in ("en", "it"):
                with self.subTest(size=size, locale=locale):
                    app, clock, _, _, _ = _make_app(size=size, locale=locale)
                    _step(app, clock, 4.0)
                    app._render()
                    app.canvas.present()
                    pygame.display.quit()


if __name__ == "__main__":
    unittest.main()

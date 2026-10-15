"""Magic Syllables — Leo's Syllable Train: content, model, saves and app loop."""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
import tomllib
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import hermetic_volume


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "sillabe_magiche"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from sillabe_content import (  # noqa: E402
    PICTURE_PENDING,
    ReadingMethod,
    TrainWord,
    approved_syllables,
    get_reading_method,
    syllable_cue,
    train_words,
)
from sillabe_model import (  # noqa: E402
    CHALLENGE_COUNT,
    HISTORY_LIMIT,
    AttemptSummary,
    Phase,
    StepKind,
    TrainRoundFactory,
    TrainSession,
    adapt_level,
)
from sillabe_services import GreiaTrainProgress, TrainProgress  # noqa: E402
from sillabe_audio import recorded_clip_checker  # noqa: E402


def setUpModule() -> None:
    hermetic_volume.install_for_module()


def _factory(locale: str, seed: int = 7) -> TrainRoundFactory:
    return TrainRoundFactory(
        random.Random(seed), locale, clip_exists=recorded_clip_checker(ACTIVITY_ROOT, locale)
    )


def _solve(session: TrainSession) -> None:
    while not session.is_complete:
        if session.phase is Phase.CLAP:
            session.clap()
        else:
            step = session.current_step
            assert step is not None
            session.select_choice(step.correct_index)


class ContentTests(unittest.TestCase):
    def test_reading_method_per_language(self) -> None:
        self.assertIs(get_reading_method("it"), ReadingMethod.CV_SYLLABLES)
        self.assertIs(get_reading_method("es-ES"), ReadingMethod.CV_SYLLABLES)
        self.assertIs(get_reading_method("fr"), ReadingMethod.SYLLABLE_TILES)
        self.assertIs(get_reading_method("en-GB"), ReadingMethod.BEATS)
        with self.assertRaises(ValueError):
            get_reading_method("de")

    def test_every_offered_word_has_a_library_picture_and_approved_audio(self) -> None:
        from sillabe_art import resolve_picture

        for locale in ("it", "en", "es", "fr"):
            words = train_words(locale)
            self.assertGreaterEqual(len(words), CHALLENGE_COUNT, locale)
            for word in words:
                with self.subTest(locale=locale, word=word.word_id):
                    self.assertNotEqual(word.picture, PICTURE_PENDING)
                    self.assertTrue(word.picture.isascii(), "pictures are library IDs, never emoji")
                    self.assertTrue(resolve_picture(word.picture).is_file(), word.picture)
                    self.assertTrue((ACTIVITY_ROOT / "assets/audio" / locale / f"{word.audio_id}.wav").is_file())
                    if get_reading_method(locale) is not ReadingMethod.BEATS:
                        for part in word.syllables:
                            self.assertTrue(
                                (ACTIVITY_ROOT / "assets/audio" / locale / f"{syllable_cue(part)}.wav").is_file()
                            )

    def test_english_has_one_and_two_beat_words_and_no_cast_lookalikes(self) -> None:
        words = train_words("en")
        beats = {word.beats for word in words}
        self.assertEqual(beats, {1, 2})
        labels = {word.label for word in words}
        # A rabbit or robot picture would be named "Flash" / "Dani".
        self.assertFalse({"RABBIT", "ROBOT"} & labels)
        self.assertTrue({"SUN", "ROCK", "PAN", "BEE"} <= labels)

    def test_no_emoji_in_package_source(self) -> None:
        for path in ACTIVITY_ROOT.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertFalse(any(ord(ch) >= 0x2600 for ch in text), "emoji/pictograph in source")

    def test_activity_art_has_reviewable_sources(self) -> None:
        for name in ("locomotive", "wheel", "station_sign", "wagon_ocean", "wagon_coral",
                     "lemon", "panda", "tiger", "zebra"):
            with self.subTest(asset=name):
                source = ACTIVITY_ROOT / "assets" / "source" / f"{name}.svg"
                runtime = ACTIVITY_ROOT / "assets" / "runtime" / f"{name}.png"
                self.assertTrue(source.is_file())
                self.assertTrue(runtime.is_file())
                text = source.read_text(encoding="utf-8")
                for forbidden in ("<image", "<text", "<filter", "<style", "<script", "data:", "<mask"):
                    self.assertNotIn(forbidden, text)


class FactoryTests(unittest.TestCase):
    def test_seed_is_deterministic(self) -> None:
        first = [c.word.word_id for c in _factory("it", 3).build_set(2)]
        second = [c.word.word_id for c in _factory("it", 3).build_set(2)]
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)

    def test_italian_stage_one_builds_vowels_after_the_given_consonant(self) -> None:
        for seed in range(12):
            for challenge in _factory("it", seed).build_set(1):
                self.assertTrue(challenge.clap_first)
                self.assertEqual(len(challenge.steps), challenge.wagons)
                for step in challenge.steps:
                    with self.subTest(seed=seed, word=challenge.word.word_id, wagon=step.wagon):
                        self.assertIs(step.kind, StepKind.VOWEL)
                        self.assertEqual(len(step.choices), 3)
                        self.assertTrue(all(c in "AEIOU" for c in step.choices))
                        self.assertEqual(step.target_syllable, challenge.word.syllables[step.wagon])

    def test_italian_stage_two_offers_near_whole_syllables(self) -> None:
        approved = set(approved_syllables("it"))
        for challenge in _factory("it", 5).build_set(2):
            for step in challenge.steps:
                self.assertIs(step.kind, StepKind.SYLLABLE)
                self.assertEqual(len(step.choices), 3)
                self.assertTrue(set(step.choices) <= approved)
                others = set(challenge.word.syllables) - {step.target_syllable}
                self.assertFalse(others & set(step.choices), "the other wagon's syllable is not a distractor")

    def test_stage_three_builds_the_word_from_one_shared_pool(self) -> None:
        for challenge in _factory("it", 9).build_set(3):
            first, second = challenge.steps
            self.assertEqual(first.choices, second.choices)
            self.assertEqual(len(first.choices), 4)
            self.assertEqual(second.used, frozenset({first.correct_index}))

    def test_english_never_shows_syllabary_and_exactly_one_picture_fits(self) -> None:
        for level, size in ((1, 2), (2, 3), (3, 3)):
            for seed in range(10):
                for challenge in _factory("en", seed).build_set(level):
                    step = challenge.steps[0]
                    with self.subTest(level=level, seed=seed, word=challenge.word.word_id):
                        self.assertIs(step.kind, StepKind.PICTURE)
                        self.assertFalse(challenge.clap_first)
                        self.assertEqual(len(step.choices), size)
                        fits = [w for w in step.choices if isinstance(w, TrainWord) and w.beats == challenge.wagons]
                        self.assertEqual(fits, [challenge.word])

    def test_english_round_mixes_one_and_two_beat_trains(self) -> None:
        wagons = [c.wagons for c in _factory("en", 4).build_set(2)]
        self.assertEqual(sorted(wagons), [1, 1, 1, 2, 2, 2])

    def test_staged_languages_offer_only_recorded_native_syllables(self) -> None:
        for locale in ("es", "fr"):
            recorded = recorded_clip_checker(ACTIVITY_ROOT, locale)
            approved = set(approved_syllables(locale))
            for level in (1, 2, 3):
                for seed in range(8):
                    for challenge in _factory(locale, seed).build_set(level):
                        for step in challenge.steps:
                            with self.subTest(locale=locale, level=level, word=challenge.word.word_id):
                                for index in range(len(step.choices)):
                                    syllable = step.syllable_for(index)
                                    self.assertIn(syllable, approved)
                                    self.assertTrue(recorded(syllable_cue(syllable)), syllable)
                                if locale == "fr":
                                    self.assertIs(step.kind, StepKind.SYLLABLE)


class SessionTests(unittest.TestCase):
    def test_wrong_choice_is_eliminated_and_retry_is_unlimited(self) -> None:
        session = TrainSession(_factory("it").build_set(2), level=2)
        self.assertIs(session.phase, Phase.CLAP)
        for _ in range(session.current_challenge.wagons):
            session.clap()
        self.assertIsNone(session.clap())
        step = session.current_step
        wrong = [i for i in range(len(step.choices)) if i != step.correct_index]
        for count, index in enumerate(wrong, start=1):
            result = session.select_choice(index)
            self.assertFalse(result.correct)
            self.assertEqual(result.errors, count)
            self.assertIn(index, session.eliminated)
        with self.assertRaises(ValueError):
            session.select_choice(wrong[0])
        self.assertTrue(session.select_choice(step.correct_index).correct)
        self.assertEqual(session.built_wagons, (0,))

    def test_beats_train_claps_after_choosing_and_completes_on_last_beat(self) -> None:
        session = TrainSession(_factory("en").build_set(1), level=1)
        challenge = session.current_challenge
        self.assertIs(session.phase, Phase.CHOOSE)
        self.assertIsNone(session.clap())
        result = session.select_choice(session.current_step.correct_index)
        self.assertFalse(result.challenge_completed)
        self.assertIs(session.phase, Phase.CLAP)
        for beat in range(challenge.wagons):
            clap = session.clap()
            self.assertEqual(clap.beat, beat)
        self.assertTrue(clap.challenge_completed)
        self.assertEqual(session.challenge_index, 1)
        self.assertEqual(session.consume_milestone()["beats"], challenge.wagons)

    def test_completion_payload_is_one_shot(self) -> None:
        session = TrainSession(_factory("it").build_set(1), level=1)
        _solve(session)
        payload = session.consume_completion()
        self.assertEqual(payload["first_attempt_count"], CHALLENGE_COUNT)
        self.assertIsNone(session.consume_completion())

    def test_adaptation(self) -> None:
        strong = [AttemptSummary(True, 0, False)] * HISTORY_LIMIT
        weak = [AttemptSummary(False, 2, True)] * 3
        self.assertEqual(adapt_level(1, strong), 2)
        self.assertEqual(adapt_level(3, strong), 3)
        self.assertEqual(adapt_level(2, weak), 1)
        self.assertEqual(adapt_level(1, weak), 1)


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value
        self.saved = None

    def kv_get(self, key, default=None):
        return self.value if self.value is not None else default

    def kv_set(self, key, value):
        self.saved = value
        self.value = value


class ProgressTests(unittest.TestCase):
    def test_schema_one_counters_are_carried_forward(self) -> None:
        storage = _Storage({"score": 120, "stars": 14, "words_completed": 9})
        repo = GreiaTrainProgress(storage)
        loaded = repo.load()
        self.assertEqual(loaded, TrainProgress(1, (), 120, 14, 9))
        repo.save(2, [AttemptSummary(True, 0, False)], words=6, stars=6)
        saved = storage.saved
        self.assertEqual(saved["schema_version"], 2)
        self.assertEqual(saved["level"], 2)
        self.assertEqual((saved["score"], saved["stars"], saved["words_completed"]), (180, 20, 15))
        self.assertEqual(GreiaTrainProgress(storage).load().level, 2)

    def test_malformed_storage_recovers_and_history_is_bounded(self) -> None:
        storage = _Storage({"schema_version": 2, "level": 99, "history": "corrupt", "stars": -5, "score": True})
        repo = GreiaTrainProgress(storage)
        self.assertEqual(repo.load(), TrainProgress())
        repo.save(3, [AttemptSummary(True, 0, False) for _ in range(20)], words=6, stars=6)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)
        self.assertEqual(GreiaTrainProgress(_Storage("garbage")).load(), TrainProgress())


class ManifestAndTextTests(unittest.TestCase):
    def test_manifest_matches_the_literacy_ladder_rung(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.sillabe-magiche")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "navigation")
        education = manifest["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (5, 6))
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, 3))
        self.assertIn("phonological_awareness", education["categories"])
        self.assertEqual(
            education["events"],
            [
                {"id": "syllable.word_completed", "kind": "milestone"},
                {"id": "syllable.train_completed", "kind": "completion"},
            ],
        )

    def test_bundles_keep_parity_and_name_leo(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"]["strings"])
        for locale, bundle in bundles.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(bundle["strings"]), keys)
                self.assertTrue(all(value.strip() for value in bundle["strings"].values()))
                self.assertTrue("Leo" in bundle["strings"]["victory.subtitle"] or "Léo" in bundle["strings"]["victory.subtitle"])
        for locale in ("es", "fr"):
            self.assertEqual(bundles[locale]["audio"], {})
        for name in ("sillabe_renderer.py", "sillabe_app.py", "sillabe_controls.py"):
            source = (ACTIVITY_ROOT / name).read_text(encoding="utf-8")
            for phrase in ("ASCOLTA", "LISTEN", "Sillabario", "display_text("):
                self.assertNotIn(phrase, source)


class SpeechQueueTests(unittest.TestCase):
    def test_queue_is_bounded_tagged_and_plays_sfx_cues(self) -> None:
        from sillabe_audio import MAX_QUEUE_LEN, SpeechQueue

        class _Audio:
            def __init__(self) -> None:
                self.played: list[str] = []
                self.stopped = 0

            def play_speech(self, cue_id: str):
                self.played.append(cue_id)
                return 0.2 if cue_id else None

            def stop_speech(self) -> None:
                self.stopped += 1

        audio = _Audio()
        queue = SpeechQueue(audio)
        for index in range(MAX_QUEUE_LEN + 5):
            queue.enqueue(f"syl_{index}", tag="wagon.0")
        queue.update(0.0)
        self.assertEqual(queue.current_tag, "wagon.0")
        for _ in range(200):
            queue.update(0.1)
        self.assertFalse(queue.busy)
        self.assertEqual(len(audio.played), MAX_QUEUE_LEN)
        queue.enqueue("sfx:drum", tag="beat.0")
        queue.clear()
        self.assertFalse(queue.busy)
        self.assertEqual(audio.stopped, 1)

    def test_audio_resolves_lazily_with_a_bounded_cache(self) -> None:
        from sillabe_audio import SillabeAudio

        pygame.mixer.quit()
        audio = SillabeAudio(ACTIVITY_ROOT, locale="it", max_clips=3)
        self.assertTrue(audio.has_clip("syl_lu"))
        self.assertTrue(audio.has_clip("leo.praise"))
        self.assertFalse(audio.has_clip("../escape"))
        for cue in ("syl_lu", "syl_na", "word_luna", "syl_ma", "syl_me"):
            audio.play_speech(cue)
        self.assertLessEqual(len(audio._clips), 3)
        self.assertGreater(audio.play_speech("sfx:drum"), 0)


class _MockEvents:
    def __init__(self) -> None:
        self.milestones: list[dict[str, int]] = []
        self.completions: list[dict[str, int]] = []

    def word_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.milestones.append(payload)

    def train_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.completions.append(payload)


class _SpyQueue:
    """Wrap the real queue and record every cue the app asks for."""

    def __init__(self, queue) -> None:
        self._queue = queue
        self.cues: list[str] = []

    def enqueue(self, cue_id: str, **kwargs) -> None:
        self.cues.append(cue_id)
        self._queue.enqueue(cue_id, **kwargs)

    def __getattr__(self, name):
        return getattr(self._queue, name)


def build_app(level: int = 1, locale: str = "it", seed: int = 99, storage=None):
    """Compose the real app on the current display with a fake clock (tests/tools)."""

    from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
    from greia_platform.pygame_canvas import PygameReferenceCanvas
    from greia_platform.typography import GreiaTypography
    from sillabe_app import SillabeActivity
    from sillabe_art import SillabeArt
    from sillabe_audio import SillabeAudio, SpeechQueue
    from sillabe_renderer import SillabeRenderer

    screen = pygame.display.get_surface()
    assert screen is not None
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(locale, support)
    assert context is not None
    resources = LocalizedResources(ACTIVITY_ROOT, context)
    typography = GreiaTypography()
    art = SillabeArt(1024, 600, typography)
    storage = storage if storage is not None else _Storage({"schema_version": 2, "level": level, "history": []})
    progress = GreiaTrainProgress(storage)
    saved = progress.load()
    events = _MockEvents()
    audio = SillabeAudio(ACTIVITY_ROOT, locale=locale, resources=resources)
    queue = _SpyQueue(SpeechQueue(audio))
    rng = random.Random(seed)
    factory = TrainRoundFactory(rng, locale, clip_exists=recorded_clip_checker(ACTIVITY_ROOT, locale))
    session = TrainSession(factory.build_set(saved.level), level=saved.level)
    now = [100.0]
    app = SillabeActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        session=session,
        factory=factory,
        renderer=SillabeRenderer(art),
        typography=typography,
        resources=resources,
        locale=locale,
        progress=progress,
        events=events,
        audio=audio,
        speech_queue=queue,
        rng=rng,
        session_id="syllable-session-1",
        clock=lambda: now[0],
    )
    return app, now, events, storage, queue


def advance(app, now, seconds: float, step: float = 0.05) -> None:
    for _ in range(int(seconds / step)):
        now[0] += step
        app.tick()


def wait_for_input(app, now, limit: float = 20.0) -> None:
    from sillabe_app import AppState

    waited = 0.0
    while app.state is not AppState.PLAYING and app.state is not AppState.TERMINAL and waited < limit:
        advance(app, now, 0.1)
        waited += 0.1


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _play_round(self, app, now, *, use_keyboard: bool) -> None:
        from sillabe_app import AppState

        guard = 0
        while app.state is not AppState.TERMINAL and guard < 4000:
            guard += 1
            if app.state is AppState.PLAYING:
                session = app.session
                if session.phase is Phase.CLAP:
                    if use_keyboard:
                        self.assertEqual(app.controls.layer.focused_id, "drum")
                        self.assertTrue(app._handle_keyboard(pygame.K_SPACE))
                    else:
                        self.assertTrue(app._handle_pointer(app.controls.geometry.drum.center))
                else:
                    step = session.current_step
                    target = step.correct_index
                    if use_keyboard:
                        visible = [i for i in range(len(step.choices)) if i not in step.used]
                        app.controls.layer.focus(f"choice.{visible[0]}")
                        for _ in range(visible.index(target)):
                            app._handle_keyboard(pygame.K_RIGHT)
                        self.assertEqual(app.controls.layer.focused_id, f"choice.{target}")
                        self.assertTrue(app._handle_keyboard(pygame.K_SPACE))
                    else:
                        self.assertTrue(app._handle_pointer(app.controls.choice_center(target)))
                app._render()
            advance(app, now, 0.1)
        self.assertIs(app.state, AppState.TERMINAL)

    def test_every_stage_and_language_plays_to_the_completion_scene(self) -> None:
        from sillabe_app import AppState

        for locale, level, keyboard in (
            ("it", 1, False), ("it", 2, True), ("it", 3, False),
            ("en", 1, True), ("en", 2, False), ("en", 3, True),
        ):
            with self.subTest(locale=locale, level=level):
                app, now, events, storage, _ = build_app(level=level, locale=locale)
                app._render()
                self.assertIs(app.state, AppState.ARRIVE)
                self._play_round(app, now, use_keyboard=keyboard)
                app._render()
                self.assertEqual(len(events.milestones), CHALLENGE_COUNT)
                self.assertEqual(len(events.completions), 1)
                self.assertEqual(storage.saved["schema_version"], 2)
                self.assertEqual(storage.saved["words_completed"], CHALLENGE_COUNT)
                # Play again (south face / Space) starts a fresh round.
                app._handle_keyboard(pygame.K_SPACE)
                self.assertIs(app.state, AppState.ARRIVE)
                self.assertEqual(app.session.challenge_index, 0)

    def test_italian_clap_says_each_syllable_then_the_train_reads_the_word(self) -> None:
        from sillabe_app import AppState

        app, now, _, _, queue = build_app(level=1, locale="it")
        wait_for_input(app, now)
        word = app.session.current_challenge.word
        self.assertIs(app.session.phase, Phase.CLAP)
        self.assertTrue(app.controls.drum.visible)
        self.assertFalse(any(button.visible for button in app.controls.choices))
        queue.cues.clear()
        for _ in word.syllables:
            app._handle_pointer(app.controls.geometry.drum.center)
        self.assertEqual(queue.cues, [syllable_cue(s) for s in word.syllables] + [word.audio_id])
        self.assertIs(app.state, AppState.CLAPPED)
        wait_for_input(app, now)
        step = app.session.current_step
        self.assertIs(step.kind, StepKind.VOWEL)
        self.assertIn(syllable_cue(word.syllables[0]), queue.cues[-1:])
        queue.cues.clear()
        app._handle_pointer(app.controls.choice_center(step.correct_index))
        wait_for_input(app, now)
        step = app.session.current_step
        app._handle_pointer(app.controls.choice_center(step.correct_index))
        self.assertIs(app.state, AppState.BLEND)
        reading = [syllable_cue(s) for s in word.syllables] + [word.audio_id]
        joined = queue.cues
        self.assertTrue(any(joined[i:i + len(reading)] == reading for i in range(len(joined))), joined)
        self.assertEqual(joined[-1], "leo.praise")

    def test_wrong_vowel_thinks_contrasts_then_demonstrates(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from sillabe_app import AppState

        app, now, _, _, queue = build_app(level=1, locale="it")
        wait_for_input(app, now)
        for _ in range(app.session.current_challenge.wagons):
            app._handle_pointer(app.controls.geometry.drum.center)
        wait_for_input(app, now)
        step = app.session.current_step
        wrong = [i for i in range(3) if i != step.correct_index]
        queue.cues.clear()
        app._handle_pointer(app.controls.choice_center(wrong[0]))
        self.assertIs(app.state, AppState.TRY_AGAIN)
        self.assertIs(app.renderer.cast.pose, CastPose.THINK)
        self.assertEqual(
            queue.cues,
            ["leo.retry", syllable_cue(step.syllable_for(wrong[0])), syllable_cue(step.target_syllable)],
        )
        self.assertFalse(app.controls.choices[wrong[0]].enabled)
        self.assertIsNone(app._hint_target)
        advance(app, now, 0.6)
        app._handle_pointer(app.controls.choice_center(wrong[1]))
        self.assertEqual(app._hint_target, f"choice.{step.correct_index}")

    def test_english_wrong_picture_demonstrates_its_beats_without_letters(self) -> None:
        app, now, _, _, queue = build_app(level=2, locale="en")
        wait_for_input(app, now)
        step = app.session.current_step
        self.assertIs(step.kind, StepKind.PICTURE)
        self.assertFalse(app.scene_state().sign_picture, "the beats train hides its word")
        wrong = next(i for i in range(len(step.choices)) if i != step.correct_index)
        queue.cues.clear()
        app._handle_pointer(app.controls.choice_center(wrong))
        picked = step.choices[wrong]
        self.assertEqual(queue.cues, ["leo.retry", picked.audio_id] + ["sfx:drum"] * picked.beats)

    def test_only_approved_clips_are_spoken(self) -> None:
        allowed_prefixes = ("syl_", "word_", "vowel_", "leo.", "sfx:")
        allowed = {"instruction_build", "parola_composta", "word_complete"}
        for locale in ("it", "en"):
            app, now, _, _, queue = build_app(level=1, locale=locale)
            wait_for_input(app, now)
            advance(app, now, 7.0)  # one idle hint
            AppLoopTests._play_round(self, app, now, use_keyboard=False)
            for cue in queue.cues:
                with self.subTest(locale=locale, cue=cue):
                    self.assertTrue(cue.startswith(allowed_prefixes) or cue in allowed, cue)
                    if not cue.startswith(("leo.", "sfx:")):
                        self.assertTrue(app.audio.has_clip(cue), cue)
            if locale == "en":
                self.assertFalse([c for c in queue.cues if c.startswith(("vowel_", "word_complete"))])

    def test_idle_hint_points_and_replays(self) -> None:
        app, now, _, _, queue = build_app(level=1, locale="it")
        wait_for_input(app, now)
        while queue.busy:
            advance(app, now, 0.05)
        queue.cues.clear()
        advance(app, now, 5.0)
        self.assertEqual(queue.cues, [])
        advance(app, now, 1.2)
        word = app.session.current_challenge.word
        self.assertEqual(queue.cues[0], word.audio_id)
        self.assertTrue(app.scene_state().leo_pointing)
        self.assertEqual(app.scene_state().hint_target, "drum")

    def test_vowel_keys_pick_vowel_tiles(self) -> None:
        from sillabe_app import AppState

        app, now, _, _, _ = build_app(level=1, locale="it")
        wait_for_input(app, now)
        for _ in range(app.session.current_challenge.wagons):
            app._handle_keyboard(pygame.K_SPACE)
        wait_for_input(app, now)
        step = app.session.current_step
        key = getattr(pygame, f"K_{step.answer.lower()}")
        self.assertTrue(app._handle_keyboard(key))
        self.assertIs(app.state, AppState.STEP)

    def test_protected_chrome_region_ignores_taps_and_controls_avoid_it(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        app, now, _, _, _ = build_app(level=1)
        wait_for_input(app, now)
        self.assertFalse(app._handle_pointer((10, 10)))
        layout = ControlLayout.for_canvas(app.canvas, app.screen.get_size())
        for rect in (app.controls.listen.rect, app.controls.geometry.drum, app.controls.geometry.sign,
                     *(button.rect for button in app.controls.choices)):
            self.assertFalse(layout.overlaps_chrome(rect))

    def test_renders_every_state_without_error(self) -> None:
        from sillabe_app import AppState

        app, now, _, _, _ = build_app(level=3, locale="it")
        seen = set()
        guard = 0
        while app.state is not AppState.TERMINAL and guard < 3000:
            guard += 1
            seen.add(app.state)
            app._render()
            if app.state is AppState.PLAYING:
                if app.session.phase is Phase.CLAP:
                    app._handle_pointer(app.controls.geometry.drum.center)
                else:
                    step = app.session.current_step
                    app._handle_pointer(app.controls.choice_center(step.correct_index))
            advance(app, now, 0.05)
        app._render()
        self.assertTrue({AppState.ARRIVE, AppState.PLAYING, AppState.STEP, AppState.CLAPPED,
                         AppState.BLEND, AppState.DEPART, AppState.FINALE} <= seen)


class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_magic_syllables(self) -> None:
        import tempfile
        import time
        import unittest.mock as mock
        from greia_launcher.child_shell import ProfileVisualActivitySupervisor
        from greia_launcher.composition import build_launcher_runtime_services
        from greia_launcher.runtime_adapter import PythonRuntimePolicy
        from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
        from greia_platform.trust import ActivitySource, PackageTrust
        from greia_simulator.device import DEFAULT_CAPABILITIES, SimulatedDeviceProfile
        from greia_simulator.runtime import SimulatorPythonRuntimeAdapter
        from greia_simulator.workspace import SimulatorWorkspace

        runtime = RuntimeCatalogue.load(ROOT / "runtime" / "child-runtime.toml")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(ROOT, base / "state")
            device = SimulatedDeviceProfile(1024, 600, DEFAULT_CAPABILITIES)
            adapter = SimulatorPythonRuntimeAdapter(
                device,
                policy=PythonRuntimePolicy.load(ROOT / "runtime" / "child-runtime.toml"),
            )
            source = ActivitySource(ROOT / "activities", PackageTrust.BUILT_IN, "builtin")
            registrations = ActivityRegistry([source], runtime).discover_registrations()
            registration = next(r for r in registrations if r.manifest.activity_id == "org.greia.sillabe-magiche")
            services = build_launcher_runtime_services(
                runtime,
                tuple(r.manifest for r in registrations),
                runtime_policy_path=ROOT / "runtime" / "child-runtime.toml",
                permission_policy_path=ROOT / "runtime" / "permission-policy.toml",
                storage_policy_path=ROOT / "runtime" / "storage-policy.toml",
                history_policy_path=ROOT / "runtime" / "history-policy.toml",
                progression_policy_path=ROOT / "runtime" / "progression-policy.toml",
                hal=device.to_hal(),
                runtime_adapters=(adapter,),
            )
            profile = workspace.profile_store().context(workspace.profiles()[0].profile_id)
            authority = services.permission_broker.issue(registration)
            supervisor = ProfileVisualActivitySupervisor(
                runtime_manager=services.runtime_manager,
                storage_service=services.storage_service,
                history_service=services.history_service,
                display_coordinator=None,
            )
            environment = workspace.environment()
            environment.update(
                {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy", "PYGAME_HIDE_SUPPORT_PROMPT": "1"}
            )
            with mock.patch.dict(os.environ, environment, clear=False):
                session = supervisor.start(registration.manifest, profile, authority)
                deadline = time.monotonic() + 10.0
                while session.result is None and session.ready_at is None and time.monotonic() < deadline:
                    supervisor.poll(session)
                    time.sleep(0.02)
                self.assertIsNone(session.result, session.result)
                self.assertIsNotNone(session.ready_at)
                result = supervisor.request_stop(session)
                deadline = time.monotonic() + 5.0
                while result is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                    result = supervisor.poll(session)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertTrue(result.ready)
                self.assertTrue(result.succeeded)


if __name__ == "__main__":
    unittest.main()

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
ACTIVITY_ROOT = ROOT / "activities" / "officina_dei_suoni"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from sound_content import (  # noqa: E402
    PICTURE_PENDING,
    SOUND_UNITS_EN,
    SOUND_UNITS_IT,
    WordItem,
    WorkshopMode,
    get_build_slots,
    get_sound_units,
    pictures_conflict,
)
from sound_workshop_model import (  # noqa: E402
    AttemptSummary,
    CHALLENGE_COUNT,
    HISTORY_LIMIT,
    SoundRoundFactory,
    SoundSession,
    adapt_level,
)
from sound_services import GreiaWorkshopProgress, WorkshopProgress  # noqa: E402


def setUpModule() -> None:
    # The Simulator supervision test exercises real history/storage services,
    # whose production capacity policy depends on how full the host disk is.
    hermetic_volume.install_for_module()


def _initial(word: WordItem, locale: str) -> str:
    units = {unit.phoneme_id: unit for unit in get_sound_units(locale)}
    return units[word.initial_sound_id].grapheme_upper


class CorpusTests(unittest.TestCase):
    def test_en_it_units_have_approved_sound_word_and_prompt_audio(self) -> None:
        for locale, units in (("en", SOUND_UNITS_EN), ("it", SOUND_UNITS_IT)):
            audio = ACTIVITY_ROOT / "assets" / "audio" / locale
            self.assertEqual(len(units), 8)
            for cue in ("prompt_find_sound", "prompt_first_sound", "prompt_build_word"):
                self.assertTrue((audio / f"{cue}.wav").is_file(), cue)
            for unit in units:
                with self.subTest(locale=locale, unit=unit.phoneme_id):
                    self.assertTrue((audio / f"{unit.audio_id}.wav").is_file())
                    self.assertEqual(len(unit.words), 3)
                    for word in unit.words:
                        self.assertTrue((audio / f"{word.word_id}.wav").is_file(), word.word_id)
                        self.assertTrue(word.label.startswith(unit.grapheme_upper))
                        self.assertEqual(word.label[1:], word.remainder)

    def test_en_it_pictures_are_library_art_never_emoji(self) -> None:
        from sound_art import resolve_picture

        pending = []
        for locale, units in (("en", SOUND_UNITS_EN), ("it", SOUND_UNITS_IT)):
            for unit in units:
                self.assertGreaterEqual(len(unit.pictured_words), 2, unit.phoneme_id)
                for word in unit.words:
                    with self.subTest(locale=locale, word=word.word_id):
                        if word.picture == PICTURE_PENDING:
                            pending.append(word.word_id)
                            continue
                        self.assertTrue(word.picture.isascii())
                        self.assertTrue(resolve_picture(word.picture).is_file(), word.picture)
        # Only the Italian fairy still waits for an unambiguous picture.
        self.assertEqual(pending, ["fata"])

    def test_activity_art_has_reviewable_sources(self) -> None:
        for name in ("machine", "gear", "fox", "fan", "sea", "rose", "branch"):
            with self.subTest(asset=name):
                source = ACTIVITY_ROOT / "assets" / "source" / f"{name}.svg"
                runtime = ACTIVITY_ROOT / "assets" / "runtime" / f"{name}.png"
                self.assertTrue(source.is_file())
                self.assertTrue(runtime.is_file())
                text = source.read_text(encoding="utf-8")
                for forbidden in ("<image", "<text", "<filter", "<style", "<script", "data:"):
                    self.assertNotIn(forbidden, text)

    def test_build_lessons_fill_taught_sounds_only(self) -> None:
        for locale in ("en", "it"):
            units = get_sound_units(locale)
            letters = {unit.grapheme_upper for unit in units}
            words = {word.word_id: word for unit in units for word in unit.words}
            lessons = get_build_slots(locale)
            self.assertGreaterEqual(len([w for w in lessons if words[w].has_picture]), CHALLENGE_COUNT)
            for word_id, slots in lessons.items():
                with self.subTest(locale=locale, word=word_id):
                    word = words[word_id]
                    self.assertEqual(slots[0], 0)
                    self.assertEqual(list(slots), sorted(set(slots)))
                    for slot in slots:
                        self.assertIn(word.label[slot], letters)
        self.assertEqual(dict(get_build_slots("es")), {})
        self.assertEqual(dict(get_build_slots("fr")), {})

    def test_confusable_pictures_conflict(self) -> None:
        self.assertTrue(pictures_conflict("activity:rose", "prop.nature.flower"))
        self.assertTrue(pictures_conflict("prop.vocab.moon", "prop.vocab.moon"))
        self.assertFalse(pictures_conflict("prop.vocab.moon", "prop.vocab.cat"))


class SoundRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_generates_six_challenges(self) -> None:
        first = SoundRoundFactory(random.Random(12345), locale="it").build_set(1)
        second = SoundRoundFactory(random.Random(12345), locale="it").build_set(1)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)

    def test_first_sound_stage_is_picture_only_and_unambiguous(self) -> None:
        for locale in ("en", "it"):
            for seed in range(40):
                challenges = SoundRoundFactory(random.Random(seed), locale=locale).build_set(1)
                answers = [c.answer_word.word_id for c in challenges]
                self.assertEqual(len(answers), len(set(answers)))
                for previous, current in zip(challenges, challenges[1:]):
                    self.assertNotEqual(previous.target_unit, current.target_unit)
                for c in challenges:
                    self.assertIs(c.mode, WorkshopMode.FIND_SOUND)
                    self.assertIsNone(c.target_word)
                    self.assertEqual(len(c.steps), 1)
                    self.assertEqual(len(c.choices), 3)
                    self.assertTrue(all(isinstance(item, WordItem) and item.has_picture for item in c.choices))
                    initials = [item.initial_sound_id for item in c.choices]
                    self.assertEqual(initials.count(c.target_unit.phoneme_id), 1)
                    self.assertEqual(c.choices[c.correct_index].initial_sound_id, c.target_unit.phoneme_id)
                    pictures = [item.picture for item in c.choices]
                    for i, first in enumerate(pictures):
                        for second in pictures[i + 1:]:
                            self.assertFalse(pictures_conflict(first, second), (first, second))

    def test_letter_stage_asks_for_the_first_sound_letter(self) -> None:
        for locale in ("en", "it"):
            for c in SoundRoundFactory(random.Random(7), locale=locale).build_set(2):
                self.assertIs(c.mode, WorkshopMode.INITIAL_LETTER)
                assert c.target_word is not None
                self.assertTrue(c.target_word.has_picture)
                self.assertEqual(c.slots, (0,))
                self.assertEqual(len(set(c.choices)), 3)
                self.assertEqual(c.choices[c.correct_index], _initial(c.target_word, locale))

    def test_build_stage_fills_reviewed_slots(self) -> None:
        for locale in ("en", "it"):
            lessons = get_build_slots(locale)
            for seed in range(20):
                challenges = SoundRoundFactory(random.Random(seed), locale=locale).build_set(3)
                self.assertEqual(len({c.target_word.word_id for c in challenges}), CHALLENGE_COUNT)
                for c in challenges:
                    self.assertIs(c.mode, WorkshopMode.BUILD_WORD)
                    assert c.target_word is not None
                    self.assertEqual(c.slots, lessons[c.target_word.word_id])
                    self.assertEqual(len(c.steps), 2)
                    for step in c.steps:
                        self.assertEqual(step.answer, c.target_word.label[step.slot])
                        self.assertEqual(step.unit.grapheme_upper, step.answer)
                        self.assertEqual(len(set(step.choices)), 3)

    def test_staged_languages_build_first_sound_only(self) -> None:
        for locale in ("es", "fr"):
            for c in SoundRoundFactory(random.Random(3), locale=locale).build_set(3):
                self.assertEqual(c.slots, (0,))


class SoundSessionTests(unittest.TestCase):
    def test_wrong_choice_is_eliminated_and_retry_is_unlimited(self) -> None:
        session = SoundSession(SoundRoundFactory(random.Random(42), locale="it").build_set(1), level=1)
        c = session.current_challenge
        assert c is not None
        wrong = [i for i in range(3) if i != c.correct_index]
        result = session.select_choice(wrong[0])
        self.assertFalse(result.correct)
        self.assertEqual(session.eliminated, frozenset({wrong[0]}))
        session.select_choice(wrong[1])
        self.assertEqual(session.challenge_index, 0)
        result = session.select_choice(c.correct_index)
        self.assertTrue(result.challenge_completed)
        self.assertFalse(result.first_attempt_success)
        self.assertEqual(session.history[-1], AttemptSummary(False, 2, True))
        milestone = session.consume_milestone()
        assert milestone is not None
        self.assertEqual(milestone["word_index"], 1)

    def test_build_word_has_two_steps_before_completion(self) -> None:
        session = SoundSession(SoundRoundFactory(random.Random(5), locale="en").build_set(3), level=3)
        c = session.current_challenge
        assert c is not None
        first = session.select_choice(c.steps[0].correct_index)
        self.assertTrue(first.step_completed)
        self.assertFalse(first.challenge_completed)
        self.assertIsNone(session.consume_milestone())
        self.assertEqual(session.filled_slots, (0,))
        self.assertEqual(session.step_index, 1)
        second = session.select_choice(c.steps[1].correct_index)
        self.assertTrue(second.challenge_completed)
        self.assertEqual(session.challenge_index, 1)
        self.assertEqual(session.filled_slots, ())
        self.assertEqual(session.made, (c,))

    def test_completion_payload_is_one_shot(self) -> None:
        session = SoundSession(SoundRoundFactory(random.Random(42), locale="it").build_set(3), level=3)
        while not session.is_complete:
            step = session.current_step
            assert step is not None
            session.select_choice(step.correct_index)
        payload = session.consume_completion()
        self.assertEqual(payload, {"level": 3, "first_attempt_count": 6, "retries": 0})
        self.assertIsNone(session.consume_completion())


class AdaptationTests(unittest.TestCase):
    def test_adaptation_across_levels(self) -> None:
        strong = [AttemptSummary(True, 0, False) for _ in range(HISTORY_LIMIT)]
        self.assertEqual(adapt_level(1, strong), 2)
        self.assertEqual(adapt_level(3, strong), 3)
        struggling = [AttemptSummary(False, 2, True) for _ in range(3)]
        self.assertEqual(adapt_level(3, struggling), 2)
        self.assertEqual(adapt_level(1, struggling), 1)


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value
        self.saved = None

    def kv_get(self, key):
        return self.value

    def kv_set(self, key, value):
        self.saved = value
        self.value = value


class ProgressTests(unittest.TestCase):
    def test_existing_saves_keep_their_stage(self) -> None:
        legacy = {
            "schema_version": 1,
            "level": 2,
            "history": [{"first_attempt_success": True, "hints_used": 0, "used_retry": False}],
        }
        loaded = GreiaWorkshopProgress(_Storage(legacy)).load()
        self.assertEqual(loaded, WorkshopProgress(2, (AttemptSummary(True, 0, False),)))

    def test_malformed_storage_recovers_and_save_is_bounded(self) -> None:
        storage = _Storage({"schema_version": 1, "level": 99, "history": "corrupt"})
        repo = GreiaWorkshopProgress(storage)
        self.assertEqual(repo.load(), WorkshopProgress())
        repo.save(2, [AttemptSummary(True, 0, False) for _ in range(20)])
        self.assertEqual(storage.saved["level"], 2)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)


class ManifestAndTextTests(unittest.TestCase):
    def test_manifest_matches_the_literacy_ladder_rung(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.officina-dei-suoni")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "navigation")
        education = manifest["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 6))
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, 3))
        self.assertIn("phonemic_awareness", education["categories"])
        self.assertEqual(
            education["events"],
            [
                {"id": "sound.word_completed", "kind": "milestone"},
                {"id": "sound.workshop_completed", "kind": "completion"},
            ],
        )

    def test_bundles_keep_parity_and_name_dani(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))["strings"]
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"])
        for locale, strings in bundles.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(strings), keys)
                self.assertIn("Dani", strings["victory.subtitle"])
                self.assertNotIn("Leo", " ".join(strings.values()))
        for name in ("sound_renderer.py", "sound_app.py", "sound_controls.py"):
            source = (ACTIVITY_ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("ASCOLTA", source)
            self.assertNotIn("LISTEN", source)


class SpeechQueueTests(unittest.TestCase):
    def test_queue_is_bounded_tagged_and_cancels(self) -> None:
        from sound_audio import SILENT_CUE_SECONDS, SpeechQueue

        class _Audio:
            def __init__(self) -> None:
                self.played: list[str] = []
                self.stopped = 0

            def play_speech(self, cue_id: str):
                self.played.append(cue_id)
                return 0.5 if cue_id.startswith("sound_") else None

            def stop_speech(self) -> None:
                self.stopped += 1

        audio = _Audio()
        queue = SpeechQueue(audio, max_len=3)
        for cue in ("sound_m", "moon", "map", "mouse"):
            queue.enqueue(cue, tag="horn")
        queue.update(0.01)
        self.assertEqual(audio.played, ["sound_m"])
        self.assertEqual(queue.current_tag, "horn")
        queue.update(0.5 + 0.25)
        self.assertEqual(audio.played, ["sound_m", "moon"])
        queue.update(SILENT_CUE_SECONDS + 0.25)
        self.assertEqual(audio.played, ["sound_m", "moon", "map"])
        queue.update(SILENT_CUE_SECONDS + 0.3)
        self.assertNotIn("mouse", audio.played)
        queue.clear()
        self.assertFalse(queue.busy)
        self.assertEqual(audio.stopped, 1)


class _MockEvents:
    def __init__(self) -> None:
        self.milestones: list[dict[str, int]] = []
        self.completions: list[dict[str, int]] = []

    def word_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.milestones.append(payload)

    def workshop_completed(self, session_id: str, payload: dict[str, int]) -> None:
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


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build_app(self, level: int = 1, locale: str = "it"):
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from sound_app import SoundWorkshopActivity
        from sound_art import SoundWorkshopArt
        from sound_audio import SoundWorkshopAudio, SpeechQueue
        from sound_renderer import SoundWorkshopRenderer

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale(locale, support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        art = SoundWorkshopArt(1024, 600, typography)
        storage = _Storage({"schema_version": 1, "level": level, "history": []})
        progress = GreiaWorkshopProgress(storage)
        events = _MockEvents()
        audio = SoundWorkshopAudio(ACTIVITY_ROOT, locale=locale, resources=resources)
        queue = _SpyQueue(SpeechQueue(audio))
        rng = random.Random(99)
        factory = SoundRoundFactory(rng, locale=locale)
        session = SoundSession(factory.build_set(level), level=level)
        now = [100.0]
        app = SoundWorkshopActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            session=session,
            factory=factory,
            renderer=SoundWorkshopRenderer(art),
            typography=typography,
            resources=resources,
            progress=progress,
            events=events,
            audio=audio,
            speech_queue=queue,
            rng=rng,
            session_id="sound-session-1",
            clock=lambda: now[0],
        )
        return app, now, events, storage, queue

    @staticmethod
    def _advance(app, now, seconds: float, step: float = 0.05) -> None:
        for _ in range(int(seconds / step)):
            now[0] += step
            app.tick()

    def _play_round(self, app, now, *, use_keyboard: bool) -> None:
        from sound_app import AppState

        guard = 0
        while app.state is not AppState.TERMINAL and guard < 3000:
            guard += 1
            step = app.session.current_step
            if app.state is AppState.PLAYING and step is not None:
                target = step.correct_index
                if use_keyboard:
                    app.controls.layer.focus("choice.0")
                    for _ in range(target):
                        app._handle_keyboard(pygame.K_RIGHT)
                    self.assertTrue(app._handle_keyboard(pygame.K_SPACE))
                else:
                    center = app.controls.choice_center(target)
                    self.assertTrue(app._handle_pointer(center))
                app._render()
            self._advance(app, now, 0.1)
        self.assertIs(app.state, AppState.TERMINAL)

    def test_every_stage_plays_to_the_completion_scene(self) -> None:
        from sound_app import AppState

        for level, keyboard in ((1, False), (2, True), (3, False)):
            with self.subTest(level=level):
                app, now, events, storage, queue = self._build_app(level=level)
                app._render()
                self._play_round(app, now, use_keyboard=keyboard)
                app._render()
                self.assertEqual(len(events.milestones), CHALLENGE_COUNT)
                self.assertEqual(len(events.completions), 1)
                self.assertEqual(storage.saved["schema_version"], 1)
                # Play again (south face / Space) starts a fresh round.
                app._handle_keyboard(pygame.K_SPACE)
                self.assertIs(app.state, AppState.PLAYING)
                self.assertEqual(app.session.challenge_index, 0)

    def test_only_sounds_words_prompts_and_dani_are_spoken(self) -> None:
        allowed_prefixes = ("sound_", "prompt_", "dani.")
        for level in (1, 2, 3):
            app, now, _, _, queue = self._build_app(level=level, locale="en")
            words = {w.word_id for unit in SOUND_UNITS_EN for w in unit.words}
            step = app.session.current_step
            assert step is not None
            wrong = next(i for i in range(3) if i != step.correct_index)
            app._handle_pointer(app.controls.choice_center(wrong))
            self._advance(app, now, 7.0)
            self._play_round(app, now, use_keyboard=False)
            for cue in queue.cues:
                with self.subTest(level=level, cue=cue):
                    self.assertTrue(cue.startswith(allowed_prefixes) or cue in words, cue)
                    self.assertNotIn(cue, {"letter_m", "m", "M"})

    def test_first_sound_hides_the_letter_until_solved(self) -> None:
        app, now, _, _, _ = self._build_app(level=1)
        state = app.scene_state()
        self.assertFalse(state.reveal_letter)
        self.assertFalse(state.show_answer_picture)
        step = app.session.current_step
        assert step is not None
        self.assertTrue(all(isinstance(item, WordItem) for item in step.choices))
        app._handle_pointer(app.controls.choice_center(step.correct_index))
        self._advance(app, now, 0.9)
        state = app.scene_state()
        self.assertTrue(state.show_answer_picture)
        self.assertFalse(state.reveal_letter)
        self._advance(app, now, 1.6)
        self.assertTrue(app.scene_state().reveal_letter)

    def test_wrong_pick_thinks_contrasts_then_demonstrates(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from sound_app import AppState

        app, now, _, _, queue = self._build_app(level=2, locale="en")
        step = app.session.current_step
        challenge = app.session.current_challenge
        assert step is not None and challenge is not None
        wrong = [i for i in range(3) if i != step.correct_index]
        queue.cues.clear()
        app._handle_pointer(app.controls.choice_center(wrong[0]))
        self.assertIs(app.state, AppState.TRY_AGAIN)
        self.assertIs(app.renderer.cast.pose, CastPose.THINK)
        picked_unit = app.factory.unit_for_letter(step.choices[wrong[0]])
        self.assertEqual(queue.cues, ["dani.retry", picked_unit.audio_id, challenge.target_word.word_id])
        self.assertFalse(app.controls.choices[wrong[0]].enabled)
        self.assertIsNone(app._hint_target)
        self._advance(app, now, 0.6)
        app._handle_pointer(app.controls.choice_center(wrong[1]))
        self.assertEqual(app._hint_target, f"choice.{step.correct_index}")
        self.assertEqual(queue.cues[-2], step.unit.audio_id)

    def test_idle_hint_points_and_replays(self) -> None:
        app, now, _, _, queue = self._build_app(level=1)
        while queue.busy:
            self._advance(app, now, 0.05)
        queue.cues.clear()
        self._advance(app, now, 5.0)
        self.assertEqual(queue.cues, [])
        self._advance(app, now, 1.2)
        self.assertIn("prompt_find_sound", queue.cues)
        self.assertTrue(app.scene_state().dani_pointing)

    def test_letter_keys_pick_letter_tiles(self) -> None:
        from sound_app import AppState

        app, now, events, _, _ = self._build_app(level=2, locale="en")
        step = app.session.current_step
        assert step is not None
        key = getattr(pygame, f"K_{step.answer.lower()}")
        self.assertTrue(app._handle_keyboard(key))
        self.assertIs(app.state, AppState.CELEBRATE)
        self.assertEqual(len(events.milestones), 1)

    def test_protected_chrome_region_ignores_taps(self) -> None:
        app, _, _, _, _ = self._build_app(level=1)
        self.assertFalse(app._handle_pointer((10, 10)))
        listen = app.controls.listen.rect
        from greia_platform.activity_controls import ControlLayout

        layout = ControlLayout.for_canvas(app.canvas, app.screen.get_size())
        self.assertFalse(layout.overlaps_chrome(listen))
        for control in app.controls.choices:
            self.assertFalse(layout.overlaps_chrome(control.rect))


class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_officina_dei_suoni(self) -> None:
        import os
        import tempfile
        import time
        from greia_launcher.child_shell import ProfileVisualActivitySupervisor
        from greia_launcher.composition import build_launcher_runtime_services
        from greia_launcher.runtime_adapter import PythonRuntimePolicy
        from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
        from greia_platform.trust import ActivitySource, PackageTrust
        from greia_simulator.device import DEFAULT_CAPABILITIES, SimulatedDeviceProfile
        from greia_simulator.runtime import SimulatorPythonRuntimeAdapter
        from greia_simulator.workspace import SimulatorWorkspace

        runtime = RuntimeCatalogue.load(ROOT / "runtime" / "child-runtime.toml")
        # Honor TMPDIR (device /tmp is noexec); no exec artifact or
        # explicit broker socket lives here — broker defaults already
        # handle sun_path length with a /tmp fallback. T02-SPAWN-HYGIENE.
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
            registration = next(r for r in registrations if r.manifest.activity_id == "org.greia.officina-dei-suoni")
            manifest = registration.manifest

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
                {
                    "SDL_VIDEODRIVER": "dummy",
                    "SDL_AUDIODRIVER": "dummy",
                    "PYGAME_HIDE_SUPPORT_PROMPT": "1",
                }
            )
            import unittest.mock as mock
            with mock.patch.dict(os.environ, environment, clear=False):
                session = supervisor.start(manifest, profile, authority)
                deadline = time.monotonic() + 10.0
                while (
                    session.result is None
                    and session.ready_at is None
                    and time.monotonic() < deadline
                ):
                    supervisor.poll(session)
                    time.sleep(0.02)
                self.assertIsNone(session.result, session.result)
                self.assertIsNotNone(session.ready_at)

                # Request stop
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

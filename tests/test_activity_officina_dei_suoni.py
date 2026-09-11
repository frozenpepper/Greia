from __future__ import annotations

from pathlib import Path
import random
import sys
import tomllib
import unittest

import pygame


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "officina_dei_suoni"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from sound_content import (  # noqa: E402
    SOUND_UNITS_EN,
    SOUND_UNITS_IT,
    SoundUnit,
    WordItem,
    WorkshopMode,
    get_sound_units,
)
from sound_workshop_model import (  # noqa: E402
    AttemptSummary,
    CHALLENGE_COUNT,
    HISTORY_LIMIT,
    SoundRoundFactory,
    SoundSession,
    WorkshopChallenge,
    adapt_level,
)
from sound_services import GreiaWorkshopProgress, WorkshopProgress  # noqa: E402


class CorpusTests(unittest.TestCase):
    def test_corpora_are_distinct_and_complete(self) -> None:
        self.assertEqual(len(SOUND_UNITS_IT), 8)
        self.assertEqual(len(SOUND_UNITS_EN), 8)

        for unit in SOUND_UNITS_IT + SOUND_UNITS_EN:
            self.assertTrue(unit.phoneme_id)
            self.assertTrue(unit.grapheme_upper)
            self.assertTrue(unit.grapheme_lower)
            self.assertTrue(unit.audio_id)
            self.assertGreaterEqual(len(unit.words), 3)
            for w in unit.words:
                self.assertTrue(w.word_id)
                self.assertTrue(w.symbol)
                self.assertTrue(w.label.startswith(unit.grapheme_upper))


class SoundRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_generates_six_challenges(self) -> None:
        first = SoundRoundFactory(random.Random(12345), locale="it").build_set(1)
        second = SoundRoundFactory(random.Random(12345), locale="it").build_set(1)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)

    def test_each_level_has_planned_modes_and_choice_counts(self) -> None:
        factory_it = SoundRoundFactory(random.Random(42), locale="it")
        factory_en = SoundRoundFactory(random.Random(42), locale="en")

        for factory in (factory_it, factory_en):
            # L1: 3 choices, find sound mode
            l1 = factory.build_set(1)
            for c in l1:
                self.assertEqual(c.mode, WorkshopMode.FIND_SOUND)
                self.assertEqual(len(c.choices), 3)
                self.assertIsNotNone(c.target_unit)
                self.assertIsInstance(c.choices[c.correct_index], WordItem)

            # L2: 3 choices, initial letter mode
            l2 = factory.build_set(2)
            for c in l2:
                self.assertEqual(c.mode, WorkshopMode.INITIAL_LETTER)
                self.assertEqual(len(c.choices), 3)
                self.assertIsNotNone(c.target_word)
                self.assertIsInstance(c.choices[c.correct_index], str)

            # L3: 3 choices, build word mode
            l3 = factory.build_set(3)
            for c in l3:
                self.assertEqual(c.mode, WorkshopMode.BUILD_WORD)
                self.assertEqual(len(c.choices), 3)
                self.assertIsNotNone(c.target_word)
                self.assertIsInstance(c.choices[c.correct_index], str)


class SpeechQueueTests(unittest.TestCase):
    def test_speech_queue_is_bounded_and_cancels(self) -> None:
        from sound_audio import SpeechQueue

        class _MockAudio:
            def __init__(self) -> None:
                self.played = []
                self.stopped = 0

            def play_speech(self, cue_id: str) -> None:
                self.played.append(cue_id)

            def stop_speech(self) -> None:
                self.stopped += 1

            def is_speech_busy(self) -> bool:
                return False

        mock_audio = _MockAudio()
        queue = SpeechQueue(mock_audio)

        queue.enqueue("cue1", delay_after=0.1)
        queue.enqueue("cue2", delay_after=0.1)
        queue.enqueue("cue3", delay_after=0.1)
        queue.enqueue("cue4", delay_after=0.1)
        queue.enqueue("cue5", delay_after=0.1)

        queue.update(0.01)
        self.assertEqual(mock_audio.played, ["cue1"])

        queue.clear()
        self.assertEqual(mock_audio.stopped, 1)


class SoundSessionTests(unittest.TestCase):
    def test_correct_and_wrong_choices(self) -> None:
        factory = SoundRoundFactory(random.Random(42), locale="it")
        session = SoundSession(factory.build_set(1), level=1)

        c = session.current_challenge
        self.assertIsNotNone(c)
        assert c is not None

        wrong_idx = 1 if c.correct_index == 0 else 0
        res = session.select_choice(wrong_idx)
        self.assertFalse(res.correct)
        self.assertEqual(session.challenge_index, 0)

        res = session.select_choice(c.correct_index)
        self.assertTrue(res.correct)
        self.assertEqual(session.challenge_index, 1)

        milestone = session.consume_milestone()
        self.assertIsNotNone(milestone)
        assert milestone is not None
        self.assertEqual(milestone["word_index"], 1)

    def test_completion_payload_is_one_shot(self) -> None:
        factory = SoundRoundFactory(random.Random(42), locale="it")
        session = SoundSession(factory.build_set(1), level=1)

        while not session.is_complete:
            c = session.current_challenge
            assert c is not None
            session.select_choice(c.correct_index)

        payload = session.consume_completion()
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["level"], 1)
        self.assertEqual(payload["first_attempt_count"], 6)
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


class ProgressTests(unittest.TestCase):
    def test_malformed_storage_recovers_and_save_is_bounded(self) -> None:
        storage = _Storage({"schema_version": 1, "level": 99, "history": "corrupt"})
        repo = GreiaWorkshopProgress(storage)
        self.assertEqual(repo.load(), WorkshopProgress())

        history = [AttemptSummary(True, 0, False) for _ in range(20)]
        repo.save(2, history)
        self.assertIsNotNone(storage.saved)
        self.assertEqual(storage.saved["level"], 2)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)


class ManifestTests(unittest.TestCase):
    def test_manifest_declares_exact_milestone_completion_and_range(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.officina-dei-suoni")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertEqual(manifest["education"]["difficulty_min"], 1)
        self.assertEqual(manifest["education"]["difficulty_max"], 3)
        self.assertEqual(
            manifest["education"]["events"],
            [
                {"id": "sound.word_completed", "kind": "milestone"},
                {"id": "sound.workshop_completed", "kind": "completion"},
            ],
        )


class _MockEvents:
    def __init__(self) -> None:
        self.milestones: list[dict[str, int]] = []
        self.completions: list[dict[str, int]] = []

    def word_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.milestones.append(payload)

    def workshop_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.completions.append(payload)


class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import os
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build_app(self, level: int = 1):
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
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        canvas = PygameReferenceCanvas(screen)
        art = SoundWorkshopArt(1024, 600, typography)
        renderer = SoundWorkshopRenderer(art, typography, resources)
        storage = _Storage({"schema_version": 1, "level": level, "history": []})
        progress = GreiaWorkshopProgress(storage)
        events = _MockEvents()
        audio = SoundWorkshopAudio(ACTIVITY_ROOT, locale="it")
        speech_queue = SpeechQueue(audio)
        rng = random.Random(99)
        factory = SoundRoundFactory(rng, locale="it")
        session = SoundSession(factory.build_set(level), level=level)

        simulated_time = [100.0]

        def clock() -> float:
            return simulated_time[0]

        app = SoundWorkshopActivity(
            screen=screen,
            canvas=canvas,
            session=session,
            factory=factory,
            renderer=renderer,
            typography=typography,
            resources=resources,
            progress=progress,
            events=events,
            audio=audio,
            speech_queue=speech_queue,
            rng=rng,
            session_id="sound-session-1",
            clock=clock,
        )
        return app, simulated_time, events, progress

    def test_full_session_with_keyboard_and_pointer(self) -> None:
        from sound_app import AppState

        app, sim_time, events, progress = self._build_app(level=1)

        for _ in range(6):
            current = app.session.current_challenge
            assert current is not None
            # Navigate using keyboard arrows to the correct index
            while app._focused_choice != current.correct_index:
                app._handle_keyboard(pygame.K_RIGHT)

            # Activate via Space
            app._handle_keyboard(pygame.K_SPACE)

            sim_time[0] += 1.0
            app._advance_state()

        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(len(events.completions), 1)
        self.assertEqual(len(events.milestones), 6)

        # Play Again via Space
        app._handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.assertEqual(app.state, AppState.PLAYING)
        self.assertEqual(app.session.challenge_index, 0)


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

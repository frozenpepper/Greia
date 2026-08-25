from __future__ import annotations

from pathlib import Path
import random
import sys
import tomllib
import unittest

import pygame


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "luci_di_momo"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from firefly_model import (  # noqa: E402
    AttemptSummary,
    FireflyRoundFactory,
    FireflySession,
    HISTORY_LIMIT,
    MIN_CENTER_SEPARATION,
    adapt_level,
)
from firefly_services import FireflyProgress, GreiaFireflyProgress  # noqa: E402


class FireflyRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_rounds_obey_bounds(self) -> None:
        first = FireflyRoundFactory(random.Random(12345)).build_set(4)
        second = FireflyRoundFactory(random.Random(12345)).build_set(4)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)
        for round_ in first:
            self.assertIn(round_.quantity, round_.choice_values)
            self.assertEqual(len(set(round_.choice_values)), 3)
            self.assertEqual(len(round_.positions), round_.quantity)
            for index, point in enumerate(round_.positions):
                for other in round_.positions[index + 1:]:
                    dx = point[0] - other[0]
                    dy = point[1] - other[1]
                    self.assertGreaterEqual((dx * dx + dy * dy) ** 0.5, MIN_CENTER_SEPARATION)

    def test_each_level_uses_planned_quantity_and_reveal_bounds(self) -> None:
        expected = {
            1: (1, 3, 1600),
            2: (1, 4, 1400),
            3: (1, 5, 1200),
            4: (1, 5, 1100),
        }
        for level, (low, high, reveal) in expected.items():
            rounds = FireflyRoundFactory(random.Random(level)).build_set(level)
            self.assertTrue(all(low <= item.quantity <= high for item in rounds))
            self.assertTrue(all(item.reveal_ms == reveal for item in rounds))


class FireflySessionTests(unittest.TestCase):
    def _session(self) -> FireflySession:
        rounds = FireflyRoundFactory(random.Random(77)).build_set(2)
        return FireflySession(rounds, level=2)

    def test_wrong_answer_and_replay_do_not_advance_round(self) -> None:
        session = self._session()
        current = session.current_round
        assert current is not None
        wrong = next(value for value in current.choice_values if value != current.quantity)

        result = session.choose(wrong)
        self.assertFalse(result.correct)
        self.assertEqual(session.round_index, 0)
        self.assertIs(session.current_round, current)

        session.mark_replay()
        self.assertEqual(session.round_index, 0)
        self.assertIs(session.current_round, current)

        result = session.choose(current.quantity)
        self.assertTrue(result.correct)
        self.assertTrue(result.used_replay)
        self.assertFalse(result.first_attempt_success)
        self.assertEqual(session.round_index, 1)

    def test_completion_payload_is_one_shot(self) -> None:
        session = self._session()
        while not session.is_complete:
            current = session.current_round
            assert current is not None
            session.choose(current.quantity)

        payload = session.consume_completion()
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["level"], 2)
        self.assertEqual(payload["first_attempt_count"], 5)
        self.assertIsNone(session.consume_completion())


class AdaptationTests(unittest.TestCase):
    def test_level_moves_only_from_bounded_recent_evidence(self) -> None:
        strong = [AttemptSummary(True, 0, False) for _ in range(HISTORY_LIMIT)]
        self.assertEqual(adapt_level(2, strong), 3)

        scaffolded = [AttemptSummary(False, 2, False) for _ in range(3)]
        self.assertEqual(adapt_level(3, scaffolded), 2)

        mixed = [AttemptSummary(True, 0, False), AttemptSummary(False, 1, True)]
        self.assertEqual(adapt_level(2, mixed), 2)


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
        storage = _Storage({"schema_version": 1, "level": 99, "history": ["bad"]})
        repo = GreiaFireflyProgress(storage)
        self.assertEqual(repo.load(), FireflyProgress())

        history = [AttemptSummary(i % 2 == 0, i % 3, False) for i in range(20)]
        repo.save(4, history)
        self.assertIsNotNone(storage.saved)
        self.assertEqual(storage.saved["level"], 4)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)


class ManifestTests(unittest.TestCase):
    def test_manifest_declares_exact_completion_and_adaptive_range(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.luci-di-momo")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "pointer")
        self.assertEqual(manifest["education"]["difficulty_min"], 1)
        self.assertEqual(manifest["education"]["difficulty_max"], 4)
        self.assertEqual(
            manifest["education"]["events"],
            [{"id": "firefly.garden_completed", "kind": "completion"}],
        )


class _MockEvents:
    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict[str, int]]] = []

    def garden_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.emitted.append((session_id, payload))


class _MockAudio:
    def __init__(self) -> None:
        self.played: list[str] = []
        self.speech_played: list[str] = []

    def play(self, cue: str) -> None:
        self.played.append(cue)

    def play_speech(self, cue_id: str) -> None:
        self.speech_played.append(cue_id)

    def play_welcome(self) -> None:
        self.speech_played.append("welcome")

    def play_prompt_ready(self) -> None:
        self.speech_played.append("prompt_ready")

    def play_prompt_choose(self) -> None:
        self.speech_played.append("prompt_choose")

    def play_count(self, quantity: int) -> None:
        self.speech_played.append(f"count_{quantity}")

    def play_feedback(self, correct: bool) -> None:
        self.played.append("correct" if correct else "retry")
        self.speech_played.append("feedback_correct" if correct else "feedback_retry")

    def play_garden_complete(self) -> None:
        self.played.append("complete")
        self.speech_played.append("garden_complete")


class FireflyAppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import os
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()
        if pygame.display.get_surface() is None:
            pygame.display.set_mode((1024, 600))

    def _build_app(self, level: int = 1):
        from firefly_app import FireflyActivity, PresentationPhase
        from firefly_art import FireflyArt
        from firefly_renderer import FireflyRenderer
        from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        canvas = PygameReferenceCanvas(screen)
        art = FireflyArt(1024, 600)
        renderer = FireflyRenderer(art, typography, resources)
        storage = _Storage({"schema_version": 1, "level": level, "history": []})
        progress = GreiaFireflyProgress(storage)
        events = _MockEvents()
        audio = _MockAudio()
        rng = random.Random(42)
        factory = FireflyRoundFactory(rng)
        session = FireflySession(factory.build_set(level), level=level)

        simulated_time = [100.0]

        def clock() -> float:
            return simulated_time[0]

        app = FireflyActivity(
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
            rng=rng,
            session_id="test-session-1",
            clock=clock,
        )
        return app, simulated_time, events, audio, progress

    def test_presentation_cycle_and_wrong_choice_hint(self) -> None:
        from firefly_app import PresentationPhase
        from firefly_renderer import CHOICE_RECTS, START_BTN_RECT, LISTEN_BTN_RECT

        app, sim_time, events, audio, _ = self._build_app(level=1)
        self.assertEqual(app.phase, PresentationPhase.READY)

        # Test Listen button in ready phase
        handled = app._handle_pointer((LISTEN_BTN_RECT.centerx, LISTEN_BTN_RECT.centery))
        self.assertTrue(handled)
        self.assertIn("welcome", audio.speech_played)

        # Click BIG START button
        handled = app._handle_pointer((START_BTN_RECT.centerx, START_BTN_RECT.centery))
        self.assertTrue(handled)
        self.assertEqual(app.phase, PresentationPhase.REVEAL)
        self.assertIn("reveal", audio.played)

        # Render first frame of reveal
        app._render()
        self.assertFalse(app._advance_timed_phase())

        # Advance past reveal duration (1600ms for L1)
        sim_time[0] += 1.7
        self.assertTrue(app._advance_timed_phase())
        self.assertEqual(app.phase, PresentationPhase.CHOOSE)
        self.assertIn("prompt_choose", audio.speech_played)

        # Render choice screen
        app._render()

        # Click wrong answer
        current = app.session.current_round
        assert current is not None
        wrong_idx = next(
            i for i, val in enumerate(current.choice_values) if val != current.quantity
        )
        rect = CHOICE_RECTS[wrong_idx]
        handled = app._handle_pointer((rect.centerx, rect.centery))
        self.assertTrue(handled)
        self.assertEqual(app.phase, PresentationPhase.HINT)
        self.assertIn("retry", audio.played)

        # Step through hint
        sim_time[0] += 0.5
        app._render()
        # Finish hint phase
        sim_time[0] += 2.0
        self.assertTrue(app._advance_timed_phase())
        self.assertEqual(app.phase, PresentationPhase.CHOOSE)

    def test_five_rounds_to_terminal_and_restart(self) -> None:
        from firefly_app import PresentationPhase
        from firefly_renderer import CHOICE_RECTS, START_BTN_RECT

        app, sim_time, events, audio, progress = self._build_app(level=1)

        for round_num in range(5):
            self.assertEqual(app.phase, PresentationPhase.READY)
            # Click big start button
            handled = app._handle_pointer((START_BTN_RECT.centerx, START_BTN_RECT.centery))
            self.assertTrue(handled)
            self.assertEqual(app.phase, PresentationPhase.REVEAL)

            sim_time[0] += 2.0
            app._advance_timed_phase()
            self.assertEqual(app.phase, PresentationPhase.CHOOSE)

            current = app.session.current_round
            assert current is not None
            correct_idx = next(
                i for i, val in enumerate(current.choice_values) if val == current.quantity
            )
            rect = CHOICE_RECTS[correct_idx]
            handled = app._handle_pointer((rect.centerx, rect.centery))
            self.assertTrue(handled)

        self.assertEqual(app.phase, PresentationPhase.TERMINAL)
        self.assertEqual(len(events.emitted), 1)
        session_id, payload = events.emitted[0]
        self.assertEqual(session_id, "test-session-1")
        self.assertEqual(payload["level"], 1)
        self.assertEqual(payload["first_attempt_count"], 5)
        self.assertIn("garden_complete", audio.speech_played)

        # Render terminal screen
        app._render()

        # Click Play Again (primary button in completion screen)
        handled = app._handle_pointer((app.completion._primary_rect.centerx, app.completion._primary_rect.centery))
        self.assertTrue(handled)
        self.assertEqual(app.phase, PresentationPhase.READY)
        self.assertEqual(app.session.round_index, 0)
        self.assertFalse(app.session.is_complete)


class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_luci_di_momo(self) -> None:
        import os
        import tempfile
        import time
        from greia_launcher.child_shell import ProfileVisualActivitySupervisor
        from greia_launcher.runtime_adapter import PythonRuntimePolicy
        from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
        from greia_platform.trust import ActivitySource, PackageTrust
        from greia_simulator.device import DEFAULT_CAPABILITIES, SimulatedDeviceProfile
        from greia_simulator.runtime import SimulatorPythonRuntimeAdapter
        from greia_simulator.workspace import SimulatorWorkspace
        from greia_launcher.composition import build_launcher_runtime_services

        runtime = RuntimeCatalogue.load(ROOT / "runtime" / "child-runtime.toml")
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(ROOT, base / "state")
            device = SimulatedDeviceProfile(1024, 600, DEFAULT_CAPABILITIES)
            adapter = SimulatorPythonRuntimeAdapter(
                device,
                policy=PythonRuntimePolicy.load(ROOT / "runtime" / "child-runtime.toml"),
            )
            source = ActivitySource(ROOT / "activities", PackageTrust.BUILT_IN, "builtin")
            registrations = ActivityRegistry([source], runtime).discover_registrations()
            registration = next(r for r in registrations if r.manifest.activity_id == "org.greia.luci-di-momo")
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


class AudioAndPreReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import os
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.init()

    def test_audio_loads_and_exposes_cues(self) -> None:
        from firefly_audio import FireflyAudio
        audio = FireflyAudio(ACTIVITY_ROOT, locale="it")
        self.assertIsNotNone(audio)
        audio.play("reveal")
        audio.play("correct")
        audio.play("retry")
        audio.play("complete")
        audio.play_welcome()
        audio.play_prompt_ready()
        audio.play_prompt_choose()
        audio.play_count(3)
        audio.play_feedback(True)
        audio.play_feedback(False)
        audio.play_garden_complete()
        audio.stop_speech()


if __name__ == "__main__":
    unittest.main()


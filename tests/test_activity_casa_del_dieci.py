from __future__ import annotations

from pathlib import Path
import random
import sys
import tomllib
import unittest

import pygame


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "casa_del_dieci"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from ten_house_model import (  # noqa: E402
    AttemptSummary,
    CHALLENGE_COUNT,
    HISTORY_LIMIT,
    OperationMode,
    ROOM_COUNT,
    TenHouseChallenge,
    TenHouseRoundFactory,
    TenHouseSession,
    adapt_level,
)
from ten_house_services import GreiaTenHouseProgress, TenHouseProgress  # noqa: E402


class TenHouseRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_generates_six_unique_challenges(self) -> None:
        first = TenHouseRoundFactory(random.Random(12345)).build_set(3)
        second = TenHouseRoundFactory(random.Random(12345)).build_set(3)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)

        for c in first:
            self.assertTrue(0 <= c.target <= ROOM_COUNT)
            self.assertTrue(0 <= c.starting_lit <= ROOM_COUNT)
            self.assertTrue(0 <= c.delta <= ROOM_COUNT)
            self.assertTrue(0 <= c.answer <= ROOM_COUNT)
            self.assertIn(c.answer, c.choice_values)
            self.assertEqual(len(set(c.choice_values)), 3)

    def test_each_level_adheres_to_planned_arithmetic_invariants(self) -> None:
        factory = TenHouseRoundFactory(random.Random(999))
        for level in range(1, 6):
            challenges = factory.build_set(level, count=12)
            for c in challenges:
                if c.mode == OperationMode.COMPOSE:
                    self.assertEqual(c.answer, c.target)
                    self.assertTrue(1 <= c.target <= 10)
                elif c.mode == OperationMode.ADD:
                    self.assertEqual(c.starting_lit + c.delta, c.answer)
                    self.assertTrue(c.answer <= 10)
                elif c.mode == OperationMode.TAKE_AWAY:
                    self.assertEqual(c.starting_lit - c.delta, c.answer)
                    self.assertTrue(c.answer >= 0)
                elif c.mode == OperationMode.MISSING_PART:
                    self.assertEqual(c.starting_lit + c.answer, c.target)
                    self.assertTrue(c.target <= 10)


class TenHouseSessionTests(unittest.TestCase):
    def test_compose_mode_room_toggling_and_confirm(self) -> None:
        challenge = TenHouseChallenge(
            challenge_id="test-1",
            mode=OperationMode.COMPOSE,
            target=4,
            starting_lit=1,
            delta=0,
            answer=4,
            choice_values=(4, 2, 5),
        )
        session = TenHouseSession([challenge] * 6, level=1)
        self.assertEqual(session.lit_count, 1)

        # Toggle room 1, 2, 3 -> now 4 lit
        session.toggle_room(1)
        session.toggle_room(2)
        session.toggle_room(3)
        self.assertEqual(session.lit_count, 4)

        result = session.confirm_compose()
        self.assertTrue(result.correct)
        self.assertTrue(result.first_attempt_success)
        self.assertEqual(session.challenge_index, 1)

        milestone = session.consume_milestone()
        self.assertIsNotNone(milestone)
        assert milestone is not None
        self.assertEqual(milestone["challenge_index"], 1)
        self.assertEqual(milestone["first_attempt"], 1)

    def test_operation_mode_wrong_choice_and_retry(self) -> None:
        challenge = TenHouseChallenge(
            challenge_id="test-2",
            mode=OperationMode.ADD,
            target=5,
            starting_lit=3,
            delta=2,
            answer=5,
            choice_values=(5, 4, 6),
        )
        session = TenHouseSession([challenge] * 6, level=3)

        # Choose wrong
        result = session.choose(4)
        self.assertFalse(result.correct)
        self.assertEqual(session.challenge_index, 0)
        self.assertTrue(result.used_retry)

        # Choose correct
        result = session.choose(5)
        self.assertTrue(result.correct)
        self.assertFalse(result.first_attempt_success)
        self.assertTrue(result.used_retry)
        self.assertEqual(session.challenge_index, 1)

    def test_completion_payload_is_one_shot(self) -> None:
        factory = TenHouseRoundFactory(random.Random(42))
        session = TenHouseSession(factory.build_set(2), level=2)

        while not session.is_complete:
            current = session.current_challenge
            assert current is not None
            if current.mode == OperationMode.COMPOSE:
                # Set rooms to target
                session.room_states = [False] * 10
                for i in range(current.target):
                    session.room_states[i] = True
                session.confirm_compose()
            else:
                session.choose(current.answer)

        payload = session.consume_completion()
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["level"], 2)
        self.assertEqual(payload["first_attempt_count"], 6)
        self.assertIsNone(session.consume_completion())


class AdaptationTests(unittest.TestCase):
    def test_adaptation_across_levels(self) -> None:
        strong = [AttemptSummary(True, 0, False) for _ in range(HISTORY_LIMIT)]
        self.assertEqual(adapt_level(1, strong), 2)
        self.assertEqual(adapt_level(5, strong), 5)

        struggling = [AttemptSummary(False, 2, True) for _ in range(3)]
        self.assertEqual(adapt_level(4, struggling), 3)
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
        repo = GreiaTenHouseProgress(storage)
        self.assertEqual(repo.load(), TenHouseProgress())

        history = [AttemptSummary(True, 0, False) for _ in range(20)]
        repo.save(3, history)
        self.assertIsNotNone(storage.saved)
        self.assertEqual(storage.saved["level"], 3)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)


class ManifestTests(unittest.TestCase):
    def test_manifest_declares_exact_milestone_completion_and_range(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.casa-del-dieci")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertEqual(manifest["education"]["difficulty_min"], 1)
        self.assertEqual(manifest["education"]["difficulty_max"], 5)
        self.assertEqual(
            manifest["education"]["events"],
            [
                {"id": "ten_house.room_completed", "kind": "milestone"},
                {"id": "ten_house.house_completed", "kind": "completion"},
            ],
        )


class _MockEvents:
    def __init__(self) -> None:
        self.milestones: list[dict[str, int]] = []
        self.completions: list[dict[str, int]] = []

    def room_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.milestones.append(payload)

    def house_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.completions.append(payload)


class _MockAudio:
    def __init__(self) -> None:
        self.played: list[str] = []
        self.speech_played: list[str] = []

    def play(self, cue: str) -> None:
        self.played.append(cue)

    def play_speech(self, cue: str) -> None:
        self.speech_played.append(cue)

    def play_feedback(self, correct: bool) -> None:
        self.played.append("correct" if correct else "retry")

    def stop_speech(self) -> None:
        pass

    def is_speech_busy(self) -> bool:
        return False


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
        from ten_house_app import TenHouseActivity
        from ten_house_art import TenHouseArt
        from ten_house_renderer import TenHouseRenderer

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        canvas = PygameReferenceCanvas(screen)
        art = TenHouseArt(1024, 600)
        renderer = TenHouseRenderer(art, typography, resources)
        storage = _Storage({"schema_version": 1, "level": level, "history": []})
        progress = GreiaTenHouseProgress(storage)
        events = _MockEvents()
        audio = _MockAudio()
        rng = random.Random(77)
        factory = TenHouseRoundFactory(rng)
        session = TenHouseSession(factory.build_set(level), level=level)

        simulated_time = [100.0]

        def clock() -> float:
            return simulated_time[0]

        app = TenHouseActivity(
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
            session_id="casa-session-1",
            clock=clock,
        )
        return app, simulated_time, events, audio, progress

    def test_keyboard_navigation_and_toggle(self) -> None:
        from ten_house_app import AppState

        app, sim_time, events, audio, _ = self._build_app(level=1)
        self.assertEqual(app.state, AppState.PLAYING)

        # Initial focus is room 0
        self.assertEqual(app.session.focused_room, 0)
        self.assertFalse(app.session.focus_in_choices)

        # Press RIGHT -> focus room 1
        app._handle_keyboard(pygame.K_RIGHT)
        self.assertEqual(app.session.focused_room, 1)

        # Press SPACE -> toggle room 1
        app._handle_keyboard(pygame.K_SPACE)
        self.assertIn("toggle", audio.played)

        # Press DOWN twice -> focus in choices/confirm
        app._handle_keyboard(pygame.K_DOWN)
        app._handle_keyboard(pygame.K_DOWN)
        self.assertTrue(app.session.focus_in_choices)

    def test_full_session_to_completion_and_restart(self) -> None:
        from ten_house_app import AppState

        app, sim_time, events, audio, progress = self._build_app(level=3)

        for _ in range(6):
            current = app.session.current_challenge
            assert current is not None
            # Choose correct answer via pointer
            from ten_house_renderer import CHOICE_RECTS
            choice_idx = next(i for i, v in enumerate(current.choice_values) if v == current.answer)
            rect = CHOICE_RECTS[choice_idx]
            app._handle_pointer((rect.centerx, rect.centery))
            sim_time[0] += 0.6
            app._advance_state()
            sim_time[0] += 0.3
            app._advance_state()

        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(len(events.completions), 1)
        self.assertEqual(len(events.milestones), 6)

        # Play Again
        handled = app._handle_terminal_pointer(
            (app.completion._primary_rect.centerx, app.completion._primary_rect.centery)
        )
        self.assertTrue(handled)
        self.assertEqual(app.state, AppState.PLAYING)
        self.assertEqual(app.session.challenge_index, 0)


class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_casa_del_dieci(self) -> None:
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
            registration = next(r for r in registrations if r.manifest.activity_id == "org.greia.casa-del-dieci")
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

from __future__ import annotations

from pathlib import Path
import random
import sys
import tomllib
import unittest

import pygame


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "bottega_delle_misure"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from measure_model import (  # noqa: E402
    Attribute,
    AttemptSummary,
    CHALLENGE_COUNT,
    HISTORY_LIMIT,
    MeasureChallenge,
    MeasureItem,
    MeasureMode,
    MeasureRoundFactory,
    MeasureSession,
    adapt_level,
)
from measure_services import GreiaMeasureProgress, MeasureProgress  # noqa: E402


class MeasureRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_generates_five_unique_challenges(self) -> None:
        first = MeasureRoundFactory(random.Random(12345)).build_set(3)
        second = MeasureRoundFactory(random.Random(12345)).build_set(3)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)

        for c in first:
            self.assertTrue(1 <= c.target_units <= 8)
            self.assertTrue(c.items)
            for it in c.items:
                self.assertTrue(1 <= it.units <= 8)

    def test_each_level_adheres_to_planned_invariants(self) -> None:
        factory = MeasureRoundFactory(random.Random(999))
        for level in range(1, 6):
            challenges = factory.build_set(level, count=10)
            for c in challenges:
                if level == 1:
                    self.assertEqual(c.mode, MeasureMode.COMPARE)
                    self.assertEqual(len(c.items), 2)
                elif level == 2:
                    self.assertEqual(c.mode, MeasureMode.ORDER)
                    self.assertEqual(len(c.items), 3)
                elif level == 3:
                    self.assertEqual(c.mode, MeasureMode.MEASURE)
                elif level == 4:
                    self.assertEqual(c.mode, MeasureMode.SHELF)


class MeasureSessionTests(unittest.TestCase):
    def test_compare_mode_selection(self) -> None:
        item_a = MeasureItem("item_a", 2, Attribute.LENGTH, 0)
        item_b = MeasureItem("item_b", 4, Attribute.LENGTH, 1)
        challenge = MeasureChallenge(
            challenge_id="test-c1",
            mode=MeasureMode.COMPARE,
            attribute=Attribute.LENGTH,
            items=(item_a, item_b),
            target_id="item_b",
            target_units=4,
            unit_capacity=0,
            choice_values=(4, 5, 6),
            prompt_key="prompt.compare_longer",
        )
        session = MeasureSession([challenge] * 5, level=1)

        # Select wrong item
        res = session.select_item("item_a")
        self.assertIsNotNone(res)
        assert res is not None
        self.assertFalse(res.correct)
        self.assertEqual(session.challenge_index, 0)

        # Select correct item
        res = session.select_item("item_b")
        self.assertIsNotNone(res)
        assert res is not None
        self.assertTrue(res.correct)
        self.assertEqual(session.challenge_index, 1)

        milestone = session.consume_milestone()
        self.assertIsNotNone(milestone)
        assert milestone is not None
        self.assertEqual(milestone["challenge_index"], 1)

    def test_order_mode_seriation(self) -> None:
        item_1 = MeasureItem("i1", 1, Attribute.HEIGHT, 0)
        item_2 = MeasureItem("i2", 3, Attribute.HEIGHT, 1)
        item_3 = MeasureItem("i3", 5, Attribute.HEIGHT, 2)
        challenge = MeasureChallenge(
            challenge_id="test-c2",
            mode=MeasureMode.ORDER,
            attribute=Attribute.HEIGHT,
            items=(item_2, item_1, item_3),  # unsorted
            target_id="ordered",
            target_units=3,
            unit_capacity=0,
            choice_values=(1, 2, 3),
            prompt_key="prompt.order_height",
        )
        session = MeasureSession([challenge] * 5, level=2)

        # Click out of order
        self.assertIsNone(session.select_item("i2"))
        self.assertIsNone(session.select_item("i1"))
        res = session.select_item("i3")
        self.assertIsNotNone(res)
        assert res is not None
        self.assertFalse(res.correct)

        # Click in correct order (i1, i2, i3)
        self.assertIsNone(session.select_item("i1"))
        self.assertIsNone(session.select_item("i2"))
        res = session.select_item("i3")
        self.assertIsNotNone(res)
        assert res is not None
        self.assertTrue(res.correct)
        self.assertEqual(session.challenge_index, 1)

    def test_completion_payload_is_one_shot(self) -> None:
        factory = MeasureRoundFactory(random.Random(42))
        session = MeasureSession(factory.build_set(3), level=3)

        while not session.is_complete:
            current = session.current_challenge
            assert current is not None
            session.select_answer_value(current.target_units)

        payload = session.consume_completion()
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["level"], 3)
        self.assertEqual(payload["first_attempt_count"], 5)
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
        repo = GreiaMeasureProgress(storage)
        self.assertEqual(repo.load(), MeasureProgress())

        history = [AttemptSummary(True, 0, False) for _ in range(20)]
        repo.save(3, history)
        self.assertIsNotNone(storage.saved)
        self.assertEqual(storage.saved["level"], 3)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)


class ManifestTests(unittest.TestCase):
    def test_manifest_declares_exact_milestone_completion_and_range(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.bottega-delle-misure")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "pointer")
        self.assertEqual(manifest["education"]["difficulty_min"], 1)
        self.assertEqual(manifest["education"]["difficulty_max"], 5)
        self.assertEqual(
            manifest["education"]["events"],
            [
                {"id": "measure.parcel_completed", "kind": "milestone"},
                {"id": "measure.delivery_completed", "kind": "completion"},
            ],
        )


class _MockEvents:
    def __init__(self) -> None:
        self.milestones: list[dict[str, int]] = []
        self.completions: list[dict[str, int]] = []

    def parcel_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.milestones.append(payload)

    def delivery_completed(self, session_id: str, payload: dict[str, int]) -> None:
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
        from measure_app import BottegaActivity
        from measure_art import MeasureArt
        from measure_renderer import MeasureRenderer

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        canvas = PygameReferenceCanvas(screen)
        art = MeasureArt(1024, 600)
        renderer = MeasureRenderer(art, typography, resources)
        storage = _Storage({"schema_version": 1, "level": level, "history": []})
        progress = GreiaMeasureProgress(storage)
        events = _MockEvents()
        audio = _MockAudio()
        rng = random.Random(88)
        factory = MeasureRoundFactory(rng)
        session = MeasureSession(factory.build_set(level), level=level)

        simulated_time = [100.0]

        def clock() -> float:
            return simulated_time[0]

        app = BottegaActivity(
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
            session_id="bottega-session-1",
            clock=clock,
        )
        return app, simulated_time, events, audio, progress

    def test_full_session_to_completion_and_restart(self) -> None:
        from measure_app import AppState

        app, sim_time, events, audio, progress = self._build_app(level=3)

        for _ in range(5):
            current = app.session.current_challenge
            assert current is not None
            # Choose correct answer via pointer
            from measure_renderer import CHOICE_RECTS
            choice_idx = next(i for i, v in enumerate(current.choice_values) if v == current.target_units)
            rect = CHOICE_RECTS[choice_idx]
            app._handle_pointer((rect.centerx, rect.centery))
            sim_time[0] += 0.6
            app._advance_state()
            sim_time[0] += 0.3
            app._advance_state()

        self.assertEqual(app.state, AppState.TERMINAL)
        self.assertEqual(len(events.completions), 1)
        self.assertEqual(len(events.milestones), 5)

        # Play Again
        handled = app._handle_terminal_pointer(
            (app.completion._primary_rect.centerx, app.completion._primary_rect.centery)
        )
        self.assertTrue(handled)
        self.assertEqual(app.state, AppState.PLAYING)
        self.assertEqual(app.session.challenge_index, 0)


class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_bottega_delle_misure(self) -> None:
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
            registration = next(r for r in registrations if r.manifest.activity_id == "org.greia.bottega-delle-misure")
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

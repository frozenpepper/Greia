from __future__ import annotations

from pathlib import Path
import random
import sys
import tomllib
import unittest

import pygame


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "specchi_magici"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from mirror_model import (  # noqa: E402
    AttemptSummary,
    CHALLENGE_COUNT,
    GRID_COLS,
    GRID_ROWS,
    HISTORY_LIMIT,
    MirrorRoundFactory,
    MirrorSession,
    MosaicPuzzle,
    Piece,
    ShapeKind,
    adapt_level,
    mirror_col,
    reflect_piece,
)
from mirror_services import GreiaMirrorProgress, MirrorProgress  # noqa: E402


class SymmetryInvariantsTests(unittest.TestCase):
    def test_mirror_col_is_exact_involution(self) -> None:
        for c in range(GRID_COLS):
            mc = mirror_col(c)
            self.assertEqual(mirror_col(mc), c)
            self.assertEqual(c + mc, GRID_COLS - 1)

    def test_reflect_piece_is_exact_involution(self) -> None:
        for kind in ShapeKind:
            for color in range(5):
                rotations = (0,) if kind in {ShapeKind.CIRCLE, ShapeKind.SQUARE} else (0, 1, 2, 3)
                for rot in rotations:
                    piece = Piece(kind, color, rot)
                    reflected = reflect_piece(piece)
                    self.assertEqual(reflect_piece(reflected), piece)
                    if kind in {ShapeKind.CIRCLE, ShapeKind.SQUARE}:
                        self.assertEqual(reflected.rotation, 0)
                    elif kind in {ShapeKind.TRIANGLE, ShapeKind.SEMICIRCLE}:
                        # Vertical reflection maps 1 (RIGHT) <-> 3 (LEFT) while 0 (UP) and 2 (DOWN) stay fixed
                        if rot in {0, 2}:
                            self.assertEqual(reflected.rotation, rot)
                        elif rot == 1:
                            self.assertEqual(reflected.rotation, 3)
                        elif rot == 3:
                            self.assertEqual(reflected.rotation, 1)


class MirrorRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_generates_six_unique_puzzles(self) -> None:
        first = MirrorRoundFactory(random.Random(12345)).build_set(3)
        second = MirrorRoundFactory(random.Random(12345)).build_set(3)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)

        for p in first:
            self.assertTrue(p.givens)
            self.assertTrue(p.required)
            self.assertEqual(len(p.givens), len(p.required))
            self.assertEqual(len(p.tray_pieces), len(p.required))

    def test_each_level_adheres_to_planned_invariants(self) -> None:
        factory = MirrorRoundFactory(random.Random(999))
        for level in range(1, 6):
            puzzles = factory.build_set(level, count=6)
            for p in puzzles:
                if level == 1:
                    # Circles & Squares only, no rotation
                    for g in p.givens:
                        self.assertIn(g.piece.kind, {ShapeKind.CIRCLE, ShapeKind.SQUARE})
                        self.assertEqual(g.piece.rotation, 0)


class MirrorSessionTests(unittest.TestCase):
    def test_correct_placement_and_undo(self) -> None:
        p1_left = Piece(ShapeKind.CIRCLE, 0, 0)
        p1_right = reflect_piece(p1_left)
        from mirror_model import CellPlacement
        puzzle = MosaicPuzzle(
            puzzle_id="test-p1",
            givens=(CellPlacement(1, 1, p1_left),),
            required=(CellPlacement(1, 6, p1_right),),
            tray_pieces=(p1_right,),
        )
        session = MirrorSession([puzzle] * 6, level=1)

        # Place piece at wrong coordinate (1, 5)
        res = session.place_selected_at(1, 5)
        self.assertIsNotNone(res)
        assert res is not None
        self.assertFalse(res.correct)
        self.assertEqual(session.puzzle_index, 0)

        # Place piece at correct coordinate (1, 6)
        res = session.place_selected_at(1, 6)
        self.assertIsNotNone(res)
        assert res is not None
        self.assertTrue(res.correct)
        self.assertTrue(res.puzzle_completed)
        self.assertEqual(session.puzzle_index, 1)

        milestone = session.consume_milestone()
        self.assertIsNotNone(milestone)
        assert milestone is not None
        self.assertEqual(milestone["puzzle_index"], 1)

    def test_undo_restores_placed_piece_to_tray(self) -> None:
        from mirror_model import CellPlacement
        p1 = Piece(ShapeKind.CIRCLE, 0, 0)
        p2 = Piece(ShapeKind.SQUARE, 1, 0)
        puzzle = MosaicPuzzle(
            puzzle_id="test-p2",
            givens=(CellPlacement(0, 0, p1), CellPlacement(2, 2, p2)),
            required=(CellPlacement(0, 7, p1), CellPlacement(2, 5, p2)),
            tray_pieces=(p1, p2),
        )
        session = MirrorSession([puzzle] * 6, level=1)
        self.assertEqual(len(session.tray), 2)

        # Select p1 and place at (0, 7)
        session.select_tray_index(0)
        session.place_selected_at(0, 7)
        self.assertEqual(len(session.tray), 1)
        self.assertIn((0, 7), session.grid)

        # Undo
        self.assertTrue(session.undo())
        self.assertEqual(len(session.tray), 2)
        self.assertNotIn((0, 7), session.grid)

    def test_completion_payload_is_one_shot(self) -> None:
        factory = MirrorRoundFactory(random.Random(42))
        session = MirrorSession(factory.build_set(1), level=1)

        while not session.is_complete:
            p = session.current_puzzle
            assert p is not None
            for req in p.required:
                idx = next(i for i, piece in enumerate(session.tray) if piece == req.piece)
                session.select_tray_index(idx)
                session.place_selected_at(req.row, req.col)

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
        repo = GreiaMirrorProgress(storage)
        self.assertEqual(repo.load(), MirrorProgress())

        history = [AttemptSummary(True, 0, False) for _ in range(20)]
        repo.save(3, history)
        self.assertIsNotNone(storage.saved)
        self.assertEqual(storage.saved["level"], 3)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)


class ManifestTests(unittest.TestCase):
    def test_manifest_declares_exact_milestone_completion_and_range(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.specchi-magici")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "pointer")
        self.assertEqual(manifest["education"]["difficulty_min"], 1)
        self.assertEqual(manifest["education"]["difficulty_max"], 5)
        self.assertEqual(
            manifest["education"]["events"],
            [
                {"id": "mirror.mosaic_completed", "kind": "milestone"},
                {"id": "mirror.gallery_completed", "kind": "completion"},
            ],
        )


class _MockEvents:
    def __init__(self) -> None:
        self.milestones: list[dict[str, int]] = []
        self.completions: list[dict[str, int]] = []

    def mosaic_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.milestones.append(payload)

    def gallery_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.completions.append(payload)


class _MockAudio:
    def __init__(self) -> None:
        self.played: list[str] = []

    def play(self, cue: str) -> None:
        self.played.append(cue)

    def play_welcome(self) -> None:
        self.played.append("welcome")

    def play_prompt(self) -> None:
        self.played.append("prompt")

    def play_shape(self, kind: ShapeKind) -> None:
        self.played.append(f"shape_{kind.value}")

    def play_mosaic_complete(self) -> None:
        self.played.append("mosaic_complete")

    def play_feedback(self, correct: bool) -> None:
        self.played.append("correct" if correct else "retry")


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
        from mirror_app import MirrorActivity
        from mirror_art import MirrorArt
        from mirror_renderer import MirrorRenderer

        screen = pygame.display.get_surface()
        assert screen is not None
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        context = resolve_activity_locale("it", support)
        assert context is not None
        resources = LocalizedResources(ACTIVITY_ROOT, context)
        typography = GreiaTypography()
        canvas = PygameReferenceCanvas(screen)
        art = MirrorArt(1024, 600)
        renderer = MirrorRenderer(art, typography, resources)
        storage = _Storage({"schema_version": 1, "level": level, "history": []})
        progress = GreiaMirrorProgress(storage)
        events = _MockEvents()
        audio = _MockAudio()
        rng = random.Random(99)
        factory = MirrorRoundFactory(rng)
        session = MirrorSession(factory.build_set(level), level=level)

        simulated_time = [100.0]

        def clock() -> float:
            return simulated_time[0]

        app = MirrorActivity(
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
            session_id="mirror-session-1",
            clock=clock,
        )
        return app, simulated_time, events, audio, progress

    def test_full_session_to_completion_and_restart(self) -> None:
        from mirror_app import AppState

        app, sim_time, events, audio, progress = self._build_app(level=1)

        for _ in range(6):
            current = app.session.current_puzzle
            assert current is not None
            for req in current.required:
                idx = next(i for i, piece in enumerate(app.session.tray) if piece == req.piece)
                app.session.select_tray_index(idx)
                rect = app.renderer.cell_rect(req.row, req.col)
                app._handle_pointer((rect.centerx, rect.centery))

            sim_time[0] += 0.5
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
        self.assertEqual(app.session.puzzle_index, 0)

    def test_listen_button_replays_welcome(self) -> None:
        from mirror_renderer import LISTEN_BTN_RECT

        app, _sim_time, _events, audio, _progress = self._build_app(level=1)
        audio.played.clear()

        # Click listen button
        handled = app._handle_pointer((LISTEN_BTN_RECT.centerx, LISTEN_BTN_RECT.centery))
        self.assertTrue(handled)
        self.assertIn("welcome", audio.played)

    def test_audio_assets_and_speech_cues(self) -> None:
        from mirror_audio import MirrorAudio

        for locale in ("it", "en"):
            audio = MirrorAudio(ACTIVITY_ROOT, locale=locale)
            self.assertGreaterEqual(len(audio._speech_clips), 14, f"missing clips for {locale}")
            for key in (
                "welcome",
                "prompt_place",
                "correct_1",
                "correct_2",
                "correct_3",
                "correct_4",
                "correct_5",
                "retry_1",
                "retry_2",
                "mosaic_complete",
                "shape_circle",
                "shape_square",
                "shape_triangle",
                "shape_semicircle",
            ):
                self.assertIn(key, audio._speech_clips, f"missing {key} in {locale}")



class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_specchi_magici(self) -> None:
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
            registration = next(r for r in registrations if r.manifest.activity_id == "org.greia.specchi-magici")
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

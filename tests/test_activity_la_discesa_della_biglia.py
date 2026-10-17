"""Tests for La Discesa della Biglia / Tito's Marble Run (manifest, physics,
authored boards, hints, saves and the real app loop)."""

from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "la_discesa_della_biglia"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

import tomllib  # noqa: E402

from ramp_content import (  # noqa: E402
    ALL_BOARDS,
    BOARD_HEIGHT,
    BOARD_SETS,
    BOARD_WIDTH,
    BOARDS_PER_SET,
    MARBLE_RADIUS,
    MAX_RUN_SECONDS,
    MAX_STEPS_PER_FRAME,
    STEP_SECONDS,
    Basket,
    Board,
    Facing,
    PieceKind,
    Placement,
    Shelf,
    Start,
)
from ramp_engine import Outcome, shelf_capsules  # noqa: E402
from ramp_model import (  # noqa: E402
    SNAP_AFTER_MISSES,
    BoardState,
    HintAction,
    HintPlanner,
    RampProgress,
    Visit,
)
from ramp_services import (  # noqa: E402
    SCHEMA_VERSION,
    STORAGE_KEY,
    GreiaRampEvents,
    GreiaRampProgress,
    progress_from_payload,
    progress_payload,
)

LOCALES = ("en", "it", "es", "fr")


def _arrange(board: Board, placements) -> BoardState:
    state = BoardState(board)
    for placement in placements:
        state.facings[placement.piece] = placement.facing
        state.place(placement.piece, placement.slot)
    return state


def _outcome(board: Board, placements) -> Outcome:
    return _arrange(board, placements).new_run().run_to_end()


def _arrangements(board: Board):
    """Every distinct arrangement of the tray pieces in the slots (ramps both ways)."""

    options = []
    for kind in board.pieces:
        facings = (Facing.RIGHT, Facing.LEFT) if kind is PieceKind.RAMP else (Facing.RIGHT,)
        options.append([None] + [(slot, facing) for slot in range(len(board.slots)) for facing in facings])
    seen = set()
    for combo in itertools.product(*options):
        used = [item[0] for item in combo if item]
        if len(used) != len(set(used)):
            continue
        placements = tuple(Placement(i, item[0], item[1]) for i, item in enumerate(combo) if item)
        key = frozenset(_arrange(board, placements).arrangement().items())
        if key in seen:
            continue
        seen.add(key)
        yield placements, key


class _Storage:
    def __init__(self, value=None) -> None:
        self.values = {} if value is None else {STORAGE_KEY: value}

    def kv_get(self, key, default=None):
        return self.values.get(key, default)

    def kv_set(self, key, value) -> None:
        self.values[key] = json.loads(json.dumps(value))


class _Audio:
    def __init__(self) -> None:
        self.spoken: list[str] = []
        self.sounds: list[str] = []

    def say(self, cue: str) -> None:
        self.spoken.append(cue)

    def play(self, name: str) -> None:
        self.sounds.append(name)


class _Events:
    def __init__(self) -> None:
        self.started: list[tuple] = []
        self.hits: list[tuple] = []
        self.misses: list[tuple] = []
        self.sets: list[tuple] = []

    def run_started(self, *args) -> None:
        self.started.append(args)

    def basket_hit(self, *args) -> None:
        self.hits.append(args)

    def basket_missed(self, *args) -> None:
        self.misses.append(args)

    def set_completed(self, *args) -> None:
        self.sets.append(args)


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_cause_and_effect_loop(self) -> None:
        data = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["activity"]["id"], "org.greia.la-discesa-della-biglia")
        self.assertEqual(data["activity"]["version"], "0.2.0")
        self.assertEqual(set(data["activity"]["languages"]), {"it", "en", "es", "fr"})  # four released languages (owner 2026-10-17)
        self.assertEqual(data["input"]["profile"], "hybrid")
        education = data["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 7))
        # A fixed authored ladder: no adaptive range is claimed.
        self.assertNotIn("adaptive_difficulty", education)
        self.assertNotIn("difficulty_min", education)
        events = {event["id"]: event["kind"] for event in education["events"]}
        self.assertEqual(
            events,
            {
                "ramp.run_started": "milestone",
                "ramp.basket_hit": "milestone",
                "ramp.basket_missed": "milestone",
                "ramp.set_completed": "completion",
            },
        )

    def test_four_locale_parity_without_emoji_or_retired_text_buttons(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in LOCALES
        }
        keys = set(bundles["en"]["strings"])
        self.assertEqual(
            keys,
            {"activity.title", "activity.la_discesa_della_biglia.title", "btn.go", "victory.title", "btn.play_again"},
        )
        for locale, bundle in bundles.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(bundle["strings"]), keys)
                for value in bundle["strings"].values():
                    self.assertTrue(value.strip())
                    self.assertTrue(all(ord(ch) < 0x2000 for ch in value), value)
                    self.assertNotEqual(value, value.upper(), "case comes from the platform policy (ADR 0034)")
        self.assertEqual(bundles["es"]["audio"], {})
        self.assertEqual(bundles["fr"]["audio"], {})
        source = "\n".join(path.read_text(encoding="utf-8") for path in ACTIVITY_ROOT.glob("*.py"))
        for retired in ("ui.drop", "ui.clear", "ui.tool_", "ui.miss", "PALETTE_TAPBOX", "FAI CADERE"):
            self.assertNotIn(retired, source)
        self.assertIn('CastFeedback("tito"', source)
        self.assertIn("CompletionScene(self.kit", source)


class AuthoredBoardTests(unittest.TestCase):
    def test_sets_introduce_one_new_piece_at_a_time(self) -> None:
        seen: set[PieceKind] = set()
        for board_set in BOARD_SETS:
            self.assertEqual(len(board_set.boards), BOARDS_PER_SET)
            kinds = {kind for board in board_set.boards for kind in board.pieces}
            self.assertEqual(kinds - seen, {board_set.new_piece}, board_set.set_id)
            self.assertIn(board_set.new_piece, board_set.boards[0].pieces)
            seen |= kinds
        self.assertEqual(seen, set(PieceKind))

    def test_boards_are_well_formed_and_inside_the_board(self) -> None:
        ids = [board.board_id for board in ALL_BOARDS]
        self.assertEqual(len(ids), len(set(ids)))
        for board in ALL_BOARDS:
            with self.subTest(board=board.board_id):
                self.assertTrue(1 <= len(board.slots) <= 3)
                self.assertTrue(1 <= len(board.pieces) <= 3)
                self.assertTrue(board.solutions)
                for x, y in board.slots:
                    self.assertTrue(80 <= x <= BOARD_WIDTH - 80 and 60 <= y <= BOARD_HEIGHT - 60)
                self.assertTrue(MARBLE_RADIUS < board.start.x < BOARD_WIDTH - MARBLE_RADIUS)
                for solution in board.solutions:
                    self.assertEqual(len({p.slot for p in solution}), len(solution))
                    self.assertEqual(len({p.piece for p in solution}), len(solution))
                    for placement in solution:
                        self.assertLess(placement.piece, len(board.pieces))
                        self.assertLess(placement.slot, len(board.slots))

    def test_every_solution_lands_in_the_basket_and_an_empty_board_does_not(self) -> None:
        for board in ALL_BOARDS:
            with self.subTest(board=board.board_id):
                self.assertIs(_outcome(board, ()), Outcome.LOST)
                for solution in board.solutions:
                    self.assertIs(_outcome(board, solution), Outcome.BASKET)

    def test_only_arrangements_containing_a_solution_win_so_every_board_needs_a_decision(self) -> None:
        for board in ALL_BOARDS:
            wanted = [
                frozenset(_arrange(board, solution).arrangement().items()) for solution in board.solutions
            ]
            wins = losses = 0
            for placements, key in _arrangements(board):
                run = _arrange(board, placements).new_run()
                outcome = run.run_to_end()
                self.assertLessEqual(run.elapsed, MAX_RUN_SECONDS + STEP_SECONDS)  # every run ends
                if outcome is Outcome.BASKET:
                    wins += 1
                    self.assertTrue(any(solution <= key for solution in wanted), (board.board_id, key))
                else:
                    losses += 1
            with self.subTest(board=board.board_id):
                self.assertGreaterEqual(wins, 1)
                self.assertGreaterEqual(losses, 1)

    def test_a_ramp_turned_the_wrong_way_misses(self) -> None:
        for board in ALL_BOARDS:
            solution = board.solutions[0]
            ramps = [p for p in solution if board.pieces[p.piece] is PieceKind.RAMP]
            if not ramps:
                continue
            turned = tuple(
                Placement(p.piece, p.slot, p.facing.flipped()) if p is ramps[0] else p for p in solution
            )
            with self.subTest(board=board.board_id):
                self.assertIsNot(_outcome(board, turned), Outcome.BASKET)


class PhysicsTests(unittest.TestCase):
    def test_runs_are_deterministic_and_frame_rate_independent(self) -> None:
        board = BOARD_SETS[0].boards[0]
        a = _arrange(board, board.solutions[0]).new_run()
        a.run_to_end()
        b = _arrange(board, board.solutions[0]).new_run()
        while not b.finished:
            b.advance(1 / 30)
        c = _arrange(board, board.solutions[0]).new_run()
        while not c.finished:
            c.advance(1 / 61)
        self.assertEqual((a.outcome, a.steps), (b.outcome, b.steps))
        self.assertEqual((a.marble.x, a.marble.y), (b.marble.x, b.marble.y))
        self.assertEqual((a.marble.x, a.marble.y), (c.marble.x, c.marble.y))

    def test_a_stalled_frame_never_fast_forwards_the_marble(self) -> None:
        run = BoardState(BOARD_SETS[0].boards[0]).new_run()
        run.advance(5.0)
        self.assertLessEqual(run.steps, MAX_STEPS_PER_FRAME)

    def test_a_marble_resting_on_a_flat_shelf_settles_instead_of_soft_locking(self) -> None:
        board = Board("flat", Start(400.0, 60.0), Basket(700.0, 452.0), ((200.0, 300.0),), (PieceKind.RAMP,),
                      shelves=(Shelf((300.0, 200.0), (500.0, 200.0)),))
        run = BoardState(board).new_run()
        self.assertIs(run.run_to_end(), Outcome.STOPPED)
        self.assertLess(run.elapsed, MAX_RUN_SECONDS)

    def test_a_marble_trapped_between_bumpers_ends_at_the_time_cap_or_rest(self) -> None:
        board = Board("pocket", Start(400.0, 60.0), Basket(700.0, 452.0), ((330.0, 250.0), (470.0, 250.0)),
                      (PieceKind.FUNNEL, PieceKind.FUNNEL), shelves=(Shelf((300.0, 330.0), (500.0, 330.0)),))
        state = BoardState(board)
        run = state.new_run()
        outcome = run.run_to_end()
        self.assertIn(outcome, (Outcome.STOPPED, Outcome.LOST))
        self.assertLessEqual(run.elapsed, MAX_RUN_SECONDS + STEP_SECONDS)

    def test_a_lost_marble_is_drawn_inside_the_board(self) -> None:
        board = BOARD_SETS[0].boards[0]
        run = BoardState(board).new_run()
        self.assertIs(run.run_to_end(), Outcome.LOST)
        x, y = run.drawn_position()
        self.assertTrue(MARBLE_RADIUS <= x <= BOARD_WIDTH - MARBLE_RADIUS)
        self.assertTrue(MARBLE_RADIUS <= y <= BOARD_HEIGHT - MARBLE_RADIUS)
        self.assertGreater(len(run.trail), 5)

    def test_shelves_are_solid_planks(self) -> None:
        capsules = shelf_capsules((Shelf((0.0, 0.0), (10.0, 0.0)),))
        self.assertEqual(capsules[0].tag, "shelf")


class BoardStateAndHintTests(unittest.TestCase):
    def test_place_swap_turn_and_call_back(self) -> None:
        board = BOARD_SETS[1].boards[3]  # ramp, ramp, bumper / three slots
        state = BoardState(board)
        self.assertEqual(state.selected, 0)
        self.assertEqual(state.place_selected(0), 0)
        self.assertEqual(state.selected, 1)  # selection moves to the next tray piece
        self.assertIsNone(state.place(2, 1))
        displaced = state.place(1, 1)  # swap: the bumper goes back to the tray
        self.assertEqual(displaced, 2)
        self.assertTrue(state.in_tray(2))
        self.assertEqual(state.selected, 2)
        self.assertTrue(state.turn(0))
        self.assertIs(state.facings[0], Facing.LEFT)
        self.assertFalse(state.turn(2))  # bumpers look the same both ways
        self.assertTrue(state.remove(0))
        self.assertTrue(state.in_tray(0))
        state.place(1, 2)  # moving a placed piece leaves its old slot empty
        self.assertIsNone(state.occupant(1))
        self.assertEqual(state.occupant(2), 1)

    def test_following_hints_always_reaches_a_winning_board(self) -> None:
        for board in ALL_BOARDS:
            for start in (None, "scrambled"):
                state = BoardState(board)
                if start:
                    for piece in range(len(board.pieces)):
                        state.facings[piece] = Facing.LEFT
                        state.place(piece, (piece + 1) % len(board.slots)) if piece < len(board.slots) else None
                for _ in range(12):
                    step = HintPlanner.next_step(state)
                    if step.action is HintAction.GO:
                        break
                    self.assertTrue(HintPlanner.apply(state, step), (board.board_id, step))
                with self.subTest(board=board.board_id, start=start):
                    self.assertIs(HintPlanner.next_step(state).action, HintAction.GO)
                    self.assertIs(state.new_run().run_to_end(), Outcome.BASKET)

    def test_hint_turns_a_wrong_way_ramp_before_anything_else(self) -> None:
        board = BOARD_SETS[0].boards[1]  # the basket is on the left
        state = BoardState(board)
        state.place_selected(0)
        step = HintPlanner.next_step(state)
        self.assertEqual((step.action, step.slot), (HintAction.TURN, 0))


class SaveAndEventTests(unittest.TestCase):
    def test_first_release_saves_migrate_and_schema_two_round_trips(self) -> None:
        legacy = {"best_times": {"open": 2.5, "moving": 3.25, "bad": "x", "neg": -1}}
        progress = progress_from_payload(legacy)
        self.assertEqual(progress.legacy_best_times, {"open": 2.5, "moving": 3.25})
        self.assertEqual(progress.next_set, 0)
        payload = progress_payload(progress)
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(payload["best_times"], {"open": 2.5, "moving": 3.25})  # never dropped
        progress.next_set, progress.boards_solved, progress.sets_completed = 2, 9, 2
        again = progress_from_payload(json.loads(json.dumps(progress_payload(progress))))
        self.assertEqual((again.next_set, again.boards_solved, again.sets_completed), (2, 9, 2))
        self.assertEqual(again.legacy_best_times, {"open": 2.5, "moving": 3.25})
        for junk in (None, [], "x", {"schema_version": SCHEMA_VERSION, "next_set": "a", "boards_solved": True}):
            fresh = progress_from_payload(junk)
            self.assertEqual((fresh.next_set, fresh.boards_solved), (0, 0))
        self.assertEqual(progress_from_payload({"schema_version": SCHEMA_VERSION, "next_set": 7}).next_set, 7 % len(BOARD_SETS))

    def test_storage_adapter_uses_the_original_key_and_never_raises(self) -> None:
        self.assertEqual(STORAGE_KEY, "la_discesa_della_biglia.progress.v1")
        storage = _Storage({"best_times": {"narrow": 4.0}})
        adapter = GreiaRampProgress(storage)
        progress = adapter.load()
        self.assertEqual(progress.legacy_best_times, {"narrow": 4.0})
        adapter.save(progress)
        self.assertEqual(storage.values[STORAGE_KEY]["best_times"], {"narrow": 4.0})

        class Broken:
            def kv_get(self, *a):
                raise OSError("disk")

            def kv_set(self, *a):
                raise OSError("disk")

        broken = GreiaRampProgress(Broken())
        self.assertEqual(broken.load().next_set, 0)
        broken.save(RampProgress())

    def test_event_keys_are_scoped_per_visit(self) -> None:
        calls = []
        with mock.patch("ramp_services.emit_activity_event", side_effect=lambda *a, **k: calls.append((a, k))):
            events = GreiaRampEvents()
            events.run_started("v1", "ramps.1", 1)
            events.basket_hit("v1", "ramps.1", 2)
            events.basket_missed("v1", "ramps.1", 1, "lost")
            events.set_completed("v1", "ramps", 4)
            events.basket_hit("v2", "ramps.1", 1)
        keys = [k["idempotency_key"] for _, k in calls]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual([a[0] for a, _ in calls][:4], ["ramp.run_started", "ramp.basket_hit", "ramp.basket_missed", "ramp.set_completed"])


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1024, 600))

    def _app(self, size: tuple[int, int] = (1024, 600), next_set: int = 0, storage=None, locale: str = "en"):
        from greia_platform.localization import activity_resources
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from ramp_app import MarbleRunActivity

        screen = pygame.display.set_mode(size)
        now = [500.0]
        storage = storage if storage is not None else _Storage()
        progress = GreiaRampProgress(storage)
        loaded = progress.load()
        loaded.next_set = next_set
        app = MarbleRunActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            visit=Visit(loaded),
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY_ROOT, requested_locale=locale),
            audio=_Audio(),
            progress=progress,
            events=_Events(),
            clock=lambda: now[0],
        )
        return app, now, storage

    @staticmethod
    def _advance(app, now, seconds: float, step: float = 1 / 30) -> None:
        for _ in range(max(1, int(seconds / step))):
            now[0] += step
            app.step(step)

    def _finish_run(self, app, now) -> None:
        from ramp_app import AppState

        for _ in range(int(MAX_RUN_SECONDS * 30) + 10):
            if app.state is not AppState.RUNNING:
                return
            self._advance(app, now, 1 / 30)
        self.fail("a run did not end")

    def _key_activate(self, app, control_id: str) -> None:
        self.assertTrue(app.controls.layer.focus(control_id, visible=True), control_id)
        self.assertTrue(app.press(pygame.K_SPACE), control_id)

    def _solve_with_keys(self, app, now) -> None:
        """Build the board with keyboard activation only (tray -> slot, turn, GO)."""

        from ramp_app import AppState
        from ramp_controls import slot_id, tray_id

        state = app.board_state
        for _ in range(12):
            step = HintPlanner.next_step(state)
            if step.action is HintAction.GO:
                break
            if step.action is HintAction.PLACE:
                piece = next(p for p in state.tray_pieces() if state.kind(p) is step.kind)
                self._key_activate(app, tray_id(piece))
                self.assertEqual(state.selected, piece)
                if state.facings[piece] is not step.facing:
                    state.facings[piece] = step.facing  # (or place, then Space again to turn)
                self._key_activate(app, slot_id(step.slot))
            elif step.action is HintAction.TURN:
                self._key_activate(app, slot_id(step.slot))
            else:
                self._key_activate(app, tray_id(state.occupant(step.slot)))
        self._key_activate(app, "go")
        self.assertIs(app.state, AppState.RUNNING)
        self._finish_run(app, now)
        app.render()

    def test_keyboard_plays_a_whole_set_to_the_completion_scene_and_moves_on(self) -> None:
        from ramp_app import AppState

        for next_set in range(len(BOARD_SETS)):
            app, now, storage = self._app(next_set=next_set)
            first_visit = app._visit_id
            for index in range(BOARDS_PER_SET):
                self.assertEqual(app.controls.progress.current, index)
                self._solve_with_keys(app, now)
                self.assertIs(app.state, AppState.CELEBRATE)
                self.assertIn("basket", app.audio.spoken)
                self._advance(app, now, 2.2)
            self.assertIs(app.state, AppState.TERMINAL)
            self.assertEqual(len(app.events.hits), BOARDS_PER_SET)
            self.assertEqual(len(app.events.sets), 1)
            self.assertIn("complete", app.audio.spoken)
            saved = storage.values[STORAGE_KEY]
            self.assertEqual((saved["boards_solved"], saved["sets_completed"]), (BOARDS_PER_SET, 1))
            self.assertEqual(saved["next_set"], (next_set + 1) % len(BOARD_SETS))
            app.render()
            self.assertTrue(app.tap(app.canvas.mapper.point(*app.completion.primary_rect.center)))
            self.assertIs(app.state, AppState.BUILD)
            self.assertEqual(app.visit.set_index, (next_set + 1) % len(BOARD_SETS))
            self.assertNotEqual(app._visit_id, first_visit)

    def test_space_on_completion_plays_the_next_set_through_kit_focus(self) -> None:
        from ramp_app import AppState

        app, now, _ = self._app()
        for _ in range(BOARDS_PER_SET):
            self._solve_with_keys(app, now)
            self._advance(app, now, 2.2)
        self.assertIs(app.state, AppState.TERMINAL)
        app.press(pygame.K_SPACE)
        self.assertIs(app.state, AppState.BUILD)
        self.assertEqual(app.visit.set_index, 1)

    def test_pointer_drag_tap_to_turn_and_go(self) -> None:
        from ramp_app import AppState

        app, now, _ = self._app()
        self._advance(app, now, 1.0)
        # Board 1 -> solve; board 2 has the basket on the left.
        self._solve_with_keys(app, now)
        self._advance(app, now, 2.2)
        state = app.board_state
        self.assertEqual(state.board.board_id, "ramps.2")
        tile = app.controls.tray[0].rect.center
        slot = app.view.slot_rect(state.board.slots[0]).center
        mapper = app.canvas.mapper
        self.assertTrue(app.drag_to(mapper.point(*tile), mapper.point(*slot)))
        self.assertEqual(state.occupant(0), 0)
        self.assertIs(state.facings[0], Facing.RIGHT)
        self.assertTrue(app.tap(mapper.point(*slot)))  # tap a placed ramp: it turns
        self.assertIs(state.facings[0], Facing.LEFT)
        self.assertTrue(app.tap(mapper.point(*app.controls.go.rect.center)))
        self.assertIs(app.state, AppState.RUNNING)
        self._finish_run(app, now)
        self.assertIs(app.state, AppState.CELEBRATE)

    def test_dragging_a_piece_off_the_board_returns_it_and_tray_tap_calls_it_back(self) -> None:
        app, now, _ = self._app(next_set=1)
        state = app.board_state
        mapper = app.canvas.mapper
        slot = app.view.slot_rect(state.board.slots[0]).center
        self.assertTrue(app.tap(mapper.point(*slot)))  # tap a slot: the lifted piece goes in
        self.assertEqual(state.occupant(0), 0)
        self.assertTrue(app.drag_to(mapper.point(*slot), mapper.point(500, 560)))
        self.assertIsNone(state.occupant(0))
        self.assertTrue(state.in_tray(0))
        app.tap(mapper.point(*slot))
        self.assertFalse(state.in_tray(0))
        self.assertTrue(app.tap(mapper.point(*app.controls.tray[0].rect.center)))
        self.assertTrue(state.in_tray(0))

    def test_a_miss_thinks_keeps_the_pieces_shows_the_path_and_demonstrates(self) -> None:
        from greia_platform.activity_feedback import CastPose
        from ramp_app import AppState

        app, now, _ = self._app()
        self._solve_with_keys(app, now)
        self._advance(app, now, 2.2)
        state = app.board_state  # ramps.2: the default ramp direction misses
        app._on_slot(0)
        self.assertEqual(state.occupant(0), 0)
        for miss in range(1, SNAP_AFTER_MISSES + 1):
            if state.facings[0] is Facing.LEFT:
                state.turn(0)
            app._on_go()
            self._finish_run(app, now)
            self.assertIs(app.state, AppState.PAUSE)
            self.assertIs(app.cast.feedback.pose, CastPose.THINK)
            self.assertTrue(app.trail)
            self.assertEqual(len(app.events.misses), miss)
            self._advance(app, now, 1.0)
            self.assertIs(app.state, AppState.BUILD)
            self.assertEqual(state.occupant(0), 0)  # pieces stay where the child put them
            self.assertIsNotNone(app.motion.demo)
            self.assertIs(app.motion.demo[0].action, HintAction.TURN)
            if miss < SNAP_AFTER_MISSES:
                self._advance(app, now, 1.5)
                self.assertIs(state.facings[0], Facing.RIGHT)  # demonstrated, not done
        self.assertIn("retry", app.audio.spoken)
        self._advance(app, now, 1.5)
        self.assertIs(state.facings[0], Facing.LEFT)  # third miss: Tito turns it

    def test_idle_hints_are_graduated(self) -> None:
        app, now, _ = self._app()
        app.audio.spoken.clear()
        self._advance(app, now, 6.3)
        self.assertTrue(app.cast.pointing)
        self.assertEqual(app.audio.spoken, ["nudge"])
        self.assertIsNone(app.motion.demo)  # first nudge: point + glow only
        self.assertIn(0, app.motion.pulses)
        self._advance(app, now, 12.3)  # back-off: 6 s, then a further 12 s
        self.assertIsNotNone(app.motion.demo)
        self.assertIs(app.motion.demo[0].action, HintAction.PLACE)
        hints = app.board_state.summary.hints
        self.assertTrue(app.tap(app.canvas.mapper.point(*app.controls.hint.rect.center)))
        self.assertEqual(app.board_state.summary.hints, hints + 1)

    def test_layout_stays_clear_of_protected_chrome_at_every_size(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            app, now, _ = self._app(size=size)
            with self.subTest(size=size):
                layout = ControlLayout.for_canvas(app.canvas, size)
                controls = app.controls
                for control in (*controls.tray, controls.go, controls.hint, controls.progress):
                    self.assertFalse(control.rect.colliderect(layout.protected), control.control_id)
                self.assertFalse(app.view.frame.colliderect(layout.protected))
                self.assertGreaterEqual(app.view.frame.top, controls.screen.bar.bottom)
                self.assertLessEqual(app.view.frame.bottom, 600)
                for tile in controls.tray:
                    self.assertGreaterEqual(tile.rect.height * layout.scale, 40)
                self.assertGreaterEqual(MARBLE_RADIUS * 2 * app.view.scale * layout.scale, 12)
                app.render()

    def test_go_sits_right_under_the_tray_pieces_it_confirms(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            app, now, _ = self._app(size=size)
            with self.subTest(size=size):
                controls = app.controls
                count = len(app.board_state.board.pieces)
                last = controls.tray[count - 1].rect
                go = controls.go.rect
                self.assertEqual(go.left, last.left)
                self.assertGreater(go.top, last.bottom)
                self.assertLessEqual(go.top - last.bottom, 12, "GO directly under the last piece")
                self.assertLessEqual(go.right, app.view.frame.left, "GO never reaches over the board")
                self.assertGreater(go.top, controls.screen.bar.bottom, "GO is no longer in the top bar")
                for count in (1, 2, 3):
                    rect = controls.screen.go_after(count)
                    self.assertEqual(rect.top - controls.tray[count - 1].rect.bottom, go.top - last.bottom)
                cast_top = controls.screen.cast_midbottom[1] - controls.screen.cast_height
                self.assertLessEqual(controls.screen.go_after(3).bottom, cast_top + 12, "Tito stays under GO")

    def test_pointer_in_the_protected_region_is_ignored(self) -> None:
        app, now, _ = self._app()
        before = list(app.board_state.slot_of)
        self.assertFalse(app.tap((10, 10)))
        self.assertEqual(app.board_state.slot_of, before)

    def test_frames_are_blits_only_after_warm_up(self) -> None:
        from ramp_app import AppState

        app, now, _ = self._app(next_set=2)
        state = app.board_state
        for placement in state.board.solutions[0]:
            state.facings[placement.piece] = placement.facing
            state.place(placement.piece, placement.slot)
        app._sync()
        app.render()
        app._on_go()
        self._advance(app, now, 0.2)
        app.render()
        built = app.kit.painter.build_count
        scene = app.scene
        sprites = app.art.sprites(app.view)
        for _ in range(30):  # one second of rolling marble (every run here lasts longer)
            self._advance(app, now, 1 / 30)
            app.render()
            self.assertIs(app.state, AppState.RUNNING)
        self.assertEqual(app.kit.painter.build_count, built)
        self.assertIs(app.scene, scene)
        self.assertIs(app.art.sprites(app.view), sprites)
        self.assertLessEqual(len(app.motion.fx), 12)

    def test_italian_go_label_and_completion_text(self) -> None:
        app, now, _ = self._app(locale="it")
        self.assertEqual(app.controls.go.label, "VIA!")


if __name__ == "__main__":
    unittest.main()

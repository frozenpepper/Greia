"""Tests for Quattro Amici in Fila (org.greia.quattro-amici).

Model tests cover the board, Leo's three brains, games, best-of-three
matches and the adaptive ladder; app-loop tests drive the real Activity
(fake clock, dummy SDL) through turns, hints, try-again, celebrations and a
whole match to the shared completion scene.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from activities.quattro_amici.quattro_content import (  # noqa: E402
    FIRST_STAGE,
    LAST_STAGE,
    STAGES,
    GameMode,
    GameStatus,
    LeoStyle,
    Player,
    stage_for,
)
from activities.quattro_amici.quattro_model import (  # noqa: E402
    EasyLeo,
    Ladder,
    MatchOutcome,
    MediumLeo,
    QuattroBoard,
    QuattroGame,
    QuattroMatch,
    SmartLeo,
    adapt_stage,
    kindness_for,
    suggest_column,
)
from activities.quattro_amici.quattro_services import (  # noqa: E402
    STORAGE_KEY,
    GreiaQuattroProgress,
    QuattroProgress,
)

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "activities" / "quattro_amici"
F, L, E = Player.FLASH, Player.LEO, Player.EMPTY


def _board(rows: list[str], target: int = 3) -> QuattroBoard:
    """Build a board from strings ('.', 'F', 'L'), top row first."""

    board = QuattroBoard(len(rows[0]), len(rows), target)
    mapping = {".": E, "F": F, "L": L}
    board.grid = [[mapping[ch] for ch in row] for row in rows]
    return board


class QuattroBoardTests(unittest.TestCase):
    def test_gravity_stacks_and_full_columns_refuse(self) -> None:
        board = QuattroBoard(5, 4, 3)
        self.assertEqual([board.drop_token(2, p) for p in (F, L, F, L)], [3, 2, 1, 0])
        self.assertFalse(board.can_drop(2))
        self.assertEqual(board.drop_token(2, F), -1)
        self.assertNotIn(2, board.valid_columns())
        self.assertEqual(board.undo_drop(2), 0)
        self.assertEqual(board.landing_row(2), 0)

    def test_lines_in_every_direction_are_found_in_line_order(self) -> None:
        horizontal = _board(["....", "....", ".FFF"])
        self.assertEqual(horizontal.line_at(2, 2), [(2, 1), (2, 2), (2, 3)])
        vertical = _board(["L...", "L...", "L..."])
        self.assertEqual(vertical.line_at(0, 0), [(0, 0), (1, 0), (2, 0)])
        down_right = _board(["F...", "LF..", "LLF."])
        self.assertEqual(down_right.check_win(), (F, [(0, 0), (1, 1), (2, 2)]))
        up_right = _board(["..L.", ".LF.", "LFF."])
        self.assertEqual(up_right.check_win()[0], L)
        self.assertEqual(QuattroBoard(5, 4, 3).check_win(), (E, []))

    def test_threats_and_gifts(self) -> None:
        board = _board([".....", ".....", ".....", ".FF.."])
        self.assertEqual(board.winning_columns(F), [0, 3])
        self.assertEqual(suggest_column(board, F), (0, "win"))
        self.assertEqual(suggest_column(board, L), (0, "block"))
        gift = _board([".....", ".....", ".FF..", ".LLF."])
        # Leo dropping in col 0 lets Flash complete the middle row on top of it.
        self.assertTrue(gift.gives_win_above(0, L))
        self.assertFalse(gift.gives_win_above(4, L))


class LeoBrainTests(unittest.TestCase):
    THREAT = [".....", ".....", ".....", ".FF.."]

    def _rate(self, brain, rows, wanted, kindness=0, me=L, trials=300) -> float:
        hits = 0
        for seed in range(trials):
            choice = brain.choose(_board(rows), me, random.Random(seed), kindness)
            hits += choice in wanted
        return hits / trials

    def test_every_brain_returns_a_legal_column(self) -> None:
        rows = ["F.L.F", "LFLFL", "FLFLF", "LFLFL"]
        for brain in (EasyLeo(), MediumLeo(), SmartLeo()):
            for seed in range(20):
                self.assertIn(brain.choose(_board(rows), L, random.Random(seed)), [1, 3])
        full = _board(["FLF", "LFL"])
        self.assertEqual(MediumLeo().choose(full, L, random.Random(0)), -1)

    def test_easy_leo_sometimes_misses_and_medium_blocks_obvious_rows(self) -> None:
        easy = self._rate(EasyLeo(), self.THREAT, {0, 3})
        medium = self._rate(MediumLeo(), self.THREAT, {0, 3})
        smart = self._rate(SmartLeo(), self.THREAT, {0, 3})
        self.assertLess(easy, 0.75, "easy Leo must leave real chances")
        self.assertGreater(easy, 0.3)
        self.assertGreater(medium, 0.85)
        self.assertGreater(smart, 0.95)

    def test_leo_takes_his_own_win(self) -> None:
        rows = [".....", ".....", ".....", "LL..F"]
        self.assertGreater(self._rate(MediumLeo(), rows, {2}), 0.9)
        self.assertEqual(SmartLeo(slip=0.0).choose(_board(rows), L, random.Random(1)), 2)

    def test_kindness_makes_leo_ease_off(self) -> None:
        strict = self._rate(MediumLeo(), self.THREAT, {0, 3}, kindness=0)
        kind = self._rate(MediumLeo(), self.THREAT, {0, 3}, kindness=2)
        self.assertLess(kind, strict - 0.25)
        self.assertEqual(kindness_for(0), 0)
        self.assertEqual(kindness_for(9), 2)

    def test_smart_leo_stays_within_a_frame_budget_on_the_big_board(self) -> None:
        board = QuattroBoard(7, 6, 4)
        rng = random.Random(5)
        for turn in range(16):
            board.drop_token(rng.choice(board.valid_columns()), F if turn % 2 else L)
        started = time.perf_counter()
        for seed in range(10):
            SmartLeo(slip=0.0).choose(board, L, random.Random(seed))
        self.assertLess((time.perf_counter() - started) / 10, 0.05)


class QuattroGameAndMatchTests(unittest.TestCase):
    def test_turns_wins_and_blocks(self) -> None:
        game = QuattroGame(stage_for(1))
        for col in (1, 1, 2, 2):
            self.assertTrue(game.drop(col).ok)
        self.assertEqual(game.current_player, F)
        blocked = QuattroGame(stage_for(1))
        for col in (1, 4, 2):
            blocked.drop(col)
        result = blocked.drop(3)  # Leo fills Flash's winning hole
        self.assertTrue(result.blocked)
        won = game.drop(3)
        self.assertEqual(won.status, GameStatus.WON)
        self.assertEqual(game.winner, F)
        self.assertEqual(game.winning_cells, [(3, 1), (3, 2), (3, 3)])
        self.assertFalse(game.drop(0).ok)

    def test_full_board_without_row_is_a_draw(self) -> None:
        game = QuattroGame(stage_for(1))
        rows = ["FFLL.", "LLFFL", "FFLLF", "LLFFL"]
        game.board = _board(rows)
        self.assertEqual(game.drop(4).status, GameStatus.DRAW)
        self.assertEqual(game.winner, E)

    def test_stages_grow_from_connect_three_to_connect_four(self) -> None:
        self.assertEqual((STAGES[1].cols, STAGES[1].rows, STAGES[1].target), (5, 4, 3))
        self.assertEqual((STAGES[LAST_STAGE].cols, STAGES[LAST_STAGE].rows, STAGES[LAST_STAGE].target), (7, 6, 4))
        self.assertEqual(STAGES[1].leo, LeoStyle.EASY)
        self.assertEqual(stage_for(99).number, LAST_STAGE)
        self.assertEqual(stage_for(-1).number, FIRST_STAGE)

    def test_best_of_three_alternates_starters_and_ends_at_two_wins(self) -> None:
        match = QuattroMatch(stage_for(1), GameMode.VS_CPU)
        starters = []
        for winner in (F, L, F):
            starters.append(match.game.starter)
            match.game.status, match.game.winner = GameStatus.WON, winner
            self.assertTrue(match.record_game())
            self.assertFalse(match.record_game(), "a game is recorded once")
            if not match.over:
                match.next_game()
        self.assertEqual(starters, [F, L, F])
        self.assertTrue(match.over)
        self.assertEqual(match.outcome, MatchOutcome.FLASH)
        early = QuattroMatch(stage_for(1), GameMode.VS_CPU)
        for _ in range(2):
            early.game.status, early.game.winner = GameStatus.WON, L
            early.record_game()
            if not early.over:
                early.next_game()
        self.assertTrue(early.over)
        self.assertEqual(len(early.results), 2)
        self.assertEqual(early.outcome, MatchOutcome.LEO)

    def test_draws_count_and_three_games_cap_the_match(self) -> None:
        match = QuattroMatch(stage_for(1), GameMode.TWO_PLAYERS)
        for winner in (F, E, L):
            match.game.status = GameStatus.WON if winner else GameStatus.DRAW
            match.game.winner = winner
            match.record_game()
            if not match.over:
                match.next_game()
        self.assertTrue(match.over)
        self.assertEqual(match.outcome, MatchOutcome.TIE)
        with self.assertRaises(RuntimeError):
            match.next_game()

    def test_ladder_climbs_on_a_won_match_and_eases_after_two_losses(self) -> None:
        self.assertEqual(adapt_stage(Ladder(1, 0), MatchOutcome.FLASH), Ladder(2, 0))
        self.assertEqual(adapt_stage(Ladder(LAST_STAGE, 0), MatchOutcome.FLASH).stage, LAST_STAGE)
        self.assertEqual(adapt_stage(Ladder(3, 0), MatchOutcome.LEO), Ladder(3, 1))
        self.assertEqual(adapt_stage(Ladder(3, 1), MatchOutcome.LEO), Ladder(2, 0))
        self.assertEqual(adapt_stage(Ladder(1, 1), MatchOutcome.LEO), Ladder(1, 0))
        self.assertEqual(adapt_stage(Ladder(2, 1), MatchOutcome.TIE), Ladder(2, 1))


class _Storage:
    def __init__(self, value=None, *, refuse: bool = False) -> None:
        self.value = value
        self.refuse = refuse

    def kv_get(self, key):
        return self.value

    def kv_set(self, key, value):
        if self.refuse:
            raise OSError("volume budget")
        self.value = value


class QuattroProgressTests(unittest.TestCase):
    def test_round_trip_and_defaults(self) -> None:
        storage = _Storage()
        progress = GreiaQuattroProgress(storage)
        self.assertEqual(progress.load(), QuattroProgress())
        progress.save(QuattroProgress(Ladder(3, 1), GameMode.TWO_PLAYERS))
        self.assertEqual(storage.value["schema_version"], 1)
        self.assertEqual(progress.load(), QuattroProgress(Ladder(3, 1), GameMode.TWO_PLAYERS))
        self.assertEqual(STORAGE_KEY, "quattro_amici.progress.v1")

    def test_damaged_or_refused_storage_never_breaks_the_game(self) -> None:
        damaged = GreiaQuattroProgress(_Storage({"schema_version": 1, "stage": 42, "mode": "chess", "loss_streak": -3}))
        self.assertEqual(damaged.load(), QuattroProgress())
        self.assertEqual(GreiaQuattroProgress(_Storage(["junk"])).load(), QuattroProgress())
        GreiaQuattroProgress(_Storage(refuse=True)).save(QuattroProgress(Ladder(2, 0)))


class QuattroPackageTests(unittest.TestCase):
    def test_manifest_matches_the_real_game(self) -> None:
        from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
        from greia_platform.trust import ActivitySource, PackageTrust

        runtime = RuntimeCatalogue.load(ROOT / "runtime" / "child-runtime.toml")
        source = ActivitySource(ROOT / "activities", trust=PackageTrust.BUILT_IN, source_id="builtin")
        manifest = ActivityRegistry([source], runtime).validate_package(PACKAGE)
        self.assertEqual(manifest.activity_id, "org.greia.quattro-amici")
        self.assertEqual(manifest.title_key, "activity.quattro_amici.title")
        self.assertEqual(set(manifest.languages), {"en", "it"})
        self.assertTrue(manifest.adaptive_difficulty)
        self.assertEqual(manifest.difficulty_min, FIRST_STAGE)
        self.assertEqual(manifest.difficulty_max, LAST_STAGE)
        import tomllib

        raw = tomllib.loads((PACKAGE / "activity.toml").read_text(encoding="utf-8"))
        education = raw["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 7))
        kinds = {event["id"]: event["kind"] for event in education["events"]}
        self.assertEqual(kinds["quattro.match_completed"], "completion")
        self.assertEqual(list(kinds.values()).count("completion"), 1)

    def test_four_locales_have_key_parity_and_every_used_key(self) -> None:
        bundles = {
            locale: json.loads((PACKAGE / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in ("en", "it", "es", "fr")
        }
        keys = set(bundles["en"]["strings"])
        for locale, bundle in bundles.items():
            self.assertEqual(set(bundle["strings"]), keys, locale)
        source = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE.glob("*.py"))
        import re

        used = set(re.findall(r'"(ui\.[a-z_]+)"', source))
        self.assertTrue(used)
        self.assertLessEqual(used, keys, f"missing strings: {used - keys}")
        for locale in ("en", "it"):
            self.assertTrue((PACKAGE / "locales" / locale / "audio" / "activity-title.wav").is_file())

    def test_art_is_package_svg_plus_rendition_and_icon_is_256_rgba(self) -> None:
        for name in ("token_carrot", "token_acorn", "icon"):
            self.assertTrue((PACKAGE / "assets" / "source" / f"{name}.svg").is_file(), name)
        for name in ("token_carrot", "token_acorn"):
            self.assertEqual(pygame.image.load(str(PACKAGE / "assets" / "runtime" / f"{name}.png")).get_size(), (128, 128))
        from PIL import Image

        with Image.open(PACKAGE / "assets" / "icon.png") as icon:
            self.assertEqual((icon.size, icon.mode), ((256, 256), "RGBA"))

    def test_voices_resolve_through_the_shared_character_api(self) -> None:
        from greia_platform.localization import shared_character_audio_path

        for speaker in ("flash", "leo"):
            for cue in ("ready.go", "praise.general", "celebrate.success", "encourage.retry", "encourage.progress"):
                path = shared_character_audio_path(ROOT, speaker, cue, "it")
                self.assertIsNotNone(path, f"{speaker}/{cue}")
                self.assertIn("characters/shared", path.as_posix())
        source = (PACKAGE / "quattro_audio.py").read_text(encoding="utf-8")
        self.assertIn("shared_character_audio_path", source)
        self.assertNotIn("../", source)


# ---------------------------------------------------------------------------
# App loop
# ---------------------------------------------------------------------------


class _Progress:
    def __init__(self, saved: QuattroProgress | None = None) -> None:
        self.saved = saved or QuattroProgress()
        self.writes: list[QuattroProgress] = []

    def load(self) -> QuattroProgress:
        return self.saved

    def save(self, progress: QuattroProgress) -> None:
        self.writes.append(progress)


class _Events:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict]] = []

    def emit(self, event_id: str, key: str, payload: dict) -> None:
        self.events.append((event_id, key, payload))

    def ids(self) -> list[str]:
        return [event[0] for event in self.events]


class _Scripted:
    """Leo brain that plays a script, then the first legal column."""

    style = LeoStyle.EASY

    def __init__(self, columns=()) -> None:
        self.columns = list(columns)

    def choose(self, board, me, rng, kindness=0):
        while self.columns:
            col = self.columns.pop(0)
            if board.can_drop(col):
                return col
        return board.valid_columns()[0]


class QuattroAppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        cls.screen = pygame.display.set_mode((1024, 600))

    def setUp(self) -> None:
        import activities.quattro_amici.quattro_app as app_module

        self.module = app_module
        self._brain = app_module.leo_brain_for
        self.now = [100.0]

    def tearDown(self) -> None:
        self.module.leo_brain_for = self._brain

    def _app(self, *, mode=GameMode.VS_CPU, stage=1, script=None, saved=None):
        if script is not None:
            scripted = _Scripted(script)
            self.module.leo_brain_for = lambda style: scripted
        progress = _Progress(saved or QuattroProgress(Ladder(stage, 0), mode))
        events = _Events()
        app = self.module.build_app(
            self.screen, locale="en", progress=progress, events=events, rng=random.Random(4), clock=lambda: self.now[0]
        )
        clacks: list[int] = []
        original = app.audio.play_drop_clack

        def clack() -> None:
            clacks.append(1)
            original()

        app.audio.play_drop_clack = clack  # type: ignore[method-assign]
        return app, progress, events, clacks

    def _run(self, app, seconds: float) -> None:
        for _ in range(int(seconds * 30)):
            self.now[0] += 1 / 30
            app.step()

    def test_drop_animation_settles_and_clacks_once(self) -> None:
        from activities.quattro_amici.quattro_renderer import DropAnimation

        drop = DropAnimation(col=0, target_row=3, player=F, current_y=0.0, target_y=300.0)
        landings = 0
        for _ in range(240):
            settled = drop.update(1 / 60)
            landings += int(drop.consume_landing())
            if settled:
                break
        self.assertTrue(drop.settled)
        self.assertEqual(landings, 1)
        self.assertEqual(drop.current_y, drop.target_y)

    def test_vs_leo_answers_every_turn_with_think_and_glide(self) -> None:
        app, _, events, clacks = self._app()
        Phase = self.module.Phase
        self.assertEqual(app.phase, Phase.TURN)
        for turn in range(3):
            self.assertEqual(app.model.current_player, F)
            if turn == 0:
                self.assertTrue(app.press(pygame.K_SPACE), "Space drops in the focused column")
            else:
                app._on_column(app.model.board.valid_columns()[0])
            self.assertIsNotNone(app.motion.drop, f"drop refused on turn {turn}")
            self._run(app, 0.9)
            if app.phase is Phase.LEO:
                self.assertEqual(app.friends[L].pose_name, "pose_think")
            self._run(app, 2.5)
            if app.model.finished:
                break
            self.assertEqual(len(app.model.history), 2 * (turn + 1), "Leo did not move")
        self.assertEqual(len(clacks), len(app.model.history))
        self.assertIn("quattro.game_started", events.ids())
        self.assertIn("quattro.token_dropped", events.ids())

    def test_two_friends_drop_back_to_back(self) -> None:
        app, *_ = self._app(mode=GameMode.TWO_PLAYERS)
        for turn in range(4):
            app._on_column(turn % 2)
            self._run(app, 1.0)
            self.assertEqual(app.phase, self.module.Phase.TURN)
        self.assertEqual([m.player for m in app.model.history], [F, L, F, L])

    def test_keyboard_moves_the_disc_and_down_drops_it(self) -> None:
        app, *_ = self._app(script=[4])
        start = app.selected_col
        app.press(pygame.K_RIGHT)
        self.assertEqual(app.selected_col, start + 1)
        app.press(pygame.K_DOWN)
        self.assertIsNotNone(app.motion.drop)
        self.assertEqual(app.model.history[0].col, start + 1)

    def test_tap_drops_in_the_tapped_column_and_protected_chrome_is_ignored(self) -> None:
        app, *_ = self._app(script=[4])
        x = app.geometry.column_x(1)
        y = app.geometry.grid.centery
        self.assertTrue(app.tap((x, y)))
        self.assertEqual(app.model.history[0].col, 1)
        self._run(app, 3.5)
        before = len(app.model.history)
        self.assertFalse(app.tap((5, 5)))
        self.assertEqual(len(app.model.history), before)

    def test_full_column_is_a_kind_try_again(self) -> None:
        app, *_ = self._app(mode=GameMode.TWO_PLAYERS)
        for _ in range(4):
            app._on_column(0)
            self._run(app, 1.0)
        app._on_column(0)
        self.assertEqual(app.friends[F].pose_name, "pose_think")
        self.assertEqual(app.motion.wobble_col, 0)
        self.assertEqual(len(app.model.history), 4)
        self.assertEqual(app.phase, self.module.Phase.TURN)

    def test_blocking_leo_earns_a_cheer_and_leo_blocking_points(self) -> None:
        app, *_ = self._app(script=[0, 1, 3])
        app._on_column(4)  # F
        self._run(app, 3.0)  # L at 0
        app._on_column(4)  # F
        self._run(app, 3.0)  # L at 1 -> Leo threatens col 2
        app._on_column(2)
        self._run(app, 0.8)
        self.assertEqual(app.friends[F].pose_name, "pose_cheer")
        block = self._app(script=[3])[0]
        block._on_column(1)
        self._run(block, 3.0)  # Leo plays 3
        block._on_column(2)  # Flash threatens 0 ... Leo has no script left -> first legal (0) blocks
        self._run(block, 1.0)
        self._run(block, 2.0)
        self.assertEqual(block.model.history[-1].col, 0)
        self.assertEqual(block.friends[L].pose_name, "pose_point")

    def test_idle_hints_point_then_glow_the_useful_column(self) -> None:
        app, *_ = self._app(mode=GameMode.TWO_PLAYERS)
        for col in (1, 4, 2, 4):
            app._on_column(col)
            self._run(app, 1.0)
        self._run(app, 6.3)
        self.assertEqual(app.friends[F].pose_name, "pose_point")
        self.assertIsNotNone(app.motion.pulse_start)
        self._run(app, 6.2)
        self.assertIn(app.motion.glow_col, (0, 3))

    def test_whole_match_reaches_the_completion_scene_and_adapts(self) -> None:
        # Game 1: Flash wins on the bottom row; game 2: Leo starts, Flash wins again.
        app, progress, events, _ = self._app(script=[0, 4, 0, 0, 4])
        Phase = self.module.Phase
        for col in (1, 2):
            app._on_column(col)
            self._run(app, 3.2)
        app._on_column(3)
        self._run(app, 1.8)
        self.assertEqual(app.match.results, [F])
        self.assertEqual(app.friends[F].pose_name, "pose_cheer")
        self._run(app, 3.0)
        self.assertEqual(app.phase, Phase.BETWEEN)
        self.assertTrue(app.controls.next_game.visible)
        self.assertTrue(app.press(pygame.K_SPACE), "next game is focused for keyboard/controller")
        self.assertEqual(app.model.starter, L)
        self._run(app, 3.0)
        for col in (1, 2, 3):
            app._on_column(col)
            self._run(app, 3.2)
        self._run(app, 4.0)
        self.assertEqual(app.phase, Phase.MATCH_OVER)
        self.assertIsNotNone(app.completion)
        self.assertEqual(app.match.outcome, MatchOutcome.FLASH)
        self.assertEqual(events.ids().count("quattro.match_completed"), 1)
        self.assertEqual(progress.writes[-1].ladder.stage, 2)
        app.render()
        app._play_again()
        self.assertEqual(app.phase, Phase.TURN)
        self.assertEqual(app.match.stage.number, 2)
        self.assertEqual((app.geometry.cols, app.geometry.rows), (6, 5))
        self.assertEqual(len(app.controls.columns), 6)

    def test_lost_game_makes_flash_think_and_draw_is_friendly(self) -> None:
        app, *_ = self._app(script=[0, 1, 2])
        for col in (4, 4):
            app._on_column(col)
            self._run(app, 3.2)
        app._on_column(3)
        self._run(app, 3.0)
        self.assertEqual(app.match.results, [L])
        self._run(app, 1.0)
        self.assertEqual(app.friends[F].pose_name, "pose_think")
        self.assertEqual(app.friends[L].pose_name, "pose_cheer")
        draw, *_ = self._app(mode=GameMode.TWO_PLAYERS)
        draw.model.board = _board(["FFLL.", "LLFFL", "FFLLF", "LLFFL"])
        draw._on_column(4)
        self._run(draw, 1.0)
        self.assertEqual(draw.match.results, [E])
        self.assertEqual(draw.friends[F].pose_name, "pose_wave")

    def test_mode_toggle_only_at_the_start_and_remembered(self) -> None:
        app, progress, *_ = self._app()
        self.assertTrue(all(slot.enabled for slot in app.controls.mode.controls))
        app.controls.mode.select(GameMode.TWO_PLAYERS.value, notify=True)
        self.assertEqual(app.match.mode, GameMode.TWO_PLAYERS)
        self.assertEqual(progress.writes[-1].mode, GameMode.TWO_PLAYERS)
        app._on_column(2)
        self._run(app, 1.0)
        self.assertFalse(any(slot.enabled for slot in app.controls.mode.controls))

    def test_render_at_small_viewports(self) -> None:
        for size in ((800, 480), (480, 320)):
            screen = pygame.display.set_mode(size)
            app = self.module.build_app(
                screen, locale="it", progress=_Progress(), events=_Events(), clock=lambda: self.now[0]
            )
            app.render()
            app.canvas.present()
            for control in app.controls.layer.targets:
                self.assertFalse(app.controls._layout.overlaps_chrome(control.rect), control.control_id)
        pygame.display.set_mode((1024, 600))


if __name__ == "__main__":
    unittest.main()

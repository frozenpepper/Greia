"""Tests for Il Labirinto Magico (manifest, maze rules, saves, app loop)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "labirinto_magico"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

import tomllib  # noqa: E402

from maze_model import (  # noqa: E402
    LEVELS,
    MAX_LEVEL,
    MAZES_PER_VISIT,
    OPEN,
    WALL,
    LabyrinthProgress,
    Maze,
    MazeEventKind,
    MazeGenerator,
    MazeLayout,
    MazeSummary,
    Visit,
    Walker,
    bfs_path,
    is_cell,
    next_level,
    reachable,
)
from maze_services import (  # noqa: E402
    SCHEMA_VERSION,
    STORAGE_KEY,
    GreiaLabyrinthEvents,
    GreiaLabyrinthProgress,
    progress_from_payload,
    progress_payload,
)

LOCALES = ("en", "it", "es", "fr")


def _grid(rows: list[str]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(WALL if ch == "#" else OPEN for ch in row) for row in rows)


# A 3x2-cell maze with a bend, a junction and a dead end.
#   cells: (1,1) (1,3) (1,5) / (3,1) (3,3) (3,5)
SMALL = _grid(
    [
        "#######",
        "#.....#",
        "#.###.#",
        "#.#...#",
        "#######",
    ]
)


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
        self.stars: list[tuple] = []
        self.solved: list[tuple] = []
        self.visits: list[tuple] = []

    def star_collected(self, *args) -> None:
        self.stars.append(args)

    def maze_solved(self, *args) -> None:
        self.solved.append(args)

    def visit_completed(self, *args) -> None:
        self.visits.append(args)


class ManifestAndLocaleTests(unittest.TestCase):
    def test_manifest_matches_the_route_planning_loop(self) -> None:
        data = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["activity"]["id"], "org.greia.labirinto-magico")
        self.assertEqual(data["activity"]["version"], "0.2.0")
        self.assertEqual(set(data["activity"]["languages"]), {"it", "en"})  # ES/FR stay staged
        self.assertEqual(data["input"]["profile"], "directional")
        education = data["education"]
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 7))
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, len(LEVELS)))
        self.assertTrue(education["adaptive_difficulty"])
        events = {event["id"]: event["kind"] for event in education["events"]}
        self.assertEqual(
            events,
            {"maze.star_collected": "milestone", "maze.solved": "milestone", "maze.completed": "completion"},
        )

    def test_four_locale_parity_without_emoji_or_obsolete_setting_chips(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in LOCALES
        }
        keys = set(bundles["en"]["strings"])
        self.assertEqual(
            keys, {"activity.title", "activity.labirinto_magico.title", "victory.title", "btn.play_again"}
        )
        for locale, bundle in bundles.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(bundle["strings"]), keys)
                for value in bundle["strings"].values():
                    self.assertTrue(value.strip())
                    self.assertTrue(all(ord(ch) < 0x2000 for ch in value), value)
        self.assertEqual(bundles["es"]["audio"], {})
        self.assertEqual(bundles["fr"]["audio"], {})

    def test_no_private_redraw_of_the_cast_or_emoji_hud_remains(self) -> None:
        for name in ("tito_adventurer", "portal_goal", "star_crystal", "arrow_btn"):
            self.assertFalse(list(ACTIVITY_ROOT.rglob(f"{name}.*")), name)
        source = "\n".join(path.read_text(encoding="utf-8") for path in ACTIVITY_ROOT.glob("*.py"))
        for retired in ('"difficulty.', '"biome.', "btn.new_maze", "🔄", "🌌"):
            self.assertFalse(retired in source, retired)
        self.assertIn('CastFeedback("tito"', source)
        self.assertIn("CompletionScene(self.kit", source)


class GeneratorTests(unittest.TestCase):
    def test_every_level_builds_solvable_mazes_with_reachable_items(self) -> None:
        generator = MazeGenerator(random.Random(7))
        for spec in LEVELS:
            for _ in range(30):
                layout = generator.build(spec.level)
                with self.subTest(level=spec.level):
                    self.assertEqual((layout.cols, layout.rows), (spec.cols, spec.rows))
                    self.assertEqual(len(layout.stars), spec.stars)
                    self.assertEqual(layout.key is not None, spec.key)
                    self.assertTrue(bfs_path(layout, layout.start, layout.goal))
                    # Opposite corners, everything on maze cells.
                    self.assertEqual(
                        (layout.start[0] + layout.goal[0], layout.start[1] + layout.goal[1]),
                        (layout.height - 1, layout.width - 1),
                    )
                    for cell in (*layout.stars, layout.key, layout.door):
                        if cell is not None:
                            self.assertTrue(is_cell(cell) and layout.is_open(cell))
                    garden = reachable(layout, layout.start, blocked=(layout.goal,))
                    self.assertTrue(all(star in garden for star in layout.stars))
                    if layout.door is not None:
                        before_door = reachable(layout, layout.start, blocked=(layout.door, layout.goal))
                        self.assertIn(layout.key, before_door)
                        self.assertNotIn(layout.goal, reachable(layout, layout.start, blocked=(layout.door,)))

    def test_ladder_grows_and_low_rungs_guide_with_arrows(self) -> None:
        sizes = [spec.cols * spec.rows for spec in LEVELS]
        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual([spec.level for spec in LEVELS], list(range(1, MAX_LEVEL + 1)))
        self.assertTrue(LEVELS[0].guide_arrows and LEVELS[1].guide_arrows)
        self.assertFalse(any(spec.guide_arrows for spec in LEVELS[2:]))
        self.assertEqual(LEVELS[0].stars, 0)
        self.assertTrue(any(spec.key for spec in LEVELS))
        self.assertGreater(LEVELS[0].braid, LEVELS[-1].braid)


class MovementTests(unittest.TestCase):
    def _maze(self, **kwargs) -> Maze:
        defaults = dict(level=1, grid=SMALL, start=(1, 1), goal=(3, 5))
        defaults.update(kwargs)
        return Maze(MazeLayout(**defaults))

    def test_tito_follows_bends_and_stops_at_junctions_and_dead_ends(self) -> None:
        maze = self._maze()
        # From the start the corridor goes right to the corner (1,5), bends
        # down and ends at the tent: one press walks the whole corridor.
        path = maze.route((0, 1))
        self.assertEqual(path[-1], (3, 5))
        self.assertTrue(all(is_cell(path[-1]) for _ in path))
        down = maze.route((1, 0))
        self.assertEqual(down, [(2, 1), (3, 1)])  # dead end
        events = [maze.enter(cell, final=i == len(down) - 1) for i, cell in enumerate(down)]
        self.assertEqual([e.kind for e in events[-1]], [MazeEventKind.DEAD_END])
        self.assertEqual(maze.summary.dead_ends, 1)
        self.assertEqual(maze.route((0, 1)), [])  # a hedge: no move

    def test_closed_tent_and_locked_door_are_hedges_until_earned(self) -> None:
        maze = self._maze(stars=((3, 1),))
        path = maze.route((0, 1))
        self.assertEqual(path[-1], (1, 5))  # stops in front of the closed tent
        for index, cell in enumerate(path):
            events = maze.enter(cell, final=index == len(path) - 1)
        self.assertEqual([e.kind for e in events], [MazeEventKind.GOAL_LOCKED])
        self.assertTrue(maze.blocked_by_tent((1, 0)))
        self.assertEqual(maze.hint_route()[-1], (3, 1))
        self.assertEqual(maze.open_directions(), [(0, -1)])

        door_maze = self._maze(key=(3, 1), door=(1, 3))
        self.assertEqual(door_maze.route((0, 1)), [])
        self.assertTrue(door_maze.blocked_by_door((0, 1)))
        self.assertEqual(door_maze.hint_route()[-1], (3, 1))
        route = door_maze.route((1, 0))
        for index, cell in enumerate(route):
            events = door_maze.enter(cell, final=index == len(route) - 1)
        self.assertEqual([e.kind for e in events], [MazeEventKind.KEY])
        # With the key the corridor runs on through the start and the door.
        onward = door_maze.route((-1, 0))
        self.assertIn((1, 3), onward)
        kinds = [e.kind for i, c in enumerate(onward) for e in door_maze.enter(c, final=i == len(onward) - 1)]
        self.assertEqual(kinds, [MazeEventKind.DOOR_OPENED, MazeEventKind.SOLVED])
        self.assertTrue(door_maze.solved)

    def test_tap_moves_one_corridor_towards_the_target_never_onto_a_gap(self) -> None:
        maze = self._maze()
        direction, path = maze.direction_towards((1, 3))
        self.assertEqual((direction, path[-1]), ((0, 1), (1, 3)))
        self.assertIsNone(maze.direction_towards((1, 1)))
        direction, path = maze.direction_towards((3, 3))
        self.assertTrue(is_cell(path[-1]))

    def test_walker_reports_each_square_once_and_ends_on_the_last(self) -> None:
        walker = Walker(speed=4.0)
        walker.start((1, 1), [(1, 2), (1, 3), (1, 4), (1, 5)])
        arrived = []
        for _ in range(200):
            arrived.extend(walker.advance(1 / 30))
        self.assertEqual([cell for cell, _ in arrived], [(1, 2), (1, 3), (1, 4), (1, 5)])
        self.assertEqual([last for _, last in arrived], [False, False, False, True])
        self.assertFalse(walker.moving)
        self.assertEqual(walker.position(), (1.0, 5.0))


class AdaptationAndSaveTests(unittest.TestCase):
    def test_next_maze_level_follows_how_the_last_one_went(self) -> None:
        self.assertEqual(next_level(2, MazeSummary(2, 1)), 3)
        self.assertEqual(next_level(MAX_LEVEL, MazeSummary(MAX_LEVEL, 1)), MAX_LEVEL)
        self.assertEqual(next_level(3, MazeSummary(3, 2, dead_ends=4)), 2)
        self.assertEqual(next_level(1, MazeSummary(1, 0, hints=3)), 1)
        self.assertEqual(next_level(3, MazeSummary(3, 2, dead_ends=2)), 3)

    def test_first_release_saves_migrate_and_schema_three_round_trips(self) -> None:
        self.assertEqual(progress_from_payload({"stars": 70}), LabyrinthProgress(level=3, stars=70))
        self.assertEqual(progress_from_payload({"stars": 20}).level, 2)
        self.assertEqual(progress_from_payload({"stars": 2}), LabyrinthProgress(level=1, stars=2))
        for junk in (None, [], "x", {"stars": "lots"}, {"schema_version": 99}):
            self.assertEqual(progress_from_payload(junk).level, 1)
        progress = LabyrinthProgress(level=5, stars=12, mazes_solved=9, visits_completed=2)
        payload = progress_payload(progress)
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(progress_from_payload(payload), progress)
        self.assertEqual(progress_from_payload({**payload, "level": 40}).level, MAX_LEVEL)
        storage = _Storage({"stars": 33})
        adapter = GreiaLabyrinthProgress(storage)
        loaded = adapter.load()
        self.assertEqual((loaded.level, loaded.stars), (2, 33))
        adapter.save(loaded)
        self.assertEqual(storage.values[STORAGE_KEY]["stars"], 33)

    def test_event_keys_are_scoped_per_visit(self) -> None:
        import maze_services

        calls = []
        original = maze_services.emit_activity_event
        maze_services.emit_activity_event = lambda event, payload, idempotency_key: calls.append(
            (event, idempotency_key)
        )
        try:
            events = GreiaLabyrinthEvents()
            events.star_collected("a", 1, 1, 5)
            events.maze_solved("a", 1, MazeSummary(2, 1))
            events.visit_completed("a", 4, 3)
            events.visit_completed("b", 4, 3)
        finally:
            maze_services.emit_activity_event = original
        self.assertEqual(
            calls,
            [
                ("maze.star_collected", "labirinto:a:m1:s1"),
                ("maze.solved", "labirinto:a:m1"),
                ("maze.completed", "labirinto:a:completed"),
                ("maze.completed", "labirinto:b:completed"),
            ],
        )


_KEYS = {(-1, 0): pygame.K_UP, (1, 0): pygame.K_DOWN, (0, -1): pygame.K_LEFT, (0, 1): pygame.K_RIGHT}


class AppLoopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.set_mode((1024, 600))

    def _app(self, level: int = 1, size: tuple[int, int] = (1024, 600), seed: int = 3, storage=None):
        from greia_platform.localization import activity_resources
        from greia_platform.pygame_canvas import PygameReferenceCanvas
        from greia_platform.typography import GreiaTypography
        from maze_app import LabyrinthActivity

        screen = pygame.display.set_mode(size)
        now = [500.0]
        storage = storage if storage is not None else _Storage()
        progress = GreiaLabyrinthProgress(storage)
        loaded = progress.load()
        loaded.level = level
        app = LabyrinthActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            visit=Visit(MazeGenerator(random.Random(seed)), loaded),
            typography=GreiaTypography(),
            resources=activity_resources(ACTIVITY_ROOT, requested_locale="en"),
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

    def _walk_out(self, app, now) -> None:
        while app.walker.moving:
            self._advance(app, now, 0.1)

    def _solve_with_keys(self, app, now) -> None:
        """Steer Tito with arrow keys along the next-thing-to-fetch route."""

        maze = app.maze
        for _ in range(200):
            if maze.solved:
                break
            route = maze.hint_route()
            step = (route[1][0] - maze.position[0], route[1][1] - maze.position[1])
            self.assertTrue(app.press(_KEYS[step]))
            self._walk_out(app, now)
            app.render()
        self.assertTrue(maze.solved)

    def test_keyboard_plays_a_whole_visit_to_the_completion_scene_and_replays(self) -> None:
        from maze_app import AppState

        for level in (1, 4, 6):
            app, now, storage = self._app(level=level)
            first_visit = app._visit_id
            for index in range(MAZES_PER_VISIT):
                self.assertEqual(app.controls.progress.current, index)
                self._solve_with_keys(app, now)
                self.assertIn("solved", app.audio.spoken)
                self._advance(app, now, 2.2)
            self.assertIs(app.state, AppState.TERMINAL)
            self.assertEqual(len(app.events.solved), MAZES_PER_VISIT)
            self.assertEqual(len(app.events.visits), 1)
            self.assertIn("complete", app.audio.spoken)
            saved = storage.values[STORAGE_KEY]
            self.assertEqual((saved["mazes_solved"], saved["visits_completed"]), (MAZES_PER_VISIT, 1))
            self.assertGreaterEqual(saved["level"], level)
            app.render()
            self.assertTrue(app.tap(app.canvas.mapper.point(*app.completion.primary_rect.center)))
            self.assertIs(app.state, AppState.PLAYING)
            self.assertEqual(app.visit.completed, 0)
            self.assertNotEqual(app._visit_id, first_visit)  # fresh idempotency scope
            self._solve_with_keys(app, now)

    def test_space_on_completion_replays_through_kit_focus(self) -> None:
        from maze_app import AppState

        app, now, _ = self._app(level=1)
        for _ in range(MAZES_PER_VISIT):
            self._solve_with_keys(app, now)
            self._advance(app, now, 2.2)
        self.assertIs(app.state, AppState.TERMINAL)
        app.press(pygame.K_SPACE)
        self.assertIs(app.state, AppState.PLAYING)

    def test_star_cheers_and_closed_tent_thinks_and_demonstrates(self) -> None:
        from greia_platform.activity_feedback import CastPose

        app, now, _ = self._app(level=5, seed=21)
        maze = app.maze
        while len(maze.collected) == 0:
            route = maze.hint_route()
            app.press(_KEYS[(route[1][0] - maze.position[0], route[1][1] - maze.position[1])])
            while app.walker.moving and not maze.collected:
                self._advance(app, now, 1 / 30)
        self.assertIs(app.cast.feedback.pose, CastPose.CHEER)
        self.assertEqual(app.controls._star_state, (1, len(maze.layout.stars)))
        self.assertEqual(len(app.events.stars), 1)
        self._walk_out(app, now)
        self._advance(app, now, 2.0)
        # Head for the tent with stars still missing.
        for _ in range(60):
            if maze.tent_ahead() is not None:
                break
            path = bfs_path(maze.layout, maze.position, maze.layout.goal, maze.blocked(allow=maze.layout.goal))
            app.press(_KEYS[(path[1][0] - maze.position[0], path[1][1] - maze.position[1])])
            self._walk_out(app, now)
        self.assertIsNotNone(maze.tent_ahead())
        self.assertFalse(maze.solved)
        self.assertIs(app.cast.feedback.pose, CastPose.THINK)
        self.assertIn("retry", app.audio.spoken)
        self.assertTrue(set(maze.missing_stars) <= set(app.motion.pulses))
        self._advance(app, now, 0.7)
        self.assertIsNotNone(app.motion.firefly)  # demonstration of the way
        self.assertEqual(app.motion.firefly.route[0], maze.position)
        # Pushing into the closed tent again is a kind retry, never a fail.
        tries = maze.summary.locked_tries
        app.press(_KEYS[maze.tent_ahead()])
        self.assertEqual(maze.summary.locked_tries, tries + 1)
        self.assertFalse(maze.solved)

    def test_pointer_tap_walks_tito_and_hud_taps_stay_with_the_kit(self) -> None:
        app, now, _ = self._app(level=2, seed=5)
        maze = app.maze
        direction = maze.open_directions()[0]
        target = maze.route(direction)[-1]
        x, y = app.geometry.center(*target)
        self.assertTrue(app.tap(app.canvas.mapper.point(int(x), int(y))))
        self.assertTrue(app.walker.moving)
        self._walk_out(app, now)
        self.assertEqual(maze.position, target)
        hints = maze.summary.hints
        self.assertTrue(app.tap(app.canvas.mapper.point(*app.controls.hint.rect.center)))
        self.assertEqual(maze.summary.hints, hints + 1)
        self.assertIsNotNone(app.motion.firefly)
        self.assertTrue(app.cast.pointing)

    def test_space_asks_the_firefly_and_idle_hints_are_graduated(self) -> None:
        app, now, _ = self._app(level=3, seed=9)
        self._advance(app, now, 2.0)
        self.assertTrue(app.press(pygame.K_SPACE))
        self.assertEqual(app.maze.summary.hints, 1)
        self.assertIn("hint", app.audio.sounds)
        app.motion.firefly = None
        app.audio.spoken.clear()
        self._advance(app, now, 6.2)
        self.assertTrue(app.cast.pointing)
        self.assertEqual(app.audio.spoken, ["nudge"])
        self.assertIsNone(app.motion.firefly)  # first nudge only points
        self._advance(app, now, 12.2)  # back-off: 6 s, then a further 12 s
        self.assertIsNotNone(app.motion.firefly)
        self.assertEqual(app.maze.summary.hints, 2)

    def test_a_press_while_walking_never_rewrites_the_route_it_is_buffered(self) -> None:
        app, now, _ = self._app(level=3, seed=4)
        maze = app.maze
        direction = maze.open_directions()[0]
        self.assertTrue(app.press(_KEYS[direction]))
        self._advance(app, now, 1 / 30)
        planned = list(app.walker.waypoints)
        self.assertTrue(planned)
        other = (-direction[0], -direction[1])
        app.press(_KEYS[other])
        self.assertEqual(list(app.walker.waypoints), planned)  # unchanged mid-walk
        self.assertEqual(app._queued, other)
        self._walk_out(app, now)
        self._advance(app, now, 0.05)
        self.assertIsNone(app._queued)  # applied on arrival

    def test_bumping_a_hedge_is_soft_and_counted(self) -> None:
        app, now, _ = self._app(level=1)
        maze = app.maze
        closed = [d for d in _KEYS if d not in maze.open_directions()]
        self.assertTrue(closed)
        app.press(_KEYS[closed[0]])
        self.assertEqual(maze.summary.bumps, 1)
        self.assertIn("bump", app.audio.sounds)
        self.assertFalse(app.walker.moving)

    def test_hud_and_maze_stay_clear_of_protected_chrome_at_every_size(self) -> None:
        from greia_platform.activity_controls import ControlLayout

        for size in ((1024, 600), (800, 480), (480, 320), (1280, 800)):
            for level in (1, 6):
                app, now, _ = self._app(level=level, size=size)
                with self.subTest(size=size, level=level):
                    layout = ControlLayout.for_canvas(app.canvas, size)
                    for control in (app.controls.hint, app.controls.progress, app.controls.stars, app.controls.key):
                        self.assertFalse(control.rect.colliderect(layout.protected), control.control_id)
                    maze_rect = app.geometry.rect.inflate(app.geometry.gap, app.geometry.gap)
                    self.assertFalse(maze_rect.colliderect(layout.protected))
                    self.assertGreaterEqual(maze_rect.top, app.controls.bar.bottom)
                    self.assertLessEqual(maze_rect.bottom + app.geometry.depth, 600)
                    self.assertGreaterEqual(app.geometry.cell * layout.scale, 20)
                    app.render()

    def test_frames_are_blits_only_after_warm_up(self) -> None:
        app, now, _ = self._app(level=4, seed=2)
        app.render()
        self._advance(app, now, 0.5)
        app.render()
        built = app.kit.painter.build_count
        scene = app.scene
        for _ in range(30):
            self._advance(app, now, 1 / 30)
            app.render()
        self.assertEqual(app.kit.painter.build_count, built)
        self.assertIs(app.scene, scene)
        self.assertLessEqual(len(app.motion.fx), 12)


if __name__ == "__main__":
    unittest.main()

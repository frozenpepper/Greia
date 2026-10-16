"""La Torre delle Forme (Shape Tower): geometry, fitting, catalogue, services, app loop.

The falling-block / line-clear tests of the 0.1 game were retired with that
game (2026-10-16 rework: the audit found line clears removed the tower the
child built; the owner's design is silhouette fitting with no time pressure).

Runs headlessly (SDL dummy drivers) against the real shared art catalogue,
with an injected clock, in-memory progress and recorded events, so no child
profile data, voices or windows are touched.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tomllib
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT, ROOT / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import pygame

import hermetic_volume
from activities.torre_forme.torre_app import DRAG_THRESHOLD_PX, AppState, TorreActivity
from activities.torre_forme.torre_art import BLOCK_VARIANT, TorreArt
from activities.torre_forme.torre_audio import SHARED_CUES, TorreAudio
from activities.torre_forme.torre_content import BUILDS, RUNGS, TorreSetFactory, distractor_kinds
from activities.torre_forme.torre_layout import (
    BENCH_TOP,
    BOARD_RECT,
    CARD_RECT,
    DANI_TAP_RECT,
    LISTEN_RECT,
    BoardFrame,
    tray_panel,
    tray_rects,
    turn_rect,
)
from activities.torre_forme.torre_model import (
    BUILDS_PER_SET,
    FULL,
    HISTORY_LIMIT,
    MAX_KIT,
    MAX_LEVEL,
    AttemptSummary,
    Block,
    BlockKind,
    BuildPlan,
    OutlineStyle,
    PlaceOutcome,
    Placement,
    Puzzle,
    TorreSession,
    adapt_level,
    place,
    solve,
)
from activities.torre_forme.torre_services import (
    SCHEMA_VERSION,
    STORAGE_KEY,
    GreiaTorreProgress,
    TorreProgress,
    parse_progress,
)
from greia_platform.activity_controls import ControlLayout
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import GreiaTypography

ACTIVITY_ROOT = ROOT / "activities" / "torre_forme"
LOCALES = ("en", "it", "es", "fr")


def setUpModule() -> None:
    # The Simulator supervision test exercises real history/storage services,
    # whose production capacity policy depends on how full the host disk is.
    hermetic_volume.install_for_module()


# -- geometry ------------------------------------------------------------------------


class GeometryTests(unittest.TestCase):
    def test_turns_fold_equivalent_orientations(self) -> None:
        self.assertEqual(Block.of(BlockKind.RECTANGLE, 2), Block(BlockKind.RECTANGLE, 0))
        self.assertEqual(Block.of(BlockKind.SQUARE, 3), Block(BlockKind.SQUARE, 0))
        self.assertEqual(Block(BlockKind.TRIANGLE, 3).turned(), Block(BlockKind.TRIANGLE, 0))
        self.assertFalse(Block(BlockKind.CYLINDER).rotates)
        with self.assertRaises(ValueError):
            Block(BlockKind.RECTANGLE, 2)

    def test_footprints_turn_clockwise(self) -> None:
        lying = Block(BlockKind.HALF_CIRCLE, 0)
        self.assertEqual(lying.size, (2, 1))
        standing = Block(BlockKind.HALF_CIRCLE, 1)
        self.assertEqual(standing.size, (1, 2))
        cells = dict(standing.footprint())
        self.assertEqual(set(cells), {(0, 0), (0, 1)})
        self.assertEqual(cells[(0, 0)][2], 0, "the left half turns to the top")
        self.assertEqual(dict(Block(BlockKind.RECTANGLE, 1).footprint()), {(0, 0): FULL, (0, 1): FULL})
        self.assertNotEqual(Block(BlockKind.TRIANGLE, 0).footprint(), Block(BlockKind.TRIANGLE, 2).footprint())

    def test_full_cells_compose_but_curves_do_not(self) -> None:
        two_squares = {(0, 0): FULL, (1, 0): FULL}
        self.assertEqual(len(solve(two_squares, [BlockKind.RECTANGLE])), 1)
        self.assertEqual(len(solve(two_squares, [BlockKind.SQUARE])), 2)
        dome = dict(Placement(Block(BlockKind.HALF_CIRCLE), 0, 0).fills)
        self.assertIsNone(solve(dome, [BlockKind.SQUARE, BlockKind.RECTANGLE, BlockKind.ARCH]))
        self.assertIsNotNone(solve(dome, [BlockKind.HALF_CIRCLE]))

    def test_build_plans_validate(self) -> None:
        with self.assertRaises(ValueError):
            BuildPlan("overlap", (place(BlockKind.SQUARE, 0, 0, 0), place(BlockKind.RECTANGLE, 0, 0, 0)))
        with self.assertRaises(ValueError):
            BuildPlan("apart", (place(BlockKind.SQUARE, 0, 0, 0), place(BlockKind.SQUARE, 0, 2, 0)))
        with self.assertRaises(ValueError):
            BuildPlan("wide", tuple(place(BlockKind.SQUARE, 0, col, 0) for col in range(5)))


class CatalogueTests(unittest.TestCase):
    def test_every_build_is_solvable_with_its_own_kinds(self) -> None:
        self.assertGreaterEqual(len(BUILDS), 15)
        for plan in BUILDS.values():
            with self.subTest(build=plan.build_id):
                self.assertIsNotNone(solve(plan.fills, plan.kinds))
                for kind in distractor_kinds(plan):
                    self.assertIsNone(solve(plan.fills, [kind]))

    def test_every_rung_keeps_its_promises(self) -> None:
        factory = TorreSetFactory(random.Random(11))
        for level in range(1, MAX_LEVEL + 1):
            rung = RUNGS[level]
            self.assertGreaterEqual(len(rung.pool), BUILDS_PER_SET, level)
            for _ in range(12):
                puzzles = factory.build_set(level)
                self.assertEqual(len(puzzles), BUILDS_PER_SET)
                counts = [p.plan.block_count for p in puzzles]
                self.assertEqual(counts, sorted(counts), "easiest build first")
                for puzzle in puzzles:
                    with self.subTest(level=level, build=puzzle.plan.build_id):
                        self.assertLessEqual(len(puzzle.kit), MAX_KIT)
                        self.assertIs(puzzle.style, OutlineStyle.SLOTS if level <= 3 else OutlineStyle.SILHOUETTE)
                        used = {item.block.kind: {i.block.rotation for i in puzzle.plan.placements if i.block.kind is item.block.kind} for item in puzzle.plan.placements}
                        if level == 1:
                            self.assertEqual(puzzle.distractors, ())
                            for block in puzzle.kit:
                                self.assertIn(block.rotation, used[block.kind], "rung 1 kit is already turned right")
                        if level == 2:
                            self.assertEqual(puzzle.distractors, ())
                        if level >= 2:
                            needs_turn = any(
                                block.rotation not in used[block.kind] or len(used[block.kind]) > 1
                                for block in puzzle.kit
                                if block.kind in used
                            )
                            self.assertTrue(needs_turn, "from rung 2 something must be turned")
                        if level in (3, 4):
                            self.assertEqual(len(puzzle.distractors), 1)
                        if level == 5:
                            self.assertGreaterEqual(len(puzzle.distractors), 1)

    def test_same_seed_same_set_and_replays_vary(self) -> None:
        first = TorreSetFactory(random.Random(4)).build_set(3)
        second = TorreSetFactory(random.Random(4)).build_set(3)
        self.assertEqual(first, second)
        factory = TorreSetFactory(random.Random(9))
        a = {p.plan.build_id for p in factory.build_set(1)}
        b = {p.plan.build_id for p in factory.build_set(1)}
        self.assertNotEqual(a, b, "a replay offers at least one different build")


def _puzzle(build: str, style: OutlineStyle, kit: tuple[Block, ...]) -> Puzzle:
    return Puzzle(BUILDS[build], style, kit)


def _session(puzzle: Puzzle, level: int = 1) -> TorreSession:
    return TorreSession((puzzle,) * BUILDS_PER_SET, level=level)


class SessionTests(unittest.TestCase):
    def test_slots_accept_only_their_own_block(self) -> None:
        kit = (Block(BlockKind.HALF_CIRCLE), Block(BlockKind.RECTANGLE, 0), Block(BlockKind.ARCH))
        session = _session(_puzzle("rocket", OutlineStyle.SLOTS, kit))
        # The rectangle lies flat but the rocket's slots stand up: turn it.
        result = session.try_place(1, (0.5, 2.0))
        self.assertIs(result.outcome, PlaceOutcome.NEEDS_TURN)
        self.assertEqual(session.misses, 1)
        self.assertTrue(session.turn(1))
        result = session.try_place(1, (0.5, 2.0))
        self.assertTrue(result.correct)
        self.assertEqual(result.placement, place(BlockKind.RECTANGLE, 1, 0, 1))
        # The arch belongs at the bottom, not on top.
        self.assertIs(session.try_place(2, (1.0, 0.5)).outcome, PlaceOutcome.WRONG_SPOT)
        self.assertTrue(session.try_place(2, (1.0, 3.5)).correct)

    def test_distractor_never_fits(self) -> None:
        kit = (Block(BlockKind.HALF_CIRCLE), Block(BlockKind.RECTANGLE, 1), Block(BlockKind.ARCH), Block(BlockKind.CYLINDER))
        session = _session(_puzzle("rocket", OutlineStyle.SILHOUETTE, kit), level=4)
        self.assertEqual(session.current_puzzle.distractors, (BlockKind.CYLINDER,))
        self.assertIs(session.try_place(3, (0.5, 1.5)).outcome, PlaceOutcome.NO_FIT)

    def test_silhouette_accepts_other_decompositions_but_never_a_dead_end(self) -> None:
        kit = (Block(BlockKind.TRIANGLE), Block(BlockKind.SQUARE), Block(BlockKind.RECTANGLE, 0), Block(BlockKind.ARCH))
        session = _session(_puzzle("castle", OutlineStyle.SILHOUETTE, kit), level=5)
        # Two squares stand where the plan has one rectangle: fine in a silhouette.
        self.assertTrue(session.try_place(1, (1.5, 1.5)).correct)
        self.assertTrue(session.try_place(1, (2.5, 1.5)).correct)
        session2 = _session(_puzzle("cat", OutlineStyle.SILHOUETTE, (Block(BlockKind.TRIANGLE), Block(BlockKind.RECTANGLE, 0), Block(BlockKind.ARCH))), level=4)
        # A lying rectangle across the head and the tail would strand single
        # cells no kit block can fill: refused although the cells match.
        self.assertFalse(session2.fits(place(BlockKind.RECTANGLE, 0, 1, 1)))
        self.assertTrue(session2.fits(place(BlockKind.RECTANGLE, 0, 0, 1)))

    def test_slots_refuse_straddling_blocks(self) -> None:
        kit = (Block(BlockKind.TRIANGLE), Block(BlockKind.SQUARE), Block(BlockKind.RECTANGLE, 0), Block(BlockKind.ARCH))
        session = _session(_puzzle("castle", OutlineStyle.SLOTS, kit), level=3)
        self.assertFalse(session.fits(place(BlockKind.SQUARE, 0, 1, 1)), "a slot wants its own block")
        self.assertTrue(session.fits(place(BlockKind.RECTANGLE, 0, 1, 1)))

    def test_snap_reach_is_local(self) -> None:
        session = _session(_puzzle("lighthouse", OutlineStyle.SLOTS, (Block(BlockKind.TRIANGLE), Block(BlockKind.RECTANGLE, 1), Block(BlockKind.SQUARE))))
        block = Block(BlockKind.SQUARE)
        self.assertEqual(session.best_fit(block, (0.6, 3.4)), place(BlockKind.SQUARE, 0, 0, 3))
        self.assertIsNone(session.best_fit(block, (0.5, 1.5)), "never snaps across the build")

    def test_finishing_builds_records_facts_and_advances(self) -> None:
        session = TorreSession(TorreSetFactory(random.Random(2)).build_set(2), level=2)
        for index in range(BUILDS_PER_SET):
            while not session.puzzle_done:
                step = session.next_step()
                while session.kit_block(step.kit_index) != step.placement.block:
                    session.turn(step.kit_index)
                result = session.try_place(step.kit_index, step.placement.center)
                self.assertTrue(result.correct)
            self.assertTrue(result.puzzle_completed)
            milestone = session.consume_milestone()
            self.assertEqual(milestone["build_index"], index + 1)
            self.assertIsNone(session.consume_milestone())
            if index < BUILDS_PER_SET - 1:
                self.assertTrue(session.next_puzzle())
        self.assertTrue(result.session_complete)
        self.assertEqual(session.consume_completion(), {"level": 2, "builds": 5, "first_attempt_count": 5, "retries": 0})
        self.assertIsNone(session.consume_completion())

    def test_next_step_starts_at_the_bench(self) -> None:
        session = _session(_puzzle("lighthouse", OutlineStyle.SLOTS, (Block(BlockKind.TRIANGLE), Block(BlockKind.RECTANGLE, 1), Block(BlockKind.SQUARE))))
        self.assertEqual(session.next_step().placement, place(BlockKind.SQUARE, 0, 0, 3))


class AdaptationTests(unittest.TestCase):
    def test_adaptation_across_levels(self) -> None:
        strong = [AttemptSummary(True, 0, False)] * BUILDS_PER_SET
        weak = [AttemptSummary(False, 3, True)] * 3
        self.assertEqual(adapt_level(1, strong), 2)
        self.assertEqual(adapt_level(MAX_LEVEL, strong), MAX_LEVEL)
        self.assertEqual(adapt_level(3, weak), 2)
        self.assertEqual(adapt_level(1, weak), 1)
        self.assertEqual(adapt_level(3, [AttemptSummary(True, 0, False)] * 2), 3)
        with self.assertRaises(ValueError):
            adapt_level(0, [])


# -- services ------------------------------------------------------------------------


class _Storage:
    def __init__(self, data=None) -> None:
        self.data = dict(data or {})

    def kv_get(self, key):
        return self.data.get(key)

    def kv_set(self, key, value) -> None:
        json.dumps(value)
        self.data[key] = value


class ProgressTests(unittest.TestCase):
    def test_saves_from_the_falling_block_game_migrate_and_keep_stars(self) -> None:
        storage = _Storage({STORAGE_KEY: {"stars": 7}})
        progress = GreiaTorreProgress(storage)
        loaded = progress.load()
        self.assertEqual(loaded, TorreProgress(level=1, history=(), builds=0, stars=7))
        progress.save(TorreProgress(2, (AttemptSummary(True, 0, False),), 3, loaded.stars + 3))
        self.assertEqual(storage.data[STORAGE_KEY]["schema_version"], SCHEMA_VERSION)
        self.assertEqual(storage.data[STORAGE_KEY]["stars"], 10)
        self.assertEqual(progress.load().level, 2)

    def test_malformed_storage_recovers_and_save_is_bounded(self) -> None:
        for raw in (None, [], "x", {"schema_version": 2, "level": 99, "history": "no"}, {"stars": -4}):
            self.assertEqual(parse_progress(raw).level, 1)
            self.assertGreaterEqual(parse_progress(raw).stars, 0)
        storage = _Storage()
        GreiaTorreProgress(storage).save(TorreProgress(3, tuple([AttemptSummary(False, 2, True)] * 40), 5, 5))
        self.assertEqual(len(storage.data[STORAGE_KEY]["history"]), HISTORY_LIMIT)

    def test_storage_failures_are_soft(self) -> None:
        class Broken:
            def kv_get(self, key):
                raise OSError("disk")

            def kv_set(self, key, value):
                raise OSError("disk")

        progress = GreiaTorreProgress(Broken())
        self.assertEqual(progress.load(), TorreProgress())
        progress.save(TorreProgress())


# -- package ---------------------------------------------------------------------------


class PackageTests(unittest.TestCase):
    def test_manifest_claims_match_the_game(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        education = manifest["education"]
        self.assertEqual(manifest["activity"]["id"], "org.greia.torre-forme")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["presentation"]["categories"], ["play"])
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertEqual(set(education["categories"]), {"spatial", "geometry"})
        self.assertNotIn("early_math", education["categories"])
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (4, 7))
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, MAX_LEVEL))
        self.assertTrue(education["adaptive_difficulty"])
        self.assertEqual(
            education["events"],
            [
                {"id": "tower.build_completed", "kind": "milestone"},
                {"id": "tower.set_completed", "kind": "completion"},
            ],
        )
        source = "".join(path.read_text(encoding="utf-8") for path in ACTIVITY_ROOT.glob("*.py"))
        self.assertNotIn("line_clear", source)
        self.assertNotIn("Lilli", source, "the builder is canonical Dani")

    def test_locales_have_key_parity_and_the_child_strings(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in LOCALES
        }
        keys = set(bundles["en"]["strings"])
        for locale, bundle in bundles.items():
            self.assertEqual(set(bundle["strings"]), keys, locale)
            self.assertTrue(all(value.strip() for value in bundle["strings"].values()))
        for key in ("victory.title", "victory.subtitle", "button.play_again", "activity.torre_forme.title"):
            self.assertIn(key, keys)

    def test_art_uses_the_shared_library_and_builds_bounded_surfaces(self) -> None:
        pygame.init()
        art = TorreArt()
        for kind in BlockKind:
            self.assertIn(kind, BLOCK_VARIANT)
            standing = Block.of(kind, 1)
            image = art.block(standing, 72)
            width, height = standing.size
            self.assertEqual(image.get_size(), (width * 72, height * 72), kind)
            self.assertIs(art.block(standing, 72), image, "scaled once per content")
        self.assertEqual(art.scene(4).get_size(), (1024, 600))
        for count in range(1, MAX_KIT + 1):
            art.scene(count)
        self.assertLessEqual(len(art._scenes), 3)
        for plan in BUILDS.values():
            for style in OutlineStyle:
                art.outline(plan, style)
        self.assertLessEqual(len(art._outlines), 4)
        self.assertIsNotNone(art.card("prop.vocab.rocket"))
        self.assertIsNone(art.card(None))
        self.assertTrue(art.fx_frames("sparkle"))
        self.assertIsNotNone(art.dani("pose_point", 120))
        self.assertEqual(art.turn_badge(40).get_size(), (40, 40))
        icon = pygame.image.load(str(ACTIVITY_ROOT / "assets" / "icon.png"))
        self.assertEqual(icon.get_size()[0], icon.get_size()[1])

    def test_layout_keeps_play_out_of_the_protected_chrome(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            screen = pygame.display.set_mode(size)
            canvas = PygameReferenceCanvas(screen)
            protected = ControlLayout.for_canvas(canvas, size).protected
            self.assertFalse(BOARD_RECT.colliderect(protected), size)
            self.assertFalse(DANI_TAP_RECT.colliderect(protected), size)
            self.assertFalse(CARD_RECT.colliderect(LISTEN_RECT))
            for count in range(1, MAX_KIT + 1):
                for rect in tray_rects(count):
                    self.assertTrue(tray_panel(count).contains(rect))
                    self.assertFalse(rect.colliderect(protected))
                self.assertLessEqual(turn_rect(count).right, 1024)
                self.assertLessEqual(tray_panel(count).bottom, 600)
        for plan in BUILDS.values():
            frame = BoardFrame(plan)
            self.assertEqual(frame.rect.bottom, BENCH_TOP)
            self.assertTrue(BOARD_RECT.contains(frame.rect), plan.build_id)

    def test_audio_resolves_only_approved_recordings(self) -> None:
        for locale in ("en", "it"):
            audio = TorreAudio(locale=locale)
            with self.subTest(locale=locale):
                self.assertEqual(set(SHARED_CUES), set(audio.cues))
                for cue in SHARED_CUES:
                    self.assertIn(f"/dani/{locale}/", str(audio._paths[cue]))

    def test_modules_import_in_script_context(self) -> None:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT / "src"))
        code = "import sys; sys.path.insert(0, sys.argv[1]); import main, torre_app; print(main.main.__name__)"
        result = subprocess.run(
            [sys.executable, "-c", code, str(ACTIVITY_ROOT)], capture_output=True, text=True, env=env, timeout=60
        )
        self.assertEqual(result.returncode, 0, result.stderr)


# -- app loop ----------------------------------------------------------------------------


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class MemoryProgress:
    def __init__(self, level: int = 1, builds: int = 3) -> None:
        self.saved = TorreProgress(level=level, builds=builds)
        self.saves = 0

    def load(self) -> TorreProgress:
        return self.saved

    def save(self, progress: TorreProgress) -> None:
        self.saved = progress
        self.saves += 1


class RecordedEvents:
    def __init__(self) -> None:
        self.milestones: list[dict[str, int]] = []
        self.completions: list[dict[str, int]] = []

    def build_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.milestones.append(payload)

    def set_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.completions.append(payload)


class AppLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((1024, 600))
        self.clock = FakeClock()
        self.events = RecordedEvents()

    def make(self, *, level: int = 1, locale: str = "en", seed: int = 5, builds: int = 3) -> TorreActivity:
        self.progress = MemoryProgress(level, builds)
        resources = activity_resources(ACTIVITY_ROOT, requested_locale=locale)
        app = TorreActivity(
            screen=self.screen,
            canvas=PygameReferenceCanvas(self.screen),
            typography=GreiaTypography(),
            resources=resources,
            audio=TorreAudio(locale=locale),
            progress=self.progress,
            events=self.events,
            rng=random.Random(seed),
            clock=self.clock,
        )
        self.advance(app, 1.0)
        self.assertIs(app.state, AppState.PLAYING)
        return app

    def advance(self, app: TorreActivity, seconds: float, dt: float = 0.05) -> None:
        elapsed = 0.0
        while elapsed < seconds:
            self.clock.now += dt
            elapsed += dt
            app.step()
            app.render()

    def mouse(self, app: TorreActivity, kind: int, pos: tuple[int, int]) -> None:
        app.handle_event(pygame.event.Event(kind, {"button": 1, "pos": pos}))

    def turn_to(self, app: TorreActivity, index: int, block: Block) -> None:
        while app.session.kit_block(index) != block:
            app.tap(app._tray_rects[index].center)  # tapping the block in hand turns it

    def place_step(self, app: TorreActivity) -> None:
        step = app.session.next_step()
        app.tap(app._tray_rects[step.kit_index].center)
        self.turn_to(app, step.kit_index, step.placement.block)
        app.tap(app.board_point(step.placement))

    def test_tap_block_then_tap_build_places_it(self) -> None:
        app = self.make()
        step = app.session.next_step()
        center = app._tray_rects[step.kit_index].center
        self.mouse(app, pygame.MOUSEBUTTONDOWN, center)
        self.mouse(app, pygame.MOUSEBUTTONUP, (center[0] + DRAG_THRESHOLD_PX - 4, center[1]))
        self.assertEqual(app.held, step.kit_index, "a short press is a tap: the block stays in hand")
        self.turn_to(app, step.kit_index, step.placement.block)
        app.tap(app.board_point(step.placement))
        self.assertIsNone(app.held)
        self.assertIn(step.placement, app.session.placed)
        self.assertEqual(app.cast.pose.value, "cheer")
        self.assertIn(step.placement, app.motion.drops)

    def test_dragging_over_the_build_glows_where_it_fits_and_drops_there(self) -> None:
        app = self.make()
        step = app.session.next_step()
        start = app._tray_rects[step.kit_index].center
        target = app.board_point(step.placement)
        from greia_platform.activity_controls import KitPointer, PointerPhase

        app._dispatch(KitPointer(PointerPhase.DOWN, start))
        app._dispatch(KitPointer(PointerPhase.MOVE, (start[0], start[1] - 60)))
        app._dispatch(KitPointer(PointerPhase.MOVE, target))
        self.assertEqual(app.preview, step.placement, "the outline glows where the block fits")
        app._dispatch(KitPointer(PointerPhase.UP, target))
        self.assertIn(step.placement, app.session.placed)
        # A drop far from the build puts the block back.
        step = app.session.next_step()
        app.drag(app._tray_rects[step.kit_index].center, (980, 330))
        self.assertIsNone(app.held)
        self.assertNotIn(step.placement, app.session.placed)

    def test_turn_button_and_keys_turn_the_block_in_hand(self) -> None:
        app = self.make(level=2)
        index = next(i for i, block in enumerate(app.session.kit) if block.rotates)
        self.assertFalse(app.controls.turn.enabled, "nothing in hand: nothing to turn")
        app.tap(app._tray_rects[index].center)
        self.assertTrue(app.controls.turn.enabled)
        before = app.session.kit_block(index)
        app.tap(app.controls.turn.rect.center)
        self.assertEqual(app.session.kit_block(index), before.turned())
        app.press(pygame.K_r)
        self.assertEqual(app.session.kit_block(index), before.turned().turned())
        from greia_platform.pygame_input import CONTROLLER_BUTTON_X

        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=CONTROLLER_BUTTON_X))
        self.assertEqual(app.session.kit_block(index), before.turned().turned().turned())

    def test_wrong_tries_think_then_explain_then_demonstrate(self) -> None:
        app = self.make(level=2, seed=8)
        step = app.session.next_step()
        wrong_spot = next(
            p for p in app.session.current_puzzle.plan.placements if p.block.kind is not step.placement.block.kind
        )
        app.tap(app._tray_rects[step.kit_index].center)
        self.turn_to(app, step.kit_index, step.placement.block)
        app.tap(app.board_point(wrong_spot))
        self.assertEqual(app.cast.pose.value, "think")
        self.assertIsNotNone(app.motion.wobble)
        self.assertEqual(app.held, step.kit_index, "the block stays in hand to try again")
        self.assertIsNone(app.motion.glide, "the first miss never plays the answer")
        self.advance(app, 0.7)
        self.assertIsNotNone(app.motion.target_glow, "it shows where this block goes")
        self.advance(app, 0.5)
        app.tap(app.board_point(wrong_spot))
        self.advance(app, 0.7)
        self.assertIsNotNone(app.motion.glide, "from the second miss Dani demonstrates")
        self.assertTrue(app.cast.pointing)
        self.assertNotIn(step.placement, app.session.placed, "Dani shows; the child still places it")
        self.assertEqual(app.session.misses, 2)

    def test_keyboard_and_controller_play(self) -> None:
        from greia_platform.pygame_input import CONTROLLER_BUTTON_A

        app = self.make(level=1)
        step = app.session.next_step()
        app.press(pygame.K_LEFT)  # reveals the focus ring on the first kit block
        self.assertEqual(app.controls.layer.focused_id, "tile.0")
        for _ in range(step.kit_index):
            app.press(pygame.K_RIGHT)
        self.assertEqual(app.controls.layer.focused_id, f"tile.{step.kit_index}")
        app.press(pygame.K_SPACE)
        self.assertEqual(app.held, step.kit_index)
        self.assertIsNotNone(app.controls.focused_cell(), "focus moves on to the build")
        targets = set(step.placement.cells)
        for _ in range(16):
            cell = app.controls.focused_cell()
            if cell in targets:
                break
            goal = min(targets, key=lambda c: abs(c[0] - cell[0]) + abs(c[1] - cell[1]))
            if cell[1] != goal[1]:
                app.press(pygame.K_DOWN if goal[1] > cell[1] else pygame.K_UP)
            else:
                app.press(pygame.K_RIGHT if goal[0] > cell[0] else pygame.K_LEFT)
        self.assertIn(app.controls.focused_cell(), targets)
        self.assertEqual(app.preview, step.placement, "the focused spot glows where it fits")
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=CONTROLLER_BUTTON_A))
        self.assertIn(step.placement, app.session.placed)
        self.assertTrue(app.controls.layer.focused_id.startswith("tile."), "back to the kit for the next block")
        # Escape puts a block in hand back instead of leaving the Activity.
        app.press(pygame.K_SPACE)
        self.assertIsNotNone(app.held)
        app.press(pygame.K_ESCAPE)
        self.assertIsNone(app.held)
        self.assertTrue(app._running)

    def test_protected_chrome_and_focus_loss(self) -> None:
        app = self.make()
        protected = ActivitySystemChromeLayout.for_surface(1024, 600).protected_region
        inside = (int(protected.x) + 2, int(protected.y) + 2)
        self.mouse(app, pygame.MOUSEBUTTONDOWN, inside)
        self.mouse(app, pygame.MOUSEBUTTONUP, inside)
        self.assertTrue(app._running)
        app.tap(app._tray_rects[0].center)
        self.assertEqual(app.held, 0)
        app.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertIsNone(app.held)
        self.assertEqual(app.session.placed, ())

    def test_idle_hints_grow_without_giving_the_answer_first(self) -> None:
        app = self.make(level=2)
        step = app.session.next_step()
        self.assertIsNone(app.motion.glide)
        self.advance(app, 6.2)
        self.assertTrue(app.cast.pointing)
        self.assertEqual(app.motion.target_glow[0], step.placement)
        self.assertNotIn(step.kit_index, app.motion.tray_hops)
        self.advance(app, 12.2)  # back-off: 6 s, +12 s, +24 s
        self.assertEqual(app.session.hints, 2)
        self.advance(app, 24.2)
        self.assertIsNotNone(app.motion.glide)

    def test_first_visit_demonstrates_once(self) -> None:
        app = self.make(builds=0)
        self.advance(app, 1.5)
        self.assertIsNotNone(app.motion.glide)
        self.advance(app, 2.0)
        # Pulsing surfaces must keep per-pixel alpha (set_alpha(None) would
        # drop it and paint the transparent corners black on later frames).
        puzzle = app.session.current_puzzle
        surfaces = [app.art.outline(puzzle.plan, puzzle.style), app.art.slot_glow(), app.art.slot_glow(106)]
        for placement in puzzle.plan.placements:
            surfaces += [app.art.ghost(placement.block, 72), app.art.glow(placement.block, 72)]
        for surface in surfaces:
            self.assertTrue(surface.get_flags() & pygame.SRCALPHA)

    def test_listen_button_and_dani_replay_the_goal(self) -> None:
        app = self.make()
        app.audio.last_speech = None
        app.tap(app.controls.listen.rect.center)
        self.assertIsNotNone(app.audio.last_speech)
        self.assertTrue(app.cast.pointing)
        app.audio.last_speech = None
        app.tap(DANI_TAP_RECT.center)
        self.assertIsNotNone(app.audio.last_speech)

    def test_full_set_reaches_the_completion_scene_then_builds_again(self) -> None:
        app = self.make(level=1, locale="it")
        for index in range(BUILDS_PER_SET):
            while app.state is AppState.PLAYING and not app.session.puzzle_done:
                self.place_step(app)
            self.assertIs(app.state, AppState.CELEBRATE)
            self.assertEqual(app.controls.progress.current, index + 1)
            self.advance(app, 3.6)
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertIsNotNone(app.completion)
        self.assertEqual(len(self.events.milestones), BUILDS_PER_SET)
        self.assertEqual(self.events.completions, [{"level": 1, "builds": 5, "first_attempt_count": 5, "retries": 0}])
        self.assertEqual(self.progress.saved.level, 2, "five clean builds climb one rung")
        self.assertEqual(self.progress.saved.builds, 3 + BUILDS_PER_SET)
        # "Build again": the replay button of the shared scene starts a new set.
        app.tap(app.completion.primary_rect.center)
        self.assertIsNone(app.completion)
        self.advance(app, 1.0)
        self.assertIs(app.state, AppState.PLAYING)
        self.assertEqual(app.session.finished_count, 0)
        self.assertEqual(app.session.level, 2)

    def test_renders_every_rung_at_supported_sizes(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            self.screen = pygame.display.set_mode(size)
            for level in range(1, MAX_LEVEL + 1):
                app = self.make(level=level)
                app.tap(app._tray_rects[0].center)
                self.advance(app, 0.2)
                app.canvas.present()
                self.assertEqual(app.screen.get_size(), size)


class SimulatorSupervisorTests(unittest.TestCase):
    def test_simulator_supervises_torre_forme(self) -> None:
        from simulator_supervision import supervise_builtin_activity

        supervise_builtin_activity(self, "org.greia.torre-forme")


if __name__ == "__main__":
    unittest.main()

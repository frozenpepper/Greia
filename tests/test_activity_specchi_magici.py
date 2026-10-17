"""Specchi Magici (Magic Mirrors): geometry, mosaics, rules, art, services, app loop.

Runs headlessly (SDL dummy drivers) against the real shared art catalogue,
with an injected clock, in-memory progress and recorded events, so no child
profile data, voices or windows are touched.
"""

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

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT, ROOT / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import pygame

import hermetic_volume
from activities.specchi_magici.mirror_app import DRAG_THRESHOLD_PX, AppState, MirrorActivity
from activities.specchi_magici.mirror_art import COLOUR_TOKENS, MirrorArt
from activities.specchi_magici.mirror_audio import PACKAGE_CUES, MirrorAudio
from activities.specchi_magici.mirror_layout import (
    FRAME_RECT,
    LILLI_TAP_RECT,
    cell_at,
    cell_rect,
    tray_panel,
    tray_rects,
)
from activities.specchi_magici.mirror_model import (
    CHALLENGE_COUNT,
    GRID_COLS,
    GRID_ROWS,
    HISTORY_LIMIT,
    LEVELS,
    MAX_LEVEL,
    MAX_TRAY,
    ORIENTED,
    AttemptSummary,
    CellPlacement,
    MirrorAxis,
    MirrorRoundFactory,
    MirrorSession,
    MosaicPuzzle,
    Piece,
    PlaceOutcome,
    ShapeKind,
    adapt_level,
    mirror_col,
    mirror_row,
    reflect_horizontal,
    reflect_vertical,
    reflections,
)
from activities.specchi_magici.mirror_services import STORAGE_KEY, GreiaMirrorProgress, MirrorProgress
from greia_platform.activity_controls import ControlLayout
from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import GreiaTypography

ACTIVITY_ROOT = ROOT / "activities" / "specchi_magici"
LOCALES = ("en", "it", "es", "fr")


def setUpModule() -> None:
    # The Simulator supervision test exercises real history/storage services,
    # whose production capacity policy depends on how full the host disk is.
    hermetic_volume.install_for_module()


# -- geometry ------------------------------------------------------------------------


class SymmetryTests(unittest.TestCase):
    def test_mirror_indices_are_exact_involutions(self) -> None:
        for col in range(GRID_COLS):
            self.assertEqual(mirror_col(mirror_col(col)), col)
        self.assertEqual(mirror_col(2), 3)
        for row in range(GRID_ROWS):
            self.assertEqual(mirror_row(mirror_row(row)), row)
        self.assertEqual(mirror_row(1), 2)
        with self.assertRaises(ValueError):
            mirror_col(GRID_COLS)

    def test_reflections_turn_only_what_a_mirror_turns(self) -> None:
        for kind in (ShapeKind.CIRCLE, ShapeKind.SQUARE, ShapeKind.RHOMBUS):
            piece = Piece(kind, 1)
            self.assertEqual(reflect_vertical(piece), piece)
            self.assertEqual(reflect_horizontal(piece), piece)
        right = Piece(ShapeKind.TRIANGLE, 0, 1)
        self.assertEqual(reflect_vertical(right), Piece(ShapeKind.TRIANGLE, 0, 3))
        self.assertEqual(reflect_horizontal(right), right)
        up = Piece(ShapeKind.SEMICIRCLE, 2, 0)
        self.assertEqual(reflect_vertical(up), up)
        self.assertEqual(reflect_horizontal(up), Piece(ShapeKind.SEMICIRCLE, 2, 2))
        heart = Piece(ShapeKind.HEART, 4, 0)
        self.assertEqual(reflect_vertical(heart), heart, "a heart is its own mirror image")
        self.assertEqual(reflect_horizontal(heart), Piece(ShapeKind.HEART, 4, 2), "water turns it over")
        for piece in (right, up, heart, Piece(ShapeKind.TRIANGLE, 5, 2)):
            self.assertEqual(reflect_vertical(reflect_vertical(piece)), piece)
            self.assertEqual(reflect_horizontal(reflect_horizontal(piece)), piece)

    def test_piece_validation(self) -> None:
        with self.assertRaises(ValueError):
            Piece(ShapeKind.SQUARE, 0, 1)
        with self.assertRaises(ValueError):
            Piece(ShapeKind.HEART, 0, 1)
        with self.assertRaises(ValueError):
            Piece(ShapeKind.CIRCLE, 6)

    def test_both_mirrors_give_three_images(self) -> None:
        source = CellPlacement(0, 1, Piece(ShapeKind.TRIANGLE, 3, 1))
        images = reflections(source, MirrorAxis.BOTH)
        self.assertEqual({image.cell for image in images}, {(0, 4), (3, 1), (3, 4)})
        self.assertEqual(
            [image.piece.rotation for image in images], [3, 1, 3]
        )

    def test_puzzle_validation_rejects_a_tray_without_choice(self) -> None:
        given = CellPlacement(0, 2, Piece(ShapeKind.CIRCLE, 0))
        required = reflections(given, MirrorAxis.VERTICAL)
        with self.assertRaises(ValueError):
            MosaicPuzzle("p", MirrorAxis.VERTICAL, (given,), required, (given.piece,))
        with self.assertRaises(ValueError):
            MosaicPuzzle("p", MirrorAxis.VERTICAL, (given,), required, (Piece(ShapeKind.SQUARE, 0), Piece(ShapeKind.SQUARE, 1)))


# -- ladder ----------------------------------------------------------------------------


class MirrorRoundFactoryTests(unittest.TestCase):
    def test_same_seed_same_set(self) -> None:
        first = MirrorRoundFactory(random.Random(42)).build_set(3)
        second = MirrorRoundFactory(random.Random(42)).build_set(3)
        self.assertEqual(first, second)
        self.assertEqual(len(first), CHALLENGE_COUNT)
        self.assertEqual(len({p.puzzle_id for p in first}), CHALLENGE_COUNT)

    def test_every_rung_keeps_its_promises(self) -> None:
        for level, spec in LEVELS.items():
            for seed in range(60):
                for puzzle in MirrorRoundFactory(random.Random(seed)).build_set(level):
                    with self.subTest(level=level, seed=seed, puzzle=puzzle.puzzle_id):
                        self.assertIs(puzzle.axis, spec.axis)
                        self.assertEqual(
                            puzzle.required,
                            tuple(image for given in puzzle.givens for image in reflections(given, puzzle.axis)),
                        )
                        low, high = spec.sources
                        self.assertTrue(low <= len(puzzle.givens) <= high)
                        for given in puzzle.givens:
                            self.assertFalse(puzzle.target_side(given.cell))
                        for target in puzzle.required:
                            self.assertTrue(puzzle.target_side(target.cell))
                        needed = {r.piece for r in puzzle.required}
                        self.assertTrue(needed <= set(puzzle.tray))
                        self.assertGreater(len(puzzle.tray), len(needed), "the kit never offers only the answer")
                        self.assertLessEqual(len(puzzle.tray), min(MAX_TRAY, spec.tray_max))
                        if spec.oriented_min:
                            turned = [
                                g for g in puzzle.givens
                                if any(image.piece != g.piece for image in reflections(g, puzzle.axis))
                            ]
                            self.assertTrue(turned, "an oriented rung needs a tile the mirror turns")
                        if spec.offer_unreflected:
                            for given in puzzle.givens:
                                if given.piece.kind in ORIENTED and given.piece not in needed:
                                    self.assertIn(given.piece, puzzle.tray, "the unmirrored copy is a real choice")

    def test_rung_one_tiles_sit_by_the_mirror_in_their_own_rows(self) -> None:
        for seed in range(40):
            for puzzle in MirrorRoundFactory(random.Random(seed)).build_set(1):
                rows = [g.row for g in puzzle.givens]
                self.assertEqual(len(rows), len(set(rows)))
                self.assertTrue(all(g.col in (1, 2) for g in puzzle.givens))
                self.assertTrue(all(g.piece.rotation == 0 for g in puzzle.givens))

    def test_ladder_axes(self) -> None:
        self.assertEqual(
            [LEVELS[level].axis for level in range(1, MAX_LEVEL + 1)],
            [MirrorAxis.VERTICAL, MirrorAxis.VERTICAL, MirrorAxis.VERTICAL, MirrorAxis.HORIZONTAL, MirrorAxis.BOTH],
        )


# -- session ---------------------------------------------------------------------------


def _session(level: int = 2, seed: int = 9) -> MirrorSession:
    return MirrorSession(MirrorRoundFactory(random.Random(seed)).build_set(level), level=level)


def _wrong_piece_for(puzzle: MosaicPuzzle, target: CellPlacement) -> Piece:
    return next(piece for piece in puzzle.tray if piece != target.piece)


class MirrorSessionTests(unittest.TestCase):
    def test_correct_tile_stays_and_wrong_ones_do_not(self) -> None:
        session = _session()
        puzzle = session.current_puzzle
        target = puzzle.required[0]
        wrong = session.place(_wrong_piece_for(puzzle, target), target.cell)
        self.assertIs(wrong.outcome, PlaceOutcome.WRONG_PIECE)
        self.assertEqual(wrong.focus, target)
        self.assertNotIn(target.cell, session.placed)
        empty = next(
            (r, c) for r in range(GRID_ROWS) for c in range(GRID_COLS)
            if puzzle.target_side((r, c)) and puzzle.target_at((r, c)) is None
        )
        stray = session.place(target.piece, empty)
        self.assertIs(stray.outcome, PlaceOutcome.WRONG_CELL)
        self.assertIsNotNone(stray.focus)
        self.assertEqual(session.misses, 2)
        given = puzzle.givens[0]
        self.assertIs(session.place(given.piece, given.cell).outcome, PlaceOutcome.IGNORED, "the picture side is not for building")
        right = session.place(target.piece, target.cell)
        self.assertIs(right.outcome, PlaceOutcome.CORRECT)
        self.assertEqual(session.placed[target.cell], target.piece)
        self.assertIs(session.place(target.piece, target.cell).outcome, PlaceOutcome.IGNORED)

    def test_finishing_mosaics_records_facts_and_advances_on_request(self) -> None:
        session = _session(level=1)
        for index in range(CHALLENGE_COUNT):
            puzzle = session.current_puzzle
            result = None
            for target in puzzle.required:
                result = session.place(target.piece, target.cell)
            self.assertTrue(result.puzzle_completed)
            self.assertTrue(session.puzzle_done)
            self.assertEqual(session.consume_milestone(), {"level": 1, "puzzle_index": index + 1, "first_attempt": 1})
            self.assertIsNone(session.consume_milestone())
            self.assertEqual(result.session_complete, index == CHALLENGE_COUNT - 1)
            if index < CHALLENGE_COUNT - 1:
                self.assertIsNone(session.consume_completion())
                self.assertTrue(session.next_puzzle())
                self.assertEqual(session.placed, {})
        self.assertTrue(session.is_complete)
        payload = session.consume_completion()
        self.assertEqual(payload, {"level": 1, "first_attempt_count": CHALLENGE_COUNT, "retries": 0})
        self.assertIsNone(session.consume_completion())

    def test_next_unmatched_starts_at_the_mirror(self) -> None:
        session = _session(level=2, seed=4)
        puzzle = session.current_puzzle
        first = session.next_unmatched()
        distances = [min(abs(r.col - 2), abs(r.col - 3)) for r in puzzle.required]
        self.assertEqual(min(abs(first.col - 2), abs(first.col - 3)), min(distances))
        session.place(first.piece, first.cell)
        self.assertNotEqual(session.next_unmatched(), first)

    def test_retries_and_hints_are_recorded(self) -> None:
        session = _session(level=3)
        puzzle = session.current_puzzle
        target = puzzle.required[0]
        session.place(_wrong_piece_for(puzzle, target), target.cell)
        session.note_hint()
        for required in puzzle.required:
            session.place(required.piece, required.cell)
        summary = session.history[-1]
        self.assertFalse(summary.first_attempt_success)
        self.assertTrue(summary.used_retry)
        self.assertEqual(summary.hints_used, 2)


class AdaptationTests(unittest.TestCase):
    def test_adaptation_across_levels(self) -> None:
        strong = [AttemptSummary(True, 0, False) for _ in range(HISTORY_LIMIT)]
        self.assertEqual(adapt_level(1, strong), 2)
        self.assertEqual(adapt_level(MAX_LEVEL, strong), MAX_LEVEL)
        struggling = [AttemptSummary(False, 2, True) for _ in range(3)]
        self.assertEqual(adapt_level(4, struggling), 3)
        self.assertEqual(adapt_level(1, struggling), 1)
        self.assertEqual(adapt_level(3, strong[:5]), 3)


# -- services ------------------------------------------------------------------------


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
        repo.save(3, [AttemptSummary(True, 0, False) for _ in range(20)])
        self.assertEqual(storage.saved["level"], 3)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)

    def test_saves_from_the_previous_version_still_load(self) -> None:
        legacy = {
            "schema_version": 1,
            "level": 4,
            "history": [{"first_attempt_success": True, "hints_used": 0, "used_retry": False}] * 3,
        }
        self.assertEqual(STORAGE_KEY, "specchi_magici.progress.v1")
        loaded = GreiaMirrorProgress(_Storage(legacy)).load()
        self.assertEqual(loaded.level, 4)
        self.assertEqual(len(loaded.history), 3)

    def test_storage_failures_are_soft(self) -> None:
        class Broken:
            def kv_get(self, key):
                raise OSError("disk")

            def kv_set(self, key, value):
                raise OSError("disk")

        repo = GreiaMirrorProgress(Broken())
        self.assertEqual(repo.load(), MirrorProgress())
        repo.save(2, ())


# -- package -------------------------------------------------------------------------


class PackageTests(unittest.TestCase):
    def test_manifest_claims_match_the_game(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        education = manifest["education"]
        self.assertEqual(manifest["activity"]["id"], "org.greia.specchi-magici")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en", "es", "fr"])
        self.assertEqual(manifest["input"]["profile"], "hybrid")
        self.assertIn("symmetry", education["categories"])
        self.assertEqual((education["recommended_age_min"], education["recommended_age_max"]), (5, 7))
        self.assertEqual((education["difficulty_min"], education["difficulty_max"]), (1, MAX_LEVEL))
        self.assertTrue(education["adaptive_difficulty"])
        self.assertEqual(
            education["events"],
            [
                {"id": "mirror.mosaic_completed", "kind": "milestone"},
                {"id": "mirror.gallery_completed", "kind": "completion"},
            ],
        )

    def test_locales_have_key_parity_and_the_child_strings(self) -> None:
        bundles = {
            locale: json.loads((ACTIVITY_ROOT / "locales" / f"{locale}.json").read_text(encoding="utf-8"))
            for locale in LOCALES
        }
        keys = set(bundles["en"]["strings"])
        for locale, bundle in bundles.items():
            self.assertEqual(set(bundle["strings"]), keys, locale)
            self.assertTrue(all(value.strip() for value in bundle["strings"].values()))
        for key in ("victory.title", "victory.subtitle", "button.play_again", "activity.specchi_magici.title"):
            self.assertIn(key, keys)

    def test_mosaic_tiles_have_sources_and_runtime_renditions(self) -> None:
        pygame.init()
        names = {f"mosaic_tile_{kind.value}_{token}" for kind in ShapeKind for token in COLOUR_TOKENS}
        self.assertEqual(len(names), 36)
        sources = {p.stem for p in (ACTIVITY_ROOT / "assets" / "source").glob("mosaic_tile_*.svg")}
        self.assertEqual(sources, names)
        for name in sorted(names):
            image = pygame.image.load(str(ACTIVITY_ROOT / "assets" / "runtime" / f"{name}.png"))
            self.assertEqual(image.get_size(), (128, 128), name)
            svg = (ACTIVITY_ROOT / "assets" / "source" / f"{name}.svg").read_text(encoding="utf-8")
            for forbidden in ("<image", "<text", "<filter", "<mask", "<style", "<script", "data:"):
                self.assertNotIn(forbidden, svg, name)
        icon = pygame.image.load(str(ACTIVITY_ROOT / "assets" / "icon.png"))
        self.assertEqual(icon.get_size(), (256, 256))

    def test_art_builds_bounded_surfaces(self) -> None:
        pygame.init()
        art = MirrorArt()
        piece = Piece(ShapeKind.TRIANGLE, 2, 1)
        self.assertEqual(art.tile(piece, 62).get_size(), (62, 62))
        self.assertIs(art.tile(piece, 62), art.tile(piece, 62), "scaled once per content")
        self.assertEqual(art.ghost(piece, 62).get_size(), (62, 62))
        picture = frozenset((r, c) for r in range(GRID_ROWS) for c in range(3))
        self.assertEqual(art.scene(picture, MirrorAxis.VERTICAL, 4).get_size(), (1024, 600))
        for count in range(2, MAX_TRAY + 1):
            art.scene(picture, MirrorAxis.VERTICAL, count)
        self.assertLessEqual(len(art._scenes), 3)
        self.assertTrue(art.fx_frames("sparkle"))
        self.assertIsNotNone(art.lilli("pose_point", 120))

    def test_layout_keeps_play_out_of_the_protected_chrome(self) -> None:
        for size in ((1024, 600), (800, 480), (480, 320)):
            screen = pygame.display.set_mode(size)
            canvas = PygameReferenceCanvas(screen)
            protected = ControlLayout.for_canvas(canvas, size).protected
            self.assertFalse(FRAME_RECT.colliderect(protected), size)
            self.assertFalse(LILLI_TAP_RECT.colliderect(protected), size)
            for rect in tray_rects(MAX_TRAY):
                self.assertTrue(tray_panel(MAX_TRAY).contains(rect))
                self.assertFalse(rect.colliderect(protected))
                self.assertLessEqual(rect.bottom, 600)
        self.assertEqual(cell_at(cell_rect(2, 4).center), (2, 4))
        self.assertIsNone(cell_at((5, 5)))

    def test_audio_resolves_only_approved_recordings(self) -> None:
        for locale in ("en", "it"):
            resources = activity_resources(ACTIVITY_ROOT, requested_locale=locale)
            audio = MirrorAudio(locale=locale, resources=resources)
            with self.subTest(locale=locale):
                self.assertTrue(set(PACKAGE_CUES) <= audio.cues, sorted(set(PACKAGE_CUES) - audio.cues))
                self.assertIn("celebrate.success", audio.cues)
                for cue in PACKAGE_CUES:
                    self.assertTrue(str(audio._paths[cue]).endswith(f"{locale}/{cue}.wav"), audio._paths[cue])


# -- app loop ----------------------------------------------------------------------------


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class MemoryProgress:
    def __init__(self, level: int = 1) -> None:
        self.saved = MirrorProgress(level=level)
        self.saves = 0

    def load(self) -> MirrorProgress:
        return self.saved

    def save(self, level: int, history) -> None:
        self.saved = MirrorProgress(level, tuple(history))
        self.saves += 1


class RecordedEvents:
    def __init__(self) -> None:
        self.milestones: list[dict[str, int]] = []
        self.completions: list[dict[str, int]] = []

    def mosaic_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.milestones.append(payload)

    def gallery_completed(self, session_id: str, payload: dict[str, int]) -> None:
        self.completions.append(payload)


class AppLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((1024, 600))
        self.clock = FakeClock()
        self.events = RecordedEvents()

    def make(self, *, level: int = 1, locale: str = "en", seed: int = 5) -> MirrorActivity:
        self.progress = MemoryProgress(level)
        resources = activity_resources(ACTIVITY_ROOT, requested_locale=locale)
        app = MirrorActivity(
            screen=self.screen,
            canvas=PygameReferenceCanvas(self.screen),
            typography=GreiaTypography(),
            resources=resources,
            audio=MirrorAudio(locale=locale, resources=resources),
            progress=self.progress,
            events=self.events,
            rng=random.Random(seed),
            clock=self.clock,
        )
        self.advance(app, 1.0)
        self.assertIs(app.state, AppState.PLAYING)
        return app

    def advance(self, app: MirrorActivity, seconds: float, dt: float = 0.05) -> None:
        elapsed = 0.0
        while elapsed < seconds:
            self.clock.now += dt
            elapsed += dt
            app.step()
            app.render()

    def mouse(self, app: MirrorActivity, kind: int, pos: tuple[int, int]) -> None:
        app.handle_event(pygame.event.Event(kind, {"button": 1, "pos": pos}))

    def tray_index(self, app: MirrorActivity, piece: Piece) -> int:
        return app.session.current_puzzle.tray.index(piece)

    def place(self, app: MirrorActivity, target: CellPlacement) -> None:
        app.tap(app._tray_rects[self.tray_index(app, target.piece)].center)
        app.tap(cell_rect(*target.cell).center)

    def test_tap_tile_then_tap_cell_places_it(self) -> None:
        app = self.make()
        target = app.session.next_unmatched()
        tile = self.tray_index(app, target.piece)
        center = app._tray_rects[tile].center
        self.mouse(app, pygame.MOUSEBUTTONDOWN, center)
        self.mouse(app, pygame.MOUSEBUTTONUP, (center[0] + DRAG_THRESHOLD_PX - 4, center[1]))
        self.assertEqual(app.held, tile, "a short press is a tap: the tile stays in hand")
        app.tap(cell_rect(*target.cell).center)
        self.assertIsNone(app.held)
        self.assertEqual(app.session.placed[target.cell], target.piece)
        self.assertEqual(app.cast.pose.value, "cheer")
        self.assertIn(target.cell, app.motion.drops)

    def test_drag_places_and_a_drop_on_nothing_puts_back(self) -> None:
        app = self.make()
        target = app.session.next_unmatched()
        start = app._tray_rects[self.tray_index(app, target.piece)].center
        app.drag(start, (900, 300))
        self.assertIsNone(app.held)
        self.assertEqual(app.session.placed, {})
        app.drag(start, cell_rect(*target.cell).center)
        self.assertEqual(app.session.placed[target.cell], target.piece)

    def test_wrong_tile_wobbles_lilli_thinks_and_then_shows_the_way(self) -> None:
        app = self.make(level=2)
        puzzle = app.session.current_puzzle
        target = app.session.next_unmatched()
        wrong = _wrong_piece_for(puzzle, target)
        app.tap(app._tray_rects[self.tray_index(app, wrong)].center)
        app.tap(cell_rect(*target.cell).center)
        self.assertEqual(app.cast.pose.value, "think")
        self.assertIsNotNone(app.motion.wobble)
        self.assertNotIn(target.cell, app.session.placed)
        self.assertIsNone(app.motion.ghost, "the first miss never shows the answer")
        self.advance(app, 0.7)
        source = puzzle.source_of(target.cell)
        self.assertIn(source.cell, app.motion.source_glow, "the picture tile to mirror glows")
        self.assertIsNone(app.motion.ghost)
        self.advance(app, 0.5)
        app.tap(app._tray_rects[self.tray_index(app, wrong)].center)
        app.tap(cell_rect(*target.cell).center)
        self.advance(app, 0.7)
        self.assertIsNotNone(app.motion.ghost, "from the second miss Lilli demonstrates")
        self.assertEqual(app.motion.ghost[:2], (target.cell, target.piece))
        self.assertTrue(app.cast.pointing)
        self.assertNotIn(target.cell, app.session.placed, "she shows the spot; the child still places it")
        self.assertEqual(app.session.misses, 2)

    def test_keyboard_and_controller_play(self) -> None:
        from greia_platform.pygame_input import CONTROLLER_BUTTON_A

        app = self.make(level=2)
        target = app.session.next_unmatched()
        tile = self.tray_index(app, target.piece)
        app.press(pygame.K_LEFT)  # reveals the focus ring on the first tile
        self.assertEqual(app.controls.layer.focused_id, "tile.0")
        for _ in range(tile):
            app.press(pygame.K_RIGHT)
        self.assertEqual(app.controls.layer.focused_id, f"tile.{tile}")
        app.press(pygame.K_SPACE)
        self.assertEqual(app.held, tile)
        self.assertIsNotNone(app.controls.focused_cell(), "focus moves on to the glass")
        for _ in range(12):
            cell = app.controls.focused_cell()
            if cell == target.cell:
                break
            if cell[0] != target.cell[0]:
                app.press(pygame.K_DOWN if target.cell[0] > cell[0] else pygame.K_UP)
            else:
                app.press(pygame.K_RIGHT if target.cell[1] > cell[1] else pygame.K_LEFT)
        self.assertEqual(app.controls.focused_cell(), target.cell)
        app.handle_event(pygame.event.Event(pygame.CONTROLLERBUTTONDOWN, button=CONTROLLER_BUTTON_A))
        self.assertEqual(app.session.placed.get(target.cell), target.piece)
        self.assertTrue(app.controls.layer.focused_id.startswith("tile."), "back to the kit for the next tile")
        # Escape puts a tile in hand back instead of leaving the Activity.
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
        self.assertEqual(app.session.placed, {})

    def test_idle_hints_grow_without_giving_the_answer_first(self) -> None:
        app = self.make(level=2)
        target = app.session.next_unmatched()
        source = app.session.current_puzzle.source_of(target.cell)
        self.advance(app, 6.2)
        self.assertTrue(app.cast.pointing)
        self.assertIn(source.cell, app.motion.source_glow)
        self.assertNotIn(target.cell, app.motion.target_ring)
        self.advance(app, 12.2)  # back-off: 6 s, then a further 12 s
        self.assertIn(target.cell, app.motion.target_ring)
        self.assertEqual(app.session.hints, 2)

    def test_listen_button_and_lilli_replay_the_goal(self) -> None:
        app = self.make()
        app.audio.last_speech = None
        app.tap(app.controls.listen.rect.center)
        self.assertEqual(app.audio.last_speech, "prompt_place")
        app.audio.last_speech = None
        app.tap(LILLI_TAP_RECT.center)
        self.assertEqual(app.audio.last_speech, "prompt_place")

    def test_full_set_reaches_the_completion_scene_then_plays_again(self) -> None:
        app = self.make(level=1, locale="it")
        for index in range(CHALLENGE_COUNT):
            while app.session.next_unmatched() is not None and app.state is AppState.PLAYING:
                self.place(app, app.session.next_unmatched())
            self.assertIs(app.state, AppState.CELEBRATE)
            self.assertEqual(app.controls.progress.current, index + 1)
            self.advance(app, 3.0)
        self.assertIs(app.state, AppState.TERMINAL)
        self.assertIsNotNone(app.completion)
        self.assertEqual(len(self.events.milestones), CHALLENGE_COUNT)
        self.assertEqual(self.events.completions, [{"level": 1, "first_attempt_count": CHALLENGE_COUNT, "retries": 0}])
        self.assertEqual(self.progress.saved.level, 1)
        self.assertEqual(len(self.progress.saved.history), CHALLENGE_COUNT)
        # "Play again": the replay button of the shared scene starts a new set.
        app.tap(app.completion.primary_rect.center)
        self.assertIsNone(app.completion)
        self.advance(app, 1.0)
        self.assertIs(app.state, AppState.PLAYING)
        self.assertEqual(app.session.finished_count, 0)
        self.assertEqual(len(app.session.history), CHALLENGE_COUNT, "evidence carries over for adaptation")

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
    def test_simulator_supervises_specchi_magici(self) -> None:
        from simulator_supervision import supervise_builtin_activity

        supervise_builtin_activity(self, "org.greia.specchi-magici")


if __name__ == "__main__":
    unittest.main()

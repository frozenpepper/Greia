"""Installer start-up animation: shared timing, skip, once-per-boot, fail-soft."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from greia_installer.boot_intro import InstallerIntro, IntroOutcome  # noqa: E402
from greia_platform import boot_animation  # noqa: E402
from greia_platform.boot_animation import IntroPhase, IntroTimeline  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _Clock:
    """Fake monotonic clock that advances ``step`` seconds per reading."""

    def __init__(self, step: float) -> None:
        self.now = 100.0
        self.step = step

    def __call__(self) -> float:
        self.now += self.step
        return self.now


class _Chime:
    def __init__(self) -> None:
        self.calls: list[bool] = []

    def play(self, *, skip: bool = False) -> bool:
        self.calls.append(skip)
        return True


class IntroTimelineTests(unittest.TestCase):
    def test_frames_follow_elapsed_time_then_hold_the_exact_final_frame(self) -> None:
        timeline = IntroTimeline(total_frames=52)
        timeline.start(10.0)
        self.assertEqual(timeline.frame(10.0), 0)
        self.assertEqual(timeline.phase(12.5), IntroPhase.ANIMATING)
        self.assertEqual(timeline.frame(12.5), 26)
        self.assertEqual(timeline.phase(15.0), IntroPhase.HOLDING)
        self.assertEqual(timeline.frame(15.0), 51)
        self.assertEqual(timeline.frame(16.9), 51)
        self.assertEqual(timeline.phase(17.0), IntroPhase.DONE)

    def test_skip_ends_immediately_and_empty_art_is_done(self) -> None:
        timeline = IntroTimeline(total_frames=52)
        timeline.start(0.0)
        timeline.skip()
        self.assertEqual(timeline.phase(0.1), IntroPhase.DONE)
        self.assertEqual(IntroTimeline(total_frames=0).phase(0.0), IntroPhase.DONE)

    def test_frame_index_matches_the_historic_launcher_formula(self) -> None:
        for elapsed in (0.0, 0.01, 1.3, 4.99, 5.0, 9.0):
            ratio = max(0.0, min(1.0, elapsed / 5.0))
            expected = min(51, int(ratio * 52))
            self.assertEqual(boot_animation.frame_index(elapsed, 52, 5.0), expected)

    def test_launcher_and_installer_share_the_same_product_timing(self) -> None:
        from greia_launcher import boot_intro as launcher_intro

        self.assertEqual(launcher_intro.ANIMATION_SECONDS, boot_animation.ANIMATION_SECONDS)
        self.assertEqual(
            launcher_intro.FINAL_FRAME_HOLD_SECONDS, boot_animation.FINAL_FRAME_HOLD_SECONDS
        )
        self.assertEqual(launcher_intro._background_rgb(None), boot_animation.BACKGROUND_RGB)

    def test_repository_frames_are_discoverable(self) -> None:
        paths = boot_animation.frame_paths(boot_animation.candidate_frame_directories(PROJECT_ROOT))
        self.assertEqual(len(paths), 52)
        self.assertEqual(paths[-1].name, "frame_0051.png")


class InstallerIntroTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((320, 200))
        self.tmp = tempfile.TemporaryDirectory()
        self.marker = Path(self.tmp.name) / "intro-played"
        pygame.event.clear()

    def tearDown(self) -> None:
        self.tmp.cleanup()
        pygame.event.clear()

    def intro(self, frames: int, *, step: float = 0.25) -> tuple[InstallerIntro, _Chime]:
        chime = _Chime()

        def loader(pg, prepare):
            return [prepare(pg.Surface((22, 60))) for _ in range(frames)]

        intro = InstallerIntro(
            root=PROJECT_ROOT,
            marker=self.marker,
            chime=chime,  # type: ignore[arg-type]
            clock=_Clock(step),
            frames_loader=loader,
        )
        return intro, chime

    def test_plays_full_sequence_once_then_chimes_and_marks(self) -> None:
        intro, chime = self.intro(52)
        first = []
        with mock.patch.dict(os.environ, {"GREIA_SKIP_BOOT_INTRO": ""}):
            outcome = intro.run(self.screen, pygame, on_first_frame=lambda: first.append(1))
        self.assertEqual(outcome, IntroOutcome.PLAYED)
        self.assertEqual(first, [1])
        self.assertTrue(self.marker.exists())
        self.assertEqual(chime.calls, [False])
        # Once per boot: a restarted installer shows only the static frame.
        again, _ = self.intro(52)
        self.assertEqual(again.run(self.screen, pygame), IntroOutcome.ALREADY_PLAYED)

    def test_any_key_skips_and_the_skipping_input_is_consumed(self) -> None:
        intro, chime = self.intro(52, step=0.05)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode="a", scancode=4))
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(5, 5)))
        with mock.patch.dict(os.environ, {"GREIA_SKIP_BOOT_INTRO": ""}):
            outcome = intro.run(self.screen, pygame)
        self.assertEqual(outcome, IntroOutcome.SKIPPED)
        self.assertEqual(pygame.event.get(), [], "skip input must not reach the language screen")
        self.assertEqual(len(chime.calls), 1)

    def test_motion_and_release_do_not_skip(self) -> None:
        intro, _ = self.intro(4, step=0.5)
        pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(1, 1), rel=(1, 1), buttons=(0, 0, 0)))
        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_a, mod=0, scancode=4))
        with mock.patch.dict(os.environ, {"GREIA_SKIP_BOOT_INTRO": ""}):
            self.assertEqual(intro.run(self.screen, pygame), IntroOutcome.PLAYED)

    def test_missing_frames_fail_soft_but_still_release_the_cover(self) -> None:
        intro, chime = self.intro(0)
        first = []
        with mock.patch.dict(os.environ, {"GREIA_SKIP_BOOT_INTRO": ""}):
            outcome = intro.run(self.screen, pygame, on_first_frame=lambda: first.append(1))
        self.assertEqual(outcome, IntroOutcome.UNAVAILABLE)
        self.assertEqual(first, [1])
        self.assertEqual(chime.calls, [])

    def test_development_escape_hatch(self) -> None:
        intro, _ = self.intro(52)
        with mock.patch.dict(os.environ, {"GREIA_SKIP_BOOT_INTRO": "1"}):
            self.assertEqual(intro.run(self.screen, pygame), IntroOutcome.DISABLED)
        self.assertFalse(self.marker.exists())

    def test_language_screen_runs_the_intro_and_releases_the_cover_after_it(self) -> None:
        source = (PROJECT_ROOT / "src/greia_installer/entrypoint.py").read_text(encoding="utf-8")
        body = source[source.index("def choose_language("):]
        self.assertLess(body.index("InstallerIntro.for_root(root).run("), body.index("LanguageChooser(root=root)"))
        self.assertIn("on_first_frame=_first_frame", body)


class LanguageChooserTests(unittest.TestCase):
    def setUp(self) -> None:
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((800, 480))

    def test_release_without_press_never_chooses(self) -> None:
        from greia_installer.entrypoint import LanguageChooser

        chooser = LanguageChooser(root=PROJECT_ROOT)
        chooser.draw(self.screen, pygame, pointer_position=(-1, -1))
        targets = chooser.hit_targets()
        self.assertGreaterEqual(len([k for k in targets if k.startswith("language-")]), 2)
        start = chooser.selected_index
        other = next(k for k in targets if k.startswith("language-") and not k.endswith(str(start)))
        up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=targets[other].center)
        self.assertIsNone(chooser.handle_event(up, pygame))
        self.assertEqual(chooser.selected_index, start, "an orphan release must be ignored")
        down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=targets[other].center)
        chooser.handle_event(down, pygame)
        chooser.handle_event(up, pygame)
        self.assertEqual(chooser.selected_index, int(other.split("-")[1]))
        chooser.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=targets["continue"].center), pygame)
        chosen = chooser.handle_event(
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=targets["continue"].center), pygame
        )
        self.assertEqual(chosen, chooser.locale)

    def test_every_language_tile_fits_on_screen_at_both_reference_sizes(self) -> None:
        from greia_installer.entrypoint import LanguageChooser

        for size in ((1024, 600), (800, 480)):
            screen = pygame.Surface(size)
            chooser = LanguageChooser(root=PROJECT_ROOT)
            chooser.draw(screen, pygame, pointer_position=(-1, -1))
            bounds = screen.get_rect()
            rects = list(chooser.hit_targets().values())
            for index, rect in enumerate(rects):
                self.assertTrue(bounds.contains(rect), (size, rect))
                for other in rects[index + 1 :]:
                    self.assertFalse(rect.colliderect(other), (size, rect, other))


class LocalizedMeasurementTests(unittest.TestCase):
    def test_measurement_uses_the_translated_copy_and_fonts_are_memoised(self) -> None:
        from greia_installer.i18n import LocalizedTypography
        from greia_platform.typography import FontRole, GreiaTypography

        pygame.display.init()
        pygame.font.init()
        base = GreiaTypography(PROJECT_ROOT / "assets" / "fonts" / "nunito-sans")
        localized = LocalizedTypography(base, "it")
        font = localized.font(FontRole.CONTROL, 24)
        self.assertIs(font, localized.font(FontRole.CONTROL, 24), "text cache keys on font identity")
        source = "Hold to erase and install"
        italian = localized.translator.text(source)
        self.assertEqual(font.size(source), font.base.size(italian))
        self.assertGreater(font.size(source)[0], font.base.size(source)[0])


if __name__ == "__main__":
    unittest.main()

"""P5-PYGAME acceptance: display-only Pygame init before the first frame.

Proves the production mechanism, not just exit codes:
- both launcher ``run()`` paths initialize the display subsystem only in the
  pre-frame region between the ``pygame_display_init_begin/end`` markers
  (broad ``pygame.init()`` absent, no font/mixer/joystick init pre-frame);
- the intro requires no font subsystem (fonts render lazily where required
  through ``greia_platform.typography``, which owns ``pygame.font.init``);
- the mixer is opened lazily after the intro, immediately before the first
  spoken-label audio, and stays fail-soft when audio is unavailable;
- controller handles still open lazily at interactive readiness through the
  existing ``PygameControllerSet`` owner (no pre-frame joystick init);
- with display-only init, the handoff frame draws, flips and the display
  event system pumps (real pygame on the dummy SDL driver).
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]


def _init_region(source: str) -> str:
    begin = source.index('"pygame_display_init_begin"')
    end = source.index('"pygame_display_init_end"')
    assert begin < end
    return source[begin:end]


class DisplayOnlyPreFrameContractTests(unittest.TestCase):
    def test_run_paths_initialize_display_only_pre_frame(self) -> None:
        for name in ("src/greia_launcher/main.py", "src/greia_launcher/presentation.py"):
            with self.subTest(path=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                region = _init_region(source)
                self.assertIn("pygame.display.init()", region)
                for forbidden in (
                    "pygame.init(",
                    "font.init(",
                    "mixer.init(",
                    "joystick.",
                ):
                    self.assertNotIn(forbidden, region)

    def test_boot_markers_stay_intact(self) -> None:
        for name in ("src/greia_launcher/main.py", "src/greia_launcher/presentation.py"):
            with self.subTest(path=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                for marker in (
                    '"pygame_display_init_begin"',
                    '"pygame_display_init_end"',
                    '"display_set_mode_begin"',
                    '"display_set_mode_end"',
                ):
                    self.assertIn(marker, source)

    def test_intro_requires_no_font_subsystem(self) -> None:
        intro = (ROOT / "src/greia_launcher/boot_intro.py").read_text(encoding="utf-8")
        self.assertNotIn("font", intro.lower())

    def test_font_init_is_owned_lazily_by_typography(self) -> None:
        typography = (ROOT / "src/greia_platform/typography.py").read_text(encoding="utf-8")
        self.assertIn("pygame.font.init()", typography)

    def test_controller_open_stays_lazy_in_platform_owner(self) -> None:
        controller_set = (ROOT / "src/greia_platform/pygame_input.py").read_text(encoding="utf-8")
        self.assertIn("sdl_controller.init()", controller_set)
        main = (ROOT / "src/greia_launcher/main.py").read_text(encoding="utf-8")
        # Interactive readiness (controller start) happens strictly after the
        # display-ready handoff, never in the pre-frame init region.
        self.assertLess(
            main.index("mark_display_ready()"),
            main.index("self._shell_input.start()"),
        )


class _FakeMixer:
    """Strict fake: Sound/channel access before init() is a loud failure."""

    class error(Exception):
        pass

    def __init__(self, *, fail_init: bool = False) -> None:
        self._initialized = False
        self._fail_init = fail_init
        self.calls: list[str] = []

    def get_init(self) -> bool:
        return self._initialized

    def init(self) -> None:
        self.calls.append("init")
        if self._fail_init:
            raise _FakeMixer.error("no audio device")
        self._initialized = True

    def Sound(self, path: str) -> object:  # noqa: N802
        if not self._initialized:
            raise AssertionError("mixer Sound() before mixer init()")
        self.calls.append("Sound")
        return ("sound", path)

    def find_channel(self, force: bool = False) -> SimpleNamespace:
        if not self._initialized:
            raise AssertionError("mixer find_channel() before mixer init()")
        assert force is True
        channel = SimpleNamespace(played=[])
        channel.stop = lambda: None
        channel.play = channel.played.append
        return channel


class _FakePygame:
    error = _FakeMixer.error

    def __init__(self, mixer: _FakeMixer) -> None:
        self.mixer = mixer


class LazyMixerTests(unittest.TestCase):
    def _clip(self, tmp: Path) -> Path:
        clip = tmp / "label.wav"
        clip.write_bytes(b"clip")
        return clip

    def test_announce_opens_mixer_immediately_before_first_audio(self) -> None:
        import tempfile

        from greia_launcher.spoken_labels import SpokenLabelPlayer

        mixer = _FakeMixer()
        player = SpokenLabelPlayer()
        with tempfile.TemporaryDirectory() as tmp:
            clip = self._clip(Path(tmp))
            self.assertTrue(player.announce("activity:a", clip, _FakePygame(mixer)))
        # Init precedes first use and happens exactly once ...
        self.assertEqual(mixer.calls, ["init", "Sound"])
        # ... and is not repeated for later labels.
        with tempfile.TemporaryDirectory() as tmp:
            clip = self._clip(Path(tmp))
            self.assertTrue(player.announce("activity:b", clip, _FakePygame(mixer)))
        self.assertEqual(mixer.calls, ["init", "Sound", "Sound"])

    def test_announce_stays_fail_soft_when_mixer_unavailable(self) -> None:
        import tempfile

        from greia_launcher.spoken_labels import SpokenLabelPlayer

        mixer = _FakeMixer(fail_init=True)
        player = SpokenLabelPlayer()
        with tempfile.TemporaryDirectory() as tmp:
            clip = self._clip(Path(tmp))
            self.assertFalse(player.announce("activity:a", clip, _FakePygame(mixer)))
        self.assertEqual(mixer.calls, ["init"])

    def test_announce_stays_fail_soft_without_mixer_init_api(self) -> None:
        import tempfile

        from greia_launcher.spoken_labels import SpokenLabelPlayer

        class _NoInitMixer:
            def get_init(self) -> bool:
                return False

        player = SpokenLabelPlayer()
        with tempfile.TemporaryDirectory() as tmp:
            clip = self._clip(Path(tmp))
            fake = SimpleNamespace(mixer=_NoInitMixer(), error=Exception)
            self.assertFalse(player.announce("activity:a", clip, fake))


class DisplayOnlyRuntimeTests(unittest.TestCase):
    """Real pygame on the dummy driver: display-only init serves first frame."""

    def test_handoff_draws_flips_and_pumps_events_after_display_init_only(
        self,
    ) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "src"))
        import pygame

        from greia_launcher import boot_intro

        pygame.display.init()
        try:
            self.assertFalse(pygame.mixer.get_init())
            screen = pygame.display.set_mode((960, 540))
            with mock.patch.dict(
                os.environ,
                {
                    "GREIA_BOOT_LOGO": str(
                        ROOT / "assets/boot/static/greia-boot-logo.png"
                    )
                },
                clear=False,
            ):
                self.assertTrue(
                    boot_intro.draw_boot_handoff_frame(screen, pygame, progress=92)
                )
            pygame.display.flip()
            # The display event system pumps without broad pygame.init():
            # drain whatever set_mode queued, then the queue stays drained.
            pygame.event.pump()
            drained = pygame.event.get()
            self.assertIsInstance(drained, list)
            self.assertEqual(pygame.event.get(), [])
        finally:
            pygame.display.quit()

    def test_fonts_render_where_required_through_lazy_typography(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "src"))
        import pygame

        from greia_platform.typography import FontRole, GreiaTypography

        pygame.display.init()
        try:
            typography = GreiaTypography(
                ROOT / "assets" / "fonts" / "nunito-sans"
            )
            rendered = typography.font(FontRole.BODY, 24).render(
                "Greia", True, (0, 0, 0)
            )
            self.assertGreater(rendered.get_width(), 0)
            self.assertGreater(rendered.get_height(), 0)
        finally:
            pygame.display.quit()

    def test_controller_set_opens_lazily_after_display_only_init(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "src"))
        import pygame

        from greia_platform.pygame_input import PygameControllerSet

        pygame.display.init()
        try:
            controllers = PygameControllerSet()
            opened = controllers.start()
            try:
                self.assertGreaterEqual(opened, 0)
                self.assertEqual(controllers.opened_count, opened)
            finally:
                controllers.close()
        finally:
            pygame.display.quit()


if __name__ == "__main__":
    raise SystemExit(unittest.main())

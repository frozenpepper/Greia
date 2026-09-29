from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FRAMES = (
    PROJECT_ROOT
    / "assets"
    / "boot"
    / "frames"
)


class BootAnimationMigrationTests(unittest.TestCase):
    """Plymouth is migration debt, not the accepted Greia boot architecture.

    The Greia-owned early framebuffer cover replaces Plymouth in target and
    installer boot. The 52-frame animation is preserved under ``assets/boot/frames/``;
    Plymouth must never be staged into a built image or wired into the builders again.
    """

    def test_animation_frames_are_present_and_no_plymouth_in_overlays(self) -> None:
        # The 52 animation frames are preserved under assets/boot/frames.
        self.assertTrue((SOURCE_FRAMES / "frame_0051.png").is_file())
        self.assertFalse((PROJECT_ROOT / "build/overlay/etc/plymouth").exists())
        self.assertFalse((PROJECT_ROOT / "build/installer-overlay/etc/plymouth").exists())

    def test_builders_never_stage_or_enable_plymouth(self) -> None:
        # T01: target-role composition lives in the shared engine; the thin
        # consumer must also stay Plymouth-free.
        for builder_name in ("build/lib/compose.sh", "build/build-installer-image.sh", "build/build-image.sh"):
            with self.subTest(builder=builder_name):
                builder = (PROJECT_ROOT / builder_name).read_text(encoding="utf-8")
                self.assertNotIn("plymouth-set-default-theme", builder)
                self.assertNotIn("usr/share/plymouth/themes", builder)
                self.assertNotIn("plymouth-quit.service", builder)
                self.assertNotIn("plymouth-quit-wait.service", builder)

    def test_launcher_starts_the_unprivileged_x_server(self) -> None:
        """The launcher must not reach X through Debian's setuid wrapper.

        /usr/bin/Xorg execs /usr/lib/xorg/Xorg.wrap, which is setuid root, so X
        runs with uid=greiakid and euid=0. xorg-server refuses -logfile on a
        uid/euid mismatch ("Invalid argument -logfile with elevated
        privileges"), the server exited at once, and Restart=always turned
        first boot into a splash loop on the reference Acer.

        This asserts the server is named directly, and that the setuid wrapper
        is not named anywhere in the unit, so the fix cannot be quietly undone
        by restoring the shorter ExecStart.
        """

        unit = (
            PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-launcher.service"
        )
        text = unit.read_text(encoding="utf-8")
        exec_lines = [
            line for line in text.splitlines() if line.startswith("ExecStart=")
        ]
        self.assertEqual(len(exec_lines), 1, exec_lines)
        self.assertIn("/usr/lib/xorg/Xorg :0 vt1", exec_lines[0])
        # The rationale comment deliberately names Xorg.wrap, so only effective
        # directives are checked for it.
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";")):
                continue
            self.assertNotIn("Xorg.wrap", stripped, line)
            self.assertNotIn("/usr/bin/Xorg", stripped, line)

    def test_launcher_and_installer_services_do_not_order_after_plymouth(self) -> None:
        for unit in (
            PROJECT_ROOT / "build/overlay/etc/systemd/system/greia-launcher.service",
            PROJECT_ROOT / "build/installer-overlay/etc/systemd/system/greia-installer.service",
        ):
            with self.subTest(unit=unit.name):
                text = unit.read_text(encoding="utf-8")
                self.assertNotIn("plymouth-start.service", text)
                self.assertNotIn("plymouth", text)

    def test_no_plymouth_release_binary_or_theme_in_overlays(self) -> None:
        # No Plymouth runtime theme is staged into the built overlays.
        self.assertFalse(
            (PROJECT_ROOT / "build/installer-overlay/etc/plymouth/themes/greia").exists()
        )

    def test_boot_cover_release_and_vt_prep_no_longer_drive_plymouth(self) -> None:
        release = (
            PROJECT_ROOT / "build/overlay/usr/local/lib/greia-os/release-boot-cover"
        ).read_text(encoding="utf-8")
        self.assertNotIn("plymouth", release)
        prepare = (
            PROJECT_ROOT / "build/overlay/usr/local/lib/greia-os/prepare-launcher-vt"
        ).read_text(encoding="utf-8")
        self.assertNotIn("plymouth", prepare)


if __name__ == "__main__":
    unittest.main()


class _FakeIntroSurface:
    def __init__(self, width: int = 222, height: int = 600) -> None:
        self._size = (width, height)

    def get_width(self) -> int:
        return self._size[0]

    def get_height(self) -> int:
        return self._size[1]

    def get_size(self) -> tuple[int, int]:
        return self._size

    def fill(self, *args: object) -> None:
        pass

    def blit(self, *args: object) -> None:
        pass

    def get_rect(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(center=kwargs.get("center", (0, 0)))


class _FakeIntroDisplay:
    def __init__(self) -> None:
        self.flips = 0

    def flip(self) -> None:
        self.flips += 1


class _FakeIntroEventQueue:
    """Minimal pygame.event stand-in with a real queue.

    Supports the filtered ``get(type)`` drain used by the intro plus the
    unfiltered ``get()``/``post()`` fallback, so the stale-burst test fails
    on the old pump-only path (which never calls ``get``) and passes once
    the intro drains motion.
    """

    def __init__(self, initial: list[SimpleNamespace] | None = None) -> None:
        self.queue: list[SimpleNamespace] = list(initial or [])
        self.pump_calls = 0

    def pump(self) -> None:
        self.pump_calls += 1

    def get(self, *args: object) -> list[SimpleNamespace]:
        if not args or args[0] is None:
            pending = list(self.queue)
            self.queue.clear()
            return pending
        wanted: set[int] = set()
        for arg in args:
            if isinstance(arg, (list, tuple, set)):
                wanted.update(int(v) for v in arg)
            else:
                wanted.add(int(arg))  # type: ignore[arg-type]
        matched = [e for e in self.queue if int(e.type) in wanted]
        self.queue = [e for e in self.queue if int(e.type) not in wanted]
        return matched

    def post(self, event: SimpleNamespace) -> None:
        self.queue.append(event)

    def clear(self, *args: object) -> None:
        if not args or args[0] is None:
            self.queue.clear()
            return
        wanted: set[int] = set()
        for arg in args:
            if isinstance(arg, (list, tuple, set)):
                wanted.update(int(v) for v in arg)
            else:
                wanted.add(int(arg))  # type: ignore[arg-type]
        self.queue = [e for e in self.queue if int(e.type) not in wanted]


def _make_intro_fake_pygame(queue: _FakeIntroEventQueue) -> SimpleNamespace:
    display = _FakeIntroDisplay()
    return SimpleNamespace(
        # Distinct constants; only relative identity matters for the test.
        MOUSEMOTION=4,
        MOUSEBUTTONDOWN=1025,
        MOUSEBUTTONUP=1026,
        MOUSEWHEEL=1027,
        KEYDOWN=768,
        KEYUP=769,
        TEXTINPUT=771,
        QUIT=256,
        VIDEORESIZE=32769,
        display=display,
        event=queue,
        time=SimpleNamespace(wait=lambda ms: None),
        transform=SimpleNamespace(smoothscale=lambda surface, size: surface),
        Rect=SimpleNamespace,
        draw=SimpleNamespace(rect=lambda *a, **k: None),
    )


def _clean_intro_env(marker: Path) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("GREIA_SKIP_BOOT_INTRO", "GREIA_SKIP_BOOT_HANDOFF")
    }
    env["GREIA_BOOT_INTRO_MARKER"] = str(marker)
    return env


class IntroQueueDrainTests(unittest.TestCase):
    """Intro queue-handling contract: drain (never pump) stale motion.

    Discard set is exactly ``{MOUSEMOTION}``; every other type (QUIT,
    KEYDOWN/KEYUP, TEXTINPUT, MOUSEBUTTONDOWN/UP, MOUSEWHEEL, VIDEORESIZE,
    …) is preserved for the post-intro interactive loop.
    """

    def _run_intro(self, pygame: SimpleNamespace, screen: _FakeIntroSurface) -> None:
        from greia_launcher import boot_intro

        frames = [_FakeIntroSurface() for _ in range(3)]
        with mock.patch.object(
            boot_intro, "ANIMATION_SECONDS", 0.05
        ), mock.patch.object(
            boot_intro, "FINAL_FRAME_HOLD_SECONDS", 0.01
        ), mock.patch.object(
            boot_intro, "_RENDER_INTERVAL_SECONDS", 0.001
        ), mock.patch.object(
            boot_intro, "load_animation_frames", return_value=frames
        ), mock.patch.object(
            boot_intro, "load_logo", return_value=_FakeIntroSurface()
        ):
            boot_intro._FIRST_FRAME_FLIPPED_EMITTED = False
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                boot_intro.run_intro(screen, pygame)

    def test_stale_motions_spanning_intro_never_reach_run_loop(self) -> None:
        from greia_launcher import boot_intro  # noqa: F401

        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "intro-marker"
            with mock.patch.dict(os.environ, _clean_intro_env(marker), clear=True):
                queue = _FakeIntroEventQueue(
                    [SimpleNamespace(type=4, pos=(i, i)) for i in range(30)]
                )
                pygame = _make_intro_fake_pygame(queue)
                screen = _FakeIntroSurface(960, 540)
                self._run_intro(pygame, screen)
                remaining = list(queue.queue)
                self.assertEqual(
                    [e for e in remaining if int(e.type) == 4],
                    [],
                    f"stale MOUSEMOTION burst survived the intro: {len(remaining)} left",
                )
                # The intro really flipped (animation + final frame ran).
                self.assertGreaterEqual(pygame.display.flips, 3)

    def test_non_motion_events_preserved_across_intro(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "intro-marker"
            with mock.patch.dict(os.environ, _clean_intro_env(marker), clear=True):
                queued = [
                    SimpleNamespace(type=4, pos=(10, 10)),
                    SimpleNamespace(type=768, key=1073741903),
                    SimpleNamespace(type=769, key=1073741903),
                    SimpleNamespace(type=771, text="a"),
                    SimpleNamespace(type=1025, button=1, pos=(5, 5)),
                    SimpleNamespace(type=1026, button=1, pos=(5, 5)),
                    SimpleNamespace(type=1027, y=1),
                    SimpleNamespace(type=256),
                    SimpleNamespace(type=32769, size=(800, 600)),
                    SimpleNamespace(type=4, pos=(20, 20)),
                ]
                queue = _FakeIntroEventQueue(list(queued))
                pygame = _make_intro_fake_pygame(queue)
                screen = _FakeIntroSurface(960, 540)
                self._run_intro(pygame, screen)
                remaining_types = [int(e.type) for e in queue.queue]
                self.assertNotIn(4, remaining_types)
                self.assertEqual(
                    remaining_types,
                    [768, 769, 771, 1025, 1026, 1027, 256, 32769],
                    f"non-motion semantics must survive the intro drain: {remaining_types}",
                )

    def test_first_frame_marker_exactly_once(self) -> None:
        import re

        from greia_launcher import boot_intro

        line_re = re.compile(r"^GREIA_BOOT event=(\S+) monotonic_ns=(\d+)$")
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "intro-marker"
            with mock.patch.dict(os.environ, _clean_intro_env(marker), clear=True):
                queue = _FakeIntroEventQueue()
                pygame = _make_intro_fake_pygame(queue)
                screen = _FakeIntroSurface(960, 540)
                frames = [_FakeIntroSurface() for _ in range(3)]
                with mock.patch.object(
                    boot_intro, "ANIMATION_SECONDS", 0.05
                ), mock.patch.object(
                    boot_intro, "FINAL_FRAME_HOLD_SECONDS", 0.01
                ), mock.patch.object(
                    boot_intro, "_RENDER_INTERVAL_SECONDS", 0.001
                ), mock.patch.object(
                    boot_intro, "load_animation_frames", return_value=frames
                ), mock.patch.object(
                    boot_intro, "load_logo", return_value=_FakeIntroSurface()
                ):
                    boot_intro._FIRST_FRAME_FLIPPED_EMITTED = False
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        boot_intro.run_intro(screen, pygame)
                lines = buffer.getvalue().splitlines()
                for line in lines:
                    self.assertIsNotNone(line_re.match(line))
                kpi = [line for line in lines if "intro_first_frame_flipped" in line]
                self.assertEqual(len(kpi), 1)

    def test_intro_duration_contract_unchanged(self) -> None:
        from greia_launcher import boot_intro

        self.assertEqual(boot_intro.ANIMATION_SECONDS, 5.0)
        self.assertEqual(boot_intro.FINAL_FRAME_HOLD_SECONDS, 2.0)
        self.assertEqual(
            boot_intro.MAX_INTRO_SECONDS,
            boot_intro.ANIMATION_SECONDS + boot_intro.FINAL_FRAME_HOLD_SECONDS,
        )
        self.assertEqual(boot_intro.MAX_INTRO_SECONDS, 7.0)

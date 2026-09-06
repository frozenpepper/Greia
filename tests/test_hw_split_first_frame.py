from __future__ import annotations

import os
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from greia_platform.hal_legacy_x import LegacyXHardwareSessionController
from greia_platform.hardware import HardwareSettings
from greia_platform.hardware_session_legacy_x import (
    run_visual_preframe,
    wait_for_first_frame,
)
from greia_platform.system_controls import SystemControlSettings
from greia_platform.system_controls_legacy_x import LegacyXSystemControlBackend

ROOT = Path(__file__).resolve().parents[1]
X_SESSION = ROOT / "build/overlay/usr/local/lib/greia-os/greia-x-session"
RELEASE_BOOT_COVER = ROOT / "build/overlay/usr/local/lib/greia-os/release-boot-cover"


class FakeRunner:
    """Minimal xrandr-only runner: no keyboard/audio/pointer vocabulary."""

    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.xrandr_stdout = (
            "Screen 0: minimum 320 x 200, current 1024 x 600\n"
            "LVDS1 connected primary 1024x600+0+0 "
            "(normal left inverted right x axis y axis) 220mm x 130mm\n"
            "   1024x600      60.00*+\n"
            "   800x600       60.32\n"
        )

    def run(self, command):
        command = tuple(command)
        self.commands.append(command)
        if command == ("xrandr", "--query"):
            return subprocess.CompletedProcess(command, 0, self.xrandr_stdout, "")
        return subprocess.CompletedProcess(command, 0, "", "")


class _HardwareStore:
    def __init__(self, settings: HardwareSettings):
        self._settings = settings

    def read(self) -> HardwareSettings:
        return self._settings


class _SystemStore:
    def __init__(self, settings: SystemControlSettings):
        self._settings = settings

    def read(self) -> SystemControlSettings:
        return self._settings


def _hardware_settings(**overrides) -> HardwareSettings:
    values: dict = {
        "schema_version": 2,
        "touchpad_tap": True,
        "touchpad_speed": -0.25,
        "mouse_speed": 0.5,
        "natural_scrolling": True,
        "resolution": "1024x600",
        "keyboard_layout": "us",
        "mic_gain": 2.0,
        "disable_while_typing": True,
    }
    values.update(overrides)
    return HardwareSettings(**values)


class VisualPreframeTests(unittest.TestCase):
    def _backlight(self, root: Path) -> Path:
        node = root / "intel_backlight"
        node.mkdir(parents=True)
        (node / "max_brightness").write_text("100\n", encoding="ascii")
        (node / "brightness").write_text("100\n", encoding="ascii")
        return root

    def test_preframe_runs_only_visual_commands(self) -> None:
        runner = FakeRunner()
        controller = LegacyXHardwareSessionController(runner)
        with tempfile.TemporaryDirectory() as temporary:
            backlight_root = self._backlight(Path(temporary) / "backlight")
            backend = LegacyXSystemControlBackend(
                runner, backlight_root=backlight_root
            )
            result = run_visual_preframe(
                _HardwareStore(_hardware_settings()),
                _SystemStore(SystemControlSettings(brightness_percent=60)),
                hardware_controller=controller,
                system_backend=backend,
            )
            self.assertEqual(result, 0)
            # Brightness went through the writable sysfs node, not a fallback.
            brightness = backlight_root / "intel_backlight" / "brightness"
            self.assertEqual(brightness.read_text(encoding="ascii").strip(), "60")
        kinds = [cmd[0] for cmd in runner.commands]
        # Only the display probe + mode-set may issue subprocesses.
        self.assertTrue(runner.commands)
        for command in runner.commands:
            self.assertEqual(command[0], "xrandr")
        self.assertIn(
            ("xrandr", "--output", "LVDS1", "--mode", "1024x600"),
            runner.commands,
        )
        self.assertNotIn("setxkbmap", kinds)
        self.assertNotIn("xinput", kinds)
        self.assertNotIn("amixer", kinds)

    def test_preframe_brightness_fallback_still_never_touches_volume(self) -> None:
        runner = FakeRunner()
        controller = LegacyXHardwareSessionController(runner)
        with tempfile.TemporaryDirectory() as temporary:
            backend = LegacyXSystemControlBackend(
                runner, backlight_root=Path(temporary) / "no-backlight"
            )
            result = run_visual_preframe(
                _HardwareStore(_hardware_settings(resolution="auto")),
                _SystemStore(SystemControlSettings(brightness_percent=80)),
                hardware_controller=controller,
                system_backend=backend,
            )
        self.assertEqual(result, 0)
        self.assertIn(
            ("xrandr", "--output", "LVDS1", "--auto"),
            runner.commands,
        )
        self.assertIn(
            ("xrandr", "--output", "LVDS1", "--brightness", "0.80"),
            runner.commands,
        )
        words = {word for command in runner.commands for word in command}
        for forbidden in ("Master", "Speaker", "PCM", "Capture", "Mic"):
            self.assertNotIn(forbidden, words)

    def test_preframe_is_fail_soft_and_always_exits_zero(self) -> None:
        class _Raising:
            def apply_display_mode(self, _settings):
                raise RuntimeError("no X display")

        result = run_visual_preframe(
            _HardwareStore(_hardware_settings()),
            _SystemStore(SystemControlSettings()),
            hardware_controller=_Raising(),  # type: ignore[arg-type]
            system_backend=LegacyXSystemControlBackend(
                FakeRunner(), backlight_root=Path("/nonexistent-backlight"),
            ),
        )
        self.assertEqual(result, 0)

    def test_full_apply_still_covers_nonvisual_work(self) -> None:
        # The split moved nonvisual work; it must not have deleted it.
        runner = FakeRunner()
        result = LegacyXHardwareSessionController(runner).apply(
            _hardware_settings()
        )
        self.assertTrue(result.applied)
        kinds = [cmd[0] for cmd in runner.commands]
        self.assertIn("setxkbmap", kinds)
        volume = LegacyXSystemControlBackend(FakeRunner())._apply_volume(
            SystemControlSettings(volume_percent=70)
        )
        self.assertTrue(volume[0])


class FirstFrameGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = os.environ.pop("GREIA_SKIP_BOOT_HANDOFF", None)

    def tearDown(self) -> None:
        if self._saved is not None:
            os.environ["GREIA_SKIP_BOOT_HANDOFF"] = self._saved
        else:
            os.environ.pop("GREIA_SKIP_BOOT_HANDOFF", None)

    def test_gate_blocks_until_fifo_poke_then_releases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fifo = Path(temporary) / "first-frame.fifo"
            os.mkfifo(fifo)
            worker = threading.Thread(
                target=wait_for_first_frame, args=(fifo,), daemon=True
            )
            worker.start()
            worker.join(timeout=2.0)
            # Still blocked: no sleep/poll released it early.
            self.assertTrue(worker.is_alive())
            # The release-boot-cover poke: a read-write open never blocks and
            # wakes the blocked reader.
            fd = os.open(fifo, os.O_RDWR)
            try:
                os.write(fd, b"ready\n")
            finally:
                os.close(fd)
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())

    def test_gate_fail_open_without_fifo(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "no-gate.fifo"
            worker = threading.Thread(
                target=wait_for_first_frame, args=(missing,), daemon=True
            )
            worker.start()
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())

    def test_gate_honors_boot_handoff_opt_out(self) -> None:
        os.environ["GREIA_SKIP_BOOT_HANDOFF"] = "1"
        with tempfile.TemporaryDirectory() as temporary:
            fifo = Path(temporary) / "never-poked.fifo"
            os.mkfifo(fifo)
            worker = threading.Thread(
                target=wait_for_first_frame, args=(fifo,), daemon=True
            )
            worker.start()
            worker.join(timeout=5.0)
            self.assertFalse(worker.is_alive())

    def test_gate_source_uses_no_sleep_or_timer(self) -> None:
        import re

        import greia_platform.hardware_session_legacy_x as entrypoint

        source = Path(entrypoint.__file__).read_text(encoding="utf-8")
        gate = source[source.index("def wait_for_first_frame"):]
        gate = gate[:gate.index("\n\n\n")]
        self.assertIsNone(re.search(r"\bsleep\s*\(", gate))
        self.assertNotIn("Timer(", gate)
        self.assertNotIn(".wait(", gate)


class SessionOrderingContractTests(unittest.TestCase):
    def test_x_session_preframe_before_shell_and_gated_watcher(self) -> None:
        text = X_SESSION.read_text(encoding="utf-8")
        self.assertIn("--preframe", text)
        self.assertIn("--wait-for-first-frame", text)
        self.assertIn("mkfifo", text)
        self.assertIn("GREIA_FIRST_FRAME_FIFO", text)
        self.assertLess(
            text.index("--preframe"), text.index("child_shell_exec")
        )
        self.assertLess(
            text.index("--wait-for-first-frame"), text.index("child_shell_exec")
        )
        # The child shell never waits for the watcher; the gate does.
        self.assertNotIn("sleep", text)
        # Single owner: exactly the preframe oneshot plus the gated watcher.
        self.assertEqual(text.count("hardware_session_legacy_x"), 2)
        self.assertNotIn("daemon", text)

    def test_release_boot_cover_pokes_gate_without_sleep(self) -> None:
        text = RELEASE_BOOT_COVER.read_text(encoding="utf-8")
        self.assertIn("GREIA_FIRST_FRAME_FIFO", text)
        self.assertIn("-p", text)
        self.assertNotIn("sleep", text)
        # The poke precedes the one-shot early exit so restarts release it.
        self.assertLess(
            text.index("GREIA_FIRST_FRAME_FIFO"), text.index("exit 0")
        )
        # Original one-shot marker behavior preserved.
        self.assertIn("boot-cover-released", text)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.activity_backend_policy import (
    ActivityBackendPolicyError,
    BackendFindingSeverity,
    assert_python_activity_backend_independent,
    scan_python_activity_backend_policy,
)


class ActivityBackendPolicyTests(unittest.TestCase):
    def _activity(self, source: str, *, name: str = "main.py") -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / name).write_text(source, encoding="utf-8")
        return root

    def test_runtime_neutral_pygame_and_performance_patterns_are_allowed(self) -> None:
        root = self._activity(
            """
import pygame

screen = pygame.display.set_mode((1024, 600), pygame.FULLSCREEN)
backdrop = pygame.Surface(screen.get_size()).convert()
for event in pygame.event.get():
    if event.type == pygame.MOUSEMOTION:
        pass
pygame.display.flip()
"""
        )

        self.assertEqual(scan_python_activity_backend_policy(root), ())
        assert_python_activity_backend_independent(root)

    def test_direct_backend_and_device_imports_are_blockers(self) -> None:
        for statement in (
            "import Xlib",
            "from xcffib import connect",
            "import pywayland",
            "from evdev import InputDevice",
            "import libinput",
        ):
            with self.subTest(statement=statement):
                root = self._activity(statement + "\n")
                findings = scan_python_activity_backend_policy(root)
                self.assertTrue(findings)
                self.assertTrue(
                    all(item.severity is BackendFindingSeverity.BLOCKER for item in findings)
                )
                with self.assertRaises(ActivityBackendPolicyError):
                    assert_python_activity_backend_independent(root)

    def test_backend_environment_reads_and_writes_are_blockers(self) -> None:
        cases = (
            'import os\nvalue = os.environ["DISPLAY"]\n',
            'import os\nvalue = os.environ.get("WAYLAND_DISPLAY")\n',
            'import os\nvalue = os.getenv("XAUTHORITY")\n',
            'import os\nos.environ.setdefault("SDL_VIDEODRIVER", "x11")\n',
            'import os\nos.environ.update({"DISPLAY": ":0"})\n',
        )
        for source in cases:
            with self.subTest(source=source):
                root = self._activity(source)
                with self.assertRaisesRegex(
                    ActivityBackendPolicyError, "backend-environment"
                ):
                    assert_python_activity_backend_independent(root)

    def test_raw_input_and_drm_device_paths_are_blockers(self) -> None:
        root = self._activity(
            'INPUT = "/dev/input/event0"\nDRM = "/dev/dri/card0"\n'
        )
        with self.assertRaisesRegex(ActivityBackendPolicyError, "raw-device-path"):
            assert_python_activity_backend_independent(root)

    def test_backend_shell_commands_are_blockers_only_when_executed(self) -> None:
        root = self._activity(
            """
import subprocess
subprocess.run(["xrandr", "--query"])
"""
        )
        with self.assertRaisesRegex(ActivityBackendPolicyError, "backend-command"):
            assert_python_activity_backend_independent(root)

        harmless = self._activity(
            'NOTE = "xrandr is a platform implementation detail"\n'
        )
        assert_python_activity_backend_independent(harmless)

    def test_native_x11_wayland_drm_library_probes_are_blockers(self) -> None:
        root = self._activity(
            """
import ctypes.util
name = ctypes.util.find_library("X11")
"""
        )
        with self.assertRaisesRegex(
            ActivityBackendPolicyError, "backend-native-library"
        ):
            assert_python_activity_backend_independent(root)

    def test_current_activity_side_system_chrome_is_migration_debt_not_new_blocker(self) -> None:
        root = self._activity(
            """
from greia_platform.activity_ui import draw_system_chrome_overlay, is_home_clicked
"""
        )
        findings = scan_python_activity_backend_policy(root)
        self.assertEqual(len(findings), 2)
        self.assertTrue(
            all(item.severity is BackendFindingSeverity.MIGRATION for item in findings)
        )
        assert_python_activity_backend_independent(root)

    def test_direct_pygame_joystick_is_migration_debt(self) -> None:
        root = self._activity(
            """
import pygame
pygame.joystick.init()
pad = pygame.joystick.Joystick(0)
"""
        )
        findings = scan_python_activity_backend_policy(root)
        self.assertTrue(findings)
        self.assertTrue(
            all(item.severity is BackendFindingSeverity.MIGRATION for item in findings)
        )
        self.assertEqual({item.code for item in findings}, {"raw-controller"})
        assert_python_activity_backend_independent(root)

    def test_comments_and_docstrings_do_not_trigger_keyword_false_positives(self) -> None:
        root = self._activity(
            '"""DISPLAY XAUTHORITY /dev/input xrandr X11 are backend details."""\n'
        )
        self.assertEqual(scan_python_activity_backend_policy(root), ())

    def test_findings_include_all_python_modules_in_package(self) -> None:
        root = self._activity("import pygame\n")
        (root / "helper.py").write_text(
            'import os\nvalue = os.getenv("DISPLAY")\n', encoding="utf-8"
        )
        findings = scan_python_activity_backend_policy(root)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].path.name, "helper.py")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from greia_platform.hal_legacy_x import (
    LegacyXHardwareSessionController,
    LegacyXInputHAL,
)


class _Runner:
    def run(self, command):
        command = tuple(command)
        if command == ("xinput", "--list", "--short"):
            output = (
                "↳ USB Mouse id=13 [slave  pointer  (2)]\n"
                "↳ AT Translated Set 2 keyboard id=14 [slave  keyboard (3)]\n"
            )
            return subprocess.CompletedProcess(command, 0, output, "")
        return subprocess.CompletedProcess(command, 1, "", "unsupported")


class LegacyXHALTests(unittest.TestCase):
    def test_input_capability_is_probed_not_inferred_from_display_environment(self) -> None:
        controller = LegacyXHardwareSessionController(_Runner())
        with patch.dict(os.environ, {}, clear=True):
            state = LegacyXInputHAL(controller).probe()
        self.assertTrue(state.pointer)
        self.assertTrue(state.keyboard)
        self.assertEqual(state.backend, "legacy-x11")

    def test_generic_hal_module_contains_no_x_session_dependency(self) -> None:
        import greia_platform.hal as hal

        source = Path(hal.__file__).read_text(encoding="utf-8")
        self.assertNotIn("LegacyXHardwareSessionController", source)
        self.assertNotIn("DISPLAY", source)
        self.assertNotIn("hardware_session", source)

    def test_x_commands_exist_only_in_explicit_legacy_adapter_not_generic_watcher(self) -> None:
        import greia_platform.hal_legacy_x as legacy
        import greia_platform.hardware_session as generic

        legacy_source = Path(legacy.__file__).read_text(encoding="utf-8")
        generic_source = Path(generic.__file__).read_text(encoding="utf-8")
        self.assertIn('"xrandr"', legacy_source)
        self.assertIn('"xinput"', legacy_source)
        self.assertNotIn('"xrandr"', generic_source)
        self.assertNotIn('"xinput"', generic_source)


if __name__ == "__main__":
    unittest.main()

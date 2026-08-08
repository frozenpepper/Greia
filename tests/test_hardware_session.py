from __future__ import annotations

import subprocess
import unittest

from greia_platform.hardware import HardwareSettings
from greia_platform.hardware_session import XSessionHardwareController


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def run(self, command):
        command = tuple(command)
        self.commands.append(command)
        if command == ("xrandr", "--query"):
            output = "Screen 0: minimum 320 x 200, current 1024 x 600\nLVDS1 connected primary 1024x600+0+0\n   1024x600      60.00*+\n   800x600       60.32\n"
        elif command == ("xinput", "--list", "--short"):
            output = "↳ SynPS/2 Synaptics TouchPad id=12 [slave  pointer  (2)]\n↳ USB Mouse id=13 [slave  pointer  (2)]\n↳ AT Translated Set 2 keyboard id=14 [slave  keyboard (3)]\n"
        elif command == ("xinput", "list-props", "12"):
            output = "libinput Tapping Enabled (300): 0\nlibinput Natural Scrolling Enabled (301): 0\nlibinput Accel Speed (302): 0.0\n"
        elif command == ("xinput", "list-props", "13"):
            output = "libinput Accel Speed (302): 0.0\n"
        else:
            output = ""
        return subprocess.CompletedProcess(command, 0, output, "")


class HardwareSessionTests(unittest.TestCase):
    def test_applies_only_known_xinput_and_xrandr_controls(self) -> None:
        runner = FakeRunner()
        controller = XSessionHardwareController(runner)
        settings = HardwareSettings(
            schema_version=1,
            touchpad_tap=True,
            touchpad_speed=-0.25,
            mouse_speed=0.5,
            natural_scrolling=True,
            resolution="1024x600",
        )
        result = controller.apply(settings)
        self.assertTrue(result.applied)
        self.assertIn(
            ("xinput", "set-prop", "12", "libinput Tapping Enabled", "1"),
            runner.commands,
        )
        self.assertIn(
            ("xinput", "set-prop", "13", "libinput Accel Speed", "0.50"),
            runner.commands,
        )
        self.assertIn(
            ("xrandr", "--output", "LVDS1", "--mode", "1024x600"),
            runner.commands,
        )
        self.assertTrue(controller.pointer_available())
        self.assertTrue(controller.keyboard_available())

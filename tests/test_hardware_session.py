from __future__ import annotations

import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from greia_platform.hal_legacy_x import LegacyXHardwareSessionController
from greia_platform.hardware import DisplayMode, HardwareSettings
from greia_platform.hardware_session import (
    ApplyResult,
    DisplayProbe,
    run_watcher,
)


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


class _Store:
    def __init__(self, settings: HardwareSettings):
        self.settings = settings
        self.validations: list[tuple[str, ...]] = []

    def version_token(self):
        return 1

    def read(self):
        return self.settings

    def validate(self, settings, *, allowed_resolutions=None):
        self.validations.append(tuple(allowed_resolutions or ()))


class _SemanticController:
    backend_id = "fake-direct"

    def __init__(self):
        self.calls: list[str] = []
        self.display = DisplayProbe(
            "panel-0",
            (
                DisplayMode(
                    width=1024,
                    height=600,
                    refresh_hz=60.0,
                    preferred=True,
                    current=True,
                ),
            ),
        )

    def topology_token(self):
        self.calls.append("topology")
        return ("panel-0:1024x600", "pointer-0")

    def probe_display(self):
        self.calls.append("probe")
        return self.display

    def apply(self, settings):
        self.calls.append("apply")
        return ApplyResult(True, self.display, ("semantic settings applied",))


class HardwareSessionTests(unittest.TestCase):
    def _settings(self) -> HardwareSettings:
        return HardwareSettings(
            schema_version=1,
            touchpad_tap=True,
            touchpad_speed=-0.25,
            mouse_speed=0.5,
            natural_scrolling=True,
            resolution="1024x600",
        )

    def test_legacy_adapter_applies_only_known_xinput_and_xrandr_controls(self) -> None:
        runner = FakeRunner()
        controller = LegacyXHardwareSessionController(runner)
        result = controller.apply(self._settings())
        self.assertTrue(result.applied)
        self.assertEqual(controller.backend_id, "legacy-x11")
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

    def test_generic_watcher_requires_explicit_controller(self) -> None:
        parameter = inspect.signature(run_watcher).parameters["controller"]
        self.assertIs(parameter.default, inspect.Parameter.empty)

    def test_generic_watcher_applies_through_non_x_controller_and_records_backend(self) -> None:
        settings = self._settings()
        store = _Store(settings)
        controller = _SemanticController()
        with tempfile.TemporaryDirectory() as temporary:
            status = Path(temporary) / "status.json"
            result = run_watcher(
                store,  # type: ignore[arg-type]
                status,
                controller=controller,
                once=True,
            )
            payload = json.loads(status.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertEqual(payload["backend"], "fake-direct")
        self.assertTrue(payload["applied"])
        self.assertEqual(payload["display_output"], "panel-0")
        self.assertEqual(store.validations, [("1024x600",)])
        self.assertEqual(controller.calls, ["topology", "probe", "apply"])

    def test_generic_watcher_source_contains_no_x_command_implementation(self) -> None:
        import greia_platform.hardware_session as hardware_session

        source = Path(hardware_session.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"xrandr"', source)
        self.assertNotIn('"xinput"', source)
        self.assertNotIn("libinput Tapping Enabled", source)
        self.assertNotIn("libinput Accel Speed", source)


if __name__ == "__main__":
    unittest.main()

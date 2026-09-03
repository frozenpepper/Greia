from __future__ import annotations

import inspect
import json
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from threading import Event

from greia_platform.hal_legacy_x import LegacyXHardwareSessionController
from greia_platform.hardware import DisplayMode, HardwareSettings
from greia_platform.hardware_session import (
    ApplyResult,
    DisplayProbe,
    PointerKind,
    preset_to_speed,
    speed_preset_names,
    speed_to_preset,
    run_watcher,
)


class FakeRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.fail_set_props: set[tuple[str, ...]] = set()
        self.list_rc = 0
        self.list_props_rc: dict[str, int] = {}
        self.xrandr_stdout = (
            "Screen 0: minimum 320 x 200, current 1024 x 600\n"
            "LVDS1 connected primary 1024x600+0+0 "
            "(normal left inverted right x axis y axis) 220mm x 130mm\n"
            "   1024x600      60.00*+\n"
            "   800x600       60.32\n"
        )
        self.xrandr_rc = 0

    def run(self, command):
        command = tuple(command)
        self.commands.append(command)
        if command == ("xrandr", "--query"):
            return subprocess.CompletedProcess(
                command, self.xrandr_rc, self.xrandr_stdout, ""
            )
        elif command == ("xinput", "--list", "--short"):
            if self.list_rc != 0:
                return subprocess.CompletedProcess(command, 1, "", "no xinput")
            output = "↳ Generic Touchpad Device id=12 [slave  pointer  (2)]\n↳ Generic Mouse Device id=13 [slave  pointer  (2)]\n↳ AT Translated Set 2 keyboard id=14 [slave  keyboard (3)]\n"
        elif command == ("xinput", "list-props", "12"):
            if self.list_props_rc.get("12", 0) != 0:
                return subprocess.CompletedProcess(command, 1, "", "no props")
            output = "libinput Tapping Enabled (300): 0\nlibinput Natural Scrolling Enabled (301): 0\nlibinput Disable While Typing Enabled (302): 0\nlibinput Accel Speed (303): 0.0\n"
        elif command == ("xinput", "list-props", "13"):
            if self.list_props_rc.get("13", 0) != 0:
                return subprocess.CompletedProcess(command, 1, "", "no props")
            output = "libinput Natural Scrolling Enabled (301): 0\nlibinput Accel Speed (303): 0.0\n"
        elif (
            len(command) >= 4
            and command[:2] == ("xinput", "set-prop")
            and tuple(command) in self.fail_set_props
        ):
            return subprocess.CompletedProcess(command, 1, "", "denied")
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
    def _settings(self, **overrides) -> HardwareSettings:
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

    def test_generic_watcher_source_contains_no_x_backend_selection_or_commands(self) -> None:
        import greia_platform.hardware_session as hardware_session

        source = Path(hardware_session.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"xrandr"', source)
        self.assertNotIn('"xinput"', source)
        self.assertNotIn("libinput Tapping Enabled", source)
        self.assertNotIn("libinput Accel Speed", source)
        self.assertNotIn("LegacyXHardwareSessionController", source)
        self.assertNotIn("hal_legacy_x", source)

    def test_legacy_x_entrypoint_owns_current_backend_selection(self) -> None:
        import greia_platform.hardware_session_legacy_x as legacy_entrypoint

        source = Path(legacy_entrypoint.__file__).read_text(encoding="utf-8")
        self.assertIn("LegacyXHardwareSessionController", source)
        self.assertIn("run_watcher", source)


class LegacyXContractTests(unittest.TestCase):
    def _settings(self, **overrides) -> HardwareSettings:
        values: dict = {
            "schema_version": 2,
            "touchpad_tap": True,
            "touchpad_speed": -0.25,
            "mouse_speed": 0.5,
            "natural_scrolling": True,
            "resolution": "auto",
            "keyboard_layout": "us",
            "mic_gain": 2.0,
            "disable_while_typing": True,
        }
        values.update(overrides)
        return HardwareSettings(**values)

    def test_no_ctm_command_during_ordinary_apply(self) -> None:
        runner = FakeRunner()
        controller = LegacyXHardwareSessionController(runner)
        result = controller.apply(self._settings())
        self.assertTrue(result.applied)
        self.assertFalse(
            any("Coordinate Transformation Matrix" in cmd for cmd in runner.commands)
        )

    def test_disable_while_typing_follows_settings(self) -> None:
        runner_on = FakeRunner()
        LegacyXHardwareSessionController(runner_on).apply_pointer_settings(
            self._settings(disable_while_typing=True)
        )
        self.assertIn(
            ("xinput", "set-prop", "12", "libinput Disable While Typing Enabled", "1"),
            runner_on.commands,
        )
        runner_off = FakeRunner()
        LegacyXHardwareSessionController(runner_off).apply_pointer_settings(
            self._settings(disable_while_typing=False)
        )
        self.assertIn(
            ("xinput", "set-prop", "12", "libinput Disable While Typing Enabled", "0"),
            runner_off.commands,
        )

    def test_correct_speed_source_per_kind(self) -> None:
        runner = FakeRunner()
        controller = LegacyXHardwareSessionController(runner)
        result = controller.apply_pointer_settings(self._settings())
        self.assertTrue(result.applied)
        self.assertIn(
            ("xinput", "set-prop", "12", "libinput Accel Speed", "-0.25"),
            runner.commands,
        )
        self.assertIn(
            ("xinput", "set-prop", "13", "libinput Accel Speed", "0.50"),
            runner.commands,
        )

    def test_natural_scrolling_shared_where_supported(self) -> None:
        runner = FakeRunner()
        LegacyXHardwareSessionController(runner).apply_pointer_settings(
            self._settings(natural_scrolling=True)
        )
        self.assertIn(
            ("xinput", "set-prop", "12", "libinput Natural Scrolling Enabled", "1"),
            runner.commands,
        )
        self.assertIn(
            ("xinput", "set-prop", "13", "libinput Natural Scrolling Enabled", "1"),
            runner.commands,
        )

    def test_physical_mm_parsed_and_metrics_contract(self) -> None:
        probe = LegacyXHardwareSessionController(FakeRunner()).probe_display()
        self.assertEqual(probe.output_name, "LVDS1")
        self.assertIsNotNone(probe.metrics)
        assert probe.metrics is not None
        self.assertEqual(
            (probe.metrics.pixel_width, probe.metrics.pixel_height), (1024, 600)
        )
        self.assertTrue(probe.metrics.physical_size_known)

    def test_malformed_mm_stays_operable_with_unknown_physical(self) -> None:
        runner = FakeRunner()
        runner.xrandr_stdout = (
            "Screen 0: minimum 320 x 200, current 1024 x 600\n"
            "LVDS1 connected primary 1024x600+0+0 (normal) 0mm x 0mm\n"
            "   1024x600      60.00*+\n"
        )
        probe = LegacyXHardwareSessionController(runner).probe_display()
        self.assertEqual(probe.output_name, "LVDS1")
        assert probe.metrics is not None
        self.assertFalse(probe.metrics.physical_size_known)
        self.assertIsNone(probe.metrics.effective_dpi_x)

    def test_missing_optional_property_is_nonfatal(self) -> None:
        runner = FakeRunner()
        runner.list_props_rc = {"12": 1, "13": 1}
        result = LegacyXHardwareSessionController(runner).apply_pointer_settings(
            self._settings()
        )
        self.assertTrue(result.applied)

    def test_real_set_prop_failure_is_reported(self) -> None:
        runner = FakeRunner()
        runner.fail_set_props = {
            ("xinput", "set-prop", "13", "libinput Accel Speed", "0.50")
        }
        result = LegacyXHardwareSessionController(runner).apply_pointer_settings(
            self._settings()
        )
        self.assertFalse(result.applied)

    def test_xrandr_failure_fails_soft_and_stays_operable(self) -> None:
        runner = FakeRunner()
        runner.xrandr_rc = 1
        runner.xrandr_stdout = ""
        controller = LegacyXHardwareSessionController(runner)
        probe = controller.probe_display()
        self.assertIsNone(probe.output_name)
        self.assertIsNone(probe.metrics)
        result = controller.apply_pointer_settings(self._settings())
        self.assertTrue(result.applied)

    def test_list_failure_fails_soft_and_stays_operable(self) -> None:
        runner = FakeRunner()
        runner.list_rc = 1
        controller = LegacyXHardwareSessionController(runner)
        self.assertEqual(controller.probe_pointers(), ())
        result = controller.apply_pointer_settings(self._settings())
        self.assertTrue(result.applied)

    def test_topology_token_changes_with_backend_output(self) -> None:
        runner = FakeRunner()
        controller = LegacyXHardwareSessionController(runner)
        before = controller.topology_token()
        runner.xrandr_stdout += "HDMI1 connected 800x600+0+0\n"
        after = controller.topology_token()
        self.assertNotEqual(before, after)

    def test_watcher_reprobes_after_topology_change(self) -> None:
        settings = self._settings()
        store = _Store(settings)

        class _ChangingController:
            backend_id = "fake-changing"

            def __init__(self) -> None:
                self.topology_calls = 0
                self.applies = 0
                self.display = DisplayProbe(
                    "panel-0",
                    (
                        DisplayMode(
                            width=1024, height=600, refresh_hz=60.0,
                            preferred=True, current=True,
                        ),
                    ),
                )

            def topology_token(self):
                self.topology_calls += 1
                if self.topology_calls < 3:
                    return ("panel-0", "pointer-0")
                return ("panel-0+HDMI1", "pointer-0")

            def probe_display(self):
                return self.display

            def apply(self, _settings):
                self.applies += 1
                return ApplyResult(True, self.display, ("ok",))

        controller = _ChangingController()
        stopper: Event = Event()
        with tempfile.TemporaryDirectory() as temporary:
            status = Path(temporary) / "status.json"
            worker = threading.Thread(
                target=run_watcher,
                args=(store, status),
                kwargs={
                    "controller": controller,  # type: ignore[arg-type]
                    "interval_seconds": 0.01,
                    "stop_event": stopper,
                },
            )
            worker.start()
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline and controller.applies < 2:
                time.sleep(0.01)
            stopper.set()
            worker.join(timeout=5.0)
        self.assertGreaterEqual(controller.applies, 2)
        self.assertGreaterEqual(controller.topology_calls, 3)

    def test_preview_seam_delegates_without_display_commands(self) -> None:
        runner = FakeRunner()
        controller = LegacyXHardwareSessionController(runner)
        # Structural preview seam: pointer-only probe/apply without
        # importing backend vocabulary into the generic layer.
        self.assertTrue(callable(getattr(controller, "probe_pointers", None)))
        self.assertTrue(callable(getattr(controller, "apply_pointer_settings", None)))
        infos = controller.probe_pointers()
        self.assertEqual(
            {info.kind for info in infos},
            {PointerKind.TOUCHPAD, PointerKind.MOUSE},
        )
        result = controller.apply_pointer_settings(self._settings())
        self.assertTrue(result.applied)
        self.assertFalse(any("--output" in cmd for cmd in runner.commands))
        self.assertFalse(any("--mode" in cmd for cmd in runner.commands))
        command_kinds = [cmd[0] for cmd in runner.commands]
        self.assertNotIn("setxkbmap", command_kinds)
        self.assertNotIn("amixer", command_kinds)
        # Generic apply entry point stays available for the watcher.
        self.assertTrue(callable(controller.apply))

    def test_speed_presets_are_shared_and_round_trip(self) -> None:
        names = speed_preset_names()
        self.assertGreaterEqual(len(names), 3)
        for name in names:
            value = preset_to_speed(name)
            self.assertGreaterEqual(value, -1.0)
            self.assertLessEqual(value, 1.0)
            self.assertEqual(speed_to_preset(value), name)
        with self.assertRaises(KeyError):
            preset_to_speed("not a preset")

    def test_backend_strings_stay_in_legacy_adapter(self) -> None:
        import greia_platform.hal as hal_module
        import greia_platform.hal_legacy_x as legacy
        import greia_platform.hardware_session as generic

        legacy_source = Path(legacy.__file__).read_text(encoding="utf-8")
        # The CTM hack is deleted: it appears nowhere, not even here.
        self.assertNotIn("Coordinate Transformation Matrix", legacy_source)
        for marker in (
            "libinput Tapping Enabled",
            "libinput Accel Speed",
            "libinput Disable While Typing Enabled",
        ):
            self.assertIn(marker, legacy_source)
        for module in (generic, hal_module):
            source = Path(module.__file__).read_text(encoding="utf-8")
            self.assertNotIn("Coordinate Transformation Matrix", source)
            self.assertNotIn("SynPS/2", source)
            self.assertNotIn("libinput Tapping Enabled", source)
            self.assertNotIn("libinput Accel Speed", source)
            self.assertNotIn("libinput Disable While Typing Enabled", source)


if __name__ == "__main__":
    unittest.main()

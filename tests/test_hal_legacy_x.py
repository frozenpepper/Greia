from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from greia_platform.display_metrics import DisplayMetricsSource
from greia_platform.hal_legacy_x import (
    LegacyXHardwareSessionController,
    LegacyXInputHAL,
)
from greia_platform.hardware import HardwareSettings
from greia_platform.hardware_session import PointerKind


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


class _ControllerProbe:
    def __init__(self, available: bool):
        self._available = available

    def available(self) -> bool:
        return self._available


def _settings(**overrides) -> HardwareSettings:
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


class _ConfigurableRunner:
    """Fake backend with scripted xrandr/xinput/list-props/set-prop behavior."""

    def __init__(
        self,
        *,
        xrandr_stdout: str = "",
        xrandr_rc: int = 0,
        list_stdout: str = "",
        list_rc: int = 0,
        props: dict | None = None,
        props_rc: dict | None = None,
        fail_set_props: tuple = (),
    ):
        self.xrandr_stdout = xrandr_stdout
        self.xrandr_rc = xrandr_rc
        self.list_stdout = list_stdout
        self.list_rc = list_rc
        self.props = props or {}
        self.props_rc = props_rc or {}
        self.fail_set_props = tuple(fail_set_props)
        self.commands: list[tuple[str, ...]] = []

    def run(self, command):
        command = tuple(command)
        self.commands.append(command)
        if command == ("xrandr", "--query"):
            return subprocess.CompletedProcess(
                command, self.xrandr_rc, self.xrandr_stdout, ""
            )
        if command == ("xinput", "--list", "--short"):
            return subprocess.CompletedProcess(
                command, self.list_rc, self.list_stdout, ""
            )
        if len(command) == 3 and command[:2] == ("xinput", "list-props"):
            device_id = command[2]
            if self.props_rc.get(device_id, 0) != 0:
                return subprocess.CompletedProcess(command, 1, "", "no such device")
            return subprocess.CompletedProcess(
                command, 0, self.props.get(device_id, ""), ""
            )
        if len(command) >= 4 and command[:2] == ("xinput", "set-prop"):
            if tuple(command) in self.fail_set_props or command[3] in self.fail_set_props:
                return subprocess.CompletedProcess(command, 1, "", "failed")
            return subprocess.CompletedProcess(command, 0, "", "")
        return subprocess.CompletedProcess(command, 0, "", "")


XRANDR_OK_MM = (
    "Screen 0: minimum 320 x 200, current 1024 x 600\n"
    "LVDS1 connected primary 1024x600+0+0 (normal left inverted right x axis y axis) 220mm x 130mm\n"
    "   1024x600      60.00*+\n"
    "   800x600       60.32\n"
)
XRANDR_OK_NO_MM = (
    "Screen 0: minimum 320 x 200, current 1024 x 600\n"
    "LVDS1 connected primary 1024x600+0+0\n"
    "   1024x600      60.00*+\n"
    "   800x600       60.32\n"
)
XRANDR_OK_BAD_MM = (
    "Screen 0: minimum 320 x 200, current 1024 x 600\n"
    "LVDS1 connected primary 1024x600+0+0 (normal) 0mm x 0mm\n"
    "   1024x600      60.00*+\n"
    "   800x600       60.32\n"
)
XRANDR_OK_NO_CURRENT = (
    "Screen 0: minimum 320 x 200, current 1024 x 600\n"
    "LVDS1 connected primary 1024x600+0+0 (normal) 220mm x 130mm\n"
    "   1024x600      60.00+\n"
    "   800x600       60.32\n"
)

LIST_TOUCHPAD_MOUSE = (
    "↳ Generic Touchpad Device id=12 [slave  pointer  (2)]\n"
    "↳ Generic Mouse Device id=13 [slave  pointer  (2)]\n"
    "↳ AT Translated Set 2 keyboard id=14 [slave  keyboard (3)]\n"
)
# No exact device names: generic labels carry no touchpad/mouse hint, so
# classification must come from properties.
LIST_GENERIC_NAMES = (
    "↳ Generic Relative Device id=12 [slave  pointer  (2)]\n"
    "↳ Generic Relative Device id=13 [slave  pointer  (2)]\n"
)

PROPS_TOUCHPAD_FULL = (
    "libinput Tapping Enabled (300): 0\n"
    "libinput Natural Scrolling Enabled (301): 0\n"
    "libinput Disable While Typing Enabled (302): 0\n"
    "libinput Accel Speed (303): 0.0\n"
)
PROPS_MOUSE_FULL = (
    "libinput Natural Scrolling Enabled (301): 0\n"
    "libinput Accel Speed (303): 0.0\n"
)
PROPS_ACCEL_ONLY = "libinput Accel Speed (303): 0.0\n"


class LegacyXHALTests(unittest.TestCase):
    def test_input_capability_is_probed_not_inferred_from_display_environment(self) -> None:
        controller = LegacyXHardwareSessionController(_Runner())
        with patch.dict(os.environ, {}, clear=True):
            state = LegacyXInputHAL(controller, _ControllerProbe(True)).probe()
        self.assertTrue(state.pointer)
        self.assertTrue(state.keyboard)
        self.assertTrue(state.controller)
        self.assertEqual(state.backend, "legacy-x11")

    def test_controller_absence_does_not_change_pointer_or_keyboard_capability(self) -> None:
        controller = LegacyXHardwareSessionController(_Runner())
        state = LegacyXInputHAL(controller, _ControllerProbe(False)).probe()
        self.assertTrue(state.pointer)
        self.assertTrue(state.keyboard)
        self.assertFalse(state.controller)

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


class LegacyXDisplayMetricsTests(unittest.TestCase):
    def test_physical_mm_parsed_into_metrics(self) -> None:
        runner = _ConfigurableRunner(xrandr_stdout=XRANDR_OK_MM)
        probe = LegacyXHardwareSessionController(runner).probe_display()
        self.assertEqual(probe.output_name, "LVDS1")
        self.assertIsNotNone(probe.metrics)
        assert probe.metrics is not None
        self.assertEqual(
            (probe.metrics.pixel_width, probe.metrics.pixel_height), (1024, 600)
        )
        self.assertTrue(probe.metrics.physical_size_known)
        self.assertEqual(probe.metrics.source, DisplayMetricsSource.XRANDR_PHYSICAL_SIZE)
        self.assertIsNotNone(probe.metrics.effective_dpi_x)

    def test_absent_mm_reports_unknown_physical_without_assumed_density(self) -> None:
        runner = _ConfigurableRunner(xrandr_stdout=XRANDR_OK_NO_MM)
        probe = LegacyXHardwareSessionController(runner).probe_display()
        self.assertEqual(probe.output_name, "LVDS1")
        self.assertIsNotNone(probe.metrics)
        assert probe.metrics is not None
        self.assertEqual(
            (probe.metrics.pixel_width, probe.metrics.pixel_height), (1024, 600)
        )
        self.assertFalse(probe.metrics.physical_size_known)
        self.assertIsNone(probe.metrics.effective_dpi_x)
        self.assertIsNone(probe.metrics.effective_dpi_y)

    def test_malformed_mm_reports_unknown_physical(self) -> None:
        runner = _ConfigurableRunner(xrandr_stdout=XRANDR_OK_BAD_MM)
        probe = LegacyXHardwareSessionController(runner).probe_display()
        self.assertIsNotNone(probe.metrics)
        assert probe.metrics is not None
        self.assertFalse(probe.metrics.physical_size_known)
        self.assertIsNone(probe.metrics.effective_dpi_x)

    def test_no_current_mode_yields_unknown_metrics(self) -> None:
        runner = _ConfigurableRunner(xrandr_stdout=XRANDR_OK_NO_CURRENT)
        probe = LegacyXHardwareSessionController(runner).probe_display()
        self.assertEqual(probe.output_name, "LVDS1")
        self.assertEqual(len(probe.modes), 2)
        self.assertIsNone(probe.metrics)

    def test_xrandr_failure_fails_soft_and_stays_operable(self) -> None:
        runner = _ConfigurableRunner(xrandr_stdout="", xrandr_rc=1)
        probe = LegacyXHardwareSessionController(runner).probe_display()
        self.assertIsNone(probe.output_name)
        self.assertEqual(probe.modes, ())
        self.assertIsNone(probe.metrics)


class LegacyXPointerSemanticsTests(unittest.TestCase):
    def _controller(self, **kwargs) -> tuple[LegacyXHardwareSessionController, _ConfigurableRunner]:
        runner = _ConfigurableRunner(
            xrandr_stdout=kwargs.pop("xrandr_stdout", XRANDR_OK_MM),
            list_stdout=kwargs.pop("list_stdout", LIST_TOUCHPAD_MOUSE),
            props=kwargs.pop(
                "props", {"12": PROPS_TOUCHPAD_FULL, "13": PROPS_MOUSE_FULL}
            ),
            **kwargs,
        )
        return LegacyXHardwareSessionController(runner), runner

    def test_classification_needs_no_exact_device_name(self) -> None:
        controller, _ = self._controller(
            list_stdout=LIST_GENERIC_NAMES,
            props={"12": PROPS_TOUCHPAD_FULL, "13": PROPS_ACCEL_ONLY},
        )
        infos = controller.probe_pointers()
        by_kind = {info.kind for info in infos}
        self.assertIn(PointerKind.TOUCHPAD, by_kind)
        # Generic-name device with only accel capability is a relative
        # pointer classified without any exact-name match.
        self.assertTrue(
            PointerKind.MOUSE in by_kind or PointerKind.OTHER_RELATIVE in by_kind
        )
        for info in infos:
            self.assertNotIn("Generic", info.label)

    def test_semantic_touchpad_mouse_classification(self) -> None:
        controller, _ = self._controller()
        infos = controller.probe_pointers()
        kinds = sorted(info.kind.value for info in infos)
        self.assertIn(PointerKind.TOUCHPAD.value, kinds)
        self.assertIn(PointerKind.MOUSE.value, kinds)

    def test_correct_speed_source_per_kind(self) -> None:
        controller, runner = self._controller()
        result = controller.apply_pointer_settings(
            _settings(touchpad_speed=-0.25, mouse_speed=0.5)
        )
        self.assertTrue(result.applied)
        self.assertIn(
            ("xinput", "set-prop", "12", "libinput Accel Speed", "-0.25"),
            runner.commands,
        )
        self.assertIn(
            ("xinput", "set-prop", "13", "libinput Accel Speed", "0.50"),
            runner.commands,
        )

    def test_no_ctm_command_during_ordinary_apply(self) -> None:
        controller, runner = self._controller()
        controller.apply_pointer_settings(_settings())
        self.assertFalse(
            any("Coordinate Transformation Matrix" in cmd for cmd in runner.commands)
        )
        controller.apply(_settings())
        self.assertFalse(
            any("Coordinate Transformation Matrix" in cmd for cmd in runner.commands)
        )

    def test_tap_applies_only_when_supported(self) -> None:
        controller, runner = self._controller(
            props={"12": PROPS_ACCEL_ONLY, "13": PROPS_MOUSE_FULL}
        )
        # Device 12 is name-hint touchpad but reports no tapping capability.
        controller.apply_pointer_settings(_settings(touchpad_tap=True))
        tap_commands = [cmd for cmd in runner.commands if "libinput Tapping Enabled" in cmd]
        self.assertEqual(tap_commands, [])

    def test_tap_follows_settings_when_supported(self) -> None:
        controller, runner = self._controller()
        controller.apply_pointer_settings(_settings(touchpad_tap=True))
        self.assertIn(
            ("xinput", "set-prop", "12", "libinput Tapping Enabled", "1"),
            runner.commands,
        )

    def test_disable_while_typing_follows_settings(self) -> None:
        controller, runner = self._controller()
        controller.apply_pointer_settings(_settings(disable_while_typing=True))
        self.assertIn(
            ("xinput", "set-prop", "12", "libinput Disable While Typing Enabled", "1"),
            runner.commands,
        )
        controller2, runner2 = self._controller()
        controller2.apply_pointer_settings(_settings(disable_while_typing=False))
        self.assertIn(
            ("xinput", "set-prop", "12", "libinput Disable While Typing Enabled", "0"),
            runner2.commands,
        )

    def test_natural_scrolling_shared_across_kinds_where_supported(self) -> None:
        controller, runner = self._controller()
        controller.apply_pointer_settings(_settings(natural_scrolling=True))
        self.assertIn(
            ("xinput", "set-prop", "12", "libinput Natural Scrolling Enabled", "1"),
            runner.commands,
        )
        self.assertIn(
            ("xinput", "set-prop", "13", "libinput Natural Scrolling Enabled", "1"),
            runner.commands,
        )
        controller2, runner2 = self._controller()
        controller2.apply_pointer_settings(_settings(natural_scrolling=False))
        self.assertIn(
            ("xinput", "set-prop", "13", "libinput Natural Scrolling Enabled", "0"),
            runner2.commands,
        )

    def test_missing_optional_property_is_nonfatal(self) -> None:
        controller, runner = self._controller(
            props={"12": PROPS_ACCEL_ONLY, "13": ""}
        )
        result = controller.apply_pointer_settings(_settings())
        self.assertTrue(result.applied)

    def test_real_set_prop_failure_is_reported(self) -> None:
        controller, runner = self._controller(
            fail_set_props=(("xinput", "set-prop", "13", "libinput Accel Speed", "0.50"),)
        )
        result = controller.apply_pointer_settings(
            _settings(touchpad_speed=-0.25, mouse_speed=0.5)
        )
        self.assertFalse(result.applied)

    def test_numeric_ids_never_leave_adapter(self) -> None:
        controller, _ = self._controller()
        for info in controller.probe_pointers():
            self.assertFalse(hasattr(info, "device_id"))
            self.assertNotIn("12", info.label)
            self.assertNotIn("13", info.label)

    def test_no_touchpad_stays_operable(self) -> None:
        controller, _ = self._controller(
            list_stdout="↳ Generic Mouse Device id=13 [slave  pointer  (2)]\n",
            props={"13": PROPS_MOUSE_FULL},
        )
        infos = controller.probe_pointers()
        self.assertTrue(all(info.kind is not PointerKind.TOUCHPAD for info in infos))
        result = controller.apply_pointer_settings(_settings())
        self.assertTrue(result.applied)

    def test_no_mouse_stays_operable(self) -> None:
        controller, _ = self._controller(
            list_stdout="↳ Generic Touchpad Device id=12 [slave  pointer  (2)]\n",
            props={"12": PROPS_TOUCHPAD_FULL},
        )
        infos = controller.probe_pointers()
        self.assertTrue(all(info.kind is PointerKind.TOUCHPAD for info in infos))
        result = controller.apply_pointer_settings(_settings())
        self.assertTrue(result.applied)

    def test_list_failure_fails_soft(self) -> None:
        runner = _ConfigurableRunner(
            xrandr_stdout=XRANDR_OK_MM, list_stdout="", list_rc=1
        )
        controller = LegacyXHardwareSessionController(runner)
        self.assertEqual(controller.probe_pointers(), ())
        result = controller.apply_pointer_settings(_settings())
        self.assertTrue(result.applied)
        self.assertIn("No pointer devices were detected.", result.messages)

    def test_list_props_failure_falls_back_to_name_hint(self) -> None:
        controller, _ = self._controller(props_rc={"12": 1, "13": 1})
        infos = controller.probe_pointers()
        kinds = {info.kind for info in infos}
        self.assertIn(PointerKind.TOUCHPAD, kinds)
        self.assertIn(PointerKind.MOUSE, kinds)
        result = controller.apply_pointer_settings(_settings())
        self.assertTrue(result.applied)

    def test_pointer_preview_runs_no_display_commands(self) -> None:
        controller, runner = self._controller()
        controller.apply_pointer_settings(_settings())
        self.assertFalse(any("--output" in cmd for cmd in runner.commands))
        self.assertFalse(any("--mode" in cmd for cmd in runner.commands))
        self.assertFalse(any("--auto" in cmd for cmd in runner.commands))
        kinds = [cmd[0] for cmd in runner.commands]
        self.assertNotIn("setxkbmap", kinds)
        self.assertNotIn("amixer", kinds)


if __name__ == "__main__":
    unittest.main()

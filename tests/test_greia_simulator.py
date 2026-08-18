from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher.child_shell import GreiaChildShell, ProfileVisualActivitySupervisor
from greia_launcher.runtime_adapter import PythonRuntimeAdapter
from greia_platform.activities import ActivityManifest
from greia_simulator.child_shell import GreiaSimulatorChildShell
from greia_simulator.device import DEFAULT_CAPABILITIES, SimulatedDeviceProfile, parse_viewport
from greia_simulator.python_activity import normalize_display_request
from greia_simulator.runtime import SimulatorActivitySupervisor, SimulatorPythonRuntimeAdapter
from greia_simulator.workspace import SimulatorWorkspace


class GreiaSimulatorDeviceTests(unittest.TestCase):
    def test_viewport_parser_and_bounds(self) -> None:
        self.assertEqual(parse_viewport("1024x600"), (1024, 600))
        self.assertEqual(parse_viewport(" 1280X800 "), (1280, 800))
        for invalid in ("1024", "x600", "12x12", "9000x600", "hello"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                parse_viewport(invalid)

    def test_hal_uses_real_capability_vocabulary(self) -> None:
        device = SimulatedDeviceProfile(
            1024,
            600,
            frozenset({"display", "keyboard", "controller", "audio.basic"}),
        )
        hal = device.to_hal()
        display = hal.display.probe()
        input_state = hal.input.probe()
        self.assertEqual(display.modes[0].mode_id, "1024x600")
        self.assertTrue(input_state.keyboard)
        self.assertTrue(input_state.controller)
        self.assertFalse(input_state.pointer)
        self.assertTrue(hal.audio.probe().basic_output)
        self.assertFalse(hal.network.probe().service_available)

    def test_display_capability_is_required(self) -> None:
        with self.assertRaises(ValueError):
            SimulatedDeviceProfile(1024, 600, frozenset({"keyboard"}))


class GreiaSimulatorRuntimeTests(unittest.TestCase):
    def test_pygame_request_is_forced_to_synthetic_viewport(self) -> None:
        size, flags = normalize_display_request(
            (0, 0),
            0b1111,
            target_size=(1366, 768),
            fullscreen_flag=0b0100,
        )
        self.assertEqual(size, (1366, 768))
        self.assertEqual(flags, 0b1011)

    def test_python_adapter_uses_simulator_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entrypoint = root / "main.py"
            entrypoint.write_text("pass\n", encoding="utf-8")
            manifest = ActivityManifest(
                activity_id="org.example.simulated",
                legacy_ids=(),
                title_key="activity.example.title",
                version="1.0.0",
                runtime_type="python",
                api_version="0.1",
                entrypoint=Path("main.py"),
                icon_id="robot",
                categories=("test",),
                skills=(),
                events=(),
                difficulty=1,
                languages=("*",),
                required_capabilities=("display",),
                optional_capabilities=(),
                requested_permissions=(),
                storage_schema_version=1,
                root=root,
            )
            adapter = SimulatorPythonRuntimeAdapter(python_executable=Path("/python"))
            command = adapter.command_for(manifest)
            self.assertEqual(
                command.command[:3],
                ("/python", "-m", "greia_simulator.python_activity"),
            )
            self.assertEqual(command.command[-1], str(entrypoint))
            self.assertEqual(command.cwd, root)

    def test_simulator_extends_canonical_runtime_and_shell_seams(self) -> None:
        self.assertTrue(issubclass(SimulatorPythonRuntimeAdapter, PythonRuntimeAdapter))
        self.assertTrue(
            issubclass(SimulatorActivitySupervisor, ProfileVisualActivitySupervisor)
        )
        self.assertTrue(issubclass(GreiaSimulatorChildShell, GreiaChildShell))

    def test_first_party_activities_have_no_simulator_specific_behavior(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        violations: list[str] = []
        for path in sorted((repo / "activities").glob("*/**/*.py")):
            source = path.read_text(encoding="utf-8")
            if "GREIA_SIMULATOR" in source or "greia_simulator" in source:
                violations.append(str(path.relative_to(repo)))
        self.assertEqual(
            violations,
            [],
            "Activity source must not branch/import on simulator identity: "
            + ", ".join(violations),
        )


class GreiaSimulatorWorkspaceTests(unittest.TestCase):
    def test_environment_uses_isolated_state_and_real_repo_root(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            workspace = SimulatorWorkspace(repo, Path(directory) / "state")
            environment = workspace.environment(
                SimulatedDeviceProfile(1024, 600, DEFAULT_CAPABILITIES)
            )
            self.assertEqual(Path(environment["GREIA_OS_ROOT"]), repo.resolve())
            self.assertTrue(
                environment["GREIA_DEVELOPER_ACTIVITY_ROOT"].startswith(directory)
            )
            self.assertEqual(environment["GREIA_SIMULATOR_VIEWPORT"], "1024x600")
            self.assertEqual(environment["GREIA_SIMULATOR"], "1")

    def test_environment_parses_back_to_same_device(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            workspace = SimulatorWorkspace(repo, Path(directory) / "state")
            device = SimulatedDeviceProfile(
                1280,
                800,
                frozenset({"display", "pointer", "touch"}),
            )
            environment = workspace.environment(device)
            with mock.patch.dict(os.environ, environment, clear=False):
                loaded = SimulatedDeviceProfile.from_environment()
            self.assertEqual(loaded, device)

    def test_workspace_must_live_outside_source_checkout(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with self.assertRaises(ValueError):
            SimulatorWorkspace(repo, repo / ".simulator-state")


if __name__ == "__main__":
    unittest.main()

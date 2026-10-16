from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
_src = str(REPO / "src")
if sys.path[:1] != [_src]:
    if _src in sys.path:
        sys.path.remove(_src)
    sys.path.insert(0, _src)

import greia_simulator.workspace as simulator_workspace
from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.composition import build_launcher_runtime_services
from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeUnavailableError,
)
from greia_platform.activities import (
    ActivityManifest,
    ActivityRegistry,
    RuntimeCatalogue,
)
from greia_platform.permissions import PermissionDecisionError
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.ui_preferences import UiPreferencesStore
from greia_simulator.app import SimulatorDesktopApp
from greia_simulator.child_shell import GreiaSimulatorChildShell
from greia_simulator.volume import simulated_volume_budget
from greia_simulator.device import (
    DEFAULT_CAPABILITIES,
    HAL_SIMULATABLE_CAPABILITIES,
    VIEWPORT_PRESETS,
    SimulatedDeviceProfile,
    canonical_capability_choices,
    parse_viewport,
)
from greia_simulator.python_activity import normalize_display_request, run_activity
from greia_simulator.runtime import SimulatorPythonRuntimeAdapter
from greia_simulator.workspace import SimulatorWorkspace
from simulator_supervision import (
    load_tolerant_supervisor,
    reap_on_cleanup,
    stop_gracefully,
    wait_until_ready,
)


REPO = Path(__file__).resolve().parents[1]


def _write_activity(
    root: Path,
    *,
    activity_id: str = "org.example.simulated",
    runtime_type: str = "python",
    required: tuple[str, ...] = ("display",),
    body: str = "pass\n",
    version: str = "1.0.0",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    requirements = ", ".join(f'"{item}"' for item in required)
    root.joinpath("activity.toml").write_text(
        f'''[activity]
id = "{activity_id}"
legacy_ids = []
title_key = "Example Activity"
version = "{version}"
icon = "robot"
languages = ["*"]

[presentation]
categories = ["play"]

[education]
categories = ["test"]
difficulty = 1
skills = [{{ id = "test.skill", weight = 1 }}]
events = [{{ id = "probe.completed", kind = "completion" }}]

[runtime]
type = "{runtime_type}"
api_version = "0.1"
entrypoint = "main.py"

[input]
profile = "hybrid"

[requirements]
required_capabilities = [{requirements}]
optional_capabilities = []

[permissions]
requested = []

[storage]
schema_version = 1
''',
        encoding="utf-8",
    )
    root.joinpath("main.py").write_text(body, encoding="utf-8")
    return root


def _manual_manifest(root: Path) -> ActivityManifest:
    entrypoint = root / "main.py"
    entrypoint.write_text("pass\n", encoding="utf-8")
    return ActivityManifest(
        activity_id="org.example.simulated",
        legacy_ids=(),
        title_key="Example Activity",
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


def _builtin_manifests(runtime: RuntimeCatalogue) -> tuple[ActivityManifest, ...]:
    registry = ActivityRegistry(
        (
            ActivitySource(
                REPO / "activities",
                PackageTrust.BUILT_IN,
                "greia-system",
            ),
        ),
        runtime,
    )
    return registry.discover()


def _services_for(
    runtime: RuntimeCatalogue,
    device: SimulatedDeviceProfile,
    manifests: tuple[ActivityManifest, ...],
    volume_budget=None,
):
    adapter = SimulatorPythonRuntimeAdapter(
        device,
        policy=PythonRuntimePolicy.load(REPO / "runtime" / "child-runtime.toml"),
    )
    services = build_launcher_runtime_services(
        runtime,
        manifests,
        runtime_policy_path=REPO / "runtime" / "child-runtime.toml",
        permission_policy_path=REPO / "runtime" / "permission-policy.toml",
        storage_policy_path=REPO / "runtime" / "storage-policy.toml",
        history_policy_path=REPO / "runtime" / "history-policy.toml",
        progression_policy_path=REPO / "runtime" / "progression-policy.toml",
        hal=device.to_hal(),
        volume_budget=volume_budget,
        runtime_adapters=(adapter,),
    )
    return adapter, services


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

    def test_simulator_capability_choices_are_derived_from_runtime_catalogue(self) -> None:
        runtime = RuntimeCatalogue.load(REPO / "runtime" / "child-runtime.toml")
        choices = frozenset(canonical_capability_choices(runtime.allowed_capabilities))
        self.assertEqual(choices, runtime.allowed_capabilities)
        self.assertFalse(runtime.allowed_capabilities - HAL_SIMULATABLE_CAPABILITIES)

    def test_presets_claim_geometry_only(self) -> None:
        self.assertEqual(VIEWPORT_PRESETS["Reference 1024x600"], (1024, 600))
        labels = " ".join(VIEWPORT_PRESETS).casefold()
        self.assertNotIn("acer", labels)
        self.assertNotIn("tablet", labels)
        self.assertNotIn("low-resource", labels)


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

    def test_python_adapter_wraps_canonical_command_with_absolute_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _manual_manifest(root)
            device = SimulatedDeviceProfile(1366, 768, DEFAULT_CAPABILITIES)
            canonical = PythonRuntimeAdapter(python_executable=Path("/python")).command_for(
                manifest
            )
            adapter = SimulatorPythonRuntimeAdapter(
                device,
                python_executable=Path("/python"),
            )
            command = adapter.command_for(manifest)

            self.assertEqual(command.cwd, canonical.cwd)
            self.assertEqual(command.environment, canonical.environment)
            self.assertEqual(command.command[0], canonical.command[0])
            self.assertEqual(Path(command.command[1]), adapter.bootstrap_path)
            self.assertTrue(adapter.bootstrap_path.is_absolute())
            self.assertNotIn("-m", command.command)
            self.assertEqual(command.command[2:4], ("--viewport", "1366x768"))
            self.assertEqual(command.command[-1], str(manifest.launch_path))

    def test_activity_package_cannot_shadow_trusted_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _manual_manifest(root)
            fake = root / "greia_simulator" / "python_activity.py"
            fake.parent.mkdir()
            fake.write_text("raise RuntimeError('shadowed')\n", encoding="utf-8")
            adapter = SimulatorPythonRuntimeAdapter(
                SimulatedDeviceProfile(),
                python_executable=Path("/python"),
            )
            command = adapter.command_for(manifest)
            self.assertEqual(Path(command.command[1]), adapter.bootstrap_path)
            self.assertNotEqual(Path(command.command[1]), fake)
            self.assertNotEqual(adapter.bootstrap_path.parent, root / "greia_simulator")

    def test_bootstrap_hides_simulator_identity_and_prioritizes_trusted_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            entrypoint = root / "main.py"
            entrypoint.write_text("pass\n", encoding="utf-8")
            captured: dict[str, object] = {}
            original_path = list(sys.path)

            def capture(path: str, *, run_name: str) -> None:
                captured["path"] = path
                captured["run_name"] = run_name
                captured["environment"] = dict(os.environ)
                captured["sys_path"] = list(sys.path)

            environment = {
                "GREIA_ACTIVITY_ROOT": str(root),
                "GREIA_SIMULATOR": "stale",
                "GREIA_SIMULATOR_VIEWPORT": "999x999",
            }
            try:
                with mock.patch.dict(os.environ, environment, clear=False), mock.patch(
                    "greia_simulator.python_activity.install_pygame_display_patch"
                ) as display_patch, mock.patch(
                    "greia_simulator.python_activity.runpy.run_path",
                    side_effect=capture,
                ):
                    run_activity(entrypoint, target_size=(1024, 600))
                display_patch.assert_called_once_with((1024, 600))
            finally:
                sys.path[:] = original_path

            child_environment = captured["environment"]
            assert isinstance(child_environment, dict)
            self.assertFalse(
                any(str(name).startswith("GREIA_SIMULATOR") for name in child_environment)
            )
            child_path = captured["sys_path"]
            assert isinstance(child_path, list)
            self.assertEqual(child_path[0], str(REPO / "src"))
            self.assertEqual(child_path[1], str(root))

    def test_simulator_does_not_replace_shell_authority_methods(self) -> None:
        self.assertTrue(issubclass(SimulatorPythonRuntimeAdapter, PythonRuntimeAdapter))
        self.assertTrue(issubclass(GreiaSimulatorChildShell, GreiaChildShell))
        self.assertNotIn("_rebuild_runtime_services", GreiaSimulatorChildShell.__dict__)
        self.assertNotIn("_draw", GreiaSimulatorChildShell.__dict__)
        self.assertIn("_rebuild_runtime_services", GreiaChildShell.__dict__)

    def test_simulator_uses_shared_display_policy_hooks(self) -> None:
        shell = object.__new__(GreiaSimulatorChildShell)
        shell.simulated_device = SimulatedDeviceProfile(1111, 700, DEFAULT_CAPABILITIES)
        pygame = SimpleNamespace(RESIZABLE=0x10)
        event = SimpleNamespace(size=(700, 400))
        self.assertEqual(shell._initial_display_request(pygame), ((1111, 700), 0x10))
        self.assertEqual(shell._resize_display_request(event, pygame), ((1111, 700), 0x10))
        self.assertIn("1111x700", shell._display_caption())

    def test_first_party_activities_have_no_simulator_specific_behavior(self) -> None:
        violations: list[str] = []
        for path in sorted((REPO / "activities").glob("*/**/*.py")):
            source = path.read_text(encoding="utf-8")
            if "GREIA_SIMULATOR" in source or "greia_simulator" in source:
                violations.append(str(path.relative_to(REPO)))
        self.assertEqual(
            violations,
            [],
            "Activity source must not branch/import on simulator identity: "
            + ", ".join(violations),
        )


class GreiaSimulatorWorkspaceTests(unittest.TestCase):
    def test_environment_uses_only_normal_greia_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = SimulatorWorkspace(REPO, Path(directory) / "state")
            environment = workspace.environment()
            self.assertEqual(Path(environment["GREIA_OS_ROOT"]), REPO.resolve())
            self.assertTrue(
                environment["GREIA_DEVELOPER_ACTIVITY_ROOT"].startswith(
                    str(Path(directory).resolve())
                )
            )
            self.assertFalse(
                any(name.startswith("GREIA_SIMULATOR") for name in environment)
            )

    def test_workspace_must_live_outside_source_checkout(self) -> None:
        with self.assertRaises(ValueError):
            SimulatorWorkspace(REPO, REPO / ".simulator-state")

    def test_workspace_is_bound_to_checkout_and_rebind_requires_writer_lease(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            state = base / "state"
            first = SimulatorWorkspace(REPO, state)
            first.ensure()

            other_repo = base / "other-greia"
            (other_repo / "runtime").mkdir(parents=True)
            (other_repo / "runtime" / "child-runtime.toml").write_bytes(
                (REPO / "runtime" / "child-runtime.toml").read_bytes()
            )
            second = SimulatorWorkspace(other_repo, state)
            with self.assertRaisesRegex(RuntimeError, "another Greia checkout"):
                second.ensure()
            with self.assertRaisesRegex(RuntimeError, "active writer lock"):
                second.ensure(allow_repo_rebind=True)

            second.acquire_lock(allow_repo_rebind=True)
            try:
                metadata = json.loads(second.metadata_path.read_text(encoding="utf-8"))
                self.assertEqual(metadata["repo_root"], str(other_repo.resolve()))
            finally:
                second.release_lock()

    def test_workspace_single_writer_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            first = SimulatorWorkspace(REPO, state)
            second = SimulatorWorkspace(REPO, state)
            first.acquire_lock()
            try:
                with self.assertRaisesRegex(RuntimeError, "already in use"):
                    second.acquire_lock()
            finally:
                first.release_lock()
            second.acquire_lock()
            second.release_lock()

    def test_workspace_release_requires_child_lease_to_be_cleared(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = SimulatorWorkspace(REPO, Path(directory) / "state")
            workspace.acquire_lock()
            workspace.update_lock_child_pid(os.getpid())
            with self.assertRaisesRegex(RuntimeError, "owned Shell"):
                workspace.release_lock()
            workspace.update_lock_child_pid(None)
            workspace.release_lock()

    def test_stale_lock_is_retained_while_recorded_shell_pid_is_alive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = SimulatorWorkspace(REPO, Path(directory) / "state")
            workspace.ensure()
            workspace.lock_path.write_text(
                json.dumps(
                    {
                        "pid": 111,
                        "child_pid": 222,
                        "repo_root": str(REPO.resolve()),
                        "schema_version": 1,
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(simulator_workspace.os, "name", "posix"), mock.patch.object(
                simulator_workspace,
                "_posix_pid_alive",
                side_effect=(False, True),
            ):
                self.assertFalse(workspace._discard_stale_lock())
            self.assertTrue(workspace.lock_path.exists())

            with mock.patch.object(simulator_workspace.os, "name", "posix"), mock.patch.object(
                simulator_workspace,
                "_posix_pid_alive",
                side_effect=(False, False),
            ):
                self.assertTrue(workspace._discard_stale_lock())
            self.assertFalse(workspace.lock_path.exists())

    def test_partial_or_malformed_lock_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = SimulatorWorkspace(REPO, Path(directory) / "state")
            workspace.ensure()
            workspace.lock_path.write_text("{", encoding="utf-8")
            with mock.patch.object(simulator_workspace.os, "name", "posix"), mock.patch.object(
                simulator_workspace,
                "_posix_pid_alive",
            ) as pid_probe:
                self.assertFalse(workspace._discard_stale_lock())
                pid_probe.assert_not_called()
            self.assertEqual(workspace.lock_path.read_text(encoding="utf-8"), "{")

    def test_non_posix_stale_lock_probe_fails_closed_without_pid_probe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = SimulatorWorkspace(REPO, Path(directory) / "state")
            workspace.ensure()
            workspace.lock_path.write_text(
                json.dumps(
                    {
                        "pid": 12345,
                        "child_pid": None,
                        "repo_root": str(REPO.resolve()),
                        "schema_version": 1,
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(simulator_workspace.os, "name", "nt"), mock.patch.object(
                simulator_workspace,
                "_posix_pid_alive",
            ) as pid_probe:
                self.assertFalse(workspace._discard_stale_lock())
                pid_probe.assert_not_called()
            self.assertTrue(workspace.lock_path.exists())

    def test_profile_interface_size_uses_real_store_and_named_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = SimulatorWorkspace(REPO, Path(directory) / "state")
            profiles = workspace.profiles()
            profile = profiles[0]
            result = workspace.set_interface_size(profile.profile_id, "large")
            self.assertEqual(result.value, "large")
            context = workspace.profile_store().context(profile.profile_id)
            persisted = UiPreferencesStore(context.customization_dir).read()
            self.assertEqual(persisted.interface_size.value, "large")

    def test_load_activity_is_canonical_developer_registration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(REPO, base / "state")
            source = _write_activity(base / "source")
            registration = workspace.load_activity(source)
            self.assertEqual(registration.package_trust, PackageTrust.DEVELOPER_UNSIGNED)
            self.assertEqual(registration.source_id, "greia-developer-remote")
            self.assertEqual(registration.manifest.activity_id, "org.example.simulated")
            self.assertTrue(registration.manifest.root.is_relative_to(workspace.developer_root))

    def test_load_activity_rejects_builtin_identity_collision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(REPO, base / "state")
            source = _write_activity(
                base / "source",
                activity_id="org.greia.shape-garden",
            )
            with self.assertRaises(ValueError):
                workspace.load_activity(source)

    def test_load_activity_rejects_source_state_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            state = base / "state"
            workspace = SimulatorWorkspace(REPO, state)
            workspace.ensure()
            _write_activity(state / "inside")
            with self.assertRaisesRegex(ValueError, "overlap"):
                workspace.load_activity(state / "inside")
            _write_activity(base)
            with self.assertRaisesRegex(ValueError, "overlap"):
                workspace.load_activity(base)

    @unittest.skipUnless(hasattr(os, "symlink"), "host has no symlink support")
    def test_load_activity_rejects_file_and_directory_symlinks_before_copy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(REPO, base / "state")
            outside = base / "outside.txt"
            outside.write_text("secret", encoding="utf-8")

            file_source = _write_activity(base / "file-source")
            os.symlink(outside, file_source / "escape.txt")
            with self.assertRaisesRegex(ValueError, "symlinks are forbidden"):
                workspace.load_activity(file_source)

            dir_source = _write_activity(
                base / "dir-source",
                activity_id="org.example.dirlink",
            )
            target_dir = base / "outside-dir"
            target_dir.mkdir()
            (target_dir / "payload.txt").write_text("outside", encoding="utf-8")
            os.symlink(target_dir, dir_source / "linked-dir")
            with self.assertRaisesRegex(ValueError, "symlinks are forbidden"):
                workspace.load_activity(dir_source)

    def test_oversize_source_is_rejected_before_staging_copy(self) -> None:
        runtime = RuntimeCatalogue.load(REPO / "runtime" / "child-runtime.toml")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(REPO, base / "state")
            source = _write_activity(base / "source")
            with (source / "huge.dat").open("wb") as handle:
                handle.truncate(runtime.maximum_activity_bytes + 1)
            with self.assertRaisesRegex(ValueError, "exceeds"):
                workspace.load_activity(source)
            self.assertEqual(tuple(workspace.state_root.glob("greia-simulator-load-*")), ())

    def test_snapshot_digest_rejects_same_metadata_different_content(self) -> None:
        runtime = RuntimeCatalogue.load(REPO / "runtime" / "child-runtime.toml")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(REPO, base / "state")
            workspace.ensure()
            source = _write_activity(base / "source", body="VALUE = 'old'\n")
            snapshot = workspace._inspect_development_tree(source, runtime)
            entrypoint = source / "main.py"
            original = entrypoint.stat()
            replacement = "VALUE = 'new'\n"
            self.assertEqual(len(replacement.encode("utf-8")), original.st_size)
            entrypoint.write_text(replacement, encoding="utf-8")
            os.utime(
                entrypoint,
                ns=(original.st_atime_ns, original.st_mtime_ns),
            )
            with self.assertRaisesRegex(ValueError, "changed while staging"):
                workspace._copy_development_snapshot(
                    source,
                    workspace.state_root / "digest-staging",
                    snapshot,
                    runtime,
                )

    def test_failed_final_publication_restores_previous_valid_activity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(REPO, base / "state")
            source = _write_activity(base / "source", body="VALUE = 'old'\n")
            first = workspace.load_activity(source)
            destination = first.manifest.root
            self.assertIn("old", (destination / "main.py").read_text(encoding="utf-8"))

            (source / "main.py").write_text("VALUE = 'new'\n", encoding="utf-8")
            original = ActivityRegistry.discover_registrations
            calls = {"count": 0}

            def fail_final(registry_self):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise ValueError("forced final validation failure")
                return original(registry_self)

            with mock.patch.object(
                ActivityRegistry,
                "discover_registrations",
                autospec=True,
                side_effect=fail_final,
            ):
                with self.assertRaisesRegex(ValueError, "forced final"):
                    workspace.load_activity(source)

            self.assertIn("old", (destination / "main.py").read_text(encoding="utf-8"))

    def test_package_install_delegates_to_canonical_service_when_available(self) -> None:
        try:
            import greia_platform.activity_packages as package_module
        except ImportError:
            self.skipTest("canonical package service is unavailable on this host")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(REPO, base / "state")
            archive = base / "test.greiaactivity"
            archive.write_bytes(b"placeholder")
            receipt = object()
            with mock.patch.object(package_module, "ActivityPackageService") as service_class:
                service_class.return_value.install_archive.return_value = receipt
                self.assertIs(workspace.install_activity_package(archive), receipt)
                service_class.assert_called_once_with(
                    state_root=workspace.package_root,
                    runtime_catalogue=REPO / "runtime" / "child-runtime.toml",
                    built_in_root=REPO / "activities",
                )
                service_class.return_value.install_archive.assert_called_once_with(archive)


class GreiaSimulatorDesktopOwnershipTests(unittest.TestCase):
    @staticmethod
    def _app(process=None):
        app = object.__new__(SimulatorDesktopApp)
        app.workspace = mock.Mock()
        app.workspace.repo_root = REPO
        app.process = process
        app._stopping = False
        app.status = mock.Mock()
        return app

    def test_start_registers_spawned_shell_pid_in_workspace_lease(self) -> None:
        app = self._app()
        app._device = mock.Mock(return_value=SimulatedDeviceProfile())
        app.interface_size = mock.Mock()
        app.interface_size.get.return_value = "normal"
        app._refresh_profiles = mock.Mock()
        app._selected_profile_id = mock.Mock(return_value="profile-id")
        app.stop = mock.Mock(return_value=True)
        app._child_command = mock.Mock(return_value=["child-shell"])
        app._child_environment = mock.Mock(return_value={})
        process = mock.Mock(pid=4242)

        tkinter_module = ModuleType("tkinter")
        messagebox_module = ModuleType("tkinter.messagebox")
        messagebox_module.showerror = mock.Mock()
        tkinter_module.messagebox = messagebox_module
        with mock.patch.dict(
            sys.modules,
            {
                "tkinter": tkinter_module,
                "tkinter.messagebox": messagebox_module,
            },
        ), mock.patch(
            "greia_simulator.app.subprocess.Popen",
            return_value=process,
        ):
            app.start()

        self.assertIs(app.process, process)
        app.workspace.update_lock_child_pid.assert_called_once_with(4242)

    def test_stop_clears_child_lease_before_dropping_exited_handle(self) -> None:
        process = mock.Mock()
        process.poll.return_value = 0
        app = self._app(process)
        self.assertTrue(app.stop())
        app.workspace.update_lock_child_pid.assert_called_once_with(None)
        self.assertIsNone(app.process)

    def test_stop_retains_live_handle_when_terminate_fails(self) -> None:
        process = mock.Mock()
        process.poll.side_effect = (None, None)
        process.terminate.side_effect = OSError("terminate failed")
        app = self._app(process)
        self.assertFalse(app.stop())
        self.assertIs(app.process, process)
        app.workspace.update_lock_child_pid.assert_not_called()

    def test_stop_fails_closed_when_dead_child_lease_cannot_be_cleared(self) -> None:
        process = mock.Mock()
        process.poll.return_value = 0
        app = self._app(process)
        app.workspace.update_lock_child_pid.side_effect = RuntimeError("lease write failed")
        self.assertFalse(app.stop())
        self.assertIs(app.process, process)


class GreiaSimulatorAuthorityIntegrationTests(unittest.TestCase):
    def test_canonical_composition_uses_injected_adapter_and_denies_missing_capability(self) -> None:
        runtime = RuntimeCatalogue.load(REPO / "runtime" / "child-runtime.toml")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(REPO, base / "state")
            registration = workspace.load_activity(
                _write_activity(base / "source", required=("display", "touch"))
            )
            device = SimulatedDeviceProfile(
                1024,
                600,
                frozenset({"display", "keyboard", "pointer"}),
            )
            manifests = (*_builtin_manifests(runtime), registration.manifest)
            adapter, services = _services_for(runtime, device, manifests)
            self.assertIs(services.runtime_manager.adapter_for("python"), adapter)
            with self.assertRaises(PermissionDecisionError):
                services.permission_broker.issue(registration)

    def test_valid_but_unavailable_runtime_is_registry_valid_and_runtime_unavailable(self) -> None:
        runtime = RuntimeCatalogue.load(REPO / "runtime" / "child-runtime.toml")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(REPO, base / "state")
            registration = workspace.load_activity(
                _write_activity(base / "source", runtime_type="web")
            )
            device = SimulatedDeviceProfile()
            manifests = (*_builtin_manifests(runtime), registration.manifest)
            _, services = _services_for(runtime, device, manifests)
            authority = services.permission_broker.issue(registration)
            self.assertEqual(authority.activity_id, registration.manifest.activity_id)
            with self.assertRaises(RuntimeUnavailableError):
                services.runtime_manager.prepare_launch(
                    registration.manifest,
                    expected_device_snapshot_token=authority.device_snapshot_token,
                )

    def test_bounded_shutdown_uses_normal_supervisor_path(self) -> None:
        shell = object.__new__(GreiaSimulatorChildShell)
        session = object()
        result = object()
        supervisor = mock.Mock()
        supervisor.active_session = session
        supervisor.request_stop.return_value = result
        shell.supervisor = supervisor
        shell._shutdown_active_bounded()
        supervisor.request_stop.assert_called_once_with(session)
        supervisor.force_stop.assert_not_called()

    def test_bounded_shutdown_escalates_through_supervisor_not_process_kill(self) -> None:
        shell = object.__new__(GreiaSimulatorChildShell)
        session = object()
        supervisor = mock.Mock()
        supervisor.active_session = session
        supervisor.request_stop.return_value = None
        supervisor.poll.return_value = None
        supervisor.force_stop.return_value = None
        shell.supervisor = supervisor
        with mock.patch(
            "greia_simulator.child_shell.time.monotonic",
            side_effect=(0.0, 2.0, 2.0, 3.0),
        ), mock.patch("greia_simulator.child_shell.time.sleep"):
            shell._shutdown_active_bounded()
        supervisor.force_stop.assert_called_once()
        self.assertEqual(supervisor.force_stop.call_args.args[0], session)

    @unittest.skipUnless(
        os.name == "posix" and importlib.util.find_spec("pygame") is not None,
        "POSIX + Pygame are required for real simulator broker/lifecycle integration",
    )
    def test_real_python_activity_ready_storage_event_history_and_stop(self) -> None:
        runtime = RuntimeCatalogue.load(REPO / "runtime" / "child-runtime.toml")
        body = '''from greia_platform.activity_api import (
    activity_stop_requested, emit_activity_event, get_storage, mark_activity_ready
)
import pygame
import time

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
screen.fill((255, 255, 255))
pygame.display.flip()
get_storage().kv_set("probe", {"ok": True})
emit_activity_event("probe.completed", idempotency_key="probe-1")
mark_activity_ready()
while not activity_stop_requested():
    time.sleep(0.02)
pygame.quit()
'''
        # Honor $TMPDIR (never pin to /tmp): the Acer device host mounts /tmp
        # as a 64 MiB tmpfs while storage policy keeps a 64 MiB protected
        # free-space reserve, so any profile write under /tmp is refused with
        # quota_exceeded there. Device runs set TMPDIR to a /dev/sda1-backed
        # workspace directory where the reserve holds.
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            workspace = SimulatorWorkspace(REPO, base / "state")
            registration = workspace.load_activity(_write_activity(base / "source", body=body))
            device = SimulatedDeviceProfile(640, 480, DEFAULT_CAPABILITIES)
            manifests = (*_builtin_manifests(runtime), registration.manifest)
            # Model the simulated device volume, not this host's disk fullness.
            _, services = _services_for(
                runtime,
                device,
                manifests,
                volume_budget=simulated_volume_budget(workspace.profiles_root),
            )
            profile = workspace.profile_store().context(workspace.profiles()[0].profile_id)
            authority = services.permission_broker.issue(registration)
            supervisor = load_tolerant_supervisor(
                runtime_manager=services.runtime_manager,
                storage_service=services.storage_service,
                history_service=services.history_service,
                display_coordinator=None,
            )
            environment = workspace.environment()
            environment.update(
                {
                    "SDL_VIDEODRIVER": "dummy",
                    "PYGAME_HIDE_SUPPORT_PROMPT": "1",
                }
            )
            with mock.patch.dict(os.environ, environment, clear=False):
                session = supervisor.start(registration.manifest, profile, authority)
                reap_on_cleanup(self, supervisor, session)
                wait_until_ready(self, supervisor, session)
                stop_gracefully(self, supervisor, session)

            storage = services.storage_service.open(
                profile,
                registration.manifest.activity_id,
                schema_version=registration.manifest.storage_schema_version,
                package_version=registration.manifest.version,
            )
            self.assertEqual(storage.kv_get("probe"), {"ok": True})
            history = services.history_service.open(profile).export_state()
            events = history["events"]
            sessions = history["sessions"]
            assert isinstance(events, list)
            assert isinstance(sessions, list)
            self.assertTrue(
                any(
                    event.get("activity_id") == registration.manifest.activity_id
                    and event.get("event_id") == "probe.completed"
                    for event in events
                )
            )
            self.assertTrue(
                any(
                    item.get("activity_id") == registration.manifest.activity_id
                    and item.get("ready") is True
                    and item.get("ended_at") is not None
                    for item in sessions
                )
            )


if __name__ == "__main__":
    unittest.main()

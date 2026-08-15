from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from greia_launcher.display_session import (
    DisplaySessionCoordinator,
    DisplaySessionPhase,
    DisplayTransport,
    DisplayTransportKind,
)
from greia_launcher.lifecycle import ActivityExitReason, ActivitySessionState
from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    RuntimeLifecycleBinding,
    RuntimeManager,
)
from greia_launcher.supervisor import ActivitySupervisor
from greia_platform.activities import ActivityManifest, SkillContribution
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.trust import PackageTrust


@dataclass(frozen=True)
class _Profile:
    profile_id: str = "0123456789abcdef0123456789abcdef"
    display_name: str = "Mia"
    avatar_id: str = "unicorn"


class _ProfileContext:
    def __init__(self, root: Path):
        self.root = root
        self.profile = _Profile()
        self.customization_dir = root / "customization"
        self.customization_dir.mkdir(parents=True, exist_ok=True)

    def activity_data_dir(self, activity_id: str) -> Path:
        path = self.root / "activities" / activity_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class _Authority:
    def __init__(self, activity_id: str):
        capabilities = {"display", "pointer"}
        self.activity_id = activity_id
        self.package_digest = "a" * 64
        self.package_trust = PackageTrust.BUILT_IN
        self.device_snapshot_token = DeviceCapabilityService.static(
            capabilities, source_id="display-session-test"
        ).snapshot().token
        self.effective_capabilities = frozenset(capabilities)
        self.sdk_features = self.effective_capabilities

    def has_capability(self, capability: str) -> bool:
        return capability in self.effective_capabilities

    def has_permission(self, permission: str) -> bool:
        return False


class _FakeProcess:
    def __init__(self):
        self.pid = 424242
        self.returncode: int | None = None
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


class _DisplayBackend:
    backend_id = "test-wayland-session"
    transport_kind = DisplayTransportKind.WAYLAND

    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self.fail_present = False
        self.fail_restore = False

    def prepare_activity(self, session_id: str) -> DisplayTransport:
        self.calls.append(("prepare", session_id))
        return DisplayTransport(
            kind=DisplayTransportKind.WAYLAND,
            sdl_video_driver="wayland",
            wayland_display="wayland-greia",
            xdg_runtime_dir="/run/greia-wayland",
        )

    def present_activity(self, session_id: str) -> None:
        self.calls.append(("present", session_id))
        if self.fail_present:
            raise RuntimeError("present failed")

    def restore_shell(self, session_id: str) -> None:
        self.calls.append(("restore", session_id))
        if self.fail_restore:
            raise RuntimeError("restore failed")


class _CollidingLifecycleAdapter(PythonRuntimeAdapter):
    def create_lifecycle_binding(
        self,
        session_id: str,
        host_activity_data: Path,
        child_activity_data: Path,
    ) -> RuntimeLifecycleBinding:
        binding = super().create_lifecycle_binding(
            session_id,
            host_activity_data,
            child_activity_data,
        )
        return RuntimeLifecycleBinding(
            control=binding.control,
            environment=(*binding.environment, ("HOME", "/forbidden-runtime-home")),
        )


def _manifest(root: Path) -> ActivityManifest:
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
    return ActivityManifest(
        activity_id="org.greia.display-session-test",
        legacy_ids=(),
        title_key="activity.test.title",
        version="0.1.0",
        runtime_type="python",
        api_version="0.1",
        entrypoint=Path("main.py"),
        icon_id="test",
        categories=("test",),
        skills=(SkillContribution("test", 1),),
        events=(),
        difficulty=1,
        languages=("en",),
        required_capabilities=("display", "pointer"),
        optional_capabilities=(),
        requested_permissions=(),
        storage_schema_version=1,
        root=root,
    )


def _manager(process_factory, *, adapter: PythonRuntimeAdapter | None = None) -> RuntimeManager:
    capabilities = {"display", "pointer"}
    return RuntimeManager(
        [
            adapter
            or PythonRuntimeAdapter(
                Path("/usr/bin/python3"),
                process_factory=process_factory,
            )
        ],
        DeviceCapabilityService.static(
            capabilities, source_id="display-session-test"
        ),
    )


class SupervisorDisplaySessionTests(unittest.TestCase):
    def _start(self, root: Path, backend: _DisplayBackend, process: _FakeProcess):
        manifest = _manifest(root / "activity")
        profile = _ProfileContext(root / "profile")
        authority = _Authority(manifest.activity_id)
        calls: list[dict[str, object]] = []

        def factory(*args, **kwargs):
            calls.append(kwargs)
            return process

        coordinator = DisplaySessionCoordinator(backend)
        supervisor = ActivitySupervisor(
            require_sandbox=False,
            runtime_manager=_manager(factory),
            display_coordinator=coordinator,
        )
        session = supervisor.start(manifest, profile, authority)
        return supervisor, coordinator, session, calls

    def test_typed_transport_replaces_stale_host_display_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                os.environ,
                {
                    "DISPLAY": ":stale",
                    "XAUTHORITY": "/tmp/stale-xauthority",
                    "WAYLAND_DISPLAY": "wayland-stale",
                    "SDL_VIDEODRIVER": "x11",
                    "XDG_RUNTIME_DIR": "/run/user/stale",
                },
                clear=False,
            ):
                backend = _DisplayBackend()
                process = _FakeProcess()
                _, _, session, calls = self._start(
                    Path(temporary), backend, process
                )
                environment = calls[0]["env"]

        self.assertEqual(session.state, ActivitySessionState.STARTING)
        self.assertNotIn("DISPLAY", environment)
        self.assertNotIn("XAUTHORITY", environment)
        self.assertEqual(environment["SDL_VIDEODRIVER"], "wayland")
        self.assertEqual(environment["WAYLAND_DISPLAY"], "wayland-greia")
        self.assertEqual(environment["XDG_RUNTIME_DIR"], "/run/greia-wayland")
        self.assertEqual(backend.calls, [("prepare", session.session_id)])

    def test_ready_presents_then_normal_exit_restores_same_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            backend = _DisplayBackend()
            process = _FakeProcess()
            supervisor, coordinator, session, _ = self._start(
                Path(temporary), backend, process
            )
            with mock.patch.object(type(session.control), "ready", return_value=True):
                self.assertIsNone(supervisor.poll(session))
            self.assertEqual(session.state, ActivitySessionState.RUNNING)
            self.assertEqual(
                coordinator.snapshot.phase, DisplaySessionPhase.ACTIVITY_VISIBLE
            )

            process.returncode = 0
            result = supervisor.poll(session)

        self.assertEqual(result.exit_reason, ActivityExitReason.NORMAL)
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(
            backend.calls,
            [
                ("prepare", session.session_id),
                ("present", session.session_id),
                ("restore", session.session_id),
            ],
        )

    def test_fast_ready_then_exit_is_recorded_without_presenting_dead_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            backend = _DisplayBackend()
            process = _FakeProcess()
            supervisor, coordinator, session, _ = self._start(
                Path(temporary), backend, process
            )
            process.returncode = 0
            with mock.patch.object(type(session.control), "ready", return_value=True):
                result = supervisor.poll(session)

        self.assertTrue(result.ready)
        self.assertEqual(result.exit_reason, ActivityExitReason.NORMAL)
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(
            backend.calls,
            [
                ("prepare", session.session_id),
                ("restore", session.session_id),
            ],
        )

    def test_presentation_failure_restores_shell_and_forces_platform_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            backend = _DisplayBackend()
            backend.fail_present = True
            process = _FakeProcess()
            supervisor, coordinator, session, _ = self._start(
                Path(temporary), backend, process
            )
            with mock.patch.object(type(session.control), "ready", return_value=True):
                result = supervisor.poll(session)

        self.assertIsNotNone(result)
        self.assertTrue(process.killed)
        self.assertEqual(result.exit_reason, ActivityExitReason.PLATFORM_FAILURE)
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(
            backend.calls,
            [
                ("prepare", session.session_id),
                ("present", session.session_id),
                ("restore", session.session_id),
            ],
        )

    def test_shell_restore_failure_turns_normal_process_exit_into_platform_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            backend = _DisplayBackend()
            process = _FakeProcess()
            supervisor, coordinator, session, _ = self._start(
                Path(temporary), backend, process
            )
            with mock.patch.object(type(session.control), "ready", return_value=True):
                self.assertIsNone(supervisor.poll(session))
            backend.fail_restore = True
            process.returncode = 0
            result = supervisor.poll(session)

        self.assertEqual(result.exit_reason, ActivityExitReason.PLATFORM_FAILURE)
        self.assertEqual(coordinator.snapshot.phase, DisplaySessionPhase.FAILED)
        self.assertIn("restore failed", coordinator.snapshot.failure or "")

    def test_process_launch_failure_restores_prepared_display_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(manifest.activity_id)
            backend = _DisplayBackend()
            coordinator = DisplaySessionCoordinator(backend)

            def fail_launch(*args, **kwargs):
                raise OSError("spawn failed")

            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager(fail_launch),
                display_coordinator=coordinator,
            )
            session = supervisor.start(manifest, profile, authority)

        self.assertEqual(session.state, ActivitySessionState.FAILED)
        self.assertEqual(session.result.exit_reason, ActivityExitReason.LAUNCH_FAILURE)
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(
            backend.calls,
            [
                ("prepare", session.session_id),
                ("restore", session.session_id),
            ],
        )

    def test_environment_collision_after_display_prepare_restores_without_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(manifest.activity_id)
            backend = _DisplayBackend()
            coordinator = DisplaySessionCoordinator(backend)
            launched: list[bool] = []

            def factory(*args, **kwargs):
                launched.append(True)
                return _FakeProcess()

            adapter = _CollidingLifecycleAdapter(
                Path("/usr/bin/python3"),
                process_factory=factory,
            )
            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager(factory, adapter=adapter),
                display_coordinator=coordinator,
            )
            session = supervisor.start(manifest, profile, authority)

        self.assertEqual(launched, [])
        self.assertEqual(session.state, ActivitySessionState.FAILED)
        self.assertEqual(session.result.exit_reason, ActivityExitReason.PLATFORM_FAILURE)
        self.assertTrue(coordinator.snapshot.shell_available)
        self.assertEqual(
            backend.calls,
            [
                ("prepare", session.session_id),
                ("restore", session.session_id),
            ],
        )


if __name__ == "__main__":
    unittest.main()

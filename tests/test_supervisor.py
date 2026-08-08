from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from greia_launcher.lifecycle import ActivityExitReason, ActivitySessionState
from greia_launcher.runtime_adapter import PythonRuntimeAdapter, RuntimeManager
from greia_launcher.supervisor import ActivityLifecycleError, ActivitySupervisor
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
    def __init__(
        self,
        activity_id: str,
        *,
        capabilities: set[str],
        permissions: set[str] | None = None,
    ):
        self.activity_id = activity_id
        self.package_digest = "a" * 64
        self.package_trust = PackageTrust.BUILT_IN
        self.device_snapshot_token = DeviceCapabilityService.static(
            capabilities, source_id="supervisor-test"
        ).snapshot().token
        self.effective_capabilities = frozenset(capabilities)
        self._permissions = frozenset(permissions or set())
        self.sdk_features = self.effective_capabilities | self._permissions

    def has_capability(self, capability: str) -> bool:
        return capability in self.effective_capabilities

    def has_permission(self, permission: str) -> bool:
        return permission in self._permissions


class _FakeProcess:
    def __init__(self):
        self.pid = 424242
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


def _manifest(root: Path, *, runtime_type: str = "python") -> ActivityManifest:
    entrypoint = Path("main.py" if runtime_type == "python" else "index.html")
    target = root / entrypoint
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("print('ok')\n" if runtime_type == "python" else "<!doctype html>\n")
    return ActivityManifest(
        activity_id="org.greia.test-activity",
        legacy_ids=(),
        title_key="activity.test.title",
        version="0.1.0",
        runtime_type=runtime_type,
        api_version="0.1",
        entrypoint=entrypoint,
        icon_id="test",
        categories=("test",),
        skills=(SkillContribution("test", 1),),
        events=(),
        difficulty=1,
        languages=("en",),
        required_capabilities=("display", "pointer"),
        optional_capabilities=("audio.basic",),
        requested_permissions=(),
        storage_schema_version=1,
        root=root,
    )


def _manager(capabilities: set[str]) -> RuntimeManager:
    return RuntimeManager(
        [PythonRuntimeAdapter(Path("/usr/bin/python3"))],
        DeviceCapabilityService.static(capabilities, source_id="supervisor-test"),
    )


class SupervisorTests(unittest.TestCase):
    def test_installed_supervisor_requires_explicit_runtime_manager(self) -> None:
        with self.assertRaisesRegex(ActivityLifecycleError, "injected HAL-backed RuntimeManager"):
            ActivitySupervisor(require_sandbox=True)

    def test_missing_required_platform_authority_fails_before_process_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(manifest.activity_id, capabilities={"display"})
            factory = mock.Mock(side_effect=AssertionError("process must not start"))
            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager({"display", "pointer"}),
                process_factory=factory,
            )
            session = supervisor.start(manifest, profile, authority)

        self.assertEqual(session.state, ActivitySessionState.FAILED)
        self.assertEqual(session.result.exit_reason, ActivityExitReason.LAUNCH_FAILURE)
        factory.assert_not_called()

    def test_stale_device_authority_fails_before_process_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id, capabilities={"display", "pointer", "audio.basic"}
            )
            factory = mock.Mock(side_effect=AssertionError("process must not start"))
            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager({"display", "pointer"}),
                process_factory=factory,
            )
            session = supervisor.start(manifest, profile, authority)

        self.assertEqual(session.state, ActivitySessionState.FAILED)
        self.assertEqual(session.result.exit_reason, ActivityExitReason.LAUNCH_FAILURE)
        factory.assert_not_called()

    def test_unavailable_runtime_is_normalized_to_launch_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity", runtime_type="web")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id, capabilities={"display", "pointer"}
            )
            factory = mock.Mock(side_effect=AssertionError("process must not start"))
            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager({"display", "pointer"}),
                process_factory=factory,
            )
            session = supervisor.start(manifest, profile, authority)

        self.assertEqual(session.state, ActivitySessionState.FAILED)
        self.assertEqual(session.result.return_code, 126)
        factory.assert_not_called()

    def test_runtime_manager_starts_child_and_ready_marker_drives_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id, capabilities={"display", "pointer"}
            )
            process = _FakeProcess()
            calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

            def factory(*args, **kwargs):
                calls.append((args, kwargs))
                return process

            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager({"display", "pointer"}),
                process_factory=factory,
            )
            session = supervisor.start(manifest, profile, authority)
            self.assertEqual(session.state, ActivitySessionState.STARTING)
            self.assertIs(supervisor.active_session, session)
            with mock.patch.object(type(session.control), "ready", return_value=True):
                self.assertIsNone(supervisor.poll(session))
            self.assertEqual(session.state, ActivitySessionState.RUNNING)
            process.returncode = 0
            result = supervisor.poll(session)

        self.assertEqual(result.exit_reason, ActivityExitReason.NORMAL)
        self.assertTrue(result.ready)
        self.assertIsNone(supervisor.active_session)
        self.assertEqual(len(calls), 1)
        command = calls[0][0][0]
        self.assertEqual(command[0], "/usr/bin/python3")
        self.assertEqual(Path(command[1]), manifest.launch_path)

    def test_only_one_activity_can_be_active(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id, capabilities={"display", "pointer"}
            )
            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager({"display", "pointer"}),
                process_factory=lambda *args, **kwargs: _FakeProcess(),
            )
            supervisor.start(manifest, profile, authority)
            with self.assertRaisesRegex(ActivityLifecycleError, "only one Activity"):
                supervisor.start(manifest, profile, authority)

    def test_environment_is_descriptive_and_drops_unapproved_host_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id,
                capabilities={"display", "pointer"},
                permissions={"profile.manage_own"},
            )
            control_root = profile.activity_data_dir(manifest.activity_id)
            from greia_launcher.lifecycle import ActivityControlChannel

            control = ActivityControlChannel.create(control_root, control_root)
            try:
                with mock.patch.dict(
                    os.environ,
                    {
                        "SECRET_SHOULD_NOT_LEAK": "nope",
                        "GREIA_ACTIVITY_CAPABILITIES": "customization.manage,network",
                    },
                    clear=False,
                ):
                    environment = ActivitySupervisor._sanitized_environment(
                        manifest, profile, authority, control
                    )
            finally:
                control.cleanup()

        self.assertNotIn("SECRET_SHOULD_NOT_LEAK", environment)
        self.assertEqual(environment["GREIA_ACTIVITY_ID"], manifest.activity_id)
        self.assertEqual(
            set(environment["GREIA_ACTIVITY_CAPABILITIES"].split(",")),
            set(authority.sdk_features),
        )
        self.assertNotIn("customization.manage", environment["GREIA_ACTIVITY_CAPABILITIES"])
        self.assertIn("GREIA_AVATAR_REQUEST_PATH", environment)
        self.assertNotIn("GREIA_CUSTOMIZATION_DIR", environment)

    def test_installed_missing_bubblewrap_fails_closed_without_starting_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id, capabilities={"display", "pointer"}
            )
            factory = mock.Mock(side_effect=AssertionError("process must not start"))
            supervisor = ActivitySupervisor(
                sandbox_executable=root / "missing-bwrap",
                require_sandbox=True,
                runtime_manager=_manager({"display", "pointer"}),
                process_factory=factory,
            )
            session = supervisor.start(manifest, profile, authority)

        self.assertEqual(session.state, ActivitySessionState.FAILED)
        self.assertEqual(session.result.exit_reason, ActivityExitReason.LAUNCH_FAILURE)
        factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()

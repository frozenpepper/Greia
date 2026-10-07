from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from greia_launcher.lifecycle import ActivityExitReason, ActivitySessionState
from greia_launcher.runtime_adapter import PythonRuntimeAdapter, RuntimeManager
from greia_launcher.system_chrome import SystemChromeCoordinator, SystemChromePhase
from greia_launcher.trusted_chrome_supervisor import TrustedChromeActivitySupervisor
from greia_platform.activities import ActivityManifest, SkillContribution
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.system_chrome import SystemNavigationAction
from greia_platform.trust import PackageTrust


@dataclass(frozen=True)
class _Profile:
    profile_id: str = "0123456789abcdef0123456789abcdef"
    display_name: str = "Mia"
    avatar_id: str = "unicorn"


class _ProfileContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.profile = _Profile()
        self.customization_dir = root / "customization"
        self.customization_dir.mkdir(parents=True, exist_ok=True)

    def activity_data_dir(self, activity_id: str) -> Path:
        path = self.root / "activities" / activity_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class _Authority:
    def __init__(self, activity_id: str) -> None:
        capabilities = {"display", "pointer"}
        self.activity_id = activity_id
        self.package_digest = "a" * 64
        self.package_trust = PackageTrust.BUILT_IN
        self.device_snapshot_token = DeviceCapabilityService.static(
            capabilities,
            source_id="trusted-chrome-test",
        ).snapshot().token
        self.effective_capabilities = frozenset(capabilities)
        self.sdk_features = self.effective_capabilities

    def has_capability(self, capability: str) -> bool:
        return capability in self.effective_capabilities

    def has_permission(self, permission: str) -> bool:
        del permission
        return False


class _Process:
    def __init__(self) -> None:
        self.pid = 4242
        self.returncode: int | None = None
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


class _ChromeBackend:
    backend_id = "test-chrome"

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.actions: list[SystemNavigationAction] = []
        self.fail_prepare = False
        self.fail_show = False

    def prepare(self, session_id: str, *, back_available: bool) -> None:
        self.calls.append(("prepare", session_id, back_available))
        if self.fail_prepare:
            raise RuntimeError("prepare failed")

    def show(self, session_id: str) -> None:
        self.calls.append(("show", session_id))
        if self.fail_show:
            raise RuntimeError("show failed")

    def ensure_visible(self, session_id: str) -> None:
        self.calls.append(("restack", session_id))

    def poll_action(self, session_id: str) -> SystemNavigationAction | None:
        self.calls.append(("poll", session_id))
        return self.actions.pop(0) if self.actions else None

    def hide(self, session_id: str) -> None:
        self.calls.append(("hide", session_id))


def _manifest(root: Path) -> ActivityManifest:
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
    return ActivityManifest(
        activity_id="org.greia.trusted-chrome-test",
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


def _supervisor(process: _Process, backend: _ChromeBackend):
    capabilities = {"display", "pointer"}
    manager = RuntimeManager(
        [
            PythonRuntimeAdapter(
                Path("/usr/bin/python3"),
                process_factory=lambda *args, **kwargs: process,
            )
        ],
        DeviceCapabilityService.static(capabilities, source_id="trusted-chrome-test"),
    )
    coordinator = SystemChromeCoordinator(backend)
    return (
        TrustedChromeActivitySupervisor(
            require_sandbox=False,
            runtime_manager=manager,
            system_chrome_coordinator=coordinator,
        ),
        coordinator,
    )


class TrustedChromeActivitySupervisorTests(unittest.TestCase):
    def test_chrome_prepares_before_ready_shows_on_ready_and_hides_on_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(manifest.activity_id)
            process = _Process()
            backend = _ChromeBackend()
            supervisor, coordinator = _supervisor(process, backend)

            session = supervisor.start(manifest, profile, authority)
            self.assertEqual(backend.calls, [("prepare", session.session_id, False)])
            self.assertEqual(coordinator.snapshot.phase, SystemChromePhase.PREPARED)

            with mock.patch.object(type(session.control), "ready", return_value=True):
                self.assertIsNone(supervisor.poll(session))
            self.assertEqual(session.state, ActivitySessionState.RUNNING)
            self.assertEqual(coordinator.snapshot.phase, SystemChromePhase.VISIBLE)
            self.assertIn(("show", session.session_id), backend.calls)

            process.returncode = 0
            result = supervisor.poll(session)

        self.assertEqual(result.exit_reason, ActivityExitReason.NORMAL)
        self.assertEqual(coordinator.snapshot.phase, SystemChromePhase.HIDDEN)
        self.assertIn(("hide", session.session_id), backend.calls)

    def test_running_session_can_restack_same_trusted_chrome_for_modal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(manifest.activity_id)
            process = _Process()
            backend = _ChromeBackend()
            supervisor, coordinator = _supervisor(process, backend)
            session = supervisor.start(manifest, profile, authority)
            with mock.patch.object(type(session.control), "ready", return_value=True):
                self.assertIsNone(supervisor.poll(session))

            self.assertTrue(supervisor.ensure_system_chrome_visible(session))
            self.assertEqual(coordinator.snapshot.phase, SystemChromePhase.VISIBLE)
            self.assertIn(("restack", session.session_id), backend.calls)

    def test_home_action_requests_platform_stop_without_activity_event(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(manifest.activity_id)
            process = _Process()
            backend = _ChromeBackend()
            supervisor, _coordinator = _supervisor(process, backend)
            session = supervisor.start(manifest, profile, authority)
            with mock.patch.object(type(session.control), "ready", return_value=True):
                self.assertIsNone(supervisor.poll(session))

            backend.actions.append(SystemNavigationAction.HOME)
            self.assertIsNone(supervisor.poll(session))

        self.assertEqual(session.state, ActivitySessionState.STOPPING)
        self.assertIsNotNone(session.stop_requested_at)

    def test_prepare_failure_force_stops_before_ready_but_does_not_poison_next_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(manifest.activity_id)
            process = _Process()
            backend = _ChromeBackend()
            backend.fail_prepare = True
            supervisor, coordinator = _supervisor(process, backend)

            session = supervisor.start(manifest, profile, authority)

        self.assertTrue(process.killed)
        self.assertIsNotNone(session.result)
        self.assertEqual(session.result.exit_reason, ActivityExitReason.PLATFORM_FAILURE)
        self.assertEqual(coordinator.snapshot.phase, SystemChromePhase.HIDDEN)
        self.assertIn(("hide", session.session_id), backend.calls)

    def test_show_failure_becomes_platform_failure_and_recovers_chrome(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(manifest.activity_id)
            process = _Process()
            backend = _ChromeBackend()
            backend.fail_show = True
            supervisor, coordinator = _supervisor(process, backend)
            session = supervisor.start(manifest, profile, authority)

            with mock.patch.object(type(session.control), "ready", return_value=True):
                result = supervisor.poll(session)

        self.assertTrue(process.killed)
        self.assertIsNotNone(result)
        self.assertEqual(result.exit_reason, ActivityExitReason.PLATFORM_FAILURE)
        self.assertEqual(coordinator.snapshot.phase, SystemChromePhase.HIDDEN)
        self.assertIn(("hide", session.session_id), backend.calls)

    def test_controller_guide_button_requests_platform_stop_without_activity_event(self) -> None:
        class _FakeControllerSource:
            def __init__(self) -> None:
                self.guide_pressed = False

            def poll_guide_button(self) -> bool:
                return self.guide_pressed

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(manifest.activity_id)
            process = _Process()
            backend = _ChromeBackend()
            controller_source = _FakeControllerSource()
            supervisor, _coordinator = _supervisor(process, backend)
            supervisor._controller_set = controller_source

            session = supervisor.start(manifest, profile, authority)
            with mock.patch.object(type(session.control), "ready", return_value=True):
                self.assertIsNone(supervisor.poll(session))

            controller_source.guide_pressed = True
            self.assertIsNone(supervisor.poll(session))

        self.assertEqual(session.state, ActivitySessionState.STOPPING)
        self.assertIsNotNone(session.stop_requested_at)


if __name__ == "__main__":
    unittest.main()

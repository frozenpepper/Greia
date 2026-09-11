from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import dataclass, replace
from pathlib import Path
from unittest import mock

from greia_launcher.event_broker import ActivityEventBroker
from greia_launcher.lifecycle import ActivityExitReason, ActivitySessionState
from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    RuntimeCommand,
    RuntimeManager,
)
from greia_launcher.storage_broker import ActivityStorageBroker
from greia_launcher.supervisor import (
    SANDBOX_STORAGE_ROOT,
    ActivityLifecycleError,
    ActivitySupervisor,
)
from greia_platform.activities import ActivityManifest, SkillContribution
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.history import HistoryPolicy, PlatformHistoryService, ProgressionPolicy
from greia_platform.storage import ActivityStorageService, StoragePolicy
from greia_platform.storage_client import ActivityStorageClient
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
        self.progress_dir = root / "progress"
        self.progress_dir.mkdir(parents=True, exist_ok=True)

    def activity_data_dir(self, activity_id: str) -> Path:
        path = self.root / "activities" / activity_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def activity_storage_dir(self, activity_id: str) -> Path:
        path = self.root / "storage" / activity_id
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
        self.returncode = -9


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


def _manager(capabilities: set[str], *, process_factory=None) -> RuntimeManager:
    adapter = (
        PythonRuntimeAdapter(Path("/usr/bin/python3"))
        if process_factory is None
        else PythonRuntimeAdapter(
            Path("/usr/bin/python3"), process_factory=process_factory
        )
    )
    return RuntimeManager(
        [adapter],
        DeviceCapabilityService.static(capabilities, source_id="supervisor-test"),
    )


def _storage_service() -> ActivityStorageService:
    return ActivityStorageService(
        StoragePolicy(
            policy_schema_version=1,
            namespace_quota_bytes=1024 * 1024,
            max_kv_bytes=64 * 1024,
            max_kv_value_bytes=16 * 1024,
            max_key_bytes=128,
            max_file_bytes=256 * 1024,
            max_files=32,
            max_path_bytes=256,
            protected_free_bytes=0,
            max_rollback_snapshots=1,
        )
    )


def _broker_factory(runtime_root: Path):
    def start(storage, session_id: str, *, sandboxed: bool):
        return ActivityStorageBroker.start(
            storage,
            session_id,
            runtime_root=runtime_root,
            sandboxed=sandboxed,
        )

    return start


def _history_service() -> PlatformHistoryService:
    return PlatformHistoryService(
        HistoryPolicy(
            schema_version=1,
            max_sessions_per_profile=64,
            max_events_per_session=64,
            max_event_payload_bytes=8192,
            max_idempotency_key_bytes=64,
            max_reward_ledger_entries=256,
            max_recent_sessions_summary=16,
            max_score_absolute=10**12,
            sqlite_busy_timeout_ms=2000,
        ),
        ProgressionPolicy(1, ()),
    )


def _event_broker_factory(runtime_root: Path):
    def start(store, manifest, progression, session_id: str, *, sandboxed: bool):
        return ActivityEventBroker.start(
            store,
            manifest,
            progression,
            session_id,
            runtime_root=runtime_root,
            sandboxed=sandboxed,
        )

    return start


class SupervisorTests(unittest.TestCase):
    def test_installed_supervisor_requires_explicit_runtime_manager(self) -> None:
        with self.assertRaisesRegex(ActivityLifecycleError, "injected HAL-backed RuntimeManager"):
            ActivitySupervisor(require_sandbox=True)

    def test_installed_supervisor_requires_storage_service(self) -> None:
        with self.assertRaisesRegex(ActivityLifecycleError, "ActivityStorageService"):
            ActivitySupervisor(
                require_sandbox=True,
                runtime_manager=_manager({"display", "pointer"}),
            )

    def test_missing_required_platform_authority_fails_before_process_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(manifest.activity_id, capabilities={"display"})
            factory = mock.Mock(side_effect=AssertionError("process must not start"))
            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager(
                    {"display", "pointer"}, process_factory=factory
                ),
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
                runtime_manager=_manager(
                    {"display", "pointer"}, process_factory=factory
                ),
            )
            session = supervisor.start(manifest, profile, authority)

        self.assertEqual(session.state, ActivitySessionState.FAILED)
        self.assertEqual(session.result.exit_reason, ActivityExitReason.LAUNCH_FAILURE)
        factory.assert_not_called()

    def test_failed_runtime_preparation_has_platform_session_without_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = replace(_manifest(root / "activity"), runtime_type="web")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id, capabilities={"display", "pointer"}
            )
            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager({"display", "pointer"}),
            )
            session = supervisor.start(manifest, profile, authority)

        self.assertEqual(len(session.session_id), 32)
        int(session.session_id, 16)
        self.assertIsNone(session.control)
        self.assertEqual(session.result.session_id, session.session_id)
        self.assertEqual(session.result.exit_reason, ActivityExitReason.LAUNCH_FAILURE)

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
                runtime_manager=_manager(
                    {"display", "pointer"}, process_factory=factory
                ),
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
                runtime_manager=_manager(
                    {"display", "pointer"}, process_factory=factory
                ),
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
        environment = calls[0][1]["env"]
        self.assertEqual(environment["PYTHONNOUSERSITE"], "1")
        self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(environment["GREIA_ACTIVITY_SESSION_ID"], session.session_id)
        self.assertIn("GREIA_ACTIVITY_READY_PATH", environment)
        self.assertIn("GREIA_ACTIVITY_STOP_PATH", environment)

    def test_runtime_adapter_owns_forced_stop_and_exit_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id, capabilities={"display", "pointer"}
            )
            process = _FakeProcess()
            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager(
                    {"display", "pointer"},
                    process_factory=lambda *args, **kwargs: process,
                ),
            )
            session = supervisor.start(manifest, profile, authority)
            result = supervisor.force_stop(session)

        self.assertTrue(process.killed)
        self.assertIsNotNone(result)
        self.assertEqual(result.exit_reason, ActivityExitReason.FORCED_STOP)
        self.assertEqual(result.return_code, -9)

    def test_storage_broker_is_exposed_for_launch_and_removed_on_exit(self) -> None:
        # Outer dir honors TMPDIR (device /tmp is noexec); broker socket
        # stays short under /tmp (sun_path guard), where noexec does not
        # affect sockets. T02-SPAWN-HYGIENE split convention.
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory(
            dir="/tmp"
        ) as broker_base:
            root = Path(temporary)
            brokers = Path(broker_base)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id, capabilities={"display", "pointer"}
            )
            process = _FakeProcess()
            calls = []

            def factory(*args, **kwargs):
                calls.append((args, kwargs))
                return process

            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=_manager(
                    {"display", "pointer"}, process_factory=factory
                ),
                storage_service=_storage_service(),
                storage_broker_factory=_broker_factory(brokers / "brokers"),
            )
            session = supervisor.start(manifest, profile, authority)
            environment = calls[0][1]["env"]
            socket_path = Path(environment["GREIA_STORAGE_SOCKET"])
            client = ActivityStorageClient(
                socket_path, environment["GREIA_STORAGE_TOKEN"]
            )
            client.kv_set("level", 7)
            self.assertEqual(client.kv_get("level"), 7)
            self.assertTrue(socket_path.exists())

            process.returncode = 0
            result = supervisor.poll(session)
            self.assertEqual(result.exit_reason, ActivityExitReason.NORMAL)
            self.assertFalse(socket_path.exists())

        self.assertIsNone(supervisor.active_session)

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
                runtime_manager=_manager(
                    {"display", "pointer"},
                    process_factory=lambda *args, **kwargs: _FakeProcess(),
                ),
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
        self.assertNotIn("PYTHONNOUSERSITE", environment)
        self.assertNotIn("PYTHONDONTWRITEBYTECODE", environment)

    def test_sandbox_command_honors_runtime_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest(root / "activity")
            nested = manifest.root / "runtime-work"
            nested.mkdir()
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id, capabilities={"display", "pointer"}
            )
            command = ActivitySupervisor._sandbox_command(
                root / "bwrap",
                RuntimeCommand(command=("runtime", "--start"), cwd=nested),
                manifest,
                profile,
                authority,
            )
            chdir = command.index("--chdir")
            self.assertEqual(Path(command[chdir + 1]), nested)
            self.assertEqual(command[chdir + 2 :], ["runtime", "--start"])

    def test_sandbox_launch_mounts_only_ephemeral_storage_broker(self) -> None:
        # The fixture sandbox needs an exec-capable dir (the device host
        # mounts /tmp noexec, so honor TMPDIR here); broker sockets need a
        # short dir (sun_path guard), so they stay under /tmp, where noexec
        # does not affect sockets.
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory(
            dir="/tmp"
        ) as broker_base:
            root = Path(temporary)
            brokers = Path(broker_base)
            sandbox = root / "bwrap"
            sandbox.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            sandbox.chmod(0o755)
            manifest = _manifest(root / "activity")
            profile = _ProfileContext(root / "profile")
            authority = _Authority(
                manifest.activity_id, capabilities={"display", "pointer"}
            )
            process = _FakeProcess()
            calls = []

            def factory(*args, **kwargs):
                calls.append((args, kwargs))
                return process

            supervisor = ActivitySupervisor(
                sandbox_executable=sandbox,
                require_sandbox=True,
                runtime_manager=_manager(
                    {"display", "pointer"}, process_factory=factory
                ),
                storage_service=_storage_service(),
                storage_broker_factory=_broker_factory(brokers / "brokers"),
                history_service=_history_service(),
                event_broker_factory=_event_broker_factory(brokers / "event-brokers"),
            )
            session = supervisor.start(manifest, profile, authority)
            command = list(calls[0][0][0])
            environment = calls[0][1]["env"]
            self.assertEqual(
                Path(environment["GREIA_STORAGE_SOCKET"]),
                SANDBOX_STORAGE_ROOT / "storage.sock",
            )
            # The path appears twice: once as the --dir target, once as the
            # --ro-bind target. The bind is the second occurrence.
            mount_indices = [
                i for i, token in enumerate(command) if token == str(SANDBOX_STORAGE_ROOT)
            ]
            bind_index = mount_indices[1]
            self.assertEqual(command[bind_index - 2], "--ro-bind")
            self.assertEqual(command[bind_index - 4], "--dir")
            host_broker_root = Path(command[bind_index - 1])
            self.assertNotEqual(host_broker_root, profile.root)
            self.assertTrue((host_broker_root / "storage.sock").exists())

            process.returncode = 0
            supervisor.poll(session)
            self.assertFalse(host_broker_root.exists())

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
                runtime_manager=_manager(
                    {"display", "pointer"}, process_factory=factory
                ),
                storage_service=_storage_service(),
                storage_broker_factory=_broker_factory(root / "brokers"),
                history_service=_history_service(),
                event_broker_factory=_event_broker_factory(root / "event-brokers"),
            )
            session = supervisor.start(manifest, profile, authority)

        self.assertEqual(session.state, ActivitySessionState.FAILED)
        self.assertEqual(session.result.exit_reason, ActivityExitReason.LAUNCH_FAILURE)
        factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from unittest import mock
from pathlib import Path

from greia_launcher.event_broker import ActivityEventBroker, SANDBOX_EVENT_ROOT
from greia_launcher.runtime_adapter import PythonRuntimeAdapter, RuntimeManager
from greia_launcher.storage_broker import ActivityStorageBroker
from greia_launcher.supervisor import ActivityLifecycleError, ActivitySupervisor
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.event_client import ActivityEventClient, ActivityEventClientError
from greia_platform.history import PlatformHistoryService
from greia_platform.profiles import ProfileStore
from greia_platform.storage import ActivityStorageService, StorageError, StoragePolicy
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _Authority:
    def __init__(self, activity_id: str):
        self.activity_id = activity_id
        self.package_digest = "a" * 64
        self.package_trust = PackageTrust.BUILT_IN
        capabilities = {"display", "pointer"}
        self.device_snapshot_token = DeviceCapabilityService.static(
            capabilities, source_id="r5-integration-test"
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
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = -15

    def kill(self):
        self.returncode = -9


class _FailingStorage:
    def open(self, *args, **kwargs):
        raise StorageError("synthetic platform storage failure")


class R5IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = RuntimeCatalogue.load(
            PROJECT_ROOT / "runtime" / "child-runtime.toml"
        )
        source = ActivitySource(
            PROJECT_ROOT / "activities", PackageTrust.BUILT_IN, "greia-system"
        )
        cls.activities = ActivityRegistry([source], cls.runtime).discover()
        cls.shape = next(
            item
            for item in cls.activities
            if item.activity_id == "org.greia.shape-garden"
        )
        cls.history = PlatformHistoryService.load(
            PROJECT_ROOT / "runtime" / "history-policy.toml",
            PROJECT_ROOT / "runtime" / "progression-policy.toml",
            cls.activities,
        )
        cls.storage = ActivityStorageService(
            StoragePolicy.load(PROJECT_ROOT / "runtime" / "storage-policy.toml")
        )

    def _profile(self, root: Path):
        profiles = ProfileStore.load(
            PROJECT_ROOT / "runtime" / "profile-defaults.toml",
            root / "profiles",
        )
        child = profiles.ensure_initialized()[0]
        return profiles.context(child.profile_id)

    def _manager(self, factory=None):
        adapter = PythonRuntimeAdapter(
            Path("/usr/bin/python3"), process_factory=factory
        )
        return RuntimeManager(
            [adapter],
            DeviceCapabilityService.static(
                {"display", "pointer"}, source_id="r5-integration-test"
            ),
        )

    @staticmethod
    def _storage_factory(root: Path):
        def start(storage, session_id: str, *, sandboxed: bool):
            return ActivityStorageBroker.start(
                storage, session_id, runtime_root=root, sandboxed=sandboxed
            )
        return start

    @staticmethod
    def _event_factory(root: Path):
        def start(store, manifest, progression, session_id: str, *, sandboxed: bool):
            return ActivityEventBroker.start(
                store,
                manifest,
                progression,
                session_id,
                runtime_root=root,
                sandboxed=sandboxed,
            )
        return start

    def test_installed_supervisor_requires_history_authority(self) -> None:
        with self.assertRaisesRegex(
            ActivityLifecycleError, "PlatformHistoryService"
        ):
            ActivitySupervisor(
                require_sandbox=True,
                runtime_manager=self._manager(),
                storage_service=self.storage,
            )

    def test_runtime_preparation_failure_is_still_authoritative_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = self._profile(root)
            manifest = replace(self.shape, runtime_type="web")
            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=self._manager(),
                history_service=self.history,
            )
            session = supervisor.start(manifest, profile, _Authority(manifest.activity_id))
            summary = self.history.open(profile).summary()

        self.assertEqual(session.result.exit_reason.value, "launch_failure")
        self.assertEqual(len(summary.recent_sessions), 1)
        self.assertEqual(summary.recent_sessions[0].exit_reason, "launch_failure")

    def test_missing_bubblewrap_closes_authoritative_launch_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = self._profile(root)
            factory = mock.Mock(side_effect=AssertionError("process must not start"))
            supervisor = ActivitySupervisor(
                sandbox_executable=root / "missing-bwrap",
                require_sandbox=True,
                runtime_manager=self._manager(factory),
                storage_service=self.storage,
                history_service=self.history,
            )
            session = supervisor.start(
                self.shape, profile, _Authority(self.shape.activity_id)
            )
            summary = self.history.open(profile).summary()

        self.assertEqual(session.result.exit_reason.value, "launch_failure")
        self.assertEqual(len(summary.recent_sessions), 1)
        persisted = summary.recent_sessions[0]
        self.assertEqual(persisted.exit_reason, "launch_failure")
        self.assertIsNotNone(persisted.ended_at)
        factory.assert_not_called()

    def test_platform_storage_failure_is_distinct_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profile = self._profile(root)
            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=self._manager(),
                storage_service=_FailingStorage(),
                history_service=self.history,
            )
            session = supervisor.start(
                self.shape, profile, _Authority(self.shape.activity_id)
            )
            summary = self.history.open(profile).summary()

        self.assertEqual(session.result.exit_reason.value, "platform_failure")
        self.assertEqual(summary.recent_sessions[0].exit_reason, "platform_failure")

    def test_event_broker_round_trip_applies_only_platform_reward_and_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            profile = self._profile(root)
            process = _FakeProcess()
            calls = []

            def factory(*args, **kwargs):
                calls.append((args, kwargs))
                return process

            supervisor = ActivitySupervisor(
                require_sandbox=False,
                runtime_manager=self._manager(factory),
                storage_service=self.storage,
                storage_broker_factory=self._storage_factory(root / "storage-brokers"),
                history_service=self.history,
                event_broker_factory=self._event_factory(root / "event-brokers"),
            )
            session = supervisor.start(
                self.shape, profile, _Authority(self.shape.activity_id)
            )
            environment = calls[0][1]["env"]
            event_socket = Path(environment["GREIA_EVENT_SOCKET"])
            client = ActivityEventClient(
                event_socket, environment["GREIA_EVENT_TOKEN"]
            )
            receipt = client.emit(
                "creation.completed",
                idempotency_key="creation-one",
                payload={"reward_id": "diamonds", "reward_delta": 9999},
            )
            self.assertEqual(receipt.reward_deltas, (("star", 1),))
            with self.assertRaises(ActivityEventClientError):
                ActivityEventClient(event_socket, "wrong-token").emit(
                    "creation.completed", idempotency_key="forged-token"
                )
            with mock.patch.object(
                type(session.control), "ready", return_value=True
            ):
                self.assertIsNone(supervisor.poll(session))
            process.returncode = 0
            result = supervisor.poll(session)
            summary = self.history.open(profile).summary()

        self.assertEqual(result.exit_reason.value, "normal")
        self.assertTrue(result.ready)
        self.assertEqual(dict(summary.reward_balances), {"star": 1})
        self.assertEqual(summary.recent_sessions[0].exit_reason, "normal")
        self.assertTrue(summary.recent_sessions[0].ready)
        self.assertFalse(event_socket.exists())

    def test_sandbox_receives_only_current_event_broker_endpoint(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary)
            profile = self._profile(root)
            process = _FakeProcess()
            calls = []

            def factory(*args, **kwargs):
                calls.append((args, kwargs))
                return process

            sandbox = root / "bwrap"
            sandbox.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            sandbox.chmod(0o755)
            supervisor = ActivitySupervisor(
                sandbox_executable=sandbox,
                require_sandbox=True,
                runtime_manager=self._manager(factory),
                storage_service=self.storage,
                storage_broker_factory=self._storage_factory(root / "storage-brokers"),
                history_service=self.history,
                event_broker_factory=self._event_factory(root / "event-brokers"),
            )
            session = supervisor.start(
                self.shape, profile, _Authority(self.shape.activity_id)
            )
            command = list(calls[0][0][0])
            environment = calls[0][1]["env"]
            self.assertEqual(
                environment["GREIA_EVENT_SOCKET"],
                str(SANDBOX_EVENT_ROOT / "events.sock"),
            )
            event_root_indices = [
                i for i, token in enumerate(command) if token == str(SANDBOX_EVENT_ROOT)
            ]
            self.assertGreaterEqual(len(event_root_indices), 2)
            event_root_index = event_root_indices[1]
            self.assertEqual(command[event_root_index - 2], "--ro-bind")
            self.assertEqual(command[event_root_index - 4], "--dir")
            self.assertIn("event-brokers", command[event_root_index - 1])
            process.returncode = 0
            supervisor.poll(session)


if __name__ == "__main__":
    unittest.main()

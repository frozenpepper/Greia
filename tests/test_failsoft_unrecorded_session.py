"""Activity launch stays possible when child-data headroom is exhausted.

A volume past the platform budget must not lock the child out of Activities:
the supervisor launches an *unrecorded* session (nothing written to history,
no reward/progression mutation) instead of failing the launch. Non-capacity
history errors keep failing closed.
"""

from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher.event_broker import ActivityEventBroker
from greia_launcher.runtime_adapter import PythonRuntimeAdapter, RuntimeManager
from greia_launcher.storage_broker import ActivityStorageBroker
from greia_launcher.supervisor import ActivitySupervisor
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.creation_capacity import (
    VolumeBudget,
    VolumeCapacityPolicy,
    VolumeUsage,
)
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.event_client import ActivityEventClient, ActivityEventClientError
from greia_platform.history import (
    HistoryCapacityError,
    HistoryError,
    HistoryPolicy,
    PlatformHistoryService,
    ProgressionPolicy,
    UnrecordedSessionHistory,
)
from greia_platform.profiles import ProfileStore
from greia_platform.storage import ActivityStorageService, StoragePolicy
from greia_platform.trust import ActivitySource, PackageTrust

import hermetic_volume
from test_r5_integration import _Authority, _FakeProcess

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_GIB = 1024**3


def setUpModule() -> None:
    hermetic_volume.install_for_module()


class _SwitchableVolume:
    """Mutable synthetic volume so one test can fill the disk mid-session."""

    def __init__(self) -> None:
        self.state = "roomy"

    def __call__(self, _root: Path) -> VolumeUsage:
        if self.state == "roomy":
            return VolumeUsage(1024 * _GIB, _GIB, 1023 * _GIB)
        if self.state == "full":  # 90% used, still plenty physically free
            return VolumeUsage(10 * _GIB, 9 * _GIB, _GIB)
        # "exhausted": even non-growing replacements cannot get their journal
        return VolumeUsage(10 * _GIB, 10 * _GIB - 100 * 1024, 100 * 1024)


class UnrecordedSessionTests(unittest.TestCase):
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
        cls.history_policy = HistoryPolicy.load(
            PROJECT_ROOT / "runtime" / "history-policy.toml"
        )
        cls.progression = ProgressionPolicy.load(
            PROJECT_ROOT / "runtime" / "progression-policy.toml", cls.activities
        )
        cls.storage = ActivityStorageService(
            StoragePolicy.load(PROJECT_ROOT / "runtime" / "storage-policy.toml")
        )

    def setUp(self) -> None:
        self.volume = _SwitchableVolume()
        self.budget = VolumeBudget(VolumeCapacityPolicy(), probe=self.volume)
        self.history = PlatformHistoryService(
            self.history_policy, self.progression, volume_budget=self.budget
        )
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self._brokers = tempfile.TemporaryDirectory(dir="/tmp")
        self.addCleanup(self._brokers.cleanup)
        self.root = Path(self._temporary.name)
        profiles = ProfileStore.load(
            PROJECT_ROOT / "runtime" / "profile-defaults.toml",
            self.root / "profiles",
        )
        self.profile = profiles.context(profiles.ensure_initialized()[0].profile_id)
        self.process = _FakeProcess()
        self.calls: list[tuple] = []

    def _supervisor(self, history=None, sandbox: Path | None = None) -> ActivitySupervisor:
        brokers = Path(self._brokers.name)

        def process_factory(*args, **kwargs):
            self.calls.append((args, kwargs))
            return self.process

        def storage_factory(storage, session_id, *, sandboxed):
            return ActivityStorageBroker.start(
                storage,
                session_id,
                runtime_root=brokers / "storage",
                sandboxed=sandboxed,
            )

        def event_factory(store, manifest, progression, session_id, *, sandboxed):
            return ActivityEventBroker.start(
                store,
                manifest,
                progression,
                session_id,
                runtime_root=brokers / "events",
                sandboxed=sandboxed,
            )

        manager = RuntimeManager(
            [PythonRuntimeAdapter(Path("/usr/bin/python3"), process_factory=process_factory)],
            DeviceCapabilityService.static(
                {"display", "pointer"}, source_id="r5-integration-test"
            ),
        )
        return ActivitySupervisor(
            sandbox_executable=sandbox,
            require_sandbox=sandbox is not None,
            runtime_manager=manager,
            storage_service=self.storage,
            storage_broker_factory=storage_factory,
            history_service=history or self.history,
            event_broker_factory=event_factory,
        )

    def _client(self) -> ActivityEventClient:
        environment = self.calls[0][1]["env"]
        return ActivityEventClient(
            Path(environment["GREIA_EVENT_SOCKET"]), environment["GREIA_EVENT_TOKEN"]
        )

    def _finish(self, supervisor, session):
        with mock.patch.object(type(session.control), "ready", return_value=True):
            self.assertIsNone(supervisor.poll(session))
        self.process.returncode = 0
        return supervisor.poll(session)

    def test_launch_past_headroom_runs_unrecorded_and_drops_events(self) -> None:
        self.volume.state = "full"
        supervisor = self._supervisor()
        with self.assertLogs("greia_launcher.supervisor", logging.WARNING) as logs:
            session = supervisor.start(
                self.shape, self.profile, _Authority(self.shape.activity_id)
            )
        self.assertIsNone(session.result, "Activity must actually launch")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(logs.records), 1)
        # Broker contract intact: endpoint exists, event is rejected honestly.
        with self.assertRaisesRegex(ActivityEventClientError, "history_unavailable"):
            self._client().emit("creation.completed", idempotency_key="k1")
        result = self._finish(supervisor, session)
        self.assertEqual(result.exit_reason.value, "normal")
        self.assertTrue(result.ready)
        # Nothing was written past the budget.
        self.assertFalse(
            (self.profile.progress_dir / "history.sqlite3").exists()
        )

    def test_unrecorded_session_never_mutates_existing_history(self) -> None:
        self.history.open(self.profile)  # DB exists while roomy
        self.volume.state = "full"
        supervisor = self._supervisor()
        session = supervisor.start(
            self.shape, self.profile, _Authority(self.shape.activity_id)
        )
        with self.assertRaises(ActivityEventClientError):
            self._client().emit("creation.completed", idempotency_key="k1")
        self._finish(supervisor, session)
        summary = self.history.open(self.profile).summary()
        self.assertEqual(summary.recent_sessions, ())
        self.assertEqual(summary.reward_balances, ())

    def test_history_filling_mid_session_does_not_fail_the_session(self) -> None:
        supervisor = self._supervisor()
        session = supervisor.start(
            self.shape, self.profile, _Authority(self.shape.activity_id)
        )
        self.assertIsNone(session.result)
        self.volume.state = "exhausted"
        with self.assertRaises(ActivityEventClientError):
            self._client().emit("creation.completed", idempotency_key="k1")
        with self.assertLogs("greia_launcher.supervisor", logging.WARNING):
            result = self._finish(supervisor, session)
        self.assertEqual(result.exit_reason.value, "normal")
        self.assertTrue(result.ready)

    def test_non_capacity_history_error_still_fails_closed(self) -> None:
        class _CorruptHistory:
            history_policy = self.history_policy
            progression_policy = self.progression

            def open(self, _profile):
                raise HistoryError("history database is unavailable or corrupt")

        supervisor = self._supervisor(history=_CorruptHistory())
        session = supervisor.start(
            self.shape, self.profile, _Authority(self.shape.activity_id)
        )
        self.assertEqual(session.result.exit_reason.value, "platform_failure")
        self.assertEqual(self.calls, [])

    def test_sandboxed_launch_still_receives_event_endpoint(self) -> None:
        self.volume.state = "full"
        sandbox = self.root / "bwrap"
        sandbox.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        sandbox.chmod(0o755)
        supervisor = self._supervisor(sandbox=sandbox)
        session = supervisor.start(
            self.shape, self.profile, _Authority(self.shape.activity_id)
        )
        self.assertIsNone(session.result)
        self.assertIn("GREIA_EVENT_SOCKET", self.calls[0][1]["env"])
        self.process.returncode = 0
        supervisor.poll(session)


class UnrecordedSessionHistoryTests(unittest.TestCase):
    def test_drops_every_event_without_writing_and_counts(self) -> None:
        policy = HistoryPolicy.load(PROJECT_ROOT / "runtime" / "history-policy.toml")
        sink = UnrecordedSessionHistory(profile=object(), policy=policy)  # type: ignore[arg-type]
        sink.mark_ready("s")
        sink.finish_session("s", "normal", active_duration_seconds=1.0)
        for _ in range(3):
            with self.assertRaises(HistoryCapacityError):
                sink.emit_event(
                    object(), object(), session_id="s", event_id="e", idempotency_key="k"  # type: ignore[arg-type]
                )
        self.assertEqual(sink.dropped_events, 3)


if __name__ == "__main__":
    unittest.main()

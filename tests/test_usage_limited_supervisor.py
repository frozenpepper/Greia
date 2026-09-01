from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from unittest import mock

from greia_launcher.lifecycle import ActivityExitReason, ActivitySessionState
from greia_launcher.runtime_adapter import PythonRuntimeAdapter, RuntimeManager
from greia_launcher.usage_limit_lifecycle import ActivityUsageLimitGuard
from greia_launcher.usage_limited_supervisor import UsageLimitedActivitySupervisor
from greia_platform.activities import ActivityManifest, SkillContribution
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.trust import PackageTrust
from greia_platform.usage_limits import UsageLimitPolicy, UsageLimitStatus


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
            capabilities, source_id="usage-limit-supervisor-test"
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
        pass

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


class _FakeUsageService:
    def __init__(
        self,
        *,
        remaining: int | None,
        fail_status: bool = False,
        fail_record: bool = False,
    ) -> None:
        self.remaining = remaining
        self.used = 0
        self.fail_status = fail_status
        self.fail_record = fail_record
        self.recorded: list[tuple[str, int]] = []

    def _status(self, profile_id: str) -> UsageLimitStatus:
        effective = (
            None if self.remaining is None else max(0, self.remaining - self.used)
        )
        policy = UsageLimitPolicy(None if self.remaining is None else 60)
        return UsageLimitStatus(
            accounting_date=date(2026, 9, 1),
            profile_id=profile_id,
            device_policy=UsageLimitPolicy(),
            profile_policy=policy,
            device_used_seconds=0,
            profile_used_seconds=self.used,
            device_remaining_seconds=None,
            profile_remaining_seconds=effective,
            effective_remaining_seconds=effective,
        )

    def status(self, profile_id: str) -> UsageLimitStatus:
        if self.fail_status:
            raise OSError("usage ledger unavailable")
        return self._status(profile_id)

    def record_activity_time(
        self, profile_id: str, elapsed_seconds: int
    ) -> UsageLimitStatus:
        if self.fail_record:
            raise OSError("usage ledger unavailable")
        self.recorded.append((profile_id, elapsed_seconds))
        self.used += elapsed_seconds
        return self._status(profile_id)


def _manifest(root: Path) -> ActivityManifest:
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
    return ActivityManifest(
        activity_id="org.greia.usage-limit-test",
        legacy_ids=(),
        title_key="activity.usage-limit-test.title",
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


def _manager(process_factory) -> RuntimeManager:
    capabilities = {"display", "pointer"}
    return RuntimeManager(
        [
            PythonRuntimeAdapter(
                Path("/usr/bin/python3"), process_factory=process_factory
            )
        ],
        DeviceCapabilityService.static(
            capabilities, source_id="usage-limit-supervisor-test"
        ),
    )


class UsageLimitedActivitySupervisorTests(unittest.TestCase):
    def _start(
        self,
        root: Path,
        service: _FakeUsageService,
        process: _FakeProcess,
        *,
        graceful_stop_seconds: float = 2.0,
        process_factory=None,
    ):
        manifest = _manifest(root / "activity")
        profile = _ProfileContext(root / "profile")
        authority = _Authority(manifest.activity_id)
        factory = process_factory or (lambda *args, **kwargs: process)
        supervisor = UsageLimitedActivitySupervisor(
            require_sandbox=False,
            runtime_manager=_manager(factory),
            graceful_stop_seconds=graceful_stop_seconds,
            usage_limit_guard=ActivityUsageLimitGuard(service),
        )
        return supervisor, manifest, profile, authority

    def test_exhausted_budget_rejects_before_process_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            process = _FakeProcess()
            factory = mock.Mock(side_effect=AssertionError("process must not start"))
            supervisor, manifest, profile, authority = self._start(
                root,
                _FakeUsageService(remaining=0),
                process,
                process_factory=factory,
            )
            session = supervisor.start(manifest, profile, authority)

        self.assertEqual(session.state, ActivitySessionState.FAILED)
        self.assertEqual(session.result.exit_reason, ActivityExitReason.TIME_LIMIT_REACHED)
        factory.assert_not_called()

    def test_budget_zero_requests_graceful_stop_and_preserves_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            process = _FakeProcess()
            service = _FakeUsageService(remaining=2)
            supervisor, manifest, profile, authority = self._start(root, service, process)
            clock = [100.0]
            with (
                mock.patch(
                    "greia_launcher.supervisor.monotonic_now",
                    side_effect=lambda: clock[0],
                ),
                mock.patch(
                    "greia_launcher.usage_limited_supervisor.monotonic_now",
                    side_effect=lambda: clock[0],
                ),
            ):
                session = supervisor.start(manifest, profile, authority)
                clock[0] = 102.0
                self.assertIsNone(supervisor.poll(session))
                self.assertEqual(session.state, ActivitySessionState.STOPPING)
                self.assertEqual(service.recorded, [(profile.profile.profile_id, 2)])
                self.assertTrue(session.control.host_stop_path.exists())

                process.returncode = 0
                clock[0] = 102.5
                result = supervisor.poll(session)

        self.assertIsNotNone(result)
        self.assertEqual(result.exit_reason, ActivityExitReason.TIME_LIMIT_REACHED)
        self.assertFalse(process.killed)

    def test_uncooperative_activity_uses_existing_force_stop_but_keeps_limit_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            process = _FakeProcess()
            service = _FakeUsageService(remaining=1)
            supervisor, manifest, profile, authority = self._start(
                root, service, process, graceful_stop_seconds=2.0
            )
            clock = [200.0]
            with (
                mock.patch(
                    "greia_launcher.supervisor.monotonic_now",
                    side_effect=lambda: clock[0],
                ),
                mock.patch(
                    "greia_launcher.usage_limited_supervisor.monotonic_now",
                    side_effect=lambda: clock[0],
                ),
            ):
                session = supervisor.start(manifest, profile, authority)
                clock[0] = 201.0
                self.assertIsNone(supervisor.poll(session))
                self.assertEqual(session.state, ActivitySessionState.STOPPING)

                clock[0] = 203.1
                result = supervisor.poll(session)

        self.assertIsNotNone(result)
        self.assertTrue(process.killed)
        self.assertEqual(result.return_code, -9)
        self.assertEqual(result.exit_reason, ActivityExitReason.TIME_LIMIT_REACHED)
        self.assertEqual(
            service.recorded,
            [(profile.profile.profile_id, 1), (profile.profile.profile_id, 2)],
        )

    def test_runtime_ledger_failure_fails_closed_as_platform_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            process = _FakeProcess()
            service = _FakeUsageService(remaining=30, fail_record=True)
            supervisor, manifest, profile, authority = self._start(root, service, process)
            clock = [300.0]
            with (
                mock.patch(
                    "greia_launcher.supervisor.monotonic_now",
                    side_effect=lambda: clock[0],
                ),
                mock.patch(
                    "greia_launcher.usage_limited_supervisor.monotonic_now",
                    side_effect=lambda: clock[0],
                ),
            ):
                session = supervisor.start(manifest, profile, authority)
                clock[0] = 315.0
                result = supervisor.poll(session)

        self.assertIsNotNone(result)
        self.assertTrue(process.killed)
        self.assertEqual(result.exit_reason, ActivityExitReason.PLATFORM_FAILURE)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from datetime import date

from greia_launcher.usage_limit_lifecycle import (
    ActivityUsageLimitError,
    ActivityUsageLimitGuard,
    ActivityUsageLimitReached,
)
from greia_platform.usage_limits import UsageLimitPolicy, UsageLimitStatus


class _FakeUsageService:
    def __init__(self, *, remaining: int | None = None, fail: bool = False) -> None:
        self.remaining = remaining
        self.used = 0
        self.fail = fail
        self.recorded: list[tuple[str, int]] = []

    def _status(self, profile_id: str) -> UsageLimitStatus:
        remaining = (
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
            profile_remaining_seconds=remaining,
            effective_remaining_seconds=remaining,
        )

    def status(self, profile_id: str) -> UsageLimitStatus:
        if self.fail:
            raise OSError("ledger unavailable")
        return self._status(profile_id)

    def record_activity_time(
        self, profile_id: str, elapsed_seconds: int
    ) -> UsageLimitStatus:
        if self.fail:
            raise OSError("ledger unavailable")
        self.recorded.append((profile_id, elapsed_seconds))
        self.used += elapsed_seconds
        return self._status(profile_id)


class ActivityUsageLimitGuardTests(unittest.TestCase):
    def test_preflight_rejects_exhausted_profile(self) -> None:
        guard = ActivityUsageLimitGuard(_FakeUsageService(remaining=0))

        with self.assertRaises(ActivityUsageLimitReached) as raised:
            guard.preflight("child")

        self.assertTrue(raised.exception.status.exhausted)

    def test_normal_checkpoint_records_only_when_due(self) -> None:
        service = _FakeUsageService(remaining=120)
        guard = ActivityUsageLimitGuard(service)
        initial = guard.preflight("child")
        guard.begin("session", "child", 100.0, initial_status=initial)

        guard.checkpoint("session", 114.9)
        self.assertEqual(service.recorded, [])

        status = guard.checkpoint("session", 115.0)
        self.assertEqual(service.recorded, [("child", 15)])
        self.assertEqual(status.effective_remaining_seconds, 105)

    def test_fractional_runtime_is_preserved_between_checkpoints(self) -> None:
        service = _FakeUsageService(remaining=120)
        guard = ActivityUsageLimitGuard(service, checkpoint_seconds=5)
        guard.begin("session", "child", 10.0)

        guard.checkpoint("session", 15.8)
        guard.checkpoint("session", 20.2)

        self.assertEqual(service.recorded, [("child", 5), ("child", 5)])

    def test_remaining_budget_shortens_checkpoint_interval(self) -> None:
        service = _FakeUsageService(remaining=3)
        guard = ActivityUsageLimitGuard(service)
        guard.begin("session", "child", 20.0)

        self.assertFalse(guard.checkpoint("session", 22.9).exhausted)
        status = guard.checkpoint("session", 23.0)

        self.assertEqual(service.recorded, [("child", 3)])
        self.assertTrue(status.exhausted)

    def test_finish_records_terminal_tail_once_and_retires_session(self) -> None:
        service = _FakeUsageService(remaining=120)
        guard = ActivityUsageLimitGuard(service)
        guard.begin("session", "child", 50.0)

        guard.finish("session", 54.7)

        self.assertEqual(service.recorded, [("child", 4)])
        with self.assertRaises(ActivityUsageLimitError):
            guard.finish("session", 60.0)

    def test_unlimited_runtime_is_still_accounted(self) -> None:
        service = _FakeUsageService(remaining=None)
        guard = ActivityUsageLimitGuard(service)
        guard.begin("session", "child", 0.0)

        status = guard.checkpoint("session", 15.0)

        self.assertEqual(service.recorded, [("child", 15)])
        self.assertIsNone(status.effective_remaining_seconds)

    def test_store_failure_is_wrapped_as_lifecycle_authority_failure(self) -> None:
        guard = ActivityUsageLimitGuard(_FakeUsageService(fail=True))

        with self.assertRaises(ActivityUsageLimitError):
            guard.preflight("child")

    def test_begin_rejects_status_for_another_profile(self) -> None:
        service = _FakeUsageService(remaining=30)
        guard = ActivityUsageLimitGuard(service)
        wrong = service.status("other")

        with self.assertRaises(ActivityUsageLimitError):
            guard.begin("session", "child", 0.0, initial_status=wrong)

    def test_monotonic_time_may_not_move_backwards(self) -> None:
        guard = ActivityUsageLimitGuard(_FakeUsageService(remaining=30))
        guard.begin("session", "child", 10.0)

        with self.assertRaises(ActivityUsageLimitError):
            guard.checkpoint("session", 9.0, force=True)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from greia_platform.usage_limits import (
    UsageLimitError,
    UsageLimitPolicy,
    UsageLimitService,
    UsageLimitStore,
)


class UsageLimitPolicyTests(unittest.TestCase):
    def test_policy_is_bounded(self) -> None:
        self.assertFalse(UsageLimitPolicy().limited)
        self.assertEqual(UsageLimitPolicy(45).budget_seconds, 2700)
        for invalid in (0, -1, 1441, True):
            with self.subTest(invalid=invalid):
                with self.assertRaises(UsageLimitError):
                    UsageLimitPolicy(invalid)  # type: ignore[arg-type]


class UsageLimitServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.today = date(2026, 9, 1)
        self.store = UsageLimitStore(Path(self.temporary.name) / "usage-limits.json")
        self.service = UsageLimitService(self.store, date_provider=lambda: self.today)

    def test_unconfigured_profile_is_unlimited(self) -> None:
        status = self.service.status("child-a")
        self.assertIsNone(status.effective_remaining_seconds)
        self.assertFalse(status.exhausted)
        self.assertEqual(status.public_dict()["counting_mode"], "activity_time")

    def test_profile_limit_counts_activity_seconds(self) -> None:
        self.service.set_profile_policy("child-a", UsageLimitPolicy(10))
        status = self.service.record_activity_time("child-a", 125)
        self.assertEqual(status.profile_used_seconds, 125)
        self.assertEqual(status.effective_remaining_seconds, 475)

    def test_device_limit_is_shared_between_profiles(self) -> None:
        self.service.set_device_policy(UsageLimitPolicy(10))
        self.service.record_activity_time("child-a", 240)
        status = self.service.record_activity_time("child-b", 120)
        self.assertEqual(status.device_used_seconds, 360)
        self.assertEqual(status.effective_remaining_seconds, 240)
        self.assertEqual(self.service.status("child-a").device_used_seconds, 360)

    def test_most_restrictive_limit_wins(self) -> None:
        self.service.set_device_policy(UsageLimitPolicy(60))
        self.service.set_profile_policy("child-a", UsageLimitPolicy(20))
        status = self.service.record_activity_time("child-a", 15 * 60)
        self.assertEqual(status.device_remaining_seconds, 45 * 60)
        self.assertEqual(status.profile_remaining_seconds, 5 * 60)
        self.assertEqual(status.effective_remaining_seconds, 5 * 60)

    def test_exhaustion_clamps_at_zero(self) -> None:
        self.service.set_profile_policy("child-a", UsageLimitPolicy(1))
        status = self.service.record_activity_time("child-a", 75)
        self.assertEqual(status.effective_remaining_seconds, 0)
        self.assertTrue(status.exhausted)

    def test_new_calendar_day_gets_fresh_bucket(self) -> None:
        self.service.set_profile_policy("child-a", UsageLimitPolicy(10))
        self.service.record_activity_time("child-a", 300)
        self.today = date(2026, 9, 2)
        status = self.service.status("child-a")
        self.assertEqual(status.profile_used_seconds, 0)
        self.assertEqual(status.effective_remaining_seconds, 600)

    def test_clock_rollback_does_not_create_fresh_budget(self) -> None:
        self.service.set_profile_policy("child-a", UsageLimitPolicy(10))
        self.today = date(2026, 9, 2)
        self.service.record_activity_time("child-a", 300)
        self.today = date(2026, 9, 1)
        status = self.service.status("child-a")
        self.assertEqual(status.accounting_date, date(2026, 9, 2))
        self.assertEqual(status.effective_remaining_seconds, 300)

    def test_state_survives_service_restart(self) -> None:
        self.service.set_profile_policy("child-a", UsageLimitPolicy(30))
        self.service.record_activity_time("child-a", 91)
        restarted = UsageLimitService(self.store, date_provider=lambda: self.today)
        status = restarted.status("child-a")
        self.assertEqual(status.profile_policy.daily_minutes, 30)
        self.assertEqual(status.profile_used_seconds, 91)

    def test_store_rejects_symlink(self) -> None:
        target = Path(self.temporary.name) / "target.json"
        target.write_text("{}", encoding="utf-8")
        link = Path(self.temporary.name) / "link.json"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(UsageLimitError):
            UsageLimitStore(link).read()


if __name__ == "__main__":
    unittest.main()

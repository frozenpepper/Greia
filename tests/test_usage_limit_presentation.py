from __future__ import annotations

import unittest
from datetime import date

from greia_launcher.usage_limit_presentation import home_usage_limit_presentation
from greia_platform.usage_limits import UsageLimitPolicy, UsageLimitStatus


def _status(remaining: int | None) -> UsageLimitStatus:
    return UsageLimitStatus(
        accounting_date=date(2026, 9, 1),
        profile_id="child",
        device_policy=UsageLimitPolicy(),
        profile_policy=UsageLimitPolicy(),
        device_used_seconds=0,
        profile_used_seconds=0,
        device_remaining_seconds=None,
        profile_remaining_seconds=remaining,
        effective_remaining_seconds=remaining,
    )


class HomeUsageLimitPresentationTests(unittest.TestCase):
    def test_unlimited_budget_is_not_shown(self) -> None:
        presentation = home_usage_limit_presentation(_status(None))
        self.assertFalse(presentation.visible)
        self.assertEqual(presentation.text, "")
        self.assertFalse(presentation.exhausted)

    def test_exhausted_budget_uses_friendly_finished_state(self) -> None:
        presentation = home_usage_limit_presentation(_status(0))
        self.assertTrue(presentation.visible)
        self.assertEqual(presentation.text, "Finished for today")
        self.assertTrue(presentation.exhausted)

    def test_sub_minute_budget_avoids_seconds_countdown(self) -> None:
        presentation = home_usage_limit_presentation(_status(59))
        self.assertEqual(presentation.text, "Less than 1 min left today")

    def test_minutes_are_whole_and_stable(self) -> None:
        presentation = home_usage_limit_presentation(_status(42 * 60 + 37))
        self.assertEqual(presentation.text, "42 min left today")

    def test_hours_and_minutes_are_compact(self) -> None:
        presentation = home_usage_limit_presentation(_status(80 * 60))
        self.assertEqual(presentation.text, "1 h 20 min left today")

    def test_exact_hour_does_not_add_zero_minutes(self) -> None:
        presentation = home_usage_limit_presentation(_status(2 * 60 * 60))
        self.assertEqual(presentation.text, "2 h left today")


if __name__ == "__main__":
    unittest.main()

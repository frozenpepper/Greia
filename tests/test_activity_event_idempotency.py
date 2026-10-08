"""Event history must not deduplicate distinct facts by recycled payload identity."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from greia_platform import activity_api


class ActivityEventDefaultIdempotencyTests(unittest.TestCase):
    def test_omitted_keys_are_unique_for_repeated_equivalent_facts(self) -> None:
        with patch.object(activity_api, "get_events") as get_events:
            for _ in range(100):
                activity_api.emit_activity_event("pet.fed", {"food": "apple"})
        calls = get_events.return_value.emit.call_args_list
        keys = [call.kwargs["idempotency_key"] for call in calls]
        self.assertEqual(len(keys), 100)
        self.assertEqual(len(set(keys)), 100)
        self.assertTrue(all(key.startswith("pet.fed-") for key in keys))

    def test_explicit_retry_key_remains_stable(self) -> None:
        with patch.object(activity_api, "get_events") as get_events:
            activity_api.emit_activity_event(
                "pet.fed", {"food": "apple"}, idempotency_key="meal-42"
            )
            activity_api.emit_activity_event(
                "pet.fed", {"food": "apple"}, idempotency_key="meal-42"
            )
        calls = get_events.return_value.emit.call_args_list
        self.assertEqual(
            [call.kwargs["idempotency_key"] for call in calls],
            ["meal-42", "meal-42"],
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from greia_parent.protocol import API_BASE, api_index_payload


class ProfilePresentationParentProtocolTests(unittest.TestCase):
    def test_base_protocol_declares_resource_but_fails_closed_capability(self) -> None:
        payload = api_index_payload()
        self.assertFalse(payload["capabilities"]["profiles.presentation"])
        resources = {item["name"]: item for item in payload["resources"]}
        self.assertEqual(
            resources["profile_presentation"]["path"],
            f"{API_BASE}/profiles/{{profile_id}}/presentation",
        )
        self.assertEqual(
            resources["profile_presentation"]["methods"],
            ["GET", "PUT"],
        )

    def test_top_level_composition_can_enable_known_capability(self) -> None:
        payload = api_index_payload({"profiles.presentation": True})
        self.assertTrue(payload["capabilities"]["profiles.presentation"])

    def test_unknown_capability_still_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown Parent API capability"):
            api_index_payload({"profiles.made_up": True})


if __name__ == "__main__":
    unittest.main()

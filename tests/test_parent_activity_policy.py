from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_parent.api_server import ParentApiApplication
from greia_parent.protocol import API_BASE, api_index_payload
from greia_platform.activity_discovery import ActivityVisibilityMode


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ParentActivityPolicyTests(unittest.TestCase):
    def _app(self, root: Path) -> ParentApiApplication:
        return ParentApiApplication(
            PROJECT_ROOT,
            root / "parent",
            profiles_dir=root / "profiles",
            hardware_settings_dir=root / "hardware",
            hardware_status_path=root / "hardware-status.json",
            active_profile_status_path=root / "active-profile.json",
        )

    def test_protocol_advertises_typed_per_child_activity_policy(self) -> None:
        payload = api_index_payload()
        self.assertTrue(payload["capabilities"]["activities.policy"])
        resources = {item["name"]: item for item in payload["resources"]}
        policy = resources["profile_activity_policy"]
        self.assertEqual(
            policy["path"],
            f"{API_BASE}/profiles/{{profile_id}}/activity-policy",
        )
        self.assertEqual(policy["methods"], ["GET", "PUT"])

    def test_activity_payload_exposes_audience_and_discovery_facts_without_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary))
            activities = app.activities_payload()
            self.assertTrue(activities)
            sample = activities[0]
            self.assertIn("difficulty", sample)
            self.assertIn("recommended_age_min", sample)
            self.assertIn("recommended_age_max", sample)
            self.assertIn("adaptive_difficulty", sample)
            self.assertIn("discovery_tags", sample)
            self.assertNotIn("root", sample)
            self.assertNotIn("entrypoint", sample)

    def test_default_policy_fails_open_and_override_hides_one_activity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary))
            profile = app.profile_store.list_profiles()[0]
            baseline = app.activity_policy_payload(profile.profile_id)
            all_ids = [item["activity_id"] for item in app.activities_payload()]
            self.assertEqual(baseline["visibility_mode"], "show_all")
            self.assertEqual(set(baseline["effective_activity_ids"]), set(all_ids))

            target = all_ids[0]
            updated = app.update_activity_policy(
                profile.profile_id,
                visibility_mode=ActivityVisibilityMode.CUSTOM.value,
                difficulty_min=baseline["difficulty_min"],
                difficulty_max=baseline["difficulty_max"],
                overrides={target: "always_hide"},
            )
            self.assertEqual(updated["visibility_mode"], "custom")
            self.assertEqual(updated["overrides"][target], "always_hide")
            self.assertNotIn(target, updated["effective_activity_ids"])
            self.assertEqual(
                len(updated["effective_activity_ids"]),
                len(all_ids) - 1,
            )

    def test_profile_discovery_preferences_are_parent_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = self._app(Path(temporary))
            profile = app.profile_store.list_profiles()[0]
            updated = app.profile_store.update(
                profile.profile_id,
                approximate_age=6,
                challenge_preference="harder",
            )
            payload = next(
                item
                for item in app.profiles_payload()
                if item["profile_id"] == updated.profile_id
            )
            self.assertEqual(payload["approximate_age"], 6)
            self.assertEqual(payload["challenge_preference"], "harder")


if __name__ == "__main__":
    unittest.main()

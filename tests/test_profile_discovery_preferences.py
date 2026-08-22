from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from greia_platform.activity_discovery import ChallengePreference
from greia_platform.profiles import ProfileError, ProfileStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ProfileDiscoveryPreferenceTests(unittest.TestCase):
    def _store(self, root: Path) -> ProfileStore:
        return ProfileStore.load(
            PROJECT_ROOT / "runtime" / "profile-defaults.toml",
            root,
        )

    def test_old_profile_registry_defaults_to_unknown_age_and_automatic_challenge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = self._store(root)
            profile = store.ensure_initialized()[0]
            raw = json.loads(store.registry_path.read_text(encoding="utf-8"))
            raw["profiles"][0].pop("approximate_age", None)
            raw["profiles"][0].pop("challenge_preference", None)
            store.registry_path.write_text(json.dumps(raw), encoding="utf-8")
            loaded = store.list_profiles()[0]
            self.assertIsNone(loaded.approximate_age)
            self.assertEqual(loaded.challenge_preference, ChallengePreference.AUTOMATIC)

    def test_profile_can_set_change_and_clear_approximate_age(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            profile = store.ensure_initialized()[0]
            updated = store.update(
                profile.profile_id,
                approximate_age=6,
                challenge_preference=ChallengePreference.HARDER,
            )
            self.assertEqual(updated.approximate_age, 6)
            self.assertEqual(updated.challenge_preference, ChallengePreference.HARDER)
            cleared = store.update(profile.profile_id, clear_approximate_age=True)
            self.assertIsNone(cleared.approximate_age)
            self.assertEqual(cleared.challenge_preference, ChallengePreference.HARDER)

    def test_profile_rejects_precise_out_of_scope_age_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            profile = store.ensure_initialized()[0]
            with self.assertRaises(ProfileError):
                store.update(profile.profile_id, approximate_age=0)
            with self.assertRaises(ProfileError):
                store.update(profile.profile_id, approximate_age=19)

    def test_profile_context_owns_discovery_policy_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = self._store(Path(temporary))
            profile = store.ensure_initialized()[0]
            context = store.context(profile.profile_id)
            self.assertEqual(
                context.activity_discovery_policy_path,
                context.root / "activity-discovery.json",
            )


if __name__ == "__main__":
    unittest.main()

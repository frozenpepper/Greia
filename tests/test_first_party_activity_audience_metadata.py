from __future__ import annotations

import unittest
from pathlib import Path

from greia_launcher.catalogue_view import DISCOVERY_GROUP_IDS
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FirstPartyActivityAudienceMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifests = ActivityRegistry(
            [ActivitySource(PROJECT_ROOT / "activities", PackageTrust.BUILT_IN, "first-party")],
            RuntimeCatalogue.load(PROJECT_ROOT / "runtime" / "child-runtime.toml"),
        ).discover()

    def test_every_first_party_activity_has_audience_and_discovery_metadata(self) -> None:
        self.assertEqual(len(self.manifests), 27)
        allowed = set(DISCOVERY_GROUP_IDS)
        for manifest in self.manifests:
            with self.subTest(activity=manifest.activity_id):
                self.assertIsNotNone(manifest.recommended_age_min)
                self.assertTrue(manifest.discovery_tags)
                self.assertTrue(set(manifest.discovery_tags) <= allowed)
                self.assertGreaterEqual(manifest.difficulty, 1)
                self.assertLessEqual(manifest.difficulty, 10)

    def test_open_ended_creative_activities_are_not_given_fake_upper_age_limits(self) -> None:
        by_id = {manifest.activity_id: manifest for manifest in self.manifests}
        for activity_id in (
            "org.greia.painting",
            "org.greia.shape-garden",
            "org.greia.teatrino-fiabe",
            "org.greia.writing",
            "org.greia.orchestra-animali",
            "org.greia.posta-di-leo",
        ):
            with self.subTest(activity=activity_id):
                self.assertIsNone(by_id[activity_id].recommended_age_max)

    def test_known_multi_level_activities_declare_adaptive_challenge_span(self) -> None:
        by_id = {manifest.activity_id: manifest for manifest in self.manifests}
        for activity_id in (
            "org.greia.labirinto-magico",
            "org.greia.costruiamo-ponti",
            "org.greia.bottega-delle-misure",
            "org.greia.casa-del-dieci",
            "org.greia.luci-di-momo",
            "org.greia.specchi-magici",
            "org.greia.festa-delle-rime",
            "org.greia.officina-dei-suoni",
        ):
            with self.subTest(activity=activity_id):
                manifest = by_id[activity_id]
                self.assertTrue(manifest.adaptive_difficulty)
                self.assertIsNotNone(manifest.difficulty_min)
                self.assertIsNotNone(manifest.difficulty_max)
                self.assertLessEqual(manifest.difficulty_min, manifest.difficulty)
                self.assertGreaterEqual(manifest.difficulty_max, manifest.difficulty)


if __name__ == "__main__":
    unittest.main()

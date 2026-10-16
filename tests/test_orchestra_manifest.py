"""Orchestra source/manifest contract: free play + echo invitations + backing track."""
from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "activities" / "orchestra_animali" / "activity.toml"


class OrchestraManifestTests(unittest.TestCase):
    def test_manifest_matches_free_play_source_events_and_audio_consumer(self):
        raw = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
        education = raw["education"]
        self.assertIn("creativity", education["categories"])
        self.assertNotIn("auditory_memory", education["categories"])
        self.assertEqual(
            education["events"],
            [
                {"id": "instrument.played", "kind": "milestone"},
                {"id": "rhythm.echoed", "kind": "milestone"},
                {"id": "band.concert_completed", "kind": "completion"},
                {"id": "concert.performed", "kind": "creation"},
            ],
        )
        self.assertTrue(education["adaptive_difficulty"])
        self.assertNotIn("recommended_age_max", education)
        skills = {item["id"] for item in education["skills"]}
        self.assertIn("music.rhythm.echo_imitation", skills)
        self.assertEqual(raw["creations"]["consumes"], ["audio/wav"])


if __name__ == "__main__":
    unittest.main()

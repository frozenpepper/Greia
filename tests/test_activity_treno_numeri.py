from __future__ import annotations

import json
from pathlib import Path
import sys
import tomllib
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from activities.treno_numeri.main import FRUITS, TrainAudio

ACTIVITY_DIR = PROJECT_ROOT / "activities" / "treno_numeri"
RUNTIME_ASSETS = ACTIVITY_DIR / "assets" / "runtime"


class TrenoNumeriTests(unittest.TestCase):
    def test_manifest_is_valid_and_versioned(self) -> None:
        manifest_path = ACTIVITY_DIR / "activity.toml"
        self.assertTrue(manifest_path.is_file())
        with manifest_path.open("rb") as handle:
            data = tomllib.load(handle)
        self.assertEqual(data["activity"]["id"], "org.greia.treno-numeri")
        self.assertEqual(data["activity"]["version"], "0.1.0")
        self.assertIn("it", data["activity"]["languages"])
        self.assertIn("en", data["activity"]["languages"])

    def test_locales_contain_required_strings(self) -> None:
        it_json = json.loads((ACTIVITY_DIR / "locales" / "it.json").read_text(encoding="utf-8"))
        en_json = json.loads((ACTIVITY_DIR / "locales" / "en.json").read_text(encoding="utf-8"))
        self.assertIn("activity.title", it_json["strings"])
        self.assertIn("activity.title", en_json["strings"])

    def test_fruits_metadata(self) -> None:
        self.assertGreaterEqual(len(FRUITS), 4)
        for f in FRUITS:
            self.assertIn("id", f)
            self.assertIn("color", f)

    def test_audio_synthesizer_initializes(self) -> None:
        audio = TrainAudio()
        self.assertIsNotNone(audio)

    def test_baked_runtime_assets_exist(self) -> None:
        required_assets = [
            "locomotive.png",
            "wagon.png",
            "wheel_large.png",
            "wheel_small.png",
            "conductor_dani.png",
            "crate_basket.png",
            "fruit_apple.png",
            "fruit_banana.png",
            "fruit_carrot.png",
            "fruit_strawberry.png",
        ]
        for name in required_assets:
            p = RUNTIME_ASSETS / name
            self.assertTrue(p.exists(), f"Missing runtime asset: {name}")
            self.assertGreater(p.stat().st_size, 100, f"Asset too small: {name}")
            with p.open("rb") as f:
                header = f.read(8)
                self.assertEqual(header, b"\x89PNG\r\n\x1a\n", f"Invalid PNG: {name}")


class TrainEventKeySourceTests(unittest.TestCase):
    def test_replayed_journeys_have_independent_progress_event_keys(self) -> None:
        from pathlib import Path
        source = (ROOT / "activities" / "treno_numeri" / "treno_app.py").read_text(encoding="utf-8")
        self.assertIn("self._journey_id = uuid4().hex", source)
        self.assertIn('idempotency_key=f"train:{self._journey_id}:station:{round_idx}"', source)
        self.assertIn('idempotency_key=f"train:{self._journey_id}:completed"', source)
        self.assertEqual(source.count("self._journey_id = uuid4().hex"), 3)


if __name__ == "__main__":
    unittest.main()

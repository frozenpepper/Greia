from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
TEATRINO = _load_module("greia_test_teatrino_activity", ROOT / "activities" / "teatrino_fiabe" / "main.py")


class TeatrinoFiabeLogicTests(unittest.TestCase):
    def test_puppet_initialization_and_physics(self) -> None:
        puppet = TEATRINO.Puppet("lilli", "Lilli", 300, 250)
        self.assertEqual(puppet.puppet_id, "lilli")
        self.assertEqual(puppet.x, 300)
        self.assertEqual(puppet.y, 250)
        self.assertFalse(puppet.is_held)
        self.assertFalse(puppet.flip_x)

        # Contains check
        self.assertTrue(puppet.contains(300, 250))
        self.assertTrue(puppet.contains(320, 260))
        self.assertFalse(puppet.contains(400, 400))

        # Jump & speak
        puppet.jump()
        self.assertGreater(puppet.jump_timer, 0.0)
        puppet.speak()
        self.assertGreater(puppet.talk_timer, 0.0)

        # Update cycle
        puppet.update()
        self.assertLess(puppet.jump_timer, 1.0)
        self.assertLess(puppet.talk_timer, 1.0)

    def test_puppet_roster_and_asset_integrity(self) -> None:
        runtime_dir = ROOT / "activities" / "teatrino_fiabe" / "assets" / "runtime"
        source_dir = ROOT / "activities" / "teatrino_fiabe" / "assets" / "source"

        self.assertEqual(len(TEATRINO.PUPPET_ROSTER), 12)
        for p_id, p_name in TEATRINO.PUPPET_ROSTER:
            png_path = runtime_dir / f"puppet_{p_id}.png"
            svg_path = source_dir / f"puppet_{p_id}.svg"
            self.assertTrue(png_path.is_file(), f"Missing PNG asset for {p_id}")
            self.assertTrue(svg_path.is_file(), f"Missing SVG source for {p_id}")

    def test_backdrop_rendering_for_all_sceneries(self) -> None:
        for bg_id, bg_icon, bg_name in TEATRINO.BG_CONFIGS:
            surf = TEATRINO.render_backdrop_surface(bg_id)
            self.assertIsNotNone(surf)
            self.assertEqual(surf.get_width(), 1024)
            self.assertEqual(surf.get_height(), 600)

    def test_sound_manager_synthesis(self) -> None:
        sm = TEATRINO.SoundManager()
        self.assertTrue(sm._enabled)
        for key in ("pop", "trumpet", "magic", "applause", "giggle", "mystery", "boing"):
            self.assertIn(key, sm._sounds)
            self.assertGreater(sm._sounds[key].get_length(), 0.0)

    def test_microphone_recorder_lifecycle_and_toggle(self) -> None:
        rec = TEATRINO.MicrophoneRecorder()
        # Toggle test
        initial = rec.enabled
        if rec.has_hardware:
            self.assertEqual(rec.toggle(), not initial)
            rec.toggle()  # restore

        # Stop when not recording returns None safely
        self.assertIsNone(rec.stop_recording())

    def test_ambient_sparks(self) -> None:
        spark = TEATRINO.AmbientSpark("forest")
        self.assertGreaterEqual(spark.x, 120)
        self.assertLessEqual(spark.x, 900)
        spark.update()
        self.assertIsNotNone(spark.x)


if __name__ == "__main__":
    unittest.main()

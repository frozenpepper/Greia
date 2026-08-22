from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
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
TEATRINO = _load_module("greia_test_teatrino_activity_v2", ROOT / "activities" / "teatrino_fiabe" / "main.py")


class MockStorage:
    def __init__(self) -> None:
        self.kv: dict[str, object] = {}
        self.files: dict[str, bytes] = {}

    def kv_get(self, key: str, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key: str, value):
        self.kv[key] = value

    def file_write_atomic(self, name: str, data: bytes):
        self.files[name] = data

    def file_read(self, name: str) -> bytes | None:
        return self.files.get(name)

    def file_delete(self, name: str):
        self.files.pop(name, None)


class TeatrinoFiabeIteration2Tests(unittest.TestCase):
    def test_puppet_16_character_roster_and_asset_integrity(self) -> None:
        runtime_dir = ROOT / "activities" / "teatrino_fiabe" / "assets" / "runtime"
        source_dir = ROOT / "activities" / "teatrino_fiabe" / "assets" / "source"

        self.assertEqual(len(TEATRINO.PUPPET_ROSTER), 16)
        for p_id, p_name in TEATRINO.PUPPET_ROSTER:
            png_path = runtime_dir / f"puppet_{p_id}.png"
            svg_path = source_dir / f"puppet_{p_id}.svg"
            self.assertTrue(png_path.is_file(), f"Missing PNG asset for {p_id}")
            self.assertTrue(svg_path.is_file(), f"Missing SVG source for {p_id}")

    def test_backdrop_rendering_for_all_sceneries_including_cheerful_cottage(self) -> None:
        for bg_id, bg_icon, bg_name in TEATRINO.BG_CONFIGS:
            surf = TEATRINO.render_backdrop_surface(bg_id)
            self.assertIsNotNone(surf)
            self.assertEqual(surf.get_width(), 1024)
            self.assertEqual(surf.get_height(), 600)

    def test_show_repository_save_load_list_and_delete(self) -> None:
        mock_storage = MockStorage()
        repo = TEATRINO.ShowRepository(mock_storage)

        # Initially empty
        self.assertEqual(repo.list_shows(), [])

        # Save a show with dummy WAV audio
        dummy_wav = b"RIFF....WAVEfmt ....data...."
        puppets = [{"id": "principessa", "name": "Principessa"}, {"id": "draghetto", "name": "Draghetto"}]
        frames = [{"t": 0.0, "puppets": [{"id": "principessa", "x": 300, "y": 250, "flip": False, "jumping": False, "talking": False}]}]
        sfx = [{"t": 0.5, "sound": "trumpet"}]

        meta = repo.save_show("cottage", puppets, frames, sfx, 12.5, dummy_wav)
        self.assertIn("id", meta)
        self.assertEqual(meta["backdrop"], "cottage")
        self.assertTrue(meta["has_audio"])
        self.assertEqual(meta["duration"], 12.5)

        # List shows
        shows = repo.list_shows()
        self.assertEqual(len(shows), 1)
        self.assertEqual(shows[0]["id"], meta["id"])

        # Load show
        loaded_data, loaded_audio = repo.load_show(meta["id"])
        self.assertIsNotNone(loaded_data)
        self.assertEqual(loaded_audio, dummy_wav)
        self.assertEqual(len(loaded_data["frames"]), 1)
        self.assertEqual(len(loaded_data["sfx_events"]), 1)

        # Delete show
        repo.delete_show(meta["id"])
        self.assertEqual(repo.list_shows(), [])
        self.assertNotIn(f"show_{meta['id']}.json", mock_storage.files)
        self.assertNotIn(f"show_{meta['id']}.wav", mock_storage.files)

    def test_puppet_physics_and_gestures(self) -> None:
        p = TEATRINO.Puppet("bebe", "Bebè", 400, 260)
        self.assertEqual(p.puppet_id, "bebe")
        self.assertTrue(p.contains(400, 260))
        p.jump()
        p.speak()
        self.assertGreater(p.jump_timer, 0.0)
        self.assertGreater(p.talk_timer, 0.0)
        p.update()
        self.assertLess(p.jump_timer, 1.0)
        self.assertLess(p.talk_timer, 1.0)

    def test_sound_manager_synthesis(self) -> None:
        sm = TEATRINO.SoundManager()
        self.assertTrue(sm._enabled)
        for key in ("pop", "trumpet", "magic", "applause", "giggle", "mystery", "boing"):
            self.assertIn(key, sm._sounds)

    def test_microphone_toggle(self) -> None:
        rec = TEATRINO.MicrophoneRecorder()
        if rec.has_hardware:
            initial = rec.enabled
            self.assertEqual(rec.toggle(), not initial)
            rec.toggle()


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from activities.teatrino_fiabe.teatrino_assets import render_backdrop_surface
from activities.teatrino_fiabe.teatrino_content import BG_CONFIGS, PUPPET_ROSTER
from activities.teatrino_fiabe.teatrino_model import Puppet, ShowRepository
from activities.teatrino_fiabe.teatrino_renderer import get_library_modal_layout


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


class TeatrinoFiabeTests(unittest.TestCase):
    def test_puppet_roster_assets_exist(self) -> None:
        runtime_dir = ROOT / "activities" / "teatrino_fiabe" / "assets" / "runtime"
        source_dir = ROOT / "activities" / "teatrino_fiabe" / "assets" / "source"
        self.assertEqual(len(PUPPET_ROSTER), 16)
        for puppet_id, _name in PUPPET_ROSTER:
            self.assertTrue((runtime_dir / f"puppet_{puppet_id}.png").is_file())
            self.assertTrue((source_dir / f"puppet_{puppet_id}.svg").is_file())

    def test_backdrops_render_at_reference_size(self) -> None:
        for backdrop_id, _icon, _name in BG_CONFIGS:
            surface = render_backdrop_surface(backdrop_id)
            self.assertEqual(surface.get_size(), (1024, 600))

    def test_show_repository_round_trip_and_delete(self) -> None:
        storage = MockStorage()
        repo = ShowRepository(storage)
        dummy_wav = b"RIFF....WAVEfmt ....data...."
        puppets = [
            {"id": "principessa", "name": "Principessa"},
            {"id": "draghetto", "name": "Draghetto"},
        ]
        frames = [
            {
                "t": 0.0,
                "puppets": [
                    {
                        "id": "principessa",
                        "x": 300,
                        "y": 250,
                        "flip": False,
                        "jumping": False,
                        "talking": False,
                    }
                ],
            }
        ]
        sfx = [{"t": 0.5, "sound": "trumpet"}]

        meta = repo.save_show("cottage", puppets, frames, sfx, 12.5, dummy_wav)
        loaded_data, loaded_audio = repo.load_show(meta["id"])
        self.assertEqual(loaded_audio, dummy_wav)
        self.assertIsNotNone(loaded_data)
        assert loaded_data is not None
        self.assertEqual(len(loaded_data["frames"]), 1)
        self.assertEqual(len(loaded_data["sfx_events"]), 1)

        repo.delete_show(meta["id"])
        self.assertEqual(repo.list_shows(), [])

    def test_puppet_physics_and_gestures(self) -> None:
        puppet = Puppet("bebe", "Bebè", 400, 260)
        self.assertTrue(puppet.contains(400, 260))
        puppet.jump()
        puppet.speak()
        self.assertGreater(puppet.jump_timer, 0.0)
        self.assertGreater(puppet.talk_timer, 0.0)
        puppet.update()
        self.assertLess(puppet.jump_timer, 1.0)
        self.assertLess(puppet.talk_timer, 1.0)

    def test_repository_in_memory_fallback(self) -> None:
        repo = ShowRepository(None)
        meta = repo.save_show(
            "forest",
            [{"id": "cavaliere", "name": "Cavaliere"}],
            [],
            [],
            3.5,
            b"RIFFWAVE",
        )
        loaded_data, loaded_audio = repo.load_show(meta["id"])
        self.assertIsNotNone(loaded_data)
        self.assertEqual(loaded_audio, b"RIFFWAVE")
        repo.delete_show(meta["id"])
        self.assertEqual(repo.list_shows(), [])

    def test_library_modal_layout_geometry(self) -> None:
        layout = get_library_modal_layout(0, 6)
        self.assertEqual(len(layout["cards"]), 4)
        for card in layout["cards"]:
            self.assertTrue(layout["box"].contains(card["card_rect"]))
            self.assertTrue(card["card_rect"].contains(card["play_btn"]))
            self.assertTrue(card["card_rect"].contains(card["del_btn"]))
            self.assertFalse(card["play_btn"].colliderect(card["del_btn"]))


if __name__ == "__main__":
    unittest.main()

"""Shape Garden persistent project contracts without Pygame display."""
from __future__ import annotations

import hashlib
import unittest

from activities.shape_garden.garden_model import GardenModel, Particle, PlacedShape
from activities.shape_garden.garden_project_model import GardenProject, GardenStamp
from activities.shape_garden.garden_project_repository import (
    GardenProjectError,
    GardenProjectRepository,
)


class MemoryStorage:
    def __init__(self):
        self.kv = {}
        self.files = {}
        self.fail_kv = False

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        if self.fail_kv:
            raise RuntimeError("kv failed")
        self.kv[key] = value

    def file_write_atomic(self, name, payload):
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_list(self, prefix=None):
        names = sorted(self.files)
        if prefix:
            names = [name for name in names if name.startswith(prefix)]
        return tuple(names)

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class GardenProjectTests(unittest.TestCase):
    def test_project_roundtrip_restores_only_durable_shapes(self):
        model = GardenModel()
        model.add_shape(PlacedShape(100, 120, 30, 1, 2, 50.0))
        model.add_particle(Particle(1, 2, 3, 4, (1, 2, 3), 5, 6))
        model.reaction_until = 99
        project = GardenProject.from_model(model)
        restored = GardenModel()
        project.restore_model(restored, now=100.0)
        self.assertEqual(len(restored.shapes), 1)
        self.assertEqual(restored.shapes[0].spawn_time, 99.0)
        self.assertEqual(restored.particles, [])
        self.assertEqual(restored.reaction_until, 0.0)

    def test_invalid_stamp_and_background_digest_fail_closed(self):
        with self.assertRaises(ValueError):
            GardenStamp(-1, 20, 30, 0, 0)
        with self.assertRaises(ValueError):
            GardenStamp(10, 20, 30, 99, 0)
        with self.assertRaises(ValueError):
            GardenProject(background_sha256="not-a-digest")

    def test_repository_keeps_content_addressed_background_and_reclaims_old(self):
        storage = MemoryStorage()
        repo = GardenProjectRepository(storage)
        first = b"png-one"
        p1 = repo.save(GardenProject(), replacement_background_png=first)
        first_name = repo._background_name(hashlib.sha256(first).hexdigest())
        self.assertEqual(storage.files[first_name], first)
        self.assertEqual(repo.load_background(p1), first)

        second = b"png-two"
        p2 = repo.save(p1, replacement_background_png=second)
        second_name = repo._background_name(hashlib.sha256(second).hexdigest())
        self.assertNotIn(first_name, storage.files)
        self.assertEqual(storage.files[second_name], second)
        self.assertEqual(repo.load(), p2)

    def test_failed_metadata_commit_preserves_previous_project_and_blob(self):
        storage = MemoryStorage()
        repo = GardenProjectRepository(storage)
        original = b"original"
        previous = repo.save(GardenProject(), replacement_background_png=original)
        previous_name = repo._background_name(previous.background_sha256)
        storage.fail_kv = True
        with self.assertRaises(GardenProjectError):
            repo.save(previous, replacement_background_png=b"new")
        storage.fail_kv = False
        self.assertIn(previous_name, storage.files)
        self.assertEqual(repo.load(), previous)
        self.assertEqual(len(storage.files), 1)

    def test_corrupt_background_is_rejected(self):
        storage = MemoryStorage()
        repo = GardenProjectRepository(storage)
        project = repo.save(GardenProject(), replacement_background_png=b"good")
        name = repo._background_name(project.background_sha256)
        storage.files[name] = b"tampered"
        with self.assertRaises(GardenProjectError):
            repo.load_background(project)

    def test_export_staging_file_replaces_in_place(self):
        storage = MemoryStorage()
        repo = GardenProjectRepository(storage)
        self.assertEqual(repo.save_export(b"one"), "garden/shared.png")
        self.assertEqual(repo.save_export(b"two"), "garden/shared.png")
        self.assertEqual(storage.files["garden/shared.png"], b"two")


if __name__ == "__main__":
    unittest.main()

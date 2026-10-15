"""Shape Garden <-> My Creations: picker import as backdrop, flattened share.

Covers the P4 image round trip contract on the Shape Garden side: a shared
garden is one flattened 1024x600 ``composition`` PNG that a consumer (Painting,
Teatrino, or Shape Garden itself) can import back as an independent picture.
"""
from __future__ import annotations

import hashlib
import io
import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from PIL import Image
import pygame

from activities.shape_garden import garden_app
from activities.shape_garden.garden_app import GardenApp
from activities.shape_garden.garden_content import EXPORT_NAME, GARDEN_HEIGHT, GARDEN_WIDTH, SHAPE_KINDS
from activities.shape_garden.garden_project_repository import GardenProjectRepository


class MemoryStorage:
    def __init__(self):
        self.kv = {}
        self.files = {}

    def kv_get(self, key, default=None):
        return self.kv.get(key, default)

    def kv_set(self, key, value):
        self.kv[key] = value

    def kv_delete(self, key):
        return self.kv.pop(key, None) is not None

    def file_write_atomic(self, name, payload):
        self.files[name] = bytes(payload)

    def file_read(self, name):
        if name not in self.files:
            raise RuntimeError("missing")
        return self.files[name]

    def file_list(self, prefix=None):
        return tuple(sorted(n for n in self.files if not prefix or n.startswith(prefix)))

    def file_delete(self, name):
        return self.files.pop(name, None) is not None


class FakeCreations:
    """A tiny trusted-broker double: publishing copies bytes into a shelf."""

    def __init__(self, storage):
        self.storage = storage
        self.requests = []
        self.polls = []
        self.published = []
        self.shelf = {}
        self.reply = SimpleNamespace(state="pending", selection_token=None)

    def request_selection(self, *, media_types):
        self.requests.append(media_types)
        return "request-1"

    def poll_selection(self, request_id):
        self.polls.append(request_id)
        return self.reply

    def publish_private_file(self, name, *, media_type, role):
        payload = self.storage.file_read(name)
        self.published.append((name, media_type, role))
        self.shelf[f"token-{len(self.published)}"] = payload

    def import_selected(self, token):
        payload = self.shelf[token]
        record = {"media_type": "image/png", "sha256": hashlib.sha256(payload).hexdigest()}
        return SimpleNamespace(record=record, payload=payload)


class Silent:
    def __init__(self):
        self.played, self.spoken = [], []

    def play(self, name):
        self.played.append(name)

    def pop(self, kind):
        self.played.append(kind)

    def say(self, cue):
        self.spoken.append(cue)


def png_bytes(size=(320, 200), colour=(30, 160, 90)):
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, format="PNG")
    return buffer.getvalue()


class GardenCreationsTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1024, 600))
        self.storage = MemoryStorage()
        self.creations = FakeCreations(self.storage)
        self.now = [100.0]
        self.app = GardenApp(
            self.screen,
            repository=GardenProjectRepository(self.storage),
            creations=self.creations,
            sounds=Silent(),
            clock=lambda: self.now[0],
        )

    def tearDown(self):
        pygame.quit()

    def plant(self, kind="star", point=(400, 260)):
        self.assertTrue(self.app._plant(kind, point))

    def test_share_is_offered_only_for_a_made_garden(self):
        self.assertTrue(self.app.controls.share.visible)
        self.assertFalse(self.app.controls.share.enabled)
        self.app._publish_project()
        self.assertEqual(self.creations.published, [])
        self.plant()
        self.assertTrue(self.app.controls.share.enabled)

    def test_publish_is_one_flattened_composition_and_deduplicated(self):
        self.plant("heart", (300, 200))
        with mock.patch.object(garden_app, "emit_activity_event") as emit:
            self.app._publish_project()
            self.app._publish_project()
        self.assertEqual(self.creations.published, [(EXPORT_NAME, "image/png", "composition")])
        emit.assert_called_once()
        self.assertEqual(emit.call_args.args[0], "creation.completed")
        with Image.open(io.BytesIO(self.storage.files[EXPORT_NAME])) as image:
            self.assertEqual(image.size, (GARDEN_WIDTH, GARDEN_HEIGHT))
        self.assertEqual(self.app.cast.pose, "cheer")
        self.assertIn("praise.general", self.app.sounds.spoken)
        # The private garden was saved first; the share never replaced it.
        self.assertEqual(len(GardenProjectRepository(self.storage).list_records()), 1)

    def test_ghost_hints_never_reach_the_shared_picture(self):
        self.app._choose_ghost("house")
        self.plant("circle", (900, 500))
        plain = self.app._render_export()
        with_ghost = self.app.renderer.composer.compose(
            self.app.state, (GARDEN_WIDTH, GARDEN_HEIGHT), ghost=self.app.editor.ghost_picture,
        )
        self.assertNotEqual(pygame.image.tostring(plain, "RGB"), pygame.image.tostring(with_ghost, "RGB"))
        self.assertEqual(plain.get_size(), (GARDEN_WIDTH, GARDEN_HEIGHT))

    def test_import_request_is_typed_nonblocking_and_cancel_changes_nothing(self):
        self.plant()
        before = self.app.state
        self.app._choose_backdrop("import")
        self.assertEqual(self.creations.requests, [("image/png",)])
        self.assertEqual(self.app.import_state, "pending")
        self.app._poll_background(self.now[0])  # rate limited
        self.assertEqual(self.creations.polls, [])
        self.now[0] += 0.2
        self.app._poll_background(self.now[0])
        self.assertEqual(self.creations.polls, ["request-1"])
        self.creations.reply = SimpleNamespace(state="cancelled", selection_token=None)
        self.now[0] += 0.2
        self.app._poll_background(self.now[0])
        self.assertIsNone(self.app.import_request)
        self.assertEqual(self.app.state, before)

    def test_selected_png_becomes_a_private_backdrop_and_survives_reopen(self):
        payload = png_bytes()
        self.creations.shelf["picked"] = payload
        self.plant()
        self.app._request_background()
        self.creations.reply = SimpleNamespace(state="ready", selection_token="picked")
        self.now[0] += 0.2
        self.app._poll_background(self.now[0])
        self.assertEqual(self.app.import_state, "imported")
        digest = hashlib.sha256(payload).hexdigest()
        self.assertEqual((self.app.state.backdrop, self.app.state.picture), ("picture", digest))
        self.assertIn(f"garden/backgrounds/{digest}.png", self.storage.files)
        pygame.quit()
        pygame.init()
        screen = pygame.display.set_mode((800, 480))
        reopened = GardenApp(screen, repository=GardenProjectRepository(self.storage), sounds=Silent())
        self.assertEqual(reopened.state.backdrop, "picture")
        self.assertIsNotNone(reopened.picture_surface)

    def test_corrupt_selection_never_changes_the_garden(self):
        self.creations.shelf["bad"] = b"not a png"
        self.plant()
        before = self.app.state
        self.assertFalse(self.app._accept_background("bad"))
        self.assertEqual(self.app.state, before)
        self.assertFalse(any(name.startswith("garden/backgrounds/") for name in self.storage.files))

    def test_round_trip_shared_garden_comes_back_as_a_backdrop(self):
        for index, kind in enumerate(SHAPE_KINDS[:4]):
            self.plant(kind, (200 + index * 180, 300))
        self.app._publish_project()
        token = next(iter(self.creations.shelf))
        shared = self.creations.shelf[token]
        # A new garden takes the shared picture back as its backdrop.
        self.app._press_new()
        self.assertTrue(self.app.state.blank)
        self.assertTrue(self.app._accept_background(token))
        self.assertEqual(self.app.state.picture, hashlib.sha256(shared).hexdigest())
        self.assertEqual(self.app.picture_surface.get_size(), (GARDEN_WIDTH, GARDEN_HEIGHT))
        records = GardenProjectRepository(self.storage).list_records()
        self.assertEqual(len(records), 2)  # the original garden is untouched
        original = GardenProjectRepository(self.storage).load(records[1].garden_id)
        self.assertEqual(len(original.state.shapes), 4)


if __name__ == "__main__":
    unittest.main()
